from __future__ import annotations

import unittest

from project_72.assurance_core.models import ExecutionRequest, Subscriber, SubscriberStatus
from project_72.assurance_core.store import InMemorySubscriberRepository
from adapters.open5gs.adapter import Open5GSAdapter


class FakeSecrets:
    def resolve(self, secret_ref: str) -> dict[str, str]:
        if secret_ref != "env://TEST_7001":
            raise AssertionError(f"unexpected secret_ref: {secret_ref}")
        return {"k": "external-k", "opc": "external-opc", "amf": "8000"}


class FakeCollection:
    def __init__(self) -> None:
        self.document: dict[str, object] | None = None

    def find_one(self, filter: dict[str, object]) -> dict[str, object] | None:
        if self.document is None:
            return None
        if filter.get("imsi") == self.document.get("imsi"):
            return self.document
        return None

    def replace_one(self, filter: dict[str, object], replacement: dict[str, object], *, upsert: bool) -> None:
        if not upsert:
            raise AssertionError("test adapter requires upsert")
        self.document = replacement


class Open5GSAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://TEST_7001"},
            services={"ims": True, "data": True, "pstn_outbound": False},
        )
        self.repository = InMemorySubscriberRepository({"7001": self.subscriber})
        self.collection = FakeCollection()
        self.adapter = Open5GSAdapter(self.repository, self.collection, FakeSecrets())
        self.request = ExecutionRequest(
            request_id="req-activate-7001-0002",
            idempotency_key="activate-7001-v1-adapter",
            capability_id="cap-req-activate-7001-0002",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )

    def test_activation_advances_canonical_version_and_projects(self) -> None:
        self.assertTrue(self.adapter.execute(self.request))
        current = self.repository.get("7001")
        self.assertEqual(current.version, 2)
        self.assertEqual(current.status, SubscriberStatus.ACTIVE)
        assert self.collection.document is not None
        self.assertEqual(self.collection.document["imsi"], "001010000000001")
        marker = self.collection.document["mm7_assurance"]
        assert isinstance(marker, dict)
        self.assertEqual(marker["canonical_version"], 2)

    def test_readback_confirms_projected_state(self) -> None:
        self.adapter.execute(self.request)
        result = self.adapter.readback("7001")
        self.assertEqual(result.observed_version, 2)
        self.assertEqual(result.state, "ACTIVE")
        self.assertTrue(result.fingerprint)

    def test_replay_is_idempotent(self) -> None:
        self.adapter.execute(self.request)
        first = self.collection.document
        self.adapter.execute(self.request)
        self.assertIs(self.collection.document, first)


if __name__ == "__main__":
    unittest.main()
