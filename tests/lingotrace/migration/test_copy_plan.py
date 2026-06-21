from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.copy_plan import plan_preserve_data_copies


def write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class CopyPlanTests(unittest.TestCase):
    def test_preserved_entries_copy_by_relative_path_and_keep_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            write(source / "review/focus/vocab/example.md", b"frontmatter and body")
            target.mkdir()

            report = plan_preserve_data_copies(
                source_vault=source,
                target_vault=target,
                preserve_entries=[
                    {
                        "relative_path": "review/focus/vocab/example.md",
                        "classification": "preserve-data",
                        "content_hash": "sha256:source-manifest-hash",
                    }
                ],
                generated_target_paths=set(),
            )

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("migration-copy-preview", envelope["command"])
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(
            [
                {
                    "path": "review/focus/vocab/example.md",
                    "action": "copy_preserve_data",
                    "reason": "preserve private learning data",
                    "content_hash": "sha256:source-manifest-hash",
                }
            ],
            envelope["planned_writes"],
        )

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = plan_preserve_data_copies(
                source_vault=root / "source",
                target_vault=root / "target",
                preserve_entries=[
                    {
                        "relative_path": "../outside.md",
                        "classification": "preserve-data",
                        "content_hash": "sha256:bad",
                    }
                ],
                generated_target_paths=set(),
            )

        self.assertFalse(report.accepted)
        self.assertEqual(["unsafe_relative_path"], [finding["code"] for finding in report.to_dict()["errors"]])
        self.assertEqual(["../outside.md"], report.to_dict()["blocked_files"])

    def test_rejects_target_system_asset_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            write(source / "templates/focus-vocab-card.md", b"user file")

            report = plan_preserve_data_copies(
                source_vault=source,
                target_vault=root / "target",
                preserve_entries=[
                    {
                        "relative_path": "templates/focus-vocab-card.md",
                        "classification": "preserve-data",
                        "content_hash": "sha256:user",
                    }
                ],
                generated_target_paths={"templates/focus-vocab-card.md"},
            )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(["target_system_asset_collision"], [finding["code"] for finding in envelope["errors"]])
        self.assertEqual(["templates/focus-vocab-card.md"], envelope["blocked_files"])

    def test_reports_missing_source_assets_as_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = plan_preserve_data_copies(
                source_vault=root / "source",
                target_vault=root / "target",
                preserve_entries=[
                    {
                        "relative_path": "missing/audio.m4a",
                        "classification": "preserve-data",
                        "content_hash": "sha256:missing",
                    }
                ],
                generated_target_paths=set(),
            )

        self.assertFalse(report.accepted)
        self.assertEqual(["missing_source_asset"], [finding["code"] for finding in report.to_dict()["errors"]])
        self.assertEqual(["missing/audio.m4a"], report.to_dict()["blocked_files"])


if __name__ == "__main__":
    unittest.main()
