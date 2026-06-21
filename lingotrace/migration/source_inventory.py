from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.migration.compare import COMPARISON_STRATEGIES


REMOVE_AFTER_CUTOVER_PREFIXES = (
    ".antigravitycli/",
    ".github/",
    ".obsidian/",
    ".worktrees/",
    "docs/",
    "lingotrace/",
    "tests/",
    "tmp/",
    "tools/",
    "系统配置/",
)
REMOVE_AFTER_CUTOVER_FILES = {
    ".DS_Store",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
}
PRESERVE_DATA_PREFIXES = (
    "学习系统/",
    "笔记/",
)


def plan_final_source_inventory(
    *,
    source_vault: str | Path | None,
    target_vault: str | Path | None,
    output_dir: str | Path | None,
    write_freeze_started_at: str,
    transform_map: dict[str, dict[str, Any]] | None = None,
    exclusion_approvals: dict[str, dict[str, str]] | None = None,
) -> CommandReport:
    errors = _input_errors(source_vault, target_vault, output_dir, write_freeze_started_at)
    if errors:
        return _report(errors)

    assert source_vault is not None
    assert target_vault is not None
    assert output_dir is not None
    source_root = Path(source_vault)
    target_root = Path(target_vault)
    private_output_root = Path(output_dir)

    if _same_root(source_root, target_root):
        return _report(
            [
                Finding(
                    code="source_target_same",
                    message="Source and target Vault roots must be different.",
                    path="target_vault",
                )
            ]
        )

    transform_map = transform_map or {}
    exclusion_approvals = exclusion_approvals or {}
    source_manifest = [
        _source_entry(source_root, path, transform_map, exclusion_approvals)
        for path in _files_under(source_root)
    ]
    unclassified = [entry for entry in source_manifest if entry["classification"] == "unclassified"]
    conflicts = [
        {
            "code": "unclassified_entry",
            "relative_path": entry["relative_path"],
            "message": "Unclassified source entries block cutover.",
        }
        for entry in unclassified
    ]

    manifest = {
        "source_vault": source_root.name,
        "target_vault": target_root.name,
        "write_freeze_started_at": write_freeze_started_at,
        "source_manifest": source_manifest,
        "target_manifest": [],
        "preserve_data": _entries(source_manifest, "preserve-data"),
        "recreate_from_pack": _entries(source_manifest, "recreate-from-pack"),
        "transform_with_map": _entries(source_manifest, "transform-with-map"),
        "temporary_migration": _entries(source_manifest, "temporary-migration"),
        "remove_after_cutover": _entries(source_manifest, "remove-after-cutover"),
        "excluded_with_user_approval": _entries(source_manifest, "excluded_with_user_approval"),
        "conflicts": conflicts,
        "comparison_strategies": list(COMPARISON_STRATEGIES),
        "verification_report": {
            "unclassified_count": len(unclassified),
            "unresolved_conflict_count": len(conflicts),
            "missing_user_approval_count": 0,
            "accepted": len(conflicts) == 0,
        },
    }

    private_output_root.mkdir(parents=True, exist_ok=True)
    (private_output_root / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return CommandReport(
        command="final-source-inventory",
        mode="write-private-artifact",
        exit_code=1 if conflicts else 0,
        errors=[
            Finding(
                code=str(conflict["code"]),
                message=str(conflict["message"]),
                path=str(conflict["relative_path"]),
            )
            for conflict in conflicts
        ],
        changed_files=["source-manifest.json"],
        blocked_files=[str(entry["relative_path"]) for entry in unclassified],
        artifacts={"source_manifest": "source-manifest.json"},
    )


def _input_errors(
    source_vault: str | Path | None,
    target_vault: str | Path | None,
    output_dir: str | Path | None,
    write_freeze_started_at: str,
) -> list[Finding]:
    errors: list[Finding] = []
    if output_dir is None or str(output_dir) == "":
        errors.append(Finding(code="output_dir_required", message="Private output directory is required.", path="output_dir"))
    if source_vault is None or str(source_vault) == "":
        errors.append(Finding(code="source_vault_required", message="Explicit source Vault root is required.", path="source_vault"))
    if write_freeze_started_at == "":
        errors.append(
            Finding(
                code="write_freeze_required",
                message="Write-freeze start timestamp is required before final source inventory.",
                path="write_freeze_started_at",
            )
        )
    if target_vault is None or str(target_vault) == "":
        errors.append(Finding(code="target_vault_required", message="Explicit target Vault root is required.", path="target_vault"))
    return sorted(errors, key=lambda finding: finding.code)


def _source_entry(
    source_root: Path,
    path: Path,
    transform_map: dict[str, dict[str, Any]],
    exclusion_approvals: dict[str, dict[str, str]],
) -> dict[str, Any]:
    relative_path = path.relative_to(source_root).as_posix()
    classification = _classification(relative_path, transform_map, exclusion_approvals)
    entry: dict[str, Any] = {
        "relative_path": relative_path,
        "classification": classification,
        "comparison_strategy": "frontmatter_and_body" if path.suffix == ".md" else "content_hash",
        "content_hash": _content_hash(path),
        "conflict_status": "blocked" if classification == "unclassified" else "clear",
    }

    if classification == "transform-with-map":
        entry["transform"] = dict(transform_map[relative_path])
    if classification == "excluded_with_user_approval":
        entry["approval"] = dict(exclusion_approvals[relative_path])

    return entry


def _classification(
    relative_path: str,
    transform_map: dict[str, dict[str, Any]],
    exclusion_approvals: dict[str, dict[str, str]],
) -> str:
    if relative_path in exclusion_approvals:
        return "excluded_with_user_approval"
    if relative_path in transform_map:
        return "transform-with-map"
    if _is_transient_file(relative_path):
        return "remove-after-cutover"
    if relative_path.startswith("codex-skills/"):
        return "temporary-migration"
    if relative_path.startswith("系统配置/模板/") or relative_path == "学习系统/总训练.base":
        return "recreate-from-pack"
    if relative_path.startswith(".git/"):
        return "remove-after-cutover"
    if _has_prefix(relative_path, REMOVE_AFTER_CUTOVER_PREFIXES):
        return "remove-after-cutover"
    if _has_prefix(relative_path, PRESERVE_DATA_PREFIXES):
        return "preserve-data"
    if relative_path.endswith(".md"):
        return "preserve-data"
    return "unclassified"


def _files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _entries(entries: list[dict[str, Any]], classification: str) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry["classification"] == classification]


def _content_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _same_root(source_root: Path, target_root: Path) -> bool:
    return source_root.expanduser().resolve() == target_root.expanduser().resolve()


def _has_prefix(relative_path: str, prefixes: tuple[str, ...]) -> bool:
    return any(relative_path.startswith(prefix) for prefix in prefixes)


def _is_transient_file(relative_path: str) -> bool:
    path = Path(relative_path)
    return (
        path.name in REMOVE_AFTER_CUTOVER_FILES
        or path.suffix == ".pyc"
        or "__pycache__" in path.parts
    )


def _report(errors: list[Finding]) -> CommandReport:
    return CommandReport(
        command="final-source-inventory",
        mode="write-private-artifact",
        exit_code=1,
        errors=errors,
    )
