# AGENTS.md

This vault is an Obsidian-based Japanese learning system, not a general software repository. Treat notes, frontmatter, wikilinks, Bases, and local Codex skills as part of the user-facing study system.

## Primary Entry Points

Use the local skill documents as the source of truth for task-specific behavior:

- Review material maintenance: `codex-skills/jp-review-material-maintainer/SKILL.md`
- Listening transcription notes: `codex-skills/jp-listening-script-generator/SKILL.md`
- Survival-speaking cards: `codex-skills/jp-survival-speaking-card-generator/SKILL.md`
- General study notes from ListenKit/raw scripts: `codex-skills/jp-source-note-generator/SKILL.md`
- YouTube/audio export: use sibling `../ListenKit/cli/import-audio.sh`
- End-of-day review rollover: `codex-skills/jp-next-day-review-updater/SKILL.md`

Do not copy full schemas or workflow details from these files into this document. Read the relevant skill before changing the matching subsystem.

## Path Roles

Do not treat folder paths in prose as the source of truth. System-managed path roles live in `系统配置/paths.json`; update that file when review roots, the base vocabulary sink, or daily note roots move.

## Operating Rules

- Prefer Obsidian-aware and Markdown-aware workflows for note search, note edits, frontmatter, wikilinks, and `.base` files.
- Search before editing vocabulary. Check the focus review layer before the base lexicon so duplicate cards are not created.
- For scripts that support it, run with `--dry-run` first, inspect the output, then run the write path only when the result is clear.
- Keep edits scoped. Do not reorder large sets of notes, bulk-rewrite frontmatter, or normalize unrelated Markdown while working on a narrow task.
- Preserve manually curated content, especially listening-note sentence selections, review notes, and daily study summaries, unless the user explicitly asks to reset them.
- Avoid changing generated tools or helper scripts unless the task is specifically about the automation itself.
- アクセント對比卡 belongs to the pronunciation accent role, not ordinary vocabulary. Do not place it in the normal vocabulary or sentence-practice roles; follow the concrete card rules in `系统配置/模板/录入模板索引.md`.
- Phoneme contrast cards such as 清音/浊音, 送气, and 声带振动 belong in the pronunciation phoneme role, not in the sentence-practice role.

## Git Workflow

- Treat `main` as the protected public branch for `feiyanqiqiao/JapanLearning`.
- For normal repository updates, create a topic branch, commit there, push the branch, and merge through a pull request or explicit merge step.
- Do not push directly to `main` unless the user explicitly requests it for a small, low-risk documentation or allowlisted tooling change.
- Before committing or merging, review the staged file list and confirm it only contains public allowlisted files. Private notes, Obsidian state, audio, images, PDFs, and temporary transcription artifacts must stay untracked or ignored.

## Verification

For documentation-only changes, verify that referenced paths exist and that the new guidance does not contradict the relevant `SKILL.md` files.

For note or workflow changes, prefer a small targeted check over broad vault scans. When a script has a dry-run mode, use that as the first verification step.
