from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.packs.japanese import workflows


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic-image")


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


def write_source(root: Path, name: str) -> None:
    write(root / f"sources/{name}.md", f"# {name}\n")


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

    def test_listening_bundle_previews_and_applies_markdown_json_and_binary_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()
            create_target_context(root)
            staged_audio = Path(tmp) / "slice.m4a"
            staged_audio.write_bytes(b"synthetic-audio")
            payload = {
                "note_path": "listening/lesson/lesson.md",
                "files": [
                    {
                        "path": "listening/lesson/lesson.md",
                        "content": "---\ntitle: Lesson\n---\n\n# Lesson\n",
                    },
                    {
                        "path": "listening/lesson/artifacts/lesson.asr.json",
                        "content": "{}\n",
                    },
                    {
                        "path": "listening/lesson/attach/lesson_S01.m4a",
                        "source_path": staged_audio,
                    },
                ],
            }

            preview = workflows.listening_notes(vault_root=root, input_artifact=payload, mode="preview")
            applied = workflows.listening_notes(vault_root=root, input_artifact=payload, mode="apply")

            self.assertTrue(preview.accepted, preview.to_dict())
            self.assertEqual(preview.changed_files, [])
            self.assertTrue(applied.accepted, applied.to_dict())
            self.assertEqual(len(applied.changed_files), 3)
            self.assertEqual(
                (root / "listening/lesson/attach/lesson_S01.m4a").read_bytes(),
                b"synthetic-audio",
            )

    def test_listening_bundle_rejects_paths_outside_role_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            outside = workflows.listening_notes(
                vault_root=root,
                input_artifact={"files": [{"path": "sources/not-listening.md", "content": "x"}]},
            )
            duplicate = workflows.listening_notes(
                vault_root=root,
                input_artifact={
                    "files": [
                        {"path": "listening/duplicate.md", "content": "one"},
                        {"path": "listening/duplicate.md", "content": "two"},
                    ]
                },
            )

        self.assertEqual(outside.errors[0].code, "listening_artifact_outside_role")
        self.assertEqual(duplicate.errors[0].code, "duplicate_listening_bundle_path")

    def test_existing_listening_note_apply_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            note_path = root / "listening/lesson.md"
            write(note_path, "old")
            payload = {
                "note_path": "listening/lesson.md",
                "files": [{"path": "listening/lesson.md", "content": "new"}],
            }

            rejected = workflows.listening_notes(vault_root=root, input_artifact=payload, mode="apply")
            self.assertEqual(note_path.read_text(encoding="utf-8"), "old")
            payload["overwrite_confirmed"] = True
            accepted = workflows.listening_notes(vault_root=root, input_artifact=payload, mode="apply")

            self.assertEqual(rejected.errors[0].code, "existing_listening_note_confirmation_required")
            self.assertEqual(note_path.read_text(encoding="utf-8"), "new")
            self.assertTrue(accepted.accepted, accepted.to_dict())

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
                        "priority": "normal",
                        "done_today": False,
                        "first_seen": "2026-06-21",
                        "last_seen": "2026-06-21",
                        "seen_count": 1,
                        "error_count": 0,
                        "review_stage": "day1",
                        "next_review": "2026-06-22",
                        "last_reviewed": "",
                        "source_notes": [],
                        "tags": ["jp/vocab", "jp/class_review"],
                        "headword": "合成語",
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
priority: normal
done_today: false
first_seen: 2026-06-21
last_seen: 2026-06-21
seen_count: 1
error_count: 0
review_stage: day1
next_review: 2026-06-22
last_reviewed:
source_notes: []
tags: ['jp/vocab', 'jp/class_review']
headword: 合成語
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

    def test_review_materials_preview_keeps_legacy_cards_visible_without_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/focus/vocab/旧卡.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day3
next_review: 2026-06-25
headword: 旧卡
reading: きゅうか
meaning_zh: 旧卡
source_notes: []
---

