from __future__ import annotations

import unittest

from lingotrace.migration.schema import (
    VALID_COMPARISON_STRATEGIES,
    VALID_MIGRATION_CLASSIFICATIONS,
    validate_migration_manifest,
)


def valid_manifest() -> dict[str, object]:
    return {
        "source_vault": "source-vault",
        "target_vault": "target-vault",
        "source_manifest": [
            {
                "relative_path": "review/focus/vocab/example.md",
                "classification": "preserve-data",
                "comparison_strategy": "frontmatter_and_body",
            }
        ],
        "target_manifest": [
            {
                "relative_path": "review/focus/vocab/example.md",
                "classification": "preserve-data",
                "comparison_strategy": "frontmatter_and_body",
            }
        ],
        "preserve_data": [],
        "recreate_from_pack": [],
        "transform_with_map": [],
        "remove_after_cutover": [],
        "excluded_with_user_approval": [],
        "conflicts": [],
        "verification_report": {"accepted": True},
    }


class MigrationManifestSchemaTests(unittest.TestCase):
    def test_manifest_requires_phase2_keys(self) -> None:
        manifest = valid_manifest()
        del manifest["target_manifest"]

        report = validate_migration_manifest(manifest)

        self.assertFalse(report.accepted)
        self.assertEqual(["migration_manifest_missing_key"], [finding["code"] for finding in report.to_dict()["errors"]])
        self.assertEqual("target_manifest", report.to_dict()["errors"][0]["path"])

    def test_manifest_rejects_invalid_classification(self) -> None:
        manifest = valid_manifest()
        manifest["source_manifest"] = [
            {
                "relative_path": "unknown.bin",
                "classification": "copy-whatever",
                "comparison_strategy": "content_hash",
            }
        ]

        report = validate_migration_manifest(manifest)

        self.assertFalse(report.accepted)
        self.assertEqual(
            ["migration_manifest_invalid_classification"],
            [finding["code"] for finding in report.to_dict()["errors"]],
        )
        self.assertEqual("source_manifest[0].classification", report.to_dict()["errors"][0]["path"])

    def test_manifest_rejects_invalid_comparison_strategy(self) -> None:
        manifest = valid_manifest()
        manifest["target_manifest"] = [
            {
                "relative_path": "review/focus/vocab/example.md",
                "classification": "preserve-data",
                "comparison_strategy": "manual-eyeball",
            }
        ]

        report = validate_migration_manifest(manifest)

        self.assertFalse(report.accepted)
        self.assertEqual(
            ["migration_manifest_invalid_comparison_strategy"],
            [finding["code"] for finding in report.to_dict()["errors"]],
        )
        self.assertEqual("target_manifest[0].comparison_strategy", report.to_dict()["errors"][0]["path"])

    def test_valid_manifest_is_accepted(self) -> None:
        report = validate_migration_manifest(valid_manifest())

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual([], report.to_dict()["errors"])

    def test_valid_values_match_phase2_contract(self) -> None:
        self.assertEqual(
            {
                "preserve-data",
                "recreate-from-pack",
                "transform-with-map",
                "temporary-migration",
                "remove-after-cutover",
                "excluded_with_user_approval",
            },
            VALID_MIGRATION_CLASSIFICATIONS,
        )
        self.assertEqual(
            {
                "content_hash",
                "frontmatter_and_body",
                "links_and_hashes",
                "field_aware",
            },
            VALID_COMPARISON_STRATEGIES,
        )


if __name__ == "__main__":
    unittest.main()
