from __future__ import annotations

import unittest

from lingotrace.migration.private_artifacts import validate_public_report_paths


class PrivateArtifactGuardTests(unittest.TestCase):
    def test_rejects_personal_absolute_path_markers_in_public_reports(self) -> None:
        report = validate_public_report_paths(
            {
                "artifact": "personal-home/Documents/source-vault/private-manifest.json",
                "detail": "contains personal-home marker",
            },
            personal_path_markers=("personal-home/",),
        )

        self.assertFalse(report.accepted)
        self.assertEqual(["personal_absolute_path_rejected"], [finding["code"] for finding in report.to_dict()["errors"]])
        self.assertEqual("artifact", report.to_dict()["errors"][0]["path"])

    def test_rejects_explicit_private_roots_and_user_markers(self) -> None:
        report = validate_public_report_paths(
            {
                "source_vault": "private-source-root",
                "target": {"manifest": "private-target-root/artifacts/final-target.json"},
                "owner": "private-user-marker",
            },
            private_roots=("private-source-root", "private-target-root"),
            private_name_markers=("private-user-marker",),
        )

        envelope = report.to_dict()
        self.assertFalse(report.accepted)
        self.assertEqual(
            [
                "private_path_in_public_report",
                "private_path_in_public_report",
                "private_path_in_public_report",
            ],
            [finding["code"] for finding in envelope["errors"]],
        )
        self.assertEqual(["owner", "source_vault", "target.manifest"], [finding["path"] for finding in envelope["errors"]])

    def test_accepts_vault_relative_and_synthetic_fixture_paths(self) -> None:
        report = validate_public_report_paths(
            {
                "source_manifest": [
                    {"relative_path": "review/focus/vocab/example.md"},
                    {"relative_path": "tools/architecture-baseline/fixtures/migration/source.md"},
                ],
                "artifact": "artifacts/synthetic-report.json",
            },
            private_roots=("private-source-root",),
            private_name_markers=("private-user-marker",),
            personal_path_markers=("personal-home/",),
        )

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual([], report.to_dict()["errors"])


if __name__ == "__main__":
    unittest.main()
