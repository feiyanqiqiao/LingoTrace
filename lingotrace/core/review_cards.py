from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReviewCardShell:
    frontmatter: dict[str, Any]
    body: str


def merge_review_card_fields(existing: ReviewCardShell, updates: dict[str, Any]) -> ReviewCardShell:
    merged_frontmatter = dict(existing.frontmatter)
    merged_frontmatter.update(updates)
    return ReviewCardShell(frontmatter=merged_frontmatter, body=existing.body)
