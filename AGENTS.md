# AGENTS.md

This repository is the public LingoTrace runtime outside users' private Obsidian Vaults. Treat notes, frontmatter, wikilinks, Bases, public templates, Vault initialization, runtime connections, and language-pack agent skills as part of the user-facing study system.

## Primary Entry Points

Use `lingotrace/packs/japanese/agent_skills/SKILL.md` as the natural-language operating entry for Japanese daily learning tasks.

Use `lingotrace/packs/english/agent_skills/SKILL.md` as the natural-language operating entry for English daily learning tasks. An initialized Vault's `AGENTS.md`, `.lingotrace/vault-context.json`, and current-platform runtime connection select the matching entry without requiring the user to name it.

Users should be able to ask in ordinary study language, such as:

- "请把这段音频做成精听稿。"
- "帮我把这篇材料整理成日语学习笔记。"
- "把这个词加入复习。"
- "这句话很实用，帮我做成口语卡。"
- "今天复习结束了，帮我结算。"

Do not ask users to mention workflow entrypoints, function names, data envelopes, or write-mode terms. The agent skill maps natural-language requests to the matching Japanese pack capability. Actual file changes must still go through the LingoTrace core and Japanese pack, including context checks, capability checks, path boundaries, and the core write guard.

Do not copy full schemas or workflow details into this document. Read the agent skill, the relevant `lingotrace/packs/japanese/` module, and public tests before changing the matching subsystem.

## Documentation Language and Spec Kit

本项目维护的文档统一使用中文，包括 `README.md`、`docs/`、`AGENTS.md`、`CONTRIBUTING.md`、`CHANGELOG.md`，以及 `.specify/` 下的项目宪章、规格、计划、任务和检查单。代码、命令、文件路径、协议字段、测试名称、外部引用和用户提供的原文可以保留其必要的英文或其他语言内容。

Spec Kit 生成的 `.agents/skills/` 是上游受管的 Agent 工具指令，不属于本项目维护的说明文档；不得手工翻译或改写这些文件，必须通过当前 `specify` CLI 更新。所有 substantive engineering work 必须以 `.specify/memory/constitution.md` 为治理依据，并按当前 CLI 支持的生命周期维护 `specs/` 下的规格、计划、任务和验证工件。已有英文能力契约在未被对应功能改动时不做机械重写；若改动其用户可见内容，必须在同一变更中提供中文维护版本或将内容迁移到中文规范工件，并保留必要的领域术语和原始字段。

## User Journeys

- A learner who only wants to study starts from `docs/learner-agent-setup.md`. Install only the minimal public runtime, keep the private Vault outside it, and use the Vault as the daily Agent workspace.
- A developer starts from `docs/developer-agent-setup.md`, uses a full checkout and a topic branch, and then reuses the learner setup for their real Vault.
- Do not make learners fork the project, install GitHub CLI, read contributor documents, or run the public development test suite.
- Before changing onboarding behavior, read `docs/installation-and-onboarding-design.md` and keep the learner and developer routes distinct.
- Both journeys perform the non-blocking daily update check defined in `docs/daily-runtime-update-design.md`. Official runtimes may update only after explicit consent; personal forks must be left for the user to synchronize in the developer workspace.

## Path Roles

Do not treat folder paths in prose as the source of truth. Runtime path roles live in each target Vault's `.lingotrace/paths.json`; pack defaults live in `lingotrace/packs/japanese/paths.json`. Update the pack default only when changing the shared Japanese template, and update private Vault config only during an explicit local operation.

## Operating Rules

