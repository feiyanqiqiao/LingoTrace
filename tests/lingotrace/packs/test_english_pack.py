"""English language pack conformance tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PUBLIC_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest
from lingotrace.packs.english import workflows


REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "english"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
FIELDS_PATH = PACK_ROOT / "fields.json"
PATHS_PATH = PACK_ROOT / "paths.json"

EXPECTED_PATH_ROLES = {
    "focus_vocab_root": "review/focus/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily",
}

EXPECTED_LANGUAGE_FIELDS = {
    "ipa", "word_stress", "part_of_speech", "collocations", "english_definition",
    "meaning_zh", "chunk_pattern", "chunk_type", "chunk_meaning_zh", "practice_tier",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic-image")


def create_target_context(root: Path) -> None:
    write(
        root / ".lingotrace/vault-context.json",
        json.dumps(
            {
                "vault_schema_version": 1,
                "target_language": "en",
                "explanation_language": "zh",
                "language_pack": "lingo-english",
                "language_pack_version": "0.1.0",
                "enabled_capabilities": [
                    "listening_notes",
                    "source_notes",
                    "review_materials",
                    "review_queue",
                    "speaking_cards",
                    "review_rollover",
                    "total_training_dashboard",
                ],
            },
            ensure_ascii=False,
        ),
    )
    write(
        root / ".lingotrace/paths.json",
        json.dumps(
            {
                "path_roles": [
                    {"role": "focus_vocab_root", "relative_path": "review/focus/vocab", "source": "vault_config"},
                    {"role": "base_vocab_root", "relative_path": "review/base/vocab", "source": "vault_config"},
                    {"role": "grammar_root", "relative_path": "review/grammar", "source": "vault_config"},
                    {"role": "error_root", "relative_path": "review/errors", "source": "vault_config"},
                    {"role": "speaking_card_root", "relative_path": "speaking/cards", "source": "vault_config"},
                    {"role": "speaking_guide_root", "relative_path": "speaking/guides", "source": "vault_config"},
                    {"role": "listening_root", "relative_path": "listening", "source": "vault_config"},
                    {"role": "source_notes_root", "relative_path": "sources", "source": "vault_config"},
                    {"role": "daily_notes_root", "relative_path": "daily", "source": "vault_config"},
                    {"role": "pronunciation_accent_root", "relative_path": "review/pronunciation/accent", "source": "vault_config"},
                    {"role": "pronunciation_phoneme_root", "relative_path": "review/pronunciation/phoneme", "source": "vault_config"},
                ]
            },
            ensure_ascii=False,
        ),
    )


def remove_base_vocab_role(root: Path) -> None:
    path = root / ".lingotrace/paths.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["path_roles"] = [entry for entry in payload["path_roles"] if entry["role"] != "base_vocab_root"]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def review_card(
    *,
    track: str = "class_review",
    item_type: str = "vocab",
    review_status: str = "queued",
    done_today: str = "true",
    review_stage: str = "day0",
    next_review: str = "2026-06-21",
    last_reviewed: str = "",
    headword: str = "synthetic",
    meaning_zh: str = "synthetic",
    ipa: str = "",
    english_definition: str = "",
    collocations: str = "",
    pattern: str = "",
    formation: str = "",
    correct_form: str = "",
    wrong_form: str = "",
    target_text: str = "",
    issue_tags: str = "",
    source_notes: str = "",
) -> str:
    lines = [
        "---",
        f"track: {track}",
        f"item_type: {item_type}",
        f"review_status: {review_status}",
        f"done_today: {done_today}",
        f"review_stage: {review_stage}",
        f"next_review: {next_review}",
        f"last_reviewed: {last_reviewed}",
        f"headword: {headword}",
        f"meaning_zh: {meaning_zh}",
    ]
    if ipa:
        lines.append(f"ipa: {ipa}")
    if english_definition:
        lines.append(f"english_definition: {english_definition}")
    if collocations:
        lines.append(f"collocations: {collocations}")
    if pattern:
        lines.append(f"pattern: {pattern}")
    if formation:
        lines.append(f"formation: {formation}")
    if correct_form:
        lines.append(f"correct_form: {correct_form}")
    if wrong_form:
        lines.append(f"wrong_form: {wrong_form}")
    if target_text:
        lines.append(f"target_text: {target_text}")
    if issue_tags:
        lines.append(f"issue_tags: {issue_tags}")
    if source_notes:
        lines.append(f"source_notes: {source_notes}")
    lines.append("---")
    lines.append("")
    lines.append("# synthetic")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifest and static capability tests
# ---------------------------------------------------------------------------


class EnglishPackTests(unittest.TestCase):

    def test_manifest_loads_through_core_loader(self):
        """1. Manifest passes load_language_pack_manifest without errors."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        self.assertTrue(result.report.accepted, result.report.to_dict())
        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-english", result.manifest.language_pack_id)
        self.assertEqual("0.1.0", result.manifest.language_pack_version)
        self.assertEqual("en", result.manifest.target_language)

    def test_declared_capabilities_are_subset_of_phase0_ids(self):
        """2. All declared capabilities use reviewed public capability IDs."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        declared_ids = set(result.manifest.capabilities) | set(result.manifest.unsupported_capabilities)
        self.assertTrue(declared_ids.issubset(PUBLIC_CAPABILITY_IDS))
        self.assertEqual(PUBLIC_CAPABILITY_IDS, declared_ids)

    def test_all_phase0_capabilities_are_supported(self):
        """3. English leaves no public capability unsupported."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        self.assertEqual({}, result.manifest.unsupported_capabilities)
        self.assertEqual(PUBLIC_CAPABILITY_IDS, set(result.manifest.capabilities))

    def test_language_fields_are_english_pack_owned(self):
        """4. fields.json declares English-owned fields, not Japanese fields."""
        fields = json.loads(FIELDS_PATH.read_text(encoding="utf-8"))
        field_names = {r["name"] for r in fields["language_fields"]}
        self.assertEqual(EXPECTED_LANGUAGE_FIELDS, field_names)
        for record in fields["language_fields"]:
            self.assertEqual("English language pack", record["owner"])
        self.assertNotIn("reading", field_names)
        self.assertNotIn("accent_display", field_names)
        self.assertNotIn("kanji_diff", field_names)

    def test_default_path_roles_match_phase1_design(self):
        """5. Path roles align with general architectural paths."""
        paths = json.loads(PATHS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_PATH_ROLES, paths["default_path_roles"])

    def test_workflow_stubs_do_not_reference_japanese_runtime(self):
        """6. workflows.py does not import or reference Japanese pack modules."""
        source = (PACK_ROOT / "workflows.py").read_text(encoding="utf-8")
        self.assertNotIn("japanese", source.lower())
        self.assertNotIn("jp-", source)

    def test_pack_owned_surfaces_are_manifest_declared_and_files_exist(self):
        """7. Every template declared in manifest exists on disk."""
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for record in manifest.get("templates", []):
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])

    def test_total_training_dashboard_template_exists(self):
        """8. The total-training.base view template exists under views/."""
        dashboard_path = PACK_ROOT / "views" / "total-training.base"
        self.assertTrue(dashboard_path.is_file(), f"Missing: {dashboard_path}")


