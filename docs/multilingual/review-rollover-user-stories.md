# Review Rollover User Stories and Acceptance Tests

## Purpose

This document defines the user-facing behavior that must survive review-rollover migration. It is a maintenance contract for language-pack implementations of the shared `review_rollover` capability.

The migration rule is simple: a rollover behavior is not considered migrated until it has a user story, acceptance criteria, and a regression test.

## Ownership Boundary

Core owns:

- Vault context loading.
- Language-pack manifest loading.
- Capability enablement and stability checks.
- Vault-relative write guards.
- `FileMutation` preview/apply execution.
- Review-state storage primitives and transaction-log primitives.

Language packs own:

- Natural-language agent instructions.
- Path roles used by the pack.
- Review-card field validation.
- Language-specific rollover rules.
- Review-card frontmatter rollover.
- Daily-note text.
- Vocabulary promotion and merge semantics.
- Pack-level regression tests.

## User Stories

### 1. Preview before settlement

As a learner, I want the agent to show which review cards will change before saving, so I can confirm the settlement safely.

Acceptance criteria:

- Preview scans configured review-card roots and reads card frontmatter.
- Preview returns planned writes for active cards with `done_today: true`.
- Preview does not modify any file.
- The planned write includes old/new review stage, old/new `next_review`, `last_reviewed`, and `done_today: false`.

Regression coverage:

- `test_review_rollover_previews_due_target_card_without_writes`

### 2. Apply normal SRS advancement

As a learner, I want completed review items to advance to the next SRS stage, so tomorrow's review queue reflects today's work.

Acceptance criteria:

- Apply writes ordinary review-card frontmatter through core file mutations.
- Apply sets `done_today: false` in card frontmatter.
- Apply advances `review_stage` by the pack's SRS table in card frontmatter.
- Apply updates `next_review` from the run date and interval in card frontmatter.
- Apply writes `last_reviewed` as the run date in card frontmatter.

Regression coverage:

- `test_review_rollover_apply_advances_due_target_card`

### 3. Reschedule overdue cards without advancing

As a learner, I want very overdue cards to be rescheduled instead of advanced, so stale memory is not treated as successful recall.

Acceptance criteria:

- If overdue days exceed the current stage's allowed delay, keep the current `review_stage`.
- Set `next_review` to `run_date + allowed_delay`.
- Clear `done_today`.
- Write `last_reviewed`.
- Mark the planned write as delayed reschedule.

Regression coverage:

- `test_review_rollover_reschedules_overdue_card_without_advancing_stage`

### 4. Promote completed day180 focus vocabulary

As a learner, I want a focus vocabulary card that finishes `day180` to leave active review, so active review stays focused and stable knowledge remains searchable.

Acceptance criteria:

- A day180 focus vocabulary card becomes `mastered`.
- The focus Markdown card's review-state frontmatter is updated during settlement.
- Base-vocabulary content maintenance is a separate content workflow; settlement does not block on base-card Markdown writes.

Regression coverage:

- `test_review_rollover_sinks_day180_focus_vocab_to_base_vocab`

### 5. Keep base vocabulary content out of settlement

As a learner, I want settlement to avoid rewriting base vocabulary content, so iCloud content-file synchronization cannot block review closeout.

Acceptance criteria:

- Existing base vocabulary Markdown remains unchanged during review settlement.
- Focus-card SRS frontmatter still becomes `mastered`.
- Any base-vocabulary creation or merge must run through a separate explicit content-maintenance workflow.

Regression coverage:

- `test_review_rollover_day180_state_does_not_merge_base_vocab_during_settlement`

### 6. Update an existing daily checklist

As a learner, I want the daily note's review summary to reflect the settlement while preserving my manually recorded card points.

Acceptance criteria:

- Daily note Markdown is not rewritten by default during settlement.
- Settlement can complete even when the daily note is missing, unavailable, or iCloud-delayed.
- A second preview after apply returns no remaining review-card planned writes.

Regression coverage:

- `test_review_rollover_updates_existing_daily_checklist_and_preserves_card_points`

