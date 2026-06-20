from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE1_DESIGN = REPO_ROOT / "docs" / "multilingual" / "phase-1" / "detailed-design.md"

PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
    "zhang" + "qiao",
    "山" + "桥",
}

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"


def read_design() -> str:
    if not PHASE1_DESIGN.exists():
        raise AssertionError(f"missing Phase 1 detailed design: {PHASE1_DESIGN}")
    return PHASE1_DESIGN.read_text(encoding="utf-8")


class Phase1DetailedDesignTests(unittest.TestCase):
    def test_phase1_design_exists_without_unresolved_markers_or_private_paths(self) -> None:
        design = read_design()

        self.assertNotRegex(design, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, design)

    def test_phase1_design_keeps_runtime_scope_separate_from_blocked_work(self) -> None:
        design = read_design()

        for token in (
            "Phase 1 detailed design",
            "no English functionality",
            "no real private data migration",
            "no daily-use cutover",
            "no old Vault deletion",
            "not a compatibility mode",
            "Phase 2",
        ):
            self.assertIn(token, design)

    def test_phase1_design_assigns_each_workstream_to_one_owner(self) -> None:
        design = read_design()

        for token in (
            "core",
            "Japanese language pack",
            "new Vault initialization",
            "temporary migration",
            "external adapter boundary",
            "public documentation",
        ):
            self.assertIn(token, design)

        self.assertIn("Workstream Ownership Matrix", design)
        self.assertRegex(design, r"\|\s*Core runtime skeleton\s*\|\s*core\s*\|")
        self.assertRegex(design, r"\|\s*Japanese pack boundary\s*\|\s*Japanese language pack\s*\|")
        self.assertRegex(design, r"\|\s*New Japanese Vault scaffold\s*\|\s*new Vault initialization\s*\|")
        self.assertRegex(design, r"\|\s*Migration dry-run inventory\s*\|\s*temporary migration\s*\|")

    def test_phase1_design_defines_public_interfaces_before_tasks(self) -> None:
        design = read_design()

        for token in (
            "Vault context loader",
            "Language pack manifest loader",
            "Capability registry",
            "Path role resolver",
            "Review-card shell service",
            "Write transaction guard",
            "Conformance test suite",
            "Japanese pack manifest",
            "initializer dry-run",
            "migration inventory dry-run",
        ):
            self.assertIn(token, design)

    def test_phase1_design_keeps_japanese_migration_data_preservation_explicit(self) -> None:
        design = read_design()

        for token in (
            "preserve-data",
            "recreate-from-pack",
            "transform-with-map",
            "remove-after-cutover",
            "Japanese fields remain Japanese pack fields",
            "reading",
            "accent_display",
            "meaning_zh",
            "kanji_diff",
            "kanji_diff_pairs",
        ):
            self.assertIn(token, design)


if __name__ == "__main__":
    unittest.main()
