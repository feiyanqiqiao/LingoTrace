#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


CIRCLED_ACCENT_MARKS = "⓪①②③④⑤⑥⑦⑧⑨"
ACCENT_TYPE_TO_MARK = {str(index): mark for index, mark in enumerate(CIRCLED_ACCENT_MARKS)}


def accent_marks_from_type(value: str) -> str | None:
    marks = [
        ACCENT_TYPE_TO_MARK[item]
        for item in re.findall(r"\d+", value or "")
        if item in ACCENT_TYPE_TO_MARK
    ]
    if not marks:
        return None
    return "/".join(dict.fromkeys(marks))


def default_cache_dir() -> Path:
    override = os.environ.get("JP_LISTENING_DICT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Caches" / "jp-listening-dicts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="setup-offline-dictionary",
        description="Prepare the offline Japanese dictionary cache for listening learning packages.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Check whether an offline dictionary cache is usable.")
    action.add_argument("--install", action="store_true", help="Install fugashi and unidic-lite into the cache.")
    action.add_argument("--dry-run", action="store_true", help="Print the install command without running it.")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def cache_dir_from_args(args: argparse.Namespace) -> Path:
    return args.cache_dir.expanduser() if args.cache_dir else default_cache_dir()


def static_accent_map_path(cache_dir: Path) -> Path:
    return cache_dir / "accent_map.json"


def python_target(cache_dir: Path) -> Path:
    return cache_dir / "python"


def import_from_cache(cache_dir: Path) -> tuple[bool, str]:
    target = python_target(cache_dir)
    if target.exists():
        sys.path.insert(0, str(target))
    try:
        import fugashi  # type: ignore
        import unidic_lite  # type: ignore

        tagger = fugashi.Tagger(f"-d {unidic_lite.DICDIR}")
        words = list(tagger("公園を散歩します。"))
        parsed = [str(word.surface) for word in words]
        if not parsed:
            return False, "fugashi loaded but did not parse the sample sentence."
        accents = []
        for word in words:
            marks = accent_marks_from_type(str(getattr(word.feature, "aType", "") or ""))
            if marks:
                accents.append(f"{word.surface}{marks}")
        suffix = f"; sample accents: {' / '.join(accents)}" if accents else "; no sample accent candidates"
        return True, f"fugashi + unidic-lite ready; sample tokens: {' / '.join(parsed)}{suffix}"
    except Exception as exc:
        return False, f"Python dictionary packages are not ready: {exc}"


def check_cache(cache_dir: Path) -> tuple[bool, list[str]]:
    messages = [f"cache_dir: {cache_dir}"]
    accent_map = static_accent_map_path(cache_dir)
    if accent_map.exists():
        try:
            payload = json.loads(accent_map.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, messages + [f"accent_map.json invalid: {exc}"]
        if isinstance(payload, dict):
            messages.append(f"accent_map.json entries: {len(payload)}")
        else:
            return False, messages + ["accent_map.json must contain a JSON object."]

    package_ready, package_message = import_from_cache(cache_dir)
    messages.append(package_message)
    if accent_map.exists() or package_ready:
        return True, messages
    return False, messages + ["No usable offline dictionary found."]


def install_command(args: argparse.Namespace, cache_dir: Path) -> list[str]:
    return [
        args.python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(python_target(cache_dir)),
        "fugashi",
        "unidic-lite",
    ]


def main() -> int:
    args = parse_args()
    cache_dir = cache_dir_from_args(args)

    if args.check:
        ok, messages = check_cache(cache_dir)
        print("\n".join(messages))
        return 0 if ok else 1

    command = install_command(args, cache_dir)
    if args.dry_run:
        print(" ".join(command))
        return 0

    cache_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        return result.returncode
    ok, messages = check_cache(cache_dir)
    print("\n".join(messages))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
