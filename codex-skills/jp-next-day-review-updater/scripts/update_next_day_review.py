#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

DEFAULT_PATHS_CONFIG = Path("系统配置/paths.json")

TRACK_LABELS = {
    "class_review": "重点复习",
    "survival_speaking": "生活口语",
    "listening": "听力",
    "pronunciation": "发音",
}

STAGE_DAYS = {
    "day0": 0,
    "day1": 1,
    "day3": 3,
    "day7": 7,
    "day14": 14,
    "day30": 30,
    "day90": 90,
    "day180": 180,
}

STAGE_RULES = {
    "day0": "day1",
    "day1": "day3",
    "day3": "day7",
    "day7": "day14",
    "day14": "day30",
    "day30": "day90",
    "day90": "day180",
    "day180": "mastered",
}

ACTIVE_REVIEW_STAGES = set(STAGE_RULES)
TERMINAL_REVIEW_STAGES = {"mastered"}
CHECKLIST_MARKERS = ("## 每日学习清单\n", "## 每日學習清單\n")


class ReviewUpdateError(RuntimeError):
    pass


@dataclass
class ItemState:
    path: Path
    text: str
    status: str
    item_type: str
    done_today: bool
    review_stage: str
    next_review: date | None
    last_reviewed_raw: str
    first_seen: date
    track: str
    label: str
    new_text: str | None = None
    new_status: str | None = None
    new_stage: str | None = None
    new_next_review: date | None = None
    transition_from: str | None = None
    advanced: bool = False
    delay_rescheduled: bool = False


@dataclass
class PendingWrite:
    path: Path
    text: str


@dataclass(frozen=True)
class PathsConfig:
    managed_review_roots: tuple[Path, ...]
    base_vocab_root: Path
    daily_notes_root: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update next-day review items in the Japanese learning vault.")
    parser.add_argument("--vault-root", required=True, help="Absolute path to the vault root.")
    parser.add_argument("--date", help="Run date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned updates without writing files.")
    parser.add_argument("--note-path", help="Override the target daily note path.")
    parser.add_argument(
        "--paths-config",
        default=str(DEFAULT_PATHS_CONFIG),
        help="Vault-relative or absolute JSON file containing managed path roles.",
    )
    return parser.parse_args()


