from __future__ import annotations

import unittest

from lingotrace.migration.transform_plan import plan_transform_previews


class TransformPlanTests(unittest.TestCase):
    def test_transform_requires_non_empty_explicit_map(self) -> None:
        report = plan_transform_previews(
            transform_entries=[
                {
                    "source_path": "old/card.md",
                    "target_path": "new/card.md",
                    "reason": "path collision",
                    "field_mapping": {},
                    "before": {"meaning": "old"},
                    "after": {"meaning_zh": "old"},
                    "user_approved": True,
                }
            ]
        )

        self.assertFalse(report.accepted)
        self.assertEqual(["explicit_mapping_required"], [finding["code"] for finding in report.to_dict()["errors"]])

    def test_transform_preview_records_required_evidence(self) -> None:
        report = plan_transform_previews(
            transform_entries=[
                {
                    "source_path": "old/card.md",
                    "target_path": "review/focus/vocab/card.md",
                    "reason": "source path collides with generated target system asset",
                    "field_mapping": {"meaning": "meaning_zh"},
                    "before": {"meaning": "合成词"},
                    "after": {"meaning_zh": "合成词"},
                    "user_approved": True,
                }
            ]
        )

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("migration-transform-preview", envelope["command"])
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(
            [
                {
                    "source_path": "old/card.md",
                    "target_path": "review/focus/vocab/card.md",
                    "action": "transform_with_map",
                    "reason": "source path collides with generated target system asset",
                    "field_mapping": {"meaning": "meaning_zh"},
                    "before": {"meaning": "合成词"},
                    "after": {"meaning_zh": "合成词"},
                    "preview_result": "planned",
                    "conflict_status": "clear",
                    "acceptance_result": "dry-run-only",
                }
            ],
            envelope["planned_writes"],
        )

    def test_rejects_cosmetic_renaming_without_user_approval(self) -> None:
        report = plan_transform_previews(
            transform_entries=[
                {
                    "source_path": "old/card.md",
                    "target_path": "new/card.md",
                    "reason": "cosmetic naming consistency",
                    "field_mapping": {"reading": "reading_text"},
                    "before": {"reading": "ごうせいご"},
                    "after": {"reading_text": "ごうせいご"},
                    "user_approved": False,
                }
            ]
        )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(["cosmetic_transform_requires_user_approval"], [finding["code"] for finding in envelope["errors"]])
        self.assertEqual(["old/card.md"], envelope["blocked_files"])


if __name__ == "__main__":
    unittest.main()
