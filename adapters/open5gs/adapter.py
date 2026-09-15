from __future__ import annotations

import hashlib
import ipaddress
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from project_72.assurance_core.lifecycle import transition
from project_72.assurance_core.models import (
    AuthoritativeReadback,
    ExecutionRequest,
    Subscriber,
    SubscriberStatus,
)
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
    """Project canonical lifecycle state into the Open5GS subscribers collection."""

    canonical: SubscriberRepository
    collection: Open5GSCollection
    secret_resolver: SecretResolver
    database_name: str = "open5gs"
    collection_name: str = "subscribers"

    @classmethod
    def from_mongodb(
        cls,
        canonical: SubscriberRepository,
        mongodb_uri: str,
        secret_resolver: SecretResolver,
        *,
        database_name: str = "open5gs",
    ) -> "Open5GSAdapter":
        """Create a runtime adapter without embedding database credentials."""
        from pymongo import MongoClient

        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        collection = client[database_name]["subscribers"]
        return cls(canonical, collection, secret_resolver, database_name=database_name)

    def execute(self, request: ExecutionRequest) -> bool:
        if request.operation not in {"ACTIVATE", "SUSPEND", "DEACTIVATE"}:
            raise Open5GSAdapterError(f"unsupported Open5GS lifecycle operation: {request.operation}")

        current = self.canonical.get(request.target)
        if current.version == request.expected_version:
            try:
                target = transition(current, request.operation)
            except ValueError as exc:
                raise Open5GSAdapterError(str(exc)) from exc
            self.canonical.put(target, expected_version=request.expected_version)
        elif current.version == request.expected_version + 1:
            target = current
            expected_target_status = {
                "ACTIVATE": SubscriberStatus.ACTIVE,
                "SUSPEND": SubscriberStatus.SUSPENDED,
                "DEACTIVATE": SubscriberStatus.RETIRED,
            }[request.operation]
            if current.status is not expected_target_status:
                raise Open5GSAdapterError(
                    f"recovery state mismatch for {current.subscriber_id}: "
                    f"expected {expected_target_status.value}, current {current.status.value}"
                )
        else:
            raise Open5GSAdapterError(
                f"canonical version conflict for {current.subscriber_id}: "
                f"expected {request.expected_version}, current {current.version}"
            )

        existing = self.collection.find_one({"imsi": target.imsi})
        existing_marker = _assurance_marker(existing)
        if existing_marker is not None:
            existing_version = int(existing_marker.get("canonical_version", 0))
            if existing_version > target.version:
                raise Open5GSAdapterError(
                    f"Open5GS projection is newer than canonical state for {target.subscriber_id}"
                )
            if existing_version == target.version and _projection_matches(target, existing):
                return True

        auth = self.secret_resolver.resolve(target.secret_refs["authentication"])
        document = self._build_document(target, auth)
        self.collection.replace_one({"imsi": target.imsi}, document, upsert=True)
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
                details={"imsi": subscriber.imsi, "ue_ip": subscriber.ue_ip},
            )

        marker = _assurance_marker(document) or {}
        observed_version = int(marker.get("canonical_version", 0))
        state = _readback_state(subscriber, document)
        return AuthoritativeReadback(
            request_id="readback",
            source=f"{self.database_name}.{self.collection_name}",
            target=subscriber_id,
            observed_version=observed_version,
            state=state,
            fingerprint=_fingerprint(document),
            details={
                "imsi": document.get("imsi"),
                "ue_ip": _projected_ue_ip(document),
                "subscriber_status": document.get("subscriber_status"),
                "marker": dict(marker),
                "services": _projected_services(document),
            },
        )

    def _build_document(self, subscriber: Subscriber, auth: Mapping[str, str]) -> dict[str, Any]:
        try:
            ipaddress.ip_address(subscriber.ue_ip)
        except ValueError as exc:
            raise Open5GSAdapterError(f"invalid UE IP: {subscriber.ue_ip}") from exc

        if not {"k", "opc", "amf"}.issubset(auth):
            raise Open5GSAdapterError("secret resolver must provide k, opc and amf")

        sessions: list[dict[str, Any]] = [
            _session(name="internet", qos_index=9, ue_ipv4=subscriber.ue_ip)
        ]
        if subscriber.services.get("ims", False):
            sessions.append(_session(name="ims", qos_index=5, ue_ipv4=None))

        active = subscriber.status is SubscriberStatus.ACTIVE
        open5gs_status = 0 if active else 1
        return {
            "schema_version": 1,
            "imsi": subscriber.imsi,
            "msisdn": [subscriber.msisdn] if subscriber.msisdn else [],
            "imeisv": [],
            "mme_host": [],
            "mm_realm": [],
            "purge_flag": [],
            "slice": [{"sst": 1, "default_indicator": True, "session": sessions}],
            "security": {
                "k": auth["k"],
                "op": None,
                "opc": auth["opc"],
                "amf": auth["amf"],
            },
            "ambr": {
                "downlink": {"value": 1, "unit": 3},
                "uplink": {"value": 1, "unit": 3},
            },
            "access_restriction_data": 32,
            "network_access_mode": 0,
            "subscriber_status": open5gs_status,
            "operator_determined_barring": 0,
            "subscribed_rau_tau_timer": 12,
            "__v": 0,
            "mm7_assurance": {
                "subscriber_id": subscriber.subscriber_id,
                "canonical_version": subscriber.version,
                "status": subscriber.status.value,
            },
        }


