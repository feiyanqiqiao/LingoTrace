"""English language pack workflow stubs.

All capabilities are experimental and require core context generalization
before they can run against a real English Vault. Each function returns
a missing_vault_root error when called without a vault_root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def listening_notes(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("listening_notes", "English listening transcription tools are not yet available.")


def source_notes(
    vault_root: str | Path | None = None,
    *,
    source_artifact: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("source_notes")
    return _not_yet_implemented("source_notes", mode)


def review_materials(
    vault_root: str | Path | None = None,
    *,
    card: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_materials")
    return _not_yet_implemented("review_materials", mode)


def speaking_cards(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("speaking_cards", "English speaking card validation is not yet implemented.")


def review_rollover(
    vault_root: str | Path | None = None,
    *,
    run_date: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_rollover")
    return _not_yet_implemented("review_rollover", mode)


def _missing_vault_root(capability_id: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="missing_vault_root", message="vault_root is required.")],
    )


def _unsupported(capability_id: str, reason: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="unsupported_capability", message=reason)],
    )


def _not_yet_implemented(capability_id: str, mode: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode=mode,
        exit_code=1,
        errors=[Finding(
            code="not_yet_implemented",
            message=f"{capability_id} requires core context generalization before it can run.",
        )],
    )