- Prefer Obsidian-aware and Markdown-aware workflows for note search, note edits, frontmatter, wikilinks, and `.base` files.
- Search before editing vocabulary. Check the focus review layer before the base lexicon so duplicate cards are not created.
- For user-facing tasks that may update existing study state, describe the planned changes in ordinary language and ask for confirmation before saving them, except clear end-of-day review settlement requests. Clear review settlement runs an internal preview, applies if accepted, then verifies with a second preview.
- Keep edits scoped. Do not reorder large sets of notes, bulk-rewrite frontmatter, or normalize unrelated Markdown while working on a narrow task.
- Preserve manually curated content, especially listening-note sentence selections, review notes, and daily study summaries, unless the user explicitly asks to reset them.
- Avoid changing generated tools or helper scripts unless the task is specifically about the automation itself.
- アクセント对比卡 belongs to the pronunciation accent role, not ordinary vocabulary. Do not place it in the normal vocabulary or sentence-practice roles; follow the concrete card rules in `docs/multilingual/japanese-review-card-format-and-links.md`.
- Phoneme contrast cards such as 清音/浊音, 送气, and 声带振动 belong in the pronunciation phoneme role, not in the sentence-practice role.
- **Changelog Rule**: When modifying the project framework (e.g., source code, manifests, public templates, or core documentation), always ensure the project's `CHANGELOG.md` is updated.
  - *Exclusion*: Do not write changelogs for daily user-content creation tasks (e.g., generating notes or vocabulary cards in the Vault).
  - *Appropriate Timing*: Write the changelog entry only after all code changes are fully implemented and automated tests pass, but *before* executing the final `git commit`. This ensures the changelog reflects the true final state and is committed atomically with the code.

## Git Workflow

- Treat `main` as the protected public branch for the LingoTrace public repository.
- For every public repository update, including documentation-only changes, create a topic branch, commit there, push the branch, and merge through a pull request.
- Do not commit or push directly to `main`.
- Before the first public change, inspect remotes. In a contributor checkout, `origin` should be the contributor's fork and `upstream` should be `https://github.com/feiyanqiqiao/LingoTrace.git`; do not assume that `origin` is canonical.
- Start each topic branch from a clean, current `main`: fetch all remotes, compare local/fork/upstream `main`, tell the user when upstream has moved, then fast-forward local `main` from the canonical remote. In a fork workflow, push the synchronized `main` to `origin` before branching.
- Use a complete checkout for framework development. The sparse `lingotrace/` checkout documented for ordinary learners is a runtime distribution, not a development workspace.
- Prefer one active pull request per subsystem. If two pull requests must touch the same files, document the dependency order and update the later branch from the merged `main` before marking it ready.
- Keep the topic branch while its pull request is open so review follow-up commits can be added safely.
- Before marking a draft pull request ready or merging it, update the topic branch with the latest canonical `main` (`upstream/main` in a fork workflow), resolve conflicts intentionally, rerun the relevant checks, and update the pull request body with the final verification evidence.
- After a pull request is merged, switch the local checkout back to `main`, fast-forward from the canonical remote, synchronize the fork if one exists, then delete the merged local topic branch and its fork remote branch.
- If a merged branch is attached to a temporary worktree, verify that worktree is clean, remove it, and then delete the branch.
- After cleanup, verify that the local checkout is on `main`, `main` tracks `origin/main`, and no completed topic branches remain locally or remotely.
- Before committing or merging, review the staged file list and confirm it only contains public allowlisted files. Private notes, Obsidian state, audio, images, PDFs, and temporary transcription artifacts must stay untracked or ignored.
- `lingotrace/packs/japanese/views/total-training.base` is the canonical reusable dashboard template. It must keep the today/next-day review filter semantics and must not be replaced by a broad `status == active` view.
- Run `bash tools/git/check-public-staged-files.sh` before committing public changes. When GitHub Actions is available for this repository, use the same allowlist check against pull request diffs.
- Do not bypass failing GitHub checks when they exist unless the failure is understood, documented in the pull request, and unrelated to the proposed change.

## Verification

For documentation-only changes, verify that referenced paths exist and that the new guidance does not contradict the relevant `SKILL.md` files.

For note or workflow changes, prefer a small targeted check over broad vault scans. When a script has a dry-run mode, use that as the first verification step.
