---
name: jp-review-material-maintainer
description: Use when creating or updating Japanese review materials in this Obsidian vault, such as vocabulary, grammar, pronunciation, error cards, or daily study checklist entries. Do not use for survival-speaking cards, listening transcription, flexible source notes, or end-of-day review rollover.
---

# JP Review Material Maintainer

Use this skill when the task is to extract, create, update, merge, or promote review material in this vault, including vocabulary notes, grammar cards, pronunciation cards, error cards, and daily study checklist entries.

Do not use this skill for survival-speaking cards, listening transcription, flexible study source notes from media or transcripts, or end-of-day review rollover. Use `jp-survival-speaking-card-generator`, `jp-listening-script-generator`, `jp-source-note-generator`, or `jp-next-day-review-updater` for those tasks.

## Maintenance Source Of Truth

The project copy is the source of truth:

- source: `codex-skills/jp-review-material-maintainer/`
- installed copy: `~/.codex/skills/jp-review-material-maintainer/`

Edit the project copy first, then sync it to the global skill directory.

Default sync command:

```bash
zsh codex-skills/jp-review-material-maintainer/scripts/sync-to-global.sh
```

## Tool Preferences

Prefer Obsidian-native workflows over generic file handling when possible.

- Use the `obsidian-cli` skill first for vault-local search, note targeting, and property-aware read/update operations.
- Use the `obsidian-markdown` skill for note structure, frontmatter, wikilinks, and valid Obsidian Markdown.
- Use the `obsidian-bases` skill only when the task touches `.base` files or vocabulary views.
- Fall back to generic shell/file editing only when the Obsidian-specific path is unavailable or clearly less suitable.

When using `obsidian-cli`, prefer targeted actions:

- search before opening many files
- target notes by exact vault path when known
- change properties directly when the operation is a property update
- avoid broad vault scans when a folder-scoped search is enough

## Session Output Convention

When the task touches daily study notes or asks to update the day's study checklist in `笔记/YYYY.M/YYYY.M.D.md`, use this structure by default and do not invent a broader daily dashboard unless the user explicitly asks for it.

Default section name:

- `## 每日学习清单`

Default subsections:

- `## 今日完成`
- `## 今日卡点`
- `## 简短复盘`

Rules:

- omit `今日重点`, `今日待做`, and `明日优先` unless the user explicitly asks for them
- under `今日完成`, write plain item names or concrete completed items, not relative note paths or verbose wikilink-heavy output, unless the user explicitly asks for links
- if `今日完成` uses grouped labels such as `今日已复习 错题 / 发音`, render the contained items one per line as sub-bullets instead of compressing them into a comma-separated run-on line
- under `今日卡点`, keep only real learning blockers or recurring mistakes
- under `简短复盘`, keep it short and execution-oriented
- when this checklist is added to a dated note, append it after the raw classroom content instead of mixing it into the source note body
- treat this checklist as a lightweight execution log, not a second review-card system

## Standard Obsidian CLI Patterns

Use these patterns as the default starting point. Resolve role roots from `系统配置/paths.json` before substituting `path=...`; do not treat the example paths below as hard-coded system truth.

### 1. Search focus review cards first

```bash
obsidian search query="抱く" path="<focus_vocab_root>" limit=10
```

Use this before opening files. If a clear match exists here, treat the word as a focus-card update task.

### 2. Search the base lexicon second

```bash
obsidian search query="抱く" path="<base_vocab_root>" limit=10
```

Use this only if the focus-card search did not find a match.

### 3. Read the source classroom note by exact path

```bash
obsidian read path="笔记/2026.4/2026.4.14.md"
```

Prefer exact `path=` for dated notes and structured folders.

### 4. Read a matched vocab note by exact path

```bash
obsidian read path="<base_vocab_root>/抱く.md"
obsidian read path="<focus_vocab_root>/抱く.md"
```

Open only the matched note plus the source note. Do not open large batches unless the task explicitly requires a broader audit.

### 5. Update a property directly

```bash
obsidian property:set path="<focus_vocab_root>/抱く.md" name="last_seen" value="2026-04-14"
obsidian property:set path="<focus_vocab_root>/抱く.md" name="status" value="active"
```

