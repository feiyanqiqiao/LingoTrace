from __future__ import annotations

import datetime as dt
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from lingotrace.core.mutations import FileMutation, run_file_mutations
from lingotrace.core.reports import CommandReport, Finding
from lingotrace.core.review_lifecycle import ACTIVE_REVIEW_STAGES, REVIEW_STATUSES, validate_review_lifecycle


CardScanner = Callable[[Path, dict[str, str], tuple[str, ...]], Iterable[tuple[Path, dict[str, Any]]]]
FrontmatterBodyReader = Callable[[str], tuple[dict[str, Any], str]]
FrontmatterReplacer = Callable[..., str]
MarkdownRenderer = Callable[[dict[str, Any], str], str]
MERGE_LIST_FIELDS = {
    "source_notes",
    "tags",
    "collocations",
    "confusable_with",
    "contrast_with",
    "related_items",
    "kanji_diff_pairs",
    "usage_scenes",
}


def review_lifecycle_migration(
    *,
    vault_root: str | Path,
    manifest_path: str | Path,
    paths: dict[str, str],
    roles: tuple[str, ...],
    scanner: CardScanner,
    replace_frontmatter: FrontmatterReplacer,
    change_date: str,
    existing_update_confirmed: bool,
    mode: str,
) -> CommandReport:
    root = Path(vault_root)
    date_error = _date_error(change_date)
    if date_error:
        return _report("review-lifecycle-migration", mode, errors=[date_error])
    if mode == "apply" and not existing_update_confirmed:
        return _report(
            "review-lifecycle-migration",
            mode,
            errors=[Finding(code="migration_confirmation_required", message="Applying lifecycle migration requires existing_update_confirmed: true.")],
        )

    mutations: list[FileMutation] = []
    plans: list[dict[str, Any]] = []
    errors: list[Finding] = []
    read_files: list[str] = []
    for path, fields in scanner(root, paths, roles):
        relative = path.relative_to(root).as_posix()
        candidate = _legacy_lifecycle_candidate(fields, change_date=change_date)
        if candidate is None:
            continue
        updates, reason = candidate
        proposed = dict(fields)
        proposed.pop("status", None)
        proposed.pop("review_enabled", None)
        proposed.update(updates)
        lifecycle_errors = validate_review_lifecycle(proposed)
        if lifecycle_errors:
            errors.extend(
                Finding(code=finding.code, message=finding.message, path=relative) for finding in lifecycle_errors
            )
            continue
        changed_fields = {
            key: {"before": fields.get(key), "after": proposed.get(key)}
            for key in sorted(set(fields) | set(proposed))
            if fields.get(key) != proposed.get(key) and key in {"status", "review_enabled", "review_status", "done_today", "review_stage", "next_review", "last_reviewed"}
        }
        if not changed_fields:
            continue
        text = path.read_text(encoding="utf-8")
        mutations.append(
            FileMutation(
                path=relative,
                content=replace_frontmatter(text, updates, remove_fields=("status", "review_enabled")),
                action="migrate_review_lifecycle",
                reason=reason,
            )
        )
        plans.append(
            {
                "path": relative,
                "action": "migrate_review_lifecycle",
                "reason": reason,
                "changes": changed_fields,
            }
        )
        read_files.append(relative)
    if errors:
        return _report(
            "review-lifecycle-migration",
            mode,
            errors=errors,
            read_files=read_files,
            planned_writes=plans,
            blocked_files=[plan["path"] for plan in plans],
        )
    return _run(
        root=root,
        manifest_path=manifest_path,
        capability_id="review_lifecycle_migration",
        command="review-lifecycle-migration",
        mutations=mutations,
        plans=plans,
        read_files=read_files,
        mode=mode,
    )


