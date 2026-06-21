from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.workflow_acceptance import (
    JAPANESE_WORKFLOW_CAPABILITIES,
    evaluate_japanese_workflow_acceptance,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_complete_target_vault(root: Path) -> None:
    write(
        root / "listening/shadowing-01.md",
        """---
track: listening
listening_mode: intensive
source_audio: audio/shadowing-01.m4a
---

# Synthetic Listening

![[audio/shadowing-01.m4a]]
""",
    )
    write(root / "listening/audio/shadowing-01.m4a", "synthetic audio")
    write(
        root / "sources/article-source.md",
        """---
source_kind: plain_text
has_audio: false
final_audio:
creates_review_cards: false
---

# Synthetic Source
""",
    )
    write(
        root / "review/focus/vocab/合成語.md",
        """---
item_type: vocab
reading: ごうせいご
meaning_zh: 合成词
review_stage: 2
next_review: 2026-06-22
done_today: false
---

# 合成語
""",
    )
    write(
        root / "speaking/cards/restaurant.md",
        """---
track: survival_speaking
item_type: speaking_card
status: active
review_stage: day0
next_review: 2026-06-22
done_today: false
scene: restaurant
jp_text: 予約しています。山田です。
meaning_zh: 我有预约，我姓山田。
reply_hint: はい、少々お待ちください。
---

# Restaurant Card
""",
    )
    write(
        root / "daily/2026-06-21.md",
        """---
track: daily_review
review_rollover_checked: true
---

# Daily Review
""",
    )


class WorkflowAcceptanceTests(unittest.TestCase):
    def test_five_japanese_workflows_are_accepted_on_synthetic_target_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_vault = Path(tmp)
            create_complete_target_vault(target_vault)

            report = evaluate_japanese_workflow_acceptance(target_vault)

        envelope = report.to_dict()
        workflow_report = envelope["planned_writes"][0]["workflow_acceptance"]
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("migration-workflow-acceptance", envelope["command"])
        self.assertEqual("dry-run", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(JAPANESE_WORKFLOW_CAPABILITIES, list(workflow_report["capabilities"]))
        self.assertTrue(workflow_report["accepted"])
        for capability in workflow_report["capabilities"].values():
            self.assertTrue(capability["accepted"], capability)
            self.assertGreater(len(capability["evidence"]), 0)

    def test_missing_workflow_blocks_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_vault = Path(tmp)
            write(
                target_vault / "listening/shadowing-01.md",
                """---
track: listening
listening_mode: extensive
---

# Only Listening Exists
""",
            )

            report = evaluate_japanese_workflow_acceptance(target_vault)

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(
            [
                "source_notes",
                "review_materials",
                "speaking_cards",
                "review_rollover",
            ],
            [finding["path"] for finding in envelope["errors"]],
        )
        self.assertEqual([], envelope["changed_files"])

    def test_accepts_phase0_survival_speaking_card_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_vault = Path(tmp)
            create_complete_target_vault(target_vault)

            report = evaluate_japanese_workflow_acceptance(target_vault)

        workflow_report = report.to_dict()["planned_writes"][0]["workflow_acceptance"]
        self.assertTrue(workflow_report["capabilities"]["speaking_cards"]["accepted"])
        self.assertEqual(
            ["speaking/cards/restaurant.md"],
            workflow_report["capabilities"]["speaking_cards"]["evidence"],
        )

    def test_accepts_review_rollover_from_srs_managed_cards_without_daily_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_vault = Path(tmp)
            create_complete_target_vault(target_vault)
            (target_vault / "daily/2026-06-21.md").unlink()

            report = evaluate_japanese_workflow_acceptance(target_vault)

        workflow_report = report.to_dict()["planned_writes"][0]["workflow_acceptance"]
        self.assertTrue(workflow_report["capabilities"]["review_rollover"]["accepted"])
        self.assertIn(
            "review/focus/vocab/合成語.md",
            workflow_report["capabilities"]["review_rollover"]["evidence"],
        )


if __name__ == "__main__":
    unittest.main()
