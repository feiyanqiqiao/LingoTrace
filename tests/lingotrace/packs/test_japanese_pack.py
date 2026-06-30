from __future__ import annotations

import importlib
import json
import re
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PHASE0_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "japanese"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
FIELDS_PATH = PACK_ROOT / "fields.json"
PATHS_PATH = PACK_ROOT / "paths.json"

EXPECTED_PATH_ROLES = {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily",
}

EXPECTED_LANGUAGE_FIELDS = {
    "reading",
    "accent_display",
    "meaning_zh",
    "kanji_diff",
    "kanji_diff_pairs",
}


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_total_training_base() -> str:
    return (PACK_ROOT / "views" / "total-training.base").read_text(encoding="utf-8")


def formula(body: str, name: str) -> str:
    match = re.search(rf"^  {re.escape(name)}: (.+)$", body, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing formula: {name}")
    value = match.group(1)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def view_block(body: str, name: str) -> str:
    blocks = re.split(r"(?=^  - type: table$)", body, flags=re.MULTILINE)
    for block in blocks:
        if re.search(rf"^    name: {re.escape(name)}$", block, flags=re.MULTILINE):
            return block
    raise AssertionError(f"Missing view: {name}")


def list_values(block: str, section: str) -> list[str]:
    match = re.search(rf"^    {re.escape(section)}:\n((?:      - .+\n)+)", block, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing list section: {section}")
    return [line.strip()[2:] for line in match.group(1).splitlines()]


def column_size(block: str, property_name: str) -> int:
    match = re.search(rf"^      {re.escape(property_name)}: (\d+)$", block, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing column size for: {property_name}")
    return int(match.group(1))


def sort_properties(block: str) -> list[tuple[str, str]]:
    matches = re.findall(
        r"^      - property: (.+)\n        direction: (ASC|DESC)$",
        block,
        flags=re.MULTILINE,
    )
    if not matches:
        raise AssertionError("Missing sort property entries")
    return matches


class JapanesePackTests(unittest.TestCase):
    def test_manifest_loads_through_core_loader_and_declares_all_phase0_capabilities(self) -> None:
        result = load_language_pack_manifest(MANIFEST_PATH)

        self.assertTrue(result.report.accepted, result.report.to_dict())
        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-japanese", result.manifest.language_pack_id)
        self.assertEqual("0.1.0", result.manifest.language_pack_version)
        self.assertEqual("ja", result.manifest.target_language)
        self.assertEqual(PHASE0_CAPABILITY_IDS, set(result.manifest.capabilities))
        self.assertEqual({}, result.manifest.unsupported_capabilities)

        for capability in result.manifest.capabilities.values():
            self.assertEqual("stable", capability.maturity)
            self.assertGreater(len(capability.behavior_evidence), 0)

    def test_language_fields_are_japanese_pack_owned_and_not_generic_core_fields(self) -> None:
        fields = read_json(FIELDS_PATH)
        manifest = read_json(MANIFEST_PATH)

        field_records = fields["language_fields"]
        self.assertIsInstance(field_records, list)
        field_names = {record["name"] for record in field_records}
        self.assertEqual(EXPECTED_LANGUAGE_FIELDS, field_names)
        self.assertEqual(field_records, manifest["language_fields"])

        for record in field_records:
            self.assertEqual("Japanese language pack", record["owner"])

        self.assertNotIn("reading_text", field_names)
        self.assertNotIn("accent", field_names)
        self.assertNotIn("meaning", field_names)

    def test_default_path_roles_match_phase1_design(self) -> None:
        paths = read_json(PATHS_PATH)
        manifest = read_json(MANIFEST_PATH)
        loaded = load_language_pack_manifest(MANIFEST_PATH)

        self.assertEqual(EXPECTED_PATH_ROLES, paths["default_path_roles"])
        self.assertEqual(EXPECTED_PATH_ROLES, manifest["default_path_roles"])
        self.assertIsNotNone(loaded.manifest)
        assert loaded.manifest is not None
        self.assertEqual(EXPECTED_PATH_ROLES, loaded.manifest.default_path_roles)

    def test_pack_owned_surfaces_are_manifest_declared_and_files_exist(self) -> None:
        manifest = read_json(MANIFEST_PATH)

        templates = manifest["templates"]
        self.assertEqual(
            {"focus_vocab_card", "speaking_card", "daily_checklist"},
            {record["id"] for record in templates},
        )
        for record in templates:
            self.assertEqual("recreate-from-pack", record["artifact_class"])
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])

        default_views = manifest["default_views"]
        self.assertEqual(["total_training_dashboard"], [record["id"] for record in default_views])
        for record in default_views:
            self.assertEqual("recreate-from-pack", record["artifact_class"])
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])

        for record in manifest["initialization_artifacts"]:
            self.assertEqual("recreate-from-pack", record["artifact_class"])
            self.assertTrue(record["path"].startswith(".lingotrace/"))

    def test_total_training_dashboard_surfaces_type_specific_review_cues(self) -> None:
        template = read_total_training_base()
        core_text = formula(template, "core_text")
        support_text = formula(template, "support_text")

        expected_core_contracts = (
            'item_type == "vocab", if(accent_display, accent_display, if(headword, headword, file.name))',
            'item_type == "grammar", if(meaning_zh, meaning_zh, if(pattern, pattern, file.name))',
            'item_type == "error", if(correct_form, correct_form, file.name)',
            'track == "survival_speaking", if(jp_text, jp_text, file.name)',
            'track == "listening", if(daily_use_sentences, daily_use_sentences, if(practice_focus, practice_focus, file.name))',
            'track == "pronunciation", if(target_text, target_text, file.name)',
        )
        expected_support_contracts = (
            'item_type == "vocab", if(collocations, collocations, if(meaning_zh, meaning_zh, ""))',
            'item_type == "grammar", if(formation, formation, "")',
            'item_type == "error", if(wrong_form, wrong_form, if(reason, reason, ""))',
            'track == "survival_speaking", if(reply_hint, if(meaning_zh, meaning_zh + " / 回应: " + reply_hint, reply_hint), if(meaning_zh, meaning_zh, ""))',
            'track == "listening", if(practice_focus, practice_focus, if(weak_points, weak_points, ""))',
            'track == "pronunciation", if(issue_tags, issue_tags, "")',
        )

        for contract in expected_core_contracts:
            self.assertIn(contract, core_text)
        for contract in expected_support_contracts:
            self.assertIn(contract, support_text)

    def test_total_training_dashboard_daily_review_contract(self) -> None:
        template = read_total_training_base()
        today = view_block(template, "今日总训练")
        order = list_values(today, "order")
        sort = sort_properties(today)

        self.assertIn('next_day_flag: if(status == "active" && next_review', template)
        self.assertIn('date(next_review) <= today() + "1d"', formula(template, "next_day_flag"))
        self.assertIn('!(last_reviewed && date(last_reviewed) >= today())', formula(template, "next_day_flag"))
        self.assertIn("formula.next_day_flag == true", today)
        self.assertEqual(["file.name", "done_today"], order[:2])
        self.assertEqual(260, column_size(today, "file.name"))
        self.assertEqual(("file.name", "ASC"), sort[-1])

    def test_total_training_dashboard_uses_card_frontmatter_without_review_state_snapshots(self) -> None:
        template = read_total_training_base()

        self.assertNotIn("views/review-state", template)
        self.assertNotIn(".lingotrace/review-state", template)
        for property_name in ("done_today", "next_review", "last_reviewed", "status"):
            self.assertIn(property_name, template)

    def test_workflows_are_declarative_and_do_not_call_old_jp_skills(self) -> None:
        manifest = read_json(MANIFEST_PATH)
        workflows = importlib.import_module("lingotrace.packs.japanese.workflows")

        for record in manifest["workflow_entrypoints"]:
            self.assertEqual("through_core_write_guard", record["call_policy"])
            self.assertTrue(record["entrypoint"].startswith("lingotrace.packs.japanese.workflows:"))
            function_name = record["entrypoint"].split(":", 1)[1]
            report = getattr(workflows, function_name)()
            self.assertFalse(report.accepted)
            self.assertEqual([], report.to_dict()["changed_files"])
            self.assertEqual("missing_vault_root", report.to_dict()["errors"][0]["code"])

        workflow_source = (PACK_ROOT / "workflows.py").read_text(encoding="utf-8")
        self.assertNotIn("codex-skills", workflow_source)
        self.assertNotIn("jp-", workflow_source)

    def test_validator_stubs_accept_synthetic_public_fixtures(self) -> None:
        validators = importlib.import_module("lingotrace.packs.japanese.validators")

        review_report = validators.validate_review_materials(
            {
                "item_type": "vocab",
                "reading": "ごうせいご",
                "meaning_zh": "合成词",
                "review_stage": 1,
            }
        )
        rollover_report = validators.validate_review_rollover(
            {
                "review_stage": 1,
                "next_review": "2026-06-21",
                "done_today": False,
            }
        )

        self.assertTrue(review_report.accepted, review_report.to_dict())
        self.assertTrue(rollover_report.accepted, rollover_report.to_dict())

    def test_unsupported_capabilities_are_explicitly_empty_for_japanese_pack(self) -> None:
        manifest = read_json(MANIFEST_PATH)

        self.assertEqual([], manifest["unsupported_capabilities"])


if __name__ == "__main__":
    unittest.main()