def vocab_consolidation(
    *,
    vault_root: str | Path,
    manifest_path: str | Path,
    paths: dict[str, str],
    scanner: CardScanner,
    read_frontmatter_body: FrontmatterBodyReader,
    render_markdown: MarkdownRenderer,
    change_date: str,
    existing_update_confirmed: bool,
    body_conflict_resolutions: dict[str, str] | None,
    mode: str,
) -> CommandReport:
    root = Path(vault_root)
    date_error = _date_error(change_date)
    if date_error:
        return _report("vocab-consolidation", mode, errors=[date_error])
    if mode == "apply" and not existing_update_confirmed:
        return _report(
            "vocab-consolidation",
            mode,
            errors=[Finding(code="consolidation_confirmation_required", message="Applying vocabulary consolidation requires existing_update_confirmed: true.")],
        )
    focus_root = paths.get("focus_vocab_root")
    base_root = paths.get("base_vocab_root")
    if not focus_root or not base_root:
        return _report(
            "vocab-consolidation",
            mode,
            errors=[Finding(code="missing_path_role", message="Vocabulary consolidation requires focus_vocab_root and base_vocab_root.")],
        )
    resolution_error = _body_conflict_resolution_error(body_conflict_resolutions, base_root=base_root)
    if resolution_error:
        return _report("vocab-consolidation", mode, errors=[resolution_error])
    resolutions = dict(body_conflict_resolutions or {})
    used_resolutions: set[str] = set()

    try:
        focus = _vocab_by_key(root, paths, ("focus_vocab_root",), scanner)
        base = _vocab_by_key(root, paths, ("base_vocab_root",), scanner)
    except ValueError as exc:
        duplicate_key = str(exc).partition(":")[2]
        return _report(
            "vocab-consolidation",
            mode,
            errors=[Finding(code="duplicate_vocab_key", message="A vocabulary directory contains duplicate canonical headwords.", path=duplicate_key)],
        )
    errors: list[Finding] = []
    mutations: list[FileMutation] = []
    plans: list[dict[str, Any]] = []
    read_files: list[str] = []
    occupied_targets = {path.relative_to(root).as_posix() for path, _ in focus.values()}

    for key in sorted(base):
        base_path, base_fields = base[key]
        base_relative = base_path.relative_to(root).as_posix()
        read_files.append(base_relative)
        if base_fields.get("review_status") == "archived":
            continue
        base_text = base_path.read_text(encoding="utf-8")
        parsed_base_fields, base_body = read_frontmatter_body(base_text)
        if key in focus:
            focus_path, _ = focus[key]
            focus_relative = focus_path.relative_to(root).as_posix()
            read_files.append(focus_relative)
            focus_text = focus_path.read_text(encoding="utf-8")
            focus_fields, focus_body = read_frontmatter_body(focus_text)
            if _manual_body_conflict(focus_body, base_body):
                if resolutions.get(base_relative) == "focus":
                    used_resolutions.add(base_relative)
                else:
                    errors.append(
                        Finding(
                            code="manual_vocab_body_conflict",
                            message="Focus and base vocabulary cards contain different non-empty bodies and require manual review.",
                            path=base_relative,
                        )
                    )
                    continue
            merged = _merge_vocab_fields(focus_fields, parsed_base_fields)
            lifecycle_errors = validate_review_lifecycle(merged)
            if lifecycle_errors:
                errors.extend(Finding(code=f.code, message=f.message, path=focus_relative) for f in lifecycle_errors)
                continue
            if merged != focus_fields:
                mutations.append(
                    FileMutation(
                        path=focus_relative,
                        content=render_markdown(merged, focus_body),
                        action="merge_base_vocab_into_focus",
                        reason="focus card remains canonical and base fills only missing or mergeable fields",
                    )
                )
                plans.append({"path": focus_relative, "action": "merge_base_vocab_into_focus", "reason": "focus card is canonical"})
            archived = _archived_base_fields(parsed_base_fields, focus_relative, str(merged.get("headword") or focus_path.stem))
            archived_body = _archived_base_body(base_body, focus_relative)
            mutations.append(
                FileMutation(
                    path=base_relative,
                    content=render_markdown(archived, archived_body),
                    action="archive_legacy_base_vocab",
                    reason="legacy base card redirects to the canonical focus card",
                )
            )
            plans.append({"path": base_relative, "action": "archive_legacy_base_vocab", "canonical_path": focus_relative})
            continue

        target_relative = f"{focus_root.rstrip('/')}/{base_path.name}"
        if target_relative in occupied_targets or (root / target_relative).exists():
            errors.append(
                Finding(code="vocab_target_collision", message="A focus target path already exists for a different vocabulary key.", path=target_relative)
            )
            continue
        canonical_fields = _canonical_fields_from_base(parsed_base_fields, change_date=change_date)
        lifecycle_errors = validate_review_lifecycle(canonical_fields)
        if lifecycle_errors:
            errors.extend(Finding(code=f.code, message=f.message, path=base_relative) for f in lifecycle_errors)
            continue
        mutations.append(
            FileMutation(
                path=target_relative,
                content=render_markdown(canonical_fields, base_body),
                action="create_canonical_focus_vocab",
                reason="base-only vocabulary moves into the canonical focus directory",
            )
        )
        plans.append(
            {
                "path": target_relative,
                "action": "create_canonical_focus_vocab",
                "source_path": base_relative,
                "review_status": canonical_fields["review_status"],
            }
        )
        archived = _archived_base_fields(parsed_base_fields, target_relative, str(canonical_fields.get("headword") or base_path.stem))
        mutations.append(
            FileMutation(
                path=base_relative,
                content=render_markdown(archived, _archived_base_body(base_body, target_relative)),
                action="archive_legacy_base_vocab",
                reason="base-only card redirects to its new canonical focus card",
            )
        )
        plans.append({"path": base_relative, "action": "archive_legacy_base_vocab", "canonical_path": target_relative})
        occupied_targets.add(target_relative)

    for relative in sorted(set(resolutions) - used_resolutions):
        errors.append(
            Finding(
                code="unused_body_conflict_resolution",
                message="The confirmed focus-body resolution does not match a current manual body conflict.",
                path=relative,
            )
        )

    if errors:
        return _report(
            "vocab-consolidation",
            mode,
            errors=errors,
            read_files=list(dict.fromkeys(read_files)),
            planned_writes=plans,
            blocked_files=[plan["path"] for plan in plans],
        )
    return _run(
        root=root,
        manifest_path=manifest_path,
        capability_id="vocab_consolidation",
        command="vocab-consolidation",
        mutations=mutations,
        plans=plans,
        read_files=list(dict.fromkeys(read_files)),
        mode=mode,
    )


