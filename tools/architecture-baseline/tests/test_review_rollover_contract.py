from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import fixture_path, parse_markdown_fixture

MODULE_PATH = Path(__file__).resolve().parents[3] / "lingotrace/packs/japanese/workflows.py"
SPEC = importlib.util.spec_from_file_location("japanese_workflows", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReviewRolloverContractTests(unittest.TestCase):
    def copy_rollover_vault(self, tmpdir: str) -> Path:
        source = fixture_path("review-rollover", "vault")
        target = Path(tmpdir) / "vault"
        shutil.copytree(source, target)
        self.write_target_context(target)
        return target

    def write_target_context(self, vault: Path) -> None:
        context_root = vault / ".lingotrace"
        context_root.mkdir(parents=True, exist_ok=True)
        (context_root / "vault-context.json").write_text(
            json.dumps(
                {
                    "vault_schema_version": 1,
                    "target_language": "ja",
                    "explanation_language": "zh",
                    "language_pack": "lingo-japanese",
                    "language_pack_version": "0.1.0",
                    "enabled_capabilities": ["review_rollover"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (context_root / "paths.json").write_text(
            json.dumps(
                {
                    "path_roles": [
                        {
                            "role": "focus_vocab_root",
                            "relative_path": "synthetic-study/focus-vocab",
                            "source": "vault_config",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_active_done_items_advance_and_inactive_or_unfinished_items_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self.copy_rollover_vault(tmpdir)
            report = MODULE.review_rollover(vault_root=vault, run_date="2026-06-18")

        planned_by_name = {Path(write["path"]).name: write for write in report.to_dict()["planned_writes"]}
        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("day0-done.md", planned_by_name)
        self.assertIn("day1-overdue.md", planned_by_name)
        self.assertIn("day180-done.md", planned_by_name)
        self.assertNotIn("inactive-done.md", planned_by_name)
        self.assertNotIn("active-not-done.md", planned_by_name)
        self.assertEqual("day1", planned_by_name["day0-done.md"]["to_review_stage"])
        self.assertEqual("2026-06-19", planned_by_name["day0-done.md"]["to_next_review"])
        self.assertEqual("day1", planned_by_name["day1-overdue.md"]["to_review_stage"])
        self.assertEqual("2026-06-19", planned_by_name["day1-overdue.md"]["to_next_review"])
        self.assertTrue(planned_by_name["day1-overdue.md"]["delay_rescheduled"])
        self.assertEqual("mastered", planned_by_name["day180-done.md"]["to_review_stage"])
        self.assertEqual("", planned_by_name["day180-done.md"]["to_next_review"])

    def test_apply_updates_done_today_review_stage_next_review_and_mastered_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self.copy_rollover_vault(tmpdir)
            report = MODULE.review_rollover(vault_root=vault, run_date="2026-06-18", mode="apply")

            day0 = (vault / "synthetic-study/focus-vocab/day0-done.md").read_text(encoding="utf-8")
            day180 = (vault / "synthetic-study/focus-vocab/day180-done.md").read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("done_today: false", day0)
        self.assertIn("review_stage: day1", day0)
        self.assertIn("next_review: 2026-06-19", day0)
        self.assertIn("status: mastered", day180)
        self.assertIn("review_stage: mastered", day180)
        self.assertIn("next_review: ", day180)

    def test_validation_failure_blocks_planning_before_any_write_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self.copy_rollover_vault(tmpdir)
            broken = vault / "synthetic-study/focus-vocab/day0-done.md"
            broken.write_text(
                broken.read_text(encoding="utf-8").replace("review_stage: day0\n", ""),
                encoding="utf-8",
            )
            report = MODULE.review_rollover(vault_root=vault, run_date="2026-06-18", mode="apply")

            self.assertFalse(report.accepted)
            self.assertEqual("missing_field", report.to_dict()["errors"][0]["code"])
            self.assertEqual([], report.to_dict()["changed_files"])
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
