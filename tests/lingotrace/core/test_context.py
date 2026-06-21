from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.core.context import load_vault_context


def write_context(vault_root: Path, payload: dict[str, object]) -> None:
    config_dir = vault_root / ".lingotrace"
    config_dir.mkdir()
    (config_dir / "vault-context.json").write_text(json.dumps(payload), encoding="utf-8")


def valid_context() -> dict[str, object]:
    return {
        "vault_schema_version": 1,
        "target_language": "ja",
        "explanation_language": "zh",
        "language_pack": "lingo-japanese",
        "language_pack_version": "0.1.0",
        "enabled_capabilities": ["review_materials", "review_rollover"],
    }


class VaultContextLoaderTests(unittest.TestCase):
    def test_missing_context_stops_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_vault_context(Path(tmp))

        self.assertIsNone(result.context)
        self.assertEqual(["context_missing"], [finding.code for finding in result.findings])
        self.assertFalse(result.report.accepted)

    def test_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = valid_context()
            payload["vault_schema_version"] = 2
            write_context(root, payload)

            result = load_vault_context(root)

        self.assertIsNone(result.context)
        self.assertIn("unsupported_vault_schema", [finding.code for finding in result.findings])

    def test_rejects_unsupported_target_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = valid_context()
            payload["target_language"] = "en"
            write_context(root, payload)

            result = load_vault_context(root)

        self.assertIsNone(result.context)
        self.assertIn("unsupported_target_language", [finding.code for finding in result.findings])

    def test_rejects_duplicate_enabled_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = valid_context()
            payload["enabled_capabilities"] = ["review_materials", "review_materials"]
            write_context(root, payload)

            result = load_vault_context(root)

        self.assertIsNone(result.context)
        self.assertIn("duplicate_enabled_capability", [finding.code for finding in result.findings])

    def test_loads_valid_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_context(root, valid_context())

            result = load_vault_context(root)

        self.assertIsNotNone(result.context)
        assert result.context is not None
        self.assertEqual(1, result.context.vault_schema_version)
        self.assertEqual("ja", result.context.target_language)
        self.assertEqual("zh", result.context.explanation_language)
        self.assertEqual("lingo-japanese", result.context.language_pack)
        self.assertEqual(["review_materials", "review_rollover"], list(result.context.enabled_capabilities))
        self.assertTrue(result.report.accepted)


if __name__ == "__main__":
    unittest.main()