Prefer direct property updates for single-field changes instead of rewriting the whole file.

### 6. Create a new note in the correct layer

```bash
obsidian create path="<focus_vocab_root>/新出単語.md" content="---\ntrack: class_review\nitem_type: vocab\nstatus: active\npriority: normal\ndone_today: false\nheadword: 新出単語\nreading:\naccent_display:\nmeaning_zh:\nsource_notes:\n  - \"[[笔记/2026.4/2026.4.14]]\"\nfirst_seen: 2026-04-14\nlast_seen: 2026-04-14\nseen_count: 1\nerror_count: 0\nreview_stage: day0\nnext_review: 2026-04-14\nlast_reviewed: \"\"\nconfusable_with: []\ntags:\n  - jp/vocab\n  - jp/class_review\n---\n\n# 新出単語\n\n## 核心\n\n## 来源\n"
```

Use this for classroom-note vocabulary creation. Only create a base-lexicon note when a word has completed the focus-review cycle and is being sunk into long-term storage.

### 7. Use file-name targeting only when the name is unique

```bash
obsidian read file="抱く"
obsidian property:set file="抱く" name="priority" value="high"
```

Prefer `path=` when the note name could exist in both layers.

## Scope

This vault uses a dual-layer vocabulary system. Resolve concrete roots from `系统配置/paths.json` and role-specific local guidance:

- Focus review cards: `<focus_vocab_root>`
- Base lexicon: `<base_vocab_root>`

Only vocabulary uses the dual-layer model. Grammar and error cards stay in `学习系统/语法` and `学习系统/错题`.

When the source note contains explicit sections such as `## 単語`, `## 文法`, and `## 間違えた問題`, split them by role instead of forcing everything into vocabulary:

- `単語` → vocab extraction rules in this skill
  - `### 通常語彙` → normal vocab extraction
  - `### 漢字差分` → normal vocab extraction plus kanji-difference metadata
- `文法` → grammar cards under `学习系统/语法`
- `間違えた問題` → update related grammar cards when relevant, then create or update error cards under `学习系统/错题`

For entries under `### 漢字差分`, keep the normal vocabulary-card flow and add:

- `kanji_diff: true`
- `kanji_diff_pairs`: concrete Japanese/simplified character pairs such as `複/复`
- `jp/kanji_diff` in `tags`

Do not record a whole-word simplified form. In particular, do not create mixed forms such as `决める` or `饮む`; record only concrete interfering character pairs.

For entries without a kanji-difference need, keep:

- `kanji_diff: false`
- `kanji_diff_pairs: []`

## Image-Backed Vocabulary Sources

When a source note embeds an image inside `## 単語` or one of its subsections, treat the image as a vocabulary source:

1. open the local attachment and inspect the printed vocabulary
2. collect only clearly readable vocabulary items and normalize obvious dictionary forms before searching
3. exclude items already written as text in the same source note
4. run the normal focus-first duplicate search for each remaining item
5. keep the original image embed unchanged

Do not guess from blurred text, handwritten annotations, or uncertain OCR. Report unclear items for user confirmation instead of creating cards.

## Canonical Search Order

For every candidate word, search in this order:

1. `<focus_vocab_root>`
2. `<base_vocab_root>`
3. create a new note only if neither layer has a match

Do not create duplicates because the source note is different.

Operationally:

1. use `obsidian-cli` or an equivalent fast search to check `<focus_vocab_root>`
2. if no match, check `<base_vocab_root>`
3. open only the matched files plus the source note
4. create a new note only if neither layer has a match

## Naming Rules

- Default: one headword per note, named by the standard headword
- Allow a grouped note only when the items are clearly one learning point:
  - confusable pair
  - paired titles or roles
  - variant readings already taught together
- If unsure, prefer a single headword note

## Layer Decision

For vocabulary extracted from classroom notes or daily study notes, default to the focus review layer first:

- create or update `<focus_vocab_root>` as the primary learning card
- initialize new focus cards at `status: active`, `review_stage: day0`, `next_review: today`
- keep the word in focus review until it finishes the full `day0 / day1 / day3 / day7 / day14 / day30 / day90 / day180` cycle

Only use the base lexicon as the long-term sink layer:

