from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Protocol

from .models import AssuranceResult, AssuranceStatus, ExecutionRequest


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused for a different request."""


@dataclass(frozen=True, slots=True)
class IdempotencyFingerprint:
    key: str
    fingerprint: str


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

    def get(self, key: str) -> tuple[str, AssuranceResult] | None:
        """Return the stored fingerprint/result or None when the key is absent."""

    def put(self, key: str, fingerprint: str, result: AssuranceResult) -> None:
        """Atomically persist a new idempotency record."""


class MongoIdempotencyStore:
    """MongoDB-backed idempotency records for multi-process assurance runtimes."""

    def __init__(self, mongodb_uri: str, *, database: str = "mini_mobile_7") -> None:
        from pymongo import MongoClient

        self._client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self._collection = self._client[database]["assurance_idempotency"]
        self._collection.create_index("key", unique=True)

    def get(self, key: str) -> tuple[str, AssuranceResult] | None:
        document = self._collection.find_one({"key": key})
        if document is None:
            return None
        return str(document["fingerprint"]), _result_from_document(document["result"])

    def put(self, key: str, fingerprint: str, result: AssuranceResult) -> None:
        from pymongo.errors import DuplicateKeyError

        document = {
            "key": key,
            "fingerprint": fingerprint,
            "result": _result_to_document(result),
        }
        try:
            self._collection.insert_one(document)
        except DuplicateKeyError as exc:
            existing = self.get(key)
            if existing is None or existing[0] != fingerprint:
                raise IdempotencyConflictError(
                    f"idempotency key was already used for a different request: {key}"
                ) from exc


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