def _legacy_lifecycle_candidate(fields: dict[str, Any], *, change_date: str) -> tuple[dict[str, Any], str] | None:
    explicit = fields.get("review_status")
    legacy = fields.get("status")
    enabled = fields.get("review_enabled")
    if explicit is None and legacy is None and enabled is None:
        return None
    if explicit in REVIEW_STATUSES:
        target = str(explicit)
        reason = "remove legacy lifecycle aliases"
    elif explicit is not None:
        target, reason = "backlog", "normalize a legacy non-lifecycle review_status value"
    elif legacy in {"mastered", "promoted"}:
        target, reason = "mastered", "map legacy mastered or promoted state"
    elif legacy == "archived":
        target, reason = "archived", "map legacy archived state"
    else:
        stage = fields.get("review_stage")
        valid_stage = stage in ACTIVE_REVIEW_STAGES
        valid_date = _valid_date(fields.get("next_review"))
        reviewed = _valid_date(fields.get("last_reviewed")) or (valid_stage and stage != "day0")
        material_only = fields.get("track") in {"listening", "survival_speaking"} or fields.get("item_type") in {"chunk", "speaking_card"}
        scheduled_core = fields.get("item_type") in {"vocab", "grammar", "error", "pronunciation"} and valid_stage and valid_date
        if enabled is False:
            target, reason = "backlog", "preserve an explicit legacy queue opt-out"
        elif reviewed or scheduled_core or enabled is True:
            target, reason = "queued", "preserve a real legacy review schedule"
        elif material_only and stage == "day0" and not _valid_date(fields.get("last_reviewed")):
            target, reason = "backlog", "remove never-reviewed material from the automatic queue"
        else:
            target, reason = "backlog", "map unscheduled legacy material to backlog"

    updates: dict[str, Any] = {"review_status": target, "done_today": bool(fields.get("done_today")) if target == "queued" else False}
    if target == "queued":
        updates["review_stage"] = fields.get("review_stage") if fields.get("review_stage") in ACTIVE_REVIEW_STAGES else "day0"
        updates["next_review"] = fields.get("next_review") if _valid_date(fields.get("next_review")) else change_date
    elif target == "mastered":
        updates.update({"review_stage": "mastered", "next_review": "", "done_today": False})
    return updates, reason


def _vocab_by_key(
    root: Path,
    paths: dict[str, str],
    roles: tuple[str, ...],
    scanner: CardScanner,
) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path, fields in scanner(root, paths, roles):
        item_type = fields.get("item_type")
        is_legacy_vocab = item_type in (None, "") and bool(fields.get("headword"))
        if item_type != "vocab" and not is_legacy_vocab:
            continue
        key = _vocab_key(fields, path)
        if key in result:
            raise ValueError(f"duplicate_vocab_key:{key}")
        result[key] = (path, fields)
    return result


def _vocab_key(fields: dict[str, Any], path: Path) -> str:
    return unicodedata.normalize("NFKC", str(fields.get("headword") or path.stem)).strip().casefold()


def _canonical_fields_from_base(base: dict[str, Any], *, change_date: str) -> dict[str, Any]:
    fields = {key: value for key, value in base.items() if key not in {"status", "review_enabled", "canonical_card"}}
    fields["track"] = "class_review"
    fields["item_type"] = "vocab"
    legacy = base.get("status")
    stage = base.get("review_stage")
    if legacy in {"promoted", "mastered"} or base.get("review_status") == "mastered":
        fields.update({"review_status": "mastered", "review_stage": "mastered", "next_review": "", "done_today": False})
    elif stage in ACTIVE_REVIEW_STAGES and _valid_date(base.get("next_review")):
        fields.update({"review_status": "queued", "review_stage": stage, "next_review": base["next_review"], "done_today": bool(base.get("done_today"))})
    else:
        fields.update({"review_status": "backlog", "done_today": False})
        if stage not in ACTIVE_REVIEW_STAGES:
            fields["review_stage"] = ""
        if fields.get("next_review") not in (None, "") and not _valid_date(fields.get("next_review")):
            fields["next_review"] = ""
    return fields