- when a focus card finishes `day180` and is marked done for the day, create or update the base lexicon note
- mark that base note `status: promoted` and include `jp/promoted`
- switch the focus card to `status: mastered` so it exits the active review queue

If a word already exists in the base lexicon but appears again in a classroom note:

- create or restore the focus review card instead of stopping at the base note
- keep the base note and mark it as promoted
- reset the focus review schedule to `day0`

## Required Schemas

### Base Lexicon

Path: `<base_vocab_root>/<headword>.md`

Required properties:

- `headword`
- `reading`
- `accent_display` (leave blank when the accent is unknown)
- `meaning_zh`
- `source_notes`
- `first_seen`
- `last_seen`
- `seen_count`
- `status`
- `promote_candidate`
- `kanji_diff`
- `kanji_diff_pairs`
- `tags`

Expected tags:

- `jp/vocab`
- `jp/base_vocab`
- `jp/class_review`
- add `jp/promoted` when the word has a focus card
- add `jp/kanji_diff` when `kanji_diff: true`

### Focus Review Card

Path: `<focus_vocab_root>/<headword>.md`

Required properties:

- `track: class_review`
- `item_type: vocab`
- `status`
- `priority`
- `done_today`
- `headword`
- `reading`
- `accent_display` (leave blank when the accent is unknown)
- `meaning_zh`
- `source_notes`
- `first_seen`
- `last_seen`
- `seen_count`
- `error_count`
- `review_stage`
- `next_review`
- `last_reviewed`
- `confusable_with`
- `kanji_diff`
- `kanji_diff_pairs`
- `tags`

Allowed `status` values for vocab cards:

- `active`: participates in total review and next-day rollover
- `mastered`: completed one full review cycle and should stay out of active review until the word reappears

Linking rule for vocab cards:

- when a vocab card has a real comparison target, populate `confusable_with`
- also add Obsidian wikilinks in `## 核心` or `## 易错 / 易混` so the comparison is visible while reviewing
- only link high-value comparisons: confusable pairs, near-synonyms, opposite-choice traps, repeated classroom contrasts
- do not add links just to increase graph density
- add `jp/kanji_diff` when `kanji_diff: true`

Accent display rule for vocabulary cards:

- keep `headword` as the clean written headword and `reading` as the clean kana reading; do not append accent marks to either field
- always create the `accent_display` property on vocabulary cards; leave it blank when the accent is unknown so it can be filled later
- when a reliable accent is known, store it in `accent_display` as kana plus accent, such as `しあい⓪`, `じてんしゃ②／⓪`, or `はる⓪・はる①`
- mirror the same value visibly in the body under `## 核心` as `- 重音：<accent_display>`
- for multi-item cards, keep `accent_display` order aligned with `headword`; leave it blank when the accent is uncertain instead of guessing
- accent contrast cards still belong under `学习系统/发音/アクセント`; ordinary vocab cards only keep the word's own accent cue

Offline dictionary accent candidates for vocabulary cards:

- before creating a new vocabulary card with blank `accent_display`, check whether the local offline dictionary is ready with `python3 tools/listening-transcribe-official/setup_offline_dictionary.py --check`
- the check must show sample accent candidates such as `公園⓪`; tokenization-only output is not enough for accent-card work
- use the same default cache as listening notes: `~/Library/Caches/jp-listening-dicts`, overrideable with `JP_LISTENING_DICT_DIR`
- if an existing card already has `accent_display`, preserve it and do not replace it with an offline dictionary candidate
- if the offline dictionary returns one reliable candidate for the exact headword/base form, fill `accent_display` on the new vocab card and mirror it in `## 核心`
- do not fill `accent_display` from offline data when the lookup is a multi-candidate accent, an inflected fragment, or a substring inside a larger compound
- do not label offline candidates as NHK-confirmed or human-confirmed; they are useful starting hints, not audited accent facts
- if accent uncertainty is the study target, create or update an accent-practice card under `学习系统/发音/アクセント/` instead of overloading the ordinary vocabulary card

When applying a full-vault accent audit, use the generated CSV as the review ledger. Only rows with `nhk_status: confirmed` may be written back. Prefer the safe writer:

