from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.core.manifests import LanguagePackManifest
from lingotrace.core.paths import PathRole, load_path_config, resolve_path_roles


def manifest() -> LanguagePackManifest:
    return LanguagePackManifest(
        language_pack_id="lingo-japanese",
        language_pack_version="0.1.0",
        target_language="ja",
        capabilities={},
        unsupported_capabilities={},
        default_path_roles={
            "base_vocab_root": "review/base/vocab",
            "focus_vocab_root": "review/focus/vocab",
        },
    )


class PathRoleTests(unittest.TestCase):
    def test_missing_path_config_uses_pack_defaults_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_path_config(Path(tmp))

        self.assertEqual({}, result.path_roles)
        self.assertTrue(result.report.accepted)
        self.assertEqual(["path_config_missing"], [finding.code for finding in result.findings])

    def test_rejects_unsafe_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / ".lingotrace"
            config_dir.mkdir()
            (config_dir / "paths.json").write_text(
                json.dumps(
                    {
                        "path_roles": [
                            {
                                "role": "focus_vocab_root",
                                "relative_path": "../outside",
                                "source": "vault_config",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = load_path_config(root)

        self.assertEqual({}, result.path_roles)
        self.assertFalse(result.report.accepted)
        self.assertEqual(["unsafe_relative_path"], [finding.code for finding in result.findings])

    def test_resolver_uses_vault_config_before_pack_defaults(self) -> None:
        resolved = resolve_path_roles(
            manifest(),
            {
                "focus_vocab_root": PathRole(
                    role="focus_vocab_root",
                    relative_path="custom/focus",
                    source="vault_config",
                )
            },
        )

        self.assertEqual("custom/focus", resolved["focus_vocab_root"].relative_path)
        self.assertEqual("vault_config", resolved["focus_vocab_root"].source)
        self.assertEqual("review/base/vocab", resolved["base_vocab_root"].relative_path)
        self.assertEqual("language_pack_default", resolved["base_vocab_root"].source)
        self.assertEqual(["base_vocab_root", "focus_vocab_root"], list(resolved.keys()))

    def test_resolver_rejects_unknown_roles(self) -> None:
        with self.assertRaises(ValueError) as raised:
            resolve_path_roles(
                manifest(),
                {
                    "unknown_root": PathRole(
                        role="unknown_root",
                        relative_path="unknown",
                        source="vault_config",
                    )
                },
            )

        self.assertIn("unknown_path_role", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
