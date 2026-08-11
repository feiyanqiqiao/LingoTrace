from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.init.executables import find_executable
from lingotrace.init.runtime_connections import current_platform


CANONICAL_REPOSITORY = "feiyanqiqiao/lingotrace"
CANONICAL_GIT_URL = "https://github.com/feiyanqiqiao/LingoTrace.git"
RUNTIME_UPDATE_CHECK_DIRECTORY = ".lingotrace/runtime-update-checks"
RUNTIME_UPDATE_CHECK_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


GitRunner = Callable[[Path, list[str]], GitResult]


def runtime_update_check_relative_path(platform_name: str | None = None) -> str:
    return f"{RUNTIME_UPDATE_CHECK_DIRECTORY}/{current_platform(platform_name)}.json"


def check_runtime_update(
    vault_root: str | Path,
    runtime_root: str | Path,
    *,
    platform_name: str | None = None,
    check_date: date | None = None,
    force: bool = False,
    git_runner: GitRunner | None = None,
) -> CommandReport:
    vault = Path(vault_root)
    runtime = Path(runtime_root)
    platform_id = current_platform(platform_name)
    today = check_date or date.today()
    relative_state_path = runtime_update_check_relative_path(platform_id)
    state_path = vault / relative_state_path
    runner = git_runner or _run_git
    warnings: list[Finding] = []

    previous_state = _read_state(state_path)
    if (
        not force
        and previous_state is not None
        and previous_state.get("checked_date") == today.isoformat()
        and previous_state.get("runtime_root") == str(runtime)
    ):
        return CommandReport(
            command="check-runtime-update",
            mode="check",
            read_files=[relative_state_path],
            artifacts={
                "checkout_type": str(previous_state.get("checkout_type", "unknown")),
                "status": "already_checked_today",
                "state_path": relative_state_path,
                "update_count": str(previous_state.get("update_count", 0)),
                "user_action": "continue_learning",
            },
        )

    if previous_state is None and state_path.exists():
        warnings.append(
            Finding(
                code="invalid_runtime_update_state",
                message="The previous daily update state could not be read and will be replaced.",
                severity="warning",
                path=relative_state_path,
            )
        )

    if not (runtime / "lingotrace" / "__init__.py").is_file():
        return CommandReport(
            command="check-runtime-update",
            mode="check",
            exit_code=1,
            errors=[
                Finding(
                    code="runtime_root_invalid",
                    message="The selected runtime root does not contain lingotrace/__init__.py.",
                    path=str(runtime),
                )
            ],
        )

    repository = runner(runtime, ["rev-parse", "--is-inside-work-tree"])
    if repository.returncode != 0 or repository.stdout.strip() != "true":
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="git_runtime_unavailable",
            message="This runtime is not a Git checkout, so automatic upstream checks are unavailable.",
        )

    remotes_result = runner(runtime, ["remote"])
    if remotes_result.returncode != 0:
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="git_remote_check_failed",
            message=_git_failure_message("Git remotes could not be inspected", remotes_result),
        )

    remote_urls: dict[str, str] = {}
    for remote in [item.strip() for item in remotes_result.stdout.splitlines() if item.strip()]:
        url_result = runner(runtime, ["remote", "get-url", remote])
        if url_result.returncode == 0 and url_result.stdout.strip():
            remote_urls[remote] = url_result.stdout.strip()

    checkout_type, canonical_source = _classify_checkout(remote_urls)
    if canonical_source is None:
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="canonical_remote_not_found",
            message=(
                "The official LingoTrace upstream remote could not be identified, "
                "so no automatic update was attempted."
            ),
            checkout_type=checkout_type,
        )

    fetch = runner(runtime, ["fetch", "--quiet", canonical_source, "main"])
    if fetch.returncode != 0:
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="upstream_check_unavailable",
            message=_git_failure_message("The official upstream could not be reached", fetch),
            checkout_type=checkout_type,
        )

    upstream_ref = (
        f"refs/remotes/{canonical_source}/main" if canonical_source in remote_urls else "FETCH_HEAD"
    )
    local_head_result = runner(runtime, ["rev-parse", "HEAD"])
    upstream_head_result = runner(runtime, ["rev-parse", upstream_ref])
    if local_head_result.returncode != 0 or upstream_head_result.returncode != 0:
        failed = local_head_result if local_head_result.returncode != 0 else upstream_head_result
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="runtime_revision_unavailable",
            message=_git_failure_message("Runtime revisions could not be compared", failed),
            checkout_type=checkout_type,
        )

    local_head = local_head_result.stdout.strip()
    upstream_head = upstream_head_result.stdout.strip()
    count_result = runner(runtime, ["rev-list", "--count", f"HEAD..{upstream_ref}"])
    if count_result.returncode != 0:
        return _record_unavailable_check(
            vault,
            runtime,
            platform_id,
            today,
            relative_state_path,
            warnings,
            code="runtime_revision_compare_failed",
            message=_git_failure_message("Available updates could not be counted", count_result),
            checkout_type=checkout_type,
        )

    try:
        update_count = int(count_result.stdout.strip())
    except ValueError:
        update_count = 0
        warnings.append(
            Finding(
                code="invalid_update_count",
                message="Git returned an invalid update count; treating the runtime as up to date.",
                severity="warning",
            )
        )

    commits: list[dict[str, str]] = []
    if update_count > 0:
        log_result = runner(
            runtime,
            [
                "log",
                "--no-merges",
                "--max-count=20",
                "--format=%H%x1f%s%x1f%b%x1e",
                f"HEAD..{upstream_ref}",
            ],
        )
        if log_result.returncode == 0:
            commits = _parse_commit_log(log_result.stdout)
        else:
            warnings.append(
                Finding(
                    code="update_summary_unavailable",
                    message="Updates were found, but their commit descriptions could not be read.",
                    severity="warning",
                )
            )

    if update_count == 0:
        status = "fork_up_to_date" if checkout_type == "fork" else "up_to_date"
        user_action = "continue_learning"
    elif checkout_type == "fork":
        status = "fork_updates_available"
        user_action = "manual_fork_sync"
    else:
        status = "updates_available"
        user_action = "offer_update"

    state = {
        "runtime_update_check_schema_version": RUNTIME_UPDATE_CHECK_SCHEMA_VERSION,
        "platform": platform_id,
        "checked_date": today.isoformat(),
        "runtime_root": str(runtime),
        "checkout_type": checkout_type,
        "local_head": local_head,
        "upstream_head": upstream_head,
        "update_count": update_count,
        "result": status,
    }
    state_warning = _try_write_state(state_path, state)
    if state_warning is not None:
        warnings.append(state_warning)
    return CommandReport(
        command="check-runtime-update",
        mode="check",
        warnings=warnings,
        read_files=[relative_state_path] if previous_state is not None else [],
        changed_files=[] if state_warning is not None else [relative_state_path],
        artifacts={
            "canonical_remote": canonical_source,
            "checkout_type": checkout_type,
            "commits": json.dumps(commits, ensure_ascii=False),
            "local_head": local_head,
            "status": status,
            "state_path": relative_state_path,
            "update_count": str(update_count),
            "upstream_head": upstream_head,
            "user_action": user_action,
        },
    )


