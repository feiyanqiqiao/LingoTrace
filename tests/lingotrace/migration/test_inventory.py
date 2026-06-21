from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.inventory import (
    build_migration_inventory_report,
    build_migration_manifest,
    build_transform_entry,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class MigrationInventoryTests(unittest.TestCase):
    def test_manifest_includes_explicit_vaults_manifests_and_verification_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-vault"
            target = root / "target-vault"
            write(
                source / "review/focus/vocab/example.md",
                "---\nheadword: 合成語\nreading: ごうせいご\n---\nSee [[sources/example]].\n",
            )
            write(
                target / "review/focus/vocab/example.md",
                "---\nheadword: 合成語\nreading: ごうせいご\n---\nSee [[sources/example]].\n",
            )

            manifest = build_migration_manifest(source, target)

        self.assertEqual("source-vault", manifest["source_vault"])
        self.assertEqual("target-vault", manifest["target_vault"])
        self.assertIn("source_manifest", manifest)
        self.assertIn("target_manifest", manifest)
        self.assertIn("verification_report", manifest)
        self.assertTrue(manifest["verification_report"]["accepted"], manifest["verification_report"])

    def test_preserve_data_entries_keep_relative_paths_hashes_frontmatter_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source-vault"
            target = Path(tmp) / "target-vault"
            write(
                source / "review/focus/vocab/example.md",
                "---\nheadword: 合成語\nreading: ごうせいご\n---\nSee [[sources/example]].\n",
            )
            write(target / "review/focus/vocab/example.md", "target copy")

            manifest = build_migration_manifest(source, target)

        entry = manifest["preserve_data"][0]
        self.assertEqual("review/focus/vocab/example.md", entry["relative_path"])
        self.assertEqual("preserve-data", entry["classification"])
        self.assertEqual("frontmatter_and_body", entry["comparison_strategy"])
        self.assertTrue(entry["content_hash"].startswith("sha256:"))
        self.assertEqual({"headword": "合成語", "reading": "ごうせいご"}, entry["frontmatter"])
        self.assertEqual(["sources/example"], entry["detected_references"])

    def test_system_assets_and_old_framework_entries_are_tracked_for_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source-vault"
            target = Path(tmp) / "target-vault"
            write(source / "codex-skills/review-maintainer/SKILL.md", "legacy evidence")
            write(source / "系统配置/paths.json", "{}")

            manifest = build_migration_manifest(source, target)

        self.assertEqual(["codex-skills/review-maintainer/SKILL.md"], [entry["relative_path"] for entry in manifest["temporary_migration"]])
        self.assertEqual(["系统配置/paths.json"], [entry["relative_path"] for entry in manifest["remove_after_cutover"]])
        self.assertEqual(
            {
                "codex-skills/review-maintainer/SKILL.md",
                "系统配置/paths.json",
            },
            {entry["relative_path"] for entry in manifest["old_framework_exit_ledger"]},
        )

    def test_unclassified_entries_block_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source-vault"
            target = Path(tmp) / "target-vault"
            write(source / "unknown.bin", "unclassified")

            manifest = build_migration_manifest(source, target)
            report = build_migration_inventory_report(source, target)

        self.assertFalse(manifest["verification_report"]["accepted"])
        self.assertEqual(1, manifest["verification_report"]["unclassified_count"])
        self.assertEqual("unclassified_entry", manifest["conflicts"][0]["code"])
        self.assertFalse(report.accepted)
        self.assertEqual("unclassified_entry", report.to_dict()["errors"][0]["code"])

    def test_transform_entries_require_explicit_mapping(self) -> None:
        with self.assertRaises(ValueError) as raised:
            build_transform_entry(
                source_path="old/card.md",
                target_path="new/card.md",
                field_mapping={},
            )

        self.assertIn("explicit_mapping_required", str(raised.exception))

        entry = build_transform_entry(
            source_path="old/card.md",
            target_path="new/card.md",
            field_mapping={"meaning": "meaning_zh"},
        )
        self.assertEqual("transform-with-map", entry["classification"])
        self.assertEqual({"meaning": "meaning_zh"}, entry["field_mapping"])


if __name__ == "__main__":
    unittest.main()
