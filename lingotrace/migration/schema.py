from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


REQUIRED_MANIFEST_KEYS = {
    "source_vault",
    "target_vault",
    "source_manifest",
    "target_manifest",
    "preserve_data",
    "recreate_from_pack",
    "transform_with_map",
    "remove_after_cutover",
    "excluded_with_user_approval",
    "conflicts",
    "verification_report",
}

VALID_MIGRATION_CLASSIFICATIONS = {
    "preserve-data",
    "recreate-from-pack",
    "transform-with-map",
    "temporary-migration",
    "remove-after-cutover",
    "excluded_with_user_approval",
}

VALID_COMPARISON_STRATEGIES = {
    "content_hash",
    "frontmatter_and_body",
    "links_and_hashes",
    "field_aware",
}

ENTRY_LIST_KEYS = (
    "source_manifest",
    "target_manifest",
    "preserve_data",
    "recreate_from_pack",
    "transform_with_map",
    "remove_after_cutover",
    "excluded_with_user_approval",
)


def validate_migration_manifest(manifest: Mapping[str, Any]) -> CommandReport:
    errors: list[Finding] = []

    for key in sorted(REQUIRED_MANIFEST_KEYS - set(manifest)):
        errors.append(
            Finding(
                code="migration_manifest_missing_key",
                message=f"Migration manifest is missing required key: {key}.",
                path=key,
            )
        )

    if errors:
        return _report(errors)

    for list_key in ENTRY_LIST_KEYS:
        value = manifest.get(list_key)
        if not isinstance(value, list):
            continue
        for index, raw_entry in enumerate(value):
            if not isinstance(raw_entry, Mapping):
                continue
            errors.extend(_entry_errors(raw_entry, f"{list_key}[{index}]"))

    return _report(errors)


def _entry_errors(entry: Mapping[str, Any], path_prefix: str) -> list[Finding]:
    errors: list[Finding] = []
    classification = entry.get("classification")
    comparison_strategy = entry.get("comparison_strategy")

    if classification is not None and classification not in VALID_MIGRATION_CLASSIFICATIONS:
        errors.append(
            Finding(
                code="migration_manifest_invalid_classification",
                message=f"Invalid migration classification: {classification}.",
                path=f"{path_prefix}.classification",
            )
        )

    if comparison_strategy is not None and comparison_strategy not in VALID_COMPARISON_STRATEGIES:
        errors.append(
            Finding(
                code="migration_manifest_invalid_comparison_strategy",
                message=f"Invalid migration comparison strategy: {comparison_strategy}.",
                path=f"{path_prefix}.comparison_strategy",
            )
        )

    return errors


def _report(errors: list[Finding]) -> CommandReport:
    return CommandReport(
        command="validate-migration-manifest",
        mode="check",
        exit_code=1 if errors else 0,
        errors=errors,
    )
