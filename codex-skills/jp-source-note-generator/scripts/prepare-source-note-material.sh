#!/bin/zsh
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  prepare-source-note-material.sh (--url <url>|--input <path>|--listenkit-md <path>) [options]

Media input options:
  --url <url>                    URL supported by ListenKit
  --input <path>                 Local audio/video path
  --artifact-dir <dir>           Directory for the source-note artifact bundle
  --stem <name>                  Optional artifact stem. Defaults from input or timestamp

Existing transcript options:
  --listenkit-md <path>          Existing ListenKit Markdown transcript
  --final-audio <path>           Optional finalized audio already in the vault

ListenKit options:
  --language <label>             Defaults to Japanese
  --locale <bcp47>               Optional locale override
  --engine <name>                Optional engine override, for example apple or faster-whisper
  --format <mp3|m4a|wav|flac>    Imported audio format. Defaults to m4a

Other:
  --force                        Replace an existing finalized audio file in the artifact bundle
  --allow-missing-audio          Allow URL subtitle-only output when audio import is unavailable
  --dry-run                      Print the planned ListenKit command without running it
  --help                         Show this help
EOF
}

url=""
input_path=""
existing_listenkit_md=""
artifact_dir=""
stem=""
language="Japanese"
locale=""
engine=""
audio_format="m4a"
final_audio_override=""
force="false"
allow_missing_audio="false"
dry_run="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      [[ $# -ge 2 ]] || { echo "Missing value for --url" >&2; exit 1; }
      url="$2"
      shift 2
      ;;
    --input)
      [[ $# -ge 2 ]] || { echo "Missing value for --input" >&2; exit 1; }
      input_path="$2"
      shift 2
      ;;
    --listenkit-md)
      [[ $# -ge 2 ]] || { echo "Missing value for --listenkit-md" >&2; exit 1; }
      existing_listenkit_md="$2"
      shift 2
      ;;
    --artifact-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --artifact-dir" >&2; exit 1; }
      artifact_dir="$2"
      shift 2
      ;;
    --stem)
      [[ $# -ge 2 ]] || { echo "Missing value for --stem" >&2; exit 1; }
      stem="$2"
      shift 2
      ;;
    --language)
      [[ $# -ge 2 ]] || { echo "Missing value for --language" >&2; exit 1; }
      language="$2"
      shift 2
      ;;
    --locale)
      [[ $# -ge 2 ]] || { echo "Missing value for --locale" >&2; exit 1; }
      locale="$2"
      shift 2
      ;;
    --engine)
      [[ $# -ge 2 ]] || { echo "Missing value for --engine" >&2; exit 1; }
      engine="$2"
      shift 2
      ;;
    --format)
      [[ $# -ge 2 ]] || { echo "Missing value for --format" >&2; exit 1; }
      audio_format="$2"
      shift 2
      ;;
    --final-audio)
      [[ $# -ge 2 ]] || { echo "Missing value for --final-audio" >&2; exit 1; }
      final_audio_override="$2"
      shift 2
      ;;
    --force)
      force="true"
      shift
      ;;
    --allow-missing-audio)
      allow_missing_audio="true"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

source_count=0
for value in "$url" "$input_path" "$existing_listenkit_md"; do
  [[ -n "$value" ]] && source_count=$((source_count + 1))
done
if [[ "$source_count" -ne 1 ]]; then
  echo "Provide exactly one of --url, --input, or --listenkit-md." >&2
  exit 1
fi

case "$audio_format" in
  mp3|m4a|wav|flac) ;;
  *) echo "Unsupported --format: $audio_format" >&2; exit 1 ;;
esac

sanitize_stem() {
  local value="$1"
  local cleaned
  cleaned="$(print -r -- "$value" | sed -E 's#[\\/:*?"<>|]##g; s/[[:space:]]+/_/g; s/_+/_/g; s/^[._]+//; s/[._]+$//')"
  [[ -n "$cleaned" ]] && print -r -- "$cleaned" || print -r -- "source-note"
}

derive_url_stem() {
  local value="$1"
  local raw=""
  if [[ "$value" == *"youtu.be/"* ]]; then
    raw="youtube_${${value#*youtu.be/}%%[/?#]*}"
  elif [[ "$value" == *"youtube"* && "$value" == *"v="* ]]; then
    raw="youtube_${${value#*v=}%%[&#]*}"
  else
    local stripped="${value%%\#*}"
    stripped="${stripped%%\?*}"
    raw="${stripped:t:r}"
  fi
  if [[ -z "$raw" || "$raw" == "." || "$raw" == "/" ]]; then
    raw="source-note-$(date +%Y%m%d-%H%M%S)"
  fi
  sanitize_stem "$raw"
}

has_transcript_section() {
  local markdown_path="$1"
  if [[ -f "$markdown_path" ]] && grep -q '^## Transcript[[:space:]]*$' "$markdown_path"; then
    print -r -- "found"
  else
    print -r -- "missing"
  fi
}

print_summary() {
  local original_source="$1"
  local bundle_dir="$2"
  local markdown_path="$3"
  local json_path="$4"
  local audio_path="$5"
  local transcript_state="$6"

  print -r -- "Source note material prepared:"
  print -r -- "Original source: $original_source"
  [[ -n "$bundle_dir" ]] && print -r -- "Artifact dir: $bundle_dir"
  print -r -- "ListenKit Markdown: $markdown_path"
  if [[ -n "$json_path" && -f "$json_path" ]]; then
    print -r -- "ListenKit JSON: $json_path"
  else
    print -r -- "ListenKit JSON: missing"
  fi
  if [[ -n "$audio_path" && -f "$audio_path" ]]; then
    print -r -- "Final audio: $audio_path"
    print -r -- "Audio embed: ![[${audio_path:t}]]"
  else
    print -r -- "Final audio: missing"
    print -r -- "Audio embed: missing"
  fi
  print -r -- "Transcript section: $transcript_state"
}

if [[ -n "$existing_listenkit_md" ]]; then
  if [[ ! -f "$existing_listenkit_md" ]]; then
    echo "ListenKit Markdown not found: $existing_listenkit_md" >&2
    exit 1
  fi
  listenkit_md="${existing_listenkit_md:A}"
  artifact_dir="${artifact_dir:-${listenkit_md:h}}"
  transcript_json="${listenkit_md:r}.json"
  final_audio="$final_audio_override"
  [[ -n "$final_audio" ]] && final_audio="${final_audio:A}"
  print_summary "$listenkit_md" "$artifact_dir" "$listenkit_md" "$transcript_json" "$final_audio" "$(has_transcript_section "$listenkit_md")"
  exit 0
fi

if [[ -z "$artifact_dir" ]]; then
  echo "--artifact-dir is required for --url and --input." >&2
  exit 1
fi

if [[ -z "$stem" ]]; then
  if [[ -n "$input_path" ]]; then
    stem="$(sanitize_stem "${input_path:t:r}")"
  else
    stem="$(derive_url_stem "$url")"
  fi
else
  stem="$(sanitize_stem "$stem")"
fi

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
VAULT_ROOT="${SKILL_DIR:h:h}"
LISTENKIT_ROOT="${LISTENKIT_ROOT:-${VAULT_ROOT:h}/ListenKit}"
generate_script="${LISTENKIT_ROOT}/cli/generate-markdown.sh"

if [[ ! -x "$generate_script" ]]; then
  echo "ListenKit generate-markdown.sh not found or not executable: $generate_script" >&2
  exit 1
fi

artifact_dir="${artifact_dir:A}"
listenkit_md="${artifact_dir}/${stem}.listenkit.md"
transcript_json="${listenkit_md:r}.json"
generated_audio="${artifact_dir}/audio/${stem}.listenkit.${audio_format}"
final_audio="${artifact_dir}/audio/${stem}.${audio_format}"
original_source="${url:-$input_path}"

command=("$generate_script")
if [[ -n "$url" ]]; then
  command+=(--url "$url")
else
  command+=(--input "$input_path")
fi
command+=(--language "$language" --output "$listenkit_md" --format "$audio_format")
[[ -n "$locale" ]] && command+=(--locale "$locale")
[[ -n "$engine" ]] && command+=(--engine "$engine")
[[ "$engine" != "apple" ]] && command+=(--auto-init)

if [[ "$dry_run" == "true" ]]; then
  print -r -- "Planned ListenKit command:"
  print -r -- "${(q)command[@]}"
  print -r -- "Planned ListenKit Markdown: $listenkit_md"
  print -r -- "Planned ListenKit JSON: $transcript_json"
  print -r -- "Planned final audio: $final_audio"
  exit 0
fi

if [[ -f "$final_audio" && "$force" != "true" ]]; then
  echo "Final audio already exists. Pass --force to replace: $final_audio" >&2
  exit 1
fi

mkdir -p "$artifact_dir"
"${command[@]}"

if [[ ! -f "$listenkit_md" ]]; then
  echo "ListenKit Markdown was not created: $listenkit_md" >&2
  exit 1
fi

if [[ -f "$generated_audio" ]]; then
  if [[ "$generated_audio" != "$final_audio" ]]; then
    mv -f "$generated_audio" "$final_audio"
  fi
elif [[ "$allow_missing_audio" != "true" ]]; then
  echo "Finalized audio was not created by ListenKit: $generated_audio" >&2
  echo "If this is an intentional subtitle-only source, rerun with --allow-missing-audio." >&2
  exit 1
fi

print_summary "$original_source" "$artifact_dir" "$listenkit_md" "$transcript_json" "$final_audio" "$(has_transcript_section "$listenkit_md")"
