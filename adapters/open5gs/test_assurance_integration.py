from __future__ import annotations

import unittest

from adapters.open5gs.adapter import Open5GSAdapter
from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
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


class SevenSubscriberCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}

    def find_one(self, filter: dict[str, object]) -> dict[str, object] | None:
        imsi = filter.get("imsi")
        if not isinstance(imsi, str):
            return None
        return self.documents.get(imsi)

    def replace_one(self, filter: dict[str, object], replacement: dict[str, object], *, upsert: bool) -> None:
        if not upsert:
            raise AssertionError("projection must use upsert")
        imsi = filter.get("imsi")
        if not isinstance(imsi, str):
            raise AssertionError("projection filter must contain IMSI")
        self.documents[imsi] = replacement


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


def make_broker() -> CapabilityBroker:
    return CapabilityBroker({
        "ACTIVATE": Policy(
            version="policy-1",
            allowed_operations=frozenset({"ACTIVATE"}),
            allowed_principals=frozenset({"assurance-service"}),
            max_risk="MEDIUM",
        )
    })


class Open5GSAssuranceIntegrationTest(unittest.TestCase):
    def test_activate_7001_reaches_verified_only_after_open5gs_readback(self) -> None:
        repository = make_repository()
        collection = FakeCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())
        core = AssuranceCore(repository, make_broker(), adapter.execute, adapter.readback, activate_postcondition)

        result = core.execute(principal="assurance-service", request=make_request())
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)
        self.assertEqual(result.observed_version, 2)
        self.assertEqual(repository.get("7001").status, SubscriberStatus.ACTIVE)

    def test_all_seven_catalog_subscribers_project_and_readback_verified(self) -> None:
        catalog = build_seven_subscriber_catalog()
        repository = InMemorySubscriberRepository({
            subscriber.subscriber_id: subscriber for subscriber in catalog
        })
        collection = SevenSubscriberCollection()
        adapter = Open5GSAdapter(repository, collection, FakeSecrets())

        for subscriber in catalog:
            request_id = f"req-activate-{subscriber.subscriber_id}-open5gs-seven"
            request = ExecutionRequest(
                request_id=request_id,
                idempotency_key=f"activate-{subscriber.subscriber_id}-open5gs-seven-v1",
                capability_id=f"cap-{request_id}",
                operation="ACTIVATE",
                target=subscriber.subscriber_id,
                expected_version=1,
            )
            result = AssuranceCore(
                repository,
                make_broker(),
                adapter.execute,
                adapter.readback,
                activate_postcondition,
            ).execute(principal="assurance-service", request=request)
            self.assertEqual(result.status, AssuranceStatus.VERIFIED, subscriber.subscriber_id)
            self.assertEqual(result.observed_version, 2, subscriber.subscriber_id)
            self.assertEqual(repository.get(subscriber.subscriber_id).status, SubscriberStatus.ACTIVE)

        self.assertEqual(len(collection.documents), 7)
        for subscriber in catalog:
            document = collection.documents[subscriber.imsi]
            self.assertEqual(document["imsi"], subscriber.imsi)
            marker = document["mm7_assurance"]
            self.assertEqual(marker["subscriber_id"], subscriber.subscriber_id)
            self.assertEqual(marker["canonical_version"], 2)
            self.assertEqual(marker["status"], "ACTIVE")
            slices = document["slice"]
            self.assertIsInstance(slices, list)
            sessions = slices[0]["session"]
            internet = next(item for item in sessions if item["name"] == "internet")
            self.assertEqual(internet["ue"]["ipv4"], subscriber.ue_ip)

    def test_modified_projection_is_drift_not_verified(self) -> None:
        projection_repository = make_repository()
        collection = FakeCollection()
        projection_adapter = Open5GSAdapter(projection_repository, collection, FakeSecrets())
        projection_adapter.execute(make_request())
        assert collection.document is not None

        slices = collection.document["slice"]
        assert isinstance(slices, list)
        sessions = slices[0]["session"]
        assert isinstance(sessions, list)
        internet = next(item for item in sessions if item["name"] == "internet")
        assert isinstance(internet["ue"], dict)
        internet["ue"]["ipv4"] = "10.20.0.99"

        canonical_repository = make_repository()
        readback_adapter = Open5GSAdapter(canonical_repository, collection, FakeSecrets())
        core = AssuranceCore(
            canonical_repository,
            make_broker(),
            lambda _: True,
            readback_adapter.readback,
            activate_postcondition,
        )
        result = core.execute(
            principal="assurance-service",
            request=make_request(1, "-drift"),
        )

        self.assertEqual(result.status, AssuranceStatus.DRIFT)
        self.assertEqual(result.observed_version, 2)

    def test_malformed_projection_marker_is_drift_not_exception(self) -> None:
        projection_repository = make_repository()
        collection = FakeCollection()
        projection_adapter = Open5GSAdapter(projection_repository, collection, FakeSecrets())
        projection_adapter.execute(make_request())
        assert collection.document is not None
        marker = collection.document["mm7_assurance"]
        assert isinstance(marker, dict)
        marker["canonical_version"] = "not-an-integer"

        readback_adapter = Open5GSAdapter(projection_repository, collection, FakeSecrets())
        readback = readback_adapter.readback("7001")

        self.assertEqual(readback.observed_version, 0)
        self.assertEqual(readback.state, "MISMATCH")


if __name__ == "__main__":
    unittest.main()
