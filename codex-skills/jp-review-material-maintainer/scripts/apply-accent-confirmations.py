#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ACCENT_RE = re.compile(r"[⓪①②③④⑤⑥⑦⑧⑨]")
KANJI_RE = re.compile(r"[一-龯]")


class AccentApplyError(Exception):
    pass


def split_frontmatter(text: str, path: Path) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AccentApplyError(f"{path}: missing frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise AccentApplyError(f"{path}: missing frontmatter end delimiter")
    return text[4:end], text[end + 4 :]


def get_scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", frontmatter)
    if not match:
        return ""
    return match.group(1).strip().strip('"')


def set_scalar(frontmatter: str, key: str, value: str, after_key: str | None = None) -> str:
    lines = frontmatter.splitlines()
    field_line = f"{key}: {value}"
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*", line):
            lines[index] = field_line
            return "\n".join(lines)
    insert_at = len(lines)
    if after_key:
        for index, line in enumerate(lines):
            if re.match(rf"^{re.escape(after_key)}:\s*", line):
                insert_at = index + 1
                break
    lines.insert(insert_at, field_line)
    return "\n".join(lines)


def strip_accent_marks(value: str) -> str:
    return re.sub(r"\s*[⓪①②③④⑤⑥⑦⑧⑨]", "", value).strip()


def split_items(value: str) -> list[str]:
    value = strip_accent_marks(value)
    value = re.sub(r"\s*[（(][ぁ-んァ-ンー・/／\s]+[）)]\s*$", "", value).strip()
    return [part.strip() for part in re.split(r"\s*/\s*|／|・|、", value) if part.strip()]


def update_body_accent(body: str, accent_display: str) -> str:
    line = f"- 重音：{accent_display}"
    if re.search(r"(?m)^- 重音：", body):
        return re.sub(r"(?m)^- 重音：.*$", line, body, count=1)
    core_heading = re.search(r"(?m)^## 核心\s*$", body)
    if core_heading:
        position = core_heading.end()
        return body[:position] + "\n\n" + line + body[position:]
    title = re.search(r"(?m)^# .+$", body)
    if title:
        position = title.end()
        return body[:position] + "\n\n## 核心\n\n" + line + body[position:]
    return "## 核心\n\n" + line + "\n\n" + body


def validate_row(row: dict[str, str], path: Path, accent_display: str, frontmatter: str) -> None:
    if not ACCENT_RE.search(accent_display):
        raise AccentApplyError(f"{path}: confirmed accent_display has no accent mark: {accent_display!r}")
    if KANJI_RE.search(accent_display):
        raise AccentApplyError(f"{path}: confirmed accent_display contains kanji: {accent_display!r}")
    headword_items = split_items(get_scalar(frontmatter, "headword"))
    accent_items = split_items(accent_display)
    if len(headword_items) > 1 and len(headword_items) != len(accent_items):
        raise AccentApplyError(
            f"{path}: multi-item mismatch, headword has {len(headword_items)} items but accent has {len(accent_items)}"
        )


def build_updated_text(path: Path, accent_display: str) -> str:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text, path)
    validate_row({}, path, accent_display, frontmatter)
    headword = strip_accent_marks(get_scalar(frontmatter, "headword"))
    reading = strip_accent_marks(get_scalar(frontmatter, "reading"))
    frontmatter = set_scalar(frontmatter, "headword", headword)
    frontmatter = set_scalar(frontmatter, "reading", reading)
    frontmatter = set_scalar(frontmatter, "accent_display", accent_display, after_key="reading")
    body = update_body_accent(body, accent_display)
    return "---\n" + frontmatter.rstrip() + "\n---" + body


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply NHK-confirmed accent_display values to vocab cards.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="学习系统/词库/重音标注全量草稿.csv",
        help="CSV generated for the full accent audit.",
    )
    parser.add_argument("--write", action="store_true", help="Write changes. Omit for dry-run.")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise AccentApplyError(f"CSV not found: {csv_path}")

    confirmed: list[tuple[Path, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("nhk_status", "").strip() != "confirmed":
                continue
            accent_display = row.get("candidate_accent_display", "").strip()
            if not accent_display:
                raise AccentApplyError(f"{row.get('path')}: confirmed row has empty candidate_accent_display")
            confirmed.append((Path(row["path"]), accent_display))

    changed = 0
    for path, accent_display in confirmed:
        if not path.exists():
            raise AccentApplyError(f"Confirmed target is missing: {path}")
        old_text = path.read_text(encoding="utf-8")
        new_text = build_updated_text(path, accent_display)
        if old_text == new_text:
            continue
        changed += 1
        if args.write:
            path.write_text(new_text, encoding="utf-8")
        print(f"{'WRITE' if args.write else 'DRY'} {path}: {accent_display}")

    print(f"confirmed rows: {len(confirmed)}")
    print(f"changed cards: {changed}")
    print("mode:", "write" if args.write else "dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
