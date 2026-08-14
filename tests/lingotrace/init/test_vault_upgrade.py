from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lingotrace.init.vault_upgrade import upgrade_vault


class VaultUpgradeTests(unittest.TestCase):
    def _legacy_vault(self, root: Path, total_training: bytes) -> None:
        context = root / ".lingotrace/vault-context.json"
        context.parent.mkdir(parents=True)
        context.write_text(json.dumps({
            "vault_schema_version": 1,
            "target_language": "ja",
            "language_pack": "lingo-japanese",
            "language_pack_version": "0.1.0",
            "enabled_capabilities": ["review_materials", "review_rollover"],
        }), encoding="utf-8")
        view = root / "views/total-training.base"
        view.parent.mkdir(parents=True)
        view.write_bytes(total_training)

    def test_unmodified_legacy_view_is_upgraded_and_material_library_is_deployed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = b"known legacy pack view\n"
            self._legacy_vault(root, legacy)
            legacy_hash = hashlib.sha256(legacy).hexdigest()
            with patch.dict("lingotrace.init.vault_upgrade.LEGACY_TOTAL_TRAINING_HASHES", {"lingo-japanese": {legacy_hash}}):
                preview = upgrade_vault(root)
                applied = upgrade_vault(root, mode="apply")
            context = json.loads((root / ".lingotrace/vault-context.json").read_text(encoding="utf-8"))
            material_library_exists = (root / "views/material-library.base").is_file()
        self.assertTrue(preview.accepted, preview.to_dict())
        self.assertTrue(applied.accepted, applied.to_dict())
        self.assertIn("review_queue", context["enabled_capabilities"])
        self.assertTrue(material_library_exists)

    def test_modified_view_blocks_every_upgrade_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._legacy_vault(root, b"manual customization\n")
            before = (root / ".lingotrace/vault-context.json").read_text(encoding="utf-8")
            report = upgrade_vault(root, mode="apply")
            after = (root / ".lingotrace/vault-context.json").read_text(encoding="utf-8")
        self.assertFalse(report.accepted)
        self.assertEqual("modified_pack_view", report.errors[0].code)
        self.assertEqual(before, after)
        self.assertFalse((root / "views/material-library.base").exists())


if __name__ == "__main__":
    unittest.main()
