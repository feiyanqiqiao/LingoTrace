#!/bin/zsh
set -euo pipefail

find_vault_root() {
  local current="${PWD:A}"
  while [[ "${current}" != "/" ]]; do
    if [[ -f "${current}/tools/listening-transcribe-official/transcribe_listening.py" ]]; then
      echo "${current}"
      return 0
    fi
    current="${current:h}"
  done
  return 1
}

ROOT="$(find_vault_root || true)"
if [[ -z "${ROOT}" ]]; then
  echo "Unable to locate the LingoTrace vault root from ${PWD}" >&2
  exit 1
fi

LINGOTRACE_PYTHON="${LINGOTRACE_LISTENING_PYTHON:-${HOME}/Library/Caches/LingoTrace/venvs/cpython-314/bin/python}"
LISTENKIT_ROOT="${LISTENKIT_ROOT:-${ROOT:h}/ListenKit}"
LISTENKIT_PYTHON="${LISTENKIT_PYTHON:-${FASTER_WHISPER_PYTHON:-${HOME}/Library/Caches/ListenKit/venvs/cpython-314/bin/python}}"

for tool in ffmpeg ffprobe; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "Required media tool is missing: ${tool}" >&2
    exit 1
  fi
done

"${LINGOTRACE_PYTHON}" "${ROOT}/tools/listening-transcribe-official/setup_offline_dictionary.py" \
  --python "${LINGOTRACE_PYTHON}" --check

if "${LINGOTRACE_PYTHON}" -I -c 'import faster_whisper' >/dev/null 2>&1; then
  echo "Isolation failure: LingoTrace can import faster_whisper." >&2
  exit 1
fi

if [[ ! -x "${LISTENKIT_ROOT}/cli/check-runtime.sh" || ! -x "${LISTENKIT_ROOT}/cli/generate-markdown.sh" ]]; then
  echo "ListenKit CLI or runtime checker is missing under ${LISTENKIT_ROOT}." >&2
  exit 1
fi
"${LISTENKIT_ROOT}/cli/check-runtime.sh"

if "${LISTENKIT_PYTHON}" -I -c 'import fugashi' >/dev/null 2>&1; then
  echo "Isolation failure: ListenKit can import fugashi." >&2
  exit 1
fi

"${LINGOTRACE_PYTHON}" -I -c 'import importlib.util, json, pathlib, sys, tempfile
path = pathlib.Path("'"${ROOT}"'") / "tools/listening-transcribe-official/transcribe_listening.py"
spec = importlib.util.spec_from_file_location("transcribe_listening_health", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    root = pathlib.Path(tmp)
    for name, payload in (("v1", {"schema_version": 1}), ("legacy", {})):
        target = root / f"{name}.json"
        target.write_text(json.dumps(payload), encoding="utf-8")
        module.load_listenkit_json(target)
    target = root / "unknown.json"
    target.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    try:
        module.load_listenkit_json(target)
    except RuntimeError:
        pass
    else:
        raise SystemExit("unknown schema_version was accepted")'

echo "LingoTrace / ListenKit listening chain is healthy."
