from __future__ import annotations

import unittest

from lingotrace.core.review_lifecycle import queue_transition_updates, validate_review_lifecycle


class ReviewLifecycleTests(unittest.TestCase):
    def test_all_supported_states_validate(self) -> None:
        fixtures = (
            {"review_status": "backlog", "done_today": False, "review_stage": "", "next_review": ""},
            {"review_status": "backlog", "done_today": False, "review_stage": "day30", "next_review": "2026-08-01"},
            {"review_status": "queued", "done_today": True, "review_stage": "day3", "next_review": "2026-08-14"},
            {"review_status": "mastered", "done_today": False, "review_stage": "mastered", "next_review": ""},
            {"review_status": "archived", "done_today": False, "review_stage": "day7", "next_review": "2026-01-01"},
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertEqual([], validate_review_lifecycle(fixture))

    def test_illegal_state_combinations_are_rejected(self) -> None:
        fixtures = (
            {"review_status": "queued", "done_today": False, "review_stage": "", "next_review": ""},
            {"review_status": "backlog", "done_today": True, "review_stage": "day1", "next_review": "2026-08-14"},
            {"review_status": "mastered", "done_today": False, "review_stage": "day180", "next_review": ""},
            {"review_status": "archived", "done_today": True, "review_stage": "day7", "next_review": "2026-01-01"},
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertTrue(validate_review_lifecycle(fixture))

    def test_resume_preserves_progress_and_restart_resets_it(self) -> None:
        fields = {"review_status": "backlog", "done_today": False, "review_stage": "day30", "next_review": "2026-07-01", "last_reviewed": "2026-06-01"}
        resume = queue_transition_updates(fields, target_status="queued", activation="resume", change_date="2026-08-14")
        restart = queue_transition_updates(fields, target_status="queued", activation="restart", change_date="2026-08-14")
        self.assertEqual("day30", resume["review_stage"])
        self.assertEqual("2026-08-14", resume["next_review"])
        self.assertEqual("day0", restart["review_stage"])
        self.assertEqual("", restart["last_reviewed"])


if __name__ == "__main__":
    unittest.main()
