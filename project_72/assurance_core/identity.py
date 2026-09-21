from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrivateIdentity:
    """Deterministic private identity for one controlled lab subscriber.

    The extension is intentionally not presented as public E.164 numbering.
    Public MSISDN allocation must be supplied by an authorized numbering
    provider/operator before any public-telephony identity is introduced.
    """

    subscriber_id: str
    extension: str
    sip_uri: str
    tel_uri: str


class IdentityGenerator:
    """Generate the project's seven deterministic private identities."""

    def __init__(self, *, sip_domain: str = "ims.mm7.local") -> None:
        if not sip_domain or any(ch.isspace() for ch in sip_domain):
            raise ValueError("sip_domain must be a non-empty host-like value")
        self._sip_domain = sip_domain

    def generate(self, subscriber_id: str) -> PrivateIdentity:
        self._validate_subscriber_id(subscriber_id)
        extension = subscriber_id
        return PrivateIdentity(
            subscriber_id=subscriber_id,
            extension=extension,
            sip_uri=f"sip:{extension}@{self._sip_domain}",
            tel_uri=f"tel:{extension}",
        )

    def generate_all(self) -> tuple[PrivateIdentity, ...]:
        return tuple(self.generate(f"700{i}") for i in range(1, 8))

    @staticmethod
    def _validate_subscriber_id(subscriber_id: str) -> None:
        if subscriber_id not in {f"700{i}" for i in range(1, 8)}:
            raise ValueError("subscriber_id must be one of 7001-7007")
