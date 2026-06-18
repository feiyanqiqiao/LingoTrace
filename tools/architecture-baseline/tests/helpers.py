from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def fixture_path(*parts: str) -> Path:
    return FIXTURES_ROOT.joinpath(*parts)


def read_fixture_text(*parts: str) -> str:
    return fixture_path(*parts).read_text(encoding="utf-8")


def read_fixture_json(*parts: str) -> Any:
    return json.loads(read_fixture_text(*parts))


def parse_markdown_fixture(*parts: str) -> tuple[dict[str, Any], str]:
    return parse_markdown_file(fixture_path(*parts))


def parse_markdown_file(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        raise AssertionError(f"{path} is missing frontmatter end")
    frontmatter = parse_simple_yaml(text[4:end])
    body = text[end + len("\n---") :].lstrip("\n")
    return frontmatter, body


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise AssertionError(f"unsupported frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = parse_scalar(value)
            continue
        items: list[Any] = []
        while index < len(lines) and lines[index].lstrip().startswith("- "):
            item = lines[index].lstrip()[2:].strip()
            items.append(parse_scalar(item))
            index += 1
        data[key] = items if items else ""
    return data


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"')
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def wikilinks(text: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"(?<!!)\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    ]


def embedded_links(text: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    ]


def heading_order(text: str) -> list[str]:
    return [
        match.group(2).strip()
        for match in re.finditer(r"^(#{2,3})\s+(.+)$", text, flags=re.MULTILINE)
    ]


def hash_fixture_file(*parts: str) -> str:
    return hashlib.sha256(fixture_path(*parts).read_bytes()).hexdigest()


def evaluate_migration_fixture() -> dict[str, Any]:
    rules = read_fixture_json("migration-preservation", "rules.json")
    root = fixture_path("migration-preservation")
    source_root = root / "source-vault"
    target_root = root / "target-vault"
    result: dict[str, Any] = {
        "preserved": {},
        "recreated_from_pack": [],
        "removed_after_cutover": [],
        "transforms": {},
        "failures": {},
    }

    for rel_path in rules["preserve_data"]:
        source = source_root / rel_path
        target = target_root / rel_path
        if not target.exists():
            result["failures"][rel_path] = {"reason": "missing_target"}
            continue
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        target_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if source_hash != target_hash:
            result["failures"][rel_path] = {"reason": "content_hash_mismatch"}
            continue
        frontmatter, body = parse_markdown_file(source)
        result["preserved"][rel_path] = {
            "status": "pass",
            "source_hash": source_hash,
            "target_hash": target_hash,
            "frontmatter": frontmatter,
            "wikilinks": wikilinks(body),
            "embeds": embedded_links(body),
        }

    for rel_path in rules["recreate_from_pack"]:
        if rel_path not in result["preserved"]:
            result["recreated_from_pack"].append(rel_path)

    for rel_path in rules["remove_after_cutover"]:
        if rel_path not in result["preserved"]:
            result["removed_after_cutover"].append(rel_path)

    for transform in rules["transforms"]:
        source = source_root / transform["source"]
        target = target_root / transform["target"]
        if source.exists() and target.exists() and transform.get("approved") is True:
            result["transforms"][transform["source"]] = {
                "status": "pass",
                "target": transform["target"],
            }
        else:
            result["failures"][transform["source"]] = {"reason": "invalid_transform"}

    for rel_path, reason in rules["expected_failures"].items():
        result["failures"][rel_path] = {"reason": reason}

    return result
