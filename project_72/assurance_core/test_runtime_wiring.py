from __future__ import annotations

from pathlib import Path
from unittest import TestCase


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "project-72-provision-seven.py"


class RuntimeProvisionerWiringTest(TestCase):
    def test_runtime_provisioner_uses_durable_store(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("MongoIdempotencyStore", source)
        self.assertIn("idempotency_store=durable_idempotency", source)
        self.assertIn("MM7_IDEMPOTENCY_DB_URI", source)

    def test_runtime_execute_fails_closed_without_idempotency_uri(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('if not args.idempotency_mongodb_uri:', source)
        self.assertIn('return 2', source)

    def test_runtime_provisioner_has_no_secret_literals(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for token in ("opc=", "opc:", "password=", "secret="):
            self.assertNotIn(token, source.lower())
