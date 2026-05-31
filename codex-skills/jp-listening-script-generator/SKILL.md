---
name: jp-listening-script-generator
description: Use when turning one local audio file or media URL into this vault's fixed Japanese listening-practice note format, including 泛听 and 精听 variants. Do not use for flexible source notes, general study notes from transcripts, or review card creation and maintenance.
---

# JP Listening Script Generator

Use this skill when the task is to turn one local listening audio file or media URL into the existing listening-practice Markdown note format. Generic ASR and media acquisition are delegated to the sibling `../ListenKit` CLI; this skill keeps only the Obsidian Japanese-learning workflow and note rendering rules.

Do not use this skill for flexible source notes or general study notes from transcripts, audio, or video; use `jp-source-note-generator` for those. Do not use it for review card creation or maintenance; use `jp-review-material-maintainer`.

## Maintenance Source Of Truth

The project copy is the source of truth:

- source: `codex-skills/jp-listening-script-generator/`
- installed copy: `~/.codex/skills/jp-listening-script-generator/`

Edit the project copy first, then sync it to the global skill directory.

Default sync command:

```bash
zsh codex-skills/jp-listening-script-generator/scripts/sync-to-global.sh
```

## Default Workflow

Prefer single-item processing first. The main path is:

1. identify one local audio file under a listening material directory's `attach/`, or one URL plus a target material directory under `学习系统/听力`
2. locate the matching note, or create a new note when none exists yet
3. run the transcription pipeline
4. render the Markdown draft note
   - the CLI requires a prepared offline dictionary cache for inline accent candidates; if it is missing, run the setup script described below
   - default mode is `extensive` 泛听: the note has an accent-marked `## 脚本` but no `## 精听学习包` and no sentence slices
   - use `--listening-mode intensive` for 精听: the note includes `## 精听学习包` before the plain `## 脚本`
   - each intensive learning block uses only `### SNN`, the accent-marked sentence, and the sentence audio embed
5. unless the user explicitly asked for `--dry-run`, immediately enter a second editing phase:
   - read the generated `## 脚本`
   - use model judgment to choose `0-5` truly reusable sentences
   - write the final `## 可直接背的常用句`
   - sync frontmatter `daily_use_sentences`
6. only then treat the note as complete

Context-budget rule for this skill:

- do not proactively open multiple existing sample notes just to match style
- first trust the generator's existing Markdown contract and naming heuristics
- only inspect an existing note when the generated result is clearly unstable or ambiguous
- when inspection is needed, prefer one nearest sample note and stop there unless the first sample still leaves the issue unresolved

When rerunning transcription for an existing note, preserve the already curated `## 可直接背的常用句`, `daily_use_sentences`, and any extra manual sections unless the user explicitly asks to reset them. Existing notes with `listening_mode` keep that mode; legacy notes that already contain `## 精听学习包` are treated as `intensive`; otherwise unmarked materials default to `extensive`.

For short-choice listening materials such as `実力アップ/29番-32番.mp3`, the generator now switches into a short-choice mode automatically:

- it prefers keeping question numbers and `1/2/3` option structure
- it automatically retries with a slow-copy pass when that yields a better structure
- when an existing note already has a clearly better short-choice `## 脚本`, it preserves that script instead of overwriting it with a weaker retranscription

When there is any uncertainty about title quality or recognition stability, use `--dry-run` first.

## ListenKit Route

The generator delegates transcript acquisition to ListenKit's Markdown workflow and then applies vault-specific listening-note rendering. Set `LISTENKIT_ROOT` only when the sibling repo is not at `../ListenKit`.

- `--engine auto` is the default and lets ListenKit choose its default engine
- `--engine apple` explicitly requests ListenKit's Apple Speech route
- `--engine faster-whisper` explicitly requests ListenKit's faster-whisper route
- URL input treats `--output-dir` as the material directory: finalized audio goes into its `attach/`, raw ListenKit `.listenkit.md/.json` artifacts go into `artifacts/`, and the learning note stays at the material-directory root
- local audio under `attach/` also generates or updates the learning note at the parent material-directory root; legacy root-level local audio input remains readable during migration

