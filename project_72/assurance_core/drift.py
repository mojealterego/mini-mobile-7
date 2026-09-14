from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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
    """Compare desired canonical state with authoritative runtime readback.

    Detection is deliberately side-effect free. It never repairs a projection.
    Repair requires a separate authorized capability and an assurance cycle.
    """

    def compare(self, subscriber: Subscriber, readback: AuthoritativeReadback) -> DriftReport:
        if readback.target != subscriber.subscriber_id:
            return DriftReport(
                subscriber.subscriber_id,
                DriftState.DRIFT,
                subscriber.version,
                readback.observed_version,
                "readback target does not match canonical subscriber",
            )

        if readback.state == "ABSENT":
            return DriftReport(
                subscriber.subscriber_id,
                DriftState.ABSENT,
                subscriber.version,
                readback.observed_version,
                "Open5GS projection is absent",
            )

        if readback.state != "ACTIVE":
            return DriftReport(
                subscriber.subscriber_id,
                DriftState.DRIFT,
                subscriber.version,
                readback.observed_version,
                f"authoritative state is {readback.state}",
            )

        if readback.observed_version != subscriber.version:
            return DriftReport(
                subscriber.subscriber_id,
                DriftState.DRIFT,
                subscriber.version,
                readback.observed_version,
                "canonical and runtime versions differ",
            )

        services = readback.details.get("services")
        if isinstance(services, dict):
            for name in ("data", "ims"):
                if bool(services.get(name, False)) != bool(subscriber.services.get(name, False)):
                    return DriftReport(
                        subscriber.subscriber_id,
                        DriftState.DRIFT,
                        subscriber.version,
                        readback.observed_version,
                        f"service projection mismatch: {name}",
                    )

        return DriftReport(
            subscriber.subscriber_id,
            DriftState.IN_SYNC,
            subscriber.version,
            readback.observed_version,
            "canonical and runtime state are synchronized",
        )
