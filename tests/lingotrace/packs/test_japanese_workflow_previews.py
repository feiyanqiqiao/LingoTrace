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
                    {"role": "speaking_guide_root", "relative_path": "speaking/guides", "source": "vault_config"},
                    {"role": "listening_root", "relative_path": "listening", "source": "vault_config"},
                    {"role": "source_notes_root", "relative_path": "sources", "source": "vault_config"},
                    {"role": "daily_notes_root", "relative_path": "daily", "source": "vault_config"},
                    {"role": "pronunciation_accent_root", "relative_path": "review/pronunciation/accent", "source": "vault_config"},
                    {"role": "pronunciation_phoneme_root", "relative_path": "review/pronunciation/phoneme", "source": "vault_config"},
                ]
            },
            ensure_ascii=False,
        ),
    )


class JapaneseWorkflowPreviewTests(unittest.TestCase):
    def test_workflows_fail_explicitly_without_vault_root(self) -> None:
        for workflow in (
            workflows.listening_notes,
            workflows.source_notes,
            workflows.review_materials,
            workflows.speaking_cards,
            workflows.review_rollover,
        ):
            report = workflow()
            self.assertFalse(report.accepted)
            self.assertEqual("missing_vault_root", report.to_dict()["errors"][0]["code"])

    def test_listening_source_and_speaking_workflows_preview_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            listening = workflows.listening_notes(
                vault_root=root,
                input_artifact={
                    "path": "listening/sample-listening.md",
                    "title": "Sample Listening",
                    "body": "## 精听\n合成音声です。",
                },
            )
            source = workflows.source_notes(
                vault_root=root,
                source_artifact={
                    "path": "sources/sample-source.md",
                    "title": "Sample Source",
                    "body": "## Source\n出处明确。",
                },
            )
            speaking = workflows.speaking_cards(
                vault_root=root,
                candidate={
                    "path": "speaking/cards/restaurant.md",
                    "title": "Restaurant",
                    "body": "## Card\nお願いします。",
                    "reviewed": True,
                },
            )

        for report in (listening, source, speaking):
            envelope = report.to_dict()
            self.assertTrue(report.accepted, envelope)
            self.assertEqual("preview", envelope["mode"])
            self.assertEqual([], envelope["changed_files"])
            self.assertEqual(1, len(envelope["planned_writes"]))

    def test_listening_source_and_speaking_workflows_apply_target_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            cases = [
                (
                    workflows.listening_notes,
                    "input_artifact",
                    {
                        "path": "listening/sample-listening.md",
                        "title": "Sample Listening",
                        "body": "## 精听\n合成音声です。",
                    },
                    "listening/sample-listening.md",
                ),
                (
                    workflows.source_notes,
                    "source_artifact",
                    {
                        "path": "sources/sample-source.md",
                        "title": "Sample Source",
                        "body": "## Source\n出处明确。",
                    },
                    "sources/sample-source.md",
                ),
                (
                    workflows.speaking_cards,
                    "candidate",
                    {
                        "path": "speaking/cards/restaurant.md",
                        "title": "Restaurant",
                        "body": "## Card\nお願いします。",
                        "reviewed": True,
                    },
                    "speaking/cards/restaurant.md",
                ),
            ]

            for workflow, argument_name, payload, expected_path in cases:
                report = workflow(vault_root=root, mode="apply", **{argument_name: payload})
                envelope = report.to_dict()
                self.assertTrue(report.accepted, envelope)
                self.assertEqual([expected_path], envelope["changed_files"])
                self.assertTrue((root / expected_path).is_file())

    def test_speaking_cards_reject_unreviewed_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.speaking_cards(
                vault_root=root,
                candidate={
                    "path": "speaking/cards/unreviewed.md",
                    "title": "Unreviewed",
                    "body": "## Card\n候補です。",
                    "reviewed": False,
                },
            )

        self.assertFalse(report.accepted)
        self.assertEqual("unreviewed_speaking_candidate", report.to_dict()["errors"][0]["code"])

    def test_review_materials_apply_creates_target_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.review_materials(
                vault_root=root,
                card={
                    "path": "review/focus/vocab/合成語.md",
                    "title": "合成語",
                    "body": "## 合成語\n合成词。",
                    "fields": {
                        "track": "class_review",
                        "item_type": "vocab",
                        "status": "active",
                        "done_today": "false",
                        "review_stage": "day1",
                        "next_review": "2026-06-22",
                        "reading": "ごうせいご",
                        "meaning_zh": "合成词",
                    },
                },
                mode="apply",
            )

            envelope = report.to_dict()
            self.assertTrue(report.accepted, envelope)
            self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
            self.assertIn("reading: ごうせいご", (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8"))

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

    def test_review_rollover_apply_advances_due_target_card(self) -> None:
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

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-24", body)


if __name__ == "__main__":
    unittest.main()
