from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: str = "error"
    path: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.path is not None:
            result["path"] = self.path
        return result


@dataclass
class CommandReport:
    command: str
    mode: str
    exit_code: int = 0
    errors: list[Finding] | tuple[Finding, ...] = field(default_factory=list)
    warnings: list[Finding] | tuple[Finding, ...] = field(default_factory=list)
    read_files: list[str] | tuple[str, ...] = field(default_factory=list)
    planned_writes: list[dict[str, Any]] | tuple[dict[str, Any], ...] = field(default_factory=list)
    changed_files: list[str] | tuple[str, ...] = field(default_factory=list)
    skipped_files: list[str] | tuple[str, ...] = field(default_factory=list)
    blocked_files: list[str] | tuple[str, ...] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.exit_code == 0 and len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "mode": self.mode,
            "accepted": self.accepted,
            "exit_code": self.exit_code,
            "errors": [finding.to_dict() for finding in self.errors],
            "warnings": [finding.to_dict() for finding in self.warnings],
            "read_files": list(self.read_files),
            "planned_writes": [dict(item) for item in self.planned_writes],
            "changed_files": list(self.changed_files),
            "skipped_files": list(self.skipped_files),
            "blocked_files": list(self.blocked_files),
            "artifacts": dict(sorted(self.artifacts.items())),
        }