def apply_runtime_update(
    vault_root: str | Path,
    runtime_root: str | Path,
    *,
    platform_name: str | None = None,
    check_date: date | None = None,
    mode: str = "preview",
    git_runner: GitRunner | None = None,
) -> CommandReport:
    if mode not in {"preview", "apply"}:
        raise ValueError(f"unsupported_mode: {mode}")

    vault = Path(vault_root)
    runtime = Path(runtime_root)
    today = check_date or date.today()
    runner = git_runner or _run_git
    check = check_runtime_update(
        vault,
        runtime,
        platform_name=platform_name,
        check_date=today,
        force=True,
        git_runner=runner,
    )
    checkout_type = check.artifacts.get("checkout_type", "unknown")
    status = check.artifacts.get("status", "check_unavailable")
    if checkout_type == "fork":
        return CommandReport(
            command="apply-runtime-update",
            mode=mode,
            exit_code=1,
            errors=[
                Finding(
                    code="fork_update_requires_user_action",
                    message=(
                        "This runtime is a personal fork. Do not pull automatically; ask the user "
                        "to synchronize it in the developer repository."
                    ),
                    path=str(runtime),
                )
            ],
            warnings=check.warnings,
            read_files=check.read_files,
            changed_files=check.changed_files,
            artifacts=check.artifacts,
        )
    if checkout_type != "official":
        return CommandReport(
            command="apply-runtime-update",
            mode=mode,
            exit_code=1,
            errors=[
                Finding(
                    code="runtime_update_not_managed",
                    message="This runtime is not a recognized official checkout and cannot be updated automatically.",
                    path=str(runtime),
                )
            ],
            warnings=check.warnings,
            read_files=check.read_files,
            changed_files=check.changed_files,
            artifacts=check.artifacts,
        )
    if status == "check_unavailable":
        return CommandReport(
            command="apply-runtime-update",
            mode=mode,
            exit_code=1,
            errors=[
                Finding(
                    code="runtime_update_check_unavailable",
                    message="The official upstream could not be checked, so the runtime will not be changed.",
                    path=str(runtime),
                )
            ],
            warnings=check.warnings,
            read_files=check.read_files,
            changed_files=check.changed_files,
            artifacts=check.artifacts,
        )
    if status == "up_to_date":
        return CommandReport(
            command="apply-runtime-update",
            mode=mode,
            warnings=check.warnings,
            read_files=check.read_files,
            changed_files=check.changed_files,
            artifacts={**check.artifacts, "status": "already_up_to_date"},
        )

    planned = [
        {
            "path": str(runtime),
            "action": "git_pull_ff_only",
            "artifact_class": "public-runtime-update",
            "reason": "user-confirmed update from official upstream main",
        }
    ]
    if mode == "preview":
        return CommandReport(
            command="apply-runtime-update",
            mode="dry-run",
            warnings=check.warnings,
            read_files=check.read_files,
            changed_files=check.changed_files,
            planned_writes=planned,
            artifacts=check.artifacts,
        )

    branch = runner(runtime, ["branch", "--show-current"])
    if branch.returncode != 0 or branch.stdout.strip() != "main":
        return _update_blocked_report(check, "runtime_not_on_main", "The official runtime must be on main.", runtime)
    worktree = runner(runtime, ["status", "--porcelain"])
    if worktree.returncode != 0 or worktree.stdout.strip():
        return _update_blocked_report(
            check,
            "runtime_worktree_not_clean",
            "The official runtime has local changes. It will not be updated automatically.",
            runtime,
        )
    remote = check.artifacts["canonical_remote"]
    upstream_ref = f"refs/remotes/{remote}/main"
    ancestor = runner(runtime, ["merge-base", "--is-ancestor", "HEAD", upstream_ref])
    if ancestor.returncode != 0:
        return _update_blocked_report(
            check,
            "runtime_update_not_fast_forward",
            "The official runtime cannot be fast-forwarded safely.",
            runtime,
        )

    before = check.artifacts.get("local_head", "")
    pull = runner(runtime, ["pull", "--ff-only", remote, "main"])
    if pull.returncode != 0:
        return _update_blocked_report(
            check,
            "runtime_pull_failed",
            _git_failure_message("The official runtime update failed", pull),
            runtime,
        )
    after_result = runner(runtime, ["rev-parse", "HEAD"])
    if after_result.returncode != 0:
        return _update_blocked_report(
            check,
            "runtime_update_verification_failed",
            "The runtime was pulled, but its new revision could not be verified.",
            runtime,
        )
    after = after_result.stdout.strip()
    platform_id = current_platform(platform_name)
    relative_state_path = runtime_update_check_relative_path(platform_id)
    state_warning = _try_write_state(
        vault / relative_state_path,
        {
            "runtime_update_check_schema_version": RUNTIME_UPDATE_CHECK_SCHEMA_VERSION,
            "platform": platform_id,
            "checked_date": today.isoformat(),
            "runtime_root": str(runtime),
            "checkout_type": "official",
            "local_head": after,
            "upstream_head": after,
            "update_count": 0,
            "result": "updated",
            "updated_date": today.isoformat(),
        },
    )
    update_warnings = list(check.warnings)
    if state_warning is not None:
        update_warnings.append(state_warning)
    return CommandReport(
        command="apply-runtime-update",
        mode="apply",
        warnings=update_warnings,
        read_files=check.read_files,
        planned_writes=planned,
        changed_files=[] if state_warning is not None else [relative_state_path],
        artifacts={
            **check.artifacts,
            "before_head": before,
            "local_head": after,
            "status": "updated",
            "update_count": "0",
            "user_action": "continue_learning",
        },
    )


