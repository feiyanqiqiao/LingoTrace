from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.packs.japanese import workflows


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_target_context(root: Path) -> None:
    write(
        root / ".lingotrace/vault-context.json",
        json.dumps(
            {
                "vault_schema_version": 1,
                "target_language": "ja",
                "explanation_language": "zh",
                "language_pack": "lingo-japanese",
                "language_pack_version": "0.1.0",
                "enabled_capabilities": [
                    "listening_notes",
                    "source_notes",
                    "review_materials",
                    "speaking_cards",
                    "review_rollover",
                ],
            },
            ensure_ascii=False,
        ),
    )
    write(
        root / ".lingotrace/paths.json",
        json.dumps(
            {
                "path_roles": [
                    {"role": "focus_vocab_root", "relative_path": "review/focus/vocab", "source": "vault_config"},
                    {"role": "base_vocab_root", "relative_path": "review/base/vocab", "source": "vault_config"},
                    {"role": "grammar_root", "relative_path": "review/grammar", "source": "vault_config"},
                    {"role": "error_root", "relative_path": "review/errors", "source": "vault_config"},
                    {"role": "speaking_card_root", "relative_path": "speaking/cards", "source": "vault_config"},
                    {"role": "listening_root", "relative_path": "listening", "source": "vault_config"},
                    {"role": "daily_notes_root", "relative_path": "daily", "source": "vault_config"},
                ]
            },
            ensure_ascii=False,
        ),
    )


class JapaneseWorkflowPreviewTests(unittest.TestCase):
    def test_review_materials_previews_target_vault_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "templates/focus-vocab-card.md", "template")
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day1
next_review: 2026-06-22
reading: ごうせいご
meaning_zh: 合成词
---

# 合成語
""",
            )

            report = workflows.review_materials(vault_root=root)

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("review_materials-workflow", envelope["command"])
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(
            [
                {
                    "path": "review/focus/vocab/合成語.md",
                    "action": "preview_review_material",
                    "reason": "target Vault has readable Japanese review material",
                    "item_type": "vocab",
                    "review_stage": "day1",
                }
            ],
            envelope["planned_writes"],
        )

    def test_review_rollover_previews_due_target_card_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day1
next_review: 2026-06-21
reading: ごうせいご
meaning_zh: 合成词
---

# 合成語
""",
            )

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("review_rollover-workflow", envelope["command"])
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(
            [
                {
                    "path": "review/focus/vocab/合成語.md",
                    "action": "preview_review_rollover",
                    "reason": "done_today active card would advance during target Vault rollover",
                    "from_review_stage": "day1",
                    "to_review_stage": "day3",
                    "from_next_review": "2026-06-21",
                    "to_next_review": "2026-06-24",
                    "done_today": False,
                }
            ],
            envelope["planned_writes"],
        )


if __name__ == "__main__":
    unittest.main()