# ---------------------------------------------------------------------------
# Workflow preview tests
# ---------------------------------------------------------------------------


class EnglishWorkflowPreviewTests(unittest.TestCase):
    def test_workflows_fail_explicitly_without_vault_root(self) -> None:
        for workflow_fn in (
            workflows.source_notes,
            workflows.review_materials,
            workflows.review_rollover,
        ):
            report = workflow_fn()
            self.assertFalse(report.accepted)
            self.assertEqual("missing_vault_root", report.to_dict()["errors"][0]["code"])

    def test_listening_and_speaking_workflows_preview_guarded_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            listening = workflows.listening_notes(
                vault_root=root,
                input_artifact={"path": "listening/sample.md", "body": "## Transcript\nHello."},
            )
            speaking = workflows.speaking_cards(
                vault_root=root,
                candidate={
                    "path": "speaking/cards/hello.md", "reviewed": True,
                    "body": "---\nitem_type: speaking_card\nen_text: Hello.\n---\n\n## Target\nHello.\n",
                },
            )

        for report in (listening, speaking):
            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual("preview", report.mode)
            self.assertEqual([], report.changed_files)
            self.assertEqual(1, len(report.planned_writes))

    def test_source_notes_previews_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.source_notes(
                vault_root=root,
                source_artifact={
                    "path": "sources/sample-source.md",
                    "title": "Sample Source",
                    "body": "## Source\nTest source note.",
                },
            )

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(1, len(envelope["planned_writes"]))

    def test_source_notes_apply_writes_target_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            report = workflows.source_notes(
                vault_root=root,
                mode="apply",
                source_artifact={
                    "path": "sources/sample-source.md",
                    "title": "Sample Source",
                    "body": "## Source\nTest source note.",
                },
            )
            envelope = report.to_dict()

        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["sources/sample-source.md"], envelope["changed_files"])

    def test_review_materials_previews_target_vault_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(
                root / "review/focus/vocab/test-vocab.md",
                """---
track: class_review
item_type: vocab
status: active
done_today: false
review_stage: day1
next_review: 2026-06-22
headword: test
meaning_zh: 测试
ipa: /tɛst/
---
# test
""",
            )

            report = workflows.review_materials(vault_root=root)

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("review_materials-workflow", envelope["command"])
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(1, len(envelope["planned_writes"]))

    def test_review_materials_item_creates_initialized_focus_vocab_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            remove_base_vocab_role(root)
            write(root / "sources/source-note.md", "# Source\n")

            preview = workflows.review_materials(
                vault_root=root,
                item={
                    "item_type": "vocab",
                    "headword": "ubiquitous",
                    "ipa": "/juːˈbɪk.wɪ.təs/",
                    "meaning_zh": "无处不在的",
                    "source_note": "[[source-note]]",
                },
            )
            preview_env = preview.to_dict()
            self.assertTrue(preview.accepted, preview_env)
            planned = preview_env["planned_writes"][0]
            self.assertEqual("review/focus/vocab/ubiquitous.md", planned["path"])

            report = workflows.review_materials(
                vault_root=root,
                mode="apply",
                item={
                    "item_type": "vocab",
                    "headword": "ubiquitous",
                    "ipa": "/juːˈbɪk.wɪ.təs/",
                    "meaning_zh": "无处不在的",
                    "source_note": "[[source-note]]",
                },
            )
            envelope = report.to_dict()
            self.assertTrue(report.accepted, envelope)
            body = (root / "review/focus/vocab/ubiquitous.md").read_text(encoding="utf-8")
            self.assertIn("headword: ubiquitous", body)
            self.assertIn("ipa: /juːˈbɪk.wɪ.təs/", body)
            self.assertIn("review_stage: day0", body)


