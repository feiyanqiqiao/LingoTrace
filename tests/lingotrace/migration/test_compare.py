from __future__ import annotations

import unittest

from lingotrace.migration.compare import COMPARISON_STRATEGIES, compare_migration_manifest


class MigrationCompareTests(unittest.TestCase):
    def test_comparison_strategies_match_phase1_contract(self) -> None:
        self.assertEqual(
            [
                "content_hash",
                "frontmatter_and_body",
                "links_and_hashes",
                "field_aware",
            ],
            COMPARISON_STRATEGIES,
        )

    def test_conflicts_block_comparison_acceptance(self) -> None:
        report = compare_migration_manifest(
            {
                "conflicts": [
                    {
                        "code": "unclassified_entry",
                        "relative_path": "unknown.bin",
                        "message": "Unclassified entries block acceptance.",
                    }
                ],
                "verification_report": {"accepted": False},
            }
        )

        self.assertFalse(report.accepted)
        self.assertEqual("unclassified_entry", report.to_dict()["errors"][0]["code"])

    def test_clear_manifest_is_accepted(self) -> None:
        report = compare_migration_manifest(
            {
                "conflicts": [],
                "verification_report": {"accepted": True},
            }
        )

        self.assertTrue(report.accepted, report.to_dict())


if __name__ == "__main__":
    unittest.main()
