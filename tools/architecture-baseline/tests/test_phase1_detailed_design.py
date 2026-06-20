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
            '"workflow_entrypoints"',
            '"validators"',
            '"resources"',
            '"display_rules"',
            '"default_views"',
            '"initialization_artifacts"',
            '"capability_id": "review_materials"',
            '"capability_id": "review_rollover"',
            '"artifact_class": "recreate-from-pack"',
            "Pack-Owned Surface Registry",
            "Every capability must declare both `read_path_roles` and `write_path_roles`",
            "Pack-owned templates, workflow entrypoints, validators, resources, display rules, default views, and initialization artifacts",
            "old `jp-*` Skills are evidence only and are not pack workflow entrypoints",
        ):
            self.assertIn(token, design)

    def test_phase1_design_declares_unsupported_capability_failure_contract(self) -> None:
        design = read_design()

        for token in (
            '"unsupported_capabilities": []',
            "Unsupported Capability Declaration",
            "A reviewed capability ID absent from `capabilities` must appear in `unsupported_capabilities`",
            '"failure_policy": "stop_before_write"',
            '"fallback": "none"',
            "unsupported_capability",
            "not_enabled_in_vault",
            "experimental_not_enabled",
            "deprecated_write_blocked",
            "must not fall back to Japanese behavior",
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

    def test_phase1_design_defines_migration_manifest_and_exit_ledger(self) -> None:
        design = read_design()

        for token in (
            "Migration Manifest Schema",
            '"source_vault"',
            '"target_vault"',
            '"source_manifest"',
            '"target_manifest"',
            '"excluded_with_user_approval"',
            '"verification_report"',
            '"comparison_strategy"',
            '"content_hash"',
            '"frontmatter_and_body"',
            '"links_and_hashes"',
            '"field_aware"',
            "unclassified entries block cutover",
        ):
            self.assertIn(token, design)

        for token in (
            "Old-Framework Exit Ledger",
            '"exit_candidate_id"',
            '"exit_status"',
            '"remove-after-cutover"',
            "read-only observation",
            "not copied into the target Vault",
            "must be resolved before Phase 2 cutover acceptance",
        ):
            self.assertIn(token, design)

    def test_phase1_pr_sequence_and_completion_gate_include_latest_surfaces(self) -> None:
        design = read_design()

        for token in (
            "PR 2: Japanese Pack Boundary",
            "workflow entrypoint registry",
            "display rules",
            "default views",
            "unsupported-capability failure records",
            "PR 4: Temporary Migration Inventory",
            "migration manifest schema",
            "source and target manifest generator",
            "old-framework exit ledger",
            "unclassified entries block acceptance",
        ):
            self.assertIn(token, design)

        for token in (
            "Phase 1 Completion Gate",
            "Capability registry reports explicit unavailable-capability failure codes.",
            "Japanese pack workflow entrypoints, display rules, default views, and initialization artifacts are manifest-declared.",
            "Migration dry-run emits the manifest schema, comparison report, and old-framework exit ledger on synthetic fixtures.",
            "Temporary migration readers remain outside runtime and have recorded removal conditions.",
        ):
            self.assertIn(token, design)

    def test_phase1_design_keeps_migration_cli_matrix_and_adapter_codes_contractual(self) -> None:
        design = read_design()

        for token in (
            "migration-inventory --source <source-vault> --target <target-vault> --dry-run",
            "target is required even in dry-run",
            "source and target Vault paths in read-only mode",
            "migration manifest, source/target manifest generator, old-framework exit ledger",
        ):
            self.assertIn(token, design)

        for token in (
            "Japanese pack manifest, field ownership, workflow entrypoints, validators, resources, display rules, default views, default path roles",
            "External Adapter Preflight Codes",
            "external_tool_unavailable",
            "external_tool_version_mismatch",
            "external_locale_unavailable",
            "external_side_effect_blocked",
            "external_adapter_failed",
            "must not be converted into an unsupported capability code",
        ):
            self.assertIn(token, design)

    def test_phase1_design_defines_runtime_start_gate_and_pr_dependencies(self) -> None:
        design = read_design()

        for token in (
            "Before Runtime Implementation Gate",
            "Runtime implementation PRs cannot start until this detailed design PR is accepted",
            "project maintainers and Zheng Jie",
            "no unresolved review threads",
            "Dependency-Gated PR Sequence",
            "PR 1 has no runtime-code prerequisite beyond this gate",
            "PR 2 depends on PR 1",
            "PR 3 depends on PR 1 and PR 2",
            "PR 4 depends on PR 1 and PR 3",
            "PR 5 depends on accepted PR 1 through PR 4 evidence",
            "Any dependency exception must be documented in the PR body",
            "no PR may combine core runtime, Japanese pack boundary, new Vault initialization, temporary migration, and contributor documentation as one implementation change",
        ):
            self.assertIn(token, design)

    def test_phase1_design_has_review_acceptance_matrix(self) -> None:
        design = read_design()

        for token in (
            "Phase 1 Design Review Acceptance Matrix",
            "This matrix is a review aid, not a Phase 1 completion claim.",
            "Covered by this design PR",
            "External review required",
            "Out of this design PR scope",
            "DD-01",
            "DD-02",
            "DD-03",
            "DD-04",
            "DD-05",
            "DD-06",
            "DD-07",
            "DD-08",
            "DD-09",
            "DD-10",
            "DD-11",
            "DD-12",
            "Runtime boundaries and blocked work are explicit.",
            "Runtime configuration schemas and command surfaces are concrete enough for PR 1 implementation.",
            "The Japanese pack boundary is implementable without preserving the old framework as runtime.",
            "Temporary migration design preserves private data by default without approving real migration.",
            "Old-framework exit obligations remain visible before Phase 2.",
            "Maintainers and Zheng Jie accept this detailed design before runtime implementation starts.",
        ):
            self.assertIn(token, design)


if __name__ == "__main__":
    unittest.main()
