# Multilingual Review Rollover User Stories and Acceptance Tests

Status: `Reference Guidance`

Maturity path: `Reference Guidance -> Candidate Contract -> Enforced Contract`

Related guidance index: [Language Pack Capability Guidance](language-pack-capability-guidance.md)

## Purpose

This document defines the user-facing behavior that must survive review-rollover migration across language packs. It is the shared maintenance contract for implementations of the `review_rollover` capability.

The migration rule is simple: a rollover behavior is not considered migrated until it has a user story, acceptance criteria, and a regression test.

The active review-state source of truth is review-card Markdown frontmatter. Rollover must not introduce a parallel review-state runtime store or snapshot surface.

## Applicability

All language packs that implement `review_rollover` should index, reference, and satisfy this document before the capability is considered complete.

This document is a shared contract for:

- Preview/apply/second-preview settlement flow.
- Review-card frontmatter as the runtime source of truth.
- Fixed memory-curve advancement.
- Delayed-review rescheduling.
- Invalid-state blocking before writes.
- Daily-note independence.
- Capability and write-guard enforcement.

Language packs may define their own path roles, card-type fields, templates, and user-facing wording. If a language pack needs to change a shared rollover rule, the pack must document the exception, add language-specific acceptance criteria, and provide regression coverage before shipping the behavior.

The Japanese pack is the current reference implementation and test source for this contract.

## Ownership Boundary

Core owns:

- Vault context loading.
- Language-pack manifest loading.
- Capability enablement and stability checks.
- Vault-relative write guards.
- `FileMutation` preview/apply execution.
- Atomic file-application semantics and blocked-write reporting.

Language packs own:

- Natural-language agent instructions.
- Path roles used by the pack.
- Review-card field validation.
- Language-specific memory-curve and delayed-review rules.
- Review-card frontmatter rollover.
- Vocabulary mastery semantics.
- Decisions about optional daily-note or content-maintenance behavior.
- Pack-level regression tests.

## User Stories

### 1. Internal preview before settlement

As a learner, I want clear review-settlement requests to run without a second confirmation, while still using preview internally to prevent unsafe writes.

Acceptance criteria:

- Preview scans configured review-card roots and reads card frontmatter.
- Preview returns planned writes for active cards with `done_today: true`.
- Preview does not modify any file.
- The planned write includes old/new review stage, old/new `next_review`, `last_reviewed`, and `done_today: false`.
- For clear settlement requests, an accepted preview with no errors is immediately followed by apply.
- After apply, a fresh preview returns `0` remaining review-card planned writes.
- "更新总训练表" and "请更新总训练表" are treated as clear settlement requests.
- Other ambiguous requests still require clarification before choosing rollover versus dashboard maintenance.

Regression coverage:

- `test_review_rollover_previews_due_target_card_without_writes`
- `test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply`

### 2. Apply fixed memory-curve advancement

As a learner, I want completed review items to advance along a fixed memory curve, so scheduling stays predictable and does not depend on agent judgment.

Acceptance criteria:

- Apply writes ordinary review-card frontmatter through core file mutations.
- Only cards with `status: active` and `done_today: true` are eligible.
- The stage chain is fixed: `day0 -> day1 -> day3 -> day7 -> day14 -> day30 -> day90 -> day180 -> mastered`.
- Apply sets `done_today: false` in card frontmatter.
- Apply advances `review_stage` by the fixed memory curve in card frontmatter.
- Apply updates `next_review` from the settlement `run_date` and the next-stage interval, not by adding time to the previous `next_review`.
- Apply writes `last_reviewed` as the run date in card frontmatter.
- Unknown `review_stage` values block apply before any file is written.

Regression coverage:

- `test_review_rollover_apply_advances_due_target_card`
- `test_review_rollover_applies_every_memory_curve_transition_from_run_date`
- `test_review_rollover_blocks_unknown_stage_before_any_write`

### 3. Reschedule overdue cards without advancing

As a learner, I want very overdue cards to be rescheduled instead of advanced, so stale memory is not treated as successful recall.

Acceptance criteria:

- If overdue days exceed the current stage's allowed delay, keep the current `review_stage`.
- Set `next_review` to `run_date + allowed_delay`.
- Clear `done_today`.
- Write `last_reviewed`.
- Mark the planned write as delayed reschedule.
- If `overdue_days == allowed_delay`, the card is still allowed to advance.

Regression coverage:

- `test_review_rollover_reschedules_overdue_card_without_advancing_stage`
- `test_review_rollover_advances_when_overdue_days_equal_allowed_delay`

### 4. Complete day180 cards as mastered

As a learner, I want a card that finishes `day180` to leave active review, so the daily queue stays focused on material that still needs scheduled review.

Acceptance criteria:

- A card that advances from `day180` becomes `review_stage: mastered`.
- The card's `status` becomes `mastered`.
- `done_today` is cleared.
- `last_reviewed` is set to the settlement run date.
- `next_review` is cleared because mastered cards are no longer scheduled by the normal active-review queue.
- A completed focus vocabulary card is promoted into the base vocabulary layer while preserving existing base-card manual content.
- If a future language pack needs type-specific mastery behavior, it must update this contract and its tests before changing implementation.

Regression coverage:

- `test_review_rollover_applies_every_memory_curve_transition_from_run_date`
- `test_apply_updates_done_today_review_stage_next_review_and_mastered_status`
- `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body`
- `test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match`

### 5. Restrict base vocabulary writes to mastery sink

As a learner, I want settlement to update base vocabulary only when a focus vocabulary card completes the full review cycle, so long-term vocabulary remains aligned without broad base rewrites.

Acceptance criteria:

