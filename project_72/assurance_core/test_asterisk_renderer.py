from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "project-72-render-asterisk-pjsip.sh"


class AsteriskRendererTests(unittest.TestCase):
    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        for subscriber_id in range(7001, 7008):
            env[f"MM7_SIP_PASSWORD_{subscriber_id}"] = f"synthetic-{subscriber_id}-password"
        return env

    def test_renders_all_seven_endpoints_with_0600_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pjsip.conf"
            result = subprocess.run(
                [str(SCRIPT), str(output)],
                env=self._env(),
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            content = output.read_text(encoding="utf-8")
            for subscriber_id in range(7001, 7008):
                self.assertIn(f"username={subscriber_id}", content)
                self.assertIn(f"[${subscriber_id}]" if False else f"[{subscriber_id}]", content)
            self.assertIn("protocol=tls", content)
            self.assertIn("bind=10.40.0.20:5061", content)

    def test_missing_password_fails_closed_and_writes_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pjsip.conf"
            env = os.environ.copy()
            result = subprocess.run(
                [str(SCRIPT), str(output)],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn("missing required secret environment variable", result.stderr)

    def test_newline_in_password_fails_closed(self) -> None:
        env = self._env()
        env["MM7_SIP_PASSWORD_7001"] = "bad\npassword"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pjsip.conf"
            result = subprocess.run(
                [str(SCRIPT), str(output)],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_source_does_not_contain_production_passwords(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("MM7_SIP_PASSWORD_7001=", source)
        self.assertNotIn("password=7001", source)


if __name__ == "__main__":
    unittest.main()
