"""English language pack conformance tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PHASE0_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "english"
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

EXPECTED_LANGUAGE_FIELDS = {"ipa", "word_stress", "part_of_speech", "collocations"}


class EnglishPackTests(unittest.TestCase):

    def test_manifest_loads_through_core_loader(self):
        """1. Manifest passes load_language_pack_manifest without errors."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        self.assertTrue(result.report.accepted, result.report.to_dict())
        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-english", result.manifest.language_pack_id)
        self.assertEqual("0.1.0", result.manifest.language_pack_version)
        self.assertEqual("en", result.manifest.target_language)

    def test_declared_capabilities_are_subset_of_phase0_ids(self):
        """2. All declared capabilities use reviewed IDs from PHASE0_CAPABILITY_IDS."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        declared_ids = set(result.manifest.capabilities) | set(result.manifest.unsupported_capabilities)
        self.assertTrue(declared_ids.issubset(PHASE0_CAPABILITY_IDS))
        self.assertEqual(PHASE0_CAPABILITY_IDS, declared_ids)

    def test_unsupported_capabilities_have_fallback_none(self):
        """3. Unsupported capabilities declare fallback: 'none' and have failure policies."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        self.assertIn("listening_notes", result.manifest.unsupported_capabilities)
        self.assertIn("speaking_cards", result.manifest.unsupported_capabilities)

    def test_language_fields_are_english_pack_owned(self):
        """4. fields.json declares English-owned fields, not Japanese fields."""
        fields = json.loads(FIELDS_PATH.read_text(encoding="utf-8"))
        field_names = {r["name"] for r in fields["language_fields"]}
        self.assertEqual(EXPECTED_LANGUAGE_FIELDS, field_names)
        for record in fields["language_fields"]:
            self.assertEqual("English language pack", record["owner"])
        self.assertNotIn("reading", field_names)
        self.assertNotIn("accent_display", field_names)
        self.assertNotIn("kanji_diff", field_names)

    def test_default_path_roles_match_phase1_design(self):
        """5. Path roles align with general architectural paths."""
        paths = json.loads(PATHS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_PATH_ROLES, paths["default_path_roles"])

    def test_workflow_stubs_do_not_reference_japanese_runtime(self):
        """6. workflows.py does not import or reference Japanese pack modules."""
        source = (PACK_ROOT / "workflows.py").read_text(encoding="utf-8")
        self.assertNotIn("japanese", source.lower())
        self.assertNotIn("jp-", source)

    def test_pack_owned_surfaces_exist(self):
        """7. Every template declared in manifest exists on disk."""
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for record in manifest.get("templates", []):
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])


if __name__ == "__main__":
    unittest.main()
