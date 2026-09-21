from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "project-72-runtime-capabilities.sh"


class RuntimeCapabilitiesScriptTests(unittest.TestCase):
    def test_script_is_valid_bash(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_is_read_only_and_fail_closed(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Read-only diagnostic", source)
        self.assertIn("RUNTIME CAPABILITY RESULT: BLOCKED", source)
        self.assertIn("exit 1", source)
        self.assertNotIn("apt install", source)
        self.assertNotIn("systemctl start", source)
        self.assertNotIn("systemctl enable", source)
        self.assertNotIn("ip link set", source)
        self.assertNotIn("iptables -A", source)
        self.assertNotIn("iptables -I", source)

    def test_script_checks_runtime_boundaries(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "systemctl",
            "/proc/1/cgroup",
            "/dev/net/tun",
            "ip -4 route",
            "ip link show",
            "/proc/sys/net/ipv4/ip_forward",
            "iptables -S",
            "ss -H -lntup",
            "/proc/net/sctp/assocs",
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
