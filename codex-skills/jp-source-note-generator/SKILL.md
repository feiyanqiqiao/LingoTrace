---
name: jp-source-note-generator
description: Use when turning a transcript, ListenKit artifact, audio, video, or URL into a flexible Japanese-learning source note in this Obsidian vault. Do not use for fixed 精听稿 listening notes or automatic review card maintenance.
---

# JP Source Note Generator

Use this skill when the task is to turn a raw transcript, ListenKit Markdown transcript, video URL, audio URL, or local audio/video file into a Japanese-learning note in this Obsidian vault, and the intended output is a flexible study note rather than the fixed 精听稿 format.

For ordinary listening practice notes under the existing 精听稿 contract, use `jp-listening-script-generator`.

Do not use this skill for automatic vocabulary, grammar, pronunciation, or error-card maintenance; use `jp-review-material-maintainer` when the requested output is review material.

## Maintenance Source Of Truth

The project copy is the source of truth:

- source: `codex-skills/jp-source-note-generator/`
- installed copy: `~/.codex/skills/jp-source-note-generator/`

Edit the project copy first, then sync it to the global skill directory.

Default sync command:

```bash
zsh codex-skills/jp-source-note-generator/scripts/sync-to-global.sh
```

## Core Contract

This skill fixes the workflow and provenance requirements, not the note structure.

- do not create a new universal note directory
- do not update `学习系统/系统配置/paths.json`
- do not impose a fixed Markdown section layout
- before writing the final note, read enough material to propose the likely note direction and confirm the user's choices
- default to one learning note; create multiple notes only when the user chooses that split
- default to a learning note, not review cards
- if the user asks to create review cards, hand off to the matching workflow, especially `jp-review-material-maintainer` for review material and vocabulary deduplication

Every generated note must embed source provenance, regardless of the final structure:

- original material path or URL
- finalized audio path inside the vault
- Obsidian audio embed for the finalized audio, such as `![[audio-name.m4a]]`
- transcript appendix when transcript text exists

The main body structure is flexible, but transcript placement is not: if transcript text exists, place it after the study note body as an appendix, preferably under `## 附录：转写脚本` unless the surrounding note already uses a clearer appendix convention.

## Material Preparation Entry Point

For URL, temporary audio, or local audio/video input, first prepare a stable source-note artifact bundle with the bundled wrapper:

```bash
zsh codex-skills/jp-source-note-generator/scripts/prepare-source-note-material.sh \
  --url "<url>" \
  --artifact-dir "<vault-artifact-dir>" \
  --stem "<short-source-name>"
```

For local audio or video:

```bash
zsh codex-skills/jp-source-note-generator/scripts/prepare-source-note-material.sh \
  --input "<source-media-path>" \
  --artifact-dir "<vault-artifact-dir>" \
  --stem "<short-source-name>"
```

The artifact directory is chosen per source. Prefer a nearby, user-confirmed vault directory for the material rather than a global source-note directory.

The wrapper delegates to ListenKit's public Markdown workflow and prints the paths needed for note writing:

- original source URL or path
- ListenKit Markdown transcript path, normally `<artifact-dir>/<stem>.listenkit.md`
- ListenKit structured JSON path, normally `<artifact-dir>/<stem>.listenkit.json`
- finalized audio path, normally `<artifact-dir>/audio/<stem>.m4a`
- Obsidian audio embed, such as `![[<stem>.m4a]]`
- whether the Markdown contains `## Transcript`

The JSON artifact is for structured follow-up such as timing, segment-level checks, or future speaker-aware metadata. The normal model input for this skill remains the ListenKit Markdown transcript.

When the input is already a ListenKit Markdown transcript, summarize it with:

```bash
zsh codex-skills/jp-source-note-generator/scripts/prepare-source-note-material.sh \
  --listenkit-md "<transcript.md>" \
  --final-audio "<vault-audio-path>"
```

## Input Handling

Accepted inputs include:

- YouTube or other `yt-dlp` supported URL
- temporary local audio file
- already-final local audio file
- ListenKit Markdown transcript
- raw plain-text transcript
- existing Markdown note with an appended full script

When an input contains only text and no audio, ask whether there is a source audio or URL that should be attached. If the user explicitly has no audio, record that fact in the note instead of inventing an audio reference.

## ListenKit Transcript Acquisition

Use the material preparation wrapper for media input. It calls ListenKit to generate a readable transcript Markdown file first. The generated Markdown is the normal source text for this skill.

Internally, media input follows ListenKit's current public entrypoint:

```bash
../ListenKit/cli/generate-markdown.sh --url "<url>" --language Japanese --output "<listenkit-output.md>" --auto-init
```

```bash
../ListenKit/cli/generate-markdown.sh --input "<source-media-path>" --language Japanese --output "<listenkit-output.md>" --auto-init
```

If the user explicitly requests Apple Speech, pass `--engine apple`. Otherwise let ListenKit choose its default engine.

Read the generated Markdown as follows:

- `## Source` provides source and transcript provenance
- `## Transcript` provides the readable transcript text for the final note appendix

The wrapper verifies and reports the finalized audio path. Treat that audio as the vault-owned copy. Do not delete the original temporary file unless the user explicitly asks.

ListenKit also creates a same-stem structured transcript artifact. Use it only when the user asks for timing, segment-level analysis, or future speaker-aware metadata.

## Collaborative Workflow

1. Inspect the material enough to identify the likely study direction: grammar, vocabulary, writing, pronunciation, accent, expression, or mixed.
2. Confirm with the user before creating or rewriting the note:
   - target note path or existing note to update
   - artifact directory for media input, unless a transcript artifact already exists
   - one note or multiple notes
   - any preferred note shape for this material
3. Run the material preparation wrapper, or summarize the existing ListenKit Markdown transcript.
4. Read the generated Markdown and use `## Transcript` as the appendix text.
5. Generate the note using a structure suited to the material and user choices.
6. Include source provenance, ListenKit Markdown path, finalized audio path, the audio embed, and the transcript appendix in the note.
7. If card creation is requested, do it only after the source note exists and use the appropriate existing workflow.

Do not ask for details that can be discovered from the repo or from the material itself. Ask only for choices that materially change where the note/audio go, note granularity, note shape, or whether to create cards.

## Note-Writing Guidance

Let the material determine the shape:

- grammar explanations may center on pattern, meaning, formation, examples, and pitfalls
- vocabulary explanations may center on distinctions, register, collocations, and example sentences
- writing materials may center on rhetorical patterns, paragraph moves, correction rules, and reusable expressions
- pronunciation or accent materials may center on articulation, pitch/accent rules, listening cues, and practice items
- mixed materials may use sections by topic rather than forcing a single category

Keep the final note useful for study, not just a summary. Prefer clear rules, reusable examples, and learner-facing cautions over exhaustive transcript paraphrase.

## Boundaries

- This skill does not replace `jp-listening-script-generator`.
- This skill does not automatically create vocabulary, grammar, speaking, pronunciation, or error cards.
- This skill does not force frontmatter unless the user chooses an existing review-system template.
- This skill does not force a fixed body layout, but transcript text belongs in a note appendix when it exists.
- This skill must always preserve original-source and finalized-audio provenance in the note.
