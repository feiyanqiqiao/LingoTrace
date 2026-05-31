---
name: jp-survival-speaking-card-generator
description: Use when creating, updating, merging, or promoting survival-speaking cards in this Japanese-learning vault, including manually reviewed Shadowing common sentences and user-provided daily-life phrases.
---

# JP Survival Speaking Card Generator

Use this skill for short, reviewable `track: survival_speaking` cards. Keep the library conservative: a card should represent one sentence or fixed exchange that the learner can directly say or must quickly understand in a clear real-life scene.

Do not use this skill for listening transcription, audio slicing, broad extraction from unreviewed notes, long scene-guide authoring, or review rollover. Use `jp-listening-script-generator`, `jp-source-note-generator`, or `jp-next-day-review-updater` for those tasks.

## Maintenance Source Of Truth

The project copy is the source of truth:

- source: `codex-skills/jp-survival-speaking-card-generator/`
- installed copy: `~/.codex/skills/jp-survival-speaking-card-generator/`

Edit the project copy first, then sync it to the global skill directory:

```bash
zsh codex-skills/jp-survival-speaking-card-generator/scripts/sync-to-global.sh
```

## Accepted Inputs

Use this skill when the user explicitly asks to create or maintain speaking cards from:

- a manually reviewed Shadowing `## 可直接背的常用句` section
- one or more daily-life phrases provided directly by the user
- existing cards that need merging, correction, or template maintenance

Do not automatically promote freshly generated Shadowing selections merely because they exist. Do not scan unrelated learning notes to find candidates unless the user explicitly names those notes and asks for speaking-card conversion.

## Card Workflow

1. Read `系统配置/模板/录入模板索引.md` and use its current `## 生活口语句子卡模板` as the format source of truth.
2. Recursively search `学习系统/生活口语/句库` before writing. Check exact `jp_text`, the same core exchange, and nearby cards that should be merged instead of duplicated.
3. Promote only high-fit material:
   - keep natural phrases with a clear real-life scene, speaker role, practical meaning, and likely reply
   - keep phrases the learner should directly say or quickly understand
   - reject textbook drills, overly generic frames, unresolved ASR, unnatural phrasing, and one-off text-specific sentences
4. Create one focused card per core sentence or fixed exchange. Preserve existing review state when updating a card; initialize genuinely new cards at the current date with `review_stage: day0` and `next_review: <today>`.
5. Store cards under one scene-category subdirectory in `学习系统/生活口语/句库/<scene category>/`. Prefer the existing categories `家庭`, `学校与学习`, `餐饮`, `购物`, `办事与就医`, `职场`, `出行`, `联络与邀约`, and `日常闲聊`; add a category only for a genuinely new practice scene.
6. Use English snake_case for `scene` and `function`. Use only `self`, `staff`, or `other` for `speaker_role`.
7. Keep `source_notes` backlinks when a source exists. For user-provided phrases without a source note, use an empty list rather than inventing provenance.
8. When a reliable sentence or dialogue slice exactly matches the card, add the optional `## 跟读音频` section with a direct Obsidian embed to the original slice. Do not copy Shadowing audio into the speaking-card directory. Label a textbook variant briefly when the card itself has been naturalized.

## Scene Guides

Keep long materials, source videos, and transcript appendices under `学习系统/生活口语/场景指南` without `track: survival_speaking`.

This skill may link a speaking card to an existing scene guide. It does not generate or expand long scene guides.

## Validation

After creating or updating cards, run:

```bash
zsh codex-skills/jp-survival-speaking-card-generator/scripts/validate-survival-speaking-cards.sh
```

The validator is read-only. It checks card placement, required fields, duplicate `jp_text`, body sections, audio references, scene-guide isolation, and the rollover dry-run.
