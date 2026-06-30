from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = _missing_field_errors(card, required)

    if any(field in card for field in ("status", "done_today", "next_review")):
        errors.extend(_missing_field_errors(card, ("status", "done_today", "next_review")))

    item_type = str(card.get("item_type", ""))
    if item_type == "vocab":
        if not any(field in card for field in ("headword", "reading", "accent_display", "meaning_zh", "kanji_diff", "kanji_diff_pairs")):
            errors.append(
                Finding(
                    code="missing_japanese_field",
                    message="Vocabulary review material requires a headword, reading, meaning, accent, or kanji-difference field.",
                )
            )
    elif item_type == "grammar":
        errors.extend(_missing_field_errors(card, ("pattern",)))
        if not any(field in card for field in ("meaning_zh", "formation", "usage")):
            errors.append(
                Finding(
                    code="missing_grammar_explanation",
                    message="Grammar review material requires meaning, formation, or usage.",
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
