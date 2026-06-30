from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE25_GATE = REPO_ROOT / "docs/multilingual/phase-2/phase-2-5-switch-completion.md"
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
USER_GUIDE = REPO_ROOT / "docs/USER_GUIDE.md"
AGENT_SKILL = REPO_ROOT / "lingotrace/packs/japanese/agent_skills/SKILL.md"
PACK_VIEW = REPO_ROOT / "lingotrace/packs/japanese/views/total-training.base"


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


class Phase25SwitchCompletionTests(unittest.TestCase):
    def test_completion_gate_document_exists_without_unresolved_markers(self) -> None:
        body = read_required(PHASE25_GATE)

        self.assertNotIn("TB" + "D", body)
        self.assertNotIn("TO" + "DO", body)
        for phrase in (
            "five Japanese workflows",
            "core write guard",
            "legacy root retirement",
            "read-only observation",
            "separate user confirmation",
        ):
            self.assertIn(phrase, body)

    def test_japanese_pack_contains_skill_first_agent_entry(self) -> None:
        skill = read_required(AGENT_SKILL)

        for phrase in (
            "请把这段音频做成精听稿",
            "帮我把这篇材料整理成日语学习笔记",
            "把这个词加入复习",
            "这句话很实用，帮我做成口语卡",
            "今天复习结束了，帮我结算",
            "listening_notes",
            "source_notes",
            "review_materials",
            "speaking_cards",
            "review_rollover",
            "Agent Skill must not write Vault files directly",
            "core write guard",
        ):
            self.assertIn(phrase, skill)

        self.assertNotIn("codex-skills/", skill)

    def test_japanese_pack_agent_skill_requires_intent_recognition(self) -> None:
        skill = read_required(AGENT_SKILL)

        for phrase in (
            "## Intent Recognition",
            "infer the user's real learning intent",
            "Do not match only the example phrases",
            "Audio or video to listening material",
            "Source material to study note",
            "Word, grammar, pronunciation, or error to review",
            "Useful sentence to active output",
            "End-of-day review settlement",
            "Dashboard or view maintenance",
            "请更新总训练表",
            "ask one short clarification question",
        ):
            self.assertIn(phrase, skill)

        for phrase in (
            "处理一下总训练表",
            "总训练表有点问题",
            "词汇卡要显示重音和常见搭配",
        ):
            self.assertIn(phrase, skill)

    def test_clear_review_rollover_requests_do_not_need_second_confirmation(self) -> None:
        skill = read_required(AGENT_SKILL)
        guide = read_required(USER_GUIDE)

        for phrase in (
            "Clear review-settlement requests do not need a second user confirmation",
            "preview -> apply -> second preview",
            "If preview reports errors, stop before apply",
            "Ambiguous requests still require clarification",
        ):
            self.assertIn(phrase, skill)

        self.assertIn("明确的复习结算请求不需要二次确认", guide)
        self.assertNotIn("你确认后才会保存状态变化", guide)

    def test_review_material_agent_skill_requires_confirmation_for_risky_writes(self) -> None:
        skill = read_required(AGENT_SKILL)

        for phrase in (
            "structured review item",
            "deterministic routing",
            "duplicate handling",
            "focus/base restoration",
            "If an image-backed item is not clearly readable",
            "stop and ask before writing",
            "Merges, moves, overwrites, and broad rewrites still require user confirmation",
        ):
            self.assertIn(phrase, skill)

    def test_public_user_docs_are_natural_language_first(self) -> None:
        combined = read_required(README) + "\n" + read_required(USER_GUIDE)

        for phrase in (
            "自然语言",
            "Agent Skill",
            "请把这段音频做成精听稿",
            "今天复习结束了，帮我结算",
            "保存到你的日语学习库",
            "真实学习意图",
            "请更新总训练表",
        ):
            self.assertIn(phrase, combined)

        for stale_phrase in (
            "请更新总训练表”这类可能同时表示复习结算或视图维护",
            "请更新总训练表”可能表示结算今天的复习",
        ):
            self.assertNotIn(stale_phrase, combined)

        for forbidden in (
            "写入新框架 Vault",
            "调用 workflow entrypoint",
            "传入 artifact",
            "执行 apply mode",
            "target Vault",
            "CommandReport",
            "lingotrace.packs.japanese.workflows:",
            "codex-skills/",
        ):
            self.assertNotIn(forbidden, combined)

    def test_total_training_intent_boundary_examples_are_explicit(self) -> None:
        combined = (
            read_required(README)
            + "\n"
            + read_required(USER_GUIDE)
            + "\n"
            + read_required(AGENT_SKILL)
        )

        for phrase in (
            "更新总训练表",
            "请更新总训练表",
            "明确的每日复习结算请求",
            "处理一下总训练表",
            "总训练表有点问题",
            "Dashboard or view maintenance",
            "filters, columns, formulas, or sort order",
        ):
            self.assertIn(phrase, combined)

    def test_agents_doc_points_to_agent_skill_and_hidden_runtime_contract(self) -> None:
        agents = read_required(AGENTS)

        self.assertIn("lingotrace/packs/japanese/agent_skills/SKILL.md", agents)
        self.assertIn("natural-language operating entry", agents)
        self.assertIn("Do not ask users to mention workflow entrypoints", agents)
        self.assertIn("LingoTrace core and Japanese pack", agents)
        self.assertIn("core write guard", agents)
        self.assertNotIn("Use the local skill documents as the source of truth", agents)
        self.assertNotIn("codex-skills/", agents)

    def test_legacy_roots_are_not_public_tracked_operational_surfaces(self) -> None:
        files = tracked_files()

        for file in files:
            self.assertFalse(file.startswith("codex-skills/"), file)
            self.assertFalse(file.startswith("学习系统/"), file)
            self.assertFalse(file.startswith("系统配置/"), file)

    def test_total_training_view_has_single_canonical_source(self) -> None:
        body = read_required(PACK_VIEW)

        self.assertIn("今日总训练", body)
        self.assertIn("columnSize:", body)
        self.assertIn("file.name: 260", body)
        self.assertNotIn("Today done", body)


if __name__ == "__main__":
    unittest.main()
