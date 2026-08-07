from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDE = REPO_ROOT / "docs/multilingual/language-pack-contributor-guide.md"
HANDOFF = REPO_ROOT / "docs/multilingual/language-pack-agent-handoff-template.md"
CAPABILITY_GUIDANCE = REPO_ROOT / "docs/multilingual/language-pack-capability-guidance.md"
CAPABILITY_GUIDANCE_ZH = REPO_ROOT / "docs/multilingual/language-pack-capability-guidance.zh.md"
REVIEW_MATERIALS_GUIDANCE = REPO_ROOT / "docs/multilingual/review-materials-user-stories.md"
LISTENING_GUIDANCE = REPO_ROOT / "docs/multilingual/listening-notes-user-stories.md"
JAPANESE_AGENT_SKILL = REPO_ROOT / "lingotrace/packs/japanese/agent_skills/SKILL.md"
README = REPO_ROOT / "README.md"
PHASE1_CONTRIBUTOR_GUIDE = REPO_ROOT / "docs/multilingual/history/phase-1/contributor-guide.md"

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
            "docs/multilingual/history/phase-0/language-pack-conformance-checklist.md",
            "docs/multilingual/listening-notes-user-stories.md",
            "docs/multilingual/review-materials-user-stories.md",
            "lingotrace/packs/japanese/manifest.json",
            "lingotrace/packs/japanese/agent_skills/SKILL.md",
            "tests/lingotrace/packs/test_japanese_pack.py",
        ):
            self.assertIn(relative_path, handoff)
            self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path)

    def test_review_materials_guidance_is_indexed_as_reference_guidance(self) -> None:
        guide = read_required(CAPABILITY_GUIDANCE)
        guide_zh = read_required(CAPABILITY_GUIDANCE_ZH)
        review_materials = read_required(REVIEW_MATERIALS_GUIDANCE)

        self.assertIn(
            "| `review_materials` | Reference Guidance | `docs/multilingual/review-materials-user-stories.md` |",
            guide,
        )
        self.assertIn(
            "| `review_materials` | Reference Guidance | `docs/multilingual/review-materials-user-stories.md` |",
            guide_zh,
        )
        self.assertNotIn("`review_materials` | Planned Reference Guidance", guide)
        self.assertNotIn("`review_materials` | Planned Reference Guidance", guide_zh)
        for token in (
            "jp-review-material-maintainer",
            "focus-first",
            "base lexicon",
            "grammar cards",
            "error cards",
            "kanji-difference",
            "daily checklist",
            "Capability Input Modes",
            "three mutually exclusive input modes",
            "`item` updates preserve the existing readable body",
            "existing dated daily note",
            "managed checklist markers",
            "pathless embed is accepted only when its filename resolves to exactly one Vault attachment",
            "active focus card reappears in a new source note",
            "same canonical source note",
            "reset to `review_stage: day0`",
            "`next_review` at the current extraction date",
            "No-input legacy discovery is preview-only",
        ):
            self.assertIn(token, review_materials)

    def test_listening_guidance_is_indexed_as_reference_guidance(self) -> None:
        guide = read_required(CAPABILITY_GUIDANCE)
        guide_zh = read_required(CAPABILITY_GUIDANCE_ZH)
        listening = read_required(LISTENING_GUIDANCE)

        self.assertIn(
            "| `listening_notes` | Reference Guidance | `docs/multilingual/listening-notes-user-stories.md` |",
            guide,
        )
        self.assertIn(
            "| `listening_notes` | Reference Guidance | `docs/multilingual/listening-notes-user-stories.md` |",
            guide_zh,
        )
        self.assertNotIn("`listening_notes` | Planned Reference Guidance", guide)
        self.assertNotIn("`listening_notes` | Planned Reference Guidance", guide_zh)
        for token in (
            "jp-listening-script-generator",
            "ListenKit",
            "extensive",
            "intensive",
            "reviewed slice manifest",
            "productive-chunk curation",
            "pitch-accent markers",
            "Multi-engine ASR comparison",
            "unsupported",
        ):
            self.assertIn(token, listening)

    def test_japanese_listening_guidance_records_accent_annotation_policy(self) -> None:
        listening = read_required(LISTENING_GUIDANCE)

        for token in (
            "Language-Specific Pronunciation Cues",
            "language-pack-owned behavior",
            "公園⓪",
            "京都①",
            "こいしい③",
            "こいし＼い",
            "test_learning_package_renders_kana_accent_as_downstep_marker",
            "New Japanese intensive listening blocks",
            "Existing listening notes should not be bulk-rewritten",
            "## 精听学习包",
            "## 脚本",
            "plain by default",
            "selective high-value annotation",
            "must not fabricate",
        ):
            self.assertIn(token, listening)

    def test_listening_guidance_records_remaining_migrated_skill_rules(self) -> None:
        listening = read_required(LISTENING_GUIDANCE)

        for token in (
            "Short-Choice And Exam Listening Structure",
            "question numbers and `1/2/3` option structure",
            "slow-copy retry",
            "Listening Frontmatter And Dashboard Readiness",
            "weak_points",
            "practice_focus",
            "Dialogue And Numbered-Dialogue Rendering Contract",
            "A：/B：",
            "must not invent `C：`",
            "Use Dry-Run, Better Naming, And Uncertain-Output Gate",
            "topic-bearing filename",
            "Single-Item Safety And No Default Batch Writes",
            "Batch mode is not a default user workflow",
            "`## 素材说明` records the source, generation route, known limits, and review needs",
            "low-quality `extensive` note as an intermediate artifact",
            "Legacy notes that already contain `## 精听学习包` are treated as `intensive`",
            "test_compare_engine_persists_asr_disagreement_report_without_replacing_primary",
            "lightweight artifact schema",
            "本地候选",
            "待确认",
            "Reviewed listening chunks remain candidates",
        ):
            self.assertIn(token, listening)

    def test_japanese_agent_skill_auto_merges_asr_disagreements(self) -> None:
        skill = read_required(JAPANESE_AGENT_SKILL)
        listening = read_required(LISTENING_GUIDANCE)

        for token in (
            "status: llm_merge_required",
            "llm_merge_request_path",
            "Codex",
            "Gemini",
            "agent-runtime",
            "--reviewed-transcript",
            "confidence",
            "rationale_zh",
            "same user task",
            "Do not stop at the first `llm_merge_required`",
            "dual-ASR validation enabled by default for every listening note",
            "Do not pass `--single-asr` unless the user explicitly requests",
            "absolute, stable temporary `llm_merge_request_path`",
            "`--merge-request <llm_merge_request_path>`",
        ):
            self.assertIn(token, skill)
        for token in (
            "structured merge request",
            "audio hash",
            "merge-request identity",
            "which model performed the merge",
            "low-confidence decisions still block",
        ):
            self.assertIn(token, listening)

    def test_user_story_test_references_point_to_real_tests(self) -> None:
        user_story_docs = sorted((REPO_ROOT / "docs" / "multilingual").glob("*user-stories.md"))
        test_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for parent in (REPO_ROOT / "tests", REPO_ROOT / "tools")
            for path in parent.rglob("test_*.py")
        )

        missing: list[str] = []
        for doc in user_story_docs:
            for test_name in sorted(set(re.findall(r"`(test_[A-Za-z0-9_]+)`", read_required(doc)))):
                if f"def {test_name}" not in test_sources:
                    missing.append(f"{doc.relative_to(REPO_ROOT)}::{test_name}")

        self.assertEqual([], missing)

    def test_user_story_docs_declare_language_applicability_matrix(self) -> None:
        user_story_docs = sorted((REPO_ROOT / "docs" / "multilingual").glob("*user-stories.md"))
        self.assertGreater(len(user_story_docs), 0)

        for doc in user_story_docs:
            text = read_required(doc)
            table_headers = [
                [cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in text.splitlines()
                if line.startswith("|") and "User story" in line
            ]
            with self.subTest(doc=doc.name):
                self.assertIn("## Language Applicability Matrix", text)
                self.assertIn(["User story", "Shared", "Japanese", "English", "Notes"], table_headers)
                self.assertRegex(text, r"\| `US-\d+")
                for label in (
                    "`Required`",
                    "`Optional`",
                    "`Language-Specific`",
                    "`Covered`",
                    "`Partial`",
                    "`Planned`",
                    "`Unsupported`",
                    "`N/A`",
                ):
                    self.assertIn(label, text)

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