The vault wrapper passes ListenKit's `--auto-init` flag for the default/faster-whisper route. On first use, ListenKit may create `../ListenKit/.venv` and install faster-whisper; do not create `.venv` manually from the vault parent directory.

```bash
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/Shadowing_初中級/Unit1/attach/04.mp3" --engine faster-whisper --locale ja-JP --dry-run
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/中級を学ぼう/attach/manabo_cz22.mp3" --listening-mode intensive --dry-run
```

Set `FASTER_WHISPER_PYTHON=/path/to/python` only when intentionally overriding ListenKit's repo-local environment.

The current local test setup uses:

- model: `small`
- device: `cpu`
- compute type: `int8`
- observed cached run for `Unit1/04.mp3`: about 18 seconds, with peak memory around 1.1 GB footprint

## CLI Entry Point

The skill does not implement generic ASR itself. Always call the local Markdown generator through the wrapper; that generator consumes ListenKit's generated transcript artifacts:

```bash
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/中級を学ぼう/attach/manabo_cz16.mp3"
```

## Offline Dictionary Setup

The listening note renderer uses a local dictionary cache for word selection, reading, and accent candidates. The default cache is outside the vault:

- default: `~/Library/Caches/jp-listening-dicts`
- override: `JP_LISTENING_DICT_DIR=/path/to/cache`

Check the cache before first use:

```bash
python3 tools/listening-transcribe-official/setup_offline_dictionary.py --check
```

The check output should include both sample tokens and sample accent candidates such as `公園⓪`; tokenization alone is not enough to prove accent lookup is wired into the generator.

Install the offline dictionary packages when the check says the cache is not ready:

```bash
python3 tools/listening-transcribe-official/setup_offline_dictionary.py --install
```

The installer writes Python packages such as `fugashi` and `unidic-lite` under the cache directory, not inside the Obsidian vault or the skill folder. The generator must fail clearly when the cache is missing; do not silently generate guessed accent data.

For URL input, choose the target listening directory explicitly:

```bash
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh \
  --url "https://example.com/video" \
  --output-dir "学习系统/听力/来源名"
```

Useful variants:

```bash
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/中級を学ぼう/attach/manabo_cz16.mp3"
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/N2/202212/attach/example.mp3" --locale ja-JP
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh "学习系统/听力/Shadowing_初中級/Unit1/attach/04.mp3" --engine auto --locale ja-JP
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh --url "https://example.com/video" --output-dir "学习系统/听力/自学素材" --title "素材标题"
```

The generic transcript workflow lives in ListenKit. Vault code only converts the generated transcript artifacts into the local listening-note format.

## Sandbox And Approval

The explicit Apple Speech route may launch a macOS permission flow through ListenKit. In Codex, that should be treated as a GUI launch, not as a normal sandbox-safe shell command.

- when explicitly using Apple Speech, do not probe this route in the sandbox first
- request escalated execution on the first Apple Speech invocation of `zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh ...`
- when the approval UI appears, prefer saving a persistent prefix approval for `["zsh", "codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh"]`

That combination avoids the usual retry pattern of “sandbox run fails first, then ask for approval”.

The default/faster-whisper route is a normal ListenKit CLI subprocess. It does not launch a GUI permission flow, but first use can install Python packages into `../ListenKit/.venv` and later download model files through faster-whisper/Hugging Face caches.

## Output Contract

The generated note has two modes. Default is `extensive`; use `--listening-mode intensive` only when the user explicitly wants逐句精听.

