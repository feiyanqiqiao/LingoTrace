# JapanLearning

An Obsidian-based Japanese learning system framework.

This repository publishes the reusable automation and Codex skills from a personal Japanese learning vault. It is not a full vault backup and does not include private notes, commercial textbook audio, full textbook transcripts, or local Obsidian workspace state.

## What It Contains

- reusable Codex skills under `codex-skills/`
- vault-specific listening-note renderer under `tools/`

## What It Does Not Contain

- `.obsidian/` workspace files
- daily private notes
- textbook audio or video files
- commercial listening transcripts
- PDFs, screenshots, course schedules, or temporary files
- the generic ASR/audio import implementation

Generic audio import and ASR are handled by the sibling [ListenKit](https://github.com/feiyanqiqiao/ListenKit) project. This repository keeps only the Japanese-learning system and Obsidian note-generation logic.

## Repository Layout

```text
codex-skills/       Local Codex skills for maintaining the learning system
tools/              Vault-specific automation helpers and tests
```

## Using The Framework

1. Install or adapt the skills in `codex-skills/`.
2. Place `ListenKit` next to this repository if you want the listening transcription workflow.
3. Add your own notes and learning content in a private vault. Do not reuse copyrighted textbook audio or transcripts unless you have the right to do so.

## ListenKit Dependency

Listening transcription delegates to `../ListenKit/cli/generate-markdown.sh`. You can override the sibling path with:

```bash
export LISTENKIT_ROOT=/path/to/ListenKit
```

This repository does not vendor `yt-dlp`, `ffmpeg`, Apple Speech helper code, or faster-whisper helpers.

## Privacy And Copyright

Do not commit private daily notes, course materials, audio files, commercial textbook transcripts, local Obsidian workspace state, or temporary transcription artifacts.
