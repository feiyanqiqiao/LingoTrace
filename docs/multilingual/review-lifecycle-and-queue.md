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

`base_vocab_root` remains readable for compatibility but accepts no new review-material or rollover writes. Consolidating legacy base cards is a separate explicit migration.