def _record_unavailable_check(
    vault: Path,
    runtime: Path,
    platform_id: str,
    today: date,
    relative_state_path: str,
    warnings: list[Finding],
    *,
    code: str,
    message: str,
    checkout_type: str = "unknown",
) -> CommandReport:
    warning = Finding(code=code, message=message, severity="warning", path=str(runtime))
    state = {
        "runtime_update_check_schema_version": RUNTIME_UPDATE_CHECK_SCHEMA_VERSION,
        "platform": platform_id,
        "checked_date": today.isoformat(),
        "runtime_root": str(runtime),
        "checkout_type": checkout_type,
        "update_count": 0,
        "result": "check_unavailable",
    }
    state_warning = _try_write_state(vault / relative_state_path, state)
    result_warnings = [*warnings, warning]
    if state_warning is not None:
        result_warnings.append(state_warning)
    return CommandReport(
        command="check-runtime-update",
        mode="check",
        warnings=result_warnings,
        changed_files=[] if state_warning is not None else [relative_state_path],
        artifacts={
            "checkout_type": checkout_type,
            "status": "check_unavailable",
            "state_path": relative_state_path,
            "update_count": "0",
            "user_action": "continue_learning",
        },
    )


def _update_blocked_report(check: CommandReport, code: str, message: str, runtime: Path) -> CommandReport:
    return CommandReport(
        command="apply-runtime-update",
        mode="apply",
        exit_code=1,
        errors=[Finding(code=code, message=message, path=str(runtime))],
        warnings=check.warnings,
        read_files=check.read_files,
        changed_files=check.changed_files,
        artifacts=check.artifacts,
    )


