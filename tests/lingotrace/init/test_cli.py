from __future__ import annotations

import json
import os
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
            data_home = root / "device-data"
            listenkit = root / "ListenKit"
            (listenkit / "cli").mkdir(parents=True)
            (listenkit / "README.md").write_text("# ListenKit\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.ps1").write_text("exit 0\n", encoding="utf-8")

            preview = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "connect-listenkit",
                    "--listenkit-root",
                    str(listenkit),
                ],
                extra_env={"LINGOTRACE_DATA_HOME": str(data_home)},
            )
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertFalse(vault.exists())
            self.assertFalse(data_home.exists())

            applied = _run(
                [*preview.args, "--apply"],
                extra_env={"LINGOTRACE_DATA_HOME": str(data_home)},
            )
            self.assertEqual(0, applied.returncode, applied.stderr)

            resolved = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "resolve-listenkit",
                    "--vault",
                    str(vault),
                ],
                extra_env={"LINGOTRACE_DATA_HOME": str(data_home)},
            )

        self.assertEqual(0, resolved.returncode, resolved.stderr)
        payload = json.loads(resolved.stdout)
        self.assertEqual(str(listenkit), payload["artifacts"]["listenkit_root"])
        self.assertEqual("device", payload["artifacts"]["connection_scope"])
        expected_suffix = "generate-markdown.ps1" if os.name == "nt" else "generate-markdown.sh"
        self.assertTrue(payload["artifacts"]["generate_markdown"].endswith(expected_suffix))

    def test_report_json_is_utf8_and_matches_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "日语 Vault"
            report_path = root / "报告.json"
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "doctor",
                    "--language",
                    "japanese",
                    "--vault",
                    str(vault),
                    "--runtime-root",
                    str(REPO_ROOT),
                    "--report-json",
                    str(report_path),
                ],
                extra_env={"PYTHONIOENCODING": "cp936"},
            )
            written_payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(json.loads(result.stdout), written_payload)

    def test_vault_override_requires_a_vault_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            listenkit = Path(tmp) / "ListenKit"
            (listenkit / "cli").mkdir(parents=True)
            (listenkit / "README.md").write_text("# ListenKit\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.ps1").write_text("exit 0\n", encoding="utf-8")
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.init",
                    "connect-listenkit",
                    "--scope",
                    "vault",
                    "--listenkit-root",
                    str(listenkit),
                ]
            )

        self.assertEqual(1, result.returncode)
        self.assertEqual(
            "vault_root_required_for_listenkit_override",
            json.loads(result.stdout)["errors"][0]["code"],
        )


def _run(
    command: list[str],
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    if extra_env:
        environment.update(extra_env)
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
        env=environment,
    )


if __name__ == "__main__":
    unittest.main()
