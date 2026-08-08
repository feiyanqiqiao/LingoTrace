from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class InitializationCliTests(unittest.TestCase):
    def test_doctor_reports_machine_readable_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "English Vault"
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "doctor",
                    "--language",
                    "english",
                    "--vault",
                    str(vault),
                    "--runtime-root",
                    str(REPO_ROOT),
                ]
            )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("onboarding-doctor", payload["command"])
        self.assertIn("python", json.loads(payload["artifacts"]["dependencies"]))

    def test_preview_apply_and_resolve_english_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "English Vault"
            base_command = [
                sys.executable,
                "-m",
                "lingotrace.init",
                "vault",
                "--language",
                "english",
                "--vault",
                str(vault),
                "--runtime-root",
                str(REPO_ROOT),
            ]

            preview = _run(base_command)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertEqual("dry-run", json.loads(preview.stdout)["mode"])
            self.assertFalse(vault.exists())

            applied = _run([*base_command, "--apply"])
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertEqual("apply", json.loads(applied.stdout)["mode"])
            self.assertTrue((vault / "AGENTS.md").is_file())

            resolved = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "resolve-runtime",
                    "--vault",
                    str(vault),
                ]
            )
            self.assertEqual(0, resolved.returncode, resolved.stderr)
            self.assertEqual(str(REPO_ROOT), json.loads(resolved.stdout)["artifacts"]["runtime_root"])


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


if __name__ == "__main__":
    unittest.main()
