from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE0_ROOT = REPO_ROOT / "docs" / "multilingual" / "phase-0"
EXAMPLES_ROOT = PHASE0_ROOT / "examples" / "v1"

CAPABILITIES = {
    "listening_notes",
    "source_notes",
    "review_materials",
    "speaking_cards",
    "review_rollover",
}

MATURITY_VALUES = {"experimental", "stable", "deprecated"}

CORE_REVIEW_CARD_FIELDS = {
    "track",
    "item_type",
    "status",
    "priority",
    "done_today",
    "review_stage",
    "next_review",
    "last_reviewed",
    "first_seen",
    "last_seen",
    "seen_count",
    "error_count",
    "source_notes",
}

VAULT_CONTEXT_FIELDS = {
    "vault_schema_version",
    "target_language",
    "explanation_language",
    "language_pack",
    "language_pack_version",
    "enabled_capabilities",
}

PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
}

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required Phase 0 contract file: {path}")
    return path.read_text(encoding="utf-8")


def yaml_fence(text: str) -> str:
    match = re.search(r"```ya?ml\n(.*?)\n```", text, flags=re.DOTALL)
    if not match:
        raise AssertionError("example document must include a yaml fenced block")
    return match.group(1)


def top_level_keys(raw_yaml: str) -> set[str]:
    keys: set[str] = set()
    for line in raw_yaml.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*:", line):
            keys.add(line.split(":", 1)[0].strip())
    return keys


def list_after(raw_yaml: str, key: str) -> set[str]:
    values: set[str] = set()
    in_list = False
    for line in raw_yaml.splitlines():
        if line.startswith(f"{key}:"):
            in_list = True
            continue
        if in_list and re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*:", line):
            break
        if in_list:
            match = re.match(r"\s+-\s+([a-zA-Z_][a-zA-Z0-9_-]*)", line)
            if match:
                values.add(match.group(1))
    return values


def section_between(raw_yaml: str, start_key: str, end_key: str) -> str:
    match = re.search(rf"(?ms)^{start_key}:\n(.*?)^{end_key}:", raw_yaml)
    if not match:
        raise AssertionError(f"missing yaml section between {start_key} and {end_key}")
    return match.group(1)


