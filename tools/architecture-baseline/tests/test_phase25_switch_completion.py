from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE25_GATE = REPO_ROOT / "docs/multilingual/phase-2/phase-2-5-switch-completion.md"
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
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

    def test_public_docs_point_to_new_framework_entrypoints(self) -> None:
        combined = read_required(README) + "\n" + read_required(AGENTS)

        for phrase in (
            "lingotrace.packs.japanese.workflows:listening_notes",
            "lingotrace.packs.japanese.workflows:source_notes",
            "lingotrace.packs.japanese.workflows:review_materials",
            "lingotrace.packs.japanese.workflows:speaking_cards",
            "lingotrace.packs.japanese.workflows:review_rollover",
        ):
            self.assertIn(phrase, combined)

        self.assertNotIn("Use the local skill documents as the source of truth", combined)
        self.assertNotIn("codex-skills/", combined)

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