def _classify_checkout(remote_urls: dict[str, str]) -> tuple[str, str | None]:
    canonical_remote = next(
        (name for name, url in remote_urls.items() if _github_repository(url) == CANONICAL_REPOSITORY),
        None,
    )
    origin_repository = _github_repository(remote_urls.get("origin", ""))
    if origin_repository == CANONICAL_REPOSITORY:
        return "official", canonical_remote or "origin"
    if origin_repository is not None and origin_repository.endswith("/lingotrace"):
        return "fork", canonical_remote or CANONICAL_GIT_URL
    if canonical_remote is None:
        return "unknown", None
    return "unknown", canonical_remote


def _github_repository(url: str) -> str | None:
    value = url.strip()
    if not value:
        return None
    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    else:
        parsed = urlparse(value)
        if parsed.hostname != "github.com":
            return None
        path = parsed.path.lstrip("/")
    normalized = path.removesuffix(".git").strip("/").lower()
    parts = normalized.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return normalized


def _parse_commit_log(output: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for record in output.split("\x1e"):
        fields = record.strip().split("\x1f", 2)
        if len(fields) < 2:
            continue
        commits.append(
            {
                "commit": fields[0],
                "title": fields[1].strip()[:300],
                "body": (fields[2].strip() if len(fields) == 3 else "")[:1000],
            }
        )
    return commits


def _read_state(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("runtime_update_check_schema_version") != RUNTIME_UPDATE_CHECK_SCHEMA_VERSION:
        return None
    return payload


def _write_json_atomic(path: Path, content: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _try_write_state(path: Path, content: dict[str, object]) -> Finding | None:
    try:
        _write_json_atomic(path, content)
    except OSError as exc:
        return Finding(
            code="runtime_update_state_not_saved",
            message=f"The daily update state could not be saved: {exc}",
            severity="warning",
            path=str(path),
        )
    return None


def _git_failure_message(prefix: str, result: GitResult) -> str:
    detail = (result.stderr or result.stdout).strip()
    return f"{prefix}: {detail}" if detail else f"{prefix}."


def _run_git(runtime: Path, arguments: list[str]) -> GitResult:
    git_command = find_executable("git")
    if git_command is None:
        return GitResult(returncode=127, stderr="Git executable was not found.")
    try:
        completed = subprocess.run(
            [git_command, "-C", str(runtime), *arguments],
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return GitResult(returncode=127, stderr=str(exc))
    return GitResult(completed.returncode, completed.stdout, completed.stderr)
