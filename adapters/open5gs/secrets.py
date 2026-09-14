from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Protocol


class SecretResolutionError(RuntimeError):
    """Raised when an external authentication secret cannot be resolved."""


class SecretResolver(Protocol):
    def resolve(self, secret_ref: str) -> Mapping[str, str]:
        """Resolve a reference without persisting the secret in the repository."""


@dataclass(frozen=True, slots=True)
class EnvironmentSecretResolver:
    """Resolve a secret reference from one environment variable.

    The variable contains a JSON object, for example:
    {"k":"...","opc":"...","amf":"8000"}.
    The JSON is supplied by the deployment secret manager, never by Git.
    """

    prefix: str = "MM7_SECRET_"

    def resolve(self, secret_ref: str) -> Mapping[str, str]:
        import json

        if not secret_ref or not secret_ref.startswith("env://"):
            raise SecretResolutionError(
                "unsupported secret_ref; expected an external env:// reference"
            )
        variable = f"{self.prefix}{secret_ref.removeprefix('env://')}"
        raw = os.environ.get(variable)
        if not raw:
            raise SecretResolutionError(f"secret reference is not available: {secret_ref}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SecretResolutionError(f"secret reference is not valid JSON: {secret_ref}") from exc
        if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise SecretResolutionError("resolved authentication secret must be a string map")
        required = {"k", "opc", "amf"}
        missing = required - set(value)
        if missing:
            raise SecretResolutionError(
                f"resolved authentication secret is missing required fields: {sorted(missing)}"
            )
        return value
