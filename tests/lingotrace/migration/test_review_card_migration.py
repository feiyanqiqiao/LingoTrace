from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.packs.english import workflows as english_workflows
from lingotrace.packs.japanese import workflows as japanese_workflows


PACKS = (("lingo-english", "en", english_workflows), ("lingo-japanese", "ja", japanese_workflows))


def write(path: Path, fields: dict[str, object], body: str = "Shared body.\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f'  - "{item}"' for item in value)
        elif value == "":
            lines.append(f'{key}: ""')
        else:
            lines.append(f"{key}: {value}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8")


def prepare(root: Path, pack: str, language: str) -> None:
    context = root / ".lingotrace/vault-context.json"
    context.parent.mkdir(parents=True)
    context.write_text(json.dumps({
        "vault_schema_version": 1,
        "target_language": language,
        "explanation_language": "zh",
        "language_pack": pack,
        "language_pack_version": "0.1.0",
        "enabled_capabilities": ["review_lifecycle_migration", "vocab_consolidation"],
    }), encoding="utf-8")
    (root / ".lingotrace/paths.json").write_text(json.dumps({"path_roles": [
        {"role": "focus_vocab_root", "relative_path": "review/focus/vocab", "source": "vault_config"},
        {"role": "base_vocab_root", "relative_path": "review/base/vocab", "source": "vault_config"},
        {"role": "grammar_root", "relative_path": "review/grammar", "source": "vault_config"},
        {"role": "error_root", "relative_path": "review/errors", "source": "vault_config"},
        {"role": "speaking_card_root", "relative_path": "speaking/cards", "source": "vault_config"},
        {"role": "listening_root", "relative_path": "listening", "source": "vault_config"},
        {"role": "pronunciation_accent_root", "relative_path": "review/pronunciation/accent", "source": "vault_config"},
        {"role": "pronunciation_phoneme_root", "relative_path": "review/pronunciation/phoneme", "source": "vault_config"},
    ]}), encoding="utf-8")


def queued_vocab(headword: str) -> dict[str, object]:
    return {
        "track": "class_review", "item_type": "vocab", "review_status": "queued", "done_today": False,
        "review_stage": "day3", "next_review": "2026-08-14", "last_reviewed": "2026-08-11",
        "headword": headword, "source_notes": ["[[focus-source]]"], "seen_count": 2, "error_count": 1,
        "first_seen": "2026-08-02", "last_seen": "2026-08-11",
    }


class ReviewCardMigrationTests(unittest.TestCase):
    def test_lifecycle_audit_apply_and_second_preview_are_identical_across_packs(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                write(root / "review/base/vocab/mastered.md", {"track": "base_vocab", "item_type": "vocab", "status": "promoted", "done_today": True, "review_stage": "day180", "next_review": "2026-08-14", "headword": "mastered"})
                write(root / "listening/material.md", {"track": "listening", "item_type": "listening_note", "status": "active", "done_today": False, "review_stage": "day0", "next_review": "2026-08-14", "last_reviewed": ""})
                write(root / "review/focus/vocab/queued.md", {"track": "class_review", "item_type": "vocab", "status": "active", "done_today": False, "review_stage": "day0", "next_review": "2026-08-14", "headword": "queued"})
                write(root / "review/grammar/progress.md", {"track": "class_review", "item_type": "grammar", "status": "active", "done_today": False, "review_stage": "day30", "next_review": "", "last_reviewed": "2026-07-01", "pattern": "progress"})
                write(root / "speaking/cards/backlog.md", {"track": "survival_speaking", "item_type": "speaking_card", "status": "active", "review_enabled": False, "done_today": True, "review_stage": "day30", "next_review": "2026-08-20", "last_reviewed": "2026-08-01"})

                before = {path: (root / path).read_text(encoding="utf-8") for path in (
                    "review/base/vocab/mastered.md", "listening/material.md", "review/focus/vocab/queued.md",
                    "review/grammar/progress.md", "speaking/cards/backlog.md",
                )}
                preview = workflows.review_lifecycle_migration(vault_root=root, change_date="2026-08-14")
                self.assertTrue(preview.accepted, preview.to_dict())
                self.assertEqual(5, len(preview.planned_writes))
                for relative, text in before.items():
                    self.assertEqual(text, (root / relative).read_text(encoding="utf-8"))
                applied = workflows.review_lifecycle_migration(vault_root=root, change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertTrue(applied.accepted, applied.to_dict())
                second = workflows.review_lifecycle_migration(vault_root=root, change_date="2026-08-14")
                self.assertTrue(second.accepted, second.to_dict())
                self.assertEqual([], second.planned_writes)
                self.assertIn("review_status: mastered", (root / "review/base/vocab/mastered.md").read_text(encoding="utf-8"))
                self.assertIn("review_status: backlog", (root / "listening/material.md").read_text(encoding="utf-8"))
                self.assertIn("review_status: queued", (root / "review/focus/vocab/queued.md").read_text(encoding="utf-8"))
                grammar = (root / "review/grammar/progress.md").read_text(encoding="utf-8")
                self.assertIn("review_status: queued", grammar)
                self.assertIn("next_review: 2026-08-14", grammar)
                backlog = (root / "speaking/cards/backlog.md").read_text(encoding="utf-8")
                self.assertIn("review_status: backlog", backlog)
                self.assertIn("review_stage: day30", backlog)
                self.assertNotIn("review_enabled:", backlog)

    def test_vocab_consolidation_handles_base_only_duplicates_metadata_and_old_links(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                write(root / "review/base/vocab/backlog.md", {"track": "base_vocab", "item_type": "vocab", "review_status": "backlog", "done_today": False, "review_stage": "", "next_review": "", "headword": "backlog"})
                write(root / "review/base/vocab/mastered.md", {"track": "base_vocab", "item_type": "vocab", "review_status": "mastered", "done_today": False, "review_stage": "mastered", "next_review": "", "headword": "mastered"})
                write(root / "review/base/vocab/queued.md", {"track": "base_vocab", "item_type": "vocab", "review_status": "queued", "done_today": False, "review_stage": "day30", "next_review": "2026-08-20", "headword": "queued"})
                focus_fields = queued_vocab("duplicate")
                write(root / "review/focus/vocab/duplicate.md", focus_fields)
                write(root / "review/base/vocab/duplicate.md", {
                    "track": "base_vocab", "item_type": "vocab", "review_status": "backlog", "done_today": False,
                    "review_stage": "", "next_review": "", "headword": "duplicate", "meaning_zh": "base fill",
                    "source_notes": "[[base-source]]", "seen_count": 8, "error_count": 0,
                    "first_seen": "2026-07-01", "last_seen": "2026-08-12",
                })
                write(root / "review/focus/vocab/focus-only.md", queued_vocab("focus-only"), "Focus only.\n")
                focus_only_before = (root / "review/focus/vocab/focus-only.md").read_text(encoding="utf-8")

                preview = workflows.vocab_consolidation(vault_root=root, change_date="2026-08-14")
                self.assertTrue(preview.accepted, preview.to_dict())
                applied = workflows.vocab_consolidation(vault_root=root, change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertTrue(applied.accepted, applied.to_dict())
                second = workflows.vocab_consolidation(vault_root=root, change_date="2026-08-14")
                self.assertTrue(second.accepted, second.to_dict())
                self.assertEqual([], second.planned_writes)
                self.assertIn("review_status: backlog", (root / "review/focus/vocab/backlog.md").read_text(encoding="utf-8"))
                self.assertIn("review_status: mastered", (root / "review/focus/vocab/mastered.md").read_text(encoding="utf-8"))
                self.assertIn("review_status: queued", (root / "review/focus/vocab/queued.md").read_text(encoding="utf-8"))
                duplicate = (root / "review/focus/vocab/duplicate.md").read_text(encoding="utf-8")
                self.assertIn("meaning_zh: base fill", duplicate)
                self.assertIn('  - "[[focus-source]]"', duplicate)
                self.assertIn('  - "[[base-source]]"', duplicate)
                self.assertIn("seen_count: 8", duplicate)
                self.assertIn("first_seen: 2026-07-01", duplicate)
                self.assertIn("last_seen: 2026-08-12", duplicate)
                old_base = (root / "review/base/vocab/duplicate.md").read_text(encoding="utf-8")
                self.assertIn("review_status: archived", old_base)
                self.assertIn("canonical_card:", old_base)
                self.assertIn("[[review/focus/vocab/duplicate|规范卡]]", old_base)
                self.assertEqual(focus_only_before, (root / "review/focus/vocab/focus-only.md").read_text(encoding="utf-8"))

    def test_different_manual_bodies_block_the_entire_consolidation_batch(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                write(root / "review/focus/vocab/conflict.md", queued_vocab("conflict"), "Focus manual body.\n")
                write(root / "review/base/vocab/conflict.md", {"track": "base_vocab", "item_type": "vocab", "review_status": "backlog", "done_today": False, "review_stage": "", "next_review": "", "headword": "conflict"}, "Base manual body.\n")
                write(root / "review/base/vocab/otherwise.md", {"track": "base_vocab", "item_type": "vocab", "review_status": "backlog", "done_today": False, "review_stage": "", "next_review": "", "headword": "otherwise"})
                before = (root / "review/base/vocab/otherwise.md").read_text(encoding="utf-8")
                report = workflows.vocab_consolidation(vault_root=root, change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertFalse(report.accepted)
                self.assertEqual("manual_vocab_body_conflict", report.errors[0].code)
                self.assertFalse((root / "review/focus/vocab/otherwise.md").exists())
                self.assertEqual(before, (root / "review/base/vocab/otherwise.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