```bash
python3 codex-skills/jp-review-material-maintainer/scripts/apply-accent-confirmations.py "学习系统/词库/重音标注全量草稿.csv"
python3 codex-skills/jp-review-material-maintainer/scripts/apply-accent-confirmations.py "学习系统/词库/重音标注全量草稿.csv" --write
```

### Grammar Card

Path: `学习系统/语法/<pattern>.md`

Required properties:

- `track: class_review`
- `item_type: grammar`
- `status`
- `priority`
- `done_today`
- `pattern`
- `meaning_zh`
- `formation`
- `source_notes`
- `first_seen`
- `last_seen`
- `seen_count`
- `error_count`
- `review_stage`
- `next_review`
- `last_reviewed`
- `contrast_with`
- `tags`

Linking rule for grammar cards:

- when a grammar card has a real comparison target, populate `contrast_with`
- also add Obsidian wikilinks in `## 核心` or `## 易错 / 易混` so the contrast is visible during review
- default to linking high-confusion neighbors, near-synonyms, or cards that are explicitly easier to remember side by side
- keep cards separate unless they are genuinely one teaching point; prefer cross-links over forced merging

Expected tags:

- `jp/grammar`
- `jp/class_review`
- add `jp/high_risk` when the pattern repeatedly appears in mistakes, confusions, or high-frequency review lists

Body shape to preserve:

- `## 核心`
- `## 例句`
- optional `## 易错 / 易混`
- `## 来源`

Naming rules:

- default to the canonical pattern name
- allow a grouped grammar note only when the items are clearly one teaching point:
  - paired contrasts
  - one compact paradigm
  - one honorific mapping set

### Error Card

Path: `学习系统/错题/YYYY-MM-DD_<label>.md`

Required properties:

- `track: class_review`
- `item_type: error`
- `status`
- `priority`
- `done_today`
- `source_notes`
- `first_seen`
- `last_seen`
- `seen_count`
- `error_count`
- `review_stage`
- `next_review`
- `last_reviewed`
- `wrong_form`
- `correct_form`
- `reason`
- `related_items`
- `tags`

Expected tags:

- `jp/error`
- `jp/class_review`
- add `jp/high_risk` when the same misunderstanding reappears or would cause repeated test misses

Body shape to preserve:

- `## 错误句` or `## 错误理解`
- `## 正确句` or `## 正确理解`
- `## 为什么错`
- `## 下次怎么避免`

## Update Rules

### If the word already exists in the base lexicon only

- update `last_seen`
- increment `seen_count` when this is a new occurrence
- append the new note to `source_notes` if missing
- create or restore the focus review card
- set the base note to `status: promoted`
- include tag `jp/promoted`
- reset the focus review card to `status: active`, `review_stage: day0`, `next_review: today`

### If the word already exists in focus review cards

- update the focus card, not just the base note
- update `last_seen`
- increment `seen_count` when appropriate
- append the new note to `source_notes` if missing
- raise `priority` to `high` if the new context shows confusion or repeated failure
- if the card is currently `mastered`, switch it back to `active`
- reset the review schedule when the word clearly reappears as a weakness, or when a mastered card re-enters active review:
  - `review_stage: day0`
  - `next_review: today`

Also keep the base lexicon note and mark it as promoted:

- `status: promoted`
- include tag `jp/promoted`
- `promote_candidate: false`

### Focus-First Flow

When a classroom word is first extracted and neither layer exists:

1. create the focus note under `<focus_vocab_root>`
2. initialize focus fields:
   - `status: active`
   - `priority: normal` unless risk is obvious
   - `done_today: false`
   - `error_count: 0`
   - `review_stage: day0`
   - `next_review: today`
   - `last_reviewed: ""`
3. do not create the base lexicon note yet

### Sink Flow

When a focus review card finishes `day180` and is ready to sink:

1. create or update the base note under `<base_vocab_root>`
2. copy over `headword`, `reading`, `meaning_zh`, `source_notes`, `first_seen`, `last_seen`, and `seen_count`
   - also copy `accent_display`, including a blank placeholder when the accent is unknown
3. set the base note to `status: promoted`
4. include tag `jp/promoted`
5. switch the focus card to `status: mastered`
6. clear active scheduling on the focus card:
   - `done_today: false`
   - `next_review: ""`
   - keep `last_reviewed` as the completion date

