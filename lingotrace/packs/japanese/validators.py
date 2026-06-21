from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = _missing_field_errors(card, required)

    if not any(field in card for field in ("reading", "accent_display", "meaning_zh", "kanji_diff", "kanji_diff_pairs")):
        errors.append(
            Finding(
                code="missing_japanese_field",
                message="Review material fixture must contain at least one Japanese pack field.",
            )
        )

    return _validation_report("validate-review-materials", errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    errors = _missing_field_errors(card, ("review_stage", "next_review", "done_today"))
    return _validation_report("validate-review-rollover", errors)


def _missing_field_errors(card: dict[str, Any], fields: tuple[str, ...]) -> list[Finding]:
    return [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in fields
        if field not in card
    ]


def _validation_report(command: str, errors: list[Finding]) -> CommandReport:
    return CommandReport(
        command=command,
        mode="check",
        exit_code=1 if errors else 0,
        errors=errors,
    )
