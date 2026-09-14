from __future__ import annotations

import unittest

from adapters.open5gs.adapter import Open5GSAdapter
from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from project_72.assurance_core.lifecycle_postconditions import lifecycle_postcondition
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest
from project_72.assurance_core.store import InMemorySubscriberRepository


class FakeSecrets:
    def resolve(self, secret_ref: str) -> dict[str, str]:
        return {"k": "external-k", "opc": "external-opc", "amf": "8000"}


class FakeCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}

    def find_one(self, filter: dict[str, object]) -> dict[str, object] | None:
        imsi = filter.get("imsi")
        document = self.documents.get(str(imsi))
        return document

    def replace_one(self, filter: dict[str, object], replacement: dict[str, object], *, upsert: bool) -> None:
        if not upsert:
            raise AssertionError("lifecycle test requires upsert")
        self.documents[str(filter["imsi"])] = replacement


def request(operation: str, target: str, version: int) -> ExecutionRequest:
    request_id = f"req-{operation.lower()}-{target}-v{version}"
    return ExecutionRequest(
        request_id=request_id,
        idempotency_key=f"idem-{request_id}",
        capability_id=f"cap-{request_id}",
        operation=operation,
        target=target,
        expected_version=version,
    )


class SubscriberLifecycleTest(unittest.TestCase):
    def test_catalog_contains_all_seven_subscribers(self) -> None:
        catalog = build_seven_subscriber_catalog()
        self.assertEqual(len(catalog), 7)
        self.assertEqual([item.subscriber_id for item in catalog], [f"700{i}" for i in range(1, 8)])
        self.assertEqual([item.ue_ip for item in catalog], [f"10.20.0.{10 + i}" for i in range(1, 8)])

    def test_7001_full_lifecycle_is_verified_at_each_gate(self) -> None:
        catalog = build_seven_subscriber_catalog()
        repository = InMemorySubscriberRepository({item.subscriber_id: item for item in catalog})
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        broker = CapabilityBroker({
            operation: Policy(
                version="policy-lifecycle-1",
                allowed_operations=frozenset({operation}),
                allowed_principals=frozenset({"assurance-service"}),
                max_risk="MEDIUM",
            )
            for operation in ("ACTIVATE", "SUSPEND", "DEACTIVATE")
        })

        for operation, version, expected_state in (
            ("ACTIVATE", 1, "ACTIVE"),
            ("SUSPEND", 2, "SUSPENDED"),
            ("DEACTIVATE", 3, "RETIRED"),
        ):
            core = AssuranceCore(
                repository,
                broker,
                adapter.execute,
                adapter.readback,
                lifecycle_postcondition(expected_state),
            )
            result = core.execute(
                principal="assurance-service",
                request=request(operation, "7001", version),
            )
            self.assertEqual(result.status, AssuranceStatus.VERIFIED)
            self.assertEqual(result.observed_version, version + 1)

        self.assertEqual(repository.get("7001").version, 4)
        self.assertEqual(repository.get("7001").status.value, "RETIRED")

    def test_wrong_expected_version_is_denied_before_execution(self) -> None:
        catalog = build_seven_subscriber_catalog()
        repository = InMemorySubscriberRepository({item.subscriber_id: item for item in catalog})
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        broker = CapabilityBroker({
            "ACTIVATE": Policy(
                version="policy-1",
                allowed_operations=frozenset({"ACTIVATE"}),
                allowed_principals=frozenset({"assurance-service"}),
            )
        })
        core = AssuranceCore(
            repository,
            broker,
            adapter.execute,
            adapter.readback,
            lifecycle_postcondition("ACTIVE"),
        )
        result = core.execute(
            principal="assurance-service",
            request=request("ACTIVATE", "7001", 99),
        )
        self.assertEqual(result.status, AssuranceStatus.DENIED)
        self.assertEqual(repository.get("7001").version, 1)


if __name__ == "__main__":
    unittest.main()
