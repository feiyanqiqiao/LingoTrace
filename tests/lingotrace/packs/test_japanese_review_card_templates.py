from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from lingotrace.packs.japanese import workflows


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "review_cards"


def write(path: Path, content: str = "# fixture\n") -> None:
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
                "enabled_capabilities": ["review_materials", "review_rollover"],
            }
        ),
    )
    write(
        root / ".lingotrace/paths.json",
        json.dumps(
            {
                "path_roles": [
                    {"role": "focus_vocab_root", "relative_path": "review/focus/vocab"},
                    {"role": "base_vocab_root", "relative_path": "review/base/vocab"},
                    {"role": "grammar_root", "relative_path": "review/grammar"},
                    {"role": "error_root", "relative_path": "review/errors"},
                    {"role": "pronunciation_accent_root", "relative_path": "review/pronunciation/accent"},
                    {"role": "pronunciation_phoneme_root", "relative_path": "review/pronunciation/phoneme"},
                    {"role": "source_notes_root", "relative_path": "sources"},
                    {"role": "daily_notes_root", "relative_path": "daily"},
                ]
            }
        ),
    )


def apply_item(root: Path, item: dict[str, object], *, date: str = "2026-07-14") -> tuple[object, str, Path]:
    report = workflows.review_materials(vault_root=root, item=item, extraction_date=date, mode="apply")
    if not report.accepted:
        raise AssertionError(report.to_dict())
    path = root / report.changed_files[0]
    text = path.read_text(encoding="utf-8")
    _, body = workflows._frontmatter_and_body(text)
    return report, body.rstrip(), path


def complete_vocab_fields(*, source_notes: list[str] | None = None) -> dict[str, object]:
    return {
        "track": "class_review",
        "item_type": "vocab",
        "status": "active",
        "priority": "normal",
        "done_today": False,
        "headword": "自身",
        "reading": "じしん",
        "meaning_zh": "自身",
        "source_notes": source_notes or [],
        "first_seen": "2026-07-14",
        "last_seen": "2026-07-14",
        "seen_count": 1,
        "error_count": 0,
        "review_stage": "day0",
        "next_review": "2026-07-14",
        "last_reviewed": "",
        "tags": ["jp/vocab", "jp/class_review"],
    }


