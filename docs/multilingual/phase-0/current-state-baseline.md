# Phase 0 Japanese Current-State Baseline

- Baseline commit: `a7ecbd8cb05241c5efc24938c37d1cb84b68d4e4`
- Baseline date: `2026-06-14`
- Scope: public Japanese workflow behavior before the multilingual framework migration
- Private data: excluded

This document records migration evidence, not a permanent legacy API. The current `jp-*` entry points may be used during migration comparison, but the target Japanese Vault must run through the new core and Japanese language pack.

## Status Vocabulary

Evidence status:

- `declared`: stated by a Skill, template, or public document.
- `observed`: reproducible from a public script, validator, or read-only command.
- `verified`: covered by an executable public test or an accepted versioned manual case.

Migration status:

- `candidate`: identified behavior whose migration obligation still needs PR B evidence.
- `migration-required`: verified learning behavior that the new framework must preserve or explicitly supersede.
- `known-defect`: confirmed behavior that must be fixed before becoming a migration obligation.
- `superseded`: historical behavior replaced through an explicit behavior decision.

Boundary:

- `core-candidate`: potentially cross-language lifecycle or infrastructure behavior.
- `japanese-specific`: Japanese template, field, dictionary, naturalness, or language-processing behavior.
- `mixed-current`: current implementation combines shared and Japanese responsibilities.
- `migration-source`: evidence or a temporary source-side entry point, not a target runtime interface.
- `remove-after-cutover`: old-framework behavior that must not survive final cutover.
- `external-tool`: ListenKit or another tool boundary.

## Fixed Listening Notes

### JP-LISTEN-001 Input And Delegation

- Trigger and input: one local media file or one URL with an explicitly selected listening material directory.
- Preconditions: local media exists and is non-empty; URL input has an explicit target directory.
- Steps: the wrapper delegates acquisition and transcript generation to ListenKit, then invokes the Vault-specific renderer.
- Output: a listening note plus tracked transcript and media artifacts.
- Failure and completion: missing media, failed transcript acquisition, or incomplete artifacts stop completion.
- Repeat and manual content: the same material target is updated instead of creating an unrelated duplicate.
- Evidence: `EV-LISTEN-SKILL`, `EV-LISTEN-WRAPPER`, `EV-LISTEN-TESTS`.
- Status: `verified`; `migration-required`; `mixed-current` and `external-tool`.

### JP-LISTEN-002 Extensive And Intensive Modes

- Trigger and input: default extensive mode or explicit `--listening-mode intensive`.
- Steps: extensive mode renders an accent-aided script without learning slices; intensive mode renders a learning package before the plain script.
- Output: `listening_mode`, `## 脚本`, and mode-specific sections.
- Failure and completion: an intensive note is incomplete while slice placeholders remain.
- Repeat and manual content: an existing note keeps its established mode unless explicitly changed.
- Evidence: `EV-LISTEN-SKILL`, `EV-TEMPLATE-INDEX`, `EV-LISTEN-TESTS`.
- Status: `verified`; `migration-required`; `japanese-specific`.

### JP-LISTEN-003 Provenance And Source Audio

- Trigger and input: any generated listening note.
- Steps: keep transcript status/reference metadata and the source-audio embed.
- Output: traceable source media, transcript relationship, and note metadata.
- Failure and completion: a note cannot be considered complete when its declared media or transcript artifact is missing.
- Repeat and manual content: existing source relationships are retained when rerendering.
- Evidence: `EV-LISTEN-SKILL`, `EV-LISTEN-TESTS`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-LISTEN-004 Intensive Learning Blocks And Real Slices

- Trigger and input: intensive mode with reliable timestamps or a reviewed slice manifest.
- Steps: classify content as numbered dialogue, exchange dialogue, or sentence blocks; delegate deterministic clip export to ListenKit.
- Output: matching `segment_count`, `### SNN` blocks, audio embeds, manifest entries, and non-empty slice files.
- Failure and completion: unreliable numbering, order, or timestamps require a reviewed manifest; fabricated or missing clips are forbidden.
- Repeat and manual content: reviewed default manifests are reused; automatic manifests may be recalculated.
- Evidence: `EV-LISTEN-SKILL`, `EV-LISTEN-TESTS`, `EV-LISTEN-README`.
- Status: `verified`; `migration-required`; `mixed-current` and `external-tool`.

### JP-LISTEN-005 Japanese Accent Rendering

