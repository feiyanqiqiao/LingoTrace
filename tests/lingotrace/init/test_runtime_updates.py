from __future__ import annotations

import json
import tempfile
import unittest
from collections import defaultdict
from datetime import date
from pathlib import Path

from lingotrace.init.runtime_updates import (
    GitResult,
    apply_runtime_update,
    check_runtime_update,
    runtime_update_check_relative_path,
)


CHECK_DATE = date(2026, 8, 8)
OFFICIAL_URL = "https://github.com/feiyanqiqiao/LingoTrace.git"


class FakeGit:
    def __init__(self, responses: dict[tuple[str, ...], GitResult | list[GitResult]]) -> None:
        self.responses: dict[tuple[str, ...], list[GitResult]] = defaultdict(list)
        for command, result in responses.items():
            self.responses[command] = list(result) if isinstance(result, list) else [result]
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, _runtime: Path, arguments: list[str]) -> GitResult:
        command = tuple(arguments)
        self.calls.append(command)
        results = self.responses.get(command, [])
        if not results:
            return GitResult(99, stderr=f"unexpected command: {command}")
        return results.pop(0)


class RuntimeUpdateTests(unittest.TestCase):
    def test_official_checkout_reports_structured_updates_and_checks_only_once_per_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            git = _official_update_git()

            first = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=git,
            )
            first_call_count = len(git.calls)
            second = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=git,
            )

            state = json.loads(
                (vault / runtime_update_check_relative_path("linux")).read_text(encoding="utf-8")
            )

        self.assertTrue(first.accepted, first.to_dict())
        self.assertEqual("official", first.artifacts["checkout_type"])
        self.assertEqual("updates_available", first.artifacts["status"])
        self.assertEqual("2", first.artifacts["update_count"])
        commits = json.loads(first.artifacts["commits"])
        self.assertEqual("feat: add guided setup", commits[0]["title"])
        self.assertEqual("already_checked_today", second.artifacts["status"])
        self.assertEqual(first_call_count, len(git.calls))
        self.assertEqual("updates_available", state["result"])

    def test_platform_state_files_do_not_suppress_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            mac_git = _official_up_to_date_git()
            linux_git = _official_up_to_date_git()

            mac = check_runtime_update(
                vault,
                runtime,
                platform_name="macos",
                check_date=CHECK_DATE,
                git_runner=mac_git,
            )
            linux = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=linux_git,
            )

            self.assertTrue((vault / runtime_update_check_relative_path("macos")).is_file())
            self.assertTrue((vault / runtime_update_check_relative_path("linux")).is_file())

        self.assertEqual("up_to_date", mac.artifacts["status"])
        self.assertEqual("up_to_date", linux.artifacts["status"])
        self.assertIn(("fetch", "--quiet", "origin", "main"), linux_git.calls)

    def test_fork_reports_updates_but_automatic_apply_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            check = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=_fork_update_git(),
            )
            apply = apply_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                mode="apply",
                git_runner=_fork_update_git(),
            )

        self.assertTrue(check.accepted, check.to_dict())
        self.assertEqual("fork_updates_available", check.artifacts["status"])
        self.assertEqual("manual_fork_sync", check.artifacts["user_action"])
        self.assertFalse(apply.accepted)
        self.assertEqual("fork_update_requires_user_action", apply.errors[0].code)

    def test_fork_without_upstream_remote_checks_canonical_url_without_adding_a_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            canonical_url = "https://github.com/feiyanqiqiao/LingoTrace.git"
            git = FakeGit(
                {
                    ("rev-parse", "--is-inside-work-tree"): GitResult(0, "true\n"),
                    ("remote",): GitResult(0, "origin\n"),
                    ("remote", "get-url", "origin"): GitResult(
                        0, "git@github.com:example/LingoTrace.git\n"
                    ),
                    ("fetch", "--quiet", canonical_url, "main"): GitResult(0),
                    ("rev-parse", "HEAD"): GitResult(0, "fork-head\n"),
                    ("rev-parse", "FETCH_HEAD"): GitResult(0, "upstream-head\n"),
                    ("rev-list", "--count", "HEAD..FETCH_HEAD"): GitResult(0, "1\n"),
                    (
                        "log",
                        "--no-merges",
                        "--max-count=20",
                        "--format=%H%x1f%s%x1f%b%x1e",
                        "HEAD..FETCH_HEAD",
                    ): GitResult(0, "333\x1fdocs: clarify setup\x1f\x1e"),
                }
            )
            report = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=git,
            )

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("fork", report.artifacts["checkout_type"])
        self.assertEqual(canonical_url, report.artifacts["canonical_remote"])
        self.assertEqual("manual_fork_sync", report.artifacts["user_action"])

    def test_official_apply_requires_preview_or_explicit_apply_and_fast_forwards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            preview = apply_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                mode="preview",
                git_runner=_official_update_git(),
            )
            apply_git = _official_apply_git()
            applied = apply_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                mode="apply",
                git_runner=apply_git,
            )

        self.assertEqual("dry-run", preview.mode)
        self.assertEqual("git_pull_ff_only", preview.planned_writes[0]["action"])
        self.assertTrue(applied.accepted, applied.to_dict())
        self.assertEqual("updated", applied.artifacts["status"])
        self.assertEqual("bbb", applied.artifacts["local_head"])
        self.assertIn(("pull", "--ff-only", "origin", "main"), apply_git.calls)

    def test_dirty_official_runtime_is_never_pulled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            git = _official_update_git()
            git.responses[("branch", "--show-current")] = [GitResult(0, "main\n")]
            git.responses[("status", "--porcelain")] = [GitResult(0, " M lingotrace/init/vault.py\n")]

            report = apply_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                mode="apply",
                git_runner=git,
            )

        self.assertFalse(report.accepted)
        self.assertEqual("runtime_worktree_not_clean", report.errors[0].code)
        self.assertNotIn(("pull", "--ff-only", "origin", "main"), git.calls)

    def test_network_failure_is_recorded_as_warning_and_does_not_block_learning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            git = FakeGit(
                {
                    ("rev-parse", "--is-inside-work-tree"): GitResult(0, "true\n"),
                    ("remote",): GitResult(0, "origin\n"),
                    ("remote", "get-url", "origin"): GitResult(0, f"{OFFICIAL_URL}\n"),
                    ("fetch", "--quiet", "origin", "main"): GitResult(1, stderr="offline"),
                }
            )
            report = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=git,
            )

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("check_unavailable", report.artifacts["status"])
        self.assertEqual("continue_learning", report.artifacts["user_action"])
        self.assertIn("upstream_check_unavailable", {finding.code for finding in report.warnings})

    def test_ssh_official_remote_is_recognized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault, runtime = _make_roots(Path(tmp))
            git = _official_up_to_date_git(url="git@github.com:feiyanqiqiao/LingoTrace.git")
            report = check_runtime_update(
                vault,
                runtime,
                platform_name="linux",
                check_date=CHECK_DATE,
                git_runner=git,
            )

        self.assertEqual("official", report.artifacts["checkout_type"])


