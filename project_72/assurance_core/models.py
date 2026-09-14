from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class SubscriberStatus(str, Enum):
    PROVISIONED = "PROVISIONED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class AssuranceStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    DRIFT = "DRIFT"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Subscriber:
    subscriber_id: str
    imsi: str
    ue_ip: str
    version: int
    status: SubscriberStatus
    secret_refs: Mapping[str, str]
    services: Mapping[str, bool]
    msisdn: str | None = None

    def __post_init__(self) -> None:
        if self.subscriber_id not in {f"700{i}" for i in range(1, 8)}:
            raise ValueError("subscriber_id must be one of 7001-7007")
        if len(self.imsi) != 15 or not self.imsi.isdigit():
            raise ValueError("imsi must contain exactly 15 digits")
        if self.version < 1:
            raise ValueError("version must be >= 1")
        if not self.secret_refs.get("authentication"):
            raise ValueError("authentication secret_ref is required")

    def to_document(self) -> dict[str, Any]:
        return {
            "subscriber_id": self.subscriber_id,
            "imsi": self.imsi,
            "ue_ip": self.ue_ip,
            "version": self.version,
            "status": self.status.value,
            "secret_refs": dict(self.secret_refs),
            "services": dict(self.services),
            "msisdn": self.msisdn,
        }


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    principal: str
    operation: str
    resource: str
    decision: str
    policy_version: str
    risk: str


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    request_id: str
    idempotency_key: str
    capability_id: str
    operation: str
    target: str
    expected_version: int
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthoritativeReadback:
    request_id: str
    source: str
    target: str
    observed_version: int
    state: str
    fingerprint: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssuranceResult:
    request_id: str
    target: str
    status: AssuranceStatus
    authorization: bool
    policy: bool
    execution: bool
    readback: bool
    postcondition: bool
    reason: str
    observed_version: int | None = None
