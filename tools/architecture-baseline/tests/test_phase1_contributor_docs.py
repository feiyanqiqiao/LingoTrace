from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDE = REPO_ROOT / "docs" / "multilingual" / "phase-1" / "contributor-guide.md"
TOOLS_README = REPO_ROOT / "tools" / "README.md"

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


class Phase1ContributorDocsTests(unittest.TestCase):
    def test_contributor_guide_exists_without_unresolved_markers_or_private_paths(self) -> None:
        guide = read(GUIDE)

        self.assertNotRegex(guide, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, guide)

    def test_contributor_guide_points_to_real_phase1_entrypoints_and_tests(self) -> None:
        guide = read(GUIDE)

        for token in (
            "lingotrace/core",
            "lingotrace/packs/japanese",
            "lingotrace/init/japanese_vault.py",
            "lingotrace/migration",
            "python -m unittest discover -s tests/lingotrace -p 'test_*.py'",
            "bash tools/git/check-public-staged-files.sh",
        ):
            self.assertIn(token, guide)

    def test_contributor_guide_blocks_out_of_scope_work(self) -> None:
        guide = read(GUIDE)

        for token in (
            "Do not start new runtime work from old `jp-*` entries.",
            "Old `jp-*` skills are migration evidence only.",
            "English support has not shipped in Phase 1.",
            "Real private data migration has not shipped in Phase 1.",
            "Daily-use cutover has not shipped in Phase 1.",
            "Old Vault deletion has not shipped in Phase 1.",
            "Old-framework removal has not shipped in Phase 1.",
        ):
            self.assertIn(token, guide)

    def test_tools_readme_points_to_phase1_contributor_guide(self) -> None:
        tools = read(TOOLS_README)

        self.assertIn("Phase 1 Runtime", tools)
        self.assertIn("docs/multilingual/phase-1/contributor-guide.md", tools)


if __name__ == "__main__":
    unittest.main()
