#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".toml", ".py", ".sh", ".base"}
SKIP_DIRS = {".git", "tmp", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class Move:
    source: str
    target: str


@dataclass(frozen=True)
class Create:
    path: str
    content: str


@dataclass(frozen=True)
class Delete:
    path: str


@dataclass
class PhasePlan:
    phase: str
    moves: list[Move] = field(default_factory=list)
    creates: list[Create] = field(default_factory=list)
    deletes: list[Delete] = field(default_factory=list)
    replacements: dict[str, str] = field(default_factory=dict)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.rglob("*") if item.is_file())


def practice_entry_text() -> str:
    return """---
title: 发音练习入口
tags:
  - jp/pronunciation
  - jp/practice
---

# 发音练习入口

这里仅放句子跟读、录音回听、语调和停顿练习。

- 单词重音对比放在 [[学习系统/发音/アクセント/アクセント训练入口]]。
- 音素辨析放在 [[学习系统/发音/音素/音素训练入口]]。
- 汉字读音辨析放在 `学习系统/发音/读音辨析/`。
"""


def intermediate_review_flow_text() -> str:
    return """---
title: 复习流程
tags:
  - jp/system
  - jp/dashboard
---

# 复习流程

## 录入与维护

- 新课笔记继续放在 `笔记/`。
- 新条目优先从 [[学习系统/系统/模板/录入模板索引]] 复制。
- 每天收口可直接复制 [[学习系统/系统/模板/每日学习清单模板]] 到当天笔记。
- 日常训练直接打开 [[学习系统/系统/面板/总训练.base]]。
- `done_today` 可以临时勾选，帮助当天训练时做手工标记。
- 每天收口先运行 `zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh --date YYYY-MM-DD --dry-run`；确认无误后去掉 `--dry-run`。

## 复习曲线

统一曲线：

`day0 -> day1 -> day3 -> day7 -> day14 -> day30 -> day90 -> day180 -> mastered`

正常推进：

- `day0` 完成后：`next_review = 完成日 + 1`
- `day1` 完成后：`next_review = 完成日 + 3`
- `day3` 完成后：`next_review = 完成日 + 7`
- `day7` 完成后：`next_review = 完成日 + 14`
- `day14` 完成后：`next_review = 完成日 + 30`
- `day30` 完成后：`next_review = 完成日 + 90`
- `day90` 完成后：`next_review = 完成日 + 180`
- `day180` 完成后：`status = mastered`，`next_review = ""`

延迟规则：

- `overdue_days = 完成日 - 原 next_review`
- `allowed_delay = max(1, 当前阶段天数)`
- 如果 `overdue_days <= allowed_delay`，升到下一阶段。
- 如果 `overdue_days > allowed_delay`，不升阶，保持原 `review_stage`，并重新排到 `完成日 + allowed_delay`。

## Bases 使用注意

`今日总训练` 按 `first_seen`、优先级、`next_review`、错误次数、重复次数和 `file.name` 排序。第一列保留为限制宽度的 `file.name`，`done_today` 放在第二列，避免嵌入视图中第一列 checkbox 偶发写入相邻行。
"""


