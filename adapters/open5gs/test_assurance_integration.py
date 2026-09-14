from __future__ import annotations

import unittest

from adapters.open5gs.adapter import Open5GSAdapter
from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest, Subscriber, SubscriberStatus
from project_72.assurance_core.postconditions import activate_postcondition
from project_72.assurance_core.store import InMemorySubscriberRepository


class FakeSecrets:
    def resolve(self, secret_ref: str) -> dict[str, str]:
        return {"k": "external-k", "opc": "external-opc", "amf": "8000"}


class FakeCollection:
    def __init__(self) -> None:
        self.document: dict[str, object] | None = None

    def find_one(self, filter: dict[str, object]) -> dict[str, object] | None:
        if self.document is None:
            return None
        return self.document if filter.get("imsi") == self.document.get("imsi") else None

    def replace_one(self, filter: dict[str, object], replacement: dict[str, object], *, upsert: bool) -> None:
        if not upsert:
            raise AssertionError("projection must use upsert")
        self.document = replacement


def make_repository() -> InMemorySubscriberRepository:
    return InMemorySubscriberRepository({
        "7001": Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://TEST_7001"},
            services={"ims": True, "data": True, "pstn_outbound": False},
        )
    })


def make_request(version: int = 1, suffix: str = "") -> ExecutionRequest:
    request_id = f"req-activate-7001-open5gs{suffix}"
    return ExecutionRequest(
        request_id=request_id,
        idempotency_key=f"activate-7001-open5gs-v{version}{suffix}",
        capability_id=f"cap-{request_id}",
        operation="ACTIVATE",
        target="7001",
        expected_version=version,
    )


class Open5GSAssuranceIntegrationTest(unittest.TestCase):
    def test_activate_7001_reaches_verified_only_after_open5gs_readback(self) -> None:
        repository = make_repository()
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        broker = CapabilityBroker({
            "ACTIVATE": Policy(
                version="policy-1",
                allowed_operations=frozenset({"ACTIVATE"}),
                allowed_principals=frozenset({"assurance-service"}),
                max_risk="MEDIUM",
            )
        })
        core = AssuranceCore(repository, broker, adapter.execute, adapter.readback, activate_postcondition)

        result = core.execute(principal="assurance-service", request=make_request())
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)
        self.assertEqual(result.observed_version, 2)
        self.assertEqual(repository.get("7001").status, SubscriberStatus.ACTIVE)

    def test_modified_projection_is_reported_as_drift_by_readback(self) -> None:
        repository = make_repository()
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        adapter.execute(make_request())
        assert collection.document is not None
        collection.document["ue"] = {"ipv4": "10.20.0.99"}

        readback = adapter.readback("7001")
        self.assertEqual(readback.observed_version, 2)
        self.assertEqual(readback.state, "MISMATCH")

        broker = CapabilityBroker({
            "ACTIVATE": Policy(
                version="policy-1",
                allowed_operations=frozenset({"ACTIVATE"}),
                allowed_principals=frozenset({"assurance-service"}),
                max_risk="MEDIUM",
            )
        })
        core = AssuranceCore(repository, broker, lambda _: True, adapter.readback, activate_postcondition)
        result = core.execute(principal="assurance-service", request=make_request(1, "-drift"))
        self.assertEqual(result.status, AssuranceStatus.DRIFT)


if __name__ == "__main__":
    unittest.main()
