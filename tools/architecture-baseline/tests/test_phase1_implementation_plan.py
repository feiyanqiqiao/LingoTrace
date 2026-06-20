from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLAN = REPO_ROOT / "docs" / "multilingual" / "phase-1" / "implementation-plan.md"

PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
    "zhang" + "qiao",
    "山" + "桥",
}

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"


def read_plan() -> str:
    if not PLAN.exists():
        raise AssertionError(f"missing Phase 1 implementation plan: {PLAN}")
    return PLAN.read_text(encoding="utf-8")


class Phase1ImplementationPlanTests(unittest.TestCase):
    def test_plan_exists_without_unresolved_markers_or_private_paths(self) -> None:
        plan = read_plan()

        self.assertNotRegex(plan, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, plan)

    def test_plan_defines_dependency_gated_pr_sequence(self) -> None:
        plan = read_plan()

        for token in (
            "Dependency-Gated PR Sequence",
            "PR 1: Core Contract Skeleton",
            "PR 2: Japanese Pack Boundary",
            "PR 3: New Japanese Vault Initialization",
            "PR 4: Temporary Migration Inventory",
            "PR 5: Contributor Documentation",
            "No PR may combine core runtime, Japanese pack boundary, new Vault initialization, temporary migration, and contributor documentation as one implementation change.",
        ):
            self.assertIn(token, plan)

    def test_plan_locks_pr1_public_files_and_acceptance(self) -> None:
        plan = read_plan()

        for token in (
            "lingotrace/core/reports.py",
            "lingotrace/core/context.py",
            "lingotrace/core/manifests.py",
            "lingotrace/core/capabilities.py",
            "lingotrace/core/paths.py",
            "lingotrace/core/review_cards.py",
            "lingotrace/core/transactions.py",
            "tests/lingotrace/core/test_reports.py",
            "tests/lingotrace/core/test_context.py",
            "tests/lingotrace/core/test_manifests.py",
            "tests/lingotrace/core/test_capabilities.py",
            "tests/lingotrace/core/test_paths.py",
            "tests/lingotrace/core/test_review_cards.py",
            "tests/lingotrace/core/test_transactions.py",
            "Vault context loader rejects missing or incompatible context before write.",
            "Shared command report envelope is deterministic and safe for public CI logs.",
        ):
            self.assertIn(token, plan)

    def test_plan_requires_runtime_tests_after_pr1(self) -> None:
        plan = read_plan()

        self.assertIn("After PR 1 creates `tests/lingotrace/`", plan)
        self.assertIn(
            "/opt/homebrew/bin/python3.14 -m unittest discover -s tests/lingotrace -p 'test_*.py'",
            plan,
        )
        self.assertIn("python -m unittest discover -s tests/lingotrace -p 'test_*.py'", plan)

    def test_plan_keeps_phase1_non_goals_explicit(self) -> None:
        plan = read_plan()

        for token in (
            "English functionality.",
            "Real private data migration.",
            "Daily-use cutover.",
            "Old Vault deletion.",
            "Old-framework removal.",
            "Runtime fallback to Japanese behavior.",
            "Broad renaming of Japanese learning fields.",
            "Long-term compatibility mode for old `jp-*` entries.",
        ):
            self.assertIn(token, plan)

    def test_plan_uses_checkbox_steps_for_pr1(self) -> None:
        plan = read_plan()

        pr1_section = plan.split("## 6. PR 2: Japanese Pack Boundary", 1)[0]
        steps = re.findall(r"^- \[ \] ", pr1_section, flags=re.MULTILINE)
        self.assertGreaterEqual(len(steps), 18)


if __name__ == "__main__":
    unittest.main()
