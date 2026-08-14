from __future__ import annotations

import datetime as dt
from typing import Any

from .reports import Finding


REVIEW_STATUSES = {"backlog", "queued", "mastered", "archived"}
ACTIVE_REVIEW_STAGES = {"day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180"}


def effective_review_status(fields: dict[str, Any]) -> str:
    """Return the explicit lifecycle state, or a conservative legacy fallback."""

    explicit = fields.get("review_status")
    if explicit in REVIEW_STATUSES:
        return str(explicit)

    legacy = fields.get("status")
    if legacy in {"mastered", "promoted"}:
        return "mastered"
    if legacy == "archived":
        return "archived"
    if legacy == "active" and fields.get("review_stage") in ACTIVE_REVIEW_STAGES and _valid_date(
        fields.get("next_review")
    ):
        return "queued"
    return "backlog"


def validate_review_lifecycle(fields: dict[str, Any], *, require_explicit: bool = True) -> list[Finding]:
    errors: list[Finding] = []
    if require_explicit and "review_status" not in fields:
        return [Finding(code="missing_field", message="Required field is missing: review_status.", path="review_status")]

    review_status = fields.get("review_status") if require_explicit else effective_review_status(fields)
    if review_status not in REVIEW_STATUSES:
        return [
            Finding(
                code="invalid_review_status",
                message="review_status must be backlog, queued, mastered, or archived.",
                path="review_status",
            )
        ]

    done_today = fields.get("done_today")
    if not isinstance(done_today, bool):
        errors.append(Finding(code="invalid_field_type", message="done_today must be a boolean.", path="done_today"))
        return errors

    review_stage = fields.get("review_stage")
    next_review = fields.get("next_review")
    if review_status == "queued":
        if review_stage not in ACTIVE_REVIEW_STAGES:
            errors.append(
                Finding(
                    code="invalid_review_stage",
                    message="Queued review material requires a supported day stage.",
                    path="review_stage",
                )
            )
        if not _valid_date(next_review):
            errors.append(
                Finding(
                    code="invalid_date",
                    message="Queued review material requires next_review in YYYY-MM-DD format.",
                    path="next_review",
                )
            )
    elif review_status == "backlog":
        if done_today:
            errors.append(
                Finding(
                    code="invalid_backlog_completion",
                    message="Backlog review material requires done_today: false.",
                    path="done_today",
                )
            )
        if review_stage not in (None, "", *ACTIVE_REVIEW_STAGES):
            errors.append(
                Finding(
                    code="invalid_review_stage",
                    message="Backlog review_stage must be blank or a supported day stage.",
                    path="review_stage",
                )
            )
        if next_review not in (None, "") and not _valid_date(next_review):
            errors.append(
                Finding(
                    code="invalid_date",
                    message="Backlog next_review must be blank or use YYYY-MM-DD format.",
                    path="next_review",
                )
            )
    elif review_status == "mastered":
        if review_stage != "mastered" or next_review not in (None, "") or done_today:
            errors.append(
                Finding(
                    code="invalid_mastered_state",
                    message="Mastered material requires review_stage: mastered, blank next_review, and done_today: false.",
                    path="review_status",
                )
            )
    elif review_status == "archived" and done_today:
        errors.append(
            Finding(
                code="invalid_archived_completion",
                message="Archived material requires done_today: false.",
                path="done_today",
            )
        )
    return errors


def queue_transition_updates(
    fields: dict[str, Any],
    *,
    target_status: str,
    activation: str | None,
    change_date: str,
) -> dict[str, Any] | Finding:
    try:
        dt.date.fromisoformat(change_date)
    except ValueError:
        return Finding(code="invalid_change_date", message="change_date must use YYYY-MM-DD format.", path="change_date")

    current_status = effective_review_status(fields)
    if target_status == "backlog":
        if activation is not None:
            return Finding(
                code="unexpected_activation",
                message="activation is only valid when target_status is queued.",
                path="activation",
            )
        return {"review_status": "backlog", "done_today": False}
    if target_status != "queued":
        return Finding(
            code="unsupported_queue_target",
            message="review_queue can only move material to queued or backlog.",
            path="target_status",
        )
    if activation not in {"resume", "restart"}:
        return Finding(
            code="invalid_activation",
            message="Queued transitions require activation: resume or restart.",
            path="activation",
        )

    restart = activation == "restart" or current_status == "mastered"
    review_stage = fields.get("review_stage")
    if restart or review_stage not in ACTIVE_REVIEW_STAGES:
        return {
            "review_status": "queued",
            "done_today": False,
            "review_stage": "day0",
            "next_review": change_date,
            "last_reviewed": "",
        }
    return {
        "review_status": "queued",
        "done_today": False,
        "review_stage": review_stage,
        "next_review": change_date,
    }


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True
