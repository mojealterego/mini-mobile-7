from __future__ import annotations

import threading
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


class ConcurrentIdempotencyReservationTest(unittest.TestCase):
    def test_two_assurance_cores_share_one_side_effect(self) -> None:
        store = InMemoryIdempotencyStore()
        repository = InMemorySubscriberRepository(
            {
                "7001": Subscriber(
                    subscriber_id="7001",
                    imsi="001010000000001",
                    ue_ip="10.20.0.11",
                    version=1,
                    status=SubscriberStatus.PROVISIONED,
                    secret_refs={"authentication": "env://MINI_MOBILE_7/7001"},
                    services={"ims": True, "data": True},
                )
            }
        )
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
        executions_lock = threading.Lock()
        start = threading.Barrier(2)

        def execute(_request: ExecutionRequest) -> bool:
            nonlocal executions
            with executions_lock:
                executions += 1
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

        cores = [
            AssuranceCore(repository, broker, execute, readback, lambda _r: (True, "ok"), store),
            AssuranceCore(repository, broker, execute, readback, lambda _r: (True, "ok"), store),
        ]
        request = ExecutionRequest(
            request_id="req-1",
            idempotency_key="concurrent-7001",
            capability_id="cap-req-1",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
        )
        results: list = []
        errors: list[BaseException] = []

        def worker(core: AssuranceCore) -> None:
            try:
                start.wait(timeout=2)
                results.append(core.execute(principal="test", request=request))
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(core,)) for core in cores]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)

        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.status == AssuranceStatus.VERIFIED for result in results))
        self.assertEqual(executions, 1)


if __name__ == "__main__":
    unittest.main()
