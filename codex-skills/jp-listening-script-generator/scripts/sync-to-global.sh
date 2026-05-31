#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
TARGET_DIR="${HOME}/.codex/skills/jp-listening-script-generator"

mkdir -p "${TARGET_DIR}/agents" "${TARGET_DIR}/scripts"
cp "${SKILL_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"
cp "${SKILL_DIR}/agents/openai.yaml" "${TARGET_DIR}/agents/openai.yaml"
cp "${SKILL_DIR}/scripts/run-listening-transcribe.sh" "${TARGET_DIR}/scripts/run-listening-transcribe.sh"
cp "${SKILL_DIR}/scripts/sync-to-global.sh" "${TARGET_DIR}/scripts/sync-to-global.sh"
rm -f "${TARGET_DIR}/scripts/run-apple-speech-helper.sh"

echo "Synced jp-listening-script-generator to ${TARGET_DIR}"
