from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from lingotrace.core.mutations import FileMutation, run_file_mutations
from lingotrace.core.reports import CommandReport, Finding
from lingotrace.packs.japanese.validators import (
    validate_existing_review_material,
    validate_review_materials,
    validate_review_rollover,
)


PACK_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PACK_ROOT / "manifest.json"
REVIEW_MATERIAL_ROLES = (
    "focus_vocab_root",
    "base_vocab_root",
    "grammar_root",
    "error_root",
    "pronunciation_accent_root",
    "pronunciation_phoneme_root",
)
ROLLOVER_ROLES = (
    "focus_vocab_root",
    "grammar_root",
    "error_root",
    "speaking_card_root",
    "listening_root",
    "pronunciation_accent_root",
    "pronunciation_phoneme_root",
)
STAGE_ADVANCEMENT = {
    "day0": ("day1", 1),
    "day1": ("day3", 3),
    "day3": ("day7", 7),
    "day7": ("day14", 14),
    "day14": ("day30", 30),
    "day30": ("day90", 90),
    "day90": ("day180", 180),
    "day180": ("mastered", 0),
}
STAGE_DAYS = {
    "day0": 0,
    "day1": 1,
    "day3": 3,
    "day7": 7,
    "day14": 14,
    "day30": 30,
    "day90": 90,
    "day180": 180,
}
MAX_GENERATED_FILENAME_BYTES = 180
MAX_REVIEW_CARD_FILENAME_BYTES = 200
MAX_DAILY_CHECKLIST_ITEMS = 30
MAX_DAILY_CHECKLIST_TEXT_LENGTH = 300
DAILY_CHECKLIST_START = "<!-- lingotrace:daily-checklist:start -->"
DAILY_CHECKLIST_END = "<!-- lingotrace:daily-checklist:end -->"
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}

SOURCE_LINK_ROLES = ("source_notes_root", "daily_notes_root")
RELATED_LINK_ROLES = {
    "vocab": ("focus_vocab_root", "base_vocab_root"),
    "grammar": ("grammar_root",),
    "error": REVIEW_MATERIAL_ROLES,
    "pronunciation": ("pronunciation_accent_root", "pronunciation_phoneme_root"),
}
LIST_FIELDS = {
    "source_notes",
    "tags",
    "formation",
    "collocations",
    "confusable_with",
    "contrast_with",
    "related_items",
    "kanji_diff_pairs",
    "issue_tags",
    "usage_scenes",
}
DATE_FIELDS = {"first_seen", "last_seen", "next_review", "last_reviewed"}


class ReviewMaterialPlan:
    __slots__ = ("mutation", "warnings", "unresolved_related_items", "read_files")

    def __init__(
        self,
        mutation: FileMutation,
        warnings: tuple[Finding, ...] = (),
        unresolved_related_items: tuple[str, ...] = (),
        read_files: tuple[str, ...] = (),
    ) -> None:
        self.mutation = mutation
        self.warnings = warnings
        self.unresolved_related_items = unresolved_related_items
        self.read_files = read_files


class LinkResolution:
    __slots__ = ("raw", "link", "finding", "read_files")

    def __init__(
        self,
        raw: str,
        link: str | None = None,
        finding: Finding | None = None,
        read_files: tuple[str, ...] = (),
    ) -> None:
        self.raw = raw
        self.link = link
        self.finding = finding
        self.read_files = read_files


