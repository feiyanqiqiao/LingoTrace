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


def review_card(
    *,
    track: str = "class_review",
    item_type: str = "vocab",
    status: str = "active",
    done_today: str = "true",
    review_stage: str = "day0",
    next_review: str = "2026-06-21",
    last_reviewed: str = "",
) -> str:
    return f"""---
track: {track}
item_type: {item_type}
status: {status}
done_today: {done_today}
review_stage: {review_stage}
next_review: {next_review}
last_reviewed: {last_reviewed}
headword: synthetic
meaning_zh: synthetic
---

# synthetic
"""


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
                    "last_reviewed": "2026-06-21",
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
        self.assertIn("last_reviewed: 2026-06-21", body)

    def test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/focus/vocab/second-preview.md",
                review_card(review_stage="day1", next_review="2026-06-21"),
            )

            apply_report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            second_preview = workflows.review_rollover(vault_root=root, run_date="2026-06-21")

        self.assertTrue(apply_report.accepted, apply_report.to_dict())
        self.assertTrue(second_preview.accepted, second_preview.to_dict())
        self.assertEqual([], second_preview.to_dict()["planned_writes"])

    def test_review_rollover_applies_every_memory_curve_transition_from_run_date(self) -> None:
        cases = [
            ("day0", "day1", "2026-06-22"),
            ("day1", "day3", "2026-06-24"),
            ("day3", "day7", "2026-06-28"),
            ("day7", "day14", "2026-07-05"),
            ("day14", "day30", "2026-07-21"),
            ("day30", "day90", "2026-09-19"),
            ("day90", "day180", "2026-12-18"),
            ("day180", "mastered", ""),
        ]

        for current_stage, next_stage, next_review in cases:
            with self.subTest(current_stage=current_stage):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    create_target_context(root)
                    card_path = root / "review/focus/vocab/curve.md"
                    write(card_path, review_card(review_stage=current_stage, next_review="2026-06-21"))

                    report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
                    body = card_path.read_text(encoding="utf-8")

                self.assertTrue(report.accepted, report.to_dict())
                self.assertIn("done_today: false", body)
                self.assertIn(f"review_stage: {next_stage}", body)
                self.assertIn(f"next_review: {next_review}", body)
                self.assertIn("last_reviewed: 2026-06-21", body)
                if next_stage == "mastered":
                    self.assertIn("status: mastered", body)

    def test_review_rollover_reschedules_overdue_card_without_advancing_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/grammar/〜ものだ.md",
                """---
track: class_review
item_type: grammar
status: active
done_today: true
review_stage: day3
next_review: 2026-06-01
last_reviewed: 2026-05-29
---

# 〜ものだ
""",
            )

            preview = workflows.review_rollover(vault_root=root, run_date="2026-06-21")
            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = (root / "review/grammar/〜ものだ.md").read_text(encoding="utf-8")

        self.assertTrue(preview.accepted, preview.to_dict())
        planned = preview.to_dict()["planned_writes"][0]
        self.assertEqual("day3", planned["to_review_stage"])
        self.assertTrue(planned["delay_rescheduled"])
        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-24", body)
        self.assertIn("last_reviewed: 2026-06-21", body)

    def test_review_rollover_advances_when_overdue_days_equal_allowed_delay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/grammar/boundary.md",
                review_card(item_type="grammar", review_stage="day3", next_review="2026-06-18"),
            )

            preview = workflows.review_rollover(vault_root=root, run_date="2026-06-21")
            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = (root / "review/grammar/boundary.md").read_text(encoding="utf-8")

        self.assertTrue(preview.accepted, preview.to_dict())
        planned = preview.to_dict()["planned_writes"][0]
        self.assertEqual("day7", planned["to_review_stage"])
        self.assertNotIn("delay_rescheduled", planned)
        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("review_stage: day7", body)
        self.assertIn("next_review: 2026-06-28", body)

    def test_review_rollover_blocks_unknown_stage_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            good_path = root / "review/focus/vocab/good.md"
            bad_path = root / "review/grammar/bad.md"
            write(good_path, review_card(review_stage="day0", next_review="2026-06-21"))
            write(bad_path, review_card(item_type="grammar", review_stage="day2", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            good_body = good_path.read_text(encoding="utf-8")
            bad_body = bad_path.read_text(encoding="utf-8")

        self.assertFalse(report.accepted)
        self.assertEqual("unknown_review_stage", report.to_dict()["errors"][0]["code"])
        self.assertEqual([], report.to_dict()["changed_files"])
        self.assertIn("done_today: true", good_body)
        self.assertIn("review_stage: day0", good_body)
        self.assertIn("done_today: true", bad_body)
        self.assertIn("review_stage: day2", bad_body)

    def test_review_rollover_blocks_invalid_next_review_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            good_path = root / "review/focus/vocab/good.md"
            bad_path = root / "review/errors/bad.md"
            write(good_path, review_card(review_stage="day0", next_review="2026-06-21"))
            write(bad_path, review_card(item_type="error", review_stage="day1", next_review="not-a-date"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            good_body = good_path.read_text(encoding="utf-8")
            bad_body = bad_path.read_text(encoding="utf-8")

        self.assertFalse(report.accepted)
        self.assertEqual("invalid_next_review", report.to_dict()["errors"][0]["code"])
        self.assertEqual([], report.to_dict()["changed_files"])
        self.assertIn("done_today: true", good_body)
        self.assertIn("next_review: 2026-06-21", good_body)
        self.assertIn("done_today: true", bad_body)
        self.assertIn("next_review: not-a-date", bad_body)

    def test_review_rollover_does_not_touch_base_vocab_or_daily_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            daily_path = root / "daily/2026-06-21.md"
            daily_without_anchor_path = root / "daily/2026-06-20.md"
            write(focus_path, review_card(review_stage="day180", next_review="2026-06-21"))
            write(base_path, review_card(status="active", done_today="true", review_stage="day1", next_review="2026-06-21"))
            write(daily_path, "# Daily\n\n- manual note\n")
            write(daily_without_anchor_path, "# Daily without anchor\n")
            before_base = base_path.read_text(encoding="utf-8")
            before_daily = daily_path.read_text(encoding="utf-8")
            before_daily_without_anchor = daily_without_anchor_path.read_text(encoding="utf-8")

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            focus_body = focus_path.read_text(encoding="utf-8")
            after_base = base_path.read_text(encoding="utf-8")
            after_daily = daily_path.read_text(encoding="utf-8")
            after_daily_without_anchor = daily_without_anchor_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/focus.md"], report.to_dict()["changed_files"])
        self.assertNotIn("review/base/vocab/base.md", report.to_dict()["read_files"])
        self.assertNotIn("daily/2026-06-21.md", report.to_dict()["read_files"])
        self.assertNotIn("daily/2026-06-20.md", report.to_dict()["read_files"])
        self.assertIn("status: mastered", focus_body)
        self.assertEqual(before_base, after_base)
        self.assertEqual(before_daily, after_daily)
        self.assertEqual(before_daily_without_anchor, after_daily_without_anchor)

    def test_review_rollover_completes_when_daily_note_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/no-daily.md"
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/no-daily.md"], envelope["changed_files"])
        self.assertEqual([], [write for write in envelope["planned_writes"] if write["path"].startswith("daily/")])
        self.assertFalse(any(path.startswith("daily/") for path in envelope["read_files"]))
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-24", body)
        self.assertIn("last_reviewed: 2026-06-21", body)


if __name__ == "__main__":
    unittest.main()
