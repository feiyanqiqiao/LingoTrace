# AGENTS.md

This repository is the public LingoTrace framework inside an Obsidian-based Japanese learning history. Treat notes, frontmatter, wikilinks, Bases, public templates, and language-pack agent skills as part of the user-facing study system.

## Primary Entry Points

Use `lingotrace/packs/japanese/agent_skills/SKILL.md` as the natural-language operating entry for Japanese daily learning tasks.

Users should be able to ask in ordinary study language, such as:

- "请把这段音频做成精听稿。"
- "帮我把这篇材料整理成日语学习笔记。"
- "把这个词加入复习。"
- "这句话很实用，帮我做成口语卡。"
- "今天复习结束了，帮我结算。"

Do not ask users to mention workflow entrypoints, function names, data envelopes, or write-mode terms. The agent skill maps natural-language requests to the matching Japanese pack capability. Actual file changes must still go through the LingoTrace core and Japanese pack, including context checks, capability checks, path boundaries, and the core write guard.

Do not copy full schemas or workflow details into this document. Read the agent skill, the relevant `lingotrace/packs/japanese/` module, and public tests before changing the matching subsystem.

## Path Roles

Do not treat folder paths in prose as the source of truth. Runtime path roles live in each target Vault's `.lingotrace/paths.json`; pack defaults live in `lingotrace/packs/japanese/paths.json`. Update the pack default only when changing the shared Japanese template, and update private Vault config only during an explicit local operation.

## Operating Rules

- Prefer Obsidian-aware and Markdown-aware workflows for note search, note edits, frontmatter, wikilinks, and `.base` files.
- Search before editing vocabulary. Check the focus review layer before the base lexicon so duplicate cards are not created.
- For user-facing tasks that may update existing study state, describe the planned changes in ordinary language and ask for confirmation before saving them, except clear end-of-day review settlement requests. Clear review settlement runs an internal preview, applies if accepted, then verifies with a second preview.
- Keep edits scoped. Do not reorder large sets of notes, bulk-rewrite frontmatter, or normalize unrelated Markdown while working on a narrow task.
- Preserve manually curated content, especially listening-note sentence selections, review notes, and daily study summaries, unless the user explicitly asks to reset them.
- Avoid changing generated tools or helper scripts unless the task is specifically about the automation itself.
- アクセント对比卡 belongs to the pronunciation accent role, not ordinary vocabulary. Do not place it in the normal vocabulary or sentence-practice roles; follow the concrete card rules in `系统配置/模板/录入模板索引.md`.
- Phoneme contrast cards such as 清音/浊音, 送气, and 声带振动 belong in the pronunciation phoneme role, not in the sentence-practice role.

## Git Workflow

- Treat `main` as the protected public branch for the LingoTrace public repository.
- For every public repository update, including documentation-only changes, create a topic branch, commit there, push the branch, and merge through a pull request.
- Do not commit or push directly to `main`.
- Start each topic branch from a clean, current `main`: fetch GitHub, run `git pull --ff-only origin main`, then create the branch.
- Prefer one active pull request per subsystem. If two pull requests must touch the same files, document the dependency order and update the later branch from the merged `main` before marking it ready.
- Keep the topic branch while its pull request is open so review follow-up commits can be added safely.
- Before marking a draft pull request ready or merging it, update the topic branch with the latest `origin/main`, resolve conflicts intentionally, rerun the relevant checks, and update the pull request body with the final verification evidence.
- After a pull request is merged, switch the local checkout back to `main`, run `git pull --ff-only origin main`, then delete the merged local topic branch and its remote branch.
- If a merged branch is attached to a temporary worktree, verify that worktree is clean, remove it, and then delete the branch.
- After cleanup, verify that the local checkout is on `main`, `main` tracks `origin/main`, and no completed topic branches remain locally or remotely.
- Before committing or merging, review the staged file list and confirm it only contains public allowlisted files. Private notes, Obsidian state, audio, images, PDFs, and temporary transcription artifacts must stay untracked or ignored.
- `lingotrace/packs/japanese/views/total-training.base` is the canonical reusable dashboard template. It must keep the today/next-day review filter semantics and must not be replaced by a broad `status == active` view.
- Run `bash tools/git/check-public-staged-files.sh` before committing public changes. When GitHub Actions is available for this repository, use the same allowlist check against pull request diffs.
- Do not bypass failing GitHub checks when they exist unless the failure is understood, documented in the pull request, and unrelated to the proposed change.

## Verification

For documentation-only changes, verify that referenced paths exist and that the new guidance does not contradict the relevant `SKILL.md` files.

For note or workflow changes, prefer a small targeted check over broad vault scans. When a script has a dry-run mode, use that as the first verification step.
