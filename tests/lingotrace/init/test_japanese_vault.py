from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.init.japanese_vault import initialize_japanese_vault, plan_japanese_vault_initialization
from lingotrace.init.runtime_connections import runtime_connection_relative_path


class JapaneseVaultInitializationTests(unittest.TestCase):
    def test_empty_target_dry_run_reports_context_paths_scaffold_templates_and_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = plan_japanese_vault_initialization(root)

            self.assertEqual([], list(root.rglob("*")))

        envelope = report.to_dict()
        planned_by_path = {entry["path"]: entry for entry in envelope["planned_writes"]}

        self.assertTrue(report.accepted, envelope)
        self.assertEqual("init-japanese-vault", envelope["command"])
        self.assertEqual("dry-run", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])

        self.assertEqual("write_json", planned_by_path[".lingotrace/vault-context.json"]["action"])
        self.assertEqual("write_json", planned_by_path[".lingotrace/paths.json"]["action"])
        self.assertEqual("write_text", planned_by_path["AGENTS.md"]["action"])
        self.assertEqual("write_json", planned_by_path[runtime_connection_relative_path()]["action"])
        self.assertEqual("create_directory", planned_by_path["review/focus/vocab"]["action"])
        self.assertEqual("create_directory", planned_by_path["review/pronunciation/accent"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["templates/focus-vocab-card.md"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["templates/grammar-card.md"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["templates/error-card.md"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["views/total-training.base"]["action"])

        self.assertEqual(
            "vault-local-runtime-connection",
            planned_by_path[runtime_connection_relative_path()]["artifact_class"],
        )

    def test_generated_context_binds_one_target_language_and_one_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = plan_japanese_vault_initialization(Path(tmp))

        planned_by_path = {entry["path"]: entry for entry in report.to_dict()["planned_writes"]}
        context = planned_by_path[".lingotrace/vault-context.json"]["content"]

        self.assertEqual(1, context["vault_schema_version"])
        self.assertEqual("ja", context["target_language"])
        self.assertEqual("zh", context["explanation_language"])
        self.assertEqual("lingo-japanese", context["language_pack"])
        self.assertEqual("0.1.0", context["language_pack_version"])
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

    def test_non_empty_target_conflicts_block_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / ".lingotrace" / "vault-context.json"
            existing.parent.mkdir()
            existing.write_text("manual existing context", encoding="utf-8")

            report = plan_japanese_vault_initialization(root)

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual("target_conflict", envelope["errors"][0]["code"])
        self.assertIn(".lingotrace/vault-context.json", envelope["blocked_files"])
        self.assertEqual([], envelope["changed_files"])

    def test_dry_run_does_not_write_missing_files_or_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = plan_japanese_vault_initialization(root)

            self.assertTrue(report.accepted, report.to_dict())
            self.assertFalse((root / ".lingotrace").exists())
            self.assertFalse((root / "review").exists())
            self.assertFalse((root / "templates").exists())
            self.assertFalse((root / "views").exists())

    def test_apply_creates_complete_japanese_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Japanese Vault"
            report = initialize_japanese_vault(root)

            self.assertTrue(report.accepted, report.to_dict())
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / runtime_connection_relative_path()).is_file())
            self.assertTrue((root / "templates/focus-vocab-card.md").is_file())
            self.assertIn(
                "lingotrace/packs/japanese/agent_skills/SKILL.md",
                (root / "AGENTS.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