# 旧卡
""",
            )

            report = workflows.review_materials(vault_root=root)

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("review/focus/vocab/旧卡.md", report.planned_writes[0]["path"])
        self.assertEqual("day3", report.planned_writes[0]["review_stage"])

    def test_review_materials_item_creates_initialized_focus_vocab_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "source-note")

            preview = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                    "meaning_zh": "合成词",
                    "source_note": "[[source-note]]",
                },
                extraction_date="2026-06-22",
            )
            apply = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                    "meaning_zh": "合成词",
                    "source_note": "[[source-note]]",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        preview_envelope = preview.to_dict()
        apply_envelope = apply.to_dict()
        self.assertTrue(preview.accepted, preview_envelope)
        self.assertEqual([], preview_envelope["changed_files"])
        self.assertEqual("create_focus_card", preview_envelope["planned_writes"][0]["action"])
        self.assertTrue(apply.accepted, apply_envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], apply_envelope["changed_files"])
        self.assertIn("status: active", body)
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("next_review: 2026-06-22", body)
        self.assertIn('  - "[[sources/source-note|source-note]]"', body)
        self.assertIn("first_seen: 2026-06-22", body)
        self.assertIn("seen_count: 1", body)
        self.assertIn("## 快速复习", body)

    def test_review_materials_item_resets_reappearing_active_focus_to_day0_without_body_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "new-source")
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day3
next_review: 2026-06-25
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
source_notes: [[old-source]]
---

## 人工整理
这里不能丢。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                    "meaning_zh": "合成词",
                    "source_note": "[[new-source]]",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            files = sorted(path.relative_to(root).as_posix() for path in (root / "review/focus/vocab").glob("*.md"))
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
        self.assertEqual(["review/focus/vocab/合成語.md"], files)
        self.assertIn('  - "[[old-source]]"', body)
        self.assertIn('  - "[[sources/new-source|new-source]]"', body)
        self.assertIn("status: active", body)
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("next_review: 2026-06-22", body)
        self.assertIn("last_reviewed: ", body)
        self.assertIn("这里不能丢。", body)

    def test_review_materials_item_handles_source_note_list_without_rewriting_unknown_nested_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "new-source")
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-21
headword: 合成語
meaning_zh: 合成词
source_notes:
  - "[[old-source]]"
manual_metadata:
  source: classroom
  confidence: high
---

## 人工整理
嵌套字段和正文都不能丢。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "meaning_zh": "合成词",
                    "source_note": "[[new-source]]",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn('  - "[[old-source]]"', body)
        self.assertIn('  - "[[sources/new-source|new-source]]"', body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("manual_metadata:\n  source: classroom\n  confidence: high", body)
        self.assertNotIn("manual_metadata: ['source: classroom', 'confidence: high']", body)
        self.assertIn("嵌套字段和正文都不能丢。", body)

    def test_review_materials_item_does_not_reset_active_focus_for_same_source_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "same-source")
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-21
headword: 合成語
meaning_zh: 合成词
source_notes:
  - "[[same-source]]"
---

## 人工整理
同一来源不应重置进度。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "meaning_zh": "合成词",
                    "source_note": "[[same-source]]",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn('  - "[[same-source]]"', body)
        self.assertIn("done_today: true", body)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-25", body)
        self.assertIn("last_reviewed: 2026-06-21", body)
        self.assertIn("同一来源不应重置进度。", body)

    def test_review_materials_item_keeps_distinct_same_basename_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "daily/a/lesson.md", "# old\n")
            write(root / "sources/b/lesson.md", "# new\n")
            write(
                root / "review/focus/vocab/同名.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-21
headword: 同名
meaning_zh: 同名
source_notes:
  - "[[daily/a/lesson|lesson]]"
---

## 人工整理
两个同名来源都必须保留。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "同名",
                    "meaning_zh": "同名",
                    "source_note": "sources/b/lesson.md",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            fields = workflows._frontmatter(root / "review/focus/vocab/同名.md")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(
            ["[[daily/a/lesson|lesson]]", "[[sources/b/lesson|lesson]]"],
            fields["source_notes"],
        )
        self.assertEqual("day0", fields["review_stage"])
        self.assertEqual("2026-06-22", fields["next_review"])
        self.assertFalse(fields["done_today"])

    def test_review_materials_item_does_not_guess_ambiguous_legacy_source_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "daily/a/lesson.md", "# daily\n")
            write(root / "sources/b/lesson.md", "# source\n")
            write(
                root / "review/focus/vocab/歧义.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-21
headword: 歧义
meaning_zh: 歧义
source_notes:
  - "[[lesson]]"
---

## 人工整理
旧链接必须保留，但不能据此猜测来源。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "歧义",
                    "meaning_zh": "歧义",
                    "source_note": "sources/b/lesson.md",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            fields = workflows._frontmatter(root / "review/focus/vocab/歧义.md")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(
            ["[[lesson]]", "[[sources/b/lesson|lesson]]"],
            fields["source_notes"],
        )
        self.assertEqual("day0", fields["review_stage"])

    def test_review_materials_item_resets_reappearing_errors_and_grammar_weaknesses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/errors/2026-06-20_正しい.md",
                """---
