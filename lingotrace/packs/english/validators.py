"""English language pack validators (stubs)."""
from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-materials", mode="check", exit_code=1 if errors else 0, errors=errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    required = ("review_stage", "next_review", "done_today")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-rollover", mode="check", exit_code=1 if errors else 0, errors=errors)
