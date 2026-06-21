from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from lingotrace.core.mutations import FileMutation, run_file_mutations
from lingotrace.core.reports import CommandReport, Finding
from lingotrace.packs.japanese.validators import validate_review_materials, validate_review_rollover


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
    "base_vocab_root",
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
    mutation = _artifact_mutation(input_artifact, action="write_listening_note", reason="prepared listening artifact")
    if isinstance(mutation, Finding):
        return _workflow_error("listening_notes-workflow", mode, mutation.code, mutation.message, mutation.path)
    return _run_mutations(vault_root, "listening_notes", [mutation], mode)


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
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_materials")
    root = Path(vault_root)
    errors, read_files = _target_context_errors(root, "review_materials")
    if errors:
        return _workflow_report("review_materials-workflow", mode, errors=errors, read_files=read_files)

    if card is not None:
        mutation = _review_card_mutation(card)
        if isinstance(mutation, Finding):
            return _workflow_error("review_materials-workflow", mode, mutation.code, mutation.message, mutation.path)
        return _run_mutations(root, "review_materials", [mutation], mode)
    if mode == "apply":
        return _workflow_error(
            "review_materials-workflow",
            mode,
            "missing_review_material_input",
            "review_materials apply mode requires a card payload.",
        )

    paths = _path_roles(root)
    read_files.append(".lingotrace/paths.json")
    for card_path, fields in _cards_for_roles(root, paths, REVIEW_MATERIAL_ROLES):
        read_files.append(card_path.relative_to(root).as_posix())
        validation = validate_review_materials(fields)
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
        if fields.get("status") != "active" or fields.get("done_today") != "true":
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
        next_stage, interval_days = STAGE_ADVANCEMENT[review_stage]
        next_review = "" if next_stage == "mastered" else (rollover_date + dt.timedelta(days=interval_days)).isoformat()
        updates = {
            "done_today": "false",
            "review_stage": next_stage,
            "next_review": next_review,
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
                "from_next_review": str(fields.get("next_review", "")),
                "to_next_review": next_review,
                "done_today": False,
            }
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


def _review_card_mutation(card: dict[str, Any]) -> FileMutation | Finding:
    path = card.get("path")
    fields = card.get("fields")
    body = card.get("body")
    if not isinstance(path, str) or not path.endswith(".md"):
        return Finding(code="invalid_review_card_path", message="Review card path must be a Vault-relative Markdown path.", path="path")
    if not isinstance(fields, dict):
        return Finding(code="invalid_review_card_fields", message="Review card fields must be an object.", path=path)
    validation = validate_review_materials(fields)
    if not validation.accepted:
        return validation.errors[0]
    content = _render_markdown(fields, str(body or ""))
    return FileMutation(path=path, content=content, action="write_review_material", reason="accepted review material card")


def _render_markdown(fields: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {_format_frontmatter_value(value)}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


def _format_frontmatter_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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


def _cards_for_roles(root: Path, paths: dict[str, str], roles: tuple[str, ...]) -> list[tuple[Path, dict[str, str]]]:
    cards: list[tuple[Path, dict[str, str]]] = []
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


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}

    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line or line.startswith(" ") or line.startswith("- ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _replace_frontmatter_fields(text: str, updates: dict[str, str]) -> str:
    if not text.startswith("---\n"):
        return text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return text
    frontmatter = parts[1].splitlines()
    seen: set[str] = set()
    updated_lines: list[str] = []
    for line in frontmatter:
        if ":" not in line or line.startswith(" ") or line.startswith("- "):
            updated_lines.append(line)
            continue
        key, _ = line.split(":", 1)
        clean_key = key.strip()
        if clean_key in updates:
            updated_lines.append(f"{clean_key}: {updates[clean_key]}")
            seen.add(clean_key)
        else:
            updated_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            updated_lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(updated_lines) + "\n---\n" + parts[2]
