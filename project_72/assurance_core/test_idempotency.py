from __future__ import annotations

import unittest

from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.idempotency import InMemoryIdempotencyStore
from project_72.assurance_core.models import (
    AssuranceStatus,
    AuthoritativeReadback,
    ExecutionRequest,
    Subscriber,
    SubscriberStatus,
)
from project_72.assurance_core.store import InMemorySubscriberRepository


class IdempotencyBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://MINI_MOBILE_7/7001"},
            services={"ims": True, "data": True},
        )
        self.repository = InMemorySubscriberRepository({"7001": subscriber})
        self.executions = 0
        broker = CapabilityBroker(
            {
                "ACTIVATE": Policy(
                    version="test-1",
                    allowed_operations=frozenset({"ACTIVATE"}),
                    allowed_principals=frozenset({"test"}),
                    max_risk="MEDIUM",
                )
            }
        )

        def execute(_request: ExecutionRequest) -> bool:
            self.executions += 1
            return True

        def readback(target: str) -> AuthoritativeReadback:
            return AuthoritativeReadback(
                request_id="readback",
                source="test",
                target=target,
                observed_version=2,
                state="ACTIVE",
                fingerprint="test",
                details={"marker": {"status": "ACTIVE"}, "services": {"data": True}},
            )

        self.core = AssuranceCore(
            self.repository,
            broker,
            execute,
            readback,
            lambda _readback: (True, "ok"),
        )

    def request(self, *, request_id: str, target: str = "7001") -> ExecutionRequest:
        return ExecutionRequest(
            request_id=request_id,
            idempotency_key="activate-7001",
            capability_id=f"cap-{request_id}",
            operation="ACTIVATE",
            target=target,
            expected_version=1,
        )

    def test_identical_replay_returns_cached_result_without_execution(self) -> None:
        first = self.core.execute(principal="test", request=self.request(request_id="req-1"))
        second = self.core.execute(principal="test", request=self.request(request_id="req-1"))
        self.assertIs(first, second)
        self.assertEqual(first.status, AssuranceStatus.VERIFIED)
        self.assertEqual(self.executions, 1)

    def test_same_key_with_different_request_is_conflict(self) -> None:
        first = self.core.execute(principal="test", request=self.request(request_id="req-1"))
        second = self.core.execute(principal="test", request=self.request(request_id="req-2"))
        self.assertEqual(first.status, AssuranceStatus.VERIFIED)
        self.assertEqual(second.status, AssuranceStatus.CONFLICT)
        self.assertEqual(self.executions, 1)


class DurableReservationTest(unittest.TestCase):
    def test_second_core_cannot_execute_reserved_key(self) -> None:
        store = InMemoryIdempotencyStore()
        subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://MINI_MOBILE_7/7001"},
            services={"ims": True, "data": True},
        )
        repository = InMemorySubscriberRepository({"7001": subscriber})
        broker = CapabilityBroker(
            {
                "ACTIVATE": Policy(
                    version="test-1",
                    allowed_operations=frozenset({"ACTIVATE"}),
                    allowed_principals=frozenset({"test"}),
                    max_risk="MEDIUM",
                )
            }
        )
        executions = 0

        def execute(_request: ExecutionRequest) -> bool:
            nonlocal executions
            executions += 1
            return True

        readback = lambda target: AuthoritativeReadback(
            request_id="readback",
            source="test",
            target=target,
            observed_version=2,
            state="ACTIVE",
            fingerprint="test",
            details={"marker": {"status": "ACTIVE"}, "services": {"data": True}},
        )
        core_one = AssuranceCore(
            repository, broker, execute, readback, lambda _readback: (True, "ok"), store
        )
        core_two = AssuranceCore(
            repository, broker, execute, readback, lambda _readback: (True, "ok"), store
        )
        request = ExecutionRequest(
            request_id="req-1",
            idempotency_key="durable-7001",
            capability_id="cap-req-1",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )

        first = core_one.execute(principal="test", request=request)
        second = core_two.execute(principal="test", request=request)

        self.assertEqual(first.status, AssuranceStatus.VERIFIED)
        self.assertEqual(second.status, AssuranceStatus.VERIFIED)
        self.assertEqual(executions, 1)

    def test_reserved_key_without_result_fails_closed(self) -> None:
        store = InMemoryIdempotencyStore()
        store.reserve("durable-7001", "fingerprint")
        subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://MINI_MOBILE_7/7001"},
            services={"ims": True, "data": True},
        )
        repository = InMemorySubscriberRepository({"7001": subscriber})
        broker = CapabilityBroker(
            {
                "ACTIVATE": Policy(
                    version="test-1",
                    allowed_operations=frozenset({"ACTIVATE"}),
                    allowed_principals=frozenset({"test"}),
                    max_risk="MEDIUM",
                )
            }
        )
        core = AssuranceCore(
            repository,
            broker,
            lambda _request: True,
            lambda target: AuthoritativeReadback(
                request_id="readback",
                source="test",
                target=target,
                observed_version=2,
                state="ACTIVE",
                fingerprint="test",
                details={"marker": {"status": "ACTIVE"}, "services": {"data": True}},
            ),
            lambda _readback: (True, "ok"),
            store,
        )
        request = ExecutionRequest(
            request_id="req-1",
            idempotency_key="durable-7001",
            capability_id="cap-req-1",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )

        result = core.execute(principal="test", request=request)

        self.assertEqual(result.status, AssuranceStatus.CONFLICT)


if __name__ == "__main__":
    unittest.main()
