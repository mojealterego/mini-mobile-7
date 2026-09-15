from __future__ import annotations

import unittest

from monitoring.project_72_metrics import render


class MetricsExportTest(unittest.TestCase):
    def test_render_is_bounded_and_prometheus_compatible(self) -> None:
        snapshot = {
            "assurance_operations": {"VERIFIED": 7, "DRIFT": 2},
            "drift_events": 2,
            "subscribers": {str(7000 + i): {"healthy": i % 2 == 1} for i in range(1, 8)},
        }
        output = render(snapshot)
        self.assertIn('mm7_assurance_operations_total{status="VERIFIED"} 7', output)
        self.assertIn('mm7_drift_events_total 2', output)
        self.assertIn('mm7_subscriber_health{subscriber_id="7001"} 1', output)
        self.assertIn('mm7_subscriber_health{subscriber_id="7002"} 0', output)
        self.assertNotIn("imsi", output)
        self.assertNotIn("secret", output.lower())

    def test_invalid_snapshot_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            render({"drift_events": -1})
        with self.assertRaises(ValueError):
            render({"assurance_operations": {"VERIFIED": -1}})


if __name__ == "__main__":
    unittest.main()
