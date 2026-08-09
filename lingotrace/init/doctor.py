from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path, PureWindowsPath
from typing import Callable, Mapping

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.init.listenkit_connections import (
    is_usable_listenkit_root,
    recommended_listenkit_root,
    resolve_listenkit_connection,
)
from lingotrace.init.runtime_connections import current_platform


SUPPORTED_LANGUAGES = ("english", "japanese")


def inspect_onboarding(
    *,
    language: str,
    vault_root: str | Path,
    runtime_root: str | Path,
    listenkit_root: str | Path | None = None,
    platform_name: str | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> CommandReport:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported_language: {language}")

    platform_id = current_platform(platform_name)
    environment = dict(os.environ if environ is None else environ)
    home_path = Path(home) if home is not None else Path.home()
    vault = Path(vault_root)
    runtime = Path(runtime_root)
    listenkit = Path(listenkit_root) if listenkit_root is not None else None

    errors: list[Finding] = []
    warnings: list[Finding] = []

    python_command = which("python3") or which("python")
    git_command = which("git")
    gh_command = which("gh")
    obsidian_path = _find_obsidian(platform_id, home_path, environment, which)
    listenkit_path = _find_listenkit(runtime, listenkit)
    if listenkit_path is None and vault.exists():
        listenkit_connection = resolve_listenkit_connection(
            vault,
            platform_name=platform_id,
            home=home_path,
            environ=environment,
        )
        if listenkit_connection.accepted:
            listenkit_path = listenkit_connection.artifacts["listenkit_root"]

    if python_command is None:
        errors.append(
            Finding(
                code="python_required",
                message="A Python launcher is required to run the LingoTrace initializer.",
            )
        )
    elif sys.version_info < (3, 11):
        errors.append(
            Finding(
                code="python_version_unsupported",
                message="LingoTrace onboarding requires Python 3.11 or newer.",
                path=python_command,
            )
        )
    if not runtime.is_absolute():
        errors.append(
            Finding(
                code="runtime_root_not_absolute",
                message="The LingoTrace runtime root must be an absolute path.",
                path=str(runtime),
            )
        )
    elif not (runtime / "lingotrace" / "__init__.py").is_file():
        errors.append(
            Finding(
                code="runtime_root_invalid",
                message="The selected runtime root does not contain lingotrace/__init__.py.",
                path=str(runtime),
            )
        )
    if not vault.is_absolute():
        errors.append(
            Finding(
                code="vault_root_not_absolute",
                message="The learning Vault root must be an absolute path.",
                path=str(vault),
            )
        )
    elif runtime.is_absolute() and _paths_overlap(vault, runtime):
        errors.append(
            Finding(
                code="vault_runtime_overlap",
                message="The private Vault and public runtime must be separate and must not contain each other.",
                path=str(vault),
            )
        )

    if git_command is None:
        warnings.append(
            Finding(
                code="git_not_found",
                message="Git was not found. Learning can continue from an archive, but managed runtime updates are unavailable.",
                severity="warning",
            )
        )
    if obsidian_path is None:
        warnings.append(
            Finding(
                code="obsidian_desktop_not_found",
                message="Obsidian Desktop was not found in common locations. It may be installed now or later.",
                severity="warning",
            )
        )
    if listenkit_path is None:
        listenkit_recommendation = recommended_listenkit_root(
            platform_name=platform_id,
            home=home_path,
            environ=environment,
        )
        warnings.append(
            Finding(
                code="listenkit_not_found",
                message=(
                    "ListenKit was not found. Text learning works, but media import and transcription need it later. "
                    f"Suggested installation location: {listenkit_recommendation}. The user may choose another path."
                ),
                severity="warning",
            )
        )

    dependencies = {
        "git": {"status": "found" if git_command else "missing_optional", "path": git_command},
        "github_cli": {"status": "found" if gh_command else "missing_optional", "path": gh_command},
        "listenkit": {"status": "found" if listenkit_path else "missing_optional", "path": listenkit_path},
        "obsidian_desktop": {"status": "found" if obsidian_path else "missing_optional", "path": obsidian_path},
        "python": {
            "status": "found" if python_command and sys.version_info >= (3, 11) else "missing_required",
            "path": python_command,
            "version": platform_python_version(),
        },
        "runtime": {
            "status": "found" if (runtime / "lingotrace" / "__init__.py").is_file() else "missing_required",
            "path": str(runtime),
        },
    }
    recommendations = recommended_locations(language, platform_name=platform_id, home=home_path, environ=environment)
    return CommandReport(
        command="onboarding-doctor",
        mode="check",
        exit_code=1 if errors else 0,
        errors=errors,
        warnings=warnings,
        artifacts={
            "dependencies": json.dumps(dependencies, ensure_ascii=False, sort_keys=True),
            "language": language,
            "platform": platform_id,
            "recommended_runtime_root": recommendations["runtime_root"],
            "recommended_listenkit_root": recommendations["listenkit_root"],
            "recommended_vault_root": recommendations["vault_root"],
            "vault_root": str(vault),
        },
    )


def recommended_locations(
    language: str,
    *,
    platform_name: str | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported_language: {language}")
    platform_id = current_platform(platform_name)
    environment = dict(os.environ if environ is None else environ)
    home_path = Path(home) if home is not None else Path.home()
    vault = home_path / "Documents" / "Obsidian" / f"LingoTrace-{language.title()}"
    if platform_id == "macos":
        runtime = home_path / "Library" / "Application Support" / "LingoTrace" / "runtime"
    elif platform_id == "windows":
        windows_home = PureWindowsPath(environment.get("USERPROFILE", str(home))) if home is not None else PureWindowsPath(environment.get("USERPROFILE", str(home_path)))
        vault = windows_home / "Documents" / "Obsidian" / f"LingoTrace-{language.title()}"
        local_app_data = PureWindowsPath(environment.get("LOCALAPPDATA", str(windows_home / "AppData" / "Local")))
        runtime = local_app_data / "LingoTrace" / "runtime"
    else:
        data_home = Path(environment.get("XDG_DATA_HOME", str(home_path / ".local" / "share")))
        runtime = data_home / "lingotrace" / "runtime"
    listenkit = recommended_listenkit_root(
        platform_name=platform_id,
        home=home,
        environ=environment,
    )
    return {"vault_root": str(vault), "runtime_root": str(runtime), "listenkit_root": listenkit}


def platform_python_version() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])


