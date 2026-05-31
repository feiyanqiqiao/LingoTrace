#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
TARGET_DIR="${HOME}/.codex/skills/jp-survival-speaking-card-generator"

mkdir -p "${TARGET_DIR}/agents" "${TARGET_DIR}/scripts"
cp "${SKILL_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"
cp "${SKILL_DIR}/agents/openai.yaml" "${TARGET_DIR}/agents/openai.yaml"
cp "${SKILL_DIR}/scripts/validate-survival-speaking-cards.sh" "${TARGET_DIR}/scripts/validate-survival-speaking-cards.sh"
cp "${SKILL_DIR}/scripts/sync-to-global.sh" "${TARGET_DIR}/scripts/sync-to-global.sh"

chmod +x \
  "${TARGET_DIR}/scripts/validate-survival-speaking-cards.sh" \
  "${TARGET_DIR}/scripts/sync-to-global.sh"

echo "Synced jp-survival-speaking-card-generator to ${TARGET_DIR}"
