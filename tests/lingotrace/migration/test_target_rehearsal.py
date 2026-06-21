from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.migration.target_rehearsal import plan_target_vault_rehearsal


class TargetVaultRehearsalTests(unittest.TestCase):
    def test_rehearsal_reports_recreate_from_pack_assets_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            report = plan_target_vault_rehearsal(target)

            self.assertEqual([], list(target.rglob("*")))

        envelope = report.to_dict()
        planned_by_path = {entry["path"]: entry for entry in envelope["planned_writes"]}

        self.assertTrue(report.accepted, envelope)
        self.assertEqual("target-vault-rehearsal", envelope["command"])
        self.assertEqual("dry-run", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual("write_json", planned_by_path[".lingotrace/vault-context.json"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["templates/focus-vocab-card.md"]["action"])
        self.assertEqual("copy_pack_artifact", planned_by_path["views/total-training.base"]["action"])
        for entry in envelope["planned_writes"]:
            self.assertEqual("recreate-from-pack", entry["artifact_class"])

    def test_rehearsal_blocks_existing_target_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / ".lingotrace" / "vault-context.json"
            existing.parent.mkdir()
            existing.write_text("manual context", encoding="utf-8")

            report = plan_target_vault_rehearsal(target)

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(["target_conflict"], [finding["code"] for finding in envelope["errors"]])
        self.assertEqual([".lingotrace/vault-context.json"], envelope["blocked_files"])
        self.assertEqual([], envelope["changed_files"])

    def test_rehearsal_context_binds_japanese_pack_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = plan_target_vault_rehearsal(Path(tmp))

        planned_by_path = {entry["path"]: entry for entry in report.to_dict()["planned_writes"]}
        context = planned_by_path[".lingotrace/vault-context.json"]["content"]

        self.assertEqual("ja", context["target_language"])
        self.assertEqual("zh", context["explanation_language"])
        self.assertEqual("lingo-japanese", context["language_pack"])
        self.assertEqual("0.1.0", context["language_pack_version"])


if __name__ == "__main__":
    unittest.main()
