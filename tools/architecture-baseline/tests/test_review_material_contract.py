from __future__ import annotations

import unittest

from helpers import parse_markdown_fixture, read_fixture_json, wikilinks


class ReviewMaterialContractTests(unittest.TestCase):
    def test_lookup_cases_preserve_focus_first_and_routing_decisions(self) -> None:
        cases = read_fixture_json("review-materials", "lookup-cases.json")

        self.assertEqual(cases["search_order"], ["focus", "base"])
        self.assertEqual(cases["cases"]["new_vocab"]["action"], "create_focus_card")
        self.assertEqual(cases["cases"]["base_match"]["action"], "restore_focus_card")
        self.assertEqual(cases["cases"]["mastered_reappears"]["new_review_stage"], "day0")
        self.assertEqual(cases["cases"]["grammar_input"]["target_root"], "grammar")
        self.assertEqual(cases["cases"]["error_input"]["target_root"], "error")

    def test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body(self) -> None:
        frontmatter, body = parse_markdown_fixture("review-materials", "base-after-sink.md")

        self.assertEqual(frontmatter["status"], "promoted")
        self.assertEqual(frontmatter["reading"], "まぎらわしい")
        self.assertEqual(frontmatter["meaning_zh"], "容易混淆")
        self.assertEqual(frontmatter["accent_display"], "まぎらわしい⑤")
        self.assertEqual(frontmatter["kanji_diff"], True)
        self.assertEqual(frontmatter["kanji_diff_pairs"], ["紛らわしい / 間違えやすい"])
        self.assertEqual(frontmatter["seen_count"], 4)
        self.assertEqual(frontmatter["error_count"], 1)
        self.assertIn("[[source-note]]", frontmatter["source_notes"])
        self.assertIn("## 人工整理", body)
        self.assertIn("ここは移行時にも残す。", body)
        self.assertIn("source-note", wikilinks(body))

    def test_grammar_and_error_cards_do_not_route_to_vocab_layer(self) -> None:
        grammar_frontmatter, _ = parse_markdown_fixture("review-materials", "grammar-card.md")
        error_frontmatter, _ = parse_markdown_fixture("review-materials", "error-card.md")

        self.assertEqual(grammar_frontmatter["item_type"], "grammar")
        self.assertEqual(grammar_frontmatter["target_root"], "grammar")
        self.assertEqual(error_frontmatter["item_type"], "error")
        self.assertEqual(error_frontmatter["target_root"], "error")


if __name__ == "__main__":
    unittest.main()
