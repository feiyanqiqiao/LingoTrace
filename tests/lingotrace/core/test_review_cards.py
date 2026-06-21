from __future__ import annotations

import unittest

from lingotrace.core.review_cards import ReviewCardShell, merge_review_card_fields


class ReviewCardShellTests(unittest.TestCase):
    def test_merge_preserves_unknown_and_language_owned_fields(self) -> None:
        existing = ReviewCardShell(
            frontmatter={
                "term": "合成語",
                "accent_display": "⓪",
                "custom_user_note": "keep this",
                "review_stage": 1,
            },
            body="Manual study note body.",
        )

        merged = merge_review_card_fields(existing, {"review_stage": 2, "next_review": "2026-06-21"})

        self.assertEqual("合成語", merged.frontmatter["term"])
        self.assertEqual("⓪", merged.frontmatter["accent_display"])
        self.assertEqual("keep this", merged.frontmatter["custom_user_note"])
        self.assertEqual(2, merged.frontmatter["review_stage"])
        self.assertEqual("2026-06-21", merged.frontmatter["next_review"])
        self.assertEqual("Manual study note body.", merged.body)

    def test_merge_does_not_mutate_existing_shell(self) -> None:
        existing = ReviewCardShell(frontmatter={"review_stage": 1}, body="body")

        merged = merge_review_card_fields(existing, {"review_stage": 2})

        self.assertEqual(1, existing.frontmatter["review_stage"])
        self.assertEqual(2, merged.frontmatter["review_stage"])


if __name__ == "__main__":
    unittest.main()
