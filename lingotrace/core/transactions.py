from __future__ import annotations

from dataclasses import dataclass

from .capabilities import CapabilityDecision
from .reports import CommandReport, Finding


@dataclass(frozen=True)
class WritePlanEntry:
    path: str
    action: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "action": self.action,
            "reason": self.reason,
        }


class WriteTransactionGuard:
    def __init__(self, capability_decision: CapabilityDecision):
        self._decision = capability_decision

    def preview(self, entries: list[WritePlanEntry] | tuple[WritePlanEntry, ...]) -> CommandReport:
        errors = self._errors()
        return CommandReport(
            command="write-transaction",
            mode="dry-run",
            exit_code=1 if errors else 0,
            errors=errors,
            planned_writes=[entry.to_dict() for entry in entries],
        )

    def apply(self, entries: list[WritePlanEntry] | tuple[WritePlanEntry, ...]) -> CommandReport:
        errors = self._errors()
        if errors:
            return CommandReport(
                command="write-transaction",
                mode="write",
                exit_code=1,
                errors=errors,
                blocked_files=[entry.path for entry in entries],
            )

        return CommandReport(
            command="write-transaction",
            mode="write",
            changed_files=[entry.path for entry in entries],
        )

    def _errors(self) -> list[Finding]:
        if self._decision.accepted:
            return []
        return list(self._decision.findings)