- Trigger and input: generated Japanese script text.
- Steps: prefer confirmed Vault accent data, otherwise use offline dictionary candidates; unknown values remain pending confirmation.
- Output: Japanese accent display in extensive scripts or intensive learning blocks.
- Failure and completion: local candidates are not written back as confirmed vocabulary data.
- Repeat and manual content: confirmed manual values take precedence over generated candidates.
- Evidence: `EV-LISTEN-SKILL`, `EV-LISTEN-TOOL`, `EV-LISTEN-TESTS`.
- Status: `verified`; `migration-required`; `japanese-specific`.

### JP-LISTEN-006 Common-Sentence Curation

- Trigger and input: a complete listening script.
- Steps: a model or human conservatively selects zero to five reusable sentences and records original sentence, replaceable frame, use scene, and selection reason.
- Output: `## 可直接背的常用句` and synchronized `daily_use_sentences` containing Japanese core sentences only.
- Failure and completion: generic filler and unresolved ASR are rejected; an empty result is valid.
- Repeat and manual content: reruns preserve manually curated selections unless reset is explicitly requested.
- Evidence: `EV-LISTEN-SKILL`, `EV-TEMPLATE-INDEX`, `EV-LISTEN-TESTS`.
- Status: `verified` for preservation and structure, `declared` for semantic quality; `candidate`; `japanese-specific`.

### JP-LISTEN-007 Dialogue Grouping

- Trigger and input: transcript structure showing reliable turn-taking or numbered exchanges.
- Steps: add conservative speaker labels and keep one complete exchange or numbered dialogue per learning block.
- Output: dialogue-structured script and slice groups.
- Failure and completion: ambiguous content falls back to sentence formatting; speaker identities are not invented.
- Repeat and manual content: reviewed grouping decisions remain authoritative.
- Evidence: `EV-LISTEN-SKILL`, `EV-LISTEN-TESTS`.
- Status: `verified`; `migration-required`; `japanese-specific`.

### JP-LISTEN-008 Speaking-Card Handoff

- Trigger and input: manually reviewed listening common-sentence candidates plus an explicit conversion request.
- Steps: hand off to the speaking-card workflow; do not auto-promote fresh candidates.
- Output: no speaking-card write occurs within the listening workflow itself.
- Failure and completion: unreviewed candidates remain only in the listening note.
- Repeat and manual content: user approval remains the promotion boundary.
- Evidence: `EV-LISTEN-SKILL`, `EV-SPEAK-SKILL`.
- Status: `declared`; `candidate`; `core-candidate`.

## Flexible Source Notes

### JP-SOURCE-001 Accepted Inputs And Material Preparation

- Trigger and input: text, transcript, ListenKit artifact, local audio/video, or URL.
- Preconditions: media and URL inputs are first converted into a stable source artifact bundle.
- Steps: the source-note wrapper invokes ListenKit for media preparation, then the Skill organizes learning content.
- Output: finalized media, readable transcript, structured artifact, and a source note.
- Failure and completion: missing preparation output stops note completion.
- Repeat and manual content: stable source artifacts are reused instead of inventing new provenance.
- Evidence: `EV-SOURCE-SKILL`, `EV-SOURCE-WRAPPER`.
- Status: `observed`; `candidate`; `mixed-current` and `external-tool`.

### JP-SOURCE-002 Collaborative Note Direction

- Trigger and input: prepared source material with an unknown learning emphasis.
- Steps: inspect enough material to propose a direction and confirm whether the note should emphasize vocabulary, grammar, pronunciation, writing, or content structure.
- Output: one learning note by default; multiple notes only after user choice.
- Failure and completion: the Skill does not impose a universal section layout.
- Repeat and manual content: user-selected structure remains authoritative.
- Evidence: `EV-SOURCE-SKILL`.
- Status: `declared`; `candidate`; `japanese-specific`.

### JP-SOURCE-003 Mandatory Provenance

- Trigger and input: every source note.
- Steps: record original URL or path, finalized in-Vault audio, audio embed, transcript Markdown, and structured artifact relationships when available.
- Output: traceable provenance independent of the note's learning structure.
- Failure and completion: provenance is mandatory and is never fabricated.
- Repeat and manual content: existing source links are preserved.
- Evidence: `EV-SOURCE-SKILL`.
- Status: `declared`; `candidate`; `core-candidate`.

### JP-SOURCE-004 Transcript Appendix

