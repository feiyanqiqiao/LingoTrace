from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.init.runtime_connections import current_platform, resolve_runtime_connection


LISTENKIT_CONNECTION_SCHEMA_VERSION = 1
VAULT_LISTENKIT_CONNECTION_DIRECTORY = ".lingotrace/listenkit-connections"
DEVICE_LISTENKIT_CONNECTION_RELATIVE_PATH = "connections/listenkit.json"
LINGOTRACE_DATA_HOME_ENV = "LINGOTRACE_DATA_HOME"


def listenkit_connection_relative_path(platform_name: str | None = None) -> str:
    """Return the legacy Vault-local override path for compatibility."""
    return f"{VAULT_LISTENKIT_CONNECTION_DIRECTORY}/{current_platform(platform_name)}.json"


def device_listenkit_connection_path(
    *,
    platform_name: str | None = None,
    data_home: str | Path | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    platform_id = current_platform(platform_name)
    environment = dict(os.environ if environ is None else environ)
    if data_home is not None:
        root = Path(data_home)
    elif environment.get(LINGOTRACE_DATA_HOME_ENV):
        root = Path(environment[LINGOTRACE_DATA_HOME_ENV])
    else:
        home_path = Path(home) if home is not None else Path.home()
        if platform_id == "windows":
            windows_home = PureWindowsPath(environment.get("USERPROFILE", str(home_path)))
            local_app_data = PureWindowsPath(
                environment.get("LOCALAPPDATA", str(windows_home / "AppData" / "Local"))
            )
            root = Path(str(local_app_data / "LingoTrace"))
        elif platform_id == "macos":
            root = home_path / "Library" / "Application Support" / "LingoTrace"
        else:
            xdg_data_home = Path(environment.get("XDG_DATA_HOME", str(home_path / ".local" / "share")))
            root = xdg_data_home / "lingotrace"
    return root / DEVICE_LISTENKIT_CONNECTION_RELATIVE_PATH


def recommended_listenkit_root(
    *,
    runtime_root: str | Path,
    platform_name: str | None = None,
) -> str:
    platform_id = current_platform(platform_name)
    runtime_value = str(runtime_root)
    if platform_id == "windows" or PureWindowsPath(runtime_value).is_absolute():
        root = PureWindowsPath(runtime_value).parent / "ListenKit"
    else:
        root = PurePosixPath(runtime_value).parent / "ListenKit"
    return str(root)


def default_listenkit_connection(
    listenkit_root: str | Path,
    platform_name: str | None = None,
    *,
    source: str = "user-confirmed",
) -> dict[str, Any]:
    platform_id = current_platform(platform_name)
    return {
        "listenkit_connection_schema_version": LISTENKIT_CONNECTION_SCHEMA_VERSION,
        "platform": platform_id,
        "connections": [
            {
                "listenkit_root": str(listenkit_root),
                "source": source,
            }
        ],
    }


def register_listenkit_connection(
    vault_root: str | Path | None,
    listenkit_root: str | Path,
    *,
    platform_name: str | None = None,
    scope: str = "device",
    data_home: str | Path | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if mode not in {"preview", "apply"}:
        raise ValueError(f"unsupported_mode: {mode}")
    if scope not in {"device", "vault"}:
        raise ValueError(f"unsupported_listenkit_connection_scope: {scope}")
    if scope == "vault" and vault_root is None:
        return CommandReport(
            command="connect-listenkit",
            mode=mode,
            exit_code=1,
            errors=[
                Finding(
                    code="vault_root_required_for_listenkit_override",
                    message="A Vault root is required when registering a Vault-specific ListenKit override.",
                )
            ],
            artifacts={"connection_scope": scope},
        )

    vault = Path(vault_root) if vault_root is not None else None
    platform_id = current_platform(platform_name)
    if scope == "vault":
        assert vault is not None
        relative_path = listenkit_connection_relative_path(platform_id)
        connection_path = vault / relative_path
        report_path = relative_path
        artifact_class = "vault-local-listenkit-override"
        source = "vault-override"
    else:
        connection_path = device_listenkit_connection_path(
            platform_name=platform_id,
            data_home=data_home,
            home=home,
            environ=environ,
        )
        report_path = str(connection_path)
        artifact_class = "device-local-listenkit-connection"
        source = "user-confirmed"

    listenkit_value = str(listenkit_root)
    findings: list[Finding] = []
    if not _is_absolute_for_platform(listenkit_value, platform_id):
        findings.append(
            Finding(
                code="listenkit_root_not_absolute",
                message="ListenKit root must be an absolute path for the selected platform.",
                path=listenkit_value,
            )
        )
    if platform_id == current_platform():
        findings.extend(_listenkit_root_findings(Path(listenkit_value)))
        if vault is not None and _paths_overlap(vault, Path(listenkit_value)):
            findings.append(
                Finding(
                    code="vault_listenkit_overlap",
                    message="The private Vault and ListenKit installation must be separate and must not contain each other.",
                    path=listenkit_value,
                )
            )

    existing: dict[str, Any] | None = None
    read_files: list[str] = []
    if connection_path.exists():
        read_files.append(report_path)
        existing, load_findings = _load_connection_file(connection_path, platform_id)
        findings.extend(load_findings)

    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        return CommandReport(
            command="connect-listenkit",
            mode=mode,
            exit_code=1,
            errors=errors,
            warnings=[finding for finding in findings if finding.severity == "warning"],
            read_files=read_files,
            blocked_files=[report_path] if connection_path.exists() else [],
            artifacts={"connection_scope": scope, "connection_path": report_path},
        )

    if existing is None:
        content = default_listenkit_connection(listenkit_value, platform_id, source=source)
        already_registered = False
    else:
        content = existing
        connections = content["connections"]
        already_registered = any(entry["listenkit_root"] == listenkit_value for entry in connections)
        if not already_registered:
            connections.append({"listenkit_root": listenkit_value, "source": source})

    action = "no_change" if already_registered else ("update_json" if existing else "write_json")
    report = CommandReport(
        command="connect-listenkit",
        mode=mode,
        read_files=read_files,
        planned_writes=[
            {
                "path": report_path,
                "action": action,
                "artifact_class": artifact_class,
                "reason": f"ListenKit candidates for {platform_id} ({scope} scope)",
                "content": content,
            }
        ],
        skipped_files=[report_path] if already_registered else [],
        artifacts={"connection_scope": scope, "connection_path": report_path},
    )
    if mode == "preview" or already_registered:
        return report

    _write_json_atomic(connection_path, content)
    report.changed_files = [report_path]
    return report


def resolve_listenkit_connection(
    vault_root: str | Path,
    *,
    listenkit_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
    platform_name: str | None = None,
    data_home: str | Path | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> CommandReport:
    vault = Path(vault_root)
    platform_id = current_platform(platform_name)
    vault_relative_path = listenkit_connection_relative_path(platform_id)
    vault_connection_path = vault / vault_relative_path
    device_connection_path = device_listenkit_connection_path(
        platform_name=platform_id,
        data_home=data_home,
        home=home,
        environ=environ,
    )
    if runtime_root is not None:
        recommendation = recommended_listenkit_root(runtime_root=runtime_root, platform_name=platform_id)
    else:
        runtime_report = resolve_runtime_connection(vault, platform_name=platform_id)
        recommendation = (
            recommended_listenkit_root(
                runtime_root=runtime_report.artifacts["runtime_root"],
                platform_name=platform_id,
            )
            if runtime_report.accepted
            else None
        )

    if listenkit_root is not None:
        explicit_value = str(listenkit_root)
        findings: list[Finding] = []
        if not _is_absolute_for_platform(explicit_value, platform_id):
            findings.append(
                Finding(
                    code="listenkit_root_not_absolute",
                    message="ListenKit root must be an absolute path for the selected platform.",
                    path=explicit_value,
                )
            )
        if platform_id == current_platform():
            findings.extend(_listenkit_root_findings(Path(explicit_value)))
            if _paths_overlap(vault, Path(explicit_value)):
                findings.append(
                    Finding(
                        code="vault_listenkit_overlap",
                        message="The private Vault and ListenKit installation must be separate and must not contain each other.",
                        path=explicit_value,
                    )
                )
        if findings:
            return CommandReport(
                command="resolve-listenkit",
                mode="check",
                exit_code=1,
                errors=findings,
                artifacts=_recovery_artifacts(recommendation, str(device_connection_path)),
            )
        return _resolved_report(explicit_value, "explicit", None)

    read_files: list[str] = []
    stale_candidates: list[str] = []
    for scope, path, report_path in (
        ("vault", vault_connection_path, vault_relative_path),
        ("device", device_connection_path, str(device_connection_path)),
    ):
        if not path.exists():
            continue
        read_files.append(report_path)
        content, findings = _load_connection_file(path, platform_id)
        errors = [finding for finding in findings if finding.severity == "error"]
        if content is None or errors:
            return CommandReport(
                command="resolve-listenkit",
                mode="check",
                exit_code=1,
                errors=errors,
                warnings=[finding for finding in findings if finding.severity == "warning"],
                read_files=read_files,
                artifacts=_recovery_artifacts(recommendation, str(device_connection_path)),
            )
        for entry in content["connections"]:
            candidate = Path(entry["listenkit_root"])
            if is_usable_listenkit_root(candidate):
                return _resolved_report(str(candidate), scope, report_path, read_files=read_files)
            stale_candidates.append(str(candidate))

    if recommendation is not None and is_usable_listenkit_root(Path(recommendation)):
        return _resolved_report(recommendation, "recommended", None, read_files=read_files)

    if stale_candidates:
        message = (
            "Configured ListenKit paths are unavailable on this device. Ask the user whether to reinstall "
            f"ListenKit (suggested location: {recommendation}) or provide an existing ListenKit directory. "
            "Register the shared device default unless this Vault intentionally needs an override."
        )
        artifacts = _recovery_artifacts(recommendation, str(device_connection_path))
        artifacts["unavailable_listenkit_roots"] = json.dumps(stale_candidates, ensure_ascii=False)
        return CommandReport(
            command="resolve-listenkit",
            mode="check",
            exit_code=1,
            errors=[Finding(code="listenkit_connection_unavailable", message=message)],
            read_files=read_files,
            artifacts=artifacts,
        )

    return _listenkit_required_report(
        recommendation=recommendation,
        device_connection_path=str(device_connection_path),
        read_files=read_files,
    )


def is_usable_listenkit_root(root: Path) -> bool:
    return (root / "README.md").is_file() and (root / "cli" / "generate-markdown.sh").is_file()


def _resolved_report(
    listenkit_root: str,
    scope: str,
    connection_path: str | None,
    *,
    read_files: list[str] | None = None,
) -> CommandReport:
    artifacts = {
        "listenkit_root": listenkit_root,
        "generate_markdown": str(Path(listenkit_root) / "cli" / "generate-markdown.sh"),
        "connection_scope": scope,
    }
    if connection_path is not None:
        artifacts["connection_path"] = connection_path
    return CommandReport(
        command="resolve-listenkit",
        mode="check",
        read_files=read_files or [],
        artifacts=artifacts,
    )


def _listenkit_required_report(
    *,
    recommendation: str | None,
    device_connection_path: str,
    read_files: list[str],
) -> CommandReport:
    if recommendation is None:
        location_instruction = "Resolve the LingoTrace runtime before suggesting its sibling ListenKit directory."
    else:
        location_instruction = f"Suggested location: {recommendation}."
    message = (
        f"No usable ListenKit connection exists. {location_instruction} Ask the user whether to install there, "
        "choose another installation location, or provide an existing ListenKit directory. After validation, "
        "save it as the shared device default; use a Vault override only when that Vault needs a different checkout."
    )
    return CommandReport(
        command="resolve-listenkit",
        mode="check",
        exit_code=1,
        errors=[Finding(code="listenkit_connection_required", message=message, path=device_connection_path)],
        read_files=read_files,
        artifacts=_recovery_artifacts(recommendation, device_connection_path),
    )


def _recovery_artifacts(recommendation: str | None, device_connection_path: str) -> dict[str, str]:
    artifacts = {
        "device_connection_path": device_connection_path,
        "recovery_options": json.dumps(
            [
                {"id": "reinstall", "description": "Install ListenKit again after user consent."},
                {"id": "select_existing", "description": "Register an existing ListenKit directory."},
            ],
            ensure_ascii=False,
        ),
    }
    if recommendation is not None:
        artifacts["recommended_listenkit_root"] = recommendation
    return artifacts


def _listenkit_root_findings(root: Path) -> list[Finding]:
    if not root.exists():
        return [
            Finding(
                code="listenkit_root_missing",
                message="The selected ListenKit root does not exist.",
                path=str(root),
            )
        ]
    if not is_usable_listenkit_root(root):
        return [
            Finding(
                code="listenkit_root_invalid",
                message="The selected directory is not a usable ListenKit checkout.",
                path=str(root),
            )
        ]
    return []


def _load_connection_file(path: Path, expected_platform: str) -> tuple[dict[str, Any] | None, list[Finding]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [Finding(code="invalid_listenkit_connection_json", message=str(exc), path=str(path))]

    findings: list[Finding] = []
    if not isinstance(payload, dict):
        return None, [
            Finding(
                code="invalid_listenkit_connection_shape",
                message="ListenKit connection file must be a JSON object.",
                path=str(path),
            )
        ]
    if payload.get("listenkit_connection_schema_version") != LISTENKIT_CONNECTION_SCHEMA_VERSION:
        findings.append(
            Finding(
                code="unsupported_listenkit_connection_schema",
                message="Unsupported ListenKit connection schema version.",
                path=str(path),
            )
        )
    if payload.get("platform") != expected_platform:
        findings.append(
            Finding(
                code="listenkit_connection_platform_mismatch",
                message=f"Expected platform {expected_platform}.",
                path=str(path),
            )
        )
    connections = payload.get("connections")
    if not isinstance(connections, list) or not connections:
        findings.append(
            Finding(
                code="invalid_listenkit_connections",
                message="ListenKit connections must be a non-empty list.",
                path=str(path),
            )
        )
    else:
        for entry in connections:
            if not isinstance(entry, dict) or not isinstance(entry.get("listenkit_root"), str):
                findings.append(
                    Finding(
                        code="invalid_listenkit_connection_entry",
                        message="Each ListenKit connection must contain a string listenkit_root.",
                        path=str(path),
                    )
                )
                break
    return payload, findings


def _is_absolute_for_platform(path: str, platform_id: str) -> bool:
    if platform_id == "windows":
        return PureWindowsPath(path).is_absolute()
    return PurePosixPath(path).is_absolute()


def _paths_overlap(first: Path, second: Path) -> bool:
    first_resolved = first.resolve(strict=False)
    second_resolved = second.resolve(strict=False)
    return (
        first_resolved == second_resolved
        or first_resolved in second_resolved.parents
        or second_resolved in first_resolved.parents
    )


def _write_json_atomic(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
