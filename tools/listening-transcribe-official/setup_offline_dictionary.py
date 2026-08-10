#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


EXPECTED_PYTHON = (3, 14)
EXPECTED_PACKAGES = {"fugashi": "1.5.2", "unidic-lite": "1.0.8"}
REQUIREMENTS_PATH = Path(__file__).with_name("requirements-listening.txt")


def default_cache_dir() -> Path:
    override = os.environ.get("JP_LISTENING_DICT_DIR")
    if override:
        return Path(override).expanduser()
    platform_name = platform.system().lower()
    if platform_name == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return root / "LingoTrace" / "Caches" / "jp-listening-dicts"
    if platform_name == "darwin":
        return Path.home() / "Library" / "Caches" / "jp-listening-dicts"
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "lingotrace" / "jp-listening-dicts"


def clean_python_subprocess_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="setup-offline-dictionary",
        description="Install or check LingoTrace's project-local Japanese dictionary runtime.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--install", action="store_true")
    action.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def cache_dir_from_args(args: argparse.Namespace) -> Path:
    return args.cache_dir.expanduser() if args.cache_dir else default_cache_dir()


def static_accent_map_path(cache_dir: Path) -> Path:
    return cache_dir / "accent_map.json"


def runtime_python_version(runtime: dict[str, object]) -> tuple[int, int] | None:
    if runtime.get("major") is not None and runtime.get("minor") is not None:
        return int(runtime["major"]), int(runtime["minor"])
    try:
        major, minor, *_ = str(runtime["version"]).split(".")
        return int(major), int(minor)
    except (KeyError, TypeError, ValueError):
        return None


def python_runtime_info(python_executable: str) -> dict[str, object]:
    code = (
        "import json, sys; "
        "print(json.dumps({'executable': sys.executable, 'version': sys.version.split()[0], "
        "'major': sys.version_info.major, 'minor': sys.version_info.minor, "
        "'cache_tag': sys.implementation.cache_tag, 'prefix': sys.prefix, "
        "'base_prefix': sys.base_prefix, 'in_venv': sys.prefix != sys.base_prefix}))"
    )
    try:
        result = subprocess.run(
            [python_executable, "-I", "-c", code],
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
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Python runtime returned invalid metadata: {result.stdout.strip()}") from exc


def import_from_runtime(runtime: dict[str, object]) -> tuple[bool, str]:
    code = r'''
import importlib.metadata
import json
import re

import fugashi
import unidic_lite

tagger = fugashi.Tagger(f"-d {unidic_lite.DICDIR}")
words = list(tagger("公園を散歩します。"))
marks = "⓪①②③④⑤⑥⑦⑧⑨"
accents = []
for word in words:
    values = re.findall(r"\d+", str(getattr(word.feature, "aType", "") or ""))
    rendered = "/".join(dict.fromkeys(marks[int(value)] for value in values if int(value) < len(marks)))
    if rendered:
        accents.append(f"{word.surface}{rendered}")
print(json.dumps({
    "tokens": [str(word.surface) for word in words],
    "accents": accents,
    "versions": {
        "fugashi": importlib.metadata.version("fugashi"),
        "unidic-lite": importlib.metadata.version("unidic-lite"),
    },
}, ensure_ascii=False))
'''
    try:
        result = subprocess.run(
            [str(runtime["executable"]), "-I", "-c", code],
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
        return False, f"Python dictionary health check failed: {exc}"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return False, f"Python dictionary packages are not ready: {detail}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, f"Python dictionary health check returned invalid output: {result.stdout.strip()}"
    versions = payload.get("versions", {})
    if versions != EXPECTED_PACKAGES:
        return False, f"Dictionary package versions do not match requirements: {versions}"
    accents = [str(item) for item in payload.get("accents", [])]
    required = {"公園⓪", "散歩⓪", "し⓪"}
    if not required.issubset(accents):
        return False, f"Dictionary sample accents are incomplete: {' / '.join(accents) or 'none'}"
    tokens = [str(item) for item in payload.get("tokens", [])]
    return True, (
        "fugashi + unidic-lite ready; "
        f"sample tokens: {' / '.join(tokens)}; sample accents: {' / '.join(accents)}"
    )


def check_runtime(cache_dir: Path, python_executable: str) -> tuple[bool, list[str]]:
    messages = [f"cache_dir: {cache_dir}"]
    try:
        runtime = python_runtime_info(python_executable)
    except RuntimeError as exc:
        return False, messages + [str(exc)]
    messages.extend(
        [
            f"python: {runtime['executable']}",
            f"version: {runtime['version']}",
            f"abi_tag: {runtime['cache_tag']}",
            f"venv: {runtime['prefix']}",
        ]
    )
    if runtime_python_version(runtime) != EXPECTED_PYTHON:
        return False, messages + ["LingoTrace listening runtime requires Python 3.14."]
    if not runtime.get("in_venv"):
        return False, messages + ["LingoTrace dictionary packages must be installed in a virtual environment."]
    if "/Library/Mobile Documents/" in str(runtime.get("prefix", "")):
        return False, messages + [
            "LingoTrace native packages cannot run from an iCloud-backed virtual environment. "
            "Run init-listening-runtime.sh to create the local Cache runtime."
        ]

    accent_map = static_accent_map_path(cache_dir)
    if accent_map.exists():
        try:
            payload = json.loads(accent_map.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, messages + [f"accent_map.json invalid: {exc}"]
        if not isinstance(payload, dict):
            return False, messages + ["accent_map.json must contain a JSON object."]
        messages.append(f"accent_map.json entries: {len(payload)}")

    package_ready, package_message = import_from_runtime(runtime)
    messages.append(package_message)
    return package_ready, messages


def install_command(args: argparse.Namespace) -> list[str]:
    return [args.python, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]


def main() -> int:
    args = parse_args()
    cache_dir = cache_dir_from_args(args)

    if args.check:
        ok, messages = check_runtime(cache_dir, args.python)
        print("\n".join(messages))
        return 0 if ok else 1

    try:
        runtime = python_runtime_info(args.python)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if runtime_python_version(runtime) != EXPECTED_PYTHON or not runtime.get("in_venv"):
        print(
            "Refusing to install outside a Python 3.14 virtual environment. "
            "Create a Python 3.14 virtual environment outside synchronized folders, then rerun this public "
            "setup_offline_dictionary.py with --python <venv-python> --install. "
            "See docs/listening-runtime-isolation.md.",
            file=sys.stderr,
        )
        return 1
    if "/Library/Mobile Documents/" in str(runtime.get("prefix", "")):
        print(
            "Refusing to install native packages into an iCloud-backed virtual environment. "
            "Run init-listening-runtime.sh to create the local Cache runtime.",
            file=sys.stderr,
        )
        return 1

    command = install_command(args)
    if args.dry_run:
        print(" ".join(command))
        return 0
    result = subprocess.run(command, check=False, env=clean_python_subprocess_environment())
    if result.returncode != 0:
        return result.returncode
    ok, messages = check_runtime(cache_dir, args.python)
    print("\n".join(messages))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