def _session(*, name: str, qos_index: int, ue_ipv4: str | None) -> dict[str, Any]:
    session: dict[str, Any] = {
        "name": name,
        "type": 3,
        "qos": {
            "index": qos_index,
            "arp": {
                "priority_level": 8 if name == "internet" else 1,
                "pre_emption_capability": 1,
                "pre_emption_vulnerability": 2,
            },
        },
        "ambr": {
            "downlink": {"value": 1, "unit": 3},
            "uplink": {"value": 1, "unit": 3},
        },
        "pcc_rule": [],
    }
    if ue_ipv4 is not None:
        session["ue"] = {"ipv4": ue_ipv4}
    return session


def _assurance_marker(document: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not document:
        return None
    marker = document.get("mm7_assurance")
    return marker if isinstance(marker, Mapping) else None


def _projection_matches(subscriber: Subscriber, document: Mapping[str, Any]) -> bool:
    marker = _assurance_marker(document) or {}
    expected_status = subscriber.status.value
    expected_open5gs_status = 0 if subscriber.status is SubscriberStatus.ACTIVE else 1
    if (
        document.get("imsi") != subscriber.imsi
        or marker.get("subscriber_id") != subscriber.subscriber_id
        or int(marker.get("canonical_version", 0)) != subscriber.version
        or marker.get("status") != expected_status
        or int(document.get("subscriber_status", -1)) != expected_open5gs_status
    ):
        return False

    slices = document.get("slice")
    if not isinstance(slices, list) or not slices:
        return False
    sessions = slices[0].get("session") if isinstance(slices[0], Mapping) else None
    if not isinstance(sessions, list):
        return False
    internet = next((s for s in sessions if isinstance(s, Mapping) and s.get("name") == "internet"), None)
    if not isinstance(internet, Mapping):
        return False
    ue = internet.get("ue")
    return isinstance(ue, Mapping) and ue.get("ipv4") == subscriber.ue_ip


def _readback_state(subscriber: Subscriber, document: Mapping[str, Any]) -> str:
    if _projection_matches(subscriber, document):
        return subscriber.status.value
    return "MISMATCH"


def _projected_ue_ip(document: Mapping[str, Any]) -> str | None:
    slices = document.get("slice")
    sessions = (
        slices[0].get("session")
        if isinstance(slices, list) and slices and isinstance(slices[0], Mapping)
        else []
    )
    internet = next(
        (s for s in sessions if isinstance(s, Mapping) and s.get("name") == "internet"),
        None,
    )
    ue = internet.get("ue") if isinstance(internet, Mapping) else None
    ip = ue.get("ipv4") if isinstance(ue, Mapping) else None
    return ip if isinstance(ip, str) else None


def _projected_services(document: Mapping[str, Any]) -> dict[str, bool]:
    slices = document.get("slice")
    sessions = (
        slices[0].get("session")
        if isinstance(slices, list) and slices and isinstance(slices[0], Mapping)
        else []
    )
    names = {s.get("name") for s in sessions if isinstance(s, Mapping)}
    return {"data": "internet" in names, "ims": "ims" in names}


def _fingerprint(document: Mapping[str, Any]) -> str:
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
