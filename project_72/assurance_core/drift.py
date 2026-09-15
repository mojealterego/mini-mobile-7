from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .models import AuthoritativeReadback, Subscriber


class DriftState(str, Enum):
    IN_SYNC = "IN_SYNC"
    DRIFT = "DRIFT"
    ABSENT = "ABSENT"


@dataclass(frozen=True, slots=True)
class DriftReport:
    subscriber_id: str
    state: DriftState
    canonical_version: int
    observed_version: int
    reason: str


class DriftDetector:
    """Compare canonical intent with authoritative runtime readback.

    Detection is deliberately side-effect free. It never repairs a projection.
    Repair requires a separate authorized capability and a complete assurance cycle.
    """

    def compare(self, subscriber: Subscriber, readback: AuthoritativeReadback) -> DriftReport:
        if readback.target != subscriber.subscriber_id:
            return self._drift(subscriber, readback, "readback target does not match canonical subscriber")

        if readback.state == "ABSENT":
            return DriftReport(
                subscriber.subscriber_id,
                DriftState.ABSENT,
                subscriber.version,
                readback.observed_version,
                "Open5GS projection is absent",
            )

        if readback.state != subscriber.status.value:
            return self._drift(
                subscriber,
                readback,
                f"authoritative state is {readback.state}; canonical state is {subscriber.status.value}",
            )

        if readback.observed_version != subscriber.version:
            return self._drift(subscriber, readback, "canonical and runtime versions differ")

        details = readback.details
        if details.get("imsi") != subscriber.imsi:
            return self._drift(subscriber, readback, "IMSI projection mismatch")

        if details.get("ue_ip") != subscriber.ue_ip:
            return self._drift(subscriber, readback, "UE IP projection mismatch")

        marker = details.get("marker")
        if not isinstance(marker, Mapping):
            return self._drift(subscriber, readback, "authoritative assurance marker is missing")
        if marker.get("subscriber_id") != subscriber.subscriber_id:
            return self._drift(subscriber, readback, "assurance marker subscriber mismatch")
        marker_version = _safe_int(marker.get("canonical_version"))
        if marker_version != subscriber.version:
            return self._drift(subscriber, readback, "assurance marker version mismatch")
        if marker.get("status") != subscriber.status.value:
            return self._drift(subscriber, readback, "assurance marker lifecycle mismatch")

        services = details.get("services")
        if not isinstance(services, Mapping):
            return self._drift(subscriber, readback, "authoritative service projection is missing")
        for name in ("data", "ims"):
            if bool(services.get(name, False)) != bool(subscriber.services.get(name, False)):
                return self._drift(subscriber, readback, f"service projection mismatch: {name}")

        return DriftReport(
            subscriber.subscriber_id,
            DriftState.IN_SYNC,
            subscriber.version,
            readback.observed_version,
            "canonical and runtime state are synchronized",
        )

    @staticmethod
    def _drift(subscriber: Subscriber, readback: AuthoritativeReadback, reason: str) -> DriftReport:
        return DriftReport(
            subscriber.subscriber_id,
            DriftState.DRIFT,
            subscriber.version,
            readback.observed_version,
            reason,
        )


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
