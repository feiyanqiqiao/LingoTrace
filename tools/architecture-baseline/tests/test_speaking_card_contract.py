from __future__ import annotations

import unittest

from helpers import embedded_links, parse_markdown_fixture, read_fixture_json


class SpeakingCardContractTests(unittest.TestCase):
    def test_reviewed_speaking_card_has_required_fields_sections_and_audio_reference(self) -> None:
        frontmatter, body = parse_markdown_fixture("speaking-cards", "restaurant-card.md")

        self.assertEqual(frontmatter["track"], "survival_speaking")
        self.assertEqual(frontmatter["review_status"], "human_reviewed")
        self.assertEqual(frontmatter["jp_text"], "予約しています。山田です。")
        self.assertEqual(frontmatter["scene"], "restaurant")
        self.assertIn("artifacts/restaurant-line.slice.txt", embedded_links(body))
        self.assertIn("## 快速复习", body)
        self.assertIn("## 使用场景", body)
        self.assertIn("## 来源", body)

    def test_unreviewed_listening_candidate_is_not_a_formal_speaking_card(self) -> None:
        frontmatter, _ = parse_markdown_fixture("speaking-cards", "unreviewed-listening-candidate.md")

        self.assertEqual(frontmatter["candidate_status"], "unreviewed")
        self.assertNotEqual(frontmatter.get("track"), "survival_speaking")

    def test_duplicate_registry_requires_reject_or_merge_decision(self) -> None:
        registry = read_fixture_json("speaking-cards", "duplicate-registry.json")

        self.assertEqual(registry["duplicate_key"], "予約しています。山田です。")
        self.assertIn(registry["decision"], {"reject", "merge"})
        self.assertEqual(registry["behavior_id"], "JP-SPEAK-002")

    def test_scene_guide_is_not_in_review_card_queue(self) -> None:
        frontmatter, _ = parse_markdown_fixture("speaking-cards", "scene-guide.md")

        self.assertEqual(frontmatter["doc_type"], "speaking_scene_guide")
        self.assertNotEqual(frontmatter.get("track"), "survival_speaking")


if __name__ == "__main__":
    unittest.main()
