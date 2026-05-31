import importlib.util
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_next_day_review.py"
SPEC = importlib.util.spec_from_file_location("update_next_day_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class UpdateNextDayReviewTests(unittest.TestCase):
    def test_class_review_track_is_presented_as_focus_review(self) -> None:
        self.assertEqual(MODULE.TRACK_LABELS["class_review"], "重点复习")

    def base_vocab_root(self, vault_root: Path) -> Path:
        return vault_root / "base-vocab"

    def focus_vocab_path(self, vault_root: Path, name: str) -> Path:
        return vault_root / "focus-vocab" / name

    def test_base_note_path_uses_focus_card_stem_not_raw_headword(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_root = Path(tmp_dir)
            focus_path = self.focus_vocab_path(vault_root, "廢棄與處理.md")
            new_text = "\n".join(
                [
                    "---",
                    "track: class_review",
                    "item_type: vocab",
                    "status: mastered",
                    "priority: normal",
                    "done_today: false",
                    "headword: 廢棄與處理 (捨てる / 廃棄 / 処分)",
                    "reading: すてる / はいき / しょぶん",
                    "meaning_zh: 丢弃、废弃、处理",
                    "source_notes:",
                    '  - "[[笔记/2026.4/2026.4.28]]"',
                    "first_seen: 2026-04-28",
                    "last_seen: 2026-04-29",
                    "seen_count: 3",
                    "error_count: 0",
                    "review_stage: mastered",
                    "next_review:",
                    "last_reviewed: 2026-04-29",
                    "tags:",
                    "  - jp/vocab",
                    "---",
                    "",
                    "# 廢棄與處理",
                    "",
                ]
            )
            item = MODULE.ItemState(
                path=focus_path,
                text=new_text,
                status="mastered",
                item_type="vocab",
                done_today=False,
                review_stage="mastered",
                next_review=None,
                last_reviewed_raw="2026-04-29",
                first_seen=date(2026, 4, 28),
                track="class_review",
                label="廢棄與處理",
                new_text=new_text,
            )

            pending = MODULE.build_base_note_write(self.base_vocab_root(vault_root), item)

        self.assertEqual(
            pending.path,
            vault_root / "base-vocab/廢棄與處理.md",
        )
        self.assertIn("headword: 廢棄與處理 (捨てる / 廃棄 / 処分)", pending.text)
        self.assertIn("aliases:\n- \"廢棄與處理 (捨てる / 廃棄 / 処分)\"", pending.text)
        self.assertIn("# 廢棄與處理", pending.text)

    def test_existing_base_note_empty_aliases_gets_headword_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_root = Path(tmp_dir)
            base_path = self.base_vocab_root(vault_root) / "廢棄與處理.md"
            base_path.parent.mkdir(parents=True)
            base_path.write_text(
                "\n".join(
                    [
                        "---",
                        "headword: 廢棄與處理",
                        "aliases: []",
                        "reading: はいき",
                        "meaning_zh: 废弃",
                        "source_notes:",
                        '  - "[[笔记/2026.4/2026.4.14]]"',
                        "first_seen: 2026-04-14",
                        "last_seen: 2026-04-14",
                        "seen_count: 1",
                        "status: promoted",
                        "promote_candidate: false",
                        "tags:",
                        "  - jp/vocab",
                        "---",
                        "",
                        "# 廢棄與處理",
                        "",
                        "## 来源",
                        "",
                        "- [[笔记/2026.4/2026.4.14]]",
                        "",
                    ]
                )
            )
            focus_path = self.focus_vocab_path(vault_root, "廢棄與處理.md")
            new_text = "\n".join(
                [
                    "---",
                    "headword: 廢棄與處理 (捨てる / 廃棄 / 処分)",
                    "reading: すてる / はいき / しょぶん",
                    "meaning_zh: 丢弃、废弃、处理",
                    "source_notes:",
                    '  - "[[笔记/2026.4/2026.4.28]]"',
                    "first_seen: 2026-04-28",
                    "last_seen: 2026-04-29",
                    "seen_count: 3",
                    "---",
                    "",
                ]
            )
            item = MODULE.ItemState(
                path=focus_path,
                text=new_text,
                status="mastered",
                item_type="vocab",
                done_today=False,
                review_stage="mastered",
                next_review=None,
                last_reviewed_raw="2026-04-29",
                first_seen=date(2026, 4, 28),
                track="class_review",
                label="廢棄與處理",
                new_text=new_text,
            )

            pending = MODULE.build_base_note_write(self.base_vocab_root(vault_root), item)

        self.assertIn("aliases:\n- \"廢棄與處理 (捨てる / 廃棄 / 処分)\"", pending.text)
        self.assertNotIn("aliases: []", pending.text)

    def test_base_note_sink_preserves_kanji_diff_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_root = Path(tmp_dir)
            focus_path = self.focus_vocab_path(vault_root, "江戸.md")
            new_text = "\n".join(
                [
                    "---",
                    "track: class_review",
                    "item_type: vocab",
                    "status: mastered",
                    "done_today: false",
                    "headword: 江戸",
                    "reading: えど",
                    "meaning_zh: 江户",
                    "source_notes:",
                    '  - "[[笔记/2026.4/2026.4.28]]"',
                    "first_seen: 2026-04-28",
                    "last_seen: 2026-04-29",
                    "seen_count: 2",
                    "review_stage: mastered",
                    "next_review:",
                    "last_reviewed: 2026-04-29",
                    "kanji_diff: true",
                    "kanji_diff_pairs:",
                    "  - 戸/户",
                    "tags:",
                    "  - jp/vocab",
                    "  - jp/class_review",
                    "  - jp/kanji_diff",
                    "---",
                    "",
                ]
            )
            item = MODULE.ItemState(
                path=focus_path,
                text=new_text,
                status="mastered",
                item_type="vocab",
                done_today=False,
                review_stage="mastered",
                next_review=None,
                last_reviewed_raw="2026-04-29",
                first_seen=date(2026, 4, 28),
                track="class_review",
                label="江戸",
                new_text=new_text,
            )

            pending = MODULE.build_base_note_write(self.base_vocab_root(vault_root), item)

        self.assertIn("kanji_diff: true", pending.text)
        self.assertIn("kanji_diff_pairs:\n- 戸/户", pending.text)
        self.assertIn("- jp/kanji_diff", pending.text)

    def test_traditional_checklist_marker_is_rewritten_once(self) -> None:
        original = "\n".join(
            [
                "# 2026.4.27",
                "",
                "## 學習紀錄",
                "",
                "人工內容",
                "",
                "## 每日學習清單",
                "",
                "## 今日完成",
                "",
                "## 今日卡點",
                "",
                "- 手動卡點",
                "",
                "## 簡短複盤",
                "",
                "- 舊複盤",
                "",
            ]
        )

        updated = MODULE.build_checklist_section(
            Path("笔记/2026.4/2026.4.27.md"),
            original,
            [],
            [],
            {},
            {track: 0 for track in MODULE.TRACK_LABELS},
            0,
            date(2026, 4, 27),
        )

        self.assertEqual(updated.count("## 每日学习清单"), 1)
        self.assertNotIn("## 每日學習清單", updated)
        self.assertIn("- 手動卡點", updated)
        self.assertIn("人工內容", updated)

    def test_update_body_sources_preserves_following_sections(self) -> None:
        original = "\n".join(
            [
                "---",
                "headword: 例",
                "---",
                "",
                "# 例",
                "",
                "## 来源",
                "",
                "- [[笔记/2026.4/2026.4.14]]",
                "",
                "## 来源摘录",
                "",
                "- 人工整理した例文。",
                "",
                "## 核心",
                "",
                "手工补充内容。",
                "",
            ]
        )

        updated = MODULE.update_body_sources(
            original,
            [
                "[[笔记/2026.4/2026.4.14]]",
                "[[笔记/2026.4/2026.4.28]]",
            ],
        )

        self.assertIn("- [[笔记/2026.4/2026.4.28]]", updated)
        self.assertIn("## 来源摘录", updated)
        self.assertIn("- 人工整理した例文。", updated)
        self.assertIn("## 核心", updated)
        self.assertIn("手工补充内容。", updated)
        self.assertLess(updated.index("## 来源"), updated.index("## 来源摘录"))


if __name__ == "__main__":
    unittest.main()
