#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
TEMPLATE_MARKERS = ("YYYY", "<", ">")


def note_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for base in (root / "学习系统", root / "系统配置", root / "笔记"):
        if base.exists():
            result.extend(base.rglob("*.md"))
    return sorted(result)


def clean_target(raw_target: str) -> str:
    return raw_target.split("|", 1)[0].split("#", 1)[0].strip()


def candidate_paths(root: Path, source: Path, target: str) -> list[Path]:
    raw = Path(target)
    if target.startswith(("./", "../", "attach/", "artifacts/")):
        base = source.parent / raw
    else:
        base = root / raw
    candidates = [base]
    candidates.append(Path(f"{base}.md"))
    return candidates


def target_resolves(root: Path, source: Path, target: str) -> bool:
    if not target or target.startswith("^") or any(marker in target for marker in TEMPLATE_MARKERS):
        return True
    if "/" not in target and Path(target).suffix.lower() not in MEDIA_SUFFIXES:
        return True
    candidates = candidate_paths(root, source, target)
    if any(candidate.exists() for candidate in candidates):
        return True
    if "/" not in target and Path(target).suffix.lower() in MEDIA_SUFFIXES:
        return len(list(root.rglob(target))) == 1
    return False


def find_missing_explicit_links(root: Path, notes: list[Path] | None = None) -> list[str]:
    missing: list[str] = []
    for note in notes or note_files(root):
        text = note.read_text(encoding="utf-8")
        for match in WIKILINK.finditer(text):
            target = clean_target(match.group(1))
            if not target_resolves(root, note, target):
                missing.append(f"{note.relative_to(root).as_posix()}::{target}")
    return sorted(set(missing))


def new_missing_links(current: set[str], baseline: set[str]) -> set[str]:
    return current - baseline


def validation_baseline(
    missing: set[str],
    loaded_baseline: set[str],
    *,
    wrote_baseline: bool,
    explicit_baseline: bool,
) -> set[str]:
    if wrote_baseline and not explicit_baseline:
        return missing
    return loaded_baseline


def find_paths_config(root: Path) -> Path:
    candidates = (
        root / "系统配置/paths.json",
        root / "学习系统/系统/配置/paths.json",
        root / "学习系统/系统配置/paths.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("paths.json was not found")


def validate_roles(root: Path) -> list[str]:
    errors: list[str] = []
    config = json.loads(find_paths_config(root).read_text(encoding="utf-8"))
    roles = config.get("roles")
    if not roles:
        return errors
    for key, value in sorted(roles.items()):
        if not isinstance(value, str) or not value:
            errors.append(f"role {key} must be a non-empty vault-relative path")
            continue
        if not (root / value).exists():
            errors.append(f"role path does not exist: {key}={value}")
    if roles.get("base_vocab_root") != config.get("base_vocab_root"):
        errors.append("base_vocab_root compatibility mirror does not match roles.base_vocab_root")
    if roles.get("daily_notes_root") != config.get("daily_notes_root"):
        errors.append("daily_notes_root compatibility mirror does not match roles.daily_notes_root")
    if "focus_vocab_root" in roles:
        managed_expected = [
            roles.get("focus_vocab_root"),
            roles.get("grammar_root"),
            roles.get("error_root"),
            roles.get("speaking_card_root"),
            roles.get("listening_root"),
            roles.get("pronunciation_accent_root"),
            roles.get("pronunciation_phoneme_root"),
        ]
    else:
        managed_expected = [
            roles.get("class_review_root"),
            roles.get("speaking_card_root"),
            roles.get("listening_root"),
            roles.get("pronunciation_accent_root"),
            roles.get("pronunciation_phoneme_root"),
        ]
    if managed_expected != config.get("managed_review_roots"):
        errors.append("managed_review_roots compatibility mirror does not match role roots")
    return errors


def validate_listening_layout(root: Path) -> list[str]:
    errors: list[str] = []
    listening = root / "学习系统/听力"
    if not listening.exists():
        return errors
    for path in sorted(listening.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in MEDIA_SUFFIXES and path.parent.name != "attach":
            errors.append(f"listening media must live under attach/: {path.relative_to(root)}")
        if path.name.endswith((".listenkit.md", ".listenkit.json")) and path.parent.name != "artifacts":
            errors.append(f"ListenKit artifact must live under artifacts/: {path.relative_to(root)}")
    return errors


def validate_untitled_bases(root: Path) -> list[str]:
    return [
        f"untitled base must be removed: {path.relative_to(root)}"
        for path in sorted((root / "学习系统").rglob("無題のファイル*.base"))
    ]


def load_baseline(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("missing_links", []))


def run_integrations(root: Path, run_date: str) -> list[str]:
    commands = [
        ["zsh", "codex-skills/jp-survival-speaking-card-generator/scripts/validate-survival-speaking-cards.sh", run_date],
    ]
    errors: list[str] = []
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False, text=True, capture_output=True)
        print(result.stdout, end="")
        if result.returncode:
            print(result.stderr, end="")
            errors.append(f"integration failed ({result.returncode}): {' '.join(command)}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Japanese-learning vault directory contract.")
    parser.add_argument("--vault-root", default=".")
    parser.add_argument("--write-baseline", help="Write the current missing explicit-link set as JSON.")
    parser.add_argument("--baseline", help="Compare missing explicit links against a baseline JSON file.")
    parser.add_argument("--enforce-listening-layout", action="store_true")
    parser.add_argument("--run-integrations", action="store_true")
    parser.add_argument("--date", default="2026-05-31")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.vault_root).expanduser().resolve()
    missing = set(find_missing_explicit_links(root))
    if args.write_baseline:
        output = root / args.write_baseline
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"missing_links": sorted(missing)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote baseline: {output.relative_to(root)} ({len(missing)} missing explicit links)")
    baseline = validation_baseline(
        missing,
        load_baseline(root / args.baseline if args.baseline else None),
        wrote_baseline=bool(args.write_baseline),
        explicit_baseline=bool(args.baseline),
    )
    errors = validate_roles(root) + validate_untitled_bases(root)
    if args.enforce_listening_layout:
        errors.extend(validate_listening_layout(root))
    errors.extend(f"new missing explicit link: {item}" for item in sorted(new_missing_links(missing, baseline)))
    if args.run_integrations:
        errors.extend(run_integrations(root, args.date))
    print(f"Missing explicit links: {len(missing)}")
    print(f"Baseline missing explicit links: {len(baseline)}")
    if errors:
        print("Vault structure validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Vault structure validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