class ContractExampleTests(unittest.TestCase):
    def test_phase0_contract_documents_exist_and_define_fixed_public_contracts(self) -> None:
        docs = {
            "architecture": PHASE0_ROOT / "architecture-contracts.md",
            "conformance": PHASE0_ROOT / "language-pack-conformance-checklist.md",
            "migration": PHASE0_ROOT / "japanese-migration-contract.md",
            "exit": PHASE0_ROOT / "old-framework-exit-checklist.md",
            "phase1": PHASE0_ROOT / "phase-1-entry-gate.md",
        }
        bodies = {name: read_required(path) for name, path in docs.items()}

        for name, body in bodies.items():
            self.assertNotRegex(body, UNRESOLVED_MARKER_PATTERN, msg=f"{name} contains unresolved marker")

        architecture = bodies["architecture"]
        for field in VAULT_CONTEXT_FIELDS:
            self.assertIn(field, architecture)
        for capability in CAPABILITIES:
            self.assertIn(capability, architecture)
        for maturity in MATURITY_VALUES:
            self.assertIn(maturity, architecture)
        for field in CORE_REVIEW_CARD_FIELDS:
            self.assertIn(field, architecture)
        self.assertIn("Do not infer target_language from path, tag, folder, or content", architecture)
        self.assertIn("Preserve unknown frontmatter fields and body content", architecture)
        self.assertIn("External tool failure is a stop condition", architecture)
        self.assertIn("Implementation Gap Register", architecture)

    def test_examples_exist_use_yaml_and_do_not_embed_private_paths(self) -> None:
        examples = [
            "japanese-vault-context.example.md",
            "japanese-language-pack-manifest.example.md",
            "review-card-shell.example.md",
            "japanese-migration-manifest.example.md",
        ]

        for filename in examples:
            text = read_required(EXAMPLES_ROOT / filename)
            yaml_fence(text)
            for marker in PRIVATE_PATH_MARKERS:
                self.assertNotIn(marker, text, msg=f"{filename} leaks private path marker {marker}")

    def test_japanese_vault_context_example_declares_language_explicitly(self) -> None:
        raw = yaml_fence(read_required(EXAMPLES_ROOT / "japanese-vault-context.example.md"))

        self.assertTrue(VAULT_CONTEXT_FIELDS.issubset(top_level_keys(raw)))
        self.assertRegex(raw, r"(?m)^target_language:\s+ja$")
        self.assertRegex(raw, r"(?m)^explanation_language:\s+zh$")
        self.assertRegex(raw, r"(?m)^language_pack:\s+lingo-japanese$")
        self.assertEqual(CAPABILITIES, list_after(raw, "enabled_capabilities"))

    def test_language_pack_manifest_example_uses_allowed_capabilities_and_maturity(self) -> None:
        raw = yaml_fence(read_required(EXAMPLES_ROOT / "japanese-language-pack-manifest.example.md"))

        required = {
            "language_pack_id",
            "language_pack_version",
            "target_language",
            "transcription_locale",
            "compatible_core",
            "compatible_vault_schema",
            "capabilities",
            "external_tools",
            "language_fields",
            "item_types",
            "tag_namespace",
            "default_path_roles",
        }
        self.assertTrue(required.issubset(top_level_keys(raw)))
        capabilities_raw = section_between(raw, "capabilities", "external_tools")
        self.assertEqual(CAPABILITIES, set(re.findall(r"\bid:\s+([a-z_]+)", capabilities_raw)))
        maturity_values = set(re.findall(r"\bmaturity:\s+([a-z_]+)", capabilities_raw))
        self.assertTrue(maturity_values)
        self.assertTrue(maturity_values.issubset(MATURITY_VALUES))
        self.assertIn("minimum_required", raw)
        self.assertIn("failure_policy: stop_before_write", raw)

    def test_review_card_shell_example_separates_core_fields_from_japanese_extensions(self) -> None:
        raw = yaml_fence(read_required(EXAMPLES_ROOT / "review-card-shell.example.md"))

        self.assertEqual(CORE_REVIEW_CARD_FIELDS, list_after(raw, "core_fields"))
        self.assertTrue(
            {"reading", "accent_display", "meaning_zh", "kanji_diff", "kanji_diff_pairs"}.issubset(
                list_after(raw, "language_fields")
            )
        )
        self.assertIn("unknown_language_fields", raw)
        self.assertIn("preserve", raw)

    def test_migration_contract_and_manifest_keep_new_japanese_vault_boundary(self) -> None:
        contract = read_required(PHASE0_ROOT / "japanese-migration-contract.md")
        manifest = yaml_fence(read_required(EXAMPLES_ROOT / "japanese-migration-manifest.example.md"))

        for token in (
            "new Japanese Vault",
            "source_vault",
            "target_vault",
            "preserve private learning data",
            "do not copy old framework wholesale",
            "dry-run",
            "repeatable",
            "source_manifest",
            "target_manifest",
            "content_hash",
            "excluded_with_user_approval",
        ):
            self.assertIn(token, contract)

        for key in (
            "source_vault",
            "target_vault",
            "preserve_data",
            "recreate_from_pack",
            "transform_with_map",
            "remove_after_cutover",
            "conflicts",
            "verification_report",
        ):
            self.assertIn(f"{key}:", manifest)
        for token in (
            "manifest_version:",
            "source_manifest:",
            "target_manifest:",
            "content_hash:",
            "excluded_with_user_approval:",
            "approved_by:",
        ):
            self.assertIn(token, manifest)

    def test_phase1_entry_gate_blocks_runtime_work_until_phase0_is_complete(self) -> None:
        gate = read_required(PHASE0_ROOT / "phase-1-entry-gate.md")

        for token in (
            "PR A",
            "PR B",
            "PR C",
            "Japanese Baseline",
            "no English functionality",
            "no real migration",
            "core",
            "Japanese language pack",
            "new Vault initialization",
            "temporary migration",
            "conformance checklist can be converted into Phase 1 tests",
            "migration contract and old-framework exit checklist are confirmed",
            "no daily-use cutover",
            "no old Vault deletion",
        ):
            self.assertIn(token, gate)


if __name__ == "__main__":
    unittest.main()
