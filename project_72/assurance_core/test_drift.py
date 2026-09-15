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

    def _readback(self, **overrides: object) -> AuthoritativeReadback:
        details = {
            "imsi": self.subscriber.imsi,
            "ue_ip": self.subscriber.ue_ip,
            "marker": {
                "subscriber_id": self.subscriber.subscriber_id,
                "canonical_version": self.subscriber.version,
                "status": self.subscriber.status.value,
            },
            "services": {"ims": True, "data": True},
        }
        details.update(overrides.pop("details", {}))
        return AuthoritativeReadback(
            request_id="readback",
            source="open5gs.subscribers",
            target=str(overrides.pop("target", "7001")),
            observed_version=int(overrides.pop("observed_version", 2)),
            state=str(overrides.pop("state", "ACTIVE")),
            fingerprint="fp",
            details=details,
        )

    def test_in_sync(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback())
        self.assertEqual(report.state, DriftState.IN_SYNC)

    def test_version_drift(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(observed_version=1))
        self.assertEqual(report.state, DriftState.DRIFT)

    def test_service_drift(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            self._readback(details={"services": {"ims": False, "data": True}}),
        )
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertIn("ims", report.reason)

    def test_imsi_drift(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(details={"imsi": "001010000000002"}))
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertEqual(report.reason, "IMSI projection mismatch")

    def test_ue_ip_drift(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(details={"ue_ip": "10.20.0.99"}))
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertEqual(report.reason, "UE IP projection mismatch")

    def test_marker_drift(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            self._readback(
                details={
                    "marker": {
                        "subscriber_id": "7002",
                        "canonical_version": 2,
                        "status": "ACTIVE",
                    }
                }
            ),
        )
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertEqual(report.reason, "assurance marker subscriber mismatch")

    def test_missing_marker_is_fail_closed(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(details={"marker": None}))
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertEqual(report.reason, "authoritative assurance marker is missing")

    def test_missing_services_are_fail_closed(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(details={"services": None}))
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertEqual(report.reason, "authoritative service projection is missing")

    def test_target_mismatch_is_drift(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(target="7002"))
        self.assertEqual(report.state, DriftState.DRIFT)

    def test_lifecycle_drift(self) -> None:
        report = self.detector.compare(self.subscriber, self._readback(state="SUSPENDED"))
        self.assertEqual(report.state, DriftState.DRIFT)
        self.assertIn("canonical state is ACTIVE", report.reason)

    def test_absent_projection_is_not_drift_silently(self) -> None:
        report = self.detector.compare(
            self.subscriber,
            self._readback(state="ABSENT", observed_version=0, details={"marker": None, "services": None}),
        )
        self.assertEqual(report.state, DriftState.ABSENT)


if __name__ == "__main__":
    unittest.main()
