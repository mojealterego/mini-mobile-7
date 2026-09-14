from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from .broker import CapabilityBroker, CapabilityDeniedError
from .idempotency import fingerprint_request
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
    _request_fingerprints: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def execute(self, *, principal: str, request: ExecutionRequest) -> AssuranceResult:
        with self._lock:
            fingerprint = fingerprint_request(request)
            previous = self._request_fingerprints.get(request.idempotency_key)
            if previous is not None and previous != fingerprint:
                return AssuranceResult(
                    request.request_id,
                    request.target,
                    AssuranceStatus.CONFLICT,
                    False,
                    False,
                    False,
                    False,
                    False,
                    "idempotency key was already used for a different request",
                )

            cached = self._results.get(request.idempotency_key)
            if cached is not None:
                return cached
            self._request_fingerprints[request.idempotency_key] = fingerprint

            try:
                subscriber = self.repository.get(request.target)
            except KeyError:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.FAILED,
                        False, False, False, False, False, "canonical subscriber not found"
                    ),
                )

            try:
                capability = self.broker.authorize(
                    principal=principal, request=request, subscriber=subscriber
                )
            except CapabilityDeniedError as exc:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.DENIED,
                        False, False, False, False, False, str(exc)
                    ),
                )

            if capability.decision != "ALLOW":
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.DENIED,
                        True, False, False, False, False, "capability decision is not ALLOW"
                    ),
                )

            try:
                executed = self.executor(request)
            except StoreConflictError as exc:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.CONFLICT,
                        True, True, False, False, False, str(exc), subscriber.version
                    ),
                )
            except Exception as exc:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.FAILED,
                        True, True, False, False, False, f"execution error: {exc}"
                    ),
                )

            if not executed:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                        True, True, False, False, False,
                        "executor did not confirm completion"
                    ),
                )

            try:
                readback = self.readback_provider(request.target)
            except Exception as exc:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                        True, True, True, False, False,
                        f"authoritative readback failed: {exc}"
                    ),
                )

            if readback.observed_version <= request.expected_version:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.STALE,
                        True, True, True, False, False,
                        "authoritative readback did not advance beyond expected_version",
                        readback.observed_version,
                    ),
                )

            if readback.state == "MISMATCH":
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.DRIFT,
                        True, True, True, True, False,
                        "authoritative Open5GS state differs from canonical postcondition",
                        readback.observed_version,
                    ),
                )

            try:
                postcondition_ok, reason = self.postcondition(readback)
            except Exception as exc:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                        True, True, True, True, False,
                        f"postcondition evaluation failed: {exc}",
                        readback.observed_version,
                    ),
                )

            if not postcondition_ok:
                return self._cache(
                    request,
                    AssuranceResult(
                        request.request_id, request.target, AssuranceStatus.UNVERIFIED,
                        True, True, True, True, False, reason,
                        readback.observed_version
                    ),
                )

            return self._cache(
                request,
                AssuranceResult(
                    request.request_id, request.target, AssuranceStatus.VERIFIED,
                    True, True, True, True, True, "all assurance gates passed",
                    readback.observed_version,
                ),
            )

    def _cache(self, request: ExecutionRequest, result: AssuranceResult) -> AssuranceResult:
        self._results[request.idempotency_key] = result
        return result
