from __future__ import annotations

import unittest

from helpers import evaluate_migration_fixture, hash_fixture_file, read_fixture_json


class MigrationAcceptanceOracleTests(unittest.TestCase):
    def test_preserve_data_requires_matching_path_hash_frontmatter_links_and_srs(self) -> None:
        result = evaluate_migration_fixture()

        self.assertEqual(result["preserved"]["synthetic-study/focus-vocab/合成語.md"]["status"], "pass")
        self.assertEqual(
            result["preserved"]["synthetic-study/focus-vocab/合成語.md"]["source_hash"],
            hash_fixture_file("migration-preservation", "source-vault", "synthetic-study", "focus-vocab", "合成語.md"),
        )

    def test_recreated_and_removed_assets_are_not_misclassified_as_private_data(self) -> None:
        result = evaluate_migration_fixture()

        self.assertEqual(result["recreated_from_pack"], ["synthetic-config/paths.json", "synthetic-study/total-training.base"])
        self.assertEqual(result["removed_after_cutover"], ["codex-skills/jp-review-material-maintainer/SKILL.md"])
        self.assertNotIn("synthetic-config/paths.json", result["preserved"])

    def test_transforms_require_explicit_map_and_unmapped_differences_fail(self) -> None:
        result = evaluate_migration_fixture()
        rules = read_fixture_json("migration-preservation", "rules.json")

        self.assertEqual(result["transforms"]["synthetic-notes/old-path.md"]["status"], "pass")
        self.assertEqual(rules["transforms"][0]["reason"], "approved_path_collision")
        self.assertEqual(result["failures"]["synthetic-notes/unmapped-difference.md"]["reason"], "unmapped_difference")

    def test_missing_attachment_duplicate_target_and_manual_conflict_fail(self) -> None:
        result = evaluate_migration_fixture()

        self.assertEqual(result["failures"]["synthetic-study/listening/missing-attachment.md"]["reason"], "missing_attachment")
        self.assertEqual(result["failures"]["synthetic-study/focus-vocab/duplicate-target.md"]["reason"], "duplicate_target")
        self.assertEqual(result["failures"]["synthetic-study/speaking-cards/manual-conflict.md"]["reason"], "manual_content_conflict")


if __name__ == "__main__":
    unittest.main()
