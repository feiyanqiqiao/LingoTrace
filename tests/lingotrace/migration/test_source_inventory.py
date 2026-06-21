from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.source_inventory import plan_final_source_inventory


def write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class FinalSourceInventoryTests(unittest.TestCase):
    def test_requires_explicit_source_vault_write_freeze_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = plan_final_source_inventory(
                source_vault=None,
                target_vault=root / "target",
                output_dir=None,
                write_freeze_started_at="",
            )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(
            ["output_dir_required", "source_vault_required", "write_freeze_required"],
            [finding["code"] for finding in envelope["errors"]],
        )

    def test_refuses_to_scan_when_source_and_target_roots_are_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = plan_final_source_inventory(
                source_vault=root,
                target_vault=root,
                output_dir=root / "private-output",
                write_freeze_started_at="2026-06-21T01:00:00Z",
            )

        self.assertFalse(report.accepted)
        self.assertEqual(["source_target_same"], [finding["code"] for finding in report.to_dict()["errors"]])

    def test_classifies_synthetic_source_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            output = root / "private-output"
            write(source / "review/focus/vocab/example.md", "---\nreview_stage: 1\n---\nbody\n")
            write(source / "系统配置/模板/card.md", "template")
            write(source / "old-layout/card.md", "needs transform")
            write(source / "codex-skills/jp-example/SKILL.md", "legacy skill")
            write(source / "tools/listening-transcribe-official/render.py", "old renderer")
            write(source / "tmp/debug.log", "approved exclusion")

            report = plan_final_source_inventory(
                source_vault=source,
                target_vault=target,
                output_dir=output,
                write_freeze_started_at="2026-06-21T01:00:00Z",
                transform_map={"old-layout/card.md": {"target_path": "review/focus/vocab/card.md"}},
                exclusion_approvals={"tmp/debug.log": {"approver": "owner", "reason": "temporary debug output"}},
            )

            envelope = report.to_dict()
            self.assertTrue(report.accepted, envelope)
            manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))
            by_path = {entry["relative_path"]: entry for entry in manifest["source_manifest"]}

        self.assertEqual("preserve-data", by_path["review/focus/vocab/example.md"]["classification"])
        self.assertEqual("recreate-from-pack", by_path["系统配置/模板/card.md"]["classification"])
        self.assertEqual("transform-with-map", by_path["old-layout/card.md"]["classification"])
        self.assertEqual("temporary-migration", by_path["codex-skills/jp-example/SKILL.md"]["classification"])
        self.assertEqual("remove-after-cutover", by_path["tools/listening-transcribe-official/render.py"]["classification"])
        self.assertEqual("excluded_with_user_approval", by_path["tmp/debug.log"]["classification"])
        self.assertEqual("frontmatter_and_body", by_path["review/focus/vocab/example.md"]["comparison_strategy"])
        self.assertTrue(by_path["review/focus/vocab/example.md"]["content_hash"].startswith("sha256:"))

    def test_unclassified_entries_block_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            write(source / "unknown.bin", "binary-ish")

            report = plan_final_source_inventory(
                source_vault=source,
                target_vault=root / "target",
                output_dir=root / "private-output",
                write_freeze_started_at="2026-06-21T01:00:00Z",
            )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(["unclassified_entry"], [finding["code"] for finding in envelope["errors"]])
        self.assertEqual(["unknown.bin"], envelope["blocked_files"])

    def test_writes_private_manifest_only_to_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            output = root / "private-output"
            write(source / "daily/2026-06-21.md", "daily note")
            target.mkdir()

            report = plan_final_source_inventory(
                source_vault=source,
                target_vault=target,
                output_dir=output,
                write_freeze_started_at="2026-06-21T01:00:00Z",
            )

            self.assertTrue(report.accepted, report.to_dict())
            self.assertTrue((output / "source-manifest.json").exists())
            self.assertFalse((source / "source-manifest.json").exists())
            self.assertEqual([], [path for path in target.rglob("*") if path.is_file()])
            self.assertEqual(["source-manifest.json"], report.to_dict()["changed_files"])
            self.assertEqual({"source_manifest": "source-manifest.json"}, report.to_dict()["artifacts"])


if __name__ == "__main__":
    unittest.main()
