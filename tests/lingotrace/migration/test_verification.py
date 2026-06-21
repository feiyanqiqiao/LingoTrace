from __future__ import annotations

import unittest

from lingotrace.migration.verification import (
    SUPPORTED_COMPARISON_STRATEGIES,
    build_verification_report,
    verify_migration_acceptance,
)


def accepted_manifest() -> dict[str, object]:
    preserved_entry = {
        "relative_path": "review/focus/vocab/合成語.md",
        "classification": "preserve-data",
        "comparison_strategy": "content_hash",
        "content_hash": "sha256:same",
        "fields": {
            "review_stage": 2,
            "next_review": "2026-06-22",
            "done_today": False,
        },
        "links": ["sources/合成語-source.md"],
        "attachments": ["audio/合成語.m4a"],
    }
    recreated_entry = {
        "relative_path": "review/templates/focus-vocab-card.md",
        "classification": "recreate-from-pack",
        "comparison_strategy": "field_aware",
    }
    transformed_entry = {
        "relative_path": "old/review-card.md",
        "target_path": "review/focus/vocab/review-card.md",
        "classification": "transform-with-map",
        "comparison_strategy": "field_aware",
        "field_mapping": {"meaning": "meaning_zh"},
        "before": {"meaning": "合成词"},
        "after": {"meaning_zh": "合成词"},
        "preview_result": "planned",
        "conflict_status": "clear",
        "acceptance_result": "dry-run-only",
    }
    removed_entry = {
        "relative_path": "codex-skills/jp-review-material-maintainer/SKILL.md",
        "classification": "remove-after-cutover",
    }
    excluded_entry = {
        "relative_path": "private/manual-note.md",
        "classification": "excluded_with_user_approval",
        "approval": {"approved_by": "owner", "reason": "private note excluded"},
    }

    return {
        "source_manifest": [
            preserved_entry,
            recreated_entry,
            transformed_entry,
            removed_entry,
            excluded_entry,
        ],
        "target_manifest": [
            {
                "relative_path": "review/focus/vocab/合成語.md",
                "content_hash": "sha256:same",
                "fields": {
                    "review_stage": 2,
                    "next_review": "2026-06-22",
                    "done_today": False,
                },
                "links": ["sources/合成語-source.md"],
                "resolved_links": ["sources/合成語-source.md"],
                "attachments": ["audio/合成語.m4a"],
                "available_attachments": ["audio/合成語.m4a"],
            },
            {
                "relative_path": "review/focus/vocab/review-card.md",
                "fields": {"meaning_zh": "合成词"},
            },
        ],
        "preserve_data": [preserved_entry],
        "recreate_from_pack": [recreated_entry],
        "transform_with_map": [transformed_entry],
        "remove_after_cutover": [removed_entry],
        "excluded_with_user_approval": [excluded_entry],
        "conflicts": [],
    }


class MigrationVerificationTests(unittest.TestCase):
    def test_supported_comparison_strategies_match_contract(self) -> None:
        self.assertEqual(
            [
                "content_hash",
                "frontmatter_and_body",
                "links_and_hashes",
                "field_aware",
            ],
            SUPPORTED_COMPARISON_STRATEGIES,
        )

    def test_verification_report_counts_acceptance_inputs(self) -> None:
        report = build_verification_report(accepted_manifest())

        self.assertEqual(
            {
                "preserved_count": 1,
                "recreated_count": 1,
                "transformed_count": 1,
                "excluded_count": 1,
                "unresolved_conflict_count": 0,
                "missing_approval_count": 0,
                "failed_comparison_count": 0,
                "accepted": True,
            },
            report,
        )

    def test_blocking_conditions_are_reported_and_reject_acceptance(self) -> None:
        manifest = accepted_manifest()
        source_manifest = manifest["source_manifest"]
        target_manifest = manifest["target_manifest"]
        assert isinstance(source_manifest, list)
        assert isinstance(target_manifest, list)

        source_manifest.extend(
            [
                {
                    "relative_path": "review/focus/vocab/hash.md",
                    "classification": "preserve-data",
                    "comparison_strategy": "content_hash",
                    "content_hash": "sha256:source",
                },
                {
                    "relative_path": "listening/missing-attachment.md",
                    "classification": "preserve-data",
                    "comparison_strategy": "links_and_hashes",
                    "attachments": ["audio/missing.m4a"],
                },
                {
                    "relative_path": "sources/unresolved-link.md",
                    "classification": "preserve-data",
                    "comparison_strategy": "links_and_hashes",
                    "links": ["missing-note"],
                },
                {
                    "relative_path": "review/focus/vocab/srs.md",
                    "classification": "preserve-data",
                    "comparison_strategy": "field_aware",
                    "fields": {
                        "review_stage": 3,
                        "next_review": "2026-06-23",
                        "done_today": True,
                    },
                },
                {
                    "relative_path": "unknown.bin",
                    "classification": "unclassified",
                },
                {
                    "relative_path": "private/missing-approval.md",
                    "classification": "excluded_with_user_approval",
                },
            ]
        )
        target_manifest.extend(
            [
                {
                    "relative_path": "review/focus/vocab/hash.md",
                    "content_hash": "sha256:target",
                },
                {
                    "relative_path": "listening/missing-attachment.md",
                    "attachments": ["audio/missing.m4a"],
                    "available_attachments": [],
                },
                {
                    "relative_path": "sources/unresolved-link.md",
                    "links": ["missing-note"],
                    "resolved_links": [],
                },
                {
                    "relative_path": "review/focus/vocab/srs.md",
                    "fields": {
                        "review_stage": 2,
                        "next_review": "2026-06-23",
                        "done_today": True,
                    },
                },
            ]
        )

        report = verify_migration_acceptance(manifest)
        envelope = report.to_dict()

        self.assertFalse(report.accepted)
        self.assertEqual(
            [
                "content_hash_mismatch",
                "missing_attachment",
                "unresolved_link",
                "srs_field_mismatch",
                "unclassified_entry",
                "missing_user_approval",
            ],
            [finding["code"] for finding in envelope["errors"]],
        )
        self.assertEqual(
            {
                "preserved_count": 1,
                "recreated_count": 1,
                "transformed_count": 1,
                "excluded_count": 2,
                "unresolved_conflict_count": 1,
                "missing_approval_count": 1,
                "failed_comparison_count": 4,
                "accepted": False,
            },
            envelope["planned_writes"][0]["verification_report"],
        )
        self.assertEqual([], envelope["changed_files"])

    def test_verification_uses_target_path_for_mapped_preserve_data(self) -> None:
        manifest = {
            "source_manifest": [
                {
                    "relative_path": "学习系统/听力/Unit1/01.mp3",
                    "target_path": "listening/Unit1/01.mp3",
                    "classification": "preserve-data",
                    "comparison_strategy": "content_hash",
                    "content_hash": "sha256:same",
                }
            ],
            "target_manifest": [
                {
                    "relative_path": "listening/Unit1/01.mp3",
                    "content_hash": "sha256:same",
                }
            ],
            "preserve_data": [
                {
                    "relative_path": "学习系统/听力/Unit1/01.mp3",
                    "target_path": "listening/Unit1/01.mp3",
                    "classification": "preserve-data",
                }
            ],
            "recreate_from_pack": [],
            "transform_with_map": [],
            "remove_after_cutover": [],
            "excluded_with_user_approval": [],
            "conflicts": [],
        }

        report = verify_migration_acceptance(manifest)

        self.assertTrue(report.accepted, report.to_dict())


if __name__ == "__main__":
    unittest.main()
