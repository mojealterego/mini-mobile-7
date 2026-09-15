from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .models import Capability, ExecutionRequest, Subscriber


class CapabilityDeniedError(PermissionError):
    """Raised when a capability request fails closed."""


@dataclass(frozen=True, slots=True)
class Policy:
    version: str
    allowed_operations: frozenset[str]
    allowed_principals: frozenset[str]
    max_risk: str = "MEDIUM"


class CapabilityBroker:
    """Fail-closed authorization boundary. It never executes network operations."""

    _risk_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def __init__(self, policies: Mapping[str, Policy]) -> None:
        self._policies = dict(policies)

    def authorize(
        self,
        *,
        principal: str,
        request: ExecutionRequest,
        subscriber: Subscriber,
    ) -> Capability:
        policy = self._policies.get(request.operation)
        if policy is None:
            raise CapabilityDeniedError("no policy exists for requested operation")
        if principal not in policy.allowed_principals:
            raise CapabilityDeniedError("principal is outside policy scope")
        if request.operation not in policy.allowed_operations:
            raise CapabilityDeniedError("operation is not allowed by policy")
        if request.target != subscriber.subscriber_id:
            raise CapabilityDeniedError("target does not match canonical subscriber")
        if request.expected_version != subscriber.version:
            raise CapabilityDeniedError("expected_version does not match canonical state")
        if request.capability_id != f"cap-{request.request_id}":
            raise CapabilityDeniedError("capability_id does not bind to request_id")
        if request.operation == "ROUTE_CALL" and not subscriber.services.get("pstn_outbound", False):
            raise CapabilityDeniedError("PSTN outbound capability is not enabled")
        if request.operation in {"ESIM_GENERATE", "ESIM_ACTIVATE"}:
            if not subscriber.secret_refs.get("esim_activation"):
                raise CapabilityDeniedError("eSIM provisioning secret_ref is not configured")
            if not subscriber.profile_id:
                raise CapabilityDeniedError("eSIM profile_id is not configured")

        risk = "MEDIUM" if request.operation in {"ACTIVATE", "SUSPEND", "ROUTE_CALL", "ESIM_ACTIVATE"} else "LOW"
        if risk not in self._risk_rank or policy.max_risk not in self._risk_rank:
            raise CapabilityDeniedError("unknown risk classification")
        if self._risk_rank[risk] > self._risk_rank[policy.max_risk]:
            raise CapabilityDeniedError("requested operation exceeds policy risk ceiling")

        return Capability(
            capability_id=request.capability_id,
            principal=principal,
            operation=request.operation,
            resource=request.target,
            decision="ALLOW",
            policy_version=policy.version,
            risk=risk,
        )