track: class_review
item_type: error
status: active
priority: normal
done_today: true
correct_form: 正しい
wrong_form: 間違い
reason: 理由
avoidance: 方法
source_notes: []
first_seen: 2026-06-20
last_seen: 2026-06-20
seen_count: 1
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-21
tags: []
---

# 错题人工正文
""",
            )
            write(
                root / "review/grammar/〜ようだ.md",
                """---
track: class_review
item_type: grammar
status: active
priority: normal
done_today: true
pattern: 〜ようだ
meaning_zh: 好像
formation:
  - V普通形 + ようだ
source_notes: []
first_seen: 2026-06-20
last_seen: 2026-06-20
seen_count: 1
error_count: 0
review_stage: day7
next_review: 2026-06-29
last_reviewed: 2026-06-21
tags: []
---

# 语法人工正文
""",
            )

            error_report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "error",
                    "correct_form": "正しい",
                    "wrong_form": "間違い",
                    "reason": "理由",
                    "avoidance": "方法",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            grammar_report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "grammar",
                    "pattern": "〜ようだ",
                    "meaning_zh": "好像",
                    "formation": ["V普通形 + ようだ"],
                    "weakness": True,
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            error_fields = workflows._frontmatter(root / "review/errors/2026-06-20_正しい.md")
            grammar_fields = workflows._frontmatter(root / "review/grammar/〜ようだ.md")

        self.assertTrue(error_report.accepted, error_report.to_dict())
        self.assertTrue(grammar_report.accepted, grammar_report.to_dict())
        for fields in (error_fields, grammar_fields):
            self.assertEqual("day0", fields["review_stage"])
            self.assertEqual("2026-06-22", fields["next_review"])
            self.assertEqual("", fields["last_reviewed"])
            self.assertFalse(fields["done_today"])
            self.assertEqual("high", fields["priority"])
            self.assertEqual(2, fields["seen_count"])
        self.assertEqual(2, error_fields["error_count"])
        self.assertEqual(1, grammar_fields["error_count"])

    def test_review_materials_item_restores_base_only_vocab_to_focus_without_touching_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "new-source")
            write(
                root / "review/base/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: promoted
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
source_notes: [[base-source]]
---

## 人工整理
base 内容。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "source_note": "[[new-source]]",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            focus_body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")
            base_body = (root / "review/base/vocab/合成語.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
        self.assertIn("status: active", focus_body)
        self.assertIn("review_stage: day0", focus_body)
        self.assertIn('  - "[[base-source]]"', focus_body)
        self.assertIn('  - "[[sources/new-source|new-source]]"', focus_body)
        self.assertIn("status: promoted", base_body)
        self.assertIn("base 内容。", base_body)

    def test_review_materials_item_stops_after_focus_match_even_when_base_has_duplicate_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/合成語.md"
            write(
                focus_path,
                """---
track: class_review
item_type: vocab
status: active
priority: normal
done_today: false
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
source_notes: []
first_seen: 2026-06-01
last_seen: 2026-06-01
seen_count: 1
error_count: 0
review_stage: day3
next_review: 2026-06-25
last_reviewed: 2026-06-20
tags:
  - jp/vocab
---