- Existing base vocabulary Markdown remains unchanged for non-mastered cards and non-vocabulary cards.
- When a focus vocabulary card advances from `day180` to `mastered`, stable vocabulary fields are written to the base vocabulary layer.
- Existing base vocabulary manual body content is preserved.
- Base source references are merged with the completed focus card's source references.
- Any broad base-vocabulary merge, move, deletion, or rewrite outside mastery sink must run through a separate explicit content-maintenance workflow.

Regression coverage:

- `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body`
- `test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match`
- `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab`

### 6. Do not rewrite daily notes during settlement

As a learner, I want review settlement to avoid rewriting my daily notes by default, so manual notes and iCloud-delayed daily files cannot block review closeout.

Acceptance criteria:

- Daily note Markdown is not rewritten by default during settlement.
- Settlement can complete even when the daily note is missing, unavailable, or iCloud-delayed.
- If a daily-note summary is desired, it must be handled by an explicit content-maintenance workflow rather than normal rollover.

Regression coverage:

- `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab`

### 7. Leave daily notes without anchors unchanged

As a learner, I want settlement to avoid editing a daily note without my explicit content-maintenance request.

Acceptance criteria:

- If the daily note exists but lacks the checklist anchor, leave the note unchanged during settlement.
- Review-card rollover still completes.

Regression coverage:

- `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab`

### 8. Complete settlement when the daily note is missing

As a learner, I want review-card settlement to complete even when no daily note exists yet.

Acceptance criteria:

- Missing daily note does not block review-card rollover.
- No daily-note write is planned by default.
- Review-card frontmatter updates still apply.

Regression coverage:

- `test_review_rollover_completes_when_daily_note_is_missing`

### 9. Block apply on invalid completed cards

As a learner, I want settlement to fail before writing if any completed card has invalid review state, so the vault is not partially settled.

Acceptance criteria:

- Invalid `next_review` blocks apply.
- Unknown `review_stage` blocks apply.
- Missing or invalid required card frontmatter blocks settlement.
- No card mutation is applied when blocking errors exist.

Regression coverage:

- `test_review_rollover_blocks_unknown_stage_before_any_write`
- `test_review_rollover_blocks_invalid_next_review_before_any_write`
- `test_validation_failure_blocks_planning_before_any_write_is_applied`

### 10. Respect capability and write guards

As a maintainer, I want all writes to pass through core manifest and capability guards, so language-pack workflows cannot write outside their declared scope.

Acceptance criteria:

- Content-writing workflows create `FileMutation` objects instead of writing Vault files directly.
- Review settlement writes only configured review-card frontmatter through `FileMutation`.
- Parallel review-state JSON files or generated snapshot notes are not part of the write path.
- `run_file_mutations` checks the selected language-pack manifest.
- The target vault must enable `review_rollover`.
- All paths must be vault-relative and inside guarded roots.

Regression coverage:

- `tests/lingotrace/core/test_mutations.py`
- `tests/lingotrace/core/test_capabilities.py`
- Japanese workflow tests exercise the end-to-end mutation path.

## Migration Test Matrix

| Behavior | Reference Japanese regression coverage | Coverage status | Required for every language pack |
| --- | --- | --- | --- |
| Internal preview before write | `test_review_rollover_previews_due_target_card_without_writes` | Covered | Yes |
| Clear request applies without second confirmation | Agent-skill/docs contract tests | Covered outside workflow unit tests | Yes |
| Second preview after apply returns zero planned writes | `test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply` | Covered | Yes |
| Fixed memory-curve advancement | `test_review_rollover_apply_advances_due_target_card` | Covered | Yes |
| Every memory-curve transition | `test_review_rollover_applies_every_memory_curve_transition_from_run_date` | Covered | Yes |
| Delayed overdue reschedule | `test_review_rollover_reschedules_overdue_card_without_advancing_stage` | Covered | Yes |
| `overdue_days == allowed_delay` advances | `test_review_rollover_advances_when_overdue_days_equal_allowed_delay` | Covered | Yes |
| day180 card becomes mastered | `test_review_rollover_applies_every_memory_curve_transition_from_run_date` | Covered | Yes |
| day180 focus vocab sinks to base | `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body`; `test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match` | Covered | Yes |
| Existing base-card manual body preserved during sink | `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body` | Covered | Yes |
| Non-mastered base-card untouched | `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab` | Covered | Yes |
| Existing daily note untouched | `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab` | Covered | Yes |
| Daily note without anchor untouched | `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab` | Covered | Yes |
| Missing daily note | `test_review_rollover_completes_when_daily_note_is_missing` | Covered | Yes |
| Invalid card blocks apply | `test_review_rollover_blocks_unknown_stage_before_any_write`, `test_review_rollover_blocks_invalid_next_review_before_any_write` | Covered | Yes |
| Capability/write guard | Core mutation and capability tests | Covered | Yes |

## Language-Pack Implementation Checklist

Before adding `review_rollover` to a new language pack:

- Declare the capability in the language-pack manifest.
- Define review-card path roles for that pack.
- Reuse the shared frontmatter fields: `status`, `done_today`, `review_stage`, `next_review`, and `last_reviewed`.
- Implement the fixed memory curve or document an approved exception.
- Add pack-level tests mapped to every required row in the migration matrix.
- Ensure the agent skill maps clear settlement requests to `preview -> apply -> second preview`.
- Include local settlement phrases such as "更新总训练表" and "请更新总训练表" in clear settlement routing.
- Ensure dashboard/view maintenance requests stay separate from review settlement.

## Maintenance Rule

When changing `review_rollover`, update this document and add or adjust a regression test in the same change. If a behavior is language-specific, place the test in that language pack's workflow test suite. If a behavior is shared by every language pack, add a core or conformance test.

Do not mark a behavior as fully migrated only because it appears in implementation or agent instructions. It must also have matching acceptance criteria and executable regression coverage.
