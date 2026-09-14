from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Protocol

from .models import AssuranceResult, AssuranceStatus, ExecutionRequest


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused for a different request."""


class IdempotencyInProgressError(RuntimeError):
    """Raised when another execution owns an idempotency key."""


@dataclass(frozen=True, slots=True)
class IdempotencyFingerprint:
    key: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    key: str
    fingerprint: str
    result: AssuranceResult | None


def fingerprint_request(request: ExecutionRequest) -> str:
    payload: dict[str, Any] = {
        "request_id": request.request_id,
        "idempotency_key": request.idempotency_key,
        "capability_id": request.capability_id,
        "operation": request.operation,
        "target": request.target,
        "expected_version": request.expected_version,
        "parameters": dict(request.parameters),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore(Protocol):
    """Durable interface for cross-process idempotency state."""

    def reserve(self, key: str, fingerprint: str) -> IdempotencyRecord | None:
        """Atomically reserve a new key or return the existing record."""

    def put(self, key: str, fingerprint: str, result: AssuranceResult) -> None:
        """Persist the terminal result for an existing reservation."""


class InMemoryIdempotencyStore:
    """Thread-safe reference implementation for deterministic tests."""

    def __init__(self) -> None:
        from threading import RLock

        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = RLock()

    def reserve(self, key: str, fingerprint: str) -> IdempotencyRecord | None:
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        f"idempotency key was already used for a different request: {key}"
                    )
                return existing
            self._records[key] = IdempotencyRecord(key, fingerprint, None)
            return None

    def put(self, key: str, fingerprint: str, result: AssuranceResult) -> None:
        with self._lock:
            existing = self._records.get(key)
            if existing is None:
                raise IdempotencyInProgressError(
                    f"cannot finalize an unreserved idempotency key: {key}"
                )
            if existing.fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    f"idempotency key was already used for a different request: {key}"
                )
            self._records[key] = IdempotencyRecord(key, fingerprint, result)


class MongoIdempotencyStore:
    """MongoDB-backed idempotency records for multi-process assurance runtimes."""

    def __init__(self, mongodb_uri: str, *, database: str = "mini_mobile_7") -> None:
        from pymongo import MongoClient

        self._client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self._collection = self._client[database]["assurance_idempotency"]
        self._collection.create_index("key", unique=True)

    def reserve(self, key: str, fingerprint: str) -> IdempotencyRecord | None:
        from pymongo.errors import DuplicateKeyError

        try:
            self._collection.insert_one({"key": key, "fingerprint": fingerprint, "result": None})
            return None
        except DuplicateKeyError as exc:
            existing = self._collection.find_one({"key": key})
            if existing is None:
                raise IdempotencyInProgressError(
                    f"idempotency reservation disappeared during conflict handling: {key}"
                ) from exc
            existing_fingerprint = str(existing["fingerprint"])
            if existing_fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    f"idempotency key was already used for a different request: {key}"
                ) from exc
            result_document = existing.get("result")
            return IdempotencyRecord(
                key=key,
                fingerprint=existing_fingerprint,
                result=(
                    _result_from_document(result_document)
                    if result_document is not None
                    else None
                ),
            )

    def put(self, key: str, fingerprint: str, result: AssuranceResult) -> None:
        from pymongo import ReturnDocument

        document = self._collection.find_one_and_update(
            {"key": key, "fingerprint": fingerprint, "result": None},
            {"$set": {"result": _result_to_document(result)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            existing = self._collection.find_one({"key": key})
            if existing is None:
                raise IdempotencyInProgressError(
                    f"cannot finalize an unreserved idempotency key: {key}"
                )
            if str(existing["fingerprint"]) != fingerprint:
                raise IdempotencyConflictError(
                    f"idempotency key was already used for a different request: {key}"
                )
            if existing.get("result") is None:
                raise IdempotencyInProgressError(
                    f"idempotency key is reserved by another execution: {key}"
                )


def _result_to_document(result: AssuranceResult) -> dict[str, Any]:
    return {
        "request_id": result.request_id,
        "target": result.target,
        "status": result.status.value,
        "authorization": result.authorization,
        "policy": result.policy,
        "execution": result.execution,
        "readback": result.readback,
        "postcondition": result.postcondition,
        "reason": result.reason,
        "observed_version": result.observed_version,
    }


def _result_from_document(document: dict[str, Any]) -> AssuranceResult:
    return AssuranceResult(
        request_id=str(document["request_id"]),
        target=str(document["target"]),
        status=AssuranceStatus(str(document["status"])),
        authorization=bool(document["authorization"]),
        policy=bool(document["policy"]),
        execution=bool(document["execution"]),
        readback=bool(document["readback"]),
        postcondition=bool(document["postcondition"]),
        reason=str(document["reason"]),
        observed_version=(
            int(document["observed_version"])
            if document.get("observed_version") is not None
            else None
        ),
    )