## 人工正文
focus only
""",
            )
            base_bodies: dict[Path, str] = {}
            for folder in ("history-a", "history-b"):
                path = root / f"review/base/vocab/{folder}/合成語.md"
                write(path, f"---\nitem_type: vocab\nheadword: 合成語\n---\n\n{folder}\n")
                base_bodies[path] = path.read_text(encoding="utf-8")

            report = workflows.review_materials(
                vault_root=root,
                item={"item_type": "vocab", "headword": "合成語", "reading": "ごうせいご", "meaning_zh": "新释义"},
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            focus = focus_path.read_text(encoding="utf-8")
            base_after = {path: path.read_text(encoding="utf-8") for path in base_bodies}

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/合成語.md"], report.changed_files)
        self.assertIn("last_seen: 2026-06-22", focus)
        self.assertIn("meaning_zh: 合成词", focus)
        self.assertIn("focus only", focus)
        self.assertEqual(base_bodies, base_after)

    def test_review_materials_item_reactivates_mastered_focus_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write_source(root, "new-source")
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: mastered
done_today: false
review_stage: mastered
next_review:
last_reviewed: 2026-06-01
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
---

## 人工整理
再次出错时仍要保留。
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "source_note": "[[new-source]]",
                },
                extraction_date="2026-06-22",
                existing_update_confirmed=True,
                mode="apply",
            )
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
        self.assertIn("status: active", body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("next_review: 2026-06-22", body)
        self.assertIn("last_reviewed: ", body)
        self.assertIn("[[sources/new-source|new-source]]", body)
        self.assertIn("再次出错时仍要保留。", body)

    def test_review_materials_item_routes_grammar_error_and_pronunciation_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            cases = [
                (
                    {
                        "item_type": "grammar",
                        "pattern": "ことによって",
                        "meaning_zh": "通过某种方式",
                        "formation": "V辞書形 + ことによって",
                    },
                    "review/grammar/ことによって.md",
                    "item_type: grammar",
                ),
                (
                    {
                        "item_type": "error",
                        "correct_form": "店として知られている",
                        "wrong_form": "店に知られている",
                        "reason": "として marks role or identity.",
                        "avoidance": "固定搭配按「Nとして」记忆。",
                    },
                    "review/errors/2026-06-22_店として知られている.md",
                    "item_type: error",
                ),
                (
                    {
                        "item_type": "pronunciation",
                        "pronunciation_kind": "accent",
                        "target_text": "雨 / 飴",
                        "issue_tags": "accent contrast",
                    },
                    "review/pronunciation/accent/雨-飴.md",
                    "item_type: pronunciation",
                ),
            ]

            for item, expected_path, expected_text in cases:
                report = workflows.review_materials(
                    vault_root=root,
                    item=item,
                    extraction_date="2026-06-22",
                    mode="apply",
                )
                self.assertTrue(report.accepted, report.to_dict())
                self.assertTrue((root / expected_path).is_file(), expected_path)
                self.assertIn(expected_text, (root / expected_path).read_text(encoding="utf-8"))

            grammar = (root / "review/grammar/ことによって.md").read_text(encoding="utf-8")
            error = (root / "review/errors/2026-06-22_店として知られている.md").read_text(encoding="utf-8")
            self.assertIn("status: active", grammar)
            self.assertIn("done_today: false", grammar)
            self.assertIn("review_stage: day0", grammar)
            self.assertIn("next_review: 2026-06-22", grammar)
            self.assertIn("  - V辞書形 + ことによって", grammar)
            self.assertIn("## 接续、用法与例句", grammar)
            self.assertIn("status: active", error)
            self.assertIn("done_today: false", error)
            self.assertIn("review_stage: day0", error)
            self.assertIn("next_review: 2026-06-22", error)
            self.assertIn("wrong_form: 店に知られている", error)

    def test_review_materials_item_blocks_uncertain_image_backed_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/image-source.md", "## 単語\n\n![[attachments/lesson.png]]\n")
            write_image(root / "attachments/lesson.png")

            legacy_report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "不鮮明",
                    "image_backed": True,
                    "image_readable": False,
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            evidence_report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "不鮮明",
                    "reading": "ふせんめい",
                    "meaning_zh": "不清晰",
                    "image_backed": True,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "uncertain",
                        "observed_text": "不鮮明",
                        "normalized_headword": "不鮮明",
                    },
                    "source_note": "sources/image-source",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )

        self.assertFalse(legacy_report.accepted)
        self.assertFalse(evidence_report.accepted)
        self.assertEqual("uncertain_image_backed_review_material", legacy_report.errors[0].code)
        self.assertEqual("uncertain_image_backed_review_material", evidence_report.errors[0].code)

    def test_review_materials_item_accepts_clearly_readable_image_backed_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/image-source.md", "# 图片词汇\n\n## 単語\n\n![[attachments/lesson.png]]\n")
            write_image(root / "attachments/lesson.png")

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "看板",
                    "reading": "かんばん",
                    "meaning_zh": "招牌",
                    "image_backed": True,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板（かんばん）",
                        "normalized_headword": "看板",
                    },
                    "source_note": "[[image-source]]",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            body = (root / "review/focus/vocab/看板.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/看板.md"], envelope["changed_files"])
        self.assertIn("attachments/lesson.png", envelope["read_files"])
        self.assertIn('  - "[[sources/image-source|image-source]]"', body)

    def test_review_materials_item_requires_real_image_inspection_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/image-source.md", "## 単語\n\n![[attachments/lesson.png]]\n")
            write_image(root / "attachments/lesson.png")
            base_item = {
                "item_type": "vocab",
                "headword": "看板",
                "reading": "かんばん",
                "meaning_zh": "招牌",
                "image_backed": True,
                "source_note": "sources/image-source",
            }
            boolean_only = workflows.review_materials(
                vault_root=root,
                item={**base_item, "image_readable": True},
            )
            ocr_only = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "ocr",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            missing_attachment = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "image_evidence": {
                        "attachment": "attachments/missing.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            traversing_attachment = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "image_evidence": {
                        "attachment": "../attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            observed_mismatch = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "別の語",
                        "normalized_headword": "看板",
                    },
                },
            )
            write(root / "sources/outside-section.md", "![[attachments/lesson.png]]\n\n## 単語\n\n仅有图片外嵌入。\n")
            outside_vocab_section = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "source_note": "sources/outside-section",
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            write(root / "sources/ambiguous-embed.md", "## 単語\n\n![[lesson.png]]\n")
            write_image(root / "other/lesson.png")
            ambiguous_embed = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "source_note": "sources/ambiguous-embed",
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            write(root / "sources/unsafe-embed.md", "## 単語\n\n![[../attachments/lesson.png]]\n")
            unsafe_embed = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "source_note": "sources/unsafe-embed",
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                },
            )
            normalized_visible_form = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "溢れる",
                    "reading": "あふれる",
                    "meaning_zh": "溢出",
                    "image_backed": True,
                    "source_note": "sources/image-source",
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "水が溢れた",
                        "observed_form": "溢れた",
                        "normalized_headword": "溢れる",
                    },
                },
            )

        self.assertEqual("missing_image_inspection_evidence", boolean_only.errors[0].code)
        self.assertEqual("invalid_image_inspection_method", ocr_only.errors[0].code)
        self.assertEqual("missing_image_attachment", missing_attachment.errors[0].code)
        self.assertEqual("invalid_image_attachment", traversing_attachment.errors[0].code)
        self.assertEqual("image_observed_text_mismatch", observed_mismatch.errors[0].code)
        self.assertEqual("image_attachment_not_in_source_vocab_section", outside_vocab_section.errors[0].code)
        self.assertEqual("ambiguous_image_attachment_embed", ambiguous_embed.errors[0].code)
        self.assertEqual("invalid_image_attachment_embed", unsafe_embed.errors[0].code)
        self.assertTrue(normalized_visible_form.accepted, normalized_visible_form.to_dict())

    def test_review_materials_item_does_not_repeat_vocab_already_written_in_source_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "sources/image-source.md",
                "# 图片词汇\n\n## 単語\n\n- 看板（かんばん）：招牌\n\n![[attachments/lesson.png]]\n",
            )
            write_image(root / "attachments/lesson.png")
            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "看板",
                    "reading": "かんばん",
                    "meaning_zh": "招牌",
                    "image_backed": True,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "manual",
                        "readability": "clear",
                        "observed_text": "看板",
                        "normalized_headword": "看板",
                    },
                    "source_note": "sources/image-source",
                },
                mode="apply",
            )

            self.assertFalse((root / "review/focus/vocab/看板.md").exists())

        self.assertFalse(report.accepted)
        self.assertEqual("image_item_already_present_in_source_text", report.errors[0].code)

    def test_review_materials_item_preserves_vocab_review_cues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "紛らわしい",
                    "reading": "まぎらわしい",
                    "accent_display": "まぎらわしい⑤",
                    "meaning_zh": "容易混淆",
                    "collocations": "紛らわしい表現",
                    "confusable_with": "[[間違えやすい]]",
                    "contrast_with": "[[ややこしい]]",
                    "kanji_diff": True,
                    "kanji_diff_pairs": "紛らわしい / 間違えやすい",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            body = (root / "review/focus/vocab/紛らわしい.md").read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("accent_display: まぎらわしい⑤", body)
        self.assertIn("  - 紛らわしい表現", body)
        self.assertNotIn("confusable_with:", body)
        self.assertNotIn("contrast_with:", body)
        self.assertIn("kanji_diff: true", body)
        self.assertIn("  - 紛らわしい / 間違えやすい", body)
        self.assertIn("## 待补卡", body)
        self.assertEqual(2, len(report.warnings))

    def test_review_materials_item_blocks_missing_core_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "grammar",
                    "meaning_zh": "通过某种方式",
                    "formation": "V辞書形 + ことによって",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual("missing_review_item_title", envelope["errors"][0]["code"])

    def test_review_materials_item_blocks_duplicate_existing_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            for folder in ("a", "b"):
                write(
                    root / f"review/focus/vocab/{folder}/合成語.md",
                    """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day1