### Closeout Schedule

All training lines use the same review curve:

`day0 -> day1 -> day3 -> day7 -> day14 -> day30 -> day90 -> day180 -> mastered`

Use `codex-skills/jp-next-day-review-updater/scripts/run-next-day-review-update.sh` for closeout. It scans active training notes, processes only `status: active` and `done_today: true`, and supports `--dry-run` before writing.

Normal advancement:

- `day0 -> day1`, next review = completion date + 1 day
- `day1 -> day3`, next review = completion date + 3 days
- `day3 -> day7`, next review = completion date + 7 days
- `day7 -> day14`, next review = completion date + 14 days
- `day14 -> day30`, next review = completion date + 30 days
- `day30 -> day90`, next review = completion date + 90 days
- `day90 -> day180`, next review = completion date + 180 days
- `day180 -> mastered`, clear `next_review`

Delay rule:

- compute `overdue_days = completion date - original next_review`
- compute `allowed_delay = max(1, current stage days)`
- if `overdue_days <= allowed_delay`, advance to the next stage
- if `overdue_days > allowed_delay`, keep the current `review_stage` and set `next_review = completion date + allowed_delay`
- in both cases, set `last_reviewed` to the completion date and reset `done_today: false`

## Grammar And Error Update Rules

### If the grammar card already exists

- update `last_seen`
- increment `seen_count` when this is a new occurrence
- append the new note to `source_notes` if missing
- if the pattern appears again inside `間違えた問題` or is clearly noted as a weakness:
  - increment `error_count`
  - raise `priority` to `high`
  - set `done_today: false`
  - reset review:
    - `review_stage: day0`
    - `next_review: today`
    - `last_reviewed: ""`

### If the error card already exists for the same misunderstanding

- update that card instead of creating a duplicate with a different date
- update `last_seen`
- increment `seen_count`
- increment `error_count`
- append the new note to `source_notes` if missing
- set `done_today: false`
- reset review:
  - `review_stage: day0`
  - `next_review: today`
  - `last_reviewed: ""`

### If the mistake is new

- create one error card per distinct misunderstanding, not one per raw sentence fragment
- if multiple examples in the source note test the same point, prefer one stronger card with the clearest wrong/correct contrast
- if the source note only records a compact pattern gloss such as `〜とはいえない：不能说是～`, it may be better to create a grammar card instead of an error card

## Extraction Workflow

When splitting a classroom note:

1. use `obsidian-cli` to search and read only the target note and the small set of matching candidate vocab notes
2. collect explicit text vocabulary items first, then inspect images embedded inside `## 単語` and collect clearly readable image-backed items
3. normalize obvious variants before searching
4. for each word, follow the canonical search order
5. default classroom vocabulary to focus review first, then only touch the base lexicon when restoring prior history or sinking a mastered word
6. collect explicit grammar items from `文法` and route them to grammar cards
7. split `間違えた問題` into:
   - grammar-card updates when the mistake strengthens an existing pattern card
   - error-card creation or updates for the concrete misunderstanding itself
8. create or update notes with valid Obsidian frontmatter and wikilinks
9. keep examples or confusion notes short and source-backed
10. when comparison clearly improves memory, add both metadata links (`contrast_with` / `confusable_with`) and body wikilinks to the counterpart card

Do not scan the entire vault if targeted search is enough.

## What Good Output Looks Like

For a note-splitting task, report:

- new focus vocab notes
- updated focus vocab notes
- restored mastered vocab notes
- base vocab notes created or updated because of sink/history alignment
- promoted words
- new or updated focus cards
- new or updated grammar cards
- new or updated error cards
- any merge or naming decisions that need review

## Validation

After edits:

- check that frontmatter keys match the intended layer
- check that focus-card words also exist in the base lexicon as `promoted`
- check that grammar cards keep `pattern` as the naming anchor
- check that error cards keep one clear wrong/correct pair and do not duplicate an existing misunderstanding under a new filename
- avoid duplicate notes across the two layers with conflicting names
- if a `.base` file was changed, validate it with the `obsidian-bases` workflow

If a word is borderline between single-word and grouped-card treatment, note the assumption briefly in the response.
