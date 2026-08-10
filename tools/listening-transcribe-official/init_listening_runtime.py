#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Mapping


EXPECTED_PYTHON = (3, 14)
SETUP_SCRIPT = Path(__file__).with_name("setup_offline_dictionary.py")


def current_platform_id(platform_name: str | None = None) -> str:
    raw = (platform_name or platform.system()).strip().lower()
    if raw in {"windows", "win32", "win"}:
        return "windows"
    if raw in {"darwin", "mac", "macos"}:
        return "macos"
    return "linux"


def default_runtime_dir(
    *,
    platform_name: str | None = None,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    platform_id = current_platform_id(platform_name)
    environment = dict(os.environ if environ is None else environ)
    home_path = Path(home) if home is not None else Path.home()
    if platform_id == "windows":
        root = Path(environment.get("LOCALAPPDATA", str(home_path / "AppData" / "Local"))) / "LingoTrace"
    elif platform_id == "macos":
        root = home_path / "Library" / "Caches" / "LingoTrace"
    else:
        root = Path(environment.get("XDG_CACHE_HOME", str(home_path / ".cache"))) / "lingotrace"
    return root / "venvs" / "cpython-314"


def runtime_python_path(runtime_dir: Path, platform_name: str | None = None) -> Path:
    if current_platform_id(platform_name) == "windows":
        return runtime_dir / "Scripts" / "python.exe"
    return runtime_dir / "bin" / "python"


def clean_python_subprocess_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if environ is None else environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def python_runtime_info(python_executable: str | Path) -> dict[str, object]:
    code = (
        "import json, sys; "
        "print(json.dumps({'executable': sys.executable, 'version': sys.version.split()[0], "
        "'major': sys.version_info.major, 'minor': sys.version_info.minor, "
        "'prefix': sys.prefix, 'base_prefix': sys.base_prefix, "
        "'in_venv': sys.prefix != sys.base_prefix}))"
    )
    try:
        result = subprocess.run(
            [str(python_executable), "-I", "-c", code],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            encoding="utf-8",
            errors="replace",
            env=clean_python_subprocess_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Unable to inspect Python runtime {python_executable}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Unable to inspect Python runtime {python_executable}: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Python runtime returned invalid metadata: {result.stdout.strip()}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Python runtime metadata must be a JSON object.")
    return payload


def validate_python_314(runtime: Mapping[str, object], description: str) -> None:
    version = runtime.get("major"), runtime.get("minor")
    if version != EXPECTED_PYTHON:
        raise RuntimeError(
            f"{description} must be Python 3.14; found {runtime.get('version', 'unknown')} "
            f"at {runtime.get('executable', 'unknown')}."
        )


def is_synchronized_runtime_path(path: Path, environ: Mapping[str, str] | None = None) -> bool:
    resolved = str(path.expanduser().resolve(strict=False))
    if "/Library/Mobile Documents/" in resolved:
        return True
    environment = dict(os.environ if environ is None else environ)
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = environment.get(variable)
        if not root:
            continue
        try:
            path.expanduser().resolve(strict=False).relative_to(Path(root).expanduser().resolve(strict=False))
        except ValueError:
            continue
        return True
    return False


def run_command(command: list[str]) -> int:
    try:
        result = subprocess.run(command, check=False, env=clean_python_subprocess_environment())
    except OSError as exc:
        raise RuntimeError(f"Unable to run {command[0]}: {exc}") from exc
    return result.returncode


def setup_command(runtime_python: Path, action: str) -> list[str]:
    return [
        str(runtime_python),
        str(SETUP_SCRIPT),
        "--python",
        str(runtime_python),
        action,
    ]


def initialize_or_check_runtime(
    *,
    bootstrap_python: str | Path,
    runtime_dir: Path,
    platform_name: str | None = None,
    action: str,
) -> int:
    if action not in {"install", "check", "dry-run"}:
        raise ValueError(f"unsupported_action: {action}")
    runtime_dir = runtime_dir.expanduser().resolve(strict=False)
    if is_synchronized_runtime_path(runtime_dir):
        raise RuntimeError(
            "The LingoTrace listening runtime must stay outside iCloud/OneDrive synchronized folders: "
            f"{runtime_dir}"
        )

    bootstrap = python_runtime_info(bootstrap_python)
    validate_python_314(bootstrap, "The listening-runtime bootstrap interpreter")
    runtime_python = runtime_python_path(runtime_dir, platform_name)
    create_command = [str(bootstrap_python), "-m", "venv", str(runtime_dir)]

    if action == "dry-run":
        print("create: " + " ".join(create_command))
        print("install: " + " ".join(setup_command(runtime_python, "--install")))
        print("check: " + " ".join(setup_command(runtime_python, "--check")))
        return 0

    if not runtime_python.is_file():
        if action == "check":
            raise RuntimeError(
                f"LingoTrace listening runtime is missing: {runtime_python}. "
                "Run this public initializer with --install."
            )
        if runtime_dir.exists() and any(runtime_dir.iterdir()):
            raise RuntimeError(
                "Refusing to initialize over a non-empty directory that is not a valid listening runtime: "
                f"{runtime_dir}"
            )
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        if run_command(create_command) != 0:
            raise RuntimeError(f"Python virtual environment creation failed: {runtime_dir}")
        if not runtime_python.is_file():
            raise RuntimeError(f"Python virtual environment did not create its interpreter: {runtime_python}")

    runtime = python_runtime_info(runtime_python)
    validate_python_314(runtime, "The LingoTrace listening runtime")
    if not runtime.get("in_venv"):
        raise RuntimeError(f"The selected listening runtime is not a virtual environment: {runtime_python}")

    command = setup_command(runtime_python, "--check" if action == "check" else "--install")
    exit_code = run_command(command)
    if exit_code == 0:
        print(f"runtime_python: {runtime_python}")
    return exit_code


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or check the isolated LingoTrace Python 3.14 listening runtime."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bootstrap-python", default=sys.executable)
    parser.add_argument("--runtime-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    action = "check" if args.check else "dry-run" if args.dry_run else "install"
    runtime_dir = args.runtime_dir or default_runtime_dir()
    try:
        return initialize_or_check_runtime(
            bootstrap_python=args.bootstrap_python,
            runtime_dir=runtime_dir,
            action=action,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