next_review: 2026-06-23
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
---

# 合成語
""",
                )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual("duplicate_review_material_match", envelope["errors"][0]["code"])

    def test_review_materials_item_blocks_target_path_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/focus/vocab/合成語.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day1
next_review: 2026-06-23
headword: 別項目
reading: べつこうもく
meaning_zh: 其他项目
---

# 別項目
""",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                    "meaning_zh": "合成词",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            body = (root / "review/focus/vocab/合成語.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual("review_material_path_collision", envelope["errors"][0]["code"])
        self.assertIn("headword: 別項目", body)

    def test_review_materials_item_does_not_touch_daily_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "daily/2026-06-22.md", "## 每日学习清单\n原内容。\n")

            report = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "合成語",
                    "reading": "ごうせいご",
                    "meaning_zh": "合成词",
                },
                extraction_date="2026-06-22",
                mode="apply",
            )
            daily = (root / "daily/2026-06-22.md").read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/合成語.md"], envelope["changed_files"])
        self.assertEqual("## 每日学习清单\n原内容。\n", daily)

    def test_review_materials_daily_checklist_requires_explicit_confirmed_structured_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            daily_path = root / "daily/2026-06-22.md"
            card_path = root / "review/focus/vocab/合成語.md"
            write(daily_path, "# 课堂原始记录\n\n老师讲了合成語。\n")
            write(card_path, review_card(done_today="true", review_stage="day3", next_review="2026-06-22"))
            card_before = card_path.read_text(encoding="utf-8")
            payload = {
                "path": "daily/2026-06-22.md",
                "completed": ["复习词汇卡 3 张", "整理语法卡 1 张"],
                "blockers": ["〜ようだ和〜らしい仍容易混淆"],
                "reflection": "明天先做一组对比练习。",
            }

            preview = workflows.review_materials(vault_root=root, daily_checklist=payload, mode="preview")
            after_preview = daily_path.read_text(encoding="utf-8")
            blocked = workflows.review_materials(vault_root=root, daily_checklist=payload, mode="apply")
            accepted = workflows.review_materials(
                vault_root=root,
                daily_checklist=payload,
                existing_update_confirmed=True,
                mode="apply",
            )
            daily_after = daily_path.read_text(encoding="utf-8")
            card_after = card_path.read_text(encoding="utf-8")

        self.assertTrue(preview.accepted, preview.to_dict())
        self.assertEqual("# 课堂原始记录\n\n老师讲了合成語。\n", after_preview)
        self.assertEqual("daily_checklist_confirmation_required", blocked.errors[0].code)
        self.assertTrue(accepted.accepted, accepted.to_dict())
        self.assertEqual(["daily/2026-06-22.md"], accepted.changed_files)
        self.assertIn("老师讲了合成語。", daily_after)
        self.assertIn("## 每日学习清单", daily_after)
        self.assertIn("- 复习词汇卡 3 张", daily_after)
        self.assertIn("## 今日卡点", daily_after)
        self.assertIn("明天先做一组对比练习。", daily_after)
        self.assertEqual(card_before, card_after)

    def test_review_materials_daily_checklist_replaces_only_managed_block_and_rejects_unsafe_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            daily_path = root / "daily/2026.6.22.md"
            write(daily_path, "课堂原始内容。\n")
            first = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "daily/2026.6.22.md", "completed": ["完成第一轮复习"]},
                existing_update_confirmed=True,
                mode="apply",
            )
            second = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "daily/2026.6.22.md", "completed": ["完成第二轮复习"]},
                existing_update_confirmed=True,
                mode="apply",
            )
            text = daily_path.read_text(encoding="utf-8")
            outside = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "sources/2026-06-22.md", "completed": ["不应写入"]},
            )
            non_dated = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "daily/today.md", "completed": ["不应写入"]},
            )
            multiline = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "daily/2026.6.22.md", "reflection": "第一行\n## 注入"},
            )
            manual_path = root / "daily/2026-06-23.md"
            write(manual_path, "## 每日学习清单\n\n人工维护内容。\n")
            manual = workflows.review_materials(
                vault_root=root,
                daily_checklist={"path": "daily/2026-06-23.md", "completed": ["不应覆盖人工内容"]},
                existing_update_confirmed=True,
                mode="apply",
            )
            manual_after = manual_path.read_text(encoding="utf-8")

        self.assertTrue(first.accepted, first.to_dict())
        self.assertTrue(second.accepted, second.to_dict())
        self.assertIn("课堂原始内容。", text)
        self.assertNotIn("完成第一轮复习", text)
        self.assertIn("完成第二轮复习", text)
        self.assertEqual(1, text.count("## 每日学习清单"))
        self.assertEqual("daily_checklist_outside_role", outside.errors[0].code)
        self.assertEqual("daily_checklist_requires_dated_note", non_dated.errors[0].code)
        self.assertEqual("invalid_daily_checklist_text", multiline.errors[0].code)
        self.assertEqual("unmanaged_daily_checklist_exists", manual.errors[0].code)
        self.assertEqual("## 每日学习清单\n\n人工维护内容。\n", manual_after)

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

    def test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            write(
                focus_path,
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day180
next_review: 2026-06-21
last_reviewed:
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
accent_display: ごうせいご⓪
source_notes: [[focus-source]]
---

## Focus
合成词。
""",
            )
            write(
                base_path,
                """---
track: base_vocab
item_type: vocab
status: active
headword: 合成語
reading: ごうせいご
meaning_zh: 旧解释
source_notes: [[base-source]]
seen_count: 2
---

## 人工整理
这段必须保留。
""",
            )

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            focus_body = focus_path.read_text(encoding="utf-8")
            base_body = base_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/base/vocab/base.md", "review/focus/vocab/focus.md"], sorted(report.to_dict()["changed_files"]))
        self.assertIn("status: mastered", focus_body)
        self.assertIn("status: promoted", base_body)
        self.assertIn("meaning_zh: 合成词", base_body)
        self.assertIn("accent_display: ごうせいご⓪", base_body)
        self.assertIn('  - "[[base-source]]"', base_body)
        self.assertIn('  - "[[focus-source]]"', base_body)
        self.assertIn("seen_count: 2", base_body)
        self.assertIn("这段必须保留。", base_body)

    def test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/new-base.md"
            base_path = root / "review/base/vocab/合成語.md"
            write(
                focus_path,
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day180
next_review: 2026-06-21
last_reviewed:
headword: 合成語
reading: ごうせいご
meaning_zh: 合成词
source_notes: [[focus-source]]
---

## Focus
合成词。
""",
            )

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            focus_body = focus_path.read_text(encoding="utf-8")
            base_body = base_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/base/vocab/合成語.md", "review/focus/vocab/new-base.md"], sorted(report.to_dict()["changed_files"]))
        self.assertIn("status: mastered", focus_body)
        self.assertIn("track: base_vocab", base_body)
        self.assertIn("status: promoted", base_body)
        self.assertIn("headword: 合成語", base_body)
        self.assertIn("reading: ごうせいご", base_body)
        self.assertIn("meaning_zh: 合成词", base_body)
        self.assertIn('  - "[[focus-source]]"', base_body)

    def test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            daily_path = root / "daily/2026-06-21.md"
            daily_without_anchor_path = root / "daily/2026-06-20.md"
            write(focus_path, review_card(review_stage="day1", next_review="2026-06-21"))
            write(base_path, review_card(status="active", done_today="true", review_stage="day1", next_review="2026-06-21"))
            write(daily_path, "# Daily\n\n- manual note\n")
            write(daily_without_anchor_path, "# Daily without anchor\n")
            before_base = base_path.read_text(encoding="utf-8")
            before_daily = daily_path.read_text(encoding="utf-8")
            before_daily_without_anchor = daily_without_anchor_path.read_text(encoding="utf-8")

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            after_base = base_path.read_text(encoding="utf-8")
            after_daily = daily_path.read_text(encoding="utf-8")
            after_daily_without_anchor = daily_without_anchor_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/focus.md"], report.to_dict()["changed_files"])
        self.assertNotIn("review/base/vocab/base.md", report.to_dict()["read_files"])
        self.assertNotIn("daily/2026-06-21.md", report.to_dict()["read_files"])
        self.assertNotIn("daily/2026-06-20.md", report.to_dict()["read_files"])
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
