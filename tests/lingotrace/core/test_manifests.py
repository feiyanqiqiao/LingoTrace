from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.core.manifests import load_language_pack_manifest


def valid_manifest() -> dict[str, object]:
    return {
        "language_pack_id": "lingo-japanese",
        "language_pack_version": "0.1.0",
        "target_language": "ja",
        "compatible_core": {"minimum": "0.1.0", "maximum_exclusive": "0.2.0"},
        "compatible_vault_schema": {"minimum": 1, "maximum": 1},
        "capabilities": [
            {
                "id": "review_materials",
                "maturity": "stable",
                "depends_on": [],
                "read_path_roles": ["focus_vocab_root"],
                "write_path_roles": ["focus_vocab_root"],
                "external_tools": [],
                "behavior_evidence": ["JP-REVIEW-001"],
                "conformance_tests": ["tests/lingotrace/core/test_manifests.py"],
                "manual_review_cases": [],
            }
        ],
        "unsupported_capabilities": [],
        "default_path_roles": {"focus_vocab_root": "review/focus/vocab"},
    }


def write_manifest(payload: dict[str, object]) -> Path:
    path = Path(tempfile.mkdtemp()) / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class ManifestLoaderTests(unittest.TestCase):
    def test_rejects_invalid_maturity(self) -> None:
        payload = valid_manifest()
        payload["capabilities"][0]["maturity"] = "beta"  # type: ignore[index]
        result = load_language_pack_manifest(write_manifest(payload))

        self.assertIsNone(result.manifest)
        self.assertIn("invalid_maturity", [finding.code for finding in result.findings])

    def test_rejects_duplicate_capability_ids(self) -> None:
        payload = valid_manifest()
        payload["capabilities"].append(payload["capabilities"][0].copy())  # type: ignore[union-attr,index]
        result = load_language_pack_manifest(write_manifest(payload))

        self.assertIsNone(result.manifest)
        self.assertIn("duplicate_capability", [finding.code for finding in result.findings])

    def test_rejects_unsupported_capability_fallbacks_other_than_none(self) -> None:
        payload = valid_manifest()
        payload["unsupported_capabilities"] = [
            {
                "id": "listening_notes",
                "failure_reason": "not implemented",
                "failure_policy": "stop_before_write",
                "fallback": "japanese_default",
            }
        ]
        result = load_language_pack_manifest(write_manifest(payload))

        self.assertIsNone(result.manifest)
        self.assertIn("unsupported_capability_fallback_not_none", [finding.code for finding in result.findings])

    def test_rejects_stable_capability_without_evidence(self) -> None:
        payload = valid_manifest()
        payload["capabilities"][0]["behavior_evidence"] = []  # type: ignore[index]
        result = load_language_pack_manifest(write_manifest(payload))

        self.assertIsNone(result.manifest)
        self.assertIn("stable_capability_missing_evidence", [finding.code for finding in result.findings])

    def test_loads_valid_manifest(self) -> None:
        result = load_language_pack_manifest(write_manifest(valid_manifest()))

        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-japanese", result.manifest.language_pack_id)
        self.assertEqual("ja", result.manifest.target_language)
        self.assertIn("review_materials", result.manifest.capabilities)
        self.assertEqual("stable", result.manifest.capabilities["review_materials"].maturity)
        self.assertTrue(result.report.accepted)


if __name__ == "__main__":
    unittest.main()
