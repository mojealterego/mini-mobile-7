from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Mapping

from .esim import EsimArtifactGenerator, EsimProfileMetadata, EsimSecretResolver, EsimStatus
from .esim_repository import EsimArtifactConflictError, EsimArtifactRepository, StoredEsimArtifact
from .models import AuthoritativeReadback, ExecutionRequest, Subscriber, SubscriberStatus
from .store import StoreConflictError, SubscriberRepository


class EsimProvisioningAdapter:
    """Execute ESIM_GENERATE against canonical state and a metadata-only artifact store.

    This adapter does not contact an SM-DP+, install an eSIM on a handset, or
    claim device verification. VERIFIED means only that the generated artifact
    is durably represented and matches canonical state by authoritative readback.
    """

    OPERATION = "ESIM_GENERATE"

    def __init__(
        self,
        repository: SubscriberRepository,
        artifact_repository: EsimArtifactRepository,
        secret_resolver: EsimSecretResolver,
        *,
        smdp_address: str,
    ) -> None:
        self._repository = repository
        self._artifacts = artifact_repository
        self._resolver = secret_resolver
        self._smdp_address = smdp_address
        self._generator = EsimArtifactGenerator()

    def execute(self, request: ExecutionRequest) -> bool:
        if request.operation != self.OPERATION:
            raise ValueError(f"unsupported eSIM operation: {request.operation}")

        subscriber = self._repository.get(request.target)
        if subscriber.version != request.expected_version:
            raise StoreConflictError(
                f"eSIM execution expected version {request.expected_version}, "
                f"current canonical version is {subscriber.version}"
            )
        if subscriber.profile_id is None:
            raise ValueError("canonical subscriber has no profile_id")
        if subscriber.esim_status not in {EsimStatus.PLANNED, EsimStatus.GENERATED}:
            raise ValueError(f"eSIM generation not allowed from {subscriber.esim_status.value}")

        artifact = self._generator.generate(
            EsimProfileMetadata(
                subscriber_id=subscriber.subscriber_id,
                profile_id=subscriber.profile_id,
                smdp_address=self._smdp_address,
                activation_code_ref=subscriber.secret_refs["esim_activation"],
            ),
            self._resolver,
        )
        next_version = subscriber.version + 1
        stored = StoredEsimArtifact(
            subscriber_id=artifact.subscriber_id,
            profile_id=artifact.profile_id,
            smdp_address=artifact.smdp_address,
            activation_code_ref=artifact.activation_code_ref,
            activation_uri_sha256=artifact.activation_uri_sha256,
            status=artifact.status.value,
            version=next_version,
        )
        self._artifacts.put(stored, expected_version=0 if subscriber.esim_status is EsimStatus.PLANNED else subscriber.version)

        updated = replace(subscriber, version=next_version, esim_status=EsimStatus.GENERATED)
        self._repository.put(updated, expected_version=request.expected_version)
        return True

    def readback(self, subscriber_id: str) -> AuthoritativeReadback:
        canonical = self._repository.get(subscriber_id)
        artifact = self._artifacts.get(subscriber_id)
        consistent = (
            canonical.version == artifact.version
            and canonical.profile_id == artifact.profile_id
            and canonical.esim_status.value == artifact.status
            and artifact.status == EsimStatus.GENERATED.value
        )
        fingerprint = _artifact_fingerprint(artifact)
        return AuthoritativeReadback(
            request_id="eSIM-readback",
            source="canonical-subscriber-store+esim-artifact-store",
            target=subscriber_id,
            observed_version=artifact.version,
            state="GENERATED" if consistent else "MISMATCH",
            fingerprint=fingerprint,
            details={
                "profile_id": artifact.profile_id,
                "smdp_address": artifact.smdp_address,
                "activation_code_ref": artifact.activation_code_ref,
                "activation_uri_sha256": artifact.activation_uri_sha256,
                "artifact_status": artifact.status,
                "canonical_version": canonical.version,
                "canonical_esim_status": canonical.esim_status.value,
            },
        )

    @staticmethod
    def postcondition(readback: AuthoritativeReadback) -> tuple[bool, str]:
        if readback.state != "GENERATED":
            return False, "authoritative eSIM artifact state is not GENERATED"
        details = readback.details
        if details.get("artifact_status") != EsimStatus.GENERATED.value:
            return False, "artifact status is not GENERATED"
        if details.get("canonical_esim_status") != EsimStatus.GENERATED.value:
            return False, "canonical eSIM status is not GENERATED"
        if details.get("canonical_version") != readback.observed_version:
            return False, "canonical and artifact versions differ"
        digest = details.get("activation_uri_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            return False, "activation URI fingerprint is invalid"
        if readback.fingerprint != _artifact_fingerprint_from_values(details):
            return False, "artifact fingerprint does not match authoritative metadata"
        return True, "eSIM generation artifact postcondition satisfied"


def _artifact_fingerprint(artifact: StoredEsimArtifact) -> str:
    return hashlib.sha256(
        "|".join(
            (
                artifact.subscriber_id,
                artifact.profile_id,
                artifact.smdp_address,
                artifact.activation_code_ref,
                artifact.activation_uri_sha256,
                artifact.status,
                str(artifact.version),
            )
        ).encode("utf-8")
    ).hexdigest()


def _artifact_fingerprint_from_values(details: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        "|".join(
            (
                str(details.get("subscriber_id", "")),
                str(details.get("profile_id", "")),
                str(details.get("smdp_address", "")),
                str(details.get("activation_code_ref", "")),
                str(details.get("activation_uri_sha256", "")),
                str(details.get("artifact_status", "")),
                str(details.get("canonical_version", "")),
            )
        ).encode("utf-8")
    ).hexdigest()
