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
track: source_note
source_url: https://example.invalid/source
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
card_type: speaking
reviewed: true
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


if __name__ == "__main__":
    unittest.main()