- Trigger and input: source material with transcript text.
- Steps: place the transcript appendix after the learning body.
- Output: flexible learning content followed by recoverable source text.
- Failure and completion: transcript-bearing notes are incomplete without the appendix.
- Repeat and manual content: body organization may change without deleting the appendix.
- Evidence: `EV-SOURCE-SKILL`.
- Status: `declared`; `candidate`; `core-candidate`.

### JP-SOURCE-005 Text-Only Material

- Trigger and input: text without audio.
- Steps: ask whether source media exists; if it does not, record that fact.
- Output: a source note without a fabricated media reference.
- Failure and completion: invented audio or provenance is forbidden.
- Repeat and manual content: later media can be attached explicitly.
- Evidence: `EV-SOURCE-SKILL`.
- Status: `declared`; `candidate`; `core-candidate`.

### JP-SOURCE-006 Card-Creation Boundary

- Trigger and input: a completed source note and an explicit request for review or speaking cards.
- Steps: hand off to the corresponding card workflow only after the source note exists.
- Output: the source-note workflow itself does not create vocabulary, grammar, pronunciation, error, or speaking cards.
- Failure and completion: automatic card promotion is forbidden.
- Repeat and manual content: downstream workflows retain source backlinks.
- Evidence: `EV-SOURCE-SKILL`, `EV-REVIEW-SKILL`, `EV-SPEAK-SKILL`.
- Status: `declared`; `candidate`; `core-candidate`.

## Review Material Maintenance

### JP-REVIEW-001 Configured Path Roles

- Trigger and input: any review-material search or write.
- Steps: resolve Focus, Base, grammar, error, pronunciation, and daily-note roots from `系统配置/paths.json`.
- Output: writes remain inside the configured role root.
- Failure and completion: prose examples are not treated as path authority.
- Repeat and manual content: moving a role requires a configuration update rather than broad note rewriting.
- Evidence: `EV-REVIEW-SKILL`, `EV-PATHS`, `EV-VAULT-TESTS`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-REVIEW-002 Focus-First Deduplication

- Trigger and input: a vocabulary candidate.
- Steps: search Focus first, then Base, opening only matched notes and the source note.
- Output: update, reactivate, or create exactly one Focus card.
- Failure and completion: a different source note does not justify a duplicate card.
- Repeat and manual content: existing card content and source history are merged.
- Evidence: `EV-REVIEW-SKILL`.
- Status: `declared`; `candidate`; `mixed-current`.

### JP-REVIEW-003 New Focus Vocabulary

- Trigger and input: a vocabulary item absent from Focus and Base.
- Steps: create a Focus card at `day0`, active status, and today's next review; do not create Base simultaneously.
- Output: a Japanese vocabulary card following the current template.
- Failure and completion: uncertain headword, core meaning, or reading requires confirmation.
- Repeat and manual content: a second encounter updates the same card.
- Evidence: `EV-REVIEW-SKILL`, `EV-VOCAB-TEMPLATE`.
- Status: `declared`; `candidate`; `mixed-current`.

### JP-REVIEW-004 Base Reappearance And Mastered Reactivation

- Trigger and input: a word found only in Base, or a mastered Focus card encountered again.
- Steps: create or restore the Focus card, merge source history, and reset active scheduling to `day0`.
- Output: Base remains long-term vocabulary while Focus becomes the active review object.
- Failure and completion: the system does not advance stale prior scheduling.
- Repeat and manual content: existing Japanese fields and notes are retained.
- Evidence: `EV-REVIEW-SKILL`.
- Status: `declared`; `candidate`; `mixed-current`.

### JP-REVIEW-005 Material Routing

- Trigger and input: source sections containing vocabulary, grammar, errors, accent contrast, phoneme contrast, or sentence practice.
- Steps: route each item to its role-specific card type and root.
- Output: vocabulary, grammar, error, pronunciation, and practice materials remain distinct.
- Failure and completion: accent and phoneme contrast cards are not stored as ordinary vocabulary or sentence practice.
- Repeat and manual content: existing role-specific cards are updated rather than retyped elsewhere.
- Evidence: `EV-REVIEW-SKILL`, `EV-TEMPLATE-INDEX`.
- Status: `declared`; `candidate`; `japanese-specific`.

### JP-REVIEW-006 Japanese Vocabulary Schema

