from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Mapping

from .esim import EsimArtifactGenerator, EsimProfileMetadata, EsimSecretResolver, EsimStatus
from .esim_repository import EsimArtifactNotFoundError, EsimArtifactRepository, StoredEsimArtifact
from .models import AuthoritativeReadback, ExecutionRequest, Subscriber
from .store import StoreConflictError, SubscriberRepository


class EsimProvisioningAdapter:
    """Execute ESIM_GENERATE against canonical state and a metadata-only artifact store.

    This adapter does not contact an SM-DP+, install an eSIM on a handset, or
    claim device verification. VERIFIED means only that the generated artifact
    is durably represented and matches canonical state by authoritative readback.

    The two stores are intentionally reconciled fail-closed: an artifact write
    can never cause a canonical eSIM state to be assumed. A retry may promote a
    matching, already-persisted artifact to canonical state without regenerating
    a provisioning artifact or contacting an external eSIM service.
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

        reconciled = self._reconcile_persisted_artifact(subscriber)
        if reconciled is not None:
            return reconciled

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
        artifact_expected_version = 0 if subscriber.esim_status is EsimStatus.PLANNED else subscriber.version
        stored = StoredEsimArtifact(
            subscriber_id=artifact.subscriber_id,
            profile_id=artifact.profile_id,
            smdp_address=artifact.smdp_address,
            activation_code_ref=artifact.activation_code_ref,
            activation_uri_sha256=artifact.activation_uri_sha256,
            status=artifact.status.value,
            version=next_version,
        )
        self._artifacts.put(stored, expected_version=artifact_expected_version)

        updated = replace(subscriber, version=next_version, esim_status=EsimStatus.GENERATED)
        self._repository.put(updated, expected_version=request.expected_version)
        return True

    def _reconcile_persisted_artifact(self, subscriber: Subscriber) -> bool | None:
        """Promote only an exact artifact left by a previous interrupted commit."""
        try:
            artifact = self._artifacts.get(subscriber.subscriber_id)
        except EsimArtifactNotFoundError:
            return None

        expected_version = subscriber.version + 1
        if artifact.version != expected_version:
            return None
        if artifact.status != EsimStatus.GENERATED.value:
            return None
        if artifact.profile_id != subscriber.profile_id:
            raise ValueError("persisted eSIM artifact profile does not match canonical state")
        if artifact.smdp_address != self._smdp_address:
            raise ValueError("persisted eSIM artifact SM-DP+ address does not match configured authority")
        if artifact.activation_code_ref != subscriber.secret_refs.get("esim_activation"):
            raise ValueError("persisted eSIM artifact activation reference does not match canonical state")

        updated = replace(subscriber, version=expected_version, esim_status=EsimStatus.GENERATED)
        self._repository.put(updated, expected_version=subscriber.version)
        return True

    def readback(self, subscriber_id: str) -> AuthoritativeReadback:
        canonical = self._repository.get(subscriber_id)
        try:
            artifact = self._artifacts.get(subscriber_id)
        except EsimArtifactNotFoundError:
            return AuthoritativeReadback(
                request_id="eSIM-readback",
                source="canonical-subscriber-store+esim-artifact-store",
                target=subscriber_id,
                observed_version=canonical.version,
                state="ABSENT",
                fingerprint="",
                details={
                    "subscriber_id": subscriber_id,
                    "canonical_version": canonical.version,
                    "canonical_esim_status": canonical.esim_status.value,
                },
            )

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
                "subscriber_id": subscriber_id,
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


def _artifact_fingerprint_from_values(details: Mapping[str, object]) -> str:
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