class JapaneseReviewCardTemplateTests(unittest.TestCase):
    def test_vocab_grammar_and_error_bodies_match_golden_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "daily/2026.7.14.md")
            write(root / "review/focus/vocab/零れる.md")
            write(root / "review/grammar/〜らしい.md")
            write(root / "review/grammar/〜も同然だ.md")

            _, vocab_body, vocab_path = apply_item(
                root,
                {
                    "item_type": "vocab",
                    "headword": "溢れる",
                    "reading": "あふれる",
                    "accent_display": "あふれ＼る",
                    "accent_label": "③",
                    "meaning_zh": "溢出、充满、洋溢",
                    "part_of_speech": "动词 (自一)",
                    "collocations": ["魅力があふれる (充满魅力)"],
                    "examples": [
                        {
                            "jp": "就職の時期になると、濃紺や黒、グレーのスーツの学生たちがあふれる。",
                            "zh": "到了求职季节，满街都是穿着深蓝色、黑色和灰色西装的学生。",
                        }
                    ],
                    "confusable_with": ["零れる"],
                    "source_note": "daily/2026.7.14.md",
                },
            )
            _, grammar_body, grammar_path = apply_item(
                root,
                {
                    "item_type": "grammar",
                    "pattern": "〜ようだ",
                    "meaning_zh": "好像……；像……一样",
                    "formation": ["V普通形 + ようだ", "Nの + ようだ"],
                    "core_nuance": "基于感官迹象进行主观推测，也可表示比喻。",
                    "typical_example_jp": "彼はまるで子供のようだ。",
                    "register": "较正式；口语常用「〜みたいだ」。",
                    "usage_scenes": ["感官推断", "比喻"],
                    "jlpt": "N3",
                    "usage_sections": [
                        {
                            "title": "主观推测",
                            "formation": ["V普通形 + ようだ"],
                            "nuance": "根据眼前迹象作出判断。",
                            "examples": [
                                {"jp": "誰もいないようだ。", "zh": "好像没有人。"},
                                "どうやら風邪をひいたようだ。",
                            ],
                        },
                        {
                            "title": "比喻",
                            "formation": ["Nの + ようだ"],
                            "nuance": "实际上不是，但状态很相似。",
                            "examples": ["彼の心は氷のように冷たい。"],
                        },
                    ],
                    "contrast_with": ["〜らしい"],
                    "confusion_notes": ["名词前需要「の」。"],
                },
            )
            _, error_body, error_path = apply_item(
                root,
                {
                    "item_type": "error",
                    "correct_form": "その態度は嫌だと言っているのも同然だ。",
                    "wrong_form": "その態度は嫌だと言っているのと同然だ。",
                    "wrong_focus": "と同然だ",
                    "correct_focus": "のも同然だ",
                    "reason": "固定语法是「〜も同然だ」，不能写成「〜と同然だ」。",
                    "avoidance": "把「〜も同然だ」作为固定结构整体记忆。",
                    "related_items": ["〜も同然だ"],
                    "source_note": "daily/2026.7.14",
                },
            )

            self.assertEqual((FIXTURE_ROOT / "vocab-body.md").read_text(encoding="utf-8").rstrip(), vocab_body)
            self.assertEqual((FIXTURE_ROOT / "grammar-body.md").read_text(encoding="utf-8").rstrip(), grammar_body)
            self.assertEqual((FIXTURE_ROOT / "error-body.md").read_text(encoding="utf-8").rstrip(), error_body)
            self.assertEqual("2026-07-14_その態度は嫌だと言っているのも同然だ。.md", error_path.name)

            for card_path in (vocab_path, grammar_path, error_path):
                for target in re.findall(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", card_path.read_text(encoding="utf-8")):
                    self.assertTrue((root / f"{target}.md").is_file(), target)

    def test_optional_sections_are_omitted_when_no_reliable_content_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            _, body, _ = apply_item(
                root,
                {
                    "item_type": "vocab",
                    "headword": "静か",
                    "reading": "しずか",
                    "meaning_zh": "安静",
                },
            )

        self.assertIn("## 快速复习", body)
        self.assertNotIn("## 核心", body)
        self.assertNotIn("## 例句", body)
        self.assertNotRegex(body, r"(?m)^## .+\n\n(?=##|$)")

    def test_empty_grammar_usage_branches_fall_back_without_empty_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            _, body, _ = apply_item(
                root,
                {
                    "item_type": "grammar",
                    "pattern": "〜ようだ",
                    "meaning_zh": "好像",
                    "formation": ["V普通形 + ようだ"],
                    "usage_sections": [{}, {"title": "空分支"}],
                },
            )

        self.assertIn("### 1. 基本用法", body)
        self.assertIn("- 接续：V普通形 + ようだ", body)
        self.assertNotIn("### 1. 用法 1", body)
        self.assertNotIn("空分支", body)
        self.assertNotRegex(body, r"(?m)^### .+\n(?=\n(?:###|##|$))")

    def test_source_links_must_resolve_uniquely_inside_source_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            base_item = {"item_type": "vocab", "headword": "合成語", "reading": "ごうせいご", "meaning_zh": "合成词"}

            missing = workflows.review_materials(vault_root=root, item={**base_item, "source_note": "missing"})
            write(root / "sources/a/lesson.md")
            write(root / "daily/b/lesson.md")
            ambiguous = workflows.review_materials(vault_root=root, item={**base_item, "source_note": "lesson"})
            outside = workflows.review_materials(vault_root=root, item={**base_item, "source_note": "review/grammar/x"})
            malformed = workflows.review_materials(vault_root=root, item={**base_item, "source_note": "[[lesson"})
            multiline_alias = workflows.review_materials(
                vault_root=root,
                item={**base_item, "source_note": "[[sources/a/lesson|alias\n## injected]]"},
            )

        self.assertEqual("missing_source_note_target", missing.errors[0].code)
        self.assertEqual("ambiguous_source_note_target", ambiguous.errors[0].code)
        self.assertEqual("source_note_outside_role", outside.errors[0].code)
        self.assertEqual("invalid_source_note_link", malformed.errors[0].code)
        self.assertEqual("invalid_source_note_link", multiline_alias.errors[0].code)

    def test_missing_or_ambiguous_optional_relations_remain_plain_text_and_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "review/grammar/a/〜らしい.md")
            write(root / "review/grammar/b/〜らしい.md")
            report, body, _ = apply_item(
                root,
                {
                    "item_type": "grammar",
                    "pattern": "〜ようだ",
                    "meaning_zh": "好像",
                    "formation": ["V普通形 + ようだ"],
                    "contrast_with": ["〜らしい", "〜みたいだ"],
                },
            )

        self.assertEqual(2, len(report.warnings))
        self.assertEqual('["〜らしい", "〜みたいだ"]', report.artifacts["unresolved_related_items"])
        self.assertIn("- 〜らしい", body)
        self.assertIn("- 〜みたいだ", body)
        self.assertNotIn("[[〜らしい]]", body)
        self.assertNotIn("[[〜みたいだ]]", body)

    def test_existing_cards_require_confirmation_and_keep_manual_semantic_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/合成語.md"
            write(
                card_path,
                """---
track: class_review
item_type: vocab
status: active
headword: 合成語
meaning_zh: 人工释义
source_notes: []
review_stage: day3
next_review: 2026-07-20
---

## 人工整理
这段不能被结构化 item 覆盖。
""",
            )
            item = {"item_type": "vocab", "headword": "合成語", "reading": "ごうせいご", "meaning_zh": "新释义"}
            blocked = workflows.review_materials(vault_root=root, item=item, extraction_date="2026-07-14", mode="apply")
            unchanged = card_path.read_text(encoding="utf-8")
            accepted = workflows.review_materials(
                vault_root=root,
                item=item,
                extraction_date="2026-07-14",
                existing_update_confirmed=True,
                mode="apply",
            )
            updated = card_path.read_text(encoding="utf-8")

        self.assertEqual("existing_review_material_confirmation_required", blocked.errors[0].code)
        self.assertIn("meaning_zh: 人工释义", unchanged)
        self.assertTrue(accepted.accepted, accepted.to_dict())
        self.assertIn("meaning_zh: 人工释义", updated)
        self.assertNotIn("新释义", updated)
        self.assertIn("这段不能被结构化 item 覆盖。", updated)

    def test_confirmed_full_card_payload_can_replace_one_existing_body_but_not_escape_review_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/自身.md"
            write(card_path, "old body\n")
            payload = {
                "path": "review/focus/vocab/自身.md",
                "body": "## 新正文\n\n明确确认后可以重排。",
                "fields": complete_vocab_fields(),
            }
            blocked = workflows.review_materials(vault_root=root, card=payload, mode="apply")
            accepted = workflows.review_materials(
                vault_root=root,
                card=payload,
                existing_update_confirmed=True,
                mode="apply",
            )
            replaced_text = card_path.read_text(encoding="utf-8")
            outside = workflows.review_materials(
                vault_root=root,
                card={**payload, "path": "sources/自身.md"},
            )

        self.assertEqual("existing_review_material_confirmation_required", blocked.errors[0].code)
        self.assertTrue(accepted.accepted, accepted.to_dict())
        self.assertIn("明确确认后可以重排。", replaced_text)
        self.assertEqual("review_card_outside_role", outside.errors[0].code)

    def test_full_card_payload_rejects_traversal_empty_body_and_oversized_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            payload = {
                "path": "review/focus/vocab/自身.md",
                "body": "## 自身\n\n可复习正文。",
                "fields": complete_vocab_fields(),
            }
            traversal = workflows.review_materials(
                vault_root=root,
                card={**payload, "path": "review/focus/vocab/../../../sources/自身.md"},
            )
            empty_body = workflows.review_materials(vault_root=root, card={**payload, "body": "  \n"})
            oversized = workflows.review_materials(
                vault_root=root,
                card={**payload, "path": f"review/focus/vocab/{'長' * 300}.md"},
            )

        self.assertEqual("invalid_review_card_path", traversal.errors[0].code)
        self.assertEqual("invalid_review_card_body", empty_body.errors[0].code)
        self.assertEqual("review_card_filename_too_long", oversized.errors[0].code)

    def test_full_card_payload_keeps_unresolved_relations_as_plain_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            report = workflows.review_materials(
                vault_root=root,
                card={
                    "path": "review/grammar/〜ようだ.md",
                    "body": "# 〜ようだ\n\n## 核心\n\n好像。",
                    "fields": {
                        "track": "class_review",
                        "item_type": "grammar",
                        "status": "active",
                        "priority": "normal",
                        "done_today": False,
                        "pattern": "〜ようだ",
                        "meaning_zh": "好像",
                        "formation": ["V普通形 + ようだ"],
                        "source_notes": [],
                        "first_seen": "2026-07-14",
                        "last_seen": "2026-07-14",
                        "seen_count": 1,
                        "error_count": 0,
                        "review_stage": "day0",
                        "next_review": "2026-07-14",
                        "last_reviewed": "",
                        "contrast_with": ["〜みたいだ"],
                        "tags": ["jp/grammar", "jp/class_review"],
                    },
                },
                mode="apply",
            )
            text = (root / "review/grammar/〜ようだ.md").read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual('["〜みたいだ"]', report.artifacts["unresolved_related_items"])
        self.assertIn("## 待补卡\n\n- 〜みたいだ", text)
        self.assertNotIn("[[〜みたいだ]]", text)

    def test_yaml_round_trip_preserves_special_text_and_typed_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "daily/injection.md")
            report, _, path = apply_item(
                root,
                {
                    "item_type": "vocab",
                    "headword": "記号語",
                    "reading": "きごうご",
                    "meaning_zh": '值: [测试] "引号"\n---\n不是新 frontmatter',
                    "collocations": ["A: B", "[括号]", "日文・符号"],
                    "source_note": "[[daily/injection.md|注入: 来源]]",
                },
            )
            text = path.read_text(encoding="utf-8")
            fields, _ = workflows._frontmatter_and_body(text)

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual('值: [测试] "引号"\n---\n不是新 frontmatter', fields["meaning_zh"])
        self.assertEqual(["A: B", "[括号]", "日文・符号"], fields["collocations"])
        self.assertEqual(["[[daily/injection|注入: 来源]]"], fields["source_notes"])
        self.assertEqual(2, text.count("\n---\n"))

    def test_yaml_round_trip_preserves_numeric_and_implicit_scalar_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            report, _, path = apply_item(
                root,
                {
                    "item_type": "vocab",
                    "headword": "数字語",
                    "reading": "123",
                    "meaning_zh": "01",
                    "collocations": ["yes", "1.2", "1e3", "2026-07-15"],
                },
            )
            text = path.read_text(encoding="utf-8")
            fields, _ = workflows._frontmatter_and_body(text)

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("123", fields["reading"])
        self.assertEqual("01", fields["meaning_zh"])
        self.assertEqual(["yes", "1.2", "1e3", "2026-07-15"], fields["collocations"])
        self.assertIn('reading: "123"', text)
        self.assertIn('meaning_zh: "01"', text)
        self.assertIn('  - "yes"', text)

    def test_long_error_sentence_uses_bounded_filename_without_losing_display_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            correct_form = "長" * 300
            report, body, path = apply_item(
                root,
                {
                    "item_type": "error",
                    "wrong_form": "短い誤文",
                    "correct_form": correct_form,
                    "reason": "理由",
                    "avoidance": "方法",
                },
            )
            fields, _ = workflows._frontmatter_and_body(path.read_text(encoding="utf-8"))

        self.assertTrue(report.accepted, report.to_dict())
        self.assertLessEqual(len(path.name.encode("utf-8")), 255)
        self.assertEqual(correct_form, fields["correct_form"])
        self.assertIn(correct_form, body)
        self.assertRegex(path.stem, r"^2026-07-14_.+-[0-9a-f]{10}$")

    def test_reserved_filename_characters_and_non_unique_error_focus_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            unsafe = workflows.review_materials(
                vault_root=root,
                item={"item_type": "vocab", "headword": "危険#語", "reading": "きけんご", "meaning_zh": "危险词"},
            )
            control = workflows.review_materials(
                vault_root=root,
                item={"item_type": "vocab", "headword": "危険\0語", "reading": "きけんご", "meaning_zh": "危险词"},
            )
            focus = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "error",
                    "wrong_form": "同じ同じ",
                    "correct_form": "同じ",
                    "wrong_focus": "同じ",
                    "reason": "重复。",
                    "avoidance": "只写一次。",
                },
            )

        self.assertEqual("unsafe_review_item_title", unsafe.errors[0].code)
        self.assertEqual("unsafe_review_item_title", control.errors[0].code)
        self.assertEqual("invalid_error_focus", focus.errors[0].code)

    def test_source_self_link_is_blocked_when_roles_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            paths_path = root / ".lingotrace/paths.json"
            paths = json.loads(paths_path.read_text(encoding="utf-8"))
            for role in paths["path_roles"]:
                if role["role"] == "source_notes_root":
                    role["relative_path"] = "review/focus/vocab"
            paths_path.write_text(json.dumps(paths), encoding="utf-8")
            write(root / "review/focus/vocab/自身.md")
            report = workflows.review_materials(
                vault_root=root,
                card={
                    "path": "review/focus/vocab/自身.md",
                    "body": "## 自身",
                    "fields": complete_vocab_fields(source_notes=["review/focus/vocab/自身"]),
                },
            )

        self.assertEqual("self_referential_source_note", report.errors[0].code)


if __name__ == "__main__":
    unittest.main()
