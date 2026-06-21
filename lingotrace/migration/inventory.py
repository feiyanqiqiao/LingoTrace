from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.migration.compare import COMPARISON_STRATEGIES


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


def build_migration_manifest(source_vault: str | Path, target_vault: str | Path) -> dict[str, Any]:
    source_root = Path(source_vault)
    target_root = Path(target_vault)

    source_manifest = [_entry_for_path(source_root, path) for path in _files_under(source_root)]
    target_manifest = [_target_entry_for_path(target_root, path) for path in _files_under(target_root)]

    preserve_data = [entry for entry in source_manifest if entry["classification"] == "preserve-data"]
    temporary_migration = [entry for entry in source_manifest if entry["classification"] == "temporary-migration"]
    remove_after_cutover = [entry for entry in source_manifest if entry["classification"] == "remove-after-cutover"]
    unclassified = [entry for entry in source_manifest if entry["classification"] == "unclassified"]

    conflicts = [
        {
            "code": "unclassified_entry",
            "relative_path": entry["relative_path"],
            "message": "Unclassified entries block acceptance.",
        }
        for entry in unclassified
    ]

    old_framework_exit_ledger = [
        _exit_ledger_entry(entry, "tracked", "temporary migration reader must be removed before cutover")
        for entry in temporary_migration
    ]
    old_framework_exit_ledger.extend(
        _exit_ledger_entry(entry, "tracked", "asset must be absent from target runtime after cutover")
        for entry in remove_after_cutover
    )

    verification_report = {
        "unclassified_count": len(unclassified),
        "unresolved_conflict_count": len(conflicts),
        "missing_user_approval_count": 0,
        "accepted": len(unclassified) == 0 and len(conflicts) == 0,
    }

    return {
        "source_vault": source_root.name,
        "target_vault": target_root.name,
        "source_manifest": source_manifest,
        "target_manifest": target_manifest,
        "preserve_data": preserve_data,
        "recreate_from_pack": [],
        "transform_with_map": [],
        "temporary_migration": temporary_migration,
        "remove_after_cutover": remove_after_cutover,
        "excluded_with_user_approval": [],
        "conflicts": conflicts,
        "comparison_strategies": list(COMPARISON_STRATEGIES),
        "verification_report": verification_report,
        "old_framework_exit_ledger": old_framework_exit_ledger,
    }


def build_migration_inventory_report(source_vault: str | Path, target_vault: str | Path) -> CommandReport:
    manifest = build_migration_manifest(source_vault, target_vault)
    errors = [
        Finding(
            code=str(conflict["code"]),
            message=str(conflict["message"]),
            path=str(conflict["relative_path"]),
        )
        for conflict in manifest["conflicts"]
    ]

    return CommandReport(
        command="migration-inventory",
        mode="dry-run",
        exit_code=1 if errors else 0,
        errors=errors,
        artifacts={"manifest": "in-memory"},
    )


def build_transform_entry(
    *,
    source_path: str,
    target_path: str,
    field_mapping: dict[str, str],
) -> dict[str, Any]:
    if not field_mapping:
        raise ValueError("explicit_mapping_required")

    return {
        "source_path": source_path,
        "target_path": target_path,
        "classification": "transform-with-map",
        "field_mapping": dict(field_mapping),
        "preview_result": "planned",
        "conflict_status": "clear",
        "acceptance_result": "dry-run-only",
    }


def _files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _entry_for_path(root: Path, path: Path) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    content = path.read_text(encoding="utf-8", errors="ignore")
    classification = _classify_source_path(relative_path)
    entry: dict[str, Any] = {
        "relative_path": relative_path,
        "classification": classification,
        "comparison_strategy": "frontmatter_and_body" if classification == "preserve-data" else "content_hash",
        "content_hash": _hash_file(path),
        "detected_references": _detected_references(content),
        "conflict_status": "clear" if classification != "unclassified" else "blocked",
    }

    if classification == "preserve-data":
        entry["frontmatter"] = _frontmatter(content)

    return entry


def _target_entry_for_path(root: Path, path: Path) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    classification = _classify_source_path(relative_path)
    return {
        "relative_path": relative_path,
        "classification": classification,
        "comparison_strategy": "frontmatter_and_body" if classification == "preserve-data" else "content_hash",
        "content_hash": _hash_file(path),
        "comparison_result": "present",
    }


def _classify_source_path(relative_path: str) -> str:
    if relative_path.startswith("codex-skills/"):
        return "temporary-migration"
    if relative_path.startswith("系统配置/") or relative_path == "学习系统/总训练.base":
        return "remove-after-cutover"
    if relative_path.endswith(".md"):
        return "preserve-data"
    return "unclassified"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _detected_references(content: str) -> list[str]:
    return sorted(set(match.strip() for match in WIKILINK_RE.findall(content)))


def _frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}

    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _exit_ledger_entry(entry: dict[str, Any], status: str, removal_condition: str) -> dict[str, str]:
    return {
        "relative_path": str(entry["relative_path"]),
        "classification": str(entry["classification"]),
        "exit_status": status,
        "removal_condition": removal_condition,
    }
