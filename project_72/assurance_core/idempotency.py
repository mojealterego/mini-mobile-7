from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .models import ExecutionRequest


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
