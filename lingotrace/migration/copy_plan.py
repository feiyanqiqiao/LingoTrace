from __future__ import annotations

from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def plan_preserve_data_copies(
    *,
    source_vault: str | Path,
    target_vault: str | Path,
    preserve_entries: list[dict[str, Any]],
    generated_target_paths: set[str],
) -> CommandReport:
    source_root = Path(source_vault)
    Path(target_vault)
    errors: list[Finding] = []
    planned_writes: list[dict[str, str]] = []
    blocked_files: list[str] = []

    for entry in preserve_entries:
        relative_path = str(entry.get("relative_path", ""))
        if _is_unsafe_relative_path(relative_path):
            errors.append(
                Finding(
                    code="unsafe_relative_path",
                    message="Preserve-data copy path must stay inside the target Vault.",
                    path=relative_path,
                )
            )
            blocked_files.append(relative_path)
            continue

        if relative_path in generated_target_paths:
            errors.append(
                Finding(
                    code="target_system_asset_collision",
                    message="Preserve-data copy would overwrite a generated target system asset.",
                    path=relative_path,
                )
            )
            blocked_files.append(relative_path)
            continue

        if not (source_root / relative_path).is_file():
            errors.append(
                Finding(
                    code="missing_source_asset",
                    message="Preserve-data source asset is missing.",
                    path=relative_path,
                )
            )
            blocked_files.append(relative_path)
            continue

        planned_writes.append(
            {
                "path": relative_path,
                "action": "copy_preserve_data",
                "reason": "preserve private learning data",
                "content_hash": str(entry.get("content_hash", "")),
            }
        )

    return CommandReport(
        command="migration-copy-preview",
        mode="preview",
        exit_code=1 if errors else 0,
        errors=errors,
        planned_writes=planned_writes,
        blocked_files=blocked_files,
    )


def _is_unsafe_relative_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return relative_path == "" or path.is_absolute() or ".." in path.parts
