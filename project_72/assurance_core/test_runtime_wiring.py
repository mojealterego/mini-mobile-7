from __future__ import annotations

from pathlib import Path
from unittest import TestCase


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "project-72-provision-seven.py"


class RuntimeProvisionerWiringTest(TestCase):
    def _source(self) -> str:
        return SCRIPT.read_text(encoding="utf-8")

    def test_runtime_provisioner_uses_durable_store(self) -> None:
        source = self._source()
        self.assertIn("MongoIdempotencyStore", source)
        self.assertIn("idempotency_store=durable_idempotency", source)
        self.assertIn("MM7_IDEMPOTENCY_DB_URI", source)

    def test_runtime_execute_fails_closed_without_idempotency_uri(self) -> None:
        source = self._source()
        self.assertIn('if not args.idempotency_mongodb_uri:', source)
        self.assertIn('return 2', source)

    def test_runtime_execute_requires_preflight(self) -> None:
        source = self._source()
        self.assertIn("def run_preflight() -> bool:", source)
        self.assertIn("PREFLIGHT_SCRIPT", source)
        self.assertIn('env["MM7_SKIP_SECRET_PREFLIGHT"] = "0"', source)
        self.assertIn("if not run_preflight():", source)
        self.assertIn("no provisioning mutation permitted", source)

    def test_runtime_provisioner_has_no_secret_literals(self) -> None:
        source = self._source()
        for token in ("opc=", "opc:", "password=", "secret="):
            self.assertNotIn(token, source.lower())
