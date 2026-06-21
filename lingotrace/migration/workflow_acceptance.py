from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lingotrace.core.reports import CommandReport, Finding


JAPANESE_WORKFLOW_CAPABILITIES = [
    "listening_notes",
    "source_notes",
    "review_materials",
    "speaking_cards",
    "review_rollover",
]


def evaluate_japanese_workflow_acceptance(target_vault: str | Path) -> CommandReport:
    root = Path(target_vault)
    markdown_files = _markdown_files(root)
    texts = [(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")) for path in markdown_files]

    capabilities = {
        "listening_notes": _capability_result(texts, _is_listening_note),
        "source_notes": _capability_result(texts, _is_source_note),
        "review_materials": _capability_result(texts, _is_review_material),
        "speaking_cards": _capability_result(texts, _is_speaking_card),
        "review_rollover": _capability_result(texts, _is_review_rollover),
    }
    errors = [
        Finding(
            code="workflow_acceptance_missing",
            message="Target Vault is missing accepted synthetic evidence for this workflow.",
            path=capability_id,
        )
        for capability_id in JAPANESE_WORKFLOW_CAPABILITIES
        if not capabilities[capability_id]["accepted"]
    ]
    workflow_report = {
        "capabilities": capabilities,
        "accepted": not errors,
    }

    return CommandReport(
        command="migration-workflow-acceptance",
        mode="dry-run",
        exit_code=1 if errors else 0,
        errors=errors,
        read_files=[relative_path for relative_path, _ in texts],
        planned_writes=[
            {
                "path": "workflow_acceptance_report",
                "action": "record_workflow_acceptance",
                "workflow_acceptance": workflow_report,
            }
        ],
        blocked_files=[finding.path for finding in errors if finding.path is not None],
    )


def _capability_result(
    texts: list[tuple[str, str]], predicate: Callable[[str, str], bool]
) -> dict[str, object]:
    evidence = [relative_path for relative_path, text in texts if predicate(relative_path, text)]
    return {
        "accepted": bool(evidence),
        "evidence": evidence,
    }


def _markdown_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def _is_listening_note(relative_path: str, text: str) -> bool:
    return relative_path.startswith("listening/") and "track: listening" in text and "listening_mode:" in text


def _is_source_note(relative_path: str, text: str) -> bool:
    return relative_path.startswith("sources/") and ("track: source_note" in text or "source_url:" in text)


def _is_review_material(relative_path: str, text: str) -> bool:
    return relative_path.startswith("review/") and "review_stage:" in text and "next_review:" in text


def _is_speaking_card(relative_path: str, text: str) -> bool:
    return relative_path.startswith("speaking/cards/") and "card_type: speaking" in text and "reviewed: true" in text


def _is_review_rollover(relative_path: str, text: str) -> bool:
    return relative_path.startswith("daily/") and (
        "track: daily_review" in text or "review_rollover_checked: true" in text
    )