# ---------------------------------------------------------------------------
# English/Japanese parity contracts
# ---------------------------------------------------------------------------


class EnglishParityWorkflowTests(unittest.TestCase):
    def test_listening_bundle_applies_note_and_real_slice_inside_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            report = workflows.listening_notes(
                vault_root=root, mode="apply",
                input_artifact={
                    "note_path": "listening/demo.md",
                    "files": [
                        {"path": "listening/demo.md", "content": "# Demo\n\n## Transcript\nHello world.\n"},
                        {"path": "listening/demo-slices/S01.mp3", "content": b"synthetic-audio"},
                    ],
                },
            )
            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual(["listening/demo-slices/S01.mp3", "listening/demo.md"], sorted(report.changed_files))
            self.assertEqual(b"synthetic-audio", (root / "listening/demo-slices/S01.mp3").read_bytes())

    def test_listening_bundle_cannot_escape_listening_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            report = workflows.listening_notes(vault_root=root, input_artifact={"path": "sources/not-listening.md", "body": "# Wrong root"})
        self.assertFalse(report.accepted)
        self.assertEqual("listening_artifact_outside_role", report.errors[0].code)

    def test_speaking_card_requires_review_and_deduplicates_chunk_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            unreviewed = workflows.speaking_cards(vault_root=root, candidate={"path": "speaking/cards/a.md", "body": "# A"})
            self.assertFalse(unreviewed.accepted)
            self.assertEqual("unreviewed_speaking_candidate", unreviewed.errors[0].code)
            write(root / "speaking/cards/existing.md", "---\nitem_type: chunk\nchunk_pattern: It goes without saying that ...\n---\n\n# Existing\n")
            duplicate = workflows.speaking_cards(
                vault_root=root,
                candidate={"path": "speaking/cards/new.md", "reviewed": True, "body": "---\nitem_type: chunk\nchunk_pattern: It goes without saying that ...\n---\n\n# New\n"},
            )
        self.assertFalse(duplicate.accepted)
        self.assertEqual("duplicate_chunk_pattern", duplicate.errors[0].code)

    def test_structured_vocab_renders_english_cues_and_canonical_source_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/article.md", "# Article\n")
            report = workflows.review_materials(
                vault_root=root, mode="apply", extraction_date="2026-08-08",
                item={
                    "item_type": "vocab", "headword": "ubiquitous", "ipa": "/juːˈbɪk.wɪ.təs/",
                    "word_stress": "bi", "part_of_speech": "adjective",
                    "english_definition": "present or found everywhere", "meaning_zh": "无处不在的",
                    "collocations": ["ubiquitous computing"],
                    "examples": [{"en": "Smartphones are ubiquitous.", "zh": "智能手机无处不在。"}],
                    "source_note": "sources/article",
                },
            )
            body = (root / "review/focus/vocab/ubiquitous.md").read_text(encoding="utf-8")
        self.assertTrue(report.accepted, report.to_dict())
        for expected in ("IPA：/juːˈbɪk.wɪ.təs/", "重音：bi", "词性：adjective", "## English Definition", "present or found everywhere", "ubiquitous computing", "Smartphones are ubiquitous.", "[[sources/article|article]]"):
            self.assertIn(expected, body)

    def test_structured_items_route_to_grammar_error_and_pronunciation_roles(self) -> None:
        cases = (
            ({"item_type": "grammar", "pattern": "used to + verb", "meaning_zh": "过去常常", "formation": ["used to + base verb"]}, "review/grammar/used-to-+-verb.md"),
            ({"item_type": "error", "correct_form": "I agree.", "wrong_form": "I am agree.", "reason": "agree is a verb", "avoidance": "Use agree directly."}, "review/errors/2026-08-08_I-agree..md"),
            ({"item_type": "pronunciation", "target_text": "record", "pronunciation_kind": "accent", "issue_tags": ["noun-verb stress"]}, "review/pronunciation/accent/record.md"),
            ({"item_type": "pronunciation", "target_text": "ship / sheep", "pronunciation_kind": "phoneme", "issue_tags": ["ɪ-iː"]}, "review/pronunciation/phoneme/ship-sheep.md"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            for item, expected_path in cases:
                report = workflows.review_materials(vault_root=root, mode="apply", item=item, extraction_date="2026-08-08")
                self.assertTrue(report.accepted, report.to_dict())
                self.assertTrue((root / expected_path).is_file(), expected_path)

    def test_existing_card_update_requires_confirmation_and_preserves_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/new-source.md", "# New source\n")
            card = root / "review/focus/vocab/known.md"
            write(card, "---\nitem_type: vocab\nstatus: active\ndone_today: true\nreview_stage: day30\nnext_review: 2026-09-01\nheadword: known\nipa: /noʊn/\nmeaning_zh: 已知的\nsource_notes: []\nseen_count: 1\nerror_count: 0\n---\n\n## Manual\nKeep me.\n")
            item = {"item_type": "vocab", "headword": "known", "ipa": "/noʊn/", "meaning_zh": "已知的", "source_note": "sources/new-source"}
            blocked = workflows.review_materials(vault_root=root, mode="apply", item=item, extraction_date="2026-08-08")
            self.assertFalse(blocked.accepted)
            applied = workflows.review_materials(vault_root=root, mode="apply", item=item, extraction_date="2026-08-08", existing_update_confirmed=True)
            body = card.read_text(encoding="utf-8")
        self.assertTrue(applied.accepted, applied.to_dict())
        self.assertIn("## Manual\nKeep me.", body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("[[sources/new-source|new-source]]", body)

    def test_mastered_vocab_reactivation_preserves_manual_english_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/new-source.md", "# Source\n")
            card = root / "review/focus/vocab/known.md"
            write(
                card,
                "---\ntrack: class_review\nitem_type: vocab\nstatus: mastered\ndone_today: false\n"
                "review_stage: mastered\nnext_review:\nlast_reviewed: 2026-08-01\nheadword: known\n"
                "ipa: /noʊn/\nmeaning_zh: 已知的\nsource_notes: []\n---\n\n## Manual\nKeep this nuance.\n",
            )

            report = workflows.review_materials(
                vault_root=root,
                item={"item_type": "vocab", "headword": "known", "source_note": "sources/new-source"},
                extraction_date="2026-08-08",
                existing_update_confirmed=True,
                mode="apply",
            )
            body = card.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertIn("review_status: queued", body)
        self.assertIn("review_stage: day0", body)
        self.assertIn("next_review: 2026-08-08", body)
        self.assertIn("[[sources/new-source|new-source]]", body)
        self.assertIn("Keep this nuance.", body)

    def test_image_vocab_requires_structured_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            write(root / "sources/image-source.md", "# Image words\n\n## Vocabulary\n\n![[attachments/lesson.png]]\n")
            write_image(root / "attachments/lesson.png")
            base_item = {
                "item_type": "vocab",
                "headword": "signboard",
                "ipa": "/ˈsaɪn.bɔːrd/",
                "meaning_zh": "招牌",
                "image_backed": True,
                "source_note": "sources/image-source",
            }
            legacy = workflows.review_materials(vault_root=root, item={**base_item, "image_readable": True})
            accepted = workflows.review_materials(
                vault_root=root,
                item={
                    **base_item,
                    "image_evidence": {
                        "attachment": "attachments/lesson.png",
                        "inspection_method": "visual",
                        "readability": "clear",
                        "observed_text": "SIGNBOARD",
                        "observed_form": "SIGNBOARD",
                        "normalized_headword": "signboard",
                    },
                },
                extraction_date="2026-08-08",
                mode="apply",
            )

        self.assertFalse(legacy.accepted)
        self.assertEqual("missing_image_inspection_evidence", legacy.errors[0].code)
        self.assertTrue(accepted.accepted, accepted.to_dict())
        self.assertEqual(["review/focus/vocab/signboard.md"], accepted.changed_files)
        self.assertIn("attachments/lesson.png", accepted.read_files)

    def test_daily_checklist_is_confirmed_and_does_not_change_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            daily = root / "daily/2026-08-08.md"
            card = root / "review/focus/vocab/known.md"
            write(daily, "# English study\n\nManual notes.\n")
            write(card, review_card(headword="known", meaning_zh="已知的", review_stage="day3"))
            card_before = card.read_text(encoding="utf-8")
            payload = {
                "path": "daily/2026-08-08.md",
                "completed": ["复习英语词汇卡 3 张"],
                "blockers": ["word stress 仍不稳定"],
                "reflection": "明天先做发音对比。",
            }

            preview = workflows.review_materials(vault_root=root, daily_checklist=payload, mode="preview")
            blocked = workflows.review_materials(vault_root=root, daily_checklist=payload, mode="apply")
            applied = workflows.review_materials(
                vault_root=root,
                daily_checklist=payload,
                existing_update_confirmed=True,
                mode="apply",
            )
            daily_after = daily.read_text(encoding="utf-8")
            card_after = card.read_text(encoding="utf-8")

        self.assertTrue(preview.accepted, preview.to_dict())
        self.assertEqual("daily_checklist_confirmation_required", blocked.errors[0].code)
        self.assertTrue(applied.accepted, applied.to_dict())
        self.assertIn("Manual notes.", daily_after)
        self.assertIn("复习英语词汇卡 3 张", daily_after)
        self.assertEqual(card_before, card_after)


# ---------------------------------------------------------------------------
# Review Rollover Contract Tests (15 Migration Matrix tests)
# ---------------------------------------------------------------------------


class TestEnglishReviewRolloverContract(unittest.TestCase):

    # US-1: Internal preview before write ----------------------------------

    def test_review_rollover_previews_due_target_card_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/preview-only.md"
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21")
            before = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual("preview", envelope["mode"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual(1, len(envelope["planned_writes"]))
        self.assertEqual("review/focus/vocab/preview-only.md", envelope["planned_writes"][0]["path"])
        self.assertEqual("preview_review_rollover", envelope["planned_writes"][0]["action"])
        # file must be unchanged
        self.assertIn("review_stage: day1", before)
        self.assertIn("done_today: true", before)

    def test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/second-preview.md"
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            apply = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            self.assertTrue(apply.accepted, apply.to_dict())

            second = workflows.review_rollover(vault_root=root, run_date="2026-06-21")
            second_env = second.to_dict()

        self.assertTrue(second.accepted, second_env)
        self.assertEqual([], second_env["planned_writes"])

    # US-2, US-4: Memory-curve advancement ---------------------------------

    def test_review_rollover_apply_advances_due_target_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/advance.md"
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/advance.md"], envelope["changed_files"])
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-24", body)
        self.assertIn("done_today: false", body)
        self.assertIn("last_reviewed: 2026-06-21", body)

    def test_review_rollover_applies_every_memory_curve_transition_from_run_date(self) -> None:
        transitions = [
            ("day0", "2026-06-21", "day1", "2026-06-22"),
            ("day1", "2026-06-21", "day3", "2026-06-24"),
            ("day3", "2026-06-21", "day7", "2026-06-28"),
            ("day7", "2026-06-21", "day14", "2026-07-05"),
            ("day14", "2026-06-21", "day30", "2026-07-21"),
            ("day30", "2026-06-21", "day90", "2026-09-19"),
            ("day90", "2026-06-21", "day180", "2026-12-18"),
            ("day180", "2026-06-21", "mastered", ""),
        ]
        for from_stage, run_date, to_stage, to_next_review in transitions:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                create_target_context(root)
                card_path = root / f"review/focus/vocab/{from_stage}.md"
                write(card_path, review_card(review_stage=from_stage, next_review=run_date))

                report = workflows.review_rollover(vault_root=root, run_date=run_date, mode="apply")
                body = card_path.read_text(encoding="utf-8")

            self.assertTrue(report.accepted, f"Failed at {from_stage}: {report.to_dict()}")
            self.assertIn(f"review_stage: {to_stage}", body)
            if to_next_review:
                self.assertIn(f"next_review: {to_next_review}", body)
            if to_stage == "mastered":
                self.assertIn("review_status: mastered", body)

    def test_apply_updates_done_today_review_stage_next_review_and_mastered_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/mastered-status.md"
            write(card_path, review_card(review_stage="day180", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertIn("review_stage: mastered", body)
        self.assertIn("review_status: mastered", body)
        self.assertIn("done_today: false", body)
        self.assertIn("last_reviewed: 2026-06-21", body)

    # US-3: Overdue rescheduling -------------------------------------------

    def test_review_rollover_reschedules_overdue_card_without_advancing_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/overdue.md"
            # day1 allows 1 day delay; run_date 2026-07-01 vs next_review 2026-06-21
            # overdue = 10 days > 1 day allowed delay
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-07-01", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertIn("review_stage: day1", body)  # stage unchanged
        self.assertNotIn("review_stage: day3", body)
        self.assertIn("done_today: false", body)
        self.assertIn("last_reviewed: 2026-07-01", body)
        # next_review = run_date + allowed_delay = 2026-07-01 + 1 = 2026-07-02
        self.assertIn("next_review: 2026-07-02", body)

    def test_review_rollover_advances_when_overdue_days_equal_allowed_delay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/boundary.md"
            # day1 allows 1 day delay; run_date 2026-06-22 vs next_review 2026-06-21
            # overdue = 1 day == allowed delay → advances
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-22", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-25", body)

    # US-4, US-5: In-place mastery tests ------------------------------------

    def test_review_rollover_mastery_does_not_rewrite_existing_base_vocab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            write(
                focus_path,
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day180
next_review: 2026-06-21
last_reviewed:
headword: ubiquitous
ipa: /juːˈbɪk.wɪ.təs/
meaning_zh: 无处不在的
english_definition: present, appearing, or found everywhere
collocations: ubiquitous computing
source_notes: [[focus-source]]
---

## Focus
Review card body.
""",
            )
            write(
                base_path,
                """---
track: base_vocab
item_type: vocab
status: active
headword: ubiquitous
ipa: /juːˈbɪk.wɪ.təs/
meaning_zh: 旧的无处不在释义
source_notes: [[base-source]]
seen_count: 2
---

## Manual Notes
这段英文释义必须保留。
""",
            )

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            focus_body = focus_path.read_text(encoding="utf-8")
            base_body = base_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/focus.md"], report.to_dict()["changed_files"])
        self.assertIn("review_status: mastered", focus_body)
        self.assertNotIn("status: active", focus_body)
        self.assertIn("meaning_zh: 旧的无处不在释义", base_body)
        self.assertNotIn("english_definition:", base_body)
        self.assertIn("source_notes: [[base-source]]", base_body)
        self.assertIn("seen_count: 2", base_body)
        self.assertIn("这段英文释义必须保留。", base_body)

    def test_review_rollover_does_not_create_base_vocab_after_day180(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/new-base.md"
            base_path = root / "review/base/vocab/ubiquitous.md"
            write(
                focus_path,
                """---
track: class_review
item_type: vocab
status: active
done_today: true
review_stage: day180
next_review: 2026-06-21
last_reviewed:
headword: ubiquitous
ipa: /juːˈbɪk.wɪ.təs/
meaning_zh: 无处不在的
english_definition: present, appearing, or found everywhere
source_notes: [[focus-source]]
---

## Focus
Review card body.
""",
            )

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            focus_body = focus_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/new-base.md"], report.to_dict()["changed_files"])
        self.assertIn("review_status: mastered", focus_body)
        self.assertFalse(base_path.exists())

    # US-5, US-6, US-7: Non-focus scope safety ----------------------------

    def test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            daily_path = root / "daily/2026-06-21.md"
            write(focus_path, review_card(review_stage="day1", next_review="2026-06-21"))
            write(base_path, review_card(review_status="queued", done_today="true", review_stage="day1", next_review="2026-06-21"))
            write(daily_path, "# Daily\n\n- manual note\n")
            before_base = base_path.read_text(encoding="utf-8")
            before_daily = daily_path.read_text(encoding="utf-8")

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            after_base = base_path.read_text(encoding="utf-8")
            after_daily = daily_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(["review/focus/vocab/focus.md"], report.to_dict()["changed_files"])
        self.assertNotIn("review/base/vocab/base.md", report.to_dict()["read_files"])
        self.assertNotIn("daily/2026-06-21.md", report.to_dict()["read_files"])
        self.assertEqual(before_base, after_base)
        self.assertEqual(before_daily, after_daily)

    # US-8: Missing daily note resilience ----------------------------------

    def test_review_rollover_completes_when_daily_note_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/no-daily.md"
            write(card_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            body = card_path.read_text(encoding="utf-8")

        envelope = report.to_dict()
        self.assertTrue(report.accepted, envelope)
        self.assertEqual(["review/focus/vocab/no-daily.md"], envelope["changed_files"])
        self.assertEqual([], [w for w in envelope.get("planned_writes", []) if w.get("path", "").startswith("daily/")])
        self.assertIn("done_today: false", body)
        self.assertIn("review_stage: day3", body)
        self.assertIn("next_review: 2026-06-24", body)
        self.assertIn("last_reviewed: 2026-06-21", body)

    # US-9, US-10: Dirty data isolation ------------------------------------

    def test_review_rollover_blocks_unknown_stage_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/bad-stage.md"
            write(card_path, review_card(review_stage="day999", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            before = card_path.read_text(encoding="utf-8")

        self.assertFalse(report.accepted)
        self.assertEqual("unknown_review_stage", report.to_dict()["errors"][0]["code"])
        # file must be unchanged
        self.assertIn("review_stage: day999", before)

    def test_review_rollover_blocks_invalid_next_review_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            card_path = root / "review/focus/vocab/bad-date.md"
            write(card_path, review_card(review_stage="day1", next_review="not-a-date"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            before = card_path.read_text(encoding="utf-8")

        self.assertFalse(report.accepted)
        self.assertEqual("invalid_next_review", report.to_dict()["errors"][0]["code"])
        self.assertIn("next_review: not-a-date", before)

    def test_validation_failure_blocks_planning_before_any_write_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            bad_path = root / "review/focus/vocab/bad-stage.md"
            good_path = root / "review/focus/vocab/good.md"
            write(bad_path, review_card(review_stage="day999", next_review="2026-06-21"))
            write(good_path, review_card(review_stage="day1", next_review="2026-06-21"))

            report = workflows.review_rollover(vault_root=root, run_date="2026-06-21", mode="apply")
            good_before = good_path.read_text(encoding="utf-8")

        self.assertFalse(report.accepted)
        # invalid card blocked everything — good card must be untouched
        self.assertIn("review_stage: day1", good_before)
        self.assertEqual([], report.to_dict()["changed_files"])

    # Dashboard contract check ---------------------------------------------

    def test_total_training_dashboard_exists_and_sorts_stably(self) -> None:
        dashboard_path = PACK_ROOT / "views" / "total-training.base"
        self.assertTrue(dashboard_path.is_file())

        content = dashboard_path.read_text(encoding="utf-8")

        # Must end with file.name in sort
        self.assertIn("file.name", content)

        # Must have the required formula fields
        self.assertIn("core_text", content)
        self.assertIn("support_text", content)
        self.assertIn("due_flag", content)
        self.assertIn("next_day_flag", content)

        # Must have order with file.name as first column
        self.assertIn("order:", content)

        # Must have both views
        for view_name in (
            "今日总训练",
            "重点复习高风险",
            "生活口语待练",
            "听力待精听",
            "发音待录音",
            "单词重音待练",
            "音素待练",
            "最近新增",
            "重复出现 / 反复出错",
        ):
            self.assertIn(view_name, content)

        # Must use if() not ifs()
        self.assertNotIn("ifs(", content)
        self.assertNotIn("jp_text", content)
        self.assertNotIn("accent_display", content)

    def test_total_training_dashboard_surfaces_english_type_specific_review_cues(self) -> None:
        dashboard_path = PACK_ROOT / "views" / "total-training.base"
        content = dashboard_path.read_text(encoding="utf-8")

        expected_core_contracts = (
            'item_type == "vocab", if(ipa, ipa, if(english_definition, english_definition, if(headword, headword, if(meaning_zh, meaning_zh, file.name))))',
            'item_type == "grammar", if(meaning_zh, meaning_zh, if(pattern, pattern, file.name))',
            'item_type == "error", if(correct_form, correct_form, file.name)',
            'item_type == "pronunciation", if(target_text, target_text, file.name)',
        )
        expected_support_contracts = (
            'item_type == "vocab", if(collocations, collocations, if(meaning_zh, meaning_zh, ""))',
            'item_type == "grammar", if(formation, formation, "")',
            'item_type == "error", if(wrong_form, wrong_form, if(reason, reason, ""))',
            'item_type == "pronunciation", if(issue_tags, issue_tags, "")',
        )

        for contract in expected_core_contracts:
            self.assertIn(contract, content)
        for contract in expected_support_contracts:
            self.assertIn(contract, content)

    def test_material_library_surfaces_backlog_and_mastered_without_editable_status_column(self) -> None:
        content = (PACK_ROOT / "views" / "material-library.base").read_text(encoding="utf-8")

        self.assertNotIn('track == "base_vocab"', content)
        for name in ("待加入复习", "听力素材", "生活口语与语块", "词汇语法素材", "已掌握"):
            self.assertIn(f"name: {name}", content)
        self.assertIn('review_status == "backlog"', content)
        self.assertIn('review_status == "mastered"', content)
        self.assertNotIn("      - review_status\n", content)


if __name__ == "__main__":
    unittest.main()
