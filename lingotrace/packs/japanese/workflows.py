from __future__ import annotations

from lingotrace.core.reports import CommandReport, Finding


def listening_notes() -> CommandReport:
    return _not_implemented("listening_notes")


def source_notes() -> CommandReport:
    return _not_implemented("source_notes")


def review_materials() -> CommandReport:
    return _not_implemented("review_materials")


def speaking_cards() -> CommandReport:
    return _not_implemented("speaking_cards")


def review_rollover() -> CommandReport:
    return _not_implemented("review_rollover")


def _not_implemented(capability_id: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="dry-run",
        exit_code=1,
        errors=[
            Finding(
                code="workflow_not_implemented",
                message=f"{capability_id} is declared by the Japanese pack but not implemented in PR 2.",
            )
        ],
    )
