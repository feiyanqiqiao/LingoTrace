from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.english_vault import initialize_english_vault


REPO_ROOT = Path(__file__).resolve().parents[2]


class AgentCliTests(unittest.TestCase):
    def test_every_public_capability_dispatches_to_a_structured_pack_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "English Vault"
            initialize_english_vault(vault, runtime_root=REPO_ROOT)

            for capability in (
                "listening_notes",
                "source_notes",
                "review_materials",
                "speaking_cards",
                "review_rollover",
            ):
                with self.subTest(capability=capability):
                    result = _run(
                        [
                            sys.executable,
                            "-m",
                            "lingotrace.agent",
                            capability,
                            "--vault",
                            str(vault),
                        ]
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(f"{capability}-workflow", report["command"])
                    self.assertEqual("preview", report["mode"])
                    self.assertIn("accepted", report)

    def test_source_note_preview_and_apply_use_the_pack_write_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "English Vault"
            initialize_english_vault(vault, runtime_root=REPO_ROOT)
            payload = root / "payload.json"
            report_path = root / "report.json"
            payload.write_text(
                json.dumps(
                    {
                        "source_artifact": {
                            "path": "sources/article.md",
                            "body": "# Article\n\nTraceable source.\n",
                        }
                    }
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                "-m",
                "lingotrace.agent",
                "source_notes",
                "--vault",
                str(vault),
                "--payload",
                str(payload),
                "--report-json",
                str(report_path),
            ]

            preview = _run(command)
            applied = _run([*command, "--apply"])
            written_report = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertEqual("preview", json.loads(preview.stdout)["mode"])
            self.assertEqual([], json.loads(preview.stdout)["changed_files"])
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertEqual("apply", written_report["mode"])
            self.assertEqual(["sources/article.md"], written_report["changed_files"])
            self.assertTrue((vault / "sources" / "article.md").is_file())

    def test_review_rollover_accepts_an_empty_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Japanese Vault"
            from lingotrace.init.japanese_vault import initialize_japanese_vault

            initialize_japanese_vault(vault, runtime_root=REPO_ROOT)
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.agent",
                    "review_rollover",
                    "--vault",
                    str(vault),
                ]
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["accepted"])

    def test_reserved_payload_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "English Vault"
            initialize_english_vault(vault, runtime_root=REPO_ROOT)
            payload = root / "payload.json"
            payload.write_text(json.dumps({"mode": "apply"}), encoding="utf-8")
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "lingotrace.agent",
                    "review_rollover",
                    "--vault",
                    str(vault),
                    "--payload",
                    str(payload),
                ]
            )

        self.assertEqual(1, result.returncode)
        self.assertEqual("reserved_payload_field", json.loads(result.stdout)["errors"][0]["code"])


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "cp936"
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
