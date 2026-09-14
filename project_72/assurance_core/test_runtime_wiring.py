from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import TestCase


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "project-72-provision-seven.py"


class RuntimeProvisionerImportTest(TestCase):
    def test_runtime_provisioner_exposes_durable_store_dependency(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("MongoIdempotencyStore", source)
        self.assertIn("idempotency_store", source)
        self.assertIn("MM7_IDEMPOTENCY_DB_URI", source)

    def test_runtime_provisioner_has_no_secret_literals(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        forbidden = ("OPC=", "OPC:", "password=", "secret=")
        for token in forbidden:
            self.assertNotIn(token.lower(), source.lower())
