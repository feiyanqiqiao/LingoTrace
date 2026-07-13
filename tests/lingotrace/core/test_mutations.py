from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lingotrace.core.mutations import FileMutation, run_file_mutations


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def create_context(root: Path, *enabled: str) -> None:
    write_json(
        root / ".lingotrace/vault-context.json",
        {
            "vault_schema_version": 1,
            "target_language": "ja",
            "explanation_language": "zh",
            "language_pack": "lingo-japanese",
            "language_pack_version": "0.1.0",
            "enabled_capabilities": list(enabled),
        },
    )


def create_manifest(root: Path) -> Path:
    manifest = root / "manifest.json"
    write_json(
        manifest,
        {
            "language_pack_id": "lingo-japanese",
            "language_pack_version": "0.1.0",
            "target_language": "ja",
            "capabilities": [
                {
                    "id": "review_materials",
                    "maturity": "stable",
                    "depends_on": [],
                    "read_path_roles": [],
                    "write_path_roles": ["focus_vocab_root"],
                    "external_tools": [],
                    "behavior_evidence": ["JP-REVIEW-001"],
                    "conformance_tests": ["tests/lingotrace/core/test_mutations.py"],
                    "manual_review_cases": [],
                }
            ],
            "unsupported_capabilities": [],
            "default_path_roles": {"focus_vocab_root": "review/focus/vocab"},
        },
    )
    return manifest


class FileMutationTests(unittest.TestCase):
    def test_preview_records_planned_writes_without_changing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root, "review_materials")
            manifest = create_manifest(root)

            report = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/example.md",
                        content="example",
                        action="create",
                        reason="new card",
                    )
                ],
                mode="preview",
            )

            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual([], report.to_dict()["changed_files"])
            self.assertFalse((root / "review/focus/vocab/example.md").exists())
            self.assertEqual(
                [{"path": "review/focus/vocab/example.md", "action": "create", "reason": "new card"}],
                report.to_dict()["planned_writes"],
            )

    def test_apply_writes_relative_target_file_after_preflight_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root, "review_materials")
            manifest = create_manifest(root)

            report = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/example.md",
                        content="example",
                        action="create",
                        reason="new card",
                    )
                ],
                mode="apply",
            )

            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual(["review/focus/vocab/example.md"], report.to_dict()["changed_files"])
            self.assertEqual("example", (root / "review/focus/vocab/example.md").read_text(encoding="utf-8"))

    def test_apply_blocks_disabled_capability_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root)
            manifest = create_manifest(root)

            report = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/example.md",
                        content="example",
                        action="create",
                        reason="new card",
                    )
                ],
                mode="apply",
            )

            self.assertFalse(report.accepted)
            self.assertEqual("capability_not_enabled", report.to_dict()["errors"][0]["code"])
            self.assertEqual(["review/focus/vocab/example.md"], report.to_dict()["blocked_files"])
            self.assertFalse((root / "review/focus/vocab/example.md").exists())

    def test_rejects_absolute_and_parent_relative_paths_before_writing_any_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root, "review_materials")
            manifest = create_manifest(root)

            report = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/valid.md",
                        content="valid",
                        action="create",
                        reason="valid card",
                    ),
                    FileMutation(
                        path="../outside.md",
                        content="invalid",
                        action="create",
                        reason="invalid escape",
                    ),
                ],
                mode="apply",
            )

            self.assertFalse(report.accepted)
            self.assertEqual("invalid_mutation_path", report.to_dict()["errors"][0]["code"])
            self.assertEqual(
                ["review/focus/vocab/valid.md", "../outside.md"],
                report.to_dict()["blocked_files"],
            )
            self.assertFalse((root / "review/focus/vocab/valid.md").exists())

    def test_apply_can_copy_binary_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()
            create_context(root, "review_materials")
            manifest = create_manifest(root)
            source = Path(tmp) / "slice.m4a"
            source.write_bytes(b"\x00\x01synthetic-audio\xff")

            report = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/slice.m4a",
                        content=None,
                        source_path=source,
                        action="copy_media",
                        reason="prepared binary artifact",
                    )
                ],
                mode="apply",
            )

            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual(source.read_bytes(), (root / "review/focus/vocab/slice.m4a").read_bytes())

    def test_missing_or_ambiguous_mutation_source_is_rejected_before_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root, "review_materials")
            manifest = create_manifest(root)

            missing = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/missing.bin",
                        content=None,
                        source_path=root / "does-not-exist.bin",
                        action="copy",
                        reason="missing source",
                    )
                ],
                mode="apply",
            )
            ambiguous = run_file_mutations(
                vault_root=root,
                manifest_path=manifest,
                capability_id="review_materials",
                mutations=[
                    FileMutation(
                        path="review/focus/vocab/ambiguous.md",
                        content="inline",
                        source_path=manifest,
                        action="copy",
                        reason="ambiguous source",
                    )
                ],
                mode="apply",
            )

            self.assertEqual(missing.errors[0].code, "mutation_source_missing")
            self.assertEqual(ambiguous.errors[0].code, "invalid_mutation_source")
            self.assertFalse((root / "review/focus/vocab/missing.bin").exists())
            self.assertFalse((root / "review/focus/vocab/ambiguous.md").exists())

    def test_apply_rolls_back_all_targets_when_a_replacement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_context(root, "review_materials")
            manifest = create_manifest(root)
            first = root / "review/focus/vocab/first.md"
            second = root / "review/focus/vocab/second.md"
            first.parent.mkdir(parents=True)
            first.write_text("old-first", encoding="utf-8")
            second.write_text("old-second", encoding="utf-8")
            real_replace = os.replace

            def fail_second_stage(source, target):
                source_path = Path(source)
                target_path = Path(target)
                if source_path.name.endswith(".lingotrace-stage") and target_path == second:
                    raise OSError("synthetic replacement failure")
                return real_replace(source, target)

            with mock.patch("lingotrace.core.mutations.os.replace", side_effect=fail_second_stage):
                with self.assertRaisesRegex(OSError, "synthetic replacement failure"):
                    run_file_mutations(
                        vault_root=root,
                        manifest_path=manifest,
                        capability_id="review_materials",
                        mutations=[
                            FileMutation("review/focus/vocab/first.md", "new-first", "update", "atomic test"),
                            FileMutation("review/focus/vocab/second.md", "new-second", "update", "atomic test"),
                        ],
                        mode="apply",
                    )

            self.assertEqual(first.read_text(encoding="utf-8"), "old-first")
            self.assertEqual(second.read_text(encoding="utf-8"), "old-second")
            self.assertEqual(list(first.parent.glob("*.lingotrace-stage")), [])
            self.assertEqual(list(first.parent.glob("*.lingotrace-backup")), [])


if __name__ == "__main__":
    unittest.main()
