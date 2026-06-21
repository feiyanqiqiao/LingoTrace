from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE2_ROOT = REPO_ROOT / "docs/multilingual/phase-2"
CUTOVER_RUNBOOK = PHASE2_ROOT / "cutover-runbook.md"
OBSERVATION_RUNBOOK = PHASE2_ROOT / "read-only-observation-runbook.md"


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required runbook: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


class Phase2CutoverRunbookTests(unittest.TestCase):
    def test_runbooks_exist_without_unresolved_markers(self) -> None:
        for path in (CUTOVER_RUNBOOK, OBSERVATION_RUNBOOK):
            body = read_required(path)
            self.assertNotIn("TB" + "D", body)
            self.assertNotIn("TO" + "DO", body)
            self.assertNotIn("/" + "Users/", body)

    def test_cutover_runbook_defines_required_gates_and_sequence(self) -> None:
        body = read_required(CUTOVER_RUNBOOK)

        required_phrases = [
            "owner approval",
            "green verification report",
            "no unresolved conflicts",
            "no missing approvals",
            "target daily-use smoke checks",
            "rollback path",
            "read-only observation entry",
            "separate final-removal confirmation",
            "freeze source writes",
            "generate final source manifest",
            "initialize target Vault",
            "migrate preserved data",
            "apply approved transforms",
            "compare manifests",
            "run five workflow checks",
            "switch daily entry points",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

    def test_observation_runbook_defines_read_only_and_repair_rules(self) -> None:
        body = read_required(OBSERVATION_RUNBOOK)

        required_phrases = [
            "old Vault read-only",
            "no new source writes",
            "target Vault handles daily learning",
            "recorded migration fix",
            "owner acceptance remains valid",
            "separate user confirmation",
            "final removal",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main()
