from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.packs.japanese.validators import validate_review_materials, validate_review_rollover


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


def listening_notes() -> CommandReport:
    return _not_implemented("listening_notes")


def source_notes() -> CommandReport:
    return _not_implemented("source_notes")


def review_materials(vault_root: str | Path | None = None) -> CommandReport:
    if vault_root is None:
        return _not_implemented("review_materials")
    root = Path(vault_root)
    errors, read_files = _target_context_errors(root, "review_materials")
    if errors:
        return _preview_report("review_materials-workflow", errors=errors, read_files=read_files)

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


def speaking_cards() -> CommandReport:
    return _not_implemented("speaking_cards")


def review_rollover(vault_root: str | Path | None = None, run_date: str | None = None) -> CommandReport:
    if vault_root is None:
        return _not_implemented("review_rollover")
    root = Path(vault_root)
    errors, read_files = _target_context_errors(root, "review_rollover")
    if errors:
        return _preview_report("review_rollover-workflow", errors=errors, read_files=read_files)

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

    return _preview_report(
        "review_rollover-workflow",
        errors=errors,
        read_files=read_files,
        planned_writes=planned_writes,
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

def _not_implemented(capability_id: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="dry-run",
        exit_code=1,
        errors=[
            Finding(
                code="workflow_not_implemented",
                message=f"{capability_id} is declared by the Japanese pack but not implemented in PR 2.",
            )
        ],
    )
