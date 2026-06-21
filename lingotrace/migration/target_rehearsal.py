from __future__ import annotations

from pathlib import Path

from lingotrace.core.reports import CommandReport
from lingotrace.init.japanese_vault import plan_japanese_vault_initialization


def plan_target_vault_rehearsal(target_vault: str | Path) -> CommandReport:
    init_report = plan_japanese_vault_initialization(target_vault)
    envelope = init_report.to_dict()

    return CommandReport(
        command="target-vault-rehearsal",
        mode="dry-run",
        exit_code=0 if init_report.accepted else 1,
        errors=list(init_report.errors),
        warnings=list(init_report.warnings),
        read_files=list(init_report.read_files),
        planned_writes=list(init_report.planned_writes),
        changed_files=[],
        skipped_files=list(init_report.skipped_files),
        blocked_files=list(envelope["blocked_files"]),
        artifacts={"rehearsal": "target-vault-rehearsal.json"},
    )
