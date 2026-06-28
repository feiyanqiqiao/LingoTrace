# English Applicability Review for the Review Rollover Chain

## Purpose

This document reviews whether the current LingoTrace review-rollover chain used by the Japanese learning vault can support an English learning vault. It focuses on runtime ownership, call flow, reusable parts, language-specific gaps, and the work required before an English implementation should be considered safe.

The chain under review is:

```text
User asks to settle review
-> Agent skill
-> language-pack review_rollover workflow
-> .lingotrace/vault-context.json validation
-> .lingotrace/paths.json path roles
-> scan role-owned cards
-> create FileMutation objects
-> run_file_mutations
-> manifest / capability / write guard
-> apply writes
-> second preview verifies no remaining planned writes
```

## Current Ownership

| Step | Current owner | English applicability |
| --- | --- | --- |
| User intent recognition | Agent skill | Reusable pattern, but English pack needs its own examples and terminology. |
| `review_rollover` workflow | Japanese pack | The shape is reusable; field names, daily-note text, and vocabulary promotion details must be English-owned. |
| Vault context validation | Core | Not yet English-ready because core context currently accepts only `target_language=ja` and `explanation_language=zh`. |
| Path role loading | Core concept, pack usage | Reusable if an English pack declares English path roles. |
| Card scanning | Language pack | Reusable pattern; English pack decides which roles are managed. |
| Rollover date/stage logic | Currently in Japanese workflow | Conceptually core-worthy, but should not be moved to core until Japanese and English both prove the same contract. |
| `FileMutation` planning | Language pack | Reusable pattern; mutation content must remain pack-specific. |
| `run_file_mutations` and write guard | Core | Reusable as-is for any declared stable capability once context/generalization is fixed. |
| Second preview verification | Agent skill + workflow | Reusable pattern. |

## What Transfers Cleanly to English

The following parts are suitable for English with little conceptual change:

- Preview before write, explicit confirmation, apply, then second preview.
- Capability gating through `enabled_capabilities`.
- Manifest-driven stable/unsupported capability checks.
- Vault-relative path safety through `FileMutation`.
- Path roles as the way to decouple runtime code from concrete folders.
- SRS stages: `day0`, `day1`, `day3`, `day7`, `day14`, `day30`, `day90`, `day180`, `mastered`.
- Delayed-review rule: keep the current stage and reschedule when overdue exceeds the allowed delay.
- `done_today`, `status`, `review_stage`, `next_review`, and `last_reviewed` as shared review-state fields.

These are good candidates for an eventual core contract once the English pack validates the same behavior.

## What Does Not Transfer Directly

The current Japanese implementation cannot be used directly for English for these reasons:

- Core context currently rejects non-Japanese vaults.
- There is no English language pack under `lingotrace/packs/english/`.
- Japanese validators accept Japanese-owned fields such as `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs`.
- Japanese daily checklist text is Chinese-facing and references the current Japanese training loop.
- Focus/base vocabulary promotion is implemented around Japanese card shape and tags.
- Listening and pronunciation concepts are language-specific.
- The current `review_rollover` workflow lives inside the Japanese pack and should not be imported by an English pack.

## English-Specific Design Questions

Before implementing English rollover, the English pack should answer:

- What are the English vocabulary fields?
  Examples may include `headword`, `pronunciation`, `stress_pattern`, `meaning_zh`, `part_of_speech`, `collocations`, `register`, `example_sentence`, and `common_errors`.
- Does English need a focus/base vocabulary lifecycle identical to Japanese?
- What makes an English focus vocabulary card ready to become a base vocabulary card?
- What daily checklist language should be used for Chinese-speaking English learners?
- Which English roles correspond to Japanese pronunciation accent and phoneme roles?
- Should English speaking cards share the same `speaking_cards` capability shape, or require English-specific usage fields?

These should be settled in the English pack, not in core.

## Required Core Work Before English

The chain is architecturally suitable for English, but it is not currently executable for English. Required core/generalization work:

1. Generalize vault context validation.
   Current context validation is hardcoded to Japanese. It needs to accept a target language and language pack declared by the selected manifest, rather than fixed constants.

2. Generalize initialization.
   Current initialization is Japanese-specific. English needs pack-driven initialization for `.lingotrace` config, default paths, templates, and views.

3. Keep capability IDs shared, not implementations shared.
   `review_rollover` can remain a shared capability ID, but Japanese and English should each expose their own pack workflow until the common parts are proven and extracted.

4. Add pack-level conformance tests.
   Tests should verify that an English manifest can declare `review_rollover`, that an English vault context can enable it, and that core write guard accepts English pack mutations.

## Recommended English Pack Call Flow

The English chain should mirror the Japanese chain structurally:

```text
User asks to settle English review
-> English agent skill
-> lingotrace.packs.english.workflows:review_rollover
-> core validates English vault context
-> English workflow reads English path roles
-> English workflow scans English review cards
-> English workflow plans FileMutation objects
-> core run_file_mutations validates manifest/capability/write boundaries
-> core applies writes
-> English workflow preview returns zero planned writes after apply
```

Important boundary: English should reuse the core write path, not the Japanese workflow implementation.

## Minimum Acceptance Tests for English

An English implementation should not be accepted until these tests exist:

- Preview advances one active `done_today: true` English card without writing.
- Apply advances the same card and updates `done_today`, `review_stage`, `next_review`, and `last_reviewed`.
- Overdue card beyond allowed delay is rescheduled without advancing stage.
- `day180` focus vocabulary card becomes `mastered` and creates or updates a promoted base vocabulary card.
- Existing base vocabulary card merge preserves prior sources and user-maintained fields.
- Daily note exists with a checklist anchor: only the checklist tail is rewritten.
- Daily note exists without a checklist anchor: checklist is appended without deleting existing text.
- Daily note missing: rollover still completes and reports no daily-note write.
- Invalid `next_review`, unknown `review_stage`, or missing required fields block apply.
- Second preview after apply returns no review-card planned writes.

## Risks If Reused Prematurely

- Importing Japanese workflow code into English would leak Japanese field assumptions into English data.
- Generalizing core too early could force Japanese and English into a lowest-common-denominator schema.
- Copying Japanese tests with only path/name changes would repeat the previous migration failure: the capability would appear present while important business rules remain uncovered.
- Daily-note content could become awkward or misleading if Japanese learning summaries are translated mechanically.

## Recommendation

The chain is suitable for English as an architectural pattern, not as a direct implementation.

Proceed in this order:

1. Generalize core context and initialization enough to load a non-Japanese pack.
2. Create `lingotrace/packs/english/` with explicit unsupported capabilities where needed.
3. Implement English `review_rollover` as its own workflow facade.
4. Port only the proven common rollover contract: SRS stage state, delayed reschedule, preview/apply/write-guard flow, and second-preview verification.
5. Design English vocabulary, pronunciation, daily-note, and base-promotion semantics inside the English pack.
6. Extract shared SRS helpers into core only after Japanese and English tests prove the same behavior.

This keeps the new chain reusable while preserving the language-pack boundary that the multilingual architecture requires.
