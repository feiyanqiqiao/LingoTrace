from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.packs.english import workflows as english_workflows
from lingotrace.packs.japanese import workflows as japanese_workflows


PACKS = (("lingo-english", "en", english_workflows), ("lingo-japanese", "ja", japanese_workflows))


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def prepare(root: Path, pack: str, language: str) -> None:
    write(root / ".lingotrace/vault-context.json", json.dumps({
        "vault_schema_version": 1,
        "target_language": language,
        "explanation_language": "zh",
        "language_pack": pack,
        "language_pack_version": "0.1.0",
        "enabled_capabilities": ["review_queue", "review_materials", "listening_notes", "speaking_cards"],
    }))
    write(root / ".lingotrace/paths.json", json.dumps({"path_roles": [
        {"role": "focus_vocab_root", "relative_path": "review/focus/vocab", "source": "vault_config"},
        {"role": "grammar_root", "relative_path": "review/grammar", "source": "vault_config"},
        {"role": "error_root", "relative_path": "review/errors", "source": "vault_config"},
        {"role": "speaking_card_root", "relative_path": "speaking/cards", "source": "vault_config"},
        {"role": "listening_root", "relative_path": "listening", "source": "vault_config"},
        {"role": "pronunciation_accent_root", "relative_path": "review/pronunciation/accent", "source": "vault_config"},
        {"role": "pronunciation_phoneme_root", "relative_path": "review/pronunciation/phoneme", "source": "vault_config"},
    ]}))


def card(status: str, stage: str = "", next_review: str = "", last_reviewed: str = "") -> str:
    return f"---\nreview_status: {status}\ndone_today: false\nreview_stage: {stage}\nnext_review: {next_review}\nlast_reviewed: {last_reviewed}\n---\n\nManual body.\n"


class ReviewQueueParityTests(unittest.TestCase):
    def test_listening_speaking_and_chunk_creation_default_to_backlog_in_both_packs(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                listening = workflows.listening_notes(
                    vault_root=root,
                    input_artifact={"path": "listening/new.md", "body": "# New listening\n"},
                    mode="apply",
                )
                speaking = workflows.speaking_cards(
                    vault_root=root,
                    candidate={
                        "path": "speaking/cards/new.md",
                        "body": "---\ntrack: survival_speaking\nitem_type: speaking_card\n---\n\nUseful line.\n",
                        "reviewed": True,
                    },
                    mode="apply",
                )
                chunk = workflows.speaking_cards(
                    vault_root=root,
                    candidate={
                        "path": "speaking/cards/chunk.md",
                        "body": "---\ntrack: survival_speaking\nitem_type: chunk\nchunk_pattern: reusable pattern\n---\n\nUseful chunk.\n",
                        "reviewed": True,
                    },
                    mode="apply",
                )
                for report in (listening, speaking, chunk):
                    self.assertTrue(report.accepted, report.to_dict())
                for relative in ("listening/new.md", "speaking/cards/new.md", "speaking/cards/chunk.md"):
                    body = (root / relative).read_text(encoding="utf-8")
                    self.assertIn("review_status: backlog", body)
                    self.assertIn("done_today: false", body)
                    self.assertIn('review_stage: ""', body)

    def test_resume_exit_and_restart_are_supported_by_both_packs(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                path = root / "speaking/cards/item.md"
                write(path, card("backlog", "day30", "2026-07-01", "2026-06-01"))
                resumed = workflows.review_queue(vault_root=root, items=[{"path": "speaking/cards/item.md", "target_status": "queued", "activation": "resume"}], change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertTrue(resumed.accepted, resumed.to_dict())
                self.assertIn("review_stage: day30", path.read_text(encoding="utf-8"))
                exited = workflows.review_queue(vault_root=root, items=[{"path": "speaking/cards/item.md", "target_status": "backlog"}], change_date="2026-08-15", existing_update_confirmed=True, mode="apply")
                self.assertTrue(exited.accepted, exited.to_dict())
                body = path.read_text(encoding="utf-8")
                self.assertIn("review_status: backlog", body)
                self.assertIn("review_stage: day30", body)
                restarted = workflows.review_queue(vault_root=root, items=[{"path": "speaking/cards/item.md", "target_status": "queued", "activation": "restart"}], change_date="2026-08-16", existing_update_confirmed=True, mode="apply")
                self.assertTrue(restarted.accepted, restarted.to_dict())
                body = path.read_text(encoding="utf-8")
                self.assertIn("review_stage: day0", body)
                self.assertIn("next_review: 2026-08-16", body)
                self.assertIn('last_reviewed: ""', body)

    def test_invalid_batch_is_atomic_for_both_packs(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                first = root / "speaking/cards/first.md"
                write(first, card("backlog"))
                before = first.read_text(encoding="utf-8")
                report = workflows.review_queue(vault_root=root, items=[
                    {"path": "speaking/cards/first.md", "target_status": "queued", "activation": "resume"},
                    {"path": "speaking/cards/missing.md", "target_status": "queued", "activation": "resume"},
                ], change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertFalse(report.accepted)
                self.assertEqual(before, first.read_text(encoding="utf-8"))

    def test_mastered_material_requires_explicit_restart_in_both_packs(self) -> None:
        for pack, language, workflows in PACKS:
            with self.subTest(pack=pack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepare(root, pack, language)
                path = root / "review/focus/vocab/mastered.md"
                write(path, card("mastered", "mastered", "", "2026-08-01"))
                blocked = workflows.review_queue(vault_root=root, items=[{
                    "path": "review/focus/vocab/mastered.md", "target_status": "queued", "activation": "resume"
                }], change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertFalse(blocked.accepted)
                self.assertEqual("mastered_restart_required", blocked.errors[0].code)
                applied = workflows.review_queue(vault_root=root, items=[{
                    "path": "review/focus/vocab/mastered.md", "target_status": "queued", "activation": "restart"
                }], change_date="2026-08-14", existing_update_confirmed=True, mode="apply")
                self.assertTrue(applied.accepted, applied.to_dict())
                body = path.read_text(encoding="utf-8")
                self.assertIn("review_status: queued", body)
                self.assertIn("review_stage: day0", body)


if __name__ == "__main__":
    unittest.main()