- Trigger and input: creation or substantial rewrite of a Japanese vocabulary card.
- Steps: apply the Focus or Base schema and maintain `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, `kanji_diff_pairs`, comparison links, source history, and review fields as applicable.
- Output: flat Frontmatter usable by Obsidian Bases.
- Failure and completion: unknown accent remains blank or pending; local candidates are not confirmed automatically.
- Repeat and manual content: manually confirmed values and body sections take precedence.
- Evidence: `EV-REVIEW-SKILL`, `EV-VOCAB-TEMPLATE`, `EV-ROLLOVER-TESTS`.
- Status: `verified` for sink preservation and `declared` for broader maintenance; `candidate`; `japanese-specific`.

### JP-REVIEW-007 Grammar And Error Schemas

- Trigger and input: explicit grammar items or a concrete misunderstanding.
- Steps: use the role-specific template, deduplicate by grammar point or misunderstanding, and maintain source links.
- Output: grammar and error cards remain separate from vocabulary.
- Failure and completion: a compact grammar gloss may be routed to grammar rather than forced into an error card.
- Repeat and manual content: stronger existing cards are updated instead of creating weaker duplicates.
- Evidence: `EV-REVIEW-SKILL`, `EV-GRAMMAR-TEMPLATE`, `EV-TEMPLATE-INDEX`.
- Status: `declared`; `candidate`; `japanese-specific`.

### JP-REVIEW-008 Image-Backed Vocabulary

- Trigger and input: a source-note vocabulary section containing an image.
- Steps: inspect the image, exclude items already present as text, then apply the normal Focus-first flow.
- Output: source-backed vocabulary candidates without duplicate extraction.
- Failure and completion: unreadable or ambiguous image content requires confirmation.
- Repeat and manual content: source note text remains authoritative.
- Evidence: `EV-REVIEW-SKILL`.
- Status: `declared`; `candidate`; `japanese-specific`.

### JP-REVIEW-009 Vocabulary Sink Contract

- Trigger and input: a Focus vocabulary card completing `day180`.
- Steps: create or update Base, merge source history, preserve Japanese metadata including `accent_display` and `kanji_diff*`, mark Base promoted, and mark Focus mastered.
- Output: Base long-term record plus inactive mastered Focus record.
- Failure and completion: invalid fields or path configuration stop the operation before partial writes.
- Repeat and manual content: an existing Base note keeps unrelated manual sections while owned fields and source links are merged.
- Evidence: `EV-REVIEW-SKILL`, `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`.
- Status: `verified`; `migration-required`; `mixed-current`.

## Survival Speaking Cards

### JP-SPEAK-001 Conservative Accepted Inputs

- Trigger and input: manually reviewed listening candidates, user-provided daily-life phrases, or existing cards needing maintenance.
- Steps: accept only natural, immediately useful expressions with a clear scene and role.
- Output: one focused card per core sentence or fixed exchange.
- Failure and completion: fresh unreviewed candidates, unresolved ASR, textbook drills, and one-off lines are rejected.
- Repeat and manual content: explicit user review remains the promotion gate.
- Evidence: `EV-SPEAK-SKILL`, `EV-LISTEN-SKILL`.
- Status: `declared`; `candidate`; `japanese-specific`.

### JP-SPEAK-002 Deduplication And Merge

- Trigger and input: an accepted speaking expression.
- Steps: recursively search the speaking library for exact `jp_text`, equivalent core exchanges, and merge candidates.
- Output: one maintained card rather than duplicates.
- Failure and completion: unresolved equivalence requires review.
- Repeat and manual content: existing review state is preserved on updates.
- Evidence: `EV-SPEAK-SKILL`, `EV-SPEAK-VALIDATOR`.
- Status: `observed`; `candidate`; `mixed-current`.

### JP-SPEAK-003 Scene Placement And Schema

- Trigger and input: a new speaking card.
- Steps: place it under one scene category and set scene, function, role, Japanese text, meaning, reply hint, source, and SRS fields.
- Output: a `track: survival_speaking` card initialized at `day0`.
- Failure and completion: cards outside one scene subdirectory or missing required fields fail validation.
- Repeat and manual content: new categories are created only for genuinely new practice scenes.
- Evidence: `EV-SPEAK-SKILL`, `EV-TEMPLATE-INDEX`, `EV-SPEAK-VALIDATOR`.
- Status: `observed`; `candidate`; `japanese-specific`.

### JP-SPEAK-004 Provenance And Optional Slice Audio

- Trigger and input: a speaking expression with a source note or reliable matching slice.
- Steps: preserve source backlinks and optionally embed the original slice without copying audio into the card directory.
- Output: traceable card and direct shadowing audio when available.
- Failure and completion: source-free user input uses an empty source list; provenance is not invented.
- Repeat and manual content: naturalized card wording can retain a brief textbook-variant note.
- Evidence: `EV-SPEAK-SKILL`, `EV-SPEAK-VALIDATOR`.
- Status: `observed`; `candidate`; `core-candidate`.

### JP-SPEAK-005 Scene-Guide Isolation

- Trigger and input: long source material or transcript appendices related to speaking scenes.
- Steps: keep them under scene guides without the speaking-card track.
- Output: guides may link to cards but do not enter the review queue.
- Failure and completion: a guide carrying `track: survival_speaking` fails validation.
- Repeat and manual content: the card workflow does not expand long guides.
- Evidence: `EV-SPEAK-SKILL`, `EV-SPEAK-VALIDATOR`.
- Status: `observed`; `candidate`; `core-candidate`.

## Daily Review Rollover

### JP-ROLLOVER-001 Managed Scope And Eligibility

- Trigger and input: explicit end-of-day rollover, normally after a dry-run.
- Steps: scan only configured managed roots and select `status: active` plus `done_today: true` items.
- Output: an eligible item set and dry-run summary.
- Failure and completion: missing paths config, missing fields, or unknown stages fail explicitly.
- Repeat and manual content: inactive and incomplete items remain unchanged.
- Evidence: `EV-ROLLOVER-SKILL`, `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-ROLLOVER-002 Fixed Stage Chain

