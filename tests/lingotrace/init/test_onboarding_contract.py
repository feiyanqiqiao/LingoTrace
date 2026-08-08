from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class OnboardingDocumentationContractTests(unittest.TestCase):
    def test_readme_exposes_one_sentence_upstream_bootstrap(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        expected_url = (
            "https://raw.githubusercontent.com/feiyanqiqiao/LingoTrace/main/"
            "docs/learner-agent-setup.md"
        )
        self.assertIn(expected_url, readme)
        self.assertIn("开发者初始化协议", readme)

    def test_learner_protocol_uses_minimal_runtime_and_safe_vault_preview(self) -> None:
        guide = (REPO_ROOT / "docs" / "learner-agent-setup.md").read_text(encoding="utf-8")
        self.assertIn("sparse-checkout set /lingotrace/", guide)
        self.assertIn("python3 -m lingotrace.init doctor", guide)
        self.assertIn("python3 -m lingotrace.init resolve-runtime", guide)
        preview_position = guide.index("先执行预览，不加 `--apply`")
        apply_position = guide.index("增加 `--apply`")
        self.assertLess(preview_position, apply_position)
        self.assertIn("不要把 Obsidian CLI 当成桌面客户端", guide)
        self.assertIn("可以延期", guide)

    def test_developer_protocol_defines_fork_branch_pr_and_ci_lifecycle(self) -> None:
        guide = (REPO_ROOT / "docs" / "developer-agent-setup.md").read_text(encoding="utf-8")
        for required in (
            "origin` 指向用户自己的 fork",
            "upstream` 指向正式上游",
            "git switch -c codex/add-korean-pack",
            "gh pr create",
            "gh pr checks",
            "git fetch --all --prune",
        ):
            self.assertIn(required, guide)
        self.assertIn("CI 通过不等于已合并", guide)

    def test_document_index_keeps_learner_and_developer_entries_separate(self) -> None:
        index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("## 用户与运行", index)
        self.assertIn("learner-agent-setup.md", index)
        self.assertIn("## 开发与贡献", index)
        self.assertIn("developer-agent-setup.md", index)


if __name__ == "__main__":
    unittest.main()
