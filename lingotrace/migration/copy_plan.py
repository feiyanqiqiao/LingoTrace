from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.migration.path_mapping import map_target_path


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


def apply_preserve_data_copies(
    *,
    source_vault: str | Path,
    target_vault: str | Path,
    preserve_entries: list[dict[str, Any]],
    generated_target_paths: set[str],
    path_mappings: list[dict[str, Any]],
) -> CommandReport:
    source_root = Path(source_vault)
    target_root = Path(target_vault)
    errors: list[Finding] = []
    planned_writes: list[dict[str, str]] = []
    changed_files: list[str] = []
    blocked_files: list[str] = []

    for entry in preserve_entries:
        relative_path = str(entry.get("relative_path", ""))
        try:
            target_path = map_target_path(relative_path, path_mappings)
        except ValueError:
            errors.append(
                Finding(
                    code="unsafe_relative_path",
                    message="Preserve-data copy path must stay inside the target Vault.",
                    path=relative_path,
                )
            )
            blocked_files.append(relative_path)
            continue

        if target_path in generated_target_paths:
            errors.append(
                Finding(
                    code="target_system_asset_collision",
                    message="Preserve-data copy would overwrite a generated target system asset.",
                    path=target_path,
                )
            )
            blocked_files.append(target_path)
            continue

        source_path = source_root / relative_path
        if not source_path.is_file():
            errors.append(
                Finding(
                    code="missing_source_asset",
                    message="Preserve-data source asset is missing.",
                    path=relative_path,
                )
            )
            blocked_files.append(relative_path)
            continue

        output_path = target_root / target_path
        if output_path.exists():
            errors.append(
                Finding(
                    code="target_path_exists",
                    message="Preserve-data target path already exists and will not be overwritten.",
                    path=target_path,
                )
            )
            blocked_files.append(target_path)
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, output_path)
        changed_files.append(target_path)
        planned_writes.append(
            {
                "source_path": relative_path,
                "target_path": target_path,
                "action": "copy_preserve_data",
                "reason": "preserve private learning data",
                "content_hash": str(entry.get("content_hash", "")),
            }
        )

    return CommandReport(
        command="migration-copy-apply",
        mode="apply",
        exit_code=1 if errors else 0,
        errors=errors,
        planned_writes=planned_writes,
        changed_files=changed_files,
        blocked_files=blocked_files,
    )


def _is_unsafe_relative_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return relative_path == "" or path.is_absolute() or ".." in path.parts
