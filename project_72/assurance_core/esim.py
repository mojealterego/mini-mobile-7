from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol


class EsimProvisioningError(RuntimeError):
    """Raised when an eSIM provisioning artifact cannot be safely created."""


class EsimStatus(str, Enum):
    PLANNED = "PLANNED"
    GENERATED = "GENERATED"
    INSTALLED = "INSTALLED"
    VERIFIED = "VERIFIED"


class EsimSecretResolver(Protocol):
    def resolve(self, secret_ref: str) -> Mapping[str, str]:
        """Resolve external provisioning material without persisting it."""


@dataclass(frozen=True, slots=True)
class EsimProfileMetadata:
    subscriber_id: str
    profile_id: str
    smdp_address: str
    activation_code_ref: str


@dataclass(frozen=True, slots=True)
class EsimActivationArtifact:
    subscriber_id: str
    profile_id: str
    smdp_address: str
    activation_code_ref: str
    activation_uri: str
    activation_uri_sha256: str
    status: EsimStatus


class EsimArtifactGenerator:
    """Build an LPA activation artifact from external SM-DP+ data.

    This class never manufactures an eSIM profile, contacts an SM-DP+,
    installs a profile, or claims device verification. The matching ID must
    be supplied by the real provisioning system through a secret reference.
    """

    def generate(
        self,
        metadata: EsimProfileMetadata,
        resolver: EsimSecretResolver,
    ) -> EsimActivationArtifact:
        self._validate_metadata(metadata)
        values = resolver.resolve(metadata.activation_code_ref)
        matching_id = values.get("matching_id", "")
        if not matching_id:
            raise EsimProvisioningError(
                "external eSIM secret must provide matching_id from the provisioning system"
            )
        if any(ch in matching_id for ch in "\r\n$"):
            raise EsimProvisioningError("matching_id contains forbidden activation-code characters")
        if not re.fullmatch(r"[A-Za-z0-9._~:/?&=+@%-]{1,512}", matching_id):
            raise EsimProvisioningError("matching_id contains unsupported characters")

        activation_uri = f"LPA:1${metadata.smdp_address}${matching_id}"
        digest = hashlib.sha256(activation_uri.encode("utf-8")).hexdigest()
        return EsimActivationArtifact(
            subscriber_id=metadata.subscriber_id,
            profile_id=metadata.profile_id,
            smdp_address=metadata.smdp_address,
            activation_code_ref=metadata.activation_code_ref,
            activation_uri=activation_uri,
            activation_uri_sha256=digest,
            status=EsimStatus.GENERATED,
        )

    @staticmethod
    def _validate_metadata(metadata: EsimProfileMetadata) -> None:
        if metadata.subscriber_id not in {f"700{i}" for i in range(1, 8)}:
            raise EsimProvisioningError("subscriber_id must be one of 7001-7007")
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,128}", metadata.profile_id):
            raise EsimProvisioningError("profile_id has invalid format")
        if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", metadata.smdp_address):
            raise EsimProvisioningError("smdp_address must be a DNS host-like value")
        if not metadata.activation_code_ref.startswith("env://"):
            raise EsimProvisioningError("activation_code_ref must be an external env:// secret reference")
