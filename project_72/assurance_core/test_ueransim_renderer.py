from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "project-72-render-ueransim.sh"


class UERANSIMRendererTest(unittest.TestCase):
    def _environment(self) -> dict[str, str]:
        env = os.environ.copy()
        for index in range(1, 8):
            env[f"MM7_SECRET_MINI_MOBILE_7_700{index}"] = (
                '{"k":"00000000000000000000000000000001",'
                '"opc":"00000000000000000000000000000002",'
                '"amf":"8000"}'
            )
        return env

    def _run(self, output: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), str(output)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_renders_all_seven_catalog_members_with_permissions_and_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self._run(output, self._environment())
            self.assertEqual(result.returncode, 0, result.stderr)
            files = sorted(output.glob("ue-*.yaml"))
            self.assertEqual([path.name for path in files], [f"ue-700{i}.yaml" for i in range(1, 8)])
            for index, path in enumerate(files, start=1):
                text = path.read_text(encoding="utf-8")
                self.assertIn(f"supi: 'imsi-00101000000000{index}'", text)
                self.assertIn("mcc: '001'", text)
                self.assertIn("mnc: '01'", text)
                self.assertIn("apn: internet", text)
                self.assertIn("gnbSearchList:\n  - 10.10.0.6", text)
                self.assertIn(f"tunName: uesimtun-{index:04d}", text)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_missing_secret_reference_fails_without_leaving_partial_output(self) -> None:
        env = self._environment()
        del env["MM7_SECRET_MINI_MOBILE_7_7004"]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self._run(output, env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("7004", result.stderr)
            self.assertFalse((output / "ue-7004.yaml").exists())
            self.assertEqual(len(list(output.glob("ue-*.yaml"))), 3)

    def test_malformed_secret_material_fails_closed_and_removes_output(self) -> None:
        env = self._environment()
        env["MM7_SECRET_MINI_MOBILE_7_7002"] = '{"k":"bad","opc":"00000000000000000000000000000002","amf":"8000"}'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self._run(output, env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("K must be exactly 32 hexadecimal characters", result.stderr)
            self.assertFalse((output / "ue-7002.yaml").exists())
            self.assertEqual(len(list(output.glob("ue-*.yaml"))), 1)

    def test_renderer_source_contains_no_authentication_literals(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for token in ("password=", "secret=", "opc=", "k=", "amf="):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