def resolve_vault_path(vault_root: Path, raw_path: str | Path, field_name: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        raise ReviewUpdateError(f"{field_name} must be vault-relative, got absolute path {path}")
    if ".." in path.parts:
        raise ReviewUpdateError(f"{field_name} must stay inside the vault, got {path}")
    return vault_root / path


def load_paths_config(vault_root: Path, raw_config_path: str) -> PathsConfig:
    config_path = Path(raw_config_path).expanduser()
    if not config_path.is_absolute():
        config_path = vault_root / config_path
    try:
        raw_config = json.loads(config_path.read_text())
    except OSError as exc:
        raise ReviewUpdateError(f"unable to read paths config {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewUpdateError(f"invalid paths config JSON {config_path}: {exc}") from exc

    try:
        managed_roots = raw_config["managed_review_roots"]
        base_vocab_root = raw_config["base_vocab_root"]
        daily_notes_root = raw_config["daily_notes_root"]
    except KeyError as exc:
        raise ReviewUpdateError(f"paths config {config_path} is missing {exc.args[0]!r}") from exc

    if not isinstance(managed_roots, list) or not all(isinstance(root, str) for root in managed_roots):
        raise ReviewUpdateError(f"paths config {config_path}: managed_review_roots must be a list of strings")
    if not isinstance(base_vocab_root, str) or not isinstance(daily_notes_root, str):
        raise ReviewUpdateError(f"paths config {config_path}: base_vocab_root and daily_notes_root must be strings")
    if not managed_roots:
        raise ReviewUpdateError(f"paths config {config_path}: managed_review_roots must not be empty")

    return PathsConfig(
        managed_review_roots=tuple(
            resolve_vault_path(vault_root, root, f"managed_review_roots[{index}]")
            for index, root in enumerate(managed_roots)
        ),
        base_vocab_root=resolve_vault_path(vault_root, base_vocab_root, "base_vocab_root"),
        daily_notes_root=resolve_vault_path(vault_root, daily_notes_root, "daily_notes_root"),
    )


def parse_iso_date(raw: str, field_name: str, path: Path) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ReviewUpdateError(f"{path}: invalid {field_name} value {raw!r}") from exc


def get_field(text: str, key: str, path: Path, required: bool = True) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    if required:
        raise ReviewUpdateError(f"{path}: missing frontmatter field {key!r}")
    return ""


def replace_field(text: str, key: str, value: str, path: Path) -> str:
    new_text, count = re.subn(
        rf"^{re.escape(key)}:\s*.*$",
        f"{key}: {value}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ReviewUpdateError(f"{path}: unable to rewrite frontmatter field {key!r}")
    return new_text


def ensure_list_item(text: str, key: str, item: str, path: Path, default_indent: str = "") -> str:
    pattern = re.compile(rf"(?m)^({re.escape(key)}:\s*\n)((?:[ \t]*- [^\n]*\n)*)")
    match = pattern.search(text)
    if not match:
        raise ReviewUpdateError(f"{path}: missing list field {key!r}")
    block = match.group(2)
    existing_items = [line.strip()[2:].strip() for line in block.splitlines() if line.strip()]
    if item in existing_items:
        return text
    indent = default_indent
    if block.splitlines():
        first_line = block.splitlines()[0]
        indent = first_line[: len(first_line) - len(first_line.lstrip())]
    updated_block = block + f"{indent}- {item}\n"
    return text[: match.start(2)] + updated_block + text[match.end(2) :]


def extract_list_field(text: str, key: str, path: Path) -> list[str]:
    pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*\n((?:[ \t]*- [^\n]*\n)*)")
    match = pattern.search(text)
    if not match:
        raise ReviewUpdateError(f"{path}: missing list field {key!r}")
    return [line.strip()[2:].strip().strip('"') for line in match.group(1).splitlines() if line.strip()]


def extract_optional_list_field(text: str, key: str, path: Path) -> list[str]:
    inline_empty_pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*\[\]\s*$")
    if inline_empty_pattern.search(text):
        return []
    pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*\n((?:[ \t]*- [^\n]*\n)*)")
    match = pattern.search(text)
    if not match:
        return []
    return [line.strip()[2:].strip().strip('"') for line in match.group(1).splitlines() if line.strip()]


def parse_optional_iso_date(raw: str, field_name: str, path: Path) -> date | None:
    cleaned = raw.strip().strip('"')
    if not cleaned:
        return None
    return parse_iso_date(cleaned, field_name, path)


def parse_int_field(raw: str, field_name: str, path: Path) -> int:
    try:
        return int(raw.strip().strip('"'))
    except ValueError as exc:
        raise ReviewUpdateError(f"{path}: invalid {field_name} value {raw!r}") from exc


def merge_source_links(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    for link in incoming:
        if link not in merged:
            merged.append(link)
    return merged


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    for item in incoming:
        if item not in merged:
            merged.append(item)
    return merged


def get_bool_field_or_default(text: str, key: str, path: Path, default: str = "false") -> str:
    raw = get_field(text, key, path, required=False).strip().strip('"')
    if not raw:
        return default
    if raw not in {"true", "false"}:
        raise ReviewUpdateError(f"{path}: {key} must be true or false, got {raw!r}")
    return raw


def split_frontmatter(text: str, path: Path) -> tuple[str, list[str], str]:
    if not text.startswith("---\n"):
        raise ReviewUpdateError(f"{path}: missing frontmatter")
    end_marker = text.find("\n---", 4)
    if end_marker == -1:
        raise ReviewUpdateError(f"{path}: missing frontmatter end delimiter")
    return text[:4], text[4:end_marker].splitlines(), text[end_marker:]


def replace_or_insert_frontmatter_scalar(text: str, key: str, value: str, path: Path) -> str:
    prefix, lines, suffix = split_frontmatter(text, path)
    field_line = f"{key}: {value}"
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*", line):
            lines[index] = field_line
            return prefix + "\n".join(lines) + suffix
    lines.append(field_line)
    return prefix + "\n".join(lines) + suffix


def format_frontmatter_list(key: str, items: list[str]) -> list[str]:
    if not items:
        return [f"{key}: []"]
    return [f"{key}:"] + [f"- {item}" for item in items]


def replace_or_insert_frontmatter_list(text: str, key: str, items: list[str], path: Path) -> str:
    prefix, lines, suffix = split_frontmatter(text, path)
    replacement = format_frontmatter_list(key, items)
    for index, line in enumerate(lines):
        if not re.match(rf"^{re.escape(key)}:\s*", line):
            continue
        end = index + 1
        while end < len(lines) and re.match(r"^[ \t]*- ", lines[end]):
            end += 1
        lines[index:end] = replacement
        return prefix + "\n".join(lines) + suffix
    lines.extend(replacement)
    return prefix + "\n".join(lines) + suffix


def ensure_optional_list_item(text: str, key: str, item: str, path: Path) -> str:
    inline_empty_pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*\[\]\s*$")
    if inline_empty_pattern.search(text):
        return inline_empty_pattern.sub(f"{key}:\n- {item}", text, count=1)
    if re.search(rf"(?m)^{re.escape(key)}:\s*\n", text):
        return ensure_list_item(text, key, item, path)
    if not text.startswith("---\n"):
        raise ReviewUpdateError(f"{path}: missing frontmatter")
    end_marker = text.find("\n---", 4)
    if end_marker == -1:
        raise ReviewUpdateError(f"{path}: missing frontmatter end delimiter")
    block = f"\n{key}:\n- {item}"
    return text[:end_marker] + block + text[end_marker:]


def update_body_sources(text: str, sources: list[str]) -> str:
    marker = "## 来源\n"
    body_lines = [f"- {source}" for source in sources]
    body = marker + "\n" + "\n".join(body_lines) + "\n"
    if marker not in text:
        return text.rstrip() + "\n\n" + body
    start = text.index(marker)
    next_heading = re.search(r"(?m)^##\s+", text[start + len(marker) :])
    if not next_heading:
        return text[:start].rstrip() + "\n\n" + body
    end = start + len(marker) + next_heading.start()
    return text[:start].rstrip() + "\n\n" + body.rstrip() + "\n\n" + text[end:].lstrip()


def render_base_note(
    note_title: str,
    headword: str,
    reading: str,
    accent_display: str,
    meaning_zh: str,
    source_notes: list[str],
    first_seen: date,
    last_seen: date,
    seen_count: int,
    kanji_diff: str,
    kanji_diff_pairs: list[str],
) -> str:
    source_lines = "\n".join(f'- "{source}"' for source in source_notes)
    body_lines = "\n".join(f"- {source}" for source in source_notes)
    tags = ["jp/vocab", "jp/base_vocab", "jp/class_review", "jp/promoted"]
    if kanji_diff == "true":
        tags.append("jp/kanji_diff")
    tag_lines = "\n".join(f"- {tag}" for tag in tags)
    kanji_diff_pair_lines = "\n".join(format_frontmatter_list("kanji_diff_pairs", kanji_diff_pairs))
    accent_line = f"accent_display: {accent_display}\n" if accent_display else ""
    return (
        "---\n"
        f"headword: {headword}\n"
        "aliases:\n"
        f"- {yaml_quote(headword)}\n"
        f"reading: {reading}\n"
        f"{accent_line}"
        f"meaning_zh: {meaning_zh}\n"
        "source_notes:\n"
        f"{source_lines}\n"
        f"first_seen: {first_seen.isoformat()}\n"
        f"last_seen: {last_seen.isoformat()}\n"
        f"seen_count: {seen_count}\n"
        "status: promoted\n"
        "promote_candidate: false\n"
        f"kanji_diff: {kanji_diff}\n"
        f"{kanji_diff_pair_lines}\n"
        "tags:\n"
        f"{tag_lines}\n"
        "---\n\n"
        f"# {note_title}\n\n"
        "## 来源\n\n"
        f"{body_lines}\n"
    )


def extract_label(text: str, path: Path) -> str:
    for key in ("headword", "pattern", "jp_text", "target_text"):
        value = get_field(text, key, path, required=False).strip().strip('"')
        if value:
            return value
    return path.stem


def is_icloud_dataless_placeholder(stat_result: object) -> bool:
    return getattr(stat_result, "st_size", 0) > 0 and getattr(stat_result, "st_blocks", 1) == 0


def stat_review_item(path: Path) -> object:
    try:
        return path.stat()
    except OSError as exc:
        raise ReviewUpdateError(f"{path}: unable to stat review item") from exc


def load_items(paths_config: PathsConfig) -> list[ItemState]:
    items: list[ItemState] = []
    for root_path in paths_config.managed_review_roots:
        if not root_path.exists():
            raise ReviewUpdateError(f"Managed root is missing: {root_path}")
        for path in sorted(root_path.rglob("*.md")):
            if is_icloud_dataless_placeholder(stat_review_item(path)):
                print(f"Skipping iCloud placeholder file: {path}")
                continue
            text = path.read_text()
            if not text.startswith("---\n"):
                continue
            status = get_field(text, "status", path)
            item_type = get_field(text, "item_type", path, required=False)
            done_today_raw = get_field(text, "done_today", path)
            review_stage = get_field(text, "review_stage", path)
            next_review_raw = get_field(text, "next_review", path, required=False)
            last_reviewed_raw = get_field(text, "last_reviewed", path)
            first_seen_raw = get_field(text, "first_seen", path)
            track = get_field(text, "track", path)
            if track not in TRACK_LABELS:
                raise ReviewUpdateError(f"{path}: unsupported track value {track!r}")
            if status == "active" and review_stage not in ACTIVE_REVIEW_STAGES:
                raise ReviewUpdateError(f"{path}: unsupported review_stage {review_stage!r}")
            if status != "active" and review_stage not in ACTIVE_REVIEW_STAGES | TERMINAL_REVIEW_STAGES:
                raise ReviewUpdateError(f"{path}: unsupported review_stage {review_stage!r}")
            if done_today_raw not in {"true", "false"}:
                raise ReviewUpdateError(f"{path}: done_today must be true or false, got {done_today_raw!r}")
            next_review = parse_optional_iso_date(next_review_raw, "next_review", path)
            if status == "active" and next_review is None:
                raise ReviewUpdateError(f"{path}: active item is missing next_review")
            first_seen = parse_iso_date(first_seen_raw.strip('"'), "first_seen", path)
            items.append(
                ItemState(
                    path=path,
                    text=text,
                    status=status,
                    item_type=item_type,
                    done_today=(done_today_raw == "true"),
                    review_stage=review_stage,
                    next_review=next_review,
                    last_reviewed_raw=last_reviewed_raw,
                    first_seen=first_seen,
                    track=track,
                    label=extract_label(text, path),
                )
            )
    return items


def is_focus_vocab(item: ItemState) -> bool:
    return item.track == "class_review" and item.item_type == "vocab"


def build_base_note_write(base_vocab_root: Path, item: ItemState) -> PendingWrite:
    if item.new_text is None:
        raise ReviewUpdateError(f"{item.path}: missing updated text for sink operation")
    headword = get_field(item.new_text, "headword", item.path).strip('"')
    reading = get_field(item.new_text, "reading", item.path).strip('"')
    accent_display = get_field(item.new_text, "accent_display", item.path, required=False).strip().strip('"')
    meaning_zh = get_field(item.new_text, "meaning_zh", item.path).strip('"')
    source_notes = extract_list_field(item.new_text, "source_notes", item.path)
    first_seen = parse_iso_date(get_field(item.new_text, "first_seen", item.path).strip('"'), "first_seen", item.path)
    last_seen = parse_iso_date(get_field(item.new_text, "last_seen", item.path).strip('"'), "last_seen", item.path)
    seen_count = parse_int_field(get_field(item.new_text, "seen_count", item.path), "seen_count", item.path)
    incoming_kanji_diff = get_bool_field_or_default(item.new_text, "kanji_diff", item.path)
    incoming_kanji_diff_pairs = extract_optional_list_field(item.new_text, "kanji_diff_pairs", item.path)
    note_title = item.path.stem
    base_path = base_vocab_root / f"{note_title}.md"
    if not base_path.exists():
        return PendingWrite(
            path=base_path,
            text=render_base_note(
                note_title,
                headword,
                reading,
                accent_display,
                meaning_zh,
                source_notes,
                first_seen,
                last_seen,
                seen_count,
                incoming_kanji_diff,
                incoming_kanji_diff_pairs,
            ),
        )

    base_text = base_path.read_text()
    existing_sources = extract_list_field(base_text, "source_notes", base_path)
    merged_sources = merge_source_links(existing_sources, source_notes)
    existing_first_seen = parse_iso_date(get_field(base_text, "first_seen", base_path).strip('"'), "first_seen", base_path)
    existing_last_seen = parse_iso_date(get_field(base_text, "last_seen", base_path).strip('"'), "last_seen", base_path)
    existing_seen_count = parse_int_field(get_field(base_text, "seen_count", base_path), "seen_count", base_path)
    existing_kanji_diff = get_bool_field_or_default(base_text, "kanji_diff", base_path)
    existing_kanji_diff_pairs = extract_optional_list_field(base_text, "kanji_diff_pairs", base_path)
    merged_kanji_diff = "true" if "true" in {existing_kanji_diff, incoming_kanji_diff} else "false"
    merged_kanji_diff_pairs = merge_unique(existing_kanji_diff_pairs, incoming_kanji_diff_pairs)
    updated_text = base_text
    updated_text = replace_field(updated_text, "reading", reading, base_path)
    if accent_display:
        updated_text = replace_or_insert_frontmatter_scalar(updated_text, "accent_display", accent_display, base_path)
    updated_text = replace_field(updated_text, "meaning_zh", meaning_zh, base_path)
    updated_text = replace_field(updated_text, "first_seen", min(existing_first_seen, first_seen).isoformat(), base_path)
    updated_text = replace_field(updated_text, "last_seen", max(existing_last_seen, last_seen).isoformat(), base_path)
    updated_text = replace_field(updated_text, "seen_count", str(max(existing_seen_count, seen_count)), base_path)
    updated_text = replace_field(updated_text, "status", "promoted", base_path)
    updated_text = replace_field(updated_text, "promote_candidate", "false", base_path)
    updated_text = ensure_optional_list_item(updated_text, "aliases", yaml_quote(headword), base_path)
    updated_text = replace_or_insert_frontmatter_scalar(updated_text, "kanji_diff", merged_kanji_diff, base_path)
    updated_text = replace_or_insert_frontmatter_list(updated_text, "kanji_diff_pairs", merged_kanji_diff_pairs, base_path)
    for source in merged_sources:
        updated_text = ensure_list_item(updated_text, "source_notes", f'"{source}"', base_path)
    updated_text = ensure_list_item(updated_text, "tags", "jp/promoted", base_path)
    if merged_kanji_diff == "true":
        updated_text = ensure_list_item(updated_text, "tags", "jp/kanji_diff", base_path)
    updated_text = update_body_sources(updated_text, merged_sources)
    return PendingWrite(path=base_path, text=updated_text)


def prepare_item_updates(
    items: Iterable[ItemState], run_date: date, paths_config: PathsConfig
) -> tuple[list[ItemState], dict[str, int], dict[str, int], int, int, list[PendingWrite]]:
    processed: list[ItemState] = []
    stage_counts: dict[str, int] = {}
    track_counts = {track: 0 for track in TRACK_LABELS}
    mastered_vocab_count = 0
    delayed_count = 0
    base_writes: list[PendingWrite] = []

    for item in items:
        if item.status != "active" or not item.done_today:
            continue
        new_text = item.text
        if item.next_review is None:
            raise ReviewUpdateError(f"{item.path}: active completed item is missing next_review")

        allowed_delay = max(1, STAGE_DAYS[item.review_stage])
        overdue_days = (run_date - item.next_review).days
        should_advance = overdue_days <= allowed_delay

        if should_advance:
            next_stage = STAGE_RULES[item.review_stage]
        else:
            next_stage = item.review_stage
            delayed_count += 1

        if next_stage == "mastered":
            new_text = replace_field(new_text, "status", "mastered", item.path)
            new_text = replace_field(new_text, "done_today", "false", item.path)
            new_text = replace_field(new_text, "review_stage", "mastered", item.path)
            new_text = replace_field(new_text, "next_review", "", item.path)
            new_text = replace_field(new_text, "last_reviewed", run_date.isoformat(), item.path)
            item.new_text = new_text
            item.new_status = "mastered"
            item.new_stage = "mastered"
            item.new_next_review = None
            item.transition_from = item.review_stage
            item.advanced = True
            processed.append(item)
            stage_counts[f"{item.review_stage} → mastered"] = stage_counts.get(f"{item.review_stage} → mastered", 0) + 1
            track_counts[item.track] += 1
            if is_focus_vocab(item):
                mastered_vocab_count += 1
                base_writes.append(build_base_note_write(paths_config.base_vocab_root, item))
            continue

        offset_days = STAGE_DAYS[next_stage] if should_advance else allowed_delay
        next_review = run_date + timedelta(days=offset_days)
        new_text = replace_field(new_text, "done_today", "false", item.path)
        new_text = replace_field(new_text, "review_stage", next_stage, item.path)
        new_text = replace_field(new_text, "next_review", next_review.isoformat(), item.path)
        new_text = replace_field(new_text, "last_reviewed", run_date.isoformat(), item.path)
        item.new_text = new_text
        item.new_stage = next_stage
        item.new_next_review = next_review
        item.transition_from = item.review_stage
        item.advanced = should_advance
        item.delay_rescheduled = not should_advance
        processed.append(item)
        transition_label = f"{item.review_stage} → {next_stage}" if should_advance else f"{item.review_stage} 延迟重排"
        stage_counts[transition_label] = stage_counts.get(transition_label, 0) + 1
        track_counts[item.track] += 1

    return processed, stage_counts, track_counts, mastered_vocab_count, delayed_count, base_writes


def simulated_next_review(item: ItemState) -> date | None:
    return item.new_next_review if item.new_text is not None else item.next_review


def simulated_status(item: ItemState) -> str:
    return item.new_status if item.new_status is not None else item.status


def build_next_day_queue(items: Iterable[ItemState], run_date: date) -> list[ItemState]:
    tomorrow = run_date + timedelta(days=1)
    queue = [
        item
        for item in items
        if simulated_status(item) == "active" and simulated_next_review(item) is not None and simulated_next_review(item) <= tomorrow
    ]
    queue.sort(key=lambda item: (item.first_seen, simulated_next_review(item), item.path.as_posix()), reverse=True)
    return queue


def extract_existing_card_points(note_tail: str) -> list[str]:
    match = re.search(
        r"^## (?:今日卡点|今日卡點)\s*\n(?P<body>.*?)(?=^## (?:简短复盘|簡短複盤)\s*$)",
        note_tail,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    lines = [line.rstrip() for line in match.group("body").splitlines()]
    bullets = [line for line in lines if line.strip()]
    return bullets


def format_stage_breakdown(stage_counts: dict[str, int], mastered_vocab_count: int) -> str:
    parts = []
    transition_order = [
        "day0 → day1",
        "day1 → day3",
        "day1 延迟重排",
        "day3 → day7",
        "day3 延迟重排",
        "day7 → day14",
        "day7 延迟重排",
        "day14 → day30",
        "day14 延迟重排",
        "day30 → day90",
        "day30 延迟重排",
        "day90 → day180",
        "day90 延迟重排",
        "day180 → mastered",
        "day180 延迟重排",
    ]
    seen = set()
    for label in transition_order:
        count = stage_counts.get(label, 0)
        if count:
            parts.append(f"{label} 共 {count} 条")
            seen.add(label)
    for label, count in sorted(stage_counts.items()):
        if label in seen or count == 0:
            continue
        parts.append(f"{label} 共 {count} 条")
    if mastered_vocab_count > 0:
        parts.append(f"词汇沉底 共 {mastered_vocab_count} 条")
    return "，".join(parts) if parts else "今日没有需要推进的复习阶段"


def format_track_breakdown(track_counts: dict[str, int]) -> str:
    return "、".join(
        f"{TRACK_LABELS[track]} {count} 条"
        for track, count in track_counts.items()
        if count > 0
    ) or "今日没有已完成复习条目"


def format_label_list(labels: list[str], limit: int | None = None) -> str:
    if limit is not None:
        labels = labels[:limit]
    return "、".join(labels)


def split_at_checklist_marker(original_text: str) -> tuple[str, str] | None:
    matches = []
    for marker in CHECKLIST_MARKERS:
        index = original_text.find(marker)
        if index != -1:
            matches.append((index, marker))
    if not matches:
        return None
    start, marker = min(matches)
    return original_text[:start], original_text[start + len(marker) :]


def build_checklist_section(
    note_path: Path,
    original_text: str,
    items: list[ItemState],
    processed: list[ItemState],
    stage_counts: dict[str, int],
    track_counts: dict[str, int],
    mastered_vocab_count: int,
    run_date: date,
) -> str:
    existing_checklist = split_at_checklist_marker(original_text)
    note_tail = existing_checklist[1] if existing_checklist else ""
    existing_card_points = extract_existing_card_points(note_tail)
    if not existing_card_points:
        existing_card_points = ["- 今日未额外记录卡点。"]

    today_new_all = [item for item in items if item.first_seen == run_date]
    today_new_completed = [item for item in processed if item.first_seen == run_date]
    tomorrow = run_date + timedelta(days=1)
    overdue_history = [
        item for item in build_next_day_queue(items, run_date)
        if simulated_next_review(item) < tomorrow
    ]

    next_start_labels = [item.label for item in today_new_completed]
    if not next_start_labels:
        next_start_labels = [item.label for item in build_next_day_queue(items, run_date) if simulated_next_review(item) == tomorrow]

    complete_lines = [
        f"- 已完成总训练收口：推进 {len(processed)} 条（{format_stage_breakdown(stage_counts, mastered_vocab_count)}），并清回 `done_today`",
        f"- 今日实际复习覆盖：{format_track_breakdown(track_counts)}",
        f"- 今日新入系统重点卡 {len(today_new_all)} 条，其中已完成首轮复习 {len(today_new_completed)} 条",
    ]
    if today_new_completed:
        complete_lines.append(f"- 今日新条目已完成首轮复习：{format_label_list([item.label for item in today_new_completed])}")
    else:
        complete_lines.append("- 今日新条目尚无已完成首轮复习项。")

    recap_lines = [
        f"- 今天的拆卡与收口已完成，次日入口会保留 {len(build_next_day_queue(items, run_date))} 条仍需复习的内容",
        f"- 明天开场先做：{format_label_list(next_start_labels, limit=10) if next_start_labels else '当前没有新的明日优先项'}",
    ]
    if overdue_history:
        recap_lines.append(f"- 仍需顺延的历史遗留：{format_label_list([item.label for item in overdue_history], limit=10)}")
    else:
        recap_lines.append("- 当前没有早于明天的历史遗留 overdue 条目。")

    body = "\n".join(
        [
            "## 每日学习清单",
            "",
            "## 今日完成",
            "",
            *complete_lines,
            "",
            "## 今日卡点",
            "",
            *existing_card_points,
            "",
            "## 简短复盘",
            "",
            *recap_lines,
            "",
        ]
    )
    if existing_checklist:
        prefix, _ = existing_checklist
        return prefix.rstrip() + "\n\n" + body
    return original_text.rstrip() + "\n\n" + body


def default_note_path(paths_config: PathsConfig, run_date: date) -> Path:
    return paths_config.daily_notes_root / f"{run_date.year}.{run_date.month}" / f"{run_date.year}.{run_date.month}.{run_date.day}.md"


def resolve_note_path(vault_root: Path, paths_config: PathsConfig, run_date: date, raw_note_path: str | None) -> Path:
    if not raw_note_path:
        return default_note_path(paths_config, run_date)
    note_path = Path(raw_note_path)
    return note_path if note_path.is_absolute() else vault_root / note_path


def main() -> int:
    args = parse_args()
    vault_root = Path(args.vault_root).expanduser().resolve()
    run_date = parse_iso_date(args.date, "date", Path("--date")) if args.date else date.today()
    note_missing = False

    try:
        paths_config = load_paths_config(vault_root, args.paths_config)
        note_path = resolve_note_path(vault_root, paths_config, run_date, args.note_path)
        items = load_items(paths_config)
        processed, stage_counts, track_counts, mastered_vocab_count, delayed_count, base_writes = prepare_item_updates(items, run_date, paths_config)
        new_note: str | None = None
        if note_path.exists():
            original_note = note_path.read_text()
            new_note = build_checklist_section(
                note_path, original_note, items, processed, stage_counts, track_counts, mastered_vocab_count, run_date
            )
        else:
            note_missing = True
    except ReviewUpdateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    next_day_queue = build_next_day_queue(items, run_date)
    today_new_completed = [item.label for item in processed if item.first_seen == run_date]

    print(f"Run date: {run_date.isoformat()}")
    print(f"Target note: {note_path}")
    print(f"Processed items: {len(processed)}")
    print(f"Stage transitions: {format_stage_breakdown(stage_counts, mastered_vocab_count)}")
    print(f"Track coverage: {format_track_breakdown(track_counts)}")
    print(f"Delay reschedules: {delayed_count}")
    print(f"Next-day queue count: {len(next_day_queue)}")
    if mastered_vocab_count:
        print(f"Mastered vocab sinks: {mastered_vocab_count}")
    if today_new_completed:
        print(f"Today new items completed: {format_label_list(today_new_completed)}")
    if note_missing:
        print(f"Skipped daily checklist rewrite because the note is missing: {note_path}")

    if args.dry_run:
        print("Dry run only: no files were written.")
        return 0

    for item in processed:
        assert item.new_text is not None
        item.path.write_text(item.new_text)
    for pending_write in base_writes:
        pending_write.path.parent.mkdir(parents=True, exist_ok=True)
        pending_write.path.write_text(pending_write.text)
    if new_note is not None:
        note_path.write_text(new_note)
        print("Updated review items and daily checklist.")
    else:
        print("Updated review items. Daily checklist rewrite was skipped because the note is missing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
