from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .manifests import LanguagePackManifest
from .reports import CommandReport, Finding


PATH_CONFIG_RELATIVE_PATH = ".lingotrace/paths.json"


@dataclass(frozen=True)
class PathRole:
    role: str
    relative_path: str
    source: str


@dataclass(frozen=True)
class PathResolution:
    role: str
    relative_path: str
    source: str


@dataclass(frozen=True)
class PathConfigLoadResult:
    path_roles: dict[str, PathRole]
    findings: list[Finding]
    report: CommandReport


def load_path_config(vault_root: str | Path) -> PathConfigLoadResult:
    root = Path(vault_root)
    config_path = root / PATH_CONFIG_RELATIVE_PATH
    read_files = [PATH_CONFIG_RELATIVE_PATH]
    findings: list[Finding] = []

    if not config_path.exists():
        findings.append(
            Finding(
                code="path_config_missing",
                message="Vault path config is missing; language-pack defaults will be used.",
                severity="warning",
                path=PATH_CONFIG_RELATIVE_PATH,
            )
        )
        return _result({}, findings, read_files)

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                code="invalid_path_config_json",
                message=f"Path config JSON is invalid: {exc.msg}.",
                path=PATH_CONFIG_RELATIVE_PATH,
            )
        )
        return _result({}, findings, read_files)

    path_roles = _parse_path_roles(payload, findings)
    if findings:
        return _result({}, findings, read_files)
    return _result(path_roles, findings, read_files)


def resolve_path_roles(
    manifest: LanguagePackManifest,
    path_roles: dict[str, PathRole],
) -> dict[str, PathResolution]:
    unknown_roles = sorted(set(path_roles) - set(manifest.default_path_roles))
    if unknown_roles:
        raise ValueError(f"unknown_path_role: {unknown_roles[0]}")

    resolved: dict[str, PathResolution] = {}
    for role in sorted(manifest.default_path_roles):
        if role in path_roles:
            item = path_roles[role]
            resolved[role] = PathResolution(role=role, relative_path=item.relative_path, source=item.source)
        else:
            resolved[role] = PathResolution(
                role=role,
                relative_path=manifest.default_path_roles[role],
                source="language_pack_default",
            )
    return resolved


def _parse_path_roles(payload: Any, findings: list[Finding]) -> dict[str, PathRole]:
    if not isinstance(payload, dict) or not isinstance(payload.get("path_roles"), list):
        findings.append(Finding(code="invalid_path_config_shape", message="Path config must contain path_roles list."))
        return {}

    path_roles: dict[str, PathRole] = {}
    for raw in payload["path_roles"]:
        if not isinstance(raw, dict):
            findings.append(Finding(code="invalid_path_role_shape", message="Path role entry must be an object."))
            continue
        role = str(raw.get("role", ""))
        relative_path = str(raw.get("relative_path", ""))
        source = str(raw.get("source", ""))
        if _is_unsafe_relative_path(relative_path):
            findings.append(Finding(code="unsafe_relative_path", message=f"Unsafe relative path: {relative_path}."))
            continue
        path_roles[role] = PathRole(role=role, relative_path=relative_path, source=source)
    return path_roles


def _is_unsafe_relative_path(relative_path: str) -> bool:
    path = PurePosixPath(relative_path)
    return path.is_absolute() or ".." in path.parts or relative_path == ""


def _result(path_roles: dict[str, PathRole], findings: list[Finding], read_files: list[str]) -> PathConfigLoadResult:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return PathConfigLoadResult(
        path_roles=path_roles,
        findings=findings,
        report=CommandReport(
            command="validate-paths",
            mode="check",
            exit_code=1 if errors else 0,
            errors=errors,
            warnings=warnings,
            read_files=read_files,
        ),
    )
