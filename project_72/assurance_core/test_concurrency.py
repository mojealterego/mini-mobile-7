from __future__ import annotations

import threading
import unittest

from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.lifecycle import transition
from project_72.assurance_core.models import Subscriber, SubscriberStatus
from project_72.assurance_core.store import InMemorySubscriberRepository, StoreConflictError


class OptimisticConcurrencyTest(unittest.TestCase):
    def test_two_writers_with_same_expected_version_have_one_winner(self) -> None:
        initial = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "env://MINI_MOBILE_7/7001"},
            services={"ims": True, "data": True},
        )
        repository = InMemorySubscriberRepository({"7001": initial})
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def writer() -> None:
            current = repository.get("7001")
            target = transition(current, "ACTIVATE")
            barrier.wait()
            try:
                repository.put(target, expected_version=1)
                outcome = "WIN"
            except StoreConflictError:
                outcome = "CONFLICT"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=writer) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(outcomes), ["CONFLICT", "WIN"])
        final = repository.get("7001")
        self.assertEqual(final.version, 2)
        self.assertEqual(final.status, SubscriberStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
