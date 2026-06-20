from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE1_DESIGN = REPO_ROOT / "docs" / "multilingual" / "phase-1" / "detailed-design.md"

PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
    "zhang" + "qiao",
    "山" + "桥",
}

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"


def read_design() -> str:
    if not PHASE1_DESIGN.exists():
        raise AssertionError(f"missing Phase 1 detailed design: {PHASE1_DESIGN}")
    return PHASE1_DESIGN.read_text(encoding="utf-8")


class Phase1DetailedDesignTests(unittest.TestCase):
    def test_phase1_design_exists_without_unresolved_markers_or_private_paths(self) -> None:
        design = read_design()

        self.assertNotRegex(design, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, design)

    def test_phase1_design_keeps_runtime_scope_separate_from_blocked_work(self) -> None:
        design = read_design()

        for token in (
            "Phase 1 detailed design",
            "no English functionality",
            "no real private data migration",
            "no daily-use cutover",
            "no old Vault deletion",
            "not a compatibility mode",
            "Phase 2",
        ):
            self.assertIn(token, design)

    def test_phase1_design_assigns_each_workstream_to_one_owner(self) -> None:
        design = read_design()

        for token in (
            "core",
            "Japanese language pack",
            "new Vault initialization",
            "temporary migration",
            "external adapter boundary",
            "public documentation",
        ):
            self.assertIn(token, design)

        self.assertIn("Workstream Ownership Matrix", design)
        self.assertRegex(design, r"\|\s*Core runtime skeleton\s*\|\s*core\s*\|")
        self.assertRegex(design, r"\|\s*Japanese pack boundary\s*\|\s*Japanese language pack\s*\|")
        self.assertRegex(design, r"\|\s*New Japanese Vault scaffold\s*\|\s*new Vault initialization\s*\|")
        self.assertRegex(design, r"\|\s*Migration dry-run inventory\s*\|\s*temporary migration\s*\|")

    def test_phase1_design_defines_public_interfaces_before_tasks(self) -> None:
        design = read_design()

        for token in (
            "Runtime Config Schemas",
            "Vault context loader",
            "Language pack manifest loader",
            "Capability registry",
            "Path role resolver",
            "Review-card shell service",
            "Write transaction guard",
            "Conformance test suite",
            "Japanese pack manifest",
            "initializer dry-run",
            "migration inventory dry-run",
        ):
            self.assertIn(token, design)

    def test_phase1_design_defines_config_schema_and_command_surface(self) -> None:
        design = read_design()

        for token in (
            '".lingotrace/vault-context.json"',
            '"vault_schema_version": 1',
            '"target_language": "ja"',
            '"explanation_language": "zh"',
            '"language_pack": "lingo-japanese"',
            '"enabled_capabilities"',
            '".lingotrace/paths.json"',
            '"path_roles"',
            '"role": "focus_vocab_root"',
            '"relative_path": "review/focus/vocab"',
            '"source": "vault_config"',
            '"lingotrace/packs/japanese/manifest.json"',
            '"language_pack_id": "lingo-japanese"',
            '"compatible_core"',
            '"compatible_vault_schema"',
            '"id": "review_materials"',
            '"minimum_required"',
            '"failure_policy": "stop_before_write"',
            '"name": "reading"',
            "Command Surface",
            "validate-vault",
            "init-japanese-vault --dry-run",
            "migration-inventory --dry-run",
        ):
            self.assertIn(token, design)

    def test_phase1_design_defines_japanese_path_roles_and_stable_evidence_gate(self) -> None:
        design = read_design()

        for token in (
            "Minimum Japanese path role set for Phase 1",
            "Target new-Vault default",
            "These defaults describe the target new Japanese Vault",
            '"role": "focus_vocab_root"',
            '"role": "base_vocab_root"',
            '"role": "grammar_root"',
            '"role": "error_root"',
            '"role": "speaking_card_root"',
            '"role": "speaking_guide_root"',
            '"role": "listening_root"',
            '"role": "pronunciation_accent_root"',
            '"role": "pronunciation_phoneme_root"',
            '"role": "source_notes_root"',
            '"role": "daily_notes_root"',
            '"grammar_root": "review/grammar"',
            '"error_root": "review/errors"',
            '"pronunciation_accent_root": "review/pronunciation/accent"',
            '"pronunciation_phoneme_root": "review/pronunciation/phoneme"',
            '"source_notes_root": "sources"',
            '"daily_notes_root": "daily"',
        ):
            self.assertIn(token, design)

        for token in (
            "Stable Capability Evidence Gate",
            '"behavior_evidence"',
            '"conformance_tests"',
            '"manual_review_cases"',
            "JP-REVIEW-001",
            "JP-ROLLOVER-001",
            "Experimental By Default Rule",
            "no capability can be marked `stable`",
        ):
            self.assertIn(token, design)

    def test_phase1_design_declares_capability_paths_and_pack_owned_surfaces(self) -> None:
        design = read_design()

        for token in (
            '"read_path_roles"',
            '"write_path_roles"',
            '"templates"',
            '"validators"',
            '"resources"',
            '"initialization_artifacts"',
            '"capability_id": "review_materials"',
            '"capability_id": "review_rollover"',
            '"artifact_class": "recreate-from-pack"',
            "Pack-Owned Surface Registry",
            "Every capability must declare both `read_path_roles` and `write_path_roles`",
            "Pack-owned templates, validators, resources, and initialization artifacts",
        ):
            self.assertIn(token, design)

    def test_phase1_design_defines_public_allowlist_and_legacy_bridge_rules(self) -> None:
        design = read_design()

        for token in (
            "Public Allowlist And CI Changes",
            "lingotrace/",
            "tests/lingotrace/",
            "tools/architecture-baseline/",
            ".lingotrace/",
            "must not be added to the public allowlist",
            "python -m unittest discover -s tests/lingotrace -p 'test_*.py'",
            "Legacy Bridge Rule",
            "Core runtime must not import or call old `jp-*` Skills",
            "no package installation or upgrade side effect",
        ):
            self.assertIn(token, design)

    def test_phase1_design_keeps_japanese_migration_data_preservation_explicit(self) -> None:
        design = read_design()

        for token in (
            "preserve-data",
            "recreate-from-pack",
            "transform-with-map",
            "remove-after-cutover",
            "Japanese fields remain Japanese pack fields",
            "reading",
            "accent_display",
            "meaning_zh",
            "kanji_diff",
            "kanji_diff_pairs",
        ):
            self.assertIn(token, design)


if __name__ == "__main__":
    unittest.main()
