from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.copy_plan import apply_preserve_data_copies, plan_preserve_data_copies


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

    def test_apply_copies_bytes_to_mapped_target_path_and_records_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source_path = source / "学习系统/听力/Unit1/01.mp3"
            write(source_path, b"audio bytes")

            report = apply_preserve_data_copies(
                source_vault=source,
                target_vault=target,
                preserve_entries=[
                    {
                        "relative_path": "学习系统/听力/Unit1/01.mp3",
                        "classification": "preserve-data",
                        "content_hash": "sha256:source-manifest-hash",
                    }
                ],
                generated_target_paths=set(),
                path_mappings=[{"source_prefix": "学习系统/听力", "target_prefix": "listening"}],
            )

            copied = target / "listening/Unit1/01.mp3"

            self.assertEqual(b"audio bytes", copied.read_bytes())
            envelope = report.to_dict()
            self.assertTrue(report.accepted, envelope)
            self.assertEqual("migration-copy-apply", envelope["command"])
            self.assertEqual("apply", envelope["mode"])
            self.assertEqual(["listening/Unit1/01.mp3"], envelope["changed_files"])
            self.assertEqual(
                [
                    {
                        "source_path": "学习系统/听力/Unit1/01.mp3",
                        "target_path": "listening/Unit1/01.mp3",
                        "action": "copy_preserve_data",
                        "reason": "preserve private learning data",
                        "content_hash": "sha256:source-manifest-hash",
                    }
                ],
                envelope["planned_writes"],
            )

    def test_apply_blocks_target_collision_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            write(source / "学习系统/听力/Unit1/01.mp3", b"source")
            write(target / "listening/Unit1/01.mp3", b"existing")

            report = apply_preserve_data_copies(
                source_vault=source,
                target_vault=target,
                preserve_entries=[
                    {
                        "relative_path": "学习系统/听力/Unit1/01.mp3",
                        "classification": "preserve-data",
                        "content_hash": "sha256:source",
                    }
                ],
                generated_target_paths=set(),
                path_mappings=[{"source_prefix": "学习系统/听力", "target_prefix": "listening"}],
            )

            self.assertEqual(b"existing", (target / "listening/Unit1/01.mp3").read_bytes())
            self.assertFalse(report.accepted)
            self.assertEqual(["target_path_exists"], [finding["code"] for finding in report.to_dict()["errors"]])
            self.assertEqual(["listening/Unit1/01.mp3"], report.to_dict()["blocked_files"])


if __name__ == "__main__":
    unittest.main()
