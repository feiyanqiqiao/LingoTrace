# Review Lifecycle and Queue Contract

This contract is shared by every language pack that exposes scheduled review. It separates whether material participates in the queue from how far it has progressed.

## Lifecycle Fields

`review_status` is the only lifecycle field for new writes:

- `backlog`: material exists but is outside scheduled review.
- `queued`: material participates in scheduled review.
- `mastered`: the memory curve is complete.
- `archived`: the material is retired and excluded from learning views.

`review_stage` stores progress independently. It is blank before first activation, one of `day0`, `day1`, `day3`, `day7`, `day14`, `day30`, `day90`, or `day180` while progress exists, and `mastered` after completion. Leaving the queue does not erase progress: `backlog + dayN` is the supported paused-equivalent state.

New writes must not add legacy `status` or `review_enabled` fields.

## Valid States

- `queued` requires an active day stage, a valid `next_review` date, and Boolean `done_today`.
- `backlog` may have no schedule or may retain a previous active stage and date; `done_today` must be false.
- `mastered` requires `review_stage: mastered`, blank `next_review`, and `done_today: false`.
- `archived` requires `done_today: false`, is excluded from training and material-library views, and otherwise preserves history.

Every batch validates all proposed records before any file is written.

## Queue Transitions

The stable `review_queue` capability accepts exact Vault-relative Markdown paths. Applying an existing-file change requires confirmation.

```json
{
  "items": [
    {
      "path": "vault/relative.md",
      "target_status": "queued",
      "activation": "resume"
    }
  ],
  "change_date": "YYYY-MM-DD",
  "existing_update_confirmed": true
}
```

- `backlog -> queued + resume` keeps a valid stage and schedules it on `change_date`; a never-started item begins at `day0`.
- `backlog/mastered -> queued + restart` resets to `day0`, clears `last_reviewed`, and schedules it on `change_date`.
- `queued -> backlog` clears `done_today` and preserves progress and historical dates.
- `queued -> mastered` is owned by `review_rollover`; content-maintenance workflows own archival.

## Creation Defaults

- Vocabulary, grammar, explicit errors, and pronunciation weaknesses default to `queued/day0`.
- Listening notes, speaking cards, and chunks default to `backlog` without scheduling.
- A user may explicitly request creation and queue activation together; the resulting material is `queued/day0` on the creation date.

## Views and Settlement

`total-training.base` shows only `queued` material. `material-library.base` provides read-only lifecycle labels for backlog and mastered material; it does not expose `review_status` as an editable column. Lifecycle changes must use `review_queue`.

`review_rollover` processes only `queued && done_today`. Completing `day180` marks the original card `mastered`; it does not create or update a second base-vocabulary copy.

New and fully migrated Vaults use `focus_vocab_root` as the only vocabulary path role. They do not declare `base_vocab_root`, and the material library does not include archived base-vocabulary records. An older Vault may retain the legacy role temporarily so its explicit consolidation can finish; normal review-material creation and rollover never write there.

## Legacy Lifecycle Migration

`review_lifecycle_migration` scans configured review and material roles without writing during preview. It reports exact paths and before/after values, requires `existing_update_confirmed: true` for apply, removes `status` and `review_enabled`, and must return zero remaining writes on the verification preview.

Legacy mapping is conservative:

- `mastered` and `promoted` become `mastered`; `archived` remains archived.
- Explicit legacy `review_enabled: false` becomes backlog while retaining progress; `review_enabled: true` becomes queued and receives a valid day/date initialization when missing.
- An active record with real review history, a stage beyond `day0`, or a valid vocabulary/grammar/error/pronunciation schedule becomes `queued`.
- Unscheduled active records become `backlog`.
- Listening, speaking, and chunk material at `day0` with no completed review becomes `backlog`.
- A progressed record with a missing next date is queued on the explicit migration date; invalid explicit new-model combinations block the batch.

## Vocabulary Consolidation

`vocab_consolidation` runs only after lifecycle migration and keeps `focus_vocab_root` as the single canonical vocabulary directory. It is a compatibility operation for older Vaults that still explicitly configure `base_vocab_root`; new Vaults do not create or configure that directory.

- Base-only unscheduled cards become focus backlog cards; legacy promoted cards become focus mastered cards; real schedules remain queued.
- For a duplicate, focus frontmatter, schedule, and body are authoritative. Base fills only blank scalar fields and contributes deduplicated lists and sources.
- Counters use the greater value, `first_seen` uses the earliest valid date, and recent dates use the latest valid date.
- Different non-empty focus and base bodies block the complete batch for manual review. After review, the user may confirm exact base-card paths through `body_conflict_resolutions` with `focus` authority; unlisted conflicts, stale paths, and any other authority continue to block the batch.
- A confirmed focus-body resolution keeps the focus body and schedule, applies the ordinary safe metadata merge, and preserves the original base body in the archived redirect.
- A successfully consolidated base card is retained at its old path with `review_status: archived`, a canonical-card link, and an in-note redirect. It is never deleted.
- A second preview after apply must report zero remaining consolidation writes.
- After that zero-write verification and inbound-link migration, remove `base_vocab_root` from the Vault path configuration. The archived directory may remain on disk until the user chooses a later cleanup.
