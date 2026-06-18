from __future__ import annotations

import unittest

from helpers import embedded_links, fixture_path, parse_markdown_fixture, read_fixture_json


class ListeningContractTests(unittest.TestCase):
    def test_extensive_note_has_no_intensive_blocks_or_slices(self) -> None:
        frontmatter, body = parse_markdown_fixture("listening", "extensive-note.md")

        self.assertEqual(frontmatter["listening_mode"], "extensive")
        self.assertEqual(frontmatter["segment_count"], 0)
        self.assertNotIn("## 精听", body)
        self.assertNotIn("### S01", body)
        self.assertEqual([link for link in embedded_links(body) if link.startswith("slices/")], [])

    def test_intensive_note_segments_match_manifest_and_nonempty_slice_files(self) -> None:
        frontmatter, body = parse_markdown_fixture("listening", "intensive-note.md")
        manifest = read_fixture_json("listening", "intensive-manifest.json")
        slice_links = [link for link in embedded_links(body) if link.startswith("slices/")]

        self.assertEqual(frontmatter["listening_mode"], "intensive")
        self.assertEqual(frontmatter["segment_count"], 2)
        self.assertEqual([entry["id"] for entry in manifest["slices"]], ["S01", "S02"])
        self.assertEqual(slice_links, ["slices/S01.slice.txt", "slices/S02.slice.txt"])
        for link in slice_links:
            self.assertGreater(fixture_path("listening", link).stat().st_size, 0)

    def test_unreliable_timestamps_require_reviewed_manifest(self) -> None:
        decision = read_fixture_json("listening", "unreliable-timestamps.json")

        self.assertEqual(decision["completion_status"], "blocked")
        self.assertEqual(decision["required_resolution"], "reviewed_slice_manifest")
        self.assertEqual(decision["behavior_id"], "JP-LISTEN-004")

    def test_rerun_preserves_manual_sentence_selection_and_sections(self) -> None:
        before_frontmatter, before_body = parse_markdown_fixture("listening", "rerun-before.md")
        after_frontmatter, after_body = parse_markdown_fixture("listening", "rerun-after.md")

        self.assertEqual(after_frontmatter["daily_use_sentences"], before_frontmatter["daily_use_sentences"])
        self.assertIn("## 我的备注", after_body)
        self.assertIn("この選択は手作業で残したい。", after_body)
        self.assertIn("原句：駅まで歩いて行けます。", after_body)


if __name__ == "__main__":
    unittest.main()