def _merge_vocab_fields(focus: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    merged = dict(focus)
    for key, value in base.items():
        if key in {"status", "review_status", "review_stage", "next_review", "last_reviewed", "done_today", "track", "item_type", "canonical_card"}:
            continue
        if key in MERGE_LIST_FIELDS or isinstance(value, list):
            merged[key] = _merge_lists(merged.get(key), value)
        elif merged.get(key) in (None, "", []):
            merged[key] = value
    for field in ("seen_count", "error_count", "attempt_count"):
        values = [value for value in (focus.get(field), base.get(field)) if isinstance(value, int) and not isinstance(value, bool)]
        if values:
            merged[field] = max(values)
    first_seen = _date_extreme((focus.get("first_seen"), base.get("first_seen")), minimum=True)
    if first_seen:
        merged["first_seen"] = first_seen
    for field in ("last_seen", "last_reviewed"):
        value = _date_extreme((focus.get(field), base.get(field)), minimum=False)
        if value:
            merged[field] = value
    return merged


def _archived_base_fields(base: dict[str, Any], canonical_path: str, headword: str) -> dict[str, Any]:
    fields = {key: value for key, value in base.items() if key not in {"status", "review_enabled"}}
    fields.update(
        {
            "review_status": "archived",
            "done_today": False,
            "canonical_card": f"[[{Path(canonical_path).with_suffix('').as_posix()}|{headword}]]",
        }
    )
    return fields


def _archived_base_body(body: str, canonical_path: str) -> str:
    link = f"[[{Path(canonical_path).with_suffix('').as_posix()}|规范卡]]"
    notice = f"> [!info] 已迁移\n> 这张旧基础词卡已归档。后续学习请使用 {link}。"
    stripped = body.strip()
    return f"{notice}\n\n{stripped}\n" if stripped else f"{notice}\n"


def _manual_body_conflict(focus_body: str, base_body: str) -> bool:
    return bool(focus_body.strip() and base_body.strip() and focus_body.strip() != base_body.strip())


def _body_conflict_resolution_error(resolutions: Any, *, base_root: str) -> Finding | None:
    if resolutions is None:
        return None
    if not isinstance(resolutions, dict):
        return Finding(
            code="invalid_body_conflict_resolutions",
            message="body_conflict_resolutions must map exact base-card paths to 'focus'.",
        )
    prefix = f"{base_root.rstrip('/')}/"
    for relative, authority in resolutions.items():
        if not isinstance(relative, str) or not relative.startswith(prefix) or not relative.endswith(".md"):
            return Finding(
                code="invalid_body_conflict_resolution_path",
                message="Each body conflict resolution must target an exact Markdown path under base_vocab_root.",
                path=str(relative),
            )
        parts = Path(relative).parts
        if Path(relative).is_absolute() or ".." in parts or authority != "focus":
            return Finding(
                code="invalid_body_conflict_resolution",
                message="Each body conflict resolution must use an exact safe base-card path with authority 'focus'.",
                path=relative,
            )
    return None


def _merge_lists(left: Any, right: Any) -> list[Any]:
    values = left if isinstance(left, list) else ([] if left in (None, "") else [left])
    additions = right if isinstance(right, list) else ([] if right in (None, "") else [right])
    return list(dict.fromkeys([*values, *additions]))


def _date_extreme(values: Iterable[Any], *, minimum: bool) -> str | None:
    dates = sorted(str(value) for value in values if _valid_date(value))
    if not dates:
        return None
    return dates[0] if minimum else dates[-1]


def _date_error(value: str) -> Finding | None:
    return None if _valid_date(value) else Finding(code="invalid_change_date", message="change_date must use YYYY-MM-DD format.", path="change_date")


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _run(
    *,
    root: Path,
    manifest_path: str | Path,
    capability_id: str,
    command: str,
    mutations: list[FileMutation],
    plans: list[dict[str, Any]],
    read_files: list[str],
    mode: str,
) -> CommandReport:
    report = run_file_mutations(
        vault_root=root,
        manifest_path=manifest_path,
        capability_id=capability_id,
        mutations=mutations,
        mode=mode,
    )
    report.command = command
    report.read_files = list(dict.fromkeys([*read_files, *report.read_files]))
    report.planned_writes = plans
    return report


def _report(
    command: str,
    mode: str,
    *,
    errors: list[Finding],
    read_files: list[str] | None = None,
    planned_writes: list[dict[str, Any]] | None = None,
    blocked_files: list[str] | None = None,
) -> CommandReport:
    return CommandReport(
        command=command,
        mode=mode,
        exit_code=1 if errors else 0,
        errors=errors,
        read_files=read_files or [],
        planned_writes=planned_writes or [],
        blocked_files=blocked_files or [],
    )
