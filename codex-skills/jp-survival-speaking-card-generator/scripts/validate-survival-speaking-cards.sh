#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"

find_vault_root() {
  local current=""
  for current in "${PWD:A}" "${SCRIPT_DIR}"; do
    while [[ "${current}" != "/" ]]; do
      if [[ -d "${current}/学习系统" && -d "${current}/codex-skills" ]]; then
        echo "${current}"
        return 0
      fi
      current="${current:h}"
    done
  done
  return 1
}

ROOT="$(find_vault_root || true)"
if [[ -z "${ROOT}" ]]; then
  echo "Unable to locate the vault root from ${SCRIPT_DIR}" >&2
  exit 1
fi

DATE="${1:-$(date +%F)}"

python3 - "${ROOT}" <<'PY'
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1])
config_path = root / "系统配置/paths.json"
if not config_path.exists():
    config_path = root / "学习系统/系统/配置/paths.json"  # legacy fallback
if not config_path.exists():
    config_path = root / "学习系统/系统配置/paths.json"  # legacy fallback
roles = json.loads(config_path.read_text()).get("roles", {})
card_root = root / roles.get("speaking_card_root", "学习系统/生活口语/句库")
guide_root = root / roles.get("speaking_guide_root", "学习系统/生活口语/场景指南")
required_fields = (
    "track",
    "status",
    "priority",
    "done_today",
    "scene",
    "speaker_role",
    "function",
    "jp_text",
    "meaning_zh",
    "reply_hint",
    "audio_ref",
    "source_notes",
    "first_seen",
    "last_seen",
    "seen_count",
    "error_count",
    "review_stage",
    "next_review",
    "last_reviewed",
    "tags",
)
nonempty_fields = (
    "track",
    "status",
    "priority",
    "done_today",
    "scene",
    "speaker_role",
    "function",
    "jp_text",
    "meaning_zh",
    "reply_hint",
    "first_seen",
    "last_seen",
    "seen_count",
    "error_count",
    "review_stage",
    "next_review",
)
snake_case = re.compile(r"^[a-z][a-z0-9_]*$")
audio_embed = re.compile(r"!\[\[([^\]|#]+\.(?:m4a|mp3|wav|aac|flac|ogg))(?:\|[^\]]+)?\]\]", re.I)
errors: list[str] = []
jp_text_paths: dict[str, list[Path]] = defaultdict(list)


def fail(path: Path, message: str) -> None:
    errors.append(f"{path.relative_to(root)}: {message}")


def parse_frontmatter(path: Path, text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        fail(path, "missing YAML frontmatter")
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        fail(path, "unterminated YAML frontmatter")
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s*(.*))?$", line)
        if match:
            result[match.group(1)] = (match.group(2) or "").strip().strip('"')
    return result


def resolve_audio(path: Path, target: str) -> Path | None:
    candidates = (root / target, path.parent / target)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


cards = sorted(card_root.rglob("*.md"))
for path in cards:
    relative = path.relative_to(card_root)
    if len(relative.parts) != 2:
        fail(path, "card must live in exactly one scene-category subdirectory")

    text = path.read_text()
    fields = parse_frontmatter(path, text)
    for key in required_fields:
        if key not in fields:
            fail(path, f"missing frontmatter field {key}")
    for key in nonempty_fields:
        if not fields.get(key, ""):
            fail(path, f"frontmatter field {key} must not be empty")

    if fields.get("track") != "survival_speaking":
        fail(path, "track must be survival_speaking")
    if fields.get("speaker_role") not in {"self", "staff", "other"}:
        fail(path, "speaker_role must be self, staff, or other")
    for key in ("scene", "function"):
        value = fields.get(key, "")
        if value and not snake_case.fullmatch(value):
            fail(path, f"{key} must use English snake_case")
    if "fallback_phrase:" in text:
        fail(path, "obsolete fallback_phrase frontmatter is not allowed")

    for heading in ("## 什么时候用", "## 直接这样说", "## 没听懂时"):
        if heading not in text:
            fail(path, f"missing body section {heading}")
    if "## 对方可能怎么说" not in text and "## 我怎么回" not in text:
        fail(path, "missing response body section")

    jp_text = fields.get("jp_text", "")
    if jp_text:
        jp_text_paths[jp_text].append(path)

    audio_ref = fields.get("audio_ref", "")
    if audio_ref and resolve_audio(path, audio_ref) is None:
        fail(path, f"audio_ref does not resolve: {audio_ref}")
    for embed in audio_embed.findall(text):
        if resolve_audio(path, embed) is None:
            fail(path, f"audio embed does not resolve: {embed}")

for jp_text, paths in sorted(jp_text_paths.items()):
    if len(paths) > 1:
        joined = ", ".join(str(path.relative_to(root)) for path in paths)
        errors.append(f"duplicate jp_text {jp_text!r}: {joined}")

if guide_root.exists():
    for path in sorted(guide_root.rglob("*.md")):
        if re.search(r"^track:\s*survival_speaking\s*$", path.read_text(), re.M):
            fail(path, "scene guides must not enter the survival_speaking review queue")

if errors:
    print("Survival-speaking validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"Validated survival-speaking cards: {len(cards)}")
print("Card structure, duplicates, and audio references: OK")
print("Scene-guide isolation: OK")
PY

cd "${ROOT}"
zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh --date "${DATE}" --dry-run