### 7. Append a checklist when the daily note has no anchor

As a learner, I want settlement to avoid editing a daily note without my explicit content-maintenance request.

Acceptance criteria:

- If the daily note exists but lacks the checklist anchor, leave the note unchanged during settlement.
- Review-state rollover still completes.

Regression coverage:

- `test_review_rollover_appends_daily_checklist_when_note_has_no_anchor`

### 8. Complete settlement when the daily note is missing

As a learner, I want review-card settlement to complete even when no daily note exists yet.

Acceptance criteria:

- Missing daily note does not block review-card rollover.
- No daily-note write is planned by default.
- Review-state updates still apply.

Regression coverage:

- Covered by card-only rollover tests such as `test_review_rollover_apply_advances_due_target_card`

### 9. Block apply on invalid completed cards

As a learner, I want settlement to fail before writing if any completed card has invalid review state, so the vault is not partially settled.

Acceptance criteria:

- Invalid `next_review` blocks apply.
- Unknown `review_stage` blocks apply.
- Missing required promotion fields block day180 focus-vocabulary promotion.
- Missing or invalid required card frontmatter blocks settlement.
- No card mutation is applied when blocking errors exist.

Regression coverage:

- `test_review_rollover_blocks_all_writes_when_any_completed_card_has_invalid_next_review`

### 10. Keep archived review-state out of runtime

As a maintainer, I want archived `.lingotrace/review-state/` files to stay out of runtime, so card frontmatter remains the only active source of truth.

Acceptance criteria:

- The total-training Base reads ordinary card frontmatter.
- Review rollover does not read `.lingotrace/review-state/*.json`.
- Archived review-state files are backup/reference only.
- Redundant `views/review-state/*.md` snapshots are not generated.

Regression coverage:

- `test_review_rollover_previews_due_target_card_without_writes`

### 11. Respect capability and write guards

As a maintainer, I want all writes to pass through core manifest and capability guards, so language-pack workflows cannot write outside their declared scope.

Acceptance criteria:

- Content-writing workflows create `FileMutation` objects instead of writing Vault files directly.
- Review settlement writes only configured review-card frontmatter through `FileMutation`.
- Archived review-state JSON files are not part of the write path.
- `run_file_mutations` checks the selected language-pack manifest.
- The target vault must enable `review_rollover`.
- All paths must be vault-relative and inside guarded roots.

Regression coverage:

- `tests/lingotrace/core/test_mutations.py`
- `tests/lingotrace/core/test_capabilities.py`
- Japanese workflow tests exercise the end-to-end mutation path.

## Migration Test Matrix

| Behavior | Japanese regression test | Required for future English pack |
| --- | --- | --- |
| Preview before write | `test_review_rollover_previews_due_target_card_without_writes` | Yes |
| Normal SRS advancement | `test_review_rollover_apply_advances_due_target_card` | Yes |
| Delayed overdue reschedule | `test_review_rollover_reschedules_overdue_card_without_advancing_stage` | Yes |
| day180 focus state mastery | `test_review_rollover_sinks_day180_focus_vocab_to_base_vocab` | Yes |
| Existing base-card untouched | `test_review_rollover_day180_state_does_not_merge_base_vocab_during_settlement` | Yes |
| Existing daily checklist untouched | `test_review_rollover_updates_existing_daily_checklist_and_preserves_card_points` | Yes |
| Daily note without anchor untouched | `test_review_rollover_appends_daily_checklist_when_note_has_no_anchor` | Yes |
| Missing daily note | Card-only apply tests | Yes |
| Invalid card blocks apply | `test_review_rollover_blocks_all_writes_when_any_completed_card_has_invalid_next_review` | Yes |
| Archived review-state ignored | Card-frontmatter preview/apply tests | Yes |
| Capability/write guard | Core mutation and capability tests | Yes |

## Maintenance Rule

When changing `review_rollover`, update this document and add or adjust a regression test in the same change. If a behavior is language-specific, place the test in that language pack's workflow test suite. If a behavior is shared by every language pack, add a core or conformance test.
