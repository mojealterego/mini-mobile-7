from __future__ import annotations

import hashlib
import ipaddress
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from project_72.assurance_core.models import AuthoritativeReadback, ExecutionRequest, Subscriber
from project_72.assurance_core.store import SubscriberRepository

from .secrets import SecretResolver


class Open5GSCollection(Protocol):
    def find_one(self, filter: Mapping[str, Any]) -> Mapping[str, Any] | None: ...

    def replace_one(
        self,
        filter: Mapping[str, Any],
        replacement: Mapping[str, Any],
        *,
        upsert: bool,
    ) -> Any: ...


class Open5GSAdapterError(RuntimeError):
    """Raised when an Open5GS projection cannot be safely applied."""


@dataclass(frozen=True, slots=True)
class Open5GSAdapter:
    """Project canonical subscribers into Open5GS MongoDB and read them back.

    Open5GS remains a projection/authoritative runtime target. The canonical
    subscriber repository is the sole source of desired state. Authentication
    material is resolved only at execution time through SecretResolver.
    """

    canonical: SubscriberRepository
    collection: Open5GSCollection
    secret_resolver: SecretResolver
    database_name: str = "open5gs"
    collection_name: str = "subscribers"

    def execute(self, request: ExecutionRequest) -> bool:
        if request.operation != "ACTIVATE":
            raise Open5GSAdapterError(f"unsupported Open5GS operation: {request.operation}")

        subscriber = self.canonical.get(request.target)
        if subscriber.version != request.expected_version:
            raise Open5GSAdapterError(
                f"canonical version conflict for {subscriber.subscriber_id}: "
                f"expected {request.expected_version}, current {subscriber.version}"
            )
        if subscriber.status.value != "ACTIVE":
            raise Open5GSAdapterError(
                f"subscriber {subscriber.subscriber_id} is not ACTIVE in canonical state"
            )

        existing = self.collection.find_one({"imsi": subscriber.imsi})
        existing_marker = _assurance_marker(existing)
        if existing_marker is not None:
            existing_version = int(existing_marker.get("canonical_version", 0))
            if existing_version == subscriber.version:
                return True
            if existing_version > subscriber.version:
                raise Open5GSAdapterError(
                    f"Open5GS projection is newer than canonical state for {subscriber.subscriber_id}"
                )

        auth = self.secret_resolver.resolve(subscriber.secret_refs["authentication"])
        document = self._build_document(subscriber, auth)
        self.collection.replace_one({"imsi": subscriber.imsi}, document, upsert=True)
        return True

    def readback(self, subscriber_id: str) -> AuthoritativeReadback:
        subscriber = self.canonical.get(subscriber_id)
        document = self.collection.find_one({"imsi": subscriber.imsi})
        if document is None:
            return AuthoritativeReadback(
                request_id="readback",
                source=f"{self.database_name}.{self.collection_name}",
                target=subscriber_id,
                observed_version=0,
                state="ABSENT",
                fingerprint="",
                details={"imsi": subscriber.imsi},
            )

        marker = _assurance_marker(document) or {}
        observed_version = int(marker.get("canonical_version", 0))
        state = "ACTIVE" if _projection_matches(subscriber, document) else "MISMATCH"
        fingerprint = _fingerprint(document)
        return AuthoritativeReadback(
            request_id="readback",
            source=f"{self.database_name}.{self.collection_name}",
            target=subscriber_id,
            observed_version=observed_version,
            state=state,
            fingerprint=fingerprint,
            details={
                "imsi": document.get("imsi"),
                "marker": dict(marker),
            },
        )

    def _build_document(self, subscriber: Subscriber, auth: Mapping[str, str]) -> dict[str, Any]:
        try:
            ipaddress.ip_address(subscriber.ue_ip)
        except ValueError as exc:
            raise Open5GSAdapterError(f"invalid UE IP: {subscriber.ue_ip}") from exc

        return {
            "imsi": subscriber.imsi,
            "security": {
                "k": auth["k"],
                "opc": auth["opc"],
                "amf": auth["amf"],
            },
            "ambr": {
                "downlink": {"value": 1, "unit": 3},
                "uplink": {"value": 1, "unit": 3},
            },
            "slice": [
                {
                    "sst": 1,
                    "default_indicator": True,
                    "session": [
                        {
                            "name": "internet",
                            "type": 3,
                            "qos": {"index": 9, "arp": {"priority": 8}},
                            "ambr": {"downlink": {"value": 1, "unit": 3}, "uplink": {"value": 1, "unit": 3}},
                        }
                    ],
                }
            ],
            "ue": {"ipv4": subscriber.ue_ip},
            "mm7_assurance": {
                "subscriber_id": subscriber.subscriber_id,
                "canonical_version": subscriber.version,
                "status": "ACTIVE",
            },
        }


def _assurance_marker(document: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not document:
        return None
    marker = document.get("mm7_assurance")
    return marker if isinstance(marker, Mapping) else None


def _projection_matches(subscriber: Subscriber, document: Mapping[str, Any]) -> bool:
    marker = _assurance_marker(document) or {}
    return (
        document.get("imsi") == subscriber.imsi
        and marker.get("subscriber_id") == subscriber.subscriber_id
        and int(marker.get("canonical_version", 0)) == subscriber.version
        and marker.get("status") == "ACTIVE"
        and document.get("ue", {}).get("ipv4") == subscriber.ue_ip
    )


def _fingerprint(document: Mapping[str, Any]) -> str:
    import json

    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
