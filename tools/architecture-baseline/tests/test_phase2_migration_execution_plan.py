from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLAN = REPO_ROOT / "docs" / "multilingual" / "phase-2" / "migration-execution-plan.md"

PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
    "zhang" + "qiao",
    "山" + "桥",
}

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required document: {path}")
    return path.read_text(encoding="utf-8")


class Phase2MigrationExecutionPlanTests(unittest.TestCase):
    def test_plan_exists_without_unresolved_markers_or_private_paths(self) -> None:
        plan = read(PLAN)

        self.assertNotRegex(plan, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, plan)

    def test_plan_preserves_phase2_boundaries(self) -> None:
        plan = read(PLAN)

        for token in (
            "Phase 2 does not automatically approve:",
            "English language support",
            "multi-target-language Vaults",
            "copying the old framework as a supported target runtime",
            "deleting or archiving the old Vault without a separate user confirmation",
            "committing private notes, media, manifests, personal paths, or migration artifacts",
        ):
            self.assertIn(token, plan)

    def test_plan_requires_migration_safety_gates(self) -> None:
        plan = read(PLAN)

        for token in (
            "Gate A: Pre-Freeze Readiness",
            "Gate B: Final Source Manifest",
            "Gate C: Target Migration Preview",
            "Gate D: Verification And Workflow Acceptance",
            "Gate E: Cutover Acceptance",
            "Gate F: Read-Only Observation",
        ):
            self.assertIn(token, plan)

    def test_plan_requires_core_migration_evidence(self) -> None:
        plan = read(PLAN)

        for token in (
            "source_vault",
            "target_vault",
            "preserve-data",
            "recreate-from-pack",
            "transform-with-map",
            "excluded_with_user_approval",
            "unclassified entries block cutover",
            "five Japanese workflow",
            "read-only observation",
            "separate user confirmation",
        ):
            self.assertIn(token, plan)

    def test_plan_lists_public_phase2_pr_sequence(self) -> None:
        plan = read(PLAN)

        for token in (
            "PR 2.0: Planning Gate",
            "PR 2.1: Migration Schema And Private Artifact Guard",
            "PR 2.2: Final Source Inventory Runner",
            "PR 2.3: Target Vault Rehearsal Runner",
            "PR 2.4: Data Copy And Transform Preview",
            "PR 2.5: Comparator And Workflow Acceptance",
            "PR 2.6: Cutover And Observation Runbook",
        ):
            self.assertIn(token, plan)


if __name__ == "__main__":
    unittest.main()
