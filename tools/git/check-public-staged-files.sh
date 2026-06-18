#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash tools/git/check-public-staged-files.sh
  bash tools/git/check-public-staged-files.sh --range <git-diff-range>

Without --range, checks staged files. With --range, checks files changed in
the supplied git diff range. The rule is intentionally conservative because
this repository sits inside a private Obsidian vault.
USAGE
}

mode="staged"
range=""

case "${1:-}" in
  "")
    ;;
  --range)
    if [ $# -ne 2 ]; then
      usage >&2
      exit 2
    fi
    mode="range"
    range="$2"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [ "$mode" = "staged" ]; then
  files=$(git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR)
else
  files=$(git -c core.quotePath=false diff --name-only --diff-filter=ACMR "$range")
fi

if [ -z "$files" ]; then
  echo "No public-file candidates to check."
  exit 0
fi

allowed_re='^(\.github/dependabot\.yml|\.github/workflows/[^/]+\.ya?ml|\.gitignore|AGENTS\.md|README\.md|CHANGELOG\.md|CONTRIBUTING\.md|LICENSE|SECURITY\.md|docs/|系统配置/|学习系统/总训练\.base|codex-skills/|tools/README\.md|tools/architecture-baseline/|tools/listening-transcribe-official/|tools/vault-structure/|tools/git/)'
public_scaffold_re='^(系统配置/|学习系统/总训练\.base$)'
private_path_re='(^|/)(\.obsidian|tmp|学习系统|筆記|笔记)(/|$)'
private_ext_re='\.(mp3|m4a|wav|flac|mp4|mov|webm|pdf|jpg|jpeg|png|heic)$'
generated_re='(^|/)__pycache__(/|$)|\.pyc$|\.pyo$'

bad_files=""

while IFS= read -r file; do
  [ -z "$file" ] && continue

  if { [[ "$file" =~ $private_path_re ]] && ! [[ "$file" =~ $public_scaffold_re ]]; } || [[ "$file" =~ $private_ext_re ]] || [[ "$file" =~ $generated_re ]]; then
    bad_files="${bad_files}${file} :: private or generated path is never allowed"$'\n'
    continue
  fi

  if ! [[ "$file" =~ $allowed_re ]]; then
    bad_files="${bad_files}${file} :: not in public allowlist"$'\n'
  fi
done <<< "$files"

if [ -n "$bad_files" ]; then
  printf 'Blocked non-public files:\n%s' "$bad_files" >&2
  exit 1
fi

echo "Public file allowlist check passed."
