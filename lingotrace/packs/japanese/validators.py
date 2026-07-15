from __future__ import annotations

import datetime as dt
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = (
        "track",
        "item_type",
        "status",
        "priority",
        "done_today",
        "source_notes",
        "first_seen",
        "last_seen",
        "seen_count",
        "error_count",
        "review_stage",
        "next_review",
        "last_reviewed",
        "tags",
    )
    errors = _missing_field_errors(card, required)
    if errors:
        return _validation_report("validate-review-materials", errors)

    if not isinstance(card.get("done_today"), bool):
        errors.append(Finding(code="invalid_field_type", message="done_today must be a boolean.", path="done_today"))
    for field in ("seen_count", "error_count"):
        value = card.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(Finding(code="invalid_field_type", message=f"{field} must be a non-negative integer.", path=field))
    for field in ("source_notes", "tags"):
        value = card.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(Finding(code="invalid_field_type", message=f"{field} must be a list of non-empty strings.", path=field))
    for field in ("first_seen", "last_seen"):
        if not _valid_date(card.get(field)):
            errors.append(Finding(code="invalid_date", message=f"{field} must use YYYY-MM-DD format.", path=field))
    if card.get("last_reviewed") not in (None, "") and not _valid_date(card.get("last_reviewed")):
        errors.append(Finding(code="invalid_date", message="last_reviewed must be blank or use YYYY-MM-DD format.", path="last_reviewed"))
    status = card.get("status")
    review_stage = card.get("review_stage")
    if status not in {"active", "mastered", "promoted"}:
        errors.append(Finding(code="invalid_review_status", message="status must be active, mastered, or promoted.", path="status"))
    elif status == "active":
        if not _valid_date(card.get("next_review")):
            errors.append(Finding(code="invalid_date", message="Active review material requires next_review in YYYY-MM-DD format.", path="next_review"))
        if review_stage not in {"day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180"}:
            errors.append(Finding(code="invalid_review_stage", message="Active review_stage must use a supported day stage.", path="review_stage"))
    elif status == "mastered" and (review_stage != "mastered" or card.get("next_review") not in (None, "")):
        errors.append(Finding(code="invalid_review_stage", message="Mastered review material requires review_stage: mastered and blank next_review.", path="review_stage"))

    item_type = str(card.get("item_type", ""))
    if item_type == "vocab":
        errors.extend(_non_empty_field_errors(card, ("headword", "reading", "meaning_zh")))
        errors.extend(_optional_list_errors(card, ("collocations", "confusable_with", "contrast_with", "kanji_diff_pairs")))
    elif item_type == "grammar":
        errors.extend(_non_empty_field_errors(card, ("pattern", "meaning_zh")))
        formation = card.get("formation")
        if not isinstance(formation, list) or not formation or any(not isinstance(item, str) or not item for item in formation):
            errors.append(Finding(code="invalid_grammar_formation", message="Grammar formation must be a non-empty list of strings.", path="formation"))
        errors.extend(_optional_list_errors(card, ("contrast_with", "usage_scenes")))
    elif item_type == "error":
        errors.extend(_non_empty_field_errors(card, ("correct_form", "wrong_form", "reason", "avoidance")))
        errors.extend(_optional_list_errors(card, ("related_items",)))
    elif item_type == "pronunciation":
        errors.extend(_non_empty_field_errors(card, ("target_text", "pronunciation_kind")))
        errors.extend(_optional_list_errors(card, ("issue_tags", "related_items")))
    elif item_type:
        errors.append(Finding(code="unsupported_item_type", message=f"Unsupported review material item_type: {item_type}."))

    return _validation_report("validate-review-materials", errors)


def validate_existing_review_material(card: dict[str, Any]) -> CommandReport:
    """Recognize readable legacy cards without requiring an in-place migration."""

    errors = _missing_field_errors(card, ("item_type", "review_stage"))
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

    return _validation_report("validate-existing-review-material", errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    errors = _missing_field_errors(card, ("review_stage", "next_review", "done_today"))
    return _validation_report("validate-review-rollover", errors)


def _missing_field_errors(card: dict[str, Any], fields: tuple[str, ...]) -> list[Finding]:
    return [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in fields
        if field not in card
    ]


def _non_empty_field_errors(card: dict[str, Any], fields: tuple[str, ...]) -> list[Finding]:
    return [
        Finding(code="missing_field", message=f"Required field is missing or blank: {field}.", path=field)
        for field in fields
        if not isinstance(card.get(field), str) or not str(card.get(field)).strip()
    ]


def _optional_list_errors(card: dict[str, Any], fields: tuple[str, ...]) -> list[Finding]:
    errors: list[Finding] = []
    for field in fields:
        if field not in card:
            continue
        value = card[field]
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(Finding(code="invalid_field_type", message=f"{field} must be a list of non-empty strings.", path=field))
    return errors


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validation_report(command: str, errors: list[Finding]) -> CommandReport:
    return CommandReport(
        command=command,
        mode="check",
        exit_code=1 if errors else 0,
        errors=errors,
    )
