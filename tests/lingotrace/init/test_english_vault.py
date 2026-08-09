from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.english_vault import initialize_english_vault, plan_english_vault_initialization
from lingotrace.init.listenkit_connections import listenkit_connection_relative_path
from lingotrace.init.runtime_connections import current_platform, runtime_connection_relative_path


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
        self.assertEqual(
            [
                "listening_notes",
                "source_notes",
                "review_materials",
                "speaking_cards",
                "review_rollover",
                "total_training_dashboard",
            ],
            context["enabled_capabilities"],
        )
        for path in (
            "templates/focus-vocab-card.md",
            "templates/grammar-card.md",
            "templates/error-card.md",
            "templates/speaking-card.md",
            "templates/chunk-card.md",
            "views/total-training.base",
        ):
            self.assertIn(path, planned)
        self.assertIn("AGENTS.md", planned)
        runtime_path = runtime_connection_relative_path()
        self.assertEqual(current_platform(), planned[runtime_path]["content"]["platform"])
        self.assertIn("runtime_root", planned[runtime_path]["content"]["connections"][0])

    def test_existing_context_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / ".lingotrace/vault-context.json"
            context.parent.mkdir(parents=True)
            context.write_text("manual", encoding="utf-8")
            report = plan_english_vault_initialization(root)
        self.assertFalse(report.accepted)
        self.assertIn(".lingotrace/vault-context.json", report.blocked_files)

    def test_apply_creates_agent_entry_runtime_connection_and_pack_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "English Vault"
            report = initialize_english_vault(root)

            self.assertTrue(report.accepted, report.to_dict())
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / runtime_connection_relative_path()).is_file())
            self.assertTrue((root / "templates/focus-vocab-card.md").is_file())
            self.assertTrue((root / "views/total-training.base").is_file())
            instructions = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("runtime-connections", instructions)
            self.assertIn("lingotrace/packs/english/agent_skills/SKILL.md", instructions)
            self.assertIn("Obsidian Desktop and ListenKit are optional onboarding dependencies", instructions)
            self.assertIn("Do not block unrelated text-learning tasks", instructions)
            self.assertIn("check-update --vault <this-vault>", instructions)
            self.assertIn("one to three plain-Chinese points", instructions)
            self.assertIn("If the report identifies a personal fork, do not pull", instructions)
            self.assertIn("resolve-listenkit --vault <this-vault>", instructions)
            self.assertIn("reinstalling ListenKit or selecting an existing ListenKit directory", instructions)

    def test_initialization_can_record_a_confirmed_listenkit_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "English Vault"
            listenkit = root / "ListenKit"
            (listenkit / "cli").mkdir(parents=True)
            (listenkit / "README.md").write_text("# ListenKit\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            report = initialize_english_vault(vault, listenkit_root=listenkit)

            self.assertTrue(report.accepted, report.to_dict())
            connection = json.loads(
                (vault / listenkit_connection_relative_path()).read_text(encoding="utf-8")
            )
            self.assertEqual(str(listenkit), connection["connections"][0]["listenkit_root"])

    def test_invalid_runtime_root_blocks_initialization_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "English Vault"
            report = initialize_english_vault(root, runtime_root=Path(tmp) / "missing-runtime")

            self.assertFalse(report.accepted)
            self.assertEqual("runtime_root_missing", report.errors[0].code)
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
