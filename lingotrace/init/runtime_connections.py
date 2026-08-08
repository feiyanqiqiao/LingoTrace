from __future__ import annotations

import json
import platform as platform_module
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from lingotrace.core.context import load_vault_context
from lingotrace.core.reports import CommandReport, Finding


RUNTIME_CONNECTION_SCHEMA_VERSION = 1
RUNTIME_CONNECTION_DIRECTORY = ".lingotrace/runtime-connections"
PLATFORM_ALIASES = {
    "darwin": "macos",
    "mac": "macos",
    "macos": "macos",
    "linux": "linux",
    "windows": "windows",
    "win32": "windows",
}


def current_platform(platform_name: str | None = None) -> str:
    raw = platform_name or platform_module.system()
    normalized = PLATFORM_ALIASES.get(raw.strip().lower())
    if normalized is None:
        raise ValueError(f"unsupported_platform: {raw}")
    return normalized


def runtime_connection_relative_path(platform_name: str | None = None) -> str:
    return f"{RUNTIME_CONNECTION_DIRECTORY}/{current_platform(platform_name)}.json"


def default_runtime_connection(runtime_root: str | Path, platform_name: str | None = None) -> dict[str, Any]:
    platform_id = current_platform(platform_name)
    return {
        "runtime_connection_schema_version": RUNTIME_CONNECTION_SCHEMA_VERSION,
        "platform": platform_id,
        "connections": [
            {
                "runtime_root": str(runtime_root),
                "source": "vault-initialization",
            }
        ],
    }


