from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.init.runtime_connections import current_platform


LISTENKIT_CONNECTION_SCHEMA_VERSION = 1
LISTENKIT_CONNECTION_DIRECTORY = ".lingotrace/listenkit-connections"


def listenkit_connection_relative_path(platform_name: str | None = None) -> str:
    return f"{LISTENKIT_CONNECTION_DIRECTORY}/{current_platform(platform_name)}.json"


def recommended_listenkit_root(
    *,
    platform_name: str | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    platform_id = current_platform(platform_name)
    environment = dict(os.environ if environ is None else environ)
    home_path = Path(home) if home is not None else Path.home()

    if platform_id == "macos":
        root = home_path / "Library" / "Application Support" / "LingoTrace" / "dependencies" / "ListenKit"
    elif platform_id == "windows":
        raw_home = environment.get("USERPROFILE", str(home) if home is not None else str(home_path))
        windows_home = PureWindowsPath(raw_home)
        local_app_data = PureWindowsPath(
            environment.get("LOCALAPPDATA", str(windows_home / "AppData" / "Local"))
        )
        root = local_app_data / "LingoTrace" / "dependencies" / "ListenKit"
    else:
        data_home = Path(environment.get("XDG_DATA_HOME", str(home_path / ".local" / "share")))
        root = data_home / "lingotrace" / "dependencies" / "ListenKit"
    return str(root)


def default_listenkit_connection(
    listenkit_root: str | Path,
    platform_name: str | None = None,
) -> dict[str, Any]:
    platform_id = current_platform(platform_name)
    return {
        "listenkit_connection_schema_version": LISTENKIT_CONNECTION_SCHEMA_VERSION,
        "platform": platform_id,
        "connections": [
            {
                "listenkit_root": str(listenkit_root),
                "source": "user-confirmed",
            }
        ],
    }


def register_listenkit_connection(
    vault_root: str | Path,
    listenkit_root: str | Path,
    *,
    platform_name: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if mode not in {"preview", "apply"}:
        raise ValueError(f"unsupported_mode: {mode}")

    vault = Path(vault_root)
    platform_id = current_platform(platform_name)
    relative_path = listenkit_connection_relative_path(platform_id)
    connection_path = vault / relative_path
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
        if _paths_overlap(vault, Path(listenkit_value)):
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
        read_files.append(relative_path)
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
            blocked_files=[relative_path] if connection_path.exists() else [],
        )

    if existing is None:
        content = default_listenkit_connection(listenkit_value, platform_id)
        already_registered = False
    else:
        content = existing
        connections = content["connections"]
        already_registered = any(entry["listenkit_root"] == listenkit_value for entry in connections)
        if not already_registered:
            connections.append({"listenkit_root": listenkit_value, "source": "user-confirmed"})

    action = "no_change" if already_registered else ("update_json" if existing else "write_json")
    report = CommandReport(
        command="connect-listenkit",
        mode=mode,
        read_files=read_files,
        planned_writes=[
            {
                "path": relative_path,
                "action": action,
                "artifact_class": "vault-local-listenkit-connection",
                "reason": f"ListenKit candidates for {platform_id}",
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


def resolve_listenkit_connection(
    vault_root: str | Path,
    *,
    platform_name: str | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> CommandReport:
    vault = Path(vault_root)
    platform_id = current_platform(platform_name)
    relative_path = listenkit_connection_relative_path(platform_id)
    connection_path = vault / relative_path
    recommendation = recommended_listenkit_root(
        platform_name=platform_id,
        home=home,
        environ=environ,
    )

    if not connection_path.exists():
        return _listenkit_required_report(
            platform_id,
            relative_path,
            recommendation,
            "No ListenKit connection file exists for this platform.",
        )

    content, findings = _load_connection_file(connection_path, platform_id)
    errors = [finding for finding in findings if finding.severity == "error"]
    if content is None or errors:
        return CommandReport(
            command="resolve-listenkit",
            mode="check",
            exit_code=1,
            errors=errors,
            warnings=[finding for finding in findings if finding.severity == "warning"],
            read_files=[relative_path],
            artifacts=_recovery_artifacts(recommendation),
        )

    stale_candidates: list[str] = []
    for entry in content["connections"]:
        listenkit_root = Path(entry["listenkit_root"])
        if is_usable_listenkit_root(listenkit_root):
            return CommandReport(
                command="resolve-listenkit",
                mode="check",
                read_files=[relative_path],
                warnings=[finding for finding in findings if finding.severity == "warning"],
                artifacts={
                    "listenkit_root": str(listenkit_root),
                    "generate_markdown": str(listenkit_root / "cli" / "generate-markdown.sh"),
                },
            )
        stale_candidates.append(str(listenkit_root))

    message = (
        "Configured ListenKit paths are unavailable on this device. Ask the user whether to reinstall ListenKit "
        f"(suggested location: {recommendation}) or provide an existing ListenKit directory. Validate the selected "
        "directory and append it to the current platform connection file."
    )
    artifacts = _recovery_artifacts(recommendation)
    artifacts["unavailable_listenkit_roots"] = json.dumps(stale_candidates, ensure_ascii=False)
    return CommandReport(
        command="resolve-listenkit",
        mode="check",
        exit_code=1,
        errors=[Finding(code="listenkit_connection_unavailable", message=message, path=relative_path)],
        read_files=[relative_path],
        artifacts=artifacts,
    )


def is_usable_listenkit_root(root: Path) -> bool:
    return (root / "README.md").is_file() and (root / "cli" / "generate-markdown.sh").is_file()


def _listenkit_required_report(
    platform_id: str,
    relative_path: str,
    recommendation: str,
    reason: str,
) -> CommandReport:
    message = (
        f"{reason} Ask the user whether to install ListenKit at the suggested location ({recommendation}), choose "
        "another installation location, or provide an existing ListenKit directory. After validation, save only "
        f"the {platform_id} connection to {relative_path}; do not modify other platforms."
    )
    return CommandReport(
        command="resolve-listenkit",
        mode="check",
        exit_code=1,
        errors=[Finding(code="listenkit_connection_required", message=message, path=relative_path)],
        artifacts=_recovery_artifacts(recommendation),
    )


def _recovery_artifacts(recommendation: str) -> dict[str, str]:
    return {
        "recommended_listenkit_root": recommendation,
        "recovery_options": json.dumps(
            [
                {"id": "reinstall", "description": "Install ListenKit again after user consent."},
                {"id": "select_existing", "description": "Register an existing ListenKit directory."},
            ],
            ensure_ascii=False,
        ),
    }


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
    return Path(path).is_absolute()


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