def _find_obsidian(
    platform_id: str,
    home: Path,
    environ: Mapping[str, str],
    which: Callable[[str], str | None],
) -> str | None:
    candidates: list[Path]
    if platform_id == "macos":
        candidates = [Path("/Applications/Obsidian.app"), home / "Applications" / "Obsidian.app"]
    elif platform_id == "windows":
        candidates = []
        for variable in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            if environ.get(variable):
                candidates.append(Path(environ[variable]) / "Obsidian" / "Obsidian.exe")
    else:
        candidates = [
            Path("/opt/Obsidian/obsidian"),
            Path("/opt/obsidian/obsidian"),
            Path("/snap/obsidian/current/obsidian"),
            Path("/var/lib/flatpak/app/md.obsidian.Obsidian"),
            home / ".local" / "share" / "flatpak" / "app" / "md.obsidian.Obsidian",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    executable = which("obsidian")
    return str(executable) if executable else None


def _find_listenkit(
    runtime: Path,
    requested: Path | None,
) -> str | None:
    candidates = [path for path in (requested, runtime.parent / "ListenKit") if path is not None]
    for candidate in candidates:
        if is_usable_listenkit_root(candidate):
            return str(candidate)
    return None


def _paths_overlap(first: Path, second: Path) -> bool:
    first_resolved = first.resolve(strict=False)
    second_resolved = second.resolve(strict=False)
    return (
        first_resolved == second_resolved
        or first_resolved in second_resolved.parents
        or second_resolved in first_resolved.parents
    )