def _make_roots(root: Path) -> tuple[Path, Path]:
    vault = root / "vault"
    runtime = root / "runtime"
    (runtime / "lingotrace").mkdir(parents=True)
    (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")
    return vault, runtime


def _base_official_responses(url: str = OFFICIAL_URL) -> dict[tuple[str, ...], GitResult]:
    return {
        ("rev-parse", "--is-inside-work-tree"): GitResult(0, "true\n"),
        ("remote",): GitResult(0, "origin\n"),
        ("remote", "get-url", "origin"): GitResult(0, f"{url}\n"),
        ("fetch", "--quiet", "origin", "main"): GitResult(0),
        ("rev-parse", "refs/remotes/origin/main"): GitResult(0, "bbb\n"),
    }


def _official_update_git() -> FakeGit:
    responses = _base_official_responses()
    responses.update(
        {
            ("rev-parse", "HEAD"): GitResult(0, "aaa\n"),
            ("rev-list", "--count", "HEAD..refs/remotes/origin/main"): GitResult(0, "2\n"),
            (
                "log",
                "--no-merges",
                "--max-count=20",
                "--format=%H%x1f%s%x1f%b%x1e",
                "HEAD..refs/remotes/origin/main",
            ): GitResult(0, "111\x1ffeat: add guided setup\x1fFriendly setup.\x1e"),
        }
    )
    return FakeGit(responses)


def _official_up_to_date_git(url: str = OFFICIAL_URL) -> FakeGit:
    responses = _base_official_responses(url)
    responses.update(
        {
            ("rev-parse", "HEAD"): GitResult(0, "bbb\n"),
            ("rev-list", "--count", "HEAD..refs/remotes/origin/main"): GitResult(0, "0\n"),
        }
    )
    return FakeGit(responses)


def _fork_update_git() -> FakeGit:
    return FakeGit(
        {
            ("rev-parse", "--is-inside-work-tree"): GitResult(0, "true\n"),
            ("remote",): GitResult(0, "origin\nupstream\n"),
            ("remote", "get-url", "origin"): GitResult(
                0, "https://github.com/example/LingoTrace.git\n"
            ),
            ("remote", "get-url", "upstream"): GitResult(0, f"{OFFICIAL_URL}\n"),
            ("fetch", "--quiet", "upstream", "main"): GitResult(0),
            ("rev-parse", "HEAD"): GitResult(0, "fork-head\n"),
            ("rev-parse", "refs/remotes/upstream/main"): GitResult(0, "upstream-head\n"),
            ("rev-list", "--count", "HEAD..refs/remotes/upstream/main"): GitResult(0, "1\n"),
            (
                "log",
                "--no-merges",
                "--max-count=20",
                "--format=%H%x1f%s%x1f%b%x1e",
                "HEAD..refs/remotes/upstream/main",
            ): GitResult(0, "222\x1ffix: preserve notes\x1f\x1e"),
        }
    )


def _official_apply_git() -> FakeGit:
    git = _official_update_git()
    git.responses[("rev-parse", "HEAD")] = [GitResult(0, "aaa\n"), GitResult(0, "bbb\n")]
    git.responses[("branch", "--show-current")] = [GitResult(0, "main\n")]
    git.responses[("status", "--porcelain")] = [GitResult(0, "")]
    git.responses[("merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/main")] = [GitResult(0)]
    git.responses[("pull", "--ff-only", "origin", "main")] = [GitResult(0, "Updating aaa..bbb\n")]
    return git


if __name__ == "__main__":
    unittest.main()
