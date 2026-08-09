from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from lingotrace.init.runtime_updates import runtime_update_check_relative_path


REPO_ROOT = Path(__file__).resolve().parents[3]


class InitializationCliTests(unittest.TestCase):
    def test_daily_update_cli_skips_git_when_today_was_already_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            runtime = root / "runtime"
            (runtime / "lingotrace").mkdir(parents=True)
            (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")
            state = vault / runtime_update_check_relative_path()
            state.parent.mkdir(parents=True)
            state.write_text(
                json.dumps(
                    {
                        "runtime_update_check_schema_version": 1,
                        "platform": state.stem,
                        "checked_date": date.today().isoformat(),
                        "runtime_root": str(runtime),
                        "checkout_type": "official",
                        "update_count": 0,
                        "result": "up_to_date",
                    }
                ),
                encoding="utf-8",
            )
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "check-update",
                    "--vault",
                    str(vault),
                    "--runtime-root",
                    str(runtime),
                ]
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("already_checked_today", json.loads(result.stdout)["artifacts"]["status"])

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

    def test_connect_and_resolve_listenkit_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            listenkit = root / "ListenKit"
            (listenkit / "cli").mkdir(parents=True)
            (listenkit / "README.md").write_text("# ListenKit\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            preview = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "connect-listenkit",
                    "--vault",
                    str(vault),
                    "--listenkit-root",
                    str(listenkit),
                ]
            )
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertFalse(vault.exists())

            applied = _run([*preview.args, "--apply"])
            self.assertEqual(0, applied.returncode, applied.stderr)

            resolved = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "resolve-listenkit",
                    "--vault",
                    str(vault),
                ]
            )

        self.assertEqual(0, resolved.returncode, resolved.stderr)
        self.assertEqual(str(listenkit), json.loads(resolved.stdout)["artifacts"]["listenkit_root"])


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


if __name__ == "__main__":
    unittest.main()
