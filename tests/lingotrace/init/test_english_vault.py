from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.init.english_vault import plan_english_vault_initialization


class EnglishVaultInitializationTests(unittest.TestCase):
    def test_empty_target_plans_a_complete_english_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = plan_english_vault_initialization(root)
            self.assertEqual([], list(root.rglob("*")))
        envelope = report.to_dict()
        planned = {entry["path"]: entry for entry in envelope["planned_writes"]}
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("init-english-vault", envelope["command"])
        context = planned[".lingotrace/vault-context.json"]["content"]
        self.assertEqual("en", context["target_language"])
        self.assertEqual("lingo-english", context["language_pack"])
        self.assertEqual(["listening_notes", "source_notes", "review_materials", "speaking_cards", "review_rollover", "total_training_dashboard"], context["enabled_capabilities"])
        for path in ("templates/focus-vocab-card.md", "templates/grammar-card.md", "templates/error-card.md", "templates/speaking-card.md", "templates/chunk-card.md", "views/total-training.base"):
            self.assertIn(path, planned)

    def test_existing_context_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / ".lingotrace/vault-context.json"
            context.parent.mkdir(parents=True)
            context.write_text("manual", encoding="utf-8")
            report = plan_english_vault_initialization(root)
        self.assertFalse(report.accepted)
        self.assertIn(".lingotrace/vault-context.json", report.blocked_files)


if __name__ == "__main__":
    unittest.main()