- preserve the existing frontmatter as much as possible
- set `transcript_status: full`
- set `transcript_ref: in-note`
- set `listening_mode: extensive` or `listening_mode: intensive`
- keep the source-audio embed as `![[attach/audio_name.ext]]`
- render `## 脚本`
- render `## 可直接背的常用句`
- render `## 素材说明`
- prefer a topic-bearing filename such as `manabo_cz18_土用の丑の日とうなぎ.md`, not a generic `识别稿`
- do not rely on rule-based extraction for `可直接背的常用句`; use model judgment after the script is generated
- in `extensive`, do not render `## 精听学习包`, do not generate sentence slices, and inline known accent marks directly in `## 脚本`
- in `intensive`, render `## 精听学习包`; each block is `### SNN`, blank line, the accent-marked sentence, blank line, then the sentence audio embed
- in `intensive`, keep `## 脚本` as the plain script without forced accent marks
- in `intensive`, embed the sentence audio clip as `![[attach/audio_stem_SNN.m4a]]`; when there is no reliable timestamp, write only `（语音切片待生成）`
- do not show `已确认`, `本地候选`, or `待确认` source labels inside the note body; use those labels only for internal selection and separate accent-review work
- for accent data, prefer the vault's existing confirmed `accent_display`; otherwise use offline dictionary candidates and label them `本地候选`; unknown items must be `待确认`
- export sentence clips only when reliable start/end timestamps are available; do not fabricate clips from uncertain alignment
- do not write `本地候选` accent values back into vocabulary cards as confirmed data
- for `可直接背的常用句`, prefer quality over quantity: 0-5 items is acceptable, and long sentences are allowed when the pattern is worth memorizing
- render each selected common sentence in this structured format, without a Chinese translation field:

```md
- 原句：
  可替换骨架：
  使用场景：
  选入理由：
```

- fixed question/answer exchanges may be merged into one `原句`, such as `日本は初めてですか？いいえ、3回目です。`
- overly generic patterns such as `〜は〜です` should usually be rejected
- if nothing is genuinely worth memorizing, leaving the section empty is better than forcing filler content

For dialogue-type listening content, apply a dialogue template layer on top of the normal note contract:

- dialogue-type content is defined by the transcript structure, not by path name, `セクションN`, question numbers, or total length
- when the transcript clearly shows short question/answer or response turn-taking, render `## 脚本` with speaker labels such as `A：` and `B：`
- use a conservative rule: only add `A：/B：` when the alternation is clearly visible from the text
- if the transcript is ambiguous, monologic, list-like, or otherwise unstable, fall back to normal non-speaker formatting
- do not invent `C：` or multi-speaker labels unless the ListenKit transcript artifact provides reliable speaker metadata
- in dialogue-type notes, prefer `可直接背的常用句` selections that are reusable question templates, response templates, and social or situational exchanges

## Second-Phase Editing Rules

After the draft note exists, the skill should treat common-sentence curation as a required second phase, not as an optional extra.

- first prefer sentences that have reusable contrast, cause-effect, requirement, trend, evaluation, or question patterns
- for dialogue-type notes, prefer reusable question templates, response templates, greetings, requests, confirmations, refusals, social formulas, and scene-specific inquiries before long expository sentences
- avoid sentences that are only useful because of one specific noun unless the structure itself is broadly reusable
- reject sentences when ASR is unstable or the phrasing is not natural enough to memorize directly
- long sentences are acceptable when their pattern is worth memorizing
- if a sentence is selected, keep frontmatter `daily_use_sentences` aligned with the final section, but include only Japanese original/core sentences there
- if no sentence is selected, keep `daily_use_sentences: []`

## Shadowing To Survival Speaking

For `Shadowing_*` notes, `## 可直接背的常用句` is only a candidate pool for survival-speaking cards. Do not automatically convert freshly generated or unreviewed common-sentence selections into `学习系统/生活口语/句库`.

Only promote Shadowing common sentences when the user explicitly asks for speaking-card conversion. Hand that task off to `jp-survival-speaking-card-generator`, which owns conservative selection, deduplication, scene placement, backlinks, and optional source-slice embeds.

## Batch Mode

Batch mode is intentionally disabled in the current single-item workflow.
