from __future__ import annotations

import unittest

from helpers import embedded_links, heading_order, parse_markdown_fixture


class SourceNoteContractTests(unittest.TestCase):
    def test_media_source_note_tracks_materials_and_keeps_transcript_appendix_last(self) -> None:
        frontmatter, body = parse_markdown_fixture("source-notes", "url-audio-source-note.md")
        headings = heading_order(body)

        self.assertEqual(frontmatter["source_kind"], "url_audio")
        self.assertEqual(frontmatter["creates_review_cards"], False)
        self.assertEqual(frontmatter["final_audio"], "artifacts/url-audio.source.txt")
        self.assertEqual(frontmatter["transcript_markdown"], "artifacts/url-audio.transcript.md")
        self.assertEqual(frontmatter["transcript_json"], "artifacts/url-audio.transcript.json")
        self.assertIn("artifacts/url-audio.source.txt", embedded_links(body))
        self.assertGreater(headings.index("转写附录"), headings.index("学习要点"))

    def test_plain_text_source_note_declares_no_audio_without_fabricated_embed(self) -> None:
        frontmatter, body = parse_markdown_fixture("source-notes", "plain-text-source-note.md")

        self.assertEqual(frontmatter["source_kind"], "plain_text")
        self.assertEqual(frontmatter["has_audio"], False)
        self.assertEqual(frontmatter["final_audio"], "")
        self.assertEqual(embedded_links(body), [])
        self.assertIn("无音频素材", body)


if __name__ == "__main__":
    unittest.main()
