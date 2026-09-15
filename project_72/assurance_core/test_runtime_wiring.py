from __future__ import annotations

from pathlib import Path
from unittest import TestCase


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "project-72-provision-seven.py"
PREFLIGHT = Path(__file__).resolve().parents[2] / "scripts" / "project-72-preflight.sh"


class RuntimeProvisionerWiringTest(TestCase):
    def _source(self) -> str:
        return SCRIPT.read_text(encoding="utf-8")

    def _preflight_source(self) -> str:
        return PREFLIGHT.read_text(encoding="utf-8")

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
        self.assertIn("def run_preflight(mongodb_uri: str, idempotency_uri: str) -> bool:", source)
        self.assertIn("PREFLIGHT_SCRIPT", source)
        self.assertIn('env["MM7_MONGODB_URI"] = mongodb_uri', source)
        self.assertIn('env["MM7_IDEMPOTENCY_DB_URI"] = idempotency_uri', source)
        self.assertIn('env["MM7_SKIP_SECRET_PREFLIGHT"] = "0"', source)
        self.assertIn("if not run_preflight(mongodb_uri, idempotency_uri):", source)
        self.assertIn("no provisioning mutation permitted", source)

    def test_runtime_preflight_uses_same_databases_as_execution(self) -> None:
        source = self._source()
        self.assertIn("def provision_execute(mongodb_uri: str, idempotency_uri: str, bootstrap_canonical: bool) -> int:", source)
        self.assertIn("if not run_preflight(mongodb_uri, idempotency_uri):", source)
        self.assertIn('env["MM7_MONGODB_URI"] = mongodb_uri', source)
        self.assertIn('env["MM7_IDEMPOTENCY_DB_URI"] = idempotency_uri', source)

    def test_dry_run_is_before_runtime_dependencies_and_mutation(self) -> None:
        source = self._source()
        dry_run = source.index('if not args.execute:')
        mutation_gate = source.index('return provision_execute(', dry_run)
        self.assertLess(dry_run, mutation_gate)
        self.assertIn('print("DRY-RUN: no MongoDB/Open5GS mutation performed")', source)
        self.assertNotIn('make_core(args.mongodb_uri', source)
        self.assertNotIn('make_core(', source[dry_run:dry_run + 1_000])

    def test_active_readback_uses_subscriber_id(self) -> None:
        source = self._source()
        self.assertIn("adapter.readback(current.subscriber_id)", source)
        self.assertNotIn("adapter.readback(current)\n", source)

    def test_preflight_validates_durable_idempotency_database(self) -> None:
        source = self._preflight_source()
        self.assertIn('MM7_IDEMPOTENCY_DB_URI', source)
        self.assertIn('durable idempotency MongoDB reachable', source)
        self.assertIn('durable idempotency MongoDB is not reachable', source)
        self.assertIn("MM7_IDEMPOTENCY_DB_URI is required for runtime execution", source)

    def test_runtime_provisioner_has_no_secret_literals(self) -> None:
        source = self._source()
        for token in ("opc=", "opc:", "password=", "secret="):
            self.assertNotIn(token, source.lower())