def intermediate_paths_config_text() -> str:
    data = {
        "managed_review_roots": [
            "学习系统/课堂复习",
            "学习系统/生活口语/句库",
            "学习系统/听力",
            "学习系统/发音/アクセント",
            "学习系统/发音/音素",
        ],
        "base_vocab_root": "学习系统/词库/基础词汇",
        "daily_notes_root": "笔记",
        "roles": {
            "system_root": "学习系统/系统",
            "template_root": "学习系统/系统/模板",
            "dashboard_root": "学习系统/系统/面板",
            "main_dashboard": "学习系统/系统/面板/总训练.base",
            "class_review_root": "学习系统/课堂复习",
            "speaking_card_root": "学习系统/生活口语/句库",
            "speaking_guide_root": "学习系统/生活口语/场景指南",
            "listening_root": "学习系统/听力",
            "pronunciation_practice_root": "学习系统/发音/练习",
            "pronunciation_accent_root": "学习系统/发音/アクセント",
            "pronunciation_phoneme_root": "学习系统/发音/音素",
            "pronunciation_reading_distinction_root": "学习系统/发音/读音辨析",
            "pronunciation_asset_root": "学习系统/发音/素材",
            "lexicon_root": "学习系统/词库",
            "base_vocab_root": "学习系统/词库/基础词汇",
            "composition_root": "学习系统/作文",
            "daily_notes_root": "笔记",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def review_flow_text() -> str:
    return intermediate_review_flow_text().replace(
        "学习系统/系统/模板", "系统配置/模板"
    ).replace(
        "学习系统/系统/面板/总训练.base", "学习系统/总训练.base"
    )


def paths_config_text() -> str:
    data = {
        "managed_review_roots": [
            "学习系统/词库/重点词汇",
            "学习系统/语法",
            "学习系统/错题",
            "学习系统/生活口语/句库",
            "学习系统/听力",
            "学习系统/发音/アクセント",
            "学习系统/发音/音素",
        ],
        "base_vocab_root": "学习系统/词库/基础词汇",
        "daily_notes_root": "笔记",
        "roles": {
            "config_root": "系统配置",
            "template_root": "系统配置/模板",
            "main_dashboard": "学习系统/总训练.base",
            "focus_vocab_root": "学习系统/词库/重点词汇",
            "base_vocab_root": "学习系统/词库/基础词汇",
            "grammar_root": "学习系统/语法",
            "error_root": "学习系统/错题",
            "speaking_card_root": "学习系统/生活口语/句库",
            "speaking_guide_root": "学习系统/生活口语/场景指南",
            "listening_root": "学习系统/听力",
            "pronunciation_practice_root": "学习系统/发音/练习",
            "pronunciation_accent_root": "学习系统/发音/アクセント",
            "pronunciation_phoneme_root": "学习系统/发音/音素",
            "pronunciation_reading_distinction_root": "学习系统/发音/读音辨析",
            "pronunciation_asset_root": "学习系统/发音/素材",
            "lexicon_root": "学习系统/词库",
            "composition_root": "学习系统/作文",
            "daily_notes_root": "笔记",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def add_tree_moves(root: Path, source_dir: str, target_dir: str, plan: PhasePlan) -> None:
    base = root / source_dir
    for path in iter_files(base):
        target = Path(target_dir) / path.relative_to(base)
        plan.moves.append(Move(rel(path, root), target.as_posix()))


def add_create_if_changed(root: Path, plan: PhasePlan, path: str, content: str) -> None:
    target = root / path
    if target.is_file() and target.read_text(encoding="utf-8") == content:
        return
    plan.creates.append(Create(path, content))


def build_pronunciation_plan(root: Path) -> PhasePlan:
    plan = PhasePlan("pronunciation")
    add_tree_moves(root, "学习系统/发音/漢字辨析", "学习系统/发音/读音辨析", plan)
    old_assets = root / "学习系统/发音/其他"
    for path in iter_files(old_assets):
        if path.suffix.lower() in MEDIA_SUFFIXES:
            target = Path("学习系统/发音/素材/audio") / path.name
        else:
            target = Path("学习系统/发音/素材/artifacts") / path.name
        plan.moves.append(Move(rel(path, root), target.as_posix()))
    entry = "学习系统/发音/练习/练习入口.md"
    add_create_if_changed(root, plan, entry, practice_entry_text())
    for name in ("無題のファイル.base", "無題のファイル 1.base"):
        path = root / "学习系统/课堂复习/词汇" / name
        if path.is_file():
            plan.deletes.append(Delete(rel(path, root)))
    for name in ("fix_all_links.py", "test_parse.py"):
        path = root / name
        if path.is_file():
            plan.moves.append(Move(name, f"tmp/legacy/{name}"))
    plan.replacements.update(
        {
            "学习系统/发音/漢字辨析": "学习系统/发音/读音辨析",
            "学习系统/发音/其他": "学习系统/发音/素材",
        }
    )
    return plan


def build_system_plan(root: Path) -> PhasePlan:
    plan = PhasePlan("system")
    add_tree_moves(root, "学习系统/模板", "学习系统/系统/模板", plan)
    add_tree_moves(root, "学习系统/面板", "学习系统/系统/面板", plan)
    old_config = root / "学习系统/系统配置/paths.json"
    if old_config.is_file():
        plan.moves.append(Move("学习系统/系统配置/paths.json", "学习系统/系统/配置/paths.json"))
    should_materialize = any(
        path.exists()
        for path in (
            root / "学习系统/模板",
            root / "学习系统/面板",
            root / "学习系统/系统配置/paths.json",
            root / "学习系统/系统",
            root / "学习系统/总训练入口.md",
        )
    )
    if should_materialize:
        add_create_if_changed(root, plan, "学习系统/系统/配置/paths.json", intermediate_paths_config_text())
        add_create_if_changed(root, plan, "学习系统/系统/复习流程.md", intermediate_review_flow_text())
    if (root / "学习系统/总训练入口.md").is_file():
        plan.deletes.append(Delete("学习系统/总训练入口.md"))
    plan.replacements.update(
        {
            "学习系统/模板": "学习系统/系统/模板",
            "学习系统/面板": "学习系统/系统/面板",
            "学习系统/系统配置/paths.json": "学习系统/系统/配置/paths.json",
            "学习系统/总训练入口.md": "学习系统/系统/面板/总训练.base",
            "学习系统/总训练入口": "学习系统/系统/面板/总训练.base",
        }
    )
    return plan


def build_content_plan(root: Path) -> PhasePlan:
    plan = PhasePlan("content")
    add_tree_moves(root, "学习系统/课堂复习/词汇", "学习系统/词库/重点词汇", plan)
    add_tree_moves(root, "学习系统/课堂复习/语法", "学习系统/语法", plan)
    add_tree_moves(root, "学习系统/课堂复习/错题", "学习系统/错题", plan)
    add_tree_moves(root, "学习系统/系统/模板", "系统配置/模板", plan)
    for source, target in (
        ("学习系统/系统/配置/paths.json", "系统配置/paths.json"),
        ("学习系统/系统/面板/总训练.base", "学习系统/总训练.base"),
        ("学习系统/系统/复习流程.md", "系统配置/复习流程.md"),
    ):
        if (root / source).is_file():
            plan.moves.append(Move(source, target))
    add_create_if_changed(root, plan, "系统配置/paths.json", paths_config_text())
    add_create_if_changed(root, plan, "系统配置/复习流程.md", review_flow_text())
    plan.replacements.update(
        {
            "学习系统/课堂复习/词汇": "学习系统/词库/重点词汇",
            "学习系统/课堂复习/语法": "学习系统/语法",
            "学习系统/课堂复习/错题": "学习系统/错题",
            "学习系统/系统/模板": "系统配置/模板",
            "学习系统/系统/配置/paths.json": "系统配置/paths.json",
            "学习系统/系统/面板/总训练.base": "学习系统/总训练.base",
            "学习系统/系统/复习流程.md": "系统配置/复习流程.md",
            'if(track == "class_review", "课堂复习"': 'if(track == "class_review", "重点复习"',
            "name: 课堂高风险": "name: 重点复习高风险",
        }
    )
    return plan


def listening_material_dir(path: Path, listening_root: Path) -> Path:
    parent = path.parent
    if parent.name == "audio":
        if parent.parent.name == "assets":
            return parent.parent.parent
        return parent.parent
    if parent.name == "assets":
        return parent.parent
    return parent


def build_listening_plan(root: Path) -> PhasePlan:
    plan = PhasePlan("listening")
    listening_root = root / "学习系统/听力"
    if not listening_root.exists():
        return plan
    for path in sorted(listening_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in MEDIA_SUFFIXES:
            if path.parent.name == "attach":
                continue
            material = listening_material_dir(path, listening_root)
            target = material / "attach" / path.name
            plan.moves.append(Move(rel(path, root), rel(target, root)))
            continue
        if path.name.endswith((".listenkit.md", ".listenkit.json")) and path.parent.name != "artifacts":
            target = path.parent / "artifacts" / path.name
            plan.moves.append(Move(rel(path, root), rel(target, root)))
    return plan


def build_phase_plan(root: Path, phase: str) -> PhasePlan:
    builders = {
        "pronunciation": build_pronunciation_plan,
        "system": build_system_plan,
        "listening": build_listening_plan,
        "content": build_content_plan,
    }
    return builders[phase](root)


def moved_path(path: Path, moves: list[Move]) -> Path:
    raw = path.as_posix()
    lookup = {move.source: move.target for move in moves}
    return Path(lookup.get(raw, raw))


def rewrite_text(source: Path, text: str, moves: list[Move], replacements: dict[str, str]) -> str:
    lines = text.splitlines(keepends=True)
    for old, new in sorted(replacements.items(), key=lambda item: -len(item[0])):
        lines = [
            line
            if "legacy fallback" in line or (source.as_posix() == ".obsidian/workspace.json" and "tmp/directory-refactor-backup/" in line)
            else line.replace(old, new)
            for line in lines
        ]
    rewritten = "".join(lines)
    for move in moves:
        rewritten = rewritten.replace(move.source, move.target)
        old = Path(move.source)
        new = Path(move.target)
        if old.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        if source.parent.as_posix() == old.parent.as_posix() and new.parent.name == "attach":
            reference = f"attach/{new.name}"
        else:
            reference = new.as_posix()
        rewritten = rewritten.replace(f"[[{old.name}", f"[[{reference}")
        rewritten = re.sub(
            rf"(^audio_ref:\s*){re.escape(old.name)}(\s*$)",
            rf"\1{reference}\2",
            rewritten,
            flags=re.MULTILINE,
        )
    return rewritten


def text_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.relative_to(root).as_posix() == ".obsidian/workspace.json":
            continue
        if path.is_relative_to(root / "tools/vault-structure"):
            continue
        result.append(path)
    return sorted(result)


def calculate_rewrites(root: Path, plan: PhasePlan) -> dict[str, str]:
    rewrites: dict[str, str] = {}
    for path in text_files(root):
        relative = Path(rel(path, root))
        updated = rewrite_text(relative, path.read_text(encoding="utf-8"), plan.moves, plan.replacements)
        if updated != path.read_text(encoding="utf-8"):
            rewrites[moved_path(relative, plan.moves).as_posix()] = updated
    return rewrites


def validate_plan(root: Path, plan: PhasePlan) -> None:
    targets: set[str] = set()
    for move in plan.moves:
        if move.target in targets:
            raise RuntimeError(f"duplicate move target: {move.target}")
        targets.add(move.target)
        target = root / move.target
        if target.exists() and move.source != move.target:
            raise RuntimeError(f"move target already exists: {move.target}")


def backup_file(root: Path, backup_files: Path, relative: str) -> None:
    source = root / relative
    if not source.is_file():
        return
    target = backup_files / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def prune_empty_dirs(root: Path) -> None:
    for path in sorted((root / "学习系统").rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def apply_plan(root: Path, plan: PhasePlan, rewrites: dict[str, str]) -> Path:
    validate_plan(root, plan)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / "tmp/directory-refactor-backup" / f"{timestamp}-{plan.phase}"
    backup_files = backup_root / "files"
    originals = {move.source for move in plan.moves} | {delete.path for delete in plan.deletes}
    for target in rewrites:
        original = next((move.source for move in plan.moves if move.target == target), target)
        originals.add(original)
    for relative in sorted(originals):
        backup_file(root, backup_files, relative)
    manifest = {
        "phase": plan.phase,
        "moves": [asdict(move) for move in plan.moves],
        "creates": [create.path for create in plan.creates],
        "deletes": [delete.path for delete in plan.deletes],
        "rewrites": sorted(rewrites),
    }
    backup_root.mkdir(parents=True, exist_ok=True)
    (backup_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for move in plan.moves:
        source = root / move.source
        if not source.exists():
            continue
        target = root / move.target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    for target, content in rewrites.items():
        path = root / target
        if path.exists():
            path.write_text(content, encoding="utf-8")
    for create in plan.creates:
        path = root / create.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(create.content, encoding="utf-8")
    for delete in plan.deletes:
        path = root / delete.path
        if path.is_file():
            path.unlink()
    prune_empty_dirs(root)
    return backup_root


def print_plan(plan: PhasePlan, rewrites: dict[str, str]) -> None:
    print(f"Phase: {plan.phase}")
    print(f"Moves: {len(plan.moves)}")
    for move in plan.moves:
        print(f"  MOVE {move.source} -> {move.target}")
    print(f"Creates: {len(plan.creates)}")
    for create in plan.creates:
        print(f"  CREATE {create.path}")
    print(f"Deletes: {len(plan.deletes)}")
    for delete in plan.deletes:
        print(f"  DELETE {delete.path}")
    print(f"Rewrites: {len(rewrites)}")
    for path in rewrites:
        print(f"  REWRITE {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or apply staged Japanese-learning vault layout migrations.")
    parser.add_argument("--vault-root", default=".", help="Vault root. Defaults to the current directory.")
    parser.add_argument("--phase", choices=("pronunciation", "system", "listening", "content"), required=True)
    parser.add_argument("--apply", action="store_true", help="Apply the previewed migration and write a backup manifest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.vault_root).expanduser().resolve()
    plan = build_phase_plan(root, args.phase)
    validate_plan(root, plan)
    rewrites = calculate_rewrites(root, plan)
    print_plan(plan, rewrites)
    if args.apply:
        backup = apply_plan(root, plan, rewrites)
        print(f"Backup: {backup.relative_to(root)}")
    else:
        print("Preview only. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
