from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .capabilities import CapabilityRegistry
from .context import load_vault_context
from .manifests import load_language_pack_manifest
from .reports import CommandReport, Finding
from .transactions import WritePlanEntry, WriteTransactionGuard


@dataclass(frozen=True)
class FileMutation:
    path: str
    content: str
    action: str
    reason: str

    def to_write_plan_entry(self) -> WritePlanEntry:
        return WritePlanEntry(path=self.path, action=self.action, reason=self.reason)


def run_file_mutations(
    *,
    vault_root: str | Path,
    manifest_path: str | Path,
    capability_id: str,
    mutations: list[FileMutation] | tuple[FileMutation, ...],
    mode: str,
) -> CommandReport:
    root = Path(vault_root)
    entries = [mutation.to_write_plan_entry() for mutation in mutations]
    blocked_files = [mutation.path for mutation in mutations]

    preflight_errors = _preflight_errors(root, manifest_path, capability_id, mutations, mode)
    if preflight_errors:
        return CommandReport(
            command="file-mutation",
            mode=mode,
            exit_code=1,
            errors=preflight_errors,
            blocked_files=blocked_files,
        )

    context_result = load_vault_context(root)
    if context_result.context is None:
        return CommandReport(
            command="file-mutation",
            mode=mode,
            exit_code=1,
            errors=context_result.report.errors,
            read_files=context_result.report.read_files,
            blocked_files=blocked_files,
        )

    manifest_result = load_language_pack_manifest(manifest_path)
    if manifest_result.manifest is None:
        return CommandReport(
            command="file-mutation",
            mode=mode,
            exit_code=1,
            errors=manifest_result.report.errors,
            read_files=[*context_result.report.read_files, *manifest_result.report.read_files],
            blocked_files=blocked_files,
        )

    decision = CapabilityRegistry(manifest_result.manifest).require(capability_id, context_result.context)
    guard = WriteTransactionGuard(decision)
    if mode == "preview":
        report = guard.preview(entries)
        report.command = "file-mutation"
        report.mode = "preview"
        report.read_files = [*context_result.report.read_files, *manifest_result.report.read_files]
        return report

    guard_report = guard.apply(entries)
    if not guard_report.accepted:
        guard_report.command = "file-mutation"
        guard_report.read_files = [*context_result.report.read_files, *manifest_result.report.read_files]
        return guard_report

    changed_files: list[str] = []
    for mutation in mutations:
        target = root / mutation.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(mutation.content, encoding="utf-8")
        changed_files.append(mutation.path)

    return CommandReport(
        command="file-mutation",
        mode="apply",
        changed_files=changed_files,
        read_files=[*context_result.report.read_files, *manifest_result.report.read_files],
    )


def _preflight_errors(
    root: Path,
    manifest_path: str | Path,
    capability_id: str,
    mutations: list[FileMutation] | tuple[FileMutation, ...],
    mode: str,
) -> list[Finding]:
    errors: list[Finding] = []
    if mode not in {"preview", "apply"}:
        errors.append(
            Finding(
                code="invalid_mutation_mode",
                message="File mutation mode must be preview or apply.",
                path="mode",
            )
        )
    if not capability_id:
        errors.append(Finding(code="missing_capability_id", message="Capability id is required."))
    if not Path(manifest_path).is_file():
        errors.append(Finding(code="manifest_missing", message="Language pack manifest is missing."))
    for mutation in mutations:
        if not _is_safe_relative_path(root, mutation.path):
            errors.append(
                Finding(
                    code="invalid_mutation_path",
                    message="File mutation paths must be Vault-relative and stay inside the target Vault.",
                    path=mutation.path,
                )
            )
            break
    return errors


def _is_safe_relative_path(root: Path, raw_path: str) -> bool:
    if not raw_path:
        return False
    candidate = PurePosixPath(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    try:
        (root / raw_path).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
