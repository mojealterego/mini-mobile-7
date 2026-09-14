from __future__ import annotations

import unittest

from project_72.assurance_core.drift import DriftDetector, DriftState
from project_72.assurance_core.models import AuthoritativeReadback, Subscriber, SubscriberStatus


class DriftDetectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=2,
            status=SubscriberStatus.ACTIVE,
            secret_refs={"authentication": "env://TEST_7001"},
            services={"ims": True, "data": True},
        )
        self.detector = DriftDetector()

    def test_in_sync(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            AuthoritativeReadback(
                request_id="readback",
                source="open5gs.subscribers",
                target="7001",
                observed_version=2,
                state="ACTIVE",
                fingerprint="fp",
                details={"services": {"ims": True, "data": True}},
            ),
        )
        self.assertEqual(report.state, DriftState.IN_SYNC)

    def test_version_drift(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            AuthoritativeReadback(
                request_id="readback",
                source="open5gs.subscribers",
                target="7001",
                observed_version=1,
                state="ACTIVE",
                fingerprint="fp",
                details={"services": {"ims": True, "data": True}},
            ),
        )
        self.assertEqual(report.state, DriftState.DRIFT)

    def test_service_drift(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            AuthoritativeReadback(
                request_id="readback",
                source="open5gs.subscribers",
                target="7001",
                observed_version=2,
                state="ACTIVE",
                fingerprint="fp",
                details={"services": {"ims": False, "data": True}},
            ),
        )
        self.assertEqual(report.state, DriftState.DRIFT)

    def test_absent_projection_is_not_drift_silently(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            AuthoritativeReadback(
                request_id="readback",
                source="open5gs.subscribers",
                target="7001",
                observed_version=0,
                state="ABSENT",
                fingerprint="",
                details={},
            ),
        )
        self.assertEqual(report.state, DriftState.ABSENT)


if __name__ == "__main__":
    unittest.main()
