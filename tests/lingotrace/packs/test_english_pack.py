"""English language pack conformance tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PHASE0_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest
from lingotrace.packs.english import workflows


REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "english"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
FIELDS_PATH = PACK_ROOT / "fields.json"
PATHS_PATH = PACK_ROOT / "paths.json"

EXPECTED_PATH_ROLES = {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
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

EXPECTED_LANGUAGE_FIELDS = {"ipa", "word_stress", "part_of_speech", "collocations", "english_definition"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
                    "source_notes",
                    "review_materials",
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


def review_card(
    *,
    track: str = "class_review",
    item_type: str = "vocab",
    status: str = "active",
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
        f"status: {status}",
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
# Manifest & static tests (Phase 2.0 baseline)
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
        """2. All declared capabilities use reviewed IDs from PHASE0_CAPABILITY_IDS."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        declared_ids = set(result.manifest.capabilities) | set(result.manifest.unsupported_capabilities)
        self.assertTrue(declared_ids.issubset(PHASE0_CAPABILITY_IDS))
        self.assertEqual(PHASE0_CAPABILITY_IDS, declared_ids)

    def test_unsupported_capabilities_have_fallback_none(self):
        """3. Unsupported capabilities declare fallback: 'none' and have failure policies."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        self.assertIn("listening_notes", result.manifest.unsupported_capabilities)
        self.assertIn("speaking_cards", result.manifest.unsupported_capabilities)

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

    def test_listening_and_speaking_workflows_return_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)

            listening = workflows.listening_notes(vault_root=root)
            speaking = workflows.speaking_cards(vault_root=root)

        for report in (listening, speaking):
            self.assertFalse(report.accepted)
            self.assertEqual("unsupported_capability", report.to_dict()["errors"][0]["code"])

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
                self.assertIn("status: mastered", body)

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
        self.assertIn("status: mastered", body)
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

    # US-4, US-5: Mastery Sink tests ---------------------------------------

    def test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body(self) -> None:
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
        self.assertEqual(
            ["review/base/vocab/base.md", "review/focus/vocab/focus.md"],
            sorted(report.to_dict()["changed_files"]),
        )
        self.assertIn("status: mastered", focus_body)
        self.assertIn("status: promoted", base_body)
        self.assertIn("meaning_zh: 无处不在的", base_body)
        self.assertIn("english_definition: present, appearing, or found everywhere", base_body)
        self.assertIn("collocations: ubiquitous computing", base_body)
        self.assertIn("source_notes: [[base-source]], [[focus-source]]", base_body)
        self.assertIn("seen_count: 2", base_body)
        self.assertIn("这段英文释义必须保留。", base_body)

    def test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match(self) -> None:
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
            base_body = base_path.read_text(encoding="utf-8")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(
            ["review/base/vocab/ubiquitous.md", "review/focus/vocab/new-base.md"],
            sorted(report.to_dict()["changed_files"]),
        )
        self.assertIn("status: mastered", focus_body)
        self.assertIn("track: base_vocab", base_body)
        self.assertIn("status: promoted", base_body)
        self.assertIn("headword: ubiquitous", base_body)
        self.assertIn("ipa: /juːˈbɪk.wɪ.təs/", base_body)
        self.assertIn("meaning_zh: 无处不在的", base_body)
        self.assertIn("english_definition: present, appearing, or found everywhere", base_body)
        self.assertIn("source_notes: [[focus-source]]", base_body)

    # US-5, US-6, US-7: Non-focus scope safety ----------------------------

    def test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_target_context(root)
            focus_path = root / "review/focus/vocab/focus.md"
            base_path = root / "review/base/vocab/base.md"
            daily_path = root / "daily/2026-06-21.md"
            write(focus_path, review_card(review_stage="day1", next_review="2026-06-21"))
            write(base_path, review_card(status="active", done_today="true", review_stage="day1", next_review="2026-06-21"))
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
        self.assertEqual("invalid_review_stage", report.to_dict()["errors"][0]["code"])
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
        self.assertIn("今日总训练", content)
        self.assertIn("最近新增", content)

        # Must use if() not ifs()
        self.assertNotIn("ifs(", content)


if __name__ == "__main__":
    unittest.main()
