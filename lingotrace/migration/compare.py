from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


COMPARISON_STRATEGIES = [
    "content_hash",
    "frontmatter_and_body",
    "links_and_hashes",
    "field_aware",
]


def compare_migration_manifest(manifest: dict[str, Any]) -> CommandReport:
    conflicts = manifest.get("conflicts", [])
    errors = [
        Finding(
            code=str(conflict.get("code", "migration_conflict")),
            message=str(conflict.get("message", "Migration conflict blocks acceptance.")),
            path=str(conflict.get("relative_path", "")) or None,
        )
        for conflict in conflicts
    ]

    verification_report = manifest.get("verification_report", {})
    if not verification_report.get("accepted", False) and not errors:
        errors.append(
            Finding(
                code="verification_not_accepted",
                message="Migration verification report is not accepted.",
            )
        )

    return CommandReport(
        command="migration-compare",
        mode="dry-run",
        exit_code=1 if errors else 0,
        errors=errors,
    )