def register_runtime_connection(
    vault_root: str | Path,
    runtime_root: str | Path,
    *,
    platform_name: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if mode not in {"preview", "apply"}:
        raise ValueError(f"unsupported_mode: {mode}")

    vault = Path(vault_root)
    platform_id = current_platform(platform_name)
    relative_path = runtime_connection_relative_path(platform_id)
    connection_path = vault / relative_path
    runtime_value = str(runtime_root)
    findings: list[Finding] = []

    if not _is_absolute_for_platform(runtime_value, platform_id):
        findings.append(
            Finding(
                code="runtime_root_not_absolute",
                message="LingoTrace runtime root must be an absolute path for the selected platform.",
                path=runtime_value,
            )
        )

    if platform_id == current_platform():
        findings.extend(_runtime_root_findings(Path(runtime_value)))

    existing: dict[str, Any] | None = None
    read_files: list[str] = []
    if connection_path.exists():
        read_files.append(relative_path)
        existing, load_findings = _load_connection_file(connection_path, platform_id)
        findings.extend(load_findings)

    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        return CommandReport(
            command="connect-runtime",
            mode=mode,
            exit_code=1,
            errors=errors,
            warnings=[finding for finding in findings if finding.severity == "warning"],
            read_files=read_files,
            blocked_files=[relative_path] if connection_path.exists() else [],
        )

    if existing is None:
        content = default_runtime_connection(runtime_value, platform_id)
        already_registered = False
    else:
        content = existing
        connections = content["connections"]
        already_registered = any(entry["runtime_root"] == runtime_value for entry in connections)
        if not already_registered:
            connections.append({"runtime_root": runtime_value, "source": "user-confirmed"})

    action = "no_change" if already_registered else ("update_json" if existing else "write_json")
    report = CommandReport(
        command="connect-runtime",
        mode=mode,
        read_files=read_files,
        planned_writes=[
            {
                "path": relative_path,
                "action": action,
                "artifact_class": "vault-local-runtime-connection",
                "reason": f"LingoTrace runtime candidates for {platform_id}",
                "content": content,
            }
        ],
        skipped_files=[relative_path] if already_registered else [],
    )
    if mode == "preview" or already_registered:
        return report

    _write_json_atomic(connection_path, content)
    report.changed_files = [relative_path]
    return report


def resolve_runtime_connection(
    vault_root: str | Path,
    *,
    platform_name: str | None = None,
) -> CommandReport:
    vault = Path(vault_root)
    platform_id = current_platform(platform_name)
    relative_path = runtime_connection_relative_path(platform_id)
    connection_path = vault / relative_path

    if not connection_path.exists():
        return _runtime_required_report(platform_id, relative_path, "No connection file exists for this platform.")

    content, findings = _load_connection_file(connection_path, platform_id)
    errors = [finding for finding in findings if finding.severity == "error"]
    if content is None or errors:
        return CommandReport(
            command="resolve-runtime",
            mode="check",
            exit_code=1,
            errors=errors,
            warnings=[finding for finding in findings if finding.severity == "warning"],
            read_files=[relative_path],
        )

    context_result = load_vault_context(vault)
    if context_result.context is None:
        return CommandReport(
            command="resolve-runtime",
            mode="check",
            exit_code=1,
            errors=context_result.report.errors,
            warnings=context_result.report.warnings,
            read_files=[relative_path, *context_result.report.read_files],
        )

    try:
        pack_directory = _pack_directory(context_result.context.language_pack)
    except ValueError as exc:
        return CommandReport(
            command="resolve-runtime",
            mode="check",
            exit_code=1,
            errors=[
                Finding(
                    code="unsupported_language_pack_id",
                    message=str(exc),
                    path=".lingotrace/vault-context.json",
                )
            ],
            read_files=[relative_path, *context_result.report.read_files],
        )
    stale_candidates: list[str] = []
    for entry in content["connections"]:
        runtime_root = Path(entry["runtime_root"])
        skill = runtime_root / "lingotrace" / "packs" / pack_directory / "agent_skills" / "SKILL.md"
        if (runtime_root / "lingotrace" / "__init__.py").is_file() and skill.is_file():
            return CommandReport(
                command="resolve-runtime",
                mode="check",
                read_files=[relative_path, *context_result.report.read_files],
                warnings=[finding for finding in findings if finding.severity == "warning"],
                artifacts={
                    "runtime_root": str(runtime_root),
                    "agent_skill": str(skill),
                },
            )
        stale_candidates.append(str(runtime_root))

    message = (
        "Configured runtime paths are unavailable on this device. Ask the user for the local LingoTrace runtime "
        "root, validate it, and append it to the current platform connection file."
    )
    return CommandReport(
        command="resolve-runtime",
        mode="check",
        exit_code=1,
        errors=[Finding(code="runtime_connection_unavailable", message=message, path=relative_path)],
        read_files=[relative_path, *context_result.report.read_files],
        artifacts={"unavailable_runtime_roots": json.dumps(stale_candidates, ensure_ascii=False)},
    )


def _runtime_required_report(platform_id: str, relative_path: str, reason: str) -> CommandReport:
    message = (
        f"{reason} Ask the user for the LingoTrace runtime root on {platform_id}, validate it, and save it to "
        f"{relative_path}. Do not modify connection files for other platforms."
    )
    return CommandReport(
        command="resolve-runtime",
        mode="check",
        exit_code=1,
        errors=[Finding(code="runtime_connection_required", message=message, path=relative_path)],
    )


def _load_connection_file(path: Path, expected_platform: str) -> tuple[dict[str, Any] | None, list[Finding]]:
    findings: list[Finding] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [Finding(code="invalid_runtime_connection_json", message=str(exc), path=str(path))]

    if not isinstance(payload, dict):
        return None, [
            Finding(
                code="invalid_runtime_connection_shape",
                message="Runtime connection file must be a JSON object.",
                path=str(path),
            )
        ]
    if payload.get("runtime_connection_schema_version") != RUNTIME_CONNECTION_SCHEMA_VERSION:
        findings.append(
            Finding(
                code="unsupported_runtime_connection_schema",
                message="Unsupported runtime connection schema version.",
                path=str(path),
            )
        )
    if payload.get("platform") != expected_platform:
        findings.append(
            Finding(
                code="runtime_connection_platform_mismatch",
                message=f"Expected platform {expected_platform}.",
                path=str(path),
            )
        )

    connections = payload.get("connections")
    if not isinstance(connections, list):
        findings.append(
            Finding(code="invalid_runtime_connections", message="connections must be a list.", path=str(path))
        )
        return None, findings

    normalized_connections: list[dict[str, str]] = []
    for entry in connections:
        if not isinstance(entry, dict) or not isinstance(entry.get("runtime_root"), str) or not entry["runtime_root"]:
            findings.append(
                Finding(
                    code="invalid_runtime_connection",
                    message="Each runtime connection needs a non-empty runtime_root.",
                    path=str(path),
                )
            )
            continue
        if not _is_absolute_for_platform(entry["runtime_root"], expected_platform):
            findings.append(
                Finding(
                    code="runtime_root_not_absolute",
                    message="Saved runtime root must be absolute for its platform.",
                    path=entry["runtime_root"],
                )
            )
            continue
        normalized_connections.append(
            {
                "runtime_root": entry["runtime_root"],
                "source": str(entry.get("source") or "user-confirmed"),
            }
        )

    if not normalized_connections:
        findings.append(
            Finding(
                code="runtime_connections_empty",
                message="At least one runtime connection is required.",
                path=str(path),
            )
        )
        return None, findings

    return {
        "runtime_connection_schema_version": RUNTIME_CONNECTION_SCHEMA_VERSION,
        "platform": expected_platform,
        "connections": normalized_connections,
    }, findings


def _runtime_root_findings(runtime_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not runtime_root.is_dir():
        findings.append(
            Finding(
                code="runtime_root_missing",
                message="LingoTrace runtime root does not exist.",
                path=str(runtime_root),
            )
        )
    elif not (runtime_root / "lingotrace" / "__init__.py").is_file():
        findings.append(
            Finding(
                code="runtime_root_invalid",
                message="Runtime root does not contain the LingoTrace package.",
                path=str(runtime_root),
            )
        )
    return findings


def _pack_directory(language_pack: str) -> str:
    if language_pack.startswith("lingo-") and len(language_pack) > len("lingo-"):
        return language_pack[len("lingo-") :]
    raise ValueError(f"unsupported_language_pack_id: {language_pack}")


def _is_absolute_for_platform(value: str, platform_id: str) -> bool:
    if platform_id == "windows":
        return PureWindowsPath(value).is_absolute()
    return PurePosixPath(value).is_absolute()


def _write_json_atomic(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
