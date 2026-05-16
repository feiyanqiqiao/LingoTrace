#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
TARGET_DIR="${HOME}/.codex/skills/jp-next-day-review-updater"

mkdir -p "${TARGET_DIR}/agents" "${TARGET_DIR}/scripts"
cp "${SKILL_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"
cp "${SKILL_DIR}/agents/openai.yaml" "${TARGET_DIR}/agents/openai.yaml"
cp "${SKILL_DIR}/scripts/run-next-day-review-update.sh" "${TARGET_DIR}/scripts/run-next-day-review-update.sh"
cp "${SKILL_DIR}/scripts/update_next_day_review.py" "${TARGET_DIR}/scripts/update_next_day_review.py"
cp "${SKILL_DIR}/scripts/sync-to-global.sh" "${TARGET_DIR}/scripts/sync-to-global.sh"

chmod +x \
  "${TARGET_DIR}/scripts/run-next-day-review-update.sh" \
  "${TARGET_DIR}/scripts/update_next_day_review.py" \
  "${TARGET_DIR}/scripts/sync-to-global.sh"

echo "Synced jp-next-day-review-updater to ${TARGET_DIR}"
