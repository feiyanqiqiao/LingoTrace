from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def plan_transform_previews(transform_entries: list[dict[str, Any]]) -> CommandReport:
    errors: list[Finding] = []
    planned_writes: list[dict[str, Any]] = []
    blocked_files: list[str] = []

    for entry in transform_entries:
        source_path = str(entry.get("source_path", ""))
        reason = str(entry.get("reason", ""))
        field_mapping = dict(entry.get("field_mapping") or {})

        if not field_mapping:
            errors.append(
                Finding(
                    code="explicit_mapping_required",
                    message="Transform preview requires a non-empty explicit field map.",
                    path=source_path,
                )
            )
            blocked_files.append(source_path)
            continue

        if _is_cosmetic_transform(reason) and not bool(entry.get("user_approved")):
            errors.append(
                Finding(
                    code="cosmetic_transform_requires_user_approval",
                    message="Cosmetic transforms require explicit user approval.",
                    path=source_path,
                )
            )
            blocked_files.append(source_path)
            continue

        planned_writes.append(
            {
                "source_path": source_path,
                "target_path": str(entry.get("target_path", "")),
                "action": "transform_with_map",
                "reason": reason,
                "field_mapping": field_mapping,
                "before": dict(entry.get("before") or {}),
                "after": dict(entry.get("after") or {}),
                "preview_result": "planned",
                "conflict_status": "clear",
                "acceptance_result": "dry-run-only",
            }
        )

    return CommandReport(
        command="migration-transform-preview",
        mode="preview",
        exit_code=1 if errors else 0,
        errors=errors,
        planned_writes=planned_writes,
        blocked_files=blocked_files,
    )


def _is_cosmetic_transform(reason: str) -> bool:
    return "cosmetic" in reason.lower()
