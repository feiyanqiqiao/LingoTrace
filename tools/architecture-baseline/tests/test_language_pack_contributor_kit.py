from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDE = REPO_ROOT / "docs/multilingual/language-pack-contributor-guide.md"
HANDOFF = REPO_ROOT / "docs/multilingual/language-pack-agent-handoff-template.md"
README = REPO_ROOT / "README.md"
PHASE1_CONTRIBUTOR_GUIDE = REPO_ROOT / "docs/multilingual/phase-1/contributor-guide.md"

UNRESOLVED_MARKER_PATTERN = r"\b(" + "|".join(("TB" + "D", "TO" + "DO")) + r")\b"
PRIVATE_PATH_MARKERS = {
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
    "zhang" + "qiao",
    "山" + "桥",
}


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required document: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


class LanguagePackContributorKitTests(unittest.TestCase):
    def test_contributor_guide_defines_four_layer_boundary_and_required_pack_files(self) -> None:
        guide = read_required(GUIDE)

        for token in (
            "core",
            "language pack",
            "Vault config",
            "private data",
            "lingotrace/packs/<language>/",
            "manifest.json",
            "paths.json",
            "fields.json",
            "agent_skills/SKILL.md",
            "validators.py",
            "workflows.py",
            "templates/",
            "views/",
        ):
            self.assertIn(token, guide)

        self.assertNotRegex(guide, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, guide)

    def test_contributor_guide_blocks_japanese_fallback_and_mechanical_field_copying(self) -> None:
        guide = read_required(GUIDE)

        for token in (
            "Do not copy Japanese fields mechanically",
            "reading",
            "accent_display",
            "kanji_diff",
            "Do not fall back to Japanese runtime",
            "Japanese workflow",
            "Japanese dictionary",
            "Japanese accent logic",
            "unsupported_capabilities",
            "failure_reason",
        ):
            self.assertIn(token, guide)

    def test_contributor_guide_records_current_infrastructure_limits(self) -> None:
        guide = read_required(GUIDE)

        for token in (
            "core context currently accepts only `target_language=ja`",
            "initializer is still Japanese-specific",
            "listening tooling is still Japanese-specific",
            "PHASE0_CAPABILITY_IDS",
            "source_notes",
            "review_materials",
            "review_rollover",
            "listening_notes",
            "speaking_cards",
            "stable",
            "experimental",
            "unsupported",
        ):
            self.assertIn(token, guide)

    def test_handoff_template_is_ready_for_other_agents(self) -> None:
        handoff = read_required(HANDOFF)

        for token in (
            "Target language:",
            "Explanation language:",
            "Initial capabilities:",
            "source_notes",
            "review_materials",
            "review_rollover",
            "Allowed directories:",
            "Forbidden directories:",
            "Read first:",
            "Required checks:",
            "PR acceptance criteria:",
            "Do not edit private Vault data.",
            "Do not implement English support by reusing Japanese runtime.",
        ):
            self.assertIn(token, handoff)

        self.assertNotRegex(handoff, UNRESOLVED_MARKER_PATTERN)
        for marker in PRIVATE_PATH_MARKERS:
            self.assertNotIn(marker, handoff)

    def test_handoff_template_points_to_real_existing_context_files(self) -> None:
        handoff = read_required(HANDOFF)

        for relative_path in (
            "docs/multilingual/language-pack-contributor-guide.md",
            "docs/lingotrace_multilingual_architecture_plan.md",
            "docs/multilingual/phase-0/language-pack-conformance-checklist.md",
            "lingotrace/packs/japanese/manifest.json",
            "lingotrace/packs/japanese/agent_skills/SKILL.md",
            "tests/lingotrace/packs/test_japanese_pack.py",
        ):
            self.assertIn(relative_path, handoff)
            self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path)

    def test_public_entry_docs_point_to_language_pack_contributor_kit(self) -> None:
        combined = read_required(README) + "\n" + read_required(PHASE1_CONTRIBUTOR_GUIDE)

        for token in (
            "docs/multilingual/language-pack-contributor-guide.md",
            "docs/multilingual/language-pack-agent-handoff-template.md",
            "Do not use the Japanese pack as a copy template",
        ):
            self.assertIn(token, combined)


if __name__ == "__main__":
    unittest.main()
