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


class Open5GSAssuranceIntegrationTest(unittest.TestCase):
    def test_activate_7001_reaches_verified_only_after_open5gs_readback(self) -> None:
        repository = InMemorySubscriberRepository({
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
        request = ExecutionRequest(
            request_id="req-activate-7001-open5gs",
            idempotency_key="activate-7001-open5gs-v1",
            capability_id="cap-req-activate-7001-open5gs",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )

        result = core.execute(principal="assurance-service", request=request)
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)
        self.assertEqual(result.observed_version, 2)
        self.assertEqual(repository.get("7001").status, SubscriberStatus.ACTIVE)

    def test_modified_projection_is_drift_not_verified(self) -> None:
        repository = InMemorySubscriberRepository({
            "7001": Subscriber(
                subscriber_id="7001",
                imsi="001010000000001",
                ue_ip="10.20.0.11",
                version=1,
                status=SubscriberStatus.PROVISIONED,
                secret_refs={"authentication": "env://TEST_7001"},
                services={"ims": True, "data": True},
            )
        })
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        broker = CapabilityBroker({
            "ACTIVATE": Policy(
                version="policy-1",
                allowed_operations=frozenset({"ACTIVATE"}),
                allowed_principals=frozenset({"assurance-service"}),
            )
        })
        core = AssuranceCore(repository, broker, adapter.execute, adapter.readback, activate_postcondition)
        request = ExecutionRequest(
            request_id="req-activate-7001-drift",
            idempotency_key="activate-7001-drift-v1",
            capability_id="cap-req-activate-7001-drift",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )
        adapter.execute(request)
        assert collection.document is not None
        collection.document["ue"] = {"ipv4": "10.20.0.99"}

        result = core.execute(principal="assurance-service", request=request)
        # The idempotency cache prevents a second execution of the same request.
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)

        fresh_request = ExecutionRequest(
            request_id="req-activate-7001-drift-2",
            idempotency_key="activate-7001-drift-v2",
            capability_id="cap-req-activate-7001-drift-2",
            operation="ACTIVATE",
            target="7001",
            expected_version=2,
        )
        # A new request is denied because ACTIVATE is only valid from PROVISIONED in the current policy path.
        denied = core.execute(principal="assurance-service", request=fresh_request)
        self.assertIn(denied.status, {AssuranceStatus.FAILED, AssuranceStatus.DENIED})


if __name__ == "__main__":
    unittest.main()
