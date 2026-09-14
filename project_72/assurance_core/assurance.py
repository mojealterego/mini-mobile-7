from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from .broker import CapabilityBroker, CapabilityDeniedError
from .models import AssuranceResult, AssuranceStatus, AuthoritativeReadback, ExecutionRequest
from .store import StoreConflictError, SubscriberRepository

Executor = Callable[[ExecutionRequest], bool]
ReadbackProvider = Callable[[str], AuthoritativeReadback]
Postcondition = Callable[[AuthoritativeReadback], tuple[bool, str]]


@dataclass(slots=True)
class AssuranceCore:
    repository: SubscriberRepository
    broker: CapabilityBroker
    executor: Executor
    readback_provider: ReadbackProvider
    postcondition: Postcondition
    _results: dict[str, AssuranceResult] = field(default_factory=dict, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def execute(self, *, principal: str, request: ExecutionRequest) -> AssuranceResult:
        with self._lock:
            cached = self._results.get(request.idempotency_key)
            if cached is not None:
                return cached

            try:
                subscriber = self.repository.get(request.target)
            except KeyError:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.FAILED,
                    False, False, False, False, False, "canonical subscriber not found"
                )
                self._results[request.idempotency_key] = result
                return result

            try:
                capability = self.broker.authorize(
                    principal=principal, request=request, subscriber=subscriber
                )
            except CapabilityDeniedError as exc:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.DENIED,
                    False, False, False, False, False, str(exc)
                )
                self._results[request.idempotency_key] = result
                return result

            if capability.decision != "ALLOW":
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.DENIED,
                    True, False, False, False, False, "capability decision is not ALLOW"
                )
                self._results[request.idempotency_key] = result
                return result

            try:
                executed = self.executor(request)
            except StoreConflictError as exc:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.CONFLICT,
                    True, True, False, False, False, str(exc), subscriber.version
                )
                self._results[request.idempotency_key] = result
                return result
            except Exception as exc:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.FAILED,
                    True, True, False, False, False, f"execution error: {exc}"
                )
                self._results[request.idempotency_key] = result
                return result

            if not executed:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                    True, True, False, False, False,
                    "executor did not confirm completion"
                )
                self._results[request.idempotency_key] = result
                return result

            readback = self.readback_provider(request.target)
            if readback.observed_version <= request.expected_version:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.STALE,
                    True, True, True, False, False,
                    "authoritative readback did not advance beyond expected_version",
                    readback.observed_version,
                )
                self._results[request.idempotency_key] = result
                return result

            postcondition_ok, reason = self.postcondition(readback)
            if not postcondition_ok:
                result = AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                    True, True, True, True, False, reason,
                    readback.observed_version
                )
                self._results[request.idempotency_key] = result
                return result

            result = AssuranceResult(
                request.request_id, request.target, AssuranceStatus.VERIFIED,
                True, True, True, True, True, "all assurance gates passed",
                readback.observed_version,
            )
            self._results[request.idempotency_key] = result
            return result