def listening_notes(
    vault_root: str | Path | None = None,
    *,
    input_artifact: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("listening_notes")
    if input_artifact is None:
        return _workflow_error("listening_notes-workflow", mode, "missing_input_artifact", "input_artifact is required.")
    root = Path(vault_root)
    paths = _path_roles(root)
    listening_root = paths.get("listening_root")
    if not listening_root:
        return _workflow_error(
            "listening_notes-workflow",
            mode,
            "missing_path_role",
            "Target Vault does not configure listening_root.",
            "listening_root",
        )
    mutations = _listening_artifact_mutations(input_artifact)
    if isinstance(mutations, Finding):
        return _workflow_error("listening_notes-workflow", mode, mutations.code, mutations.message, mutations.path)
    invalid_path = next(
        (mutation.path for mutation in mutations if not _path_is_within_role(mutation.path, listening_root)),
        None,
    )
    if invalid_path is not None:
        return _workflow_error(
            "listening_notes-workflow",
            mode,
            "listening_artifact_outside_role",
            "Every listening artifact must stay under the configured listening_root.",
            invalid_path,
        )
    note_path = input_artifact.get("note_path")
    if mode == "apply" and isinstance(note_path, str) and note_path and (root / note_path).exists():
        if input_artifact.get("overwrite_confirmed") is not True:
            return _workflow_error(
                "listening_notes-workflow",
                mode,
                "existing_listening_note_confirmation_required",
                "Applying changes to an existing listening note requires overwrite_confirmed: true.",
                note_path,
            )
    return _run_mutations(root, "listening_notes", mutations, mode)


def source_notes(
    vault_root: str | Path | None = None,
    *,
    source_artifact: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("source_notes")
    if source_artifact is None:
        return _workflow_error("source_notes-workflow", mode, "missing_source_artifact", "source_artifact is required.")
    mutation = _artifact_mutation(source_artifact, action="write_source_note", reason="prepared source artifact")
    if isinstance(mutation, Finding):
        return _workflow_error("source_notes-workflow", mode, mutation.code, mutation.message, mutation.path)
    return _run_mutations(vault_root, "source_notes", [mutation], mode)


def review_materials(
    vault_root: str | Path | None = None,
    *,
    card: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
    daily_checklist: dict[str, Any] | None = None,
    extraction_date: str | None = None,
    existing_update_confirmed: bool = False,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_materials")
    root = Path(vault_root)
    errors, read_files = _target_context_errors(root, "review_materials")
    if errors:
        return _workflow_report("review_materials-workflow", mode, errors=errors, read_files=read_files)

    provided_inputs = sum(value is not None for value in (card, item, daily_checklist))
    if provided_inputs > 1:
        return _workflow_error(
            "review_materials-workflow",
            mode,
            "ambiguous_review_material_input",
            "Provide exactly one of card, item, or daily_checklist.",
        )

    if card is not None:
        paths = _path_roles(root)
        read_files.append(".lingotrace/paths.json")
        plan = _review_card_plan(root, paths, card)
        if isinstance(plan, Finding):
            return _workflow_report("review_materials-workflow", mode, errors=[plan], read_files=read_files)
        if mode == "apply" and (root / plan.mutation.path).exists() and not existing_update_confirmed:
            return _workflow_report(
                "review_materials-workflow",
                mode,
                errors=[
                    Finding(
                        code="existing_review_material_confirmation_required",
                        message="Applying changes to an existing review card requires existing_update_confirmed: true.",
                        path=plan.mutation.path,
                    )
                ],
                read_files=[*read_files, *plan.read_files],
                blocked_files=[plan.mutation.path],
            )
        return _run_review_material_plan(root, plan, mode, read_files)
    if daily_checklist is not None:
        paths = _path_roles(root)
        read_files.append(".lingotrace/paths.json")
        plan = _daily_checklist_plan(root, paths, daily_checklist)
        if isinstance(plan, Finding):
            return _workflow_report("review_materials-workflow", mode, errors=[plan], read_files=read_files)
        if mode == "apply" and not existing_update_confirmed:
            return _workflow_report(
                "review_materials-workflow",
                mode,
                errors=[
                    Finding(
                        code="daily_checklist_confirmation_required",
                        message="Updating an existing daily study note requires existing_update_confirmed: true.",
                        path=plan.mutation.path,
                    )
                ],
                read_files=[*read_files, *plan.read_files],
                blocked_files=[plan.mutation.path],
            )
        return _run_review_material_plan(root, plan, mode, read_files)
    if item is not None:
        paths = _path_roles(root)
        read_files.append(".lingotrace/paths.json")
        plan = _review_item_plan(root, paths, item, extraction_date=extraction_date)
        if isinstance(plan, Finding):
            return _workflow_report("review_materials-workflow", mode, errors=[plan], read_files=read_files)
        if mode == "apply" and (root / plan.mutation.path).exists() and not existing_update_confirmed:
            return _workflow_report(
                "review_materials-workflow",
                mode,
                errors=[
                    Finding(
                        code="existing_review_material_confirmation_required",
                        message="Applying changes to an existing review card requires existing_update_confirmed: true.",
                        path=plan.mutation.path,
                    )
                ],
                read_files=[*read_files, *plan.read_files],
                blocked_files=[plan.mutation.path],
            )
        return _run_review_material_plan(root, plan, mode, read_files)
    if mode == "apply":
        return _workflow_error(
            "review_materials-workflow",
            mode,
            "missing_review_material_input",
            "review_materials apply mode requires a card, item, or daily_checklist payload.",
        )

    paths = _path_roles(root)
    read_files.append(".lingotrace/paths.json")
    for card_path, fields in _cards_for_roles(root, paths, REVIEW_MATERIAL_ROLES):
        read_files.append(card_path.relative_to(root).as_posix())
        validation = validate_existing_review_material(fields)
        if not validation.accepted:
            continue
        return _preview_report(
            "review_materials-workflow",
            read_files=read_files,
            planned_writes=[
                {
                    "path": card_path.relative_to(root).as_posix(),
                    "action": "preview_review_material",
                    "reason": "target Vault has readable Japanese review material",
                    "item_type": str(fields.get("item_type", "")),
                    "review_stage": str(fields.get("review_stage", "")),
                }
            ],
        )

    return _preview_report(
        "review_materials-workflow",
        errors=[
            Finding(
                code="missing_review_material",
                message="Target Vault has no readable Japanese review material for preview.",
            )
        ],
        read_files=read_files,
        )


def speaking_cards(
    vault_root: str | Path | None = None,
    *,
    candidate: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("speaking_cards")
    if candidate is None:
        return _workflow_error("speaking_cards-workflow", mode, "missing_speaking_candidate", "candidate is required.")
    if candidate.get("reviewed") is not True:
        return _workflow_error(
            "speaking_cards-workflow",
            mode,
            "unreviewed_speaking_candidate",
            "Speaking cards require an explicitly reviewed candidate before write.",
        )
    mutation = _artifact_mutation(candidate, action="write_speaking_card", reason="reviewed speaking candidate")
    if isinstance(mutation, Finding):
        return _workflow_error("speaking_cards-workflow", mode, mutation.code, mutation.message, mutation.path)
    return _run_mutations(vault_root, "speaking_cards", [mutation], mode)


def review_rollover(
    vault_root: str | Path | None = None,
    *,
    run_date: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_rollover")
    root = Path(vault_root)
    errors, read_files = _target_context_errors(root, "review_rollover")
    if errors:
        return _workflow_report("review_rollover-workflow", mode, errors=errors, read_files=read_files)

    try:
        rollover_date = dt.date.fromisoformat(run_date) if run_date else dt.date.today()
    except ValueError:
        return _preview_report(
            "review_rollover-workflow",
            errors=[
                Finding(
                    code="invalid_run_date",
                    message="run_date must use YYYY-MM-DD format.",
                    path="run_date",
                )
            ],
            read_files=read_files,
        )

    paths = _path_roles(root)
    read_files.append(".lingotrace/paths.json")
    planned_writes: list[dict[str, Any]] = []
    mutations: list[FileMutation] = []
    for card_path, fields in _cards_for_roles(root, paths, ROLLOVER_ROLES):
        read_files.append(card_path.relative_to(root).as_posix())
        if fields.get("status") != "active" or not _truthy(fields.get("done_today")):
            continue
        validation = validate_review_rollover(fields)
        if not validation.accepted:
            errors.extend(validation.errors)
            continue
        review_stage = str(fields.get("review_stage", ""))
        if review_stage not in STAGE_ADVANCEMENT:
            errors.append(
                Finding(
                    code="unknown_review_stage",
                    message="Review rollover preview cannot advance an unknown stage.",
                    path=card_path.relative_to(root).as_posix(),
                )
            )
            continue
        next_review_raw = str(fields.get("next_review", ""))
        try:
            original_next_review = dt.date.fromisoformat(next_review_raw)
        except ValueError:
            errors.append(
                Finding(
                    code="invalid_next_review",
                    message="Review rollover requires next_review to use YYYY-MM-DD format.",
                    path=card_path.relative_to(root).as_posix(),
                )
            )
            continue
        allowed_delay = max(1, STAGE_DAYS[review_stage])
        overdue_days = (rollover_date - original_next_review).days
        delay_rescheduled = overdue_days > allowed_delay
        if delay_rescheduled:
            next_stage = review_stage
            next_review = (rollover_date + dt.timedelta(days=allowed_delay)).isoformat()
        else:
            next_stage, interval_days = STAGE_ADVANCEMENT[review_stage]
            next_review = "" if next_stage == "mastered" else (rollover_date + dt.timedelta(days=interval_days)).isoformat()
        updates = {
            "done_today": False,
            "review_stage": next_stage,
            "next_review": next_review,
            "last_reviewed": rollover_date.isoformat(),
        }
        if next_stage == "mastered":
            updates["status"] = "mastered"
        planned_writes.append(
            {
                "path": card_path.relative_to(root).as_posix(),
                "action": "preview_review_rollover",
                "reason": "done_today active card would advance during target Vault rollover",
                "from_review_stage": review_stage,
                "to_review_stage": next_stage,
                "from_next_review": next_review_raw,
                "to_next_review": next_review,
                "last_reviewed": rollover_date.isoformat(),
                "done_today": False,
            }
            | ({"delay_rescheduled": True} if delay_rescheduled else {})
        )
        mutations.append(
            FileMutation(
                path=card_path.relative_to(root).as_posix(),
                action="apply_review_rollover",
                reason="done_today active card advances during target Vault rollover",
                content=_replace_frontmatter_fields(
                    card_path.read_text(encoding="utf-8"),
                    updates,
                ),
            )
        )
        if next_stage == "mastered" and fields.get("item_type") == "vocab":
            base_mutation = _base_vocab_sink_mutation(root, paths, card_path, fields)
            if isinstance(base_mutation, Finding):
                errors.append(base_mutation)
                continue
            if base_mutation is not None:
                planned_writes.append(
                    {
                        "path": base_mutation.path,
                        "action": "preview_base_vocab_sink",
                        "reason": "day180 focus vocabulary would be promoted into the base lexicon",
                        "from_focus_path": card_path.relative_to(root).as_posix(),
                        "status": "promoted",
                    }
                )
                mutations.append(base_mutation)

    if mode == "apply":
        if errors:
            return _workflow_report("review_rollover-workflow", mode, errors=errors, read_files=read_files)
        return _run_mutations(root, "review_rollover", mutations, mode)

    return _preview_report(
        "review_rollover-workflow",
        errors=errors,
        read_files=read_files,
        planned_writes=planned_writes,
    )


def _workflow_report(
    command: str,
    mode: str,
    *,
    errors: list[Finding] | None = None,
    read_files: list[str] | None = None,
    planned_writes: list[dict[str, Any]] | None = None,
    changed_files: list[str] | None = None,
    blocked_files: list[str] | None = None,
) -> CommandReport:
    errors = errors or []
    return CommandReport(
        command=command,
        mode=mode,
        exit_code=1 if errors else 0,
        errors=errors,
        read_files=read_files or [],
        planned_writes=planned_writes or [],
        changed_files=changed_files or [],
        blocked_files=blocked_files or [],
    )


def _preview_report(
    command: str,
    *,
    errors: list[Finding] | None = None,
    read_files: list[str] | None = None,
    planned_writes: list[dict[str, Any]] | None = None,
) -> CommandReport:
    errors = errors or []
    return CommandReport(
        command=command,
        mode="preview",
        exit_code=1 if errors else 0,
        errors=errors,
        read_files=read_files or [],
        planned_writes=planned_writes or [],
    )


def _missing_vault_root(capability_id: str) -> CommandReport:
    return _workflow_error(
        f"{capability_id}-workflow",
        "preview",
        "missing_vault_root",
        "vault_root is required before running a Japanese pack workflow.",
    )


def _workflow_error(command: str, mode: str, code: str, message: str, path: str | None = None) -> CommandReport:
    return _workflow_report(command, mode, errors=[Finding(code=code, message=message, path=path)])


def _run_mutations(
    vault_root: str | Path,
    capability_id: str,
    mutations: list[FileMutation],
    mode: str,
) -> CommandReport:
    report = run_file_mutations(
        vault_root=vault_root,
        manifest_path=MANIFEST_PATH,
        capability_id=capability_id,
        mutations=mutations,
        mode=mode,
    )
    report.command = f"{capability_id}-workflow"
    return report


def _run_review_material_plan(
    root: Path,
    plan: ReviewMaterialPlan,
    mode: str,
    read_files: list[str],
) -> CommandReport:
    report = _run_mutations(root, "review_materials", [plan.mutation], mode)
    report.read_files = list(dict.fromkeys([*read_files, *plan.read_files, *report.read_files]))
    report.warnings = list(plan.warnings)
    if plan.unresolved_related_items:
        report.artifacts["unresolved_related_items"] = json.dumps(
            list(plan.unresolved_related_items),
            ensure_ascii=False,
        )
        if report.planned_writes:
            report.planned_writes[0]["unresolved_related_items"] = list(plan.unresolved_related_items)
    return report


def _artifact_mutation(payload: dict[str, Any], *, action: str, reason: str) -> FileMutation | Finding:
    path = payload.get("path")
    body = payload.get("body")
    title = payload.get("title", "")
    if not isinstance(path, str) or not path.endswith(".md"):
        return Finding(code="invalid_artifact_path", message="Artifact path must be a Vault-relative Markdown path.", path="path")
    if not isinstance(body, str) or not body.strip():
        return Finding(code="invalid_artifact_body", message="Artifact body must be a non-empty string.", path=path)
    content = body if body.startswith("---\n") else f"---\ntitle: {title}\nstatus: active\n---\n\n{body}\n"
    return FileMutation(path=path, content=content, action=action, reason=reason)


def _listening_artifact_mutations(payload: dict[str, Any]) -> list[FileMutation] | Finding:
    files = payload.get("files")
    if files is None:
        mutation = _artifact_mutation(payload, action="write_listening_note", reason="prepared listening artifact")
        return mutation if isinstance(mutation, Finding) else [mutation]
    if not isinstance(files, list) or not files:
        return Finding(
            code="invalid_listening_bundle",
            message="Listening bundle files must be a non-empty list.",
            path="files",
        )
    mutations: list[FileMutation] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            return Finding(
                code="invalid_listening_bundle_file",
                message="Each listening bundle file must be an object.",
                path=f"files[{index}]",
            )
        path = item.get("path")
        if not isinstance(path, str) or not path:
            return Finding(
                code="invalid_listening_bundle_path",
                message="Each listening bundle file requires a Vault-relative path.",
                path=f"files[{index}].path",
            )
        if path in seen_paths:
            return Finding(
                code="duplicate_listening_bundle_path",
                message="Listening bundle paths must be unique.",
                path=path,
            )
        seen_paths.add(path)
        source_path = item.get("source_path")
        content = item.get("content")
        if source_path is not None and not isinstance(source_path, (str, Path)):
            return Finding(
                code="invalid_listening_bundle_source",
                message="Listening bundle source_path must be a filesystem path.",
                path=path,
            )
        mutations.append(
            FileMutation(
                path=path,
                content=content if isinstance(content, (str, bytes)) else None,
                source_path=source_path,
                action=str(item.get("action") or "write_listening_artifact"),
                reason=str(item.get("reason") or "prepared listening bundle"),
            )
        )
    return mutations


def _path_is_within_role(path: str, role_root: str) -> bool:
    normalized_path = Path(path).as_posix().strip("/")
    normalized_root = Path(role_root).as_posix().strip("/")
    return normalized_path == normalized_root or normalized_path.startswith(f"{normalized_root}/")


def _is_safe_role_root(role_root: str) -> bool:
    candidate = PurePosixPath(role_root)
    return bool(role_root) and not candidate.is_absolute() and ".." not in candidate.parts


def _review_card_plan(
    root: Path,
    paths: dict[str, str],
    card: dict[str, Any],
) -> ReviewMaterialPlan | Finding:
    path = card.get("path")
    fields = card.get("fields")
    body = card.get("body")
    if not isinstance(path, str) or not path.endswith(".md"):
        return Finding(code="invalid_review_card_path", message="Review card path must be a Vault-relative Markdown path.", path="path")
    path_candidate = PurePosixPath(path)
    if path_candidate.is_absolute() or ".." in path_candidate.parts or "\\" in path or _contains_control_character(path):
        return Finding(code="invalid_review_card_path", message="Review card path must be a safe Vault-relative Markdown path.", path=path)
    if len(Path(path).name.encode("utf-8")) > MAX_REVIEW_CARD_FILENAME_BYTES:
        return Finding(
            code="review_card_filename_too_long",
            message="Review card filenames must be short enough for guarded atomic writes.",
            path=path,
        )
    if not any(paths.get(role) and _path_is_within_role(path, str(paths[role])) for role in REVIEW_MATERIAL_ROLES):
        return Finding(
            code="review_card_outside_role",
            message="Review card path must stay inside a configured review-material role.",
            path=path,
        )
    if not (root / path).exists() and _contains_link_reserved_character(Path(path).stem):
        return Finding(
            code="unsafe_review_item_title",
            message="New review card filenames cannot contain #, |, [, ], or ^.",
            path=path,
        )
    if not isinstance(fields, dict):
        return Finding(code="invalid_review_card_fields", message="Review card fields must be an object.", path=path)
    if not isinstance(body, str) or not body.strip():
        return Finding(code="invalid_review_card_body", message="Review card body must contain readable review content.", path=path)
    normalized_fields = dict(fields)
    source_resolution = _resolve_required_source_links(
        root,
        paths,
        _input_values(normalized_fields.get("source_notes")),
        target_path=path,
    )
    if isinstance(source_resolution, Finding):
        return source_resolution
    source_links, source_reads = source_resolution
    normalized_fields["source_notes"] = source_links
    item_type = str(normalized_fields.get("item_type") or "")
    if item_type not in RELATED_LINK_ROLES:
        return Finding(code="unsupported_review_item_type", message="Review material item_type is not supported.", path="item_type")
    relations = _resolve_optional_relation_links(root, paths, item_type, normalized_fields, target_path=path)
    for relation_field in ("confusable_with", "contrast_with", "related_items"):
        normalized_fields.pop(relation_field, None)
    normalized_fields.update(relations[0])
    if not (root / path).exists() and normalized_fields.get("status") != "active":
        return Finding(
            code="invalid_new_review_status",
            message="New review cards must start with status: active.",
            path=path,
        )
    validation = validate_review_materials(normalized_fields)
    if not validation.accepted:
        return validation.errors[0]
    normalized_body = _body_with_unresolved_related_items(body, relations[1])
    content = _render_markdown(normalized_fields, normalized_body)
    return ReviewMaterialPlan(
        mutation=FileMutation(path=path, content=content, action="write_review_material", reason="accepted review material card"),
        warnings=tuple(relations[2]),
        unresolved_related_items=tuple(relations[1]),
        read_files=tuple(dict.fromkeys([*source_reads, *relations[3]])),
    )


def _daily_checklist_plan(
    root: Path,
    paths: dict[str, str],
    payload: dict[str, Any],
) -> ReviewMaterialPlan | Finding:
    path = payload.get("path")
    if not isinstance(path, str) or not path.endswith(".md"):
        return Finding(
            code="invalid_daily_checklist_path",
            message="Daily checklist updates require an exact Vault-relative Markdown path.",
            path="path",
        )
    candidate = PurePosixPath(path)
    daily_root = paths.get("daily_notes_root")
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or "\\" in path
        or _contains_control_character(path)
        or not daily_root
        or not _is_safe_role_root(daily_root)
        or not _path_is_within_role(path, daily_root)
    ):
        return Finding(
            code="daily_checklist_outside_role",
            message="Daily checklist updates must stay inside the configured daily-notes role.",
            path=path,
        )
    if not _is_dated_note_stem(Path(path).stem):
        return Finding(
            code="daily_checklist_requires_dated_note",
            message="Daily checklist updates require a dated note named YYYY-MM-DD.md or YYYY.M.D.md.",
            path=path,
        )
    target = root / path
    if not target.is_file():
        return Finding(
            code="missing_daily_checklist_note",
            message="Daily checklist updates require an existing dated note; no note was created implicitly.",
            path=path,
        )
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(root.resolve())
    except ValueError:
        return Finding(
            code="daily_checklist_outside_vault",
            message="The dated note resolves outside the target Vault.",
            path=path,
        )

    completed = _daily_checklist_items(payload.get("completed"), field="completed")
    if isinstance(completed, Finding):
        return completed
    blockers = _daily_checklist_items(payload.get("blockers"), field="blockers")
    if isinstance(blockers, Finding):
        return blockers
    reflection = _daily_checklist_reflection(payload.get("reflection"))
    if isinstance(reflection, Finding):
        return reflection
    if not completed and not blockers and not reflection:
        return Finding(
            code="empty_daily_checklist",
            message="A daily checklist update requires completed items, blockers, or a short reflection.",
            path=path,
        )

    sections = ["## 每日学习清单"]
    if completed:
        sections.append("## 今日完成\n\n" + "\n".join(f"- {value}" for value in completed))
    if blockers:
        sections.append("## 今日卡点\n\n" + "\n".join(f"- {value}" for value in blockers))
    if reflection:
        sections.append(f"## 简短复盘\n\n{reflection}")
    managed_block = f"{DAILY_CHECKLIST_START}\n" + "\n\n".join(sections) + f"\n{DAILY_CHECKLIST_END}"
    original = target.read_text(encoding="utf-8")
    if DAILY_CHECKLIST_START in original or DAILY_CHECKLIST_END in original:
        if original.count(DAILY_CHECKLIST_START) != 1 or original.count(DAILY_CHECKLIST_END) != 1:
            return Finding(
                code="malformed_managed_daily_checklist",
                message="The managed daily checklist markers are incomplete or duplicated.",
                path=path,
            )
        start = original.index(DAILY_CHECKLIST_START)
        end = original.index(DAILY_CHECKLIST_END, start) + len(DAILY_CHECKLIST_END)
        content = original[:start].rstrip() + "\n\n" + managed_block + original[end:]
    else:
        managed_headings = ("## 每日学习清单", "## 今日完成", "## 今日卡点", "## 简短复盘")
        if any(re.search(rf"(?m)^{re.escape(heading)}\s*$", original) for heading in managed_headings):
            return Finding(
                code="unmanaged_daily_checklist_exists",
                message="An existing manual daily checklist was preserved; explicit migration is required before managed updates.",
                path=path,
            )
        content = original.rstrip() + "\n\n" + managed_block + "\n"
    return ReviewMaterialPlan(
        mutation=FileMutation(
            path=path,
            content=content,
            action="update_daily_study_checklist",
            reason="explicit structured daily checklist update",
        ),
        read_files=(path,),
    )


def _daily_checklist_items(value: Any, *, field: str) -> list[str] | Finding:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_DAILY_CHECKLIST_ITEMS:
        return Finding(
            code="invalid_daily_checklist_items",
            message=f"{field} must be a list with at most {MAX_DAILY_CHECKLIST_ITEMS} short items.",
            path=field,
        )
    result: list[str] = []
    for index, raw in enumerate(value):
        normalized = _daily_checklist_text(raw, path=f"{field}[{index}]")
        if isinstance(normalized, Finding):
            return normalized
        result.append(normalized)
    return result


def _daily_checklist_reflection(value: Any) -> str | Finding:
    if value is None:
        return ""
    return _daily_checklist_text(value, path="reflection")


def _daily_checklist_text(value: Any, *, path: str) -> str | Finding:
    if not isinstance(value, str):
        return Finding(code="invalid_daily_checklist_text", message="Daily checklist text must be a string.", path=path)
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > MAX_DAILY_CHECKLIST_TEXT_LENGTH
        or "\n" in normalized
        or "\r" in normalized
        or _contains_control_character(normalized)
        or normalized.startswith("#")
        or normalized == "---"
        or "[[" in normalized
        or "]]" in normalized
        or DAILY_CHECKLIST_START in normalized
        or DAILY_CHECKLIST_END in normalized
    ):
        return Finding(
            code="invalid_daily_checklist_text",
            message="Daily checklist entries must be short single-line plain text.",
            path=path,
        )
    return normalized


def _is_dated_note_stem(stem: str) -> bool:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem):
            dt.date.fromisoformat(stem)
            return True
        match = re.fullmatch(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", stem)
        if match:
            dt.date(*(int(value) for value in match.groups()))
            return True
    except ValueError:
        return False
    return False


def _review_item_plan(
    root: Path,
    paths: dict[str, str],
    item: dict[str, Any],
    *,
    extraction_date: str | None,
) -> ReviewMaterialPlan | Finding:
    review_date = extraction_date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(review_date)
    except ValueError:
        return Finding(code="invalid_extraction_date", message="extraction_date must use YYYY-MM-DD format.", path="extraction_date")

    item_type = _infer_review_item_type(item)
    if item_type not in {"vocab", "grammar", "error", "pronunciation"}:
        return Finding(code="unsupported_review_item_type", message="Review material item_type is not supported.", path="item_type")

    title = _review_item_title(item_type, item)
    if isinstance(title, Finding):
        return title
    target_role = _review_item_target_role(item_type, item)
    if isinstance(target_role, Finding):
        return target_role
    target_root = paths.get(target_role)
    if not target_root:
        return Finding(code="missing_path_role", message=f"Target path role is not configured: {target_role}.", path=target_role)
    if not _is_safe_role_root(target_root):
        return Finding(code="invalid_path_role", message="Review material path roles must be safe Vault-relative paths.", path=target_role)

    target_match: Path | None = None
    if item_type == "vocab":
        focus_root = paths.get("focus_vocab_root")
        base_root = paths.get("base_vocab_root")
        if not focus_root or not base_root:
            return Finding(code="missing_path_role", message="Vocabulary review requires focus and base path roles.", path="focus_vocab_root")
        if not _is_safe_role_root(focus_root) or not _is_safe_role_root(base_root):
            return Finding(code="invalid_path_role", message="Vocabulary path roles must be safe Vault-relative paths.", path="focus_vocab_root")
        focus_match = _single_review_match(root / focus_root, title)
        if isinstance(focus_match, Finding):
            return focus_match
        if focus_match is not None:
            target_match = focus_match
            target_role = "focus_vocab_root"
        base_match: Path | None = None
        if target_match is None:
            base_match = _single_review_match(root / base_root, title)
            if isinstance(base_match, Finding):
                return base_match
        if base_match is not None:
            target_path = _new_review_item_path(focus_root, item_type, title, review_date)
            source_resolution = _resolve_item_source_links(root, paths, item, target_path=target_path)
            if isinstance(source_resolution, Finding):
                return source_resolution
            source_links, source_reads = source_resolution
            image_reads = _validate_image_backed_item(root, item, item_type, title, source_reads)
            if isinstance(image_reads, Finding):
                return image_reads
            source_reads = list(dict.fromkeys([*source_reads, *image_reads]))
            relations = _resolve_optional_relation_links(root, paths, item_type, item, target_path=target_path)
            base_fields = _frontmatter(base_match)
            fields = _initialized_review_fields(item_type, title, item, review_date, source_links=source_links)
            fields.update({key: value for key, value in base_fields.items() if key not in fields and value not in (None, "", [])})
            fields.update(_item_fields(item_type, item, title, relation_links=relations[0]))
            fields["source_notes"] = _merge_link_values(
                base_fields.get("source_notes"),
                source_links,
                root=root,
                paths=paths,
                target_path=target_path,
            )
            collision_error = _path_collision_error(root, target_path, title)
            if collision_error is not None:
                return collision_error
            validation_error = _review_material_validation_error(fields, target_path)
            if validation_error is not None:
                return validation_error
            generated_body = _generated_review_body(item_type, fields, item, relations[1])
            if isinstance(generated_body, Finding):
                return generated_body
            return ReviewMaterialPlan(
                mutation=FileMutation(
                    path=target_path,
                    content=_render_markdown(fields, generated_body),
                    action="restore_focus_card",
                    reason="base lexicon item reappears and returns to active focus review",
                ),
                warnings=tuple(relations[2]),
                unresolved_related_items=tuple(relations[1]),
                read_files=tuple(dict.fromkeys([*source_reads, *relations[3], base_match.relative_to(root).as_posix()])),
            )

    if target_match is None:
        target_match = _single_review_match(root / target_root, title)
        if isinstance(target_match, Finding):
            return target_match
    if target_match is not None:
        target_path = target_match.relative_to(root).as_posix()
        source_resolution = _resolve_item_source_links(root, paths, item, target_path=target_path)
        if isinstance(source_resolution, Finding):
            return source_resolution
        source_links, source_reads = source_resolution
        image_reads = _validate_image_backed_item(root, item, item_type, title, source_reads)
        if isinstance(image_reads, Finding):
            return image_reads
        source_reads = list(dict.fromkeys([*source_reads, *image_reads]))
        mutation = _mutation_for_existing_item(
            root,
            paths,
            target_match,
            item,
            review_date,
            action_role=target_role,
            source_links=source_links,
        )
        if isinstance(mutation, Finding):
            return mutation
        return ReviewMaterialPlan(
            mutation=mutation,
            read_files=tuple(dict.fromkeys([*source_reads, target_path])),
        )

    target_path = _new_review_item_path(target_root, item_type, title, review_date)
    source_resolution = _resolve_item_source_links(root, paths, item, target_path=target_path)
    if isinstance(source_resolution, Finding):
        return source_resolution
    source_links, source_reads = source_resolution
    image_reads = _validate_image_backed_item(root, item, item_type, title, source_reads)
    if isinstance(image_reads, Finding):
        return image_reads
    source_reads = list(dict.fromkeys([*source_reads, *image_reads]))
    relations = _resolve_optional_relation_links(root, paths, item_type, item, target_path=target_path)
    fields = _initialized_review_fields(item_type, title, item, review_date, source_links=source_links)
    fields.update(_item_fields(item_type, item, title, relation_links=relations[0]))
    collision_error = _path_collision_error(root, target_path, title)
    if collision_error is not None:
        return collision_error
    validation_error = _review_material_validation_error(fields, target_path)
    if validation_error is not None:
        return validation_error
    generated_body = _generated_review_body(item_type, fields, item, relations[1])
    if isinstance(generated_body, Finding):
        return generated_body
    content = _render_markdown(fields, generated_body)
    action = "create_focus_card" if item_type == "vocab" else f"create_{item_type}_card"
    return ReviewMaterialPlan(
        mutation=FileMutation(
            path=target_path,
            content=content,
            action=action,
            reason="accepted structured review material item",
        ),
        warnings=tuple(relations[2]),
        unresolved_related_items=tuple(relations[1]),
        read_files=tuple(dict.fromkeys([*source_reads, *relations[3]])),
    )


def _infer_review_item_type(item: dict[str, Any]) -> str:
    explicit = item.get("item_type")
    if isinstance(explicit, str) and explicit:
        return explicit
    if item.get("correct_form") or item.get("wrong_form"):
        return "error"
    if item.get("pattern") or item.get("formation"):
        return "grammar"
    if item.get("target_text") or item.get("pronunciation_kind"):
        return "pronunciation"
    return "vocab"


def _review_item_title(item_type: str, item: dict[str, Any]) -> str | Finding:
    key_by_type = {
        "vocab": "headword",
        "grammar": "pattern",
        "error": "correct_form",
        "pronunciation": "target_text",
    }
    key = key_by_type[item_type]
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        return Finding(code="missing_review_item_title", message=f"Review material item requires {key}.", path=key)
    title = value.strip()
    if _contains_link_reserved_character(title) or _contains_control_character(title):
        return Finding(
            code="unsafe_review_item_title",
            message="New review card filenames cannot contain control characters or #, |, [, ], or ^.",
            path=key,
        )
    return title


def _review_item_target_role(item_type: str, item: dict[str, Any]) -> str | Finding:
    if item_type == "vocab":
        return "focus_vocab_root"
    if item_type == "grammar":
        return "grammar_root"
    if item_type == "error":
        return "error_root"
    pronunciation_kind = item.get("pronunciation_kind")
    if pronunciation_kind == "accent":
        return "pronunciation_accent_root"
    if pronunciation_kind == "phoneme":
        return "pronunciation_phoneme_root"
    return Finding(
        code="missing_pronunciation_kind",
        message="Pronunciation review material requires pronunciation_kind: accent or phoneme.",
        path="pronunciation_kind",
    )


def _single_review_match(path_root: Path, title: str) -> Path | Finding | None:
    if not path_root.exists():
        return None
    matches: list[Path] = []
    for card_path in sorted(path_root.rglob("*.md")):
        fields = _frontmatter(card_path)
        if _review_match_key(fields, card_path) == title:
            matches.append(card_path)
    if len(matches) > 1:
        return Finding(
            code="duplicate_review_material_match",
            message="Multiple existing review cards match the same learning point.",
            path=", ".join(path.relative_to(path_root).as_posix() for path in matches),
        )
    return matches[0] if matches else None


def _review_match_key(fields: dict[str, Any], card_path: Path) -> str:
    for key in ("headword", "pattern", "correct_form", "target_text"):
        value = fields.get(key)
        if value:
            return value
    return card_path.stem


def _mutation_for_existing_item(
    root: Path,
    paths: dict[str, str],
    card_path: Path,
    item: dict[str, Any],
    review_date: str,
    *,
    action_role: str,
    source_links: list[str],
) -> FileMutation | Finding:
    text = card_path.read_text(encoding="utf-8")
    fields, _ = _frontmatter_and_body(text)
    item_type = str(fields.get("item_type") or _infer_review_item_type(item))
    updates: dict[str, Any] = {}
    target_path = card_path.relative_to(root).as_posix()
    existing_sources = _input_values(fields.get("source_notes"))
    merged_sources = _merge_link_values(
        existing_sources,
        source_links,
        root=root,
        paths=paths,
        target_path=target_path,
    )
    source_is_new = bool(source_links) and any(
        not any(
            _links_refer_to_same_target(
                link,
                existing,
                root=root,
                paths=paths,
                target_path=target_path,
            )
            for existing in existing_sources
        )
        for link in source_links
    )
    source_reappeared = (
        action_role == "focus_vocab_root"
        and source_is_new
    )
    weakness_reappeared = item_type == "error" or item.get("weakness") is True
    fields["source_notes"] = merged_sources
    updates["source_notes"] = merged_sources
    fields["last_seen"] = review_date
    updates["last_seen"] = review_date
    if source_is_new or weakness_reappeared:
        seen_count = _integer_value(fields.get("seen_count"), default=1) + 1
        fields["seen_count"] = seen_count
        updates["seen_count"] = seen_count
    if item_type == "error" or item.get("weakness") is True:
        prior_error_default = 1 if item_type == "error" else 0
        error_count = _integer_value(fields.get("error_count"), default=prior_error_default) + 1
        fields["error_count"] = error_count
        updates["error_count"] = error_count
        fields["priority"] = "high"
        updates["priority"] = "high"
    if fields.get("status") == "mastered":
        fields["status"] = "active"
        fields["done_today"] = False
        fields["review_stage"] = "day0"
        fields["next_review"] = review_date
        fields["last_reviewed"] = ""
        updates.update(
            {
                "status": "active",
                "done_today": False,
                "review_stage": "day0",
                "next_review": review_date,
                "last_reviewed": "",
            }
        )
    elif fields.get("status") == "active" and (source_reappeared or weakness_reappeared):
        fields["done_today"] = False
        fields["review_stage"] = "day0"
        fields["next_review"] = review_date
        fields["last_reviewed"] = ""
        updates.update(
            {
                "done_today": False,
                "review_stage": "day0",
                "next_review": review_date,
                "last_reviewed": "",
            }
        )
    action = "reactivate_review_card" if fields.get("review_stage") == "day0" and fields.get("next_review") == review_date else "update_review_card"
    if action_role == "focus_vocab_root":
        action = "update_focus_card" if action == "update_review_card" else "reactivate_focus_card"
    return FileMutation(
        path=card_path.relative_to(root).as_posix(),
        content=_replace_frontmatter_fields(text, updates),
        action=action,
        reason="existing review material matched structured item",
    )


def _path_collision_error(root: Path, relative_path: str, title: str) -> Finding | None:
    target = root / relative_path
    if not target.exists():
        return None
    fields = _frontmatter(target)
    if _review_match_key(fields, target) == title:
        return None
    return Finding(
        code="review_material_path_collision",
        message="Target review material path already exists for a different learning point.",
        path=relative_path,
    )


def _base_vocab_sink_mutation(
    root: Path,
    paths: dict[str, str],
    focus_path: Path,
    focus_fields: dict[str, Any],
) -> FileMutation | Finding | None:
    base_root = paths.get("base_vocab_root")
    if not base_root:
        return Finding(code="missing_path_role", message="Base vocabulary path role is required for day180 vocabulary sink.", path="base_vocab_root")
    title = str(focus_fields.get("headword") or focus_path.stem)
    base_match = _single_review_match(root / base_root, title)
    if isinstance(base_match, Finding):
        return base_match
    stable_fields = _base_vocab_fields_from_focus(focus_fields, title)
    if base_match is not None:
        base_text = base_match.read_text(encoding="utf-8")
        base_fields, base_body = _frontmatter_and_body(base_text)
        merged_fields = dict(base_fields)
        merged_fields.update(stable_fields)
        merged_fields["source_notes"] = _merge_link_values(base_fields.get("source_notes"), focus_fields.get("source_notes"))
        return FileMutation(
            path=base_match.relative_to(root).as_posix(),
            content=_render_markdown(merged_fields, base_body),
            action="sink_focus_vocab_to_base",
            reason="day180 focus vocabulary completed and updates the base lexicon",
        )

    target_path = f"{base_root}/{_safe_card_filename(title)}.md"
    collision_error = _path_collision_error(root, target_path, title)
    if collision_error is not None:
        return collision_error
    generated_body = _generated_review_body("vocab", stable_fields, stable_fields)
    assert isinstance(generated_body, str)
    return FileMutation(
        path=target_path,
        content=_render_markdown(stable_fields, generated_body),
        action="sink_focus_vocab_to_base",
        reason="day180 focus vocabulary completed and creates a base lexicon record",
    )


def _base_vocab_fields_from_focus(focus_fields: dict[str, Any], title: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "track": "base_vocab",
        "item_type": "vocab",
        "status": "promoted",
        "priority": focus_fields.get("priority", "normal"),
        "done_today": False,
        "headword": title,
    }
    for key in (
        "reading",
        "accent_display",
        "meaning_zh",
        "collocations",
        "confusable_with",
        "contrast_with",
        "kanji_diff",
        "kanji_diff_pairs",
        "source_notes",
        "first_seen",
        "last_seen",
        "seen_count",
        "error_count",
        "last_reviewed",
        "tags",
    ):
        value = focus_fields.get(key)
        if value not in (None, ""):
            fields[key] = value
    return fields


def _review_material_validation_error(fields: dict[str, Any], path: str) -> Finding | None:
    validation = validate_review_materials(fields)
    if validation.accepted:
        return None
    error = validation.errors[0]
    return Finding(code=error.code, message=error.message, path=path)


def _initialized_review_fields(
    item_type: str,
    title: str,
    item: dict[str, Any],
    review_date: str,
    *,
    source_links: list[str],
) -> dict[str, Any]:
    track = "pronunciation" if item_type == "pronunciation" else "class_review"
    fields: dict[str, Any] = {
        "track": track,
        "item_type": item_type,
        "status": "active",
        "priority": str(item.get("priority") or "normal"),
        "done_today": False,
        "first_seen": review_date,
        "last_seen": review_date,
        "seen_count": 1,
        "error_count": 1 if item_type == "error" else 0,
        "review_stage": "day0",
        "next_review": review_date,
        "last_reviewed": "",
        "source_notes": source_links,
        "tags": _default_review_tags(item_type, item),
    }
    return fields


def _item_fields(
    item_type: str,
    item: dict[str, Any],
    title: str,
    *,
    relation_links: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    key_by_type = {
        "vocab": "headword",
        "grammar": "pattern",
        "error": "correct_form",
        "pronunciation": "target_text",
    }
    fields[key_by_type[item_type]] = title
    allowed = {
        "vocab": (
            "reading",
            "accent_display",
            "meaning_zh",
            "part_of_speech",
            "collocations",
            "kanji_diff",
            "kanji_diff_pairs",
        ),
        "grammar": (
            "meaning_zh",
            "formation",
            "core_nuance",
            "register",
            "usage_scenes",
            "jlpt",
            "confusion_notes",
        ),
        "error": ("wrong_form", "reason", "avoidance", "meaning_zh", "source_sentence"),
        "pronunciation": ("pronunciation_kind", "issue_tags", "meaning_zh"),
    }[item_type]
    for key in allowed:
        value = item.get(key)
        if value not in (None, ""):
            if key in LIST_FIELDS:
                fields[key] = _input_values(value)
            else:
                fields[key] = value
    for key, value in (relation_links or {}).items():
        fields[key] = value
    return fields


def _default_review_tags(item_type: str, item: dict[str, Any]) -> list[str]:
    tags = [f"jp/{item_type}", "jp/class_review"]
    if item_type == "pronunciation":
        tags = ["jp/pronunciation"]
    if item.get("priority") == "high" or item.get("high_risk") is True:
        tags.append("jp/high_risk")
    if item.get("kanji_diff") is True:
        tags.append("jp/kanji_diff")
    return tags


def _generated_review_body(
    item_type: str,
    fields: dict[str, Any],
    item: dict[str, Any],
    unresolved_related_items: list[str] | tuple[str, ...] = (),
) -> str | Finding:
    if item_type == "grammar":
        return _render_grammar_body(fields, item, unresolved_related_items)
    if item_type == "error":
        return _render_error_body(fields, item, unresolved_related_items)
    if item_type == "pronunciation":
        issue_tags = "、".join(_input_values(fields.get("issue_tags")))
        return f"## {fields.get('target_text', '')}\n\n- 练习重点：{issue_tags}".rstrip()
    return _render_vocab_body(fields, item, unresolved_related_items)


def _render_vocab_body(
    fields: dict[str, Any],
    item: dict[str, Any],
    unresolved_related_items: list[str] | tuple[str, ...],
) -> str:
    sections: list[str] = []
    quick: list[str] = []
    if fields.get("meaning_zh"):
        quick.append(f"- 中文：{fields['meaning_zh']}")
    if fields.get("reading"):
        quick.append(f"- 读音：{fields['reading']}")
    collocations = _input_values(fields.get("collocations"))
    if collocations:
        quick.append(f"- 常用搭配：{'；'.join(collocations)}")
    if quick:
        sections.append("## 快速复习\n\n" + "\n".join(quick))

    core: list[str] = []
    accent = fields.get("accent_display")
    if accent:
        accent_label = item.get("accent_label")
        core.append(f"- 重音：{accent_label} ({accent})" if accent_label else f"- 重音：{accent}")
    if fields.get("part_of_speech"):
        core.append(f"- 词性：{fields['part_of_speech']}")
    if core:
        sections.append("## 核心\n\n" + "\n".join(core))

    examples = _example_entries(item.get("examples"))
    if item.get("example_jp"):
        examples.insert(0, (str(item["example_jp"]), str(item.get("example_zh") or "")))
    if examples:
        lines: list[str] = []
        for japanese, chinese in examples:
            lines.append(f"- {japanese}")
            if chinese:
                lines.append(f"  - 中文：{chinese}")
        sections.append("## 例句\n\n" + "\n".join(lines))

    confusion: list[str] = []
    for link in _input_values(fields.get("confusable_with")) + _input_values(fields.get("contrast_with")):
        confusion.append(f"- 对比：{link}")
    for note in _input_values(item.get("confusion_notes")):
        confusion.append(f"- {note}")
    if confusion:
        sections.append("## 易错 / 易混\n\n" + "\n".join(confusion))
    if unresolved_related_items:
        sections.append("## 待补卡\n\n" + "\n".join(f"- {value}" for value in unresolved_related_items))
    source_section = _render_source_section(fields)
    if source_section:
        sections.append(source_section)
    return "\n\n".join(sections)


def _render_grammar_body(
    fields: dict[str, Any],
    item: dict[str, Any],
    unresolved_related_items: list[str] | tuple[str, ...],
) -> str | Finding:
    pattern = str(fields.get("pattern") or "")
    sections = [f"# {pattern}"]
    formation = _input_values(fields.get("formation"))
    quick: list[str] = []
    if fields.get("meaning_zh"):
        quick.append(f"- 中文：{fields['meaning_zh']}")
    if formation:
        quick.append(f"- 接续：{'；'.join(formation)}")
    if fields.get("core_nuance"):
        quick.append(f"- 核心语感：{fields['core_nuance']}")
    if item.get("typical_example_jp"):
        quick.append(f"- 典型例句：{item['typical_example_jp']}")
    if quick:
        sections.append("## 快速复习\n\n" + "\n".join(quick))

    register_lines: list[str] = []
    if fields.get("register"):
        register_lines.append(f"- 语域：{fields['register']}")
    usage_scenes = _input_values(fields.get("usage_scenes"))
    if usage_scenes:
        register_lines.append(f"- 常见场景：{'；'.join(usage_scenes)}")
    if fields.get("jlpt"):
        register_lines.append(f"- JLPT：{fields['jlpt']}")
    if register_lines:
        sections.append("## 语域与使用场景\n\n" + "\n".join(register_lines))

    core_text = fields.get("core_nuance") or item.get("usage")
    if core_text:
        sections.append(f"## 核心\n\n{core_text}")

    usage_sections = item.get("usage_sections")
    if usage_sections is not None and not isinstance(usage_sections, list):
        return Finding(
            code="invalid_grammar_usage_sections",
            message="usage_sections must be a list of structured grammar usage objects.",
            path="usage_sections",
        )
    rendered_usage: list[str] = []
    if usage_sections:
        for index, usage in enumerate(usage_sections, start=1):
            if not isinstance(usage, dict):
                return Finding(
                    code="invalid_grammar_usage_section",
                    message="Every grammar usage section must be an object.",
                    path=f"usage_sections[{index - 1}]",
                )
            detail_lines: list[str] = []
            usage_formation = _input_values(usage.get("formation"))
            if usage_formation:
                detail_lines.append(f"- 接续：{'；'.join(usage_formation)}")
            if usage.get("nuance"):
                detail_lines.append(f"- 核心语感：{usage['nuance']}")
            examples = _example_entries(usage.get("examples"))
            if examples:
                detail_lines.append("- 例句：")
                for japanese, chinese in examples:
                    suffix = f"（{chinese}）" if chinese else ""
                    detail_lines.append(f"  - {japanese}{suffix}")
            if not detail_lines:
                continue
            title = str(usage.get("title") or f"用法 {index}")
            rendered_usage.append("\n".join([f"### {index}. {title}", *detail_lines]))
    if not rendered_usage and (formation or item.get("examples")):
        lines = ["### 1. 基本用法"]
        if formation:
            lines.append(f"- 接续：{'；'.join(formation)}")
        if fields.get("core_nuance"):
            lines.append(f"- 核心语感：{fields['core_nuance']}")
        examples = _example_entries(item.get("examples"))
        if examples:
            lines.append("- 例句：")
            for japanese, chinese in examples:
                suffix = f"（{chinese}）" if chinese else ""
                lines.append(f"  - {japanese}{suffix}")
        rendered_usage.append("\n".join(lines))
    if rendered_usage:
        sections.append("## 接续、用法与例句\n\n" + "\n\n".join(rendered_usage))

    confusion: list[str] = []
    for link in _input_values(fields.get("contrast_with")):
        confusion.append(f"- 对比：{link}")
    for note in _input_values(fields.get("confusion_notes")):
        confusion.append(f"- {note}")
    if confusion:
        sections.append("## 易错 / 易混\n\n" + "\n".join(confusion))
    if unresolved_related_items:
        sections.append("## 待补卡\n\n" + "\n".join(f"- {value}" for value in unresolved_related_items))
    source_section = _render_source_section(fields)
    sections.append(source_section or "## 来源\n\n- 用户直接录入；大模型整理")
    return "\n\n".join(sections)


def _render_error_body(
    fields: dict[str, Any],
    item: dict[str, Any],
    unresolved_related_items: list[str] | tuple[str, ...],
) -> str | Finding:
    wrong = _highlight_focus(str(fields.get("wrong_form") or ""), item.get("wrong_focus"), "wrong_focus")
    if isinstance(wrong, Finding):
        return wrong
    correct = _highlight_focus(str(fields.get("correct_form") or ""), item.get("correct_focus"), "correct_focus")
    if isinstance(correct, Finding):
        return correct
    sections = [
        f"## 错误句\n\n❌：{wrong}",
        f"## 正确句\n\n⭕️：{correct}",
        f"## 为什么错\n\n{fields.get('reason', '')}",
        f"## 下次怎么避免\n\n{fields.get('avoidance', '')}",
    ]
    related = _input_values(fields.get("related_items"))
    if related:
        sections.append("## 关联复习\n\n" + "\n".join(f"- {link}" for link in related))
    if unresolved_related_items:
        sections.append("## 待补卡\n\n" + "\n".join(f"- {value}" for value in unresolved_related_items))
    source_section = _render_source_section(fields)
    if source_section:
        sections.append(source_section)
    return "\n\n".join(sections)


def _highlight_focus(text: str, raw_focus: Any, field_name: str) -> str | Finding:
    if raw_focus in (None, ""):
        return text
    focus = str(raw_focus)
    if text.count(focus) != 1:
        return Finding(
            code="invalid_error_focus",
            message=f"{field_name} must match exactly one substring in its sentence.",
            path=field_name,
        )
    return text.replace(focus, f"=={focus}==", 1)


def _render_source_section(fields: dict[str, Any]) -> str:
    sources = _input_values(fields.get("source_notes"))
    if not sources:
        return ""
    return "## 来源\n\n" + "\n".join(f"- {source}" for source in sources)


def _body_with_unresolved_related_items(body: str, unresolved_related_items: list[str] | tuple[str, ...]) -> str:
    pending = list(dict.fromkeys(str(value).strip() for value in unresolved_related_items if str(value).strip()))
    text = body.rstrip()
    if not pending:
        return text

    lines = text.splitlines()
    heading = "## 待补卡"
    try:
        start = lines.index(heading)
    except ValueError:
        section = heading + "\n\n" + "\n".join(f"- {value}" for value in pending)
        return f"{text}\n\n{section}" if text else section

    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    existing = {line[2:].strip() for line in lines[start + 1 : end] if line.startswith("- ")}
    additions = [value for value in pending if value not in existing]
    if not additions:
        return text
    insertion = end
    while insertion > start + 1 and not lines[insertion - 1].strip():
        insertion -= 1
    inserted = ([""] if insertion == start + 1 else []) + [f"- {value}" for value in additions]
    if end < len(lines):
        inserted.append("")
    return "\n".join([*lines[:insertion], *inserted, *lines[insertion:]]).rstrip()


def _example_entries(value: Any) -> list[tuple[str, str]]:
    if value in (None, ""):
        return []
    values = value if isinstance(value, (list, tuple)) else [value]
    examples: list[tuple[str, str]] = []
    for entry in values:
        if isinstance(entry, dict):
            japanese = str(entry.get("jp") or entry.get("japanese") or "").strip()
            chinese = str(entry.get("zh") or entry.get("chinese") or "").strip()
        else:
            japanese = str(entry).strip()
            chinese = ""
        if japanese:
            examples.append((japanese, chinese))
    return examples


def _new_review_item_path(target_root: str, item_type: str, title: str, review_date: str) -> str:
    filename = _safe_card_filename(title)
    if item_type == "error":
        filename = f"{review_date}_{filename}"
    return f"{target_root}/{filename}.md"


def _contains_link_reserved_character(value: str) -> bool:
    return any(character in value for character in ("#", "|", "[", "]", "^"))


def _contains_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _safe_card_filename(title: str) -> str:
    cleaned = title.strip().replace(" / ", "-").replace("/", "-").replace("\\", "-")
    for char in (":", "*", "?", '"', "<", ">"):
        cleaned = cleaned.replace(char, "-")
    filename = "-".join(cleaned.split()) or "review-material"
    if len(filename.encode("utf-8")) <= MAX_GENERATED_FILENAME_BYTES:
        return filename
    digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:10]
    suffix = f"-{digest}"
    prefix_budget = MAX_GENERATED_FILENAME_BYTES - len(suffix.encode("utf-8"))
    prefix = filename
    while prefix and len(prefix.encode("utf-8")) > prefix_budget:
        prefix = prefix[:-1]
    prefix = prefix.rstrip(" .-") or "review-material"
    return f"{prefix}{suffix}"


def _frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}, text
    return _parse_frontmatter_fields(parts[1]), parts[2].lstrip("\n")


def _parse_frontmatter_fields(frontmatter: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    lines = frontmatter.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line.startswith(" ") or line.startswith("- ") or ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value and key in LIST_FIELDS:
            values: list[str] = []
            lookahead = index + 1
            while lookahead < len(lines) and lines[lookahead].startswith("  - "):
                values.append(str(_parse_yaml_scalar(lines[lookahead][4:].strip())))
                lookahead += 1
            fields[key] = values
            index = lookahead
            continue
        fields[key] = _parse_yaml_scalar(raw_value)
        index += 1
    return fields


def _render_markdown(fields: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.extend(_frontmatter_lines(key, value))
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


def _frontmatter_lines(key: str, value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        if not value:
            return [f"{key}: []"]
        return [f"{key}:", *[f"  - {_format_frontmatter_value(item, key=key)}" for item in value]]
    return [f"{key}: {_format_frontmatter_value(value, key=key)}"]


def _format_frontmatter_value(value: Any, *, key: str | None = None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if key in DATE_FIELDS and _is_iso_date(text):
        return text
    if _is_safe_plain_yaml_text(text):
        return text
    return json.dumps(text, ensure_ascii=False)


def _is_safe_plain_yaml_text(text: str) -> bool:
    if not text or text != text.strip() or "\n" in text or "\r" in text:
        return False
    if _looks_like_yaml_implicit_scalar(text):
        return False
    if text[0] in "-?:,[]{}#&*!|>'\"%@`":
        return False
    if any(character in text for character in ("[", "]", "{", "}", '"', "'")):
        return False
    if ": " in text or " #" in text:
        return False
    return True


def _looks_like_yaml_implicit_scalar(text: str) -> bool:
    lowered = text.casefold()
    if lowered in {
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        "y",
        "n",
        "null",
        "~",
        ".nan",
        ".inf",
        "+.inf",
        "-.inf",
    }:
        return True
    if re.fullmatch(
        r"[+-]?(?:(?:0|[1-9][0-9_]*|0[0-9_]+)(?:\.[0-9_]*)?(?:[eE][+-]?[0-9_]+)?|"
        r"\.[0-9_]+(?:[eE][+-]?[0-9_]+)?|0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+|"
        r"[0-9][0-9_]*(?::[0-5]?[0-9])+)",
        text,
    ):
        return True
    return re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:$|[Tt ])", text) is not None


def _parse_yaml_scalar(raw_value: str) -> Any:
    if raw_value == "[]":
        return []
    if raw_value in {"true", "false"}:
        return raw_value == "true"
    if raw_value.isdigit():
        return int(raw_value)
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == '"':
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return raw_value[1:-1]
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == "'":
        return raw_value[1:-1].replace("''", "'")
    if raw_value.startswith("[") and raw_value.endswith("]"):
        return _input_values(raw_value)
    return raw_value


def _is_iso_date(value: str) -> bool:
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _input_values(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]") and not text.startswith("[["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [part.strip().strip('"').strip("'") for part in text[1:-1].split(",")]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    wikilinks: list[str] = []
    remainder = text
    while remainder.startswith("[[") and "]]" in remainder:
        end = remainder.index("]]" ) + 2
        wikilinks.append(remainder[:end])
        remainder = remainder[end:].lstrip(" ,")
    if wikilinks and not remainder:
        return wikilinks
    return [text]


def _merge_values(existing: Any, additions: Any) -> list[str]:
    merged = _input_values(existing)
    for value in _input_values(additions):
        if value not in merged:
            merged.append(value)
    return merged


def _merge_link_values(
    existing: Any,
    additions: Any,
    *,
    root: Path | None = None,
    paths: dict[str, str] | None = None,
    target_path: str = "",
) -> list[str]:
    merged = _input_values(existing)
    for value in _input_values(additions):
        if not any(
            _links_refer_to_same_target(
                value,
                current,
                root=root,
                paths=paths,
                target_path=target_path,
            )
            for current in merged
        ):
            merged.append(value)
    return merged


def _link_identity(raw: str) -> str:
    text = raw.strip()
    if text.startswith("[[") and text.endswith("]]" ):
        text = text[2:-2].split("|", 1)[0]
    if text.endswith(".md"):
        text = text[:-3]
    return PurePosixPath(text).as_posix().strip("/")


def _links_refer_to_same_target(
    left: str,
    right: str,
    *,
    root: Path | None = None,
    paths: dict[str, str] | None = None,
    target_path: str = "",
) -> bool:
    left_target = _resolved_source_link_identity(root, paths, left, target_path=target_path)
    right_target = _resolved_source_link_identity(root, paths, right, target_path=target_path)
    return left_target == right_target


def _resolved_source_link_identity(
    root: Path | None,
    paths: dict[str, str] | None,
    raw: str,
    *,
    target_path: str,
) -> str:
    target = _link_identity(raw)
    if root is None or paths is None or "/" in target:
        return target
    resolution = _resolve_vault_link(
        root,
        paths,
        raw,
        allowed_roles=SOURCE_LINK_ROLES,
        target_path=target_path,
        link_kind="source_note",
    )
    if resolution.finding is not None or resolution.link is None:
        return target
    return _link_identity(resolution.link)


def _integer_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _truthy(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.lower() == "true")


def _validate_image_backed_item(
    root: Path,
    item: dict[str, Any],
    item_type: str,
    title: str,
    source_reads: list[str],
) -> list[str] | Finding:
    if item.get("image_backed") is not True:
        return []
    if item_type != "vocab":
        return Finding(
            code="invalid_image_backed_review_type",
            message="Image-backed extraction is supported only for vocabulary items.",
            path="item_type",
        )
    if item.get("image_readable") is False:
        return Finding(
            code="uncertain_image_backed_review_material",
            message="Image-backed review material must be clearly readable before creating a card.",
            path=str(item.get("attachment") or "image_evidence"),
        )
    evidence = item.get("image_evidence")
    if not isinstance(evidence, dict):
        return Finding(
            code="missing_image_inspection_evidence",
            message="Image-backed vocabulary requires structured evidence from a visual or manual attachment inspection.",
            path="image_evidence",
        )
    if evidence.get("inspection_method") not in {"visual", "manual"}:
        return Finding(
            code="invalid_image_inspection_method",
            message="Image inspection must be visual or manual; OCR-only evidence is not accepted.",
            path="image_evidence.inspection_method",
        )
    if evidence.get("readability") != "clear":
        return Finding(
            code="uncertain_image_backed_review_material",
            message="Only clearly readable image-backed vocabulary may enter duplicate search.",
            path="image_evidence.readability",
        )
    observed_text = evidence.get("observed_text")
    normalized_headword = evidence.get("normalized_headword")
    if not isinstance(observed_text, str) or not observed_text.strip() or _contains_control_character(observed_text):
        return Finding(
            code="invalid_image_observed_text",
            message="Image inspection evidence requires the non-empty text that was actually observed.",
            path="image_evidence.observed_text",
        )
    if not isinstance(normalized_headword, str) or normalized_headword.strip() != title:
        return Finding(
            code="image_headword_mismatch",
            message="The inspected image headword must normalize to the review item's exact headword.",
            path="image_evidence.normalized_headword",
        )
    observed_text = observed_text.strip()
    observed_form = evidence.get("observed_form")
    observed_terms = [title]
    if title not in observed_text:
        if not isinstance(observed_form, str) or not observed_form.strip() or observed_form.strip() not in observed_text:
            return Finding(
                code="image_observed_text_mismatch",
                message="The observed image text must contain the headword or an explicit observed form that normalizes to it.",
                path="image_evidence.observed_text",
            )
        observed_terms.append(observed_form.strip())

    attachment = evidence.get("attachment")
    if not isinstance(attachment, str) or not attachment:
        return Finding(
            code="missing_image_attachment",
            message="Image inspection evidence requires an exact Vault-relative attachment path.",
            path="image_evidence.attachment",
        )
    attachment_path = PurePosixPath(attachment)
    if (
        attachment_path.is_absolute()
        or ".." in attachment_path.parts
        or "\\" in attachment
        or _contains_control_character(attachment)
        or attachment_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES
    ):
        return Finding(
            code="invalid_image_attachment",
            message="Image evidence must use a safe Vault-relative path to a supported local image.",
            path=attachment,
        )
    target = root / attachment
    if not target.is_file():
        return Finding(
            code="missing_image_attachment",
            message="The inspected local image attachment does not exist.",
            path=attachment,
        )
    resolved_target = target.resolve()
    root_resolved = root.resolve()
    try:
        resolved_target.relative_to(root_resolved)
    except ValueError:
        return Finding(
            code="image_attachment_outside_vault",
            message="The inspected image attachment resolves outside the target Vault.",
            path=attachment,
        )
    attachment_relative = resolved_target.relative_to(root_resolved).as_posix()

    source_note_paths = [root / path for path in source_reads if path.endswith(".md") and (root / path).is_file()]
    if not source_note_paths:
        return Finding(
            code="missing_image_source_note",
            message="Image-backed vocabulary requires a resolved source note containing the attachment.",
            path="source_note",
        )
    embedded_sources: list[tuple[Path, str]] = []
    for source_path in source_note_paths:
        source_text = source_path.read_text(encoding="utf-8")
        vocabulary_section = _markdown_vocabulary_section(source_text)
        if vocabulary_section is None:
            continue
        embed_match = _section_embeds_attachment(root, vocabulary_section, attachment_relative)
        if isinstance(embed_match, Finding):
            return embed_match
        if embed_match:
            embedded_sources.append((source_path, vocabulary_section))
    if not embedded_sources:
        return Finding(
            code="image_attachment_not_in_source_vocab_section",
            message="The inspected attachment must be embedded inside the source note's vocabulary section.",
            path=attachment_relative,
        )
    for source_path, vocabulary_section in embedded_sources:
        explicit_text = _without_markdown_image_embeds(vocabulary_section)
        if any(term in explicit_text for term in observed_terms):
            return Finding(
                code="image_item_already_present_in_source_text",
                message="The vocabulary item already appears as text in the same source note and was not extracted again from the image.",
                path=source_path.relative_to(root).as_posix(),
            )
    return [attachment_relative]


def _markdown_vocabulary_section(text: str) -> str | None:
    match = re.search(r"(?m)^##\s+単語\s*$", text)
    if match is None:
        return None
    end = re.search(r"(?m)^#{1,2}\s+.+$", text[match.end() :])
    end_index = match.end() + end.start() if end is not None else len(text)
    return text[match.start() : end_index]


def _section_embeds_attachment(root: Path, section: str, attachment_relative: str) -> bool | Finding:
    targets = re.findall(r"!\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", section)
    targets.extend(re.findall(r"!\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", section))
    attachment_name = Path(attachment_relative).name
    for raw_target in targets:
        target = raw_target.strip()
        candidate = PurePosixPath(target)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in target or _contains_control_character(target):
            return Finding(
                code="invalid_image_attachment_embed",
                message="Image embeds used as inspection evidence must be safe Vault-relative paths or unique filenames.",
                path=raw_target,
            )
        if target.startswith("./"):
            target = target[2:]
        if target == attachment_relative:
            return True
        if "/" not in target and target == attachment_name:
            matches = [path for path in root.rglob(attachment_name) if path.is_file()]
            if len(matches) > 1:
                return Finding(
                    code="ambiguous_image_attachment_embed",
                    message="A pathless image embed matches more than one Vault attachment; no target was guessed.",
                    path=raw_target,
                )
            if len(matches) == 1 and matches[0].resolve() == (root / attachment_relative).resolve():
                return True
    return False


def _without_markdown_image_embeds(text: str) -> str:
    without_obsidian = re.sub(r"!\[\[[^\]]+\]\]", "", text)
    return re.sub(r"!\[[^\]]*\]\([^)]+\)", "", without_obsidian)


def _resolve_item_source_links(
    root: Path,
    paths: dict[str, str],
    item: dict[str, Any],
    *,
    target_path: str,
) -> tuple[list[str], list[str]] | Finding:
    values = _input_values(item.get("source_notes"))
    values = _merge_values(values, item.get("source_note"))
    return _resolve_required_source_links(root, paths, values, target_path=target_path)


def _resolve_required_source_links(
    root: Path,
    paths: dict[str, str],
    values: list[str],
    *,
    target_path: str,
) -> tuple[list[str], list[str]] | Finding:
    links: list[str] = []
    read_files: list[str] = []
    for raw in values:
        resolution = _resolve_vault_link(
            root,
            paths,
            raw,
            allowed_roles=SOURCE_LINK_ROLES,
            target_path=target_path,
            link_kind="source_note",
        )
        if resolution.finding is not None:
            return resolution.finding
        assert resolution.link is not None
        if resolution.link not in links:
            links.append(resolution.link)
        read_files.extend(resolution.read_files)
    return links, list(dict.fromkeys(read_files))


def _resolve_optional_relation_links(
    root: Path,
    paths: dict[str, str],
    item_type: str,
    item: dict[str, Any],
    *,
    target_path: str,
) -> tuple[dict[str, list[str]], list[str], list[Finding], list[str]]:
    relation_fields = {
        "vocab": ("confusable_with", "contrast_with"),
        "grammar": ("contrast_with",),
        "error": ("related_items",),
        "pronunciation": ("related_items",),
    }[item_type]
    resolved_by_field: dict[str, list[str]] = {}
    unresolved: list[str] = []
    warnings: list[Finding] = []
    read_files: list[str] = []
    for field_name in relation_fields:
        for raw in _input_values(item.get(field_name)):
            resolution = _resolve_vault_link(
                root,
                paths,
                raw,
                allowed_roles=RELATED_LINK_ROLES[item_type],
                target_path=target_path,
                link_kind="related_item",
            )
            read_files.extend(resolution.read_files)
            if resolution.finding is not None:
                label = _link_display_text(raw)
                if label not in unresolved:
                    unresolved.append(label)
                warnings.append(
                    Finding(
                        code="unresolved_related_item",
                        message=resolution.finding.message,
                        severity="warning",
                        path=raw,
                    )
                )
                continue
            assert resolution.link is not None
            resolved_by_field.setdefault(field_name, [])
            if resolution.link not in resolved_by_field[field_name]:
                resolved_by_field[field_name].append(resolution.link)
    return resolved_by_field, unresolved, warnings, list(dict.fromkeys(read_files))


def _resolve_vault_link(
    root: Path,
    paths: dict[str, str],
    raw: str,
    *,
    allowed_roles: tuple[str, ...],
    target_path: str,
    link_kind: str,
) -> LinkResolution:
    parsed = _parse_link_input(raw, link_kind=link_kind)
    if isinstance(parsed, Finding):
        return LinkResolution(raw=raw, finding=parsed)
    target, alias = parsed
    configured_role_roots = [str(paths[role]) for role in allowed_roles if paths.get(role)]
    if any(not _is_safe_role_root(role_root) for role_root in configured_role_roots):
        return LinkResolution(
            raw=raw,
            finding=Finding(
                code=f"invalid_{link_kind}_role",
                message=f"The configured path role for this {link_kind.replace('_', ' ')} is not Vault-relative.",
                path=raw,
            ),
        )
    role_roots = [role_root.strip("/") for role_root in configured_role_roots]
    if not role_roots:
        return LinkResolution(
            raw=raw,
            finding=Finding(
                code=f"missing_{link_kind}_role",
                message=f"No configured path role can resolve this {link_kind.replace('_', ' ')}.",
                path=raw,
            ),
        )

    candidates: list[Path] = []
    if "/" in target:
        candidate_relative = f"{target}.md"
        if not any(_path_is_within_role(candidate_relative, role_root) for role_root in role_roots):
            return LinkResolution(
                raw=raw,
                finding=Finding(
                    code=f"{link_kind}_outside_role",
                    message=f"The {link_kind.replace('_', ' ')} must stay inside an allowed path role.",
                    path=raw,
                ),
            )
        candidate = root / candidate_relative
        if candidate.is_file():
            candidates.append(candidate)
    else:
        for role_root in role_roots:
            path_root = root / role_root
            if not path_root.exists():
                continue
            candidates.extend(path for path in path_root.rglob("*.md") if path.stem == target)

    root_resolved = root.resolve()
    resolved_candidates: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            return LinkResolution(
                raw=raw,
                finding=Finding(
                    code=f"{link_kind}_outside_vault",
                    message=f"The {link_kind.replace('_', ' ')} resolves outside the target Vault.",
                    path=raw,
                ),
            )
        resolved_candidates.append(resolved)
    resolved_candidates = sorted(set(resolved_candidates))
    if not resolved_candidates:
        return LinkResolution(
            raw=raw,
            finding=Finding(
                code=f"missing_{link_kind}_target",
                message=f"The {link_kind.replace('_', ' ')} target does not exist in its allowed roles.",
                path=raw,
            ),
        )
    if len(resolved_candidates) > 1:
        return LinkResolution(
            raw=raw,
            finding=Finding(
                code=f"ambiguous_{link_kind}_target",
                message=f"The {link_kind.replace('_', ' ')} target matches more than one note; no link was guessed.",
                path=raw,
            ),
            read_files=tuple(path.relative_to(root_resolved).as_posix() for path in resolved_candidates),
        )
    resolved = resolved_candidates[0]
    relative = resolved.relative_to(root_resolved).as_posix()
    if relative == target_path:
        return LinkResolution(
            raw=raw,
            finding=Finding(
                code=f"self_referential_{link_kind}",
                message=f"A review card cannot use itself as a {link_kind.replace('_', ' ')}.",
                path=raw,
            ),
            read_files=(relative,),
        )
    link_target = relative[:-3] if relative.endswith(".md") else relative
    display = alias or Path(link_target).name
    return LinkResolution(
        raw=raw,
        link=f"[[{link_target}|{display}]]",
        read_files=(relative,),
    )


def _parse_link_input(raw: str, *, link_kind: str) -> tuple[str, str] | Finding:
    if _contains_control_character(raw):
        return Finding(code=f"invalid_{link_kind}_link", message="Link input cannot contain control characters.", path=raw)
    text = raw.strip()
    if not text:
        return Finding(code=f"invalid_{link_kind}_link", message="Link input cannot be blank.", path=raw)
    if text.startswith("![["):
        return Finding(code=f"invalid_{link_kind}_link", message="Embeds are not accepted as review-card links.", path=raw)
    if text.startswith("[["):
        if not text.endswith("]]" ) or text.count("[[") != 1 or text.count("]]" ) != 1:
            return Finding(code=f"invalid_{link_kind}_link", message="Wikilink syntax is malformed.", path=raw)
        inner = text[2:-2]
        target, separator, alias = inner.partition("|")
        if separator and "|" in alias:
            return Finding(code=f"invalid_{link_kind}_link", message="Wikilink contains more than one alias separator.", path=raw)
    else:
        if "[[" in text or "]]" in text or "|" in text:
            return Finding(code=f"invalid_{link_kind}_link", message="Link syntax is malformed.", path=raw)
        target, alias = text, ""
    target = target.strip()
    alias = alias.strip()
    if target.endswith(".md"):
        target = target[:-3]
    candidate = PurePosixPath(target)
    if (
        not target
        or candidate.is_absolute()
        or ".." in candidate.parts
        or any(character in target for character in ("#", "^", "[", "]", "%"))
    ):
        return Finding(code=f"invalid_{link_kind}_link", message="Link target is not a safe Vault-relative note path.", path=raw)
    if alias and any(character in alias for character in ("[", "]", "|")):
        return Finding(code=f"invalid_{link_kind}_link", message="Link alias contains reserved wikilink characters.", path=raw)
    return target.strip("/"), alias


def _link_display_text(raw: str) -> str:
    parsed = _parse_link_input(raw, link_kind="related_item")
    if isinstance(parsed, Finding):
        return raw.strip()
    target, alias = parsed
    return alias or Path(target).name


def _target_context_errors(root: Path, capability_id: str) -> tuple[list[Finding], list[str]]:
    context_path = root / ".lingotrace" / "vault-context.json"
    if not context_path.is_file():
        return [
            Finding(
                code="missing_vault_context",
                message="Target Vault context is required before workflow preview.",
                path=".lingotrace/vault-context.json",
            )
        ], []

    read_files = [".lingotrace/vault-context.json"]
    context = json.loads(context_path.read_text(encoding="utf-8"))
    errors: list[Finding] = []
    expected = {
        "target_language": "ja",
        "explanation_language": "zh",
        "language_pack": "lingo-japanese",
        "language_pack_version": "0.1.0",
    }
    for field, value in expected.items():
        if context.get(field) != value:
            errors.append(
                Finding(
                    code="vault_context_mismatch",
                    message=f"Target Vault context has unexpected {field}.",
                    path=".lingotrace/vault-context.json",
                )
            )
    if capability_id not in context.get("enabled_capabilities", []):
        errors.append(
            Finding(
                code="capability_not_enabled",
                message=f"Capability is not enabled in target Vault context: {capability_id}.",
                path=".lingotrace/vault-context.json",
            )
        )
    return errors, read_files


def _path_roles(root: Path) -> dict[str, str]:
    path_config = json.loads((root / ".lingotrace" / "paths.json").read_text(encoding="utf-8"))
    return {
        str(entry["role"]): str(entry["relative_path"])
        for entry in path_config.get("path_roles", [])
        if isinstance(entry, dict) and "role" in entry and "relative_path" in entry
    }


def _cards_for_roles(root: Path, paths: dict[str, str], roles: tuple[str, ...]) -> list[tuple[Path, dict[str, Any]]]:
    cards: list[tuple[Path, dict[str, Any]]] = []
    seen: set[Path] = set()
    for role in roles:
        relative_root = paths.get(role)
        if not relative_root:
            continue
        path_root = root / relative_root
        if not path_root.exists():
            continue
        for card_path in sorted(path_root.rglob("*.md")):
            if card_path in seen:
                continue
            seen.add(card_path)
            cards.append((card_path, _frontmatter(card_path)))
    return cards


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}

    return _parse_frontmatter_fields(parts[1])


def _replace_frontmatter_fields(text: str, updates: dict[str, Any]) -> str:
    if not text.startswith("---\n"):
        return text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return text
    frontmatter = parts[1].splitlines()
    seen: set[str] = set()
    updated_lines: list[str] = []
    skip_list_items = False
    for line in frontmatter:
        if skip_list_items:
            if line.startswith(" ") or line.startswith("- ") or not line:
                continue
            else:
                skip_list_items = False
        if ":" not in line or line.startswith(" ") or line.startswith("- "):
            updated_lines.append(line)
            continue
        key, _ = line.split(":", 1)
        clean_key = key.strip()
        if clean_key in updates:
            updated_lines.extend(_frontmatter_lines(clean_key, updates[clean_key]))
            seen.add(clean_key)
            skip_list_items = True
        else:
            updated_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            updated_lines.extend(_frontmatter_lines(key, value))
    return "---\n" + "\n".join(updated_lines) + "\n---\n" + parts[2]
