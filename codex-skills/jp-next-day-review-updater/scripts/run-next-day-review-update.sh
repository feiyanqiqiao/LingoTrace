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

cd "${ROOT}"
python3 "${SCRIPT_DIR}/update_next_day_review.py" --vault-root "${ROOT}" "$@"
