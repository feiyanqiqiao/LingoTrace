---
name: jp-next-day-review-updater
description: Use when closing out the day's Japanese review workflow, advancing done_today items, updating next_review dates, or running the scheduled review rollover. Do not use for creating new cards, manual vocabulary organization, transcription, or source-note creation.
---

# JP Next-Day Review Updater

Use this skill when the task is to run the end-of-day review rollover for this Japanese learning vault, either manually or from the scheduled automation.

Do not use this skill to create new review cards, manually organize vocabulary, generate listening notes, or create flexible source notes. Use `jp-review-material-maintainer`, `jp-listening-script-generator`, or `jp-source-note-generator` for those tasks.

## Maintenance Source Of Truth

The project copy is the source of truth:

- source: `codex-skills/jp-next-day-review-updater/`
- installed copy: `~/.codex/skills/jp-next-day-review-updater/`

Edit the project copy first, then sync it to the global skill directory.

Default sync command:

```bash
zsh codex-skills/jp-next-day-review-updater/scripts/sync-to-global.sh
```

## Default Workflow

1. run the local wrapper in `--dry-run` mode first
2. confirm the counts for processed items, stage transitions, and next-day queue look reasonable
3. rerun without `--dry-run` to perform the actual rollover
4. if the script reports an unknown `review_stage` or a missing required frontmatter field, stop and fix the data instead of patching around it manually

This skill is intentionally deterministic. Do not replace its state updates with model-written edits.

## Review Scope

The script only manages roots listed in `系统配置/paths.json` under `managed_review_roots`.

It can write to the configured `base_vocab_root` only when a focus vocab card finishes the full review cycle and needs to be sunk into the base lexicon.

## Stage Chain

The fixed review stages are:

- `day0 -> day1` (`+1 day`)
- `day1 -> day3` (`+3 days`)
- `day3 -> day7` (`+7 days`)
- `day7 -> day14` (`+14 days`)
- `day14 -> day30` (`+30 days`)
- `day30 -> day90` (`+90 days`)
- `day90 -> day180` (`+180 days`)
- `day180 -> mastered`

Vocabulary focus cards are special-cased at the end of the chain:

- `day180 + done_today + item_type: vocab -> sink to 基础词汇`
- the focus card becomes `status: mastered`
- the base lexicon note is created or updated as `status: promoted`

Delayed review rule:

- compute `overdue_days = run date - original next_review`
- compute `allowed_delay = max(1, current stage days)`
- if `overdue_days <= allowed_delay`, advance to the next stage
- if `overdue_days > allowed_delay`, keep the current stage and set `next_review = run date + allowed_delay`

Only items with `status: active` and `done_today: true` are advanced. `status: mastered` cards are ignored until a later vocab-maintenance pass reactivates them.

## CLI Entry Point

Always use the local wrapper:

```bash
zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh --dry-run
```

Useful variants:

```bash
zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh

zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh \
  --date 2026-04-22 \
  --dry-run

zsh codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh \
  --date 2026-04-22 \
  --note-path "笔记/2026.4/2026.4.22.md"
```

## Output Contract

The script should:

- update `last_reviewed`, `review_stage`, `next_review`, and `done_today` only for completed items
- sink focus vocab cards that finish `day180` into the configured base vocabulary root
- mark sunk focus vocab cards as `status: mastered` and clear their active scheduling
- leave same-day extracted but unreviewed items in the current round
- rewrite only the `## 每日学习清单` tail section of the target daily note when that note exists
- add the `## 每日学习清单` section when the daily note exists but does not yet contain that anchor
- keep the fixed structure: `今日完成 / 今日卡点 / 简短复盘`
- preserve the existing `今日卡点` bullets when they already exist
- skip checklist rewrite when the daily note is missing, but still complete the review-state rollover
- fail explicitly when required fields are missing

## Automation Integration

The scheduled automation should reference this skill rather than restating the entire business logic in natural language.
