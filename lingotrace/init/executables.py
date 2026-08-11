from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Mapping

from lingotrace.init.runtime_connections import current_platform


def find_executable(
    name: str,
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> str | None:
    resolved = which(name)
    if resolved:
        return str(resolved)
    if current_platform(platform_name) != "windows":
        return None

    environment = dict(os.environ if environ is None else environ)
    for candidate in _windows_candidates(name, environment):
        if candidate.is_file():
            return str(candidate)
    return None


def _windows_candidates(name: str, environ: Mapping[str, str]) -> list[Path]:
    local_app_data = _environment_path(environ, "LOCALAPPDATA")
    user_profile = _environment_path(environ, "USERPROFILE")
    program_files = _environment_path(environ, "ProgramFiles")
    program_files_x86 = _environment_path(environ, "ProgramFiles(x86)")
    system_root = _environment_path(environ, "SystemRoot") or Path(r"C:\Windows")
    chocolatey = _environment_path(environ, "ChocolateyInstall")
    scoop = _environment_path(environ, "SCOOP")

    candidates: list[Path | None]
    normalized = name.lower().removesuffix(".exe")
    if normalized == "git":
        candidates = [
            program_files / "Git" / "cmd" / "git.exe" if program_files else None,
            program_files_x86 / "Git" / "cmd" / "git.exe" if program_files_x86 else None,
            local_app_data / "Programs" / "Git" / "cmd" / "git.exe" if local_app_data else None,
        ]
    elif normalized == "gh":
        candidates = [
            program_files / "GitHub CLI" / "gh.exe" if program_files else None,
            program_files_x86 / "GitHub CLI" / "gh.exe" if program_files_x86 else None,
            local_app_data / "Programs" / "GitHub CLI" / "gh.exe" if local_app_data else None,
        ]
    elif normalized == "pwsh":
        candidates = [
            program_files / "PowerShell" / "7" / "pwsh.exe" if program_files else None,
            program_files / "PowerShell" / "7-preview" / "pwsh.exe" if program_files else None,
        ]
    elif normalized == "powershell":
        candidates = [system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"]
    elif normalized in {"ffmpeg", "ffprobe"}:
        executable = f"{normalized}.exe"
        candidates = [
            local_app_data / "Microsoft" / "WinGet" / "Links" / executable if local_app_data else None,
            scoop / "shims" / executable if scoop else None,
            user_profile / "scoop" / "shims" / executable if user_profile else None,
            chocolatey / "bin" / executable if chocolatey else None,
        ]
    else:
        candidates = []
    return [candidate for candidate in candidates if candidate is not None]


def _environment_path(environ: Mapping[str, str], name: str) -> Path | None:
    value = environ.get(name)
    return Path(value) if value else None
