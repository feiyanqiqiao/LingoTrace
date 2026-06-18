from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from helpers import fixture_path, parse_markdown_fixture


MODULE_PATH = Path(__file__).resolve().parents[3] / "codex-skills/jp-next-day-review-updater/scripts/update_next_day_review.py"
SPEC = importlib.util.spec_from_file_location("update_next_day_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReviewRolloverContractTests(unittest.TestCase):
    def copy_rollover_vault(self, tmpdir: str) -> Path:
        source = fixture_path("review-rollover", "vault")
        target = Path(tmpdir) / "vault"
        shutil.copytree(source, target)
        return target

    def test_active_done_items_advance_and_inactive_or_unfinished_items_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self.copy_rollover_vault(tmpdir)
            paths = MODULE.load_paths_config(vault, "系统配置/paths.json")
            items = MODULE.load_items(paths)
            processed, _, _, _, _, _ = MODULE.prepare_item_updates(items, date(2026, 6, 18), paths)

        writes_by_name = {item.path.name: item.new_text for item in processed}
        self.assertIn("day0-done.md", writes_by_name)
        self.assertIn("day1-overdue.md", writes_by_name)
        self.assertIn("day180-done.md", writes_by_name)
        self.assertNotIn("inactive-done.md", writes_by_name)
        self.assertNotIn("active-not-done.md", writes_by_name)
        self.assertIn("review_stage: day1", writes_by_name["day0-done.md"])
        self.assertIn("next_review: 2026-06-19", writes_by_name["day0-done.md"])
        self.assertIn("review_stage: day1", writes_by_name["day1-overdue.md"])
        self.assertIn("next_review: 2026-06-19", writes_by_name["day1-overdue.md"])
        self.assertIn("status: mastered", writes_by_name["day180-done.md"])
        self.assertIn("next_review: ", writes_by_name["day180-done.md"])

    def test_validation_failure_blocks_planning_before_any_write_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self.copy_rollover_vault(tmpdir)
            broken = vault / "synthetic-study/focus-vocab/missing-stage.md"
            broken.write_text(
                broken.read_text(encoding="utf-8").replace("review_stage: day0\n", ""),
                encoding="utf-8",
            )
            paths = MODULE.load_paths_config(vault, "系统配置/paths.json")

            with self.assertRaisesRegex(MODULE.ReviewUpdateError, "missing frontmatter field 'review_stage'"):
                MODULE.load_items(paths)

            frontmatter, _ = parse_markdown_fixture(
                "review-rollover",
                "vault",
                "synthetic-study",
                "focus-vocab",
                "day0-done.md",
            )
            self.assertEqual(frontmatter["review_stage"], "day0")


if __name__ == "__main__":
    unittest.main()
