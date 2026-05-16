#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
TARGET_DIR="${HOME}/.codex/skills/jp-review-material-maintainer"

mkdir -p "${TARGET_DIR}/agents"
mkdir -p "${TARGET_DIR}/scripts"
cp "${SKILL_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"
cp "${SKILL_DIR}/agents/openai.yaml" "${TARGET_DIR}/agents/openai.yaml"
cp "${SKILL_DIR}/scripts/"*.py "${TARGET_DIR}/scripts/" 2>/dev/null || true

echo "Synced jp-review-material-maintainer to ${TARGET_DIR}"
