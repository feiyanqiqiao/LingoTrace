from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.migration.compare import COMPARISON_STRATEGIES


SUPPORTED_COMPARISON_STRATEGIES = list(COMPARISON_STRATEGIES)
SRS_FIELDS = ("review_stage", "next_review", "done_today")
FAILED_COMPARISON_CODES = {
    "content_hash_mismatch",
    "missing_attachment",
    "missing_target_entry",
    "srs_field_mismatch",
    "unresolved_link",
}


def verify_migration_acceptance(manifest: dict[str, Any]) -> CommandReport:
    errors = _blocking_findings(manifest)
    verification_report = _verification_report(manifest, errors)

    return CommandReport(
        command="migration-verification",
        mode="dry-run",
        exit_code=1 if errors else 0,
        errors=errors,
        planned_writes=[
            {
                "path": "verification_report",
                "action": "record_verification_report",
                "verification_report": verification_report,
            }
        ],
        blocked_files=[finding.path for finding in errors if finding.path is not None],
    )


def build_verification_report(manifest: dict[str, Any]) -> dict[str, int | bool]:
    return _verification_report(manifest, _blocking_findings(manifest))


def _verification_report(manifest: dict[str, Any], errors: list[Finding]) -> dict[str, int | bool]:
    missing_approval_count = sum(1 for finding in errors if finding.code == "missing_user_approval")
    failed_comparison_count = sum(1 for finding in errors if finding.code in FAILED_COMPARISON_CODES)
    unresolved_conflict_count = len(manifest.get("conflicts", [])) + sum(
        1 for finding in errors if finding.code == "unclassified_entry"
    )

    return {
        "preserved_count": len(manifest.get("preserve_data", [])),
        "recreated_count": len(manifest.get("recreate_from_pack", [])),
        "transformed_count": len(manifest.get("transform_with_map", [])),
        "excluded_count": _excluded_count(manifest),
        "unresolved_conflict_count": unresolved_conflict_count,
        "missing_approval_count": missing_approval_count,
        "failed_comparison_count": failed_comparison_count,
        "accepted": not errors,
    }


def _blocking_findings(manifest: dict[str, Any]) -> list[Finding]:
    target_entries = _entries_by_path(manifest.get("target_manifest", []))
    errors: list[Finding] = []

    for conflict in manifest.get("conflicts", []):
        errors.append(
            Finding(
                code=str(conflict.get("code", "migration_conflict")),
                message=str(conflict.get("message", "Migration conflict blocks acceptance.")),
                path=str(conflict.get("relative_path", "")) or None,
            )
        )

    for source_entry in manifest.get("source_manifest", []):
        if not isinstance(source_entry, dict):
            continue
        relative_path = str(source_entry.get("relative_path", ""))
        classification = str(source_entry.get("classification", ""))

        if classification == "unclassified":
            errors.append(
                Finding(
                    code="unclassified_entry",
                    message="Unclassified source entries block migration acceptance.",
                    path=relative_path,
                )
            )
            continue

        if classification == "excluded_with_user_approval":
            if not _has_user_approval(source_entry):
                errors.append(
                    Finding(
                        code="missing_user_approval",
                        message="Explicitly excluded entries require user approval evidence.",
                        path=relative_path,
                    )
                )
            continue

        if classification != "preserve-data":
            continue

        target_path = str(source_entry.get("target_path", relative_path))
        target_entry = target_entries.get(target_path)
        if target_entry is None:
            errors.append(
                Finding(
                    code="missing_target_entry",
                    message="Preserved source entry is missing from the target manifest.",
                    path=relative_path,
                )
            )
            continue

        errors.extend(_comparison_findings(source_entry, target_entry))

    return errors


def _comparison_findings(source_entry: dict[str, Any], target_entry: dict[str, Any]) -> list[Finding]:
    relative_path = str(source_entry.get("relative_path", ""))
    strategy = str(source_entry.get("comparison_strategy", "content_hash"))
    errors: list[Finding] = []

    if strategy == "content_hash" and source_entry.get("content_hash") != target_entry.get("content_hash"):
        errors.append(
            Finding(
                code="content_hash_mismatch",
                message="Preserved entry hash differs between source and target.",
                path=relative_path,
            )
        )

    missing_attachments = sorted(set(source_entry.get("attachments", [])) - set(target_entry.get("available_attachments", [])))
    if missing_attachments:
        errors.append(
            Finding(
                code="missing_attachment",
                message="Preserved entry references attachments missing from the target Vault.",
                path=relative_path,
            )
        )

    unresolved_links = sorted(set(source_entry.get("links", [])) - set(target_entry.get("resolved_links", [])))
    if unresolved_links:
        errors.append(
            Finding(
                code="unresolved_link",
                message="Preserved entry contains links that do not resolve in the target Vault.",
                path=relative_path,
            )
        )

    source_fields = dict(source_entry.get("fields") or {})
    target_fields = dict(target_entry.get("fields") or {})
    if any(source_fields.get(field) != target_fields.get(field) for field in SRS_FIELDS if field in source_fields):
        errors.append(
            Finding(
                code="srs_field_mismatch",
                message="SRS fields must match after migration.",
                path=relative_path,
            )
        )

    return errors


def _entries_by_path(entries: object) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(entries, list):
        return result
    for entry in entries:
        if isinstance(entry, dict):
            result[str(entry.get("relative_path", ""))] = entry
    return result


def _has_user_approval(entry: dict[str, Any]) -> bool:
    approval = entry.get("approval")
    return isinstance(approval, dict) and bool(approval.get("approved_by")) and bool(approval.get("reason"))


def _excluded_count(manifest: dict[str, Any]) -> int:
    explicit_exclusions = {
        str(entry.get("relative_path", ""))
        for entry in manifest.get("excluded_with_user_approval", [])
        if isinstance(entry, dict)
    }
    source_exclusions = {
        str(entry.get("relative_path", ""))
        for entry in manifest.get("source_manifest", [])
        if isinstance(entry, dict) and entry.get("classification") == "excluded_with_user_approval"
    }
    return len(explicit_exclusions | source_exclusions)
