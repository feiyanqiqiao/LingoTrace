from __future__ import annotations

import os
import shutil
import tempfile
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
    content: str | bytes | None
    action: str
    reason: str
    source_path: str | Path | None = None

    def to_write_plan_entry(self) -> WritePlanEntry:
        return WritePlanEntry(path=self.path, action=self.action, reason=self.reason)

    def validate_source(self) -> Finding | None:
        has_content = self.content is not None
        has_source = self.source_path is not None
        if has_content == has_source:
            return Finding(
                code="invalid_mutation_source",
                message="File mutation requires exactly one of content or source_path.",
                path=self.path,
            )
        if has_source:
            source = Path(self.source_path or "")
            if not source.is_file():
                return Finding(
                    code="mutation_source_missing",
                    message="File mutation source_path must point to an existing file.",
                    path=self.path,
                )
        return None


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

    changed_files = _apply_atomically(root, mutations)

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
        source_error = mutation.validate_source()
        if source_error is not None:
            errors.append(source_error)
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


def _apply_atomically(root: Path, mutations: list[FileMutation] | tuple[FileMutation, ...]) -> list[str]:
    """Stage every mutation before replacing targets and roll back on replacement failure."""

    staged: list[tuple[FileMutation, Path, Path]] = []
    backups: list[tuple[Path, Path | None]] = []
    try:
        for mutation in mutations:
            target = root / mutation.path
            target.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".lingotrace-stage", dir=target.parent)
            os.close(handle)
            temp_path = Path(temp_name)
            if mutation.source_path is not None:
                shutil.copy2(Path(mutation.source_path), temp_path)
            elif isinstance(mutation.content, bytes):
                temp_path.write_bytes(mutation.content)
            else:
                temp_path.write_text(str(mutation.content), encoding="utf-8")
            staged.append((mutation, target, temp_path))

        for _mutation, target, temp_path in staged:
            backup_path: Path | None = None
            if target.exists():
                handle, backup_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".lingotrace-backup", dir=target.parent)
                os.close(handle)
                backup_path = Path(backup_name)
                backup_path.unlink()
                os.replace(target, backup_path)
            backups.append((target, backup_path))
            os.replace(temp_path, target)

        for _target, backup_path in backups:
            if backup_path is not None:
                backup_path.unlink(missing_ok=True)
        return [mutation.path for mutation in mutations]
    except Exception:
        for target, backup_path in reversed(backups):
            if target.exists():
                target.unlink()
            if backup_path is not None and backup_path.exists():
                os.replace(backup_path, target)
        raise
    finally:
        for _mutation, _target, temp_path in staged:
            temp_path.unlink(missing_ok=True)
        for _target, backup_path in backups:
            if backup_path is not None:
                backup_path.unlink(missing_ok=True)
