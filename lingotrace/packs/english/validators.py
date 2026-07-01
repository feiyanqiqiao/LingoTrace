"""English language pack validators."""
from __future__ import annotations

import datetime as dt
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


_VALID_REVIEW_STAGES = frozenset({
    "day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180", "mastered",
})


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = _missing_field_errors(card, required)

    if any(field in card for field in ("status", "done_today", "next_review")):
        errors.extend(_missing_field_errors(card, ("status", "done_today", "next_review")))

    item_type = str(card.get("item_type", ""))
    if item_type == "vocab":
        if not any(field in card for field in ("headword", "ipa", "english_definition", "meaning_zh", "collocations")):
            errors.append(
                Finding(
                    code="missing_english_field",
                    message="Vocabulary review material requires a headword, IPA, definition, meaning, or collocations field.",
                )
            )
    elif item_type == "grammar":
        errors.extend(_missing_field_errors(card, ("pattern",)))
        if not any(field in card for field in ("meaning_zh", "formation")):
            errors.append(
                Finding(
                    code="missing_grammar_explanation",
                    message="Grammar review material requires meaning or formation.",
                )
            )
    elif item_type == "error":
        errors.extend(_missing_field_errors(card, ("correct_form",)))
        if not any(field in card for field in ("wrong_form", "reason")):
            errors.append(
                Finding(
                    code="missing_error_contrast",
                    message="Error review material requires a wrong form or reason.",
                )
            )
    elif item_type == "pronunciation":
        errors.extend(_missing_field_errors(card, ("target_text",)))
        if not any(field in card for field in ("pronunciation_kind", "issue_tags")):
            errors.append(
                Finding(
                    code="missing_pronunciation_focus",
                    message="Pronunciation review material requires a pronunciation kind or issue tag.",
                )
            )
    elif item_type:
        errors.append(Finding(code="unsupported_item_type", message=f"Unsupported review material item_type: {item_type}."))

    return _validation_report("validate-review-materials", errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    errors = _missing_field_errors(card, ("review_stage", "next_review", "done_today"))

    review_stage = str(card.get("review_stage", ""))
    if review_stage and review_stage not in _VALID_REVIEW_STAGES:
        errors.append(
            Finding(
                code="invalid_review_stage",
                message=f"Unknown review stage: {review_stage}.",
            )
        )

    next_review = str(card.get("next_review", ""))
    if next_review:
        try:
            dt.date.fromisoformat(next_review)
        except ValueError:
            errors.append(
                Finding(
                    code="invalid_next_review",
                    message="Review rollover requires next_review to use YYYY-MM-DD format.",
                )
            )

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