- Trigger and input: an eligible review card at a known stage.
- Steps: advance through `day0`, `day1`, `day3`, `day7`, `day14`, `day30`, `day90`, `day180`, then mastered.
- Output: updated `review_stage` and `next_review`.
- Failure and completion: unknown stages stop the run.
- Repeat and manual content: deterministic dates do not depend on model output.
- Evidence: `EV-ROLLOVER-SKILL`, `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`, `EV-REVIEW-FLOW`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-ROLLOVER-003 Delayed Review Rule

- Trigger and input: an eligible card completed after its scheduled date.
- Steps: compare overdue days with the current stage allowance; advance within tolerance or retain the stage and reschedule beyond tolerance.
- Output: deterministic next-review date.
- Failure and completion: invalid dates fail instead of being guessed.
- Repeat and manual content: the same run date and input produce the same result.
- Evidence: `EV-ROLLOVER-SKILL`, `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`, `EV-REVIEW-FLOW`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-ROLLOVER-004 Atomic State Update

- Trigger and input: a fully validated eligible set.
- Steps: calculate pending writes before applying them; update `last_reviewed`, stage, date, and `done_today` only for completed items.
- Output: all accepted writes and a change summary.
- Failure and completion: validation failure prevents partial state advancement; dry-run writes nothing.
- Repeat and manual content: unowned Frontmatter and body sections are preserved.
- Evidence: `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`.
- Status: `verified`; `migration-required`; `core-candidate`.

### JP-ROLLOVER-005 Vocabulary Sink

- Trigger and input: eligible `item_type: vocab` at `day180`.
- Steps: execute the vocabulary sink contract and clear active Focus scheduling.
- Output: promoted Base note and mastered Focus note.
- Failure and completion: sink validation participates in the same pending-write boundary.
- Repeat and manual content: existing Base content and merged source relationships are preserved.
- Evidence: `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`, `EV-REVIEW-SKILL`.
- Status: `verified`; `migration-required`; `mixed-current`.

### JP-ROLLOVER-006 Daily Checklist Update

- Trigger and input: rollover with a matching daily note.
- Steps: replace or append only the `## 每日学习清单` tail using the fixed completion, difficulty, and reflection structure.
- Output: localized daily summary.
- Failure and completion: a missing daily note skips checklist writing but does not cancel valid review-state rollover.
- Repeat and manual content: existing difficulty bullets and sections outside the checklist are preserved.
- Evidence: `EV-ROLLOVER-SKILL`, `EV-ROLLOVER-CODE`, `EV-ROLLOVER-TESTS`, `EV-DAILY-TEMPLATE`.
- Status: `verified`; `migration-required`; `mixed-current`.

## Baseline Test Result

The following suites passed in the isolated PR A worktree using the system Python runtime on `2026-06-14`:

- listening transcription: 74 tests
- next-day review rollover: 6 tests
- Vault structure: 16 tests

The local Homebrew Python 3.14 runtime showed first-load delays for native extension modules. PR B must use GitHub Actions with Python 3.14 as the authoritative required check.
