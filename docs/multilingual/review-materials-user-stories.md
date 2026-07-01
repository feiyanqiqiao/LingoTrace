# Multilingual Review Materials User Stories and Acceptance Tests

Status: `Reference Guidance`

Maturity path: `Reference Guidance -> Candidate Contract -> Enforced Contract`

Related guidance index: [Language Pack Capability Guidance](language-pack-capability-guidance.md)

## Purpose

This document defines the user-facing behavior that should survive migration of the review-material extraction and maintenance workflow across language packs. It is based on the old Japanese `jp-review-material-maintainer` skill and the current public `review_materials` capability.

The migration rule is simple: review-material behavior is not considered migrated until it has a user story, acceptance criteria, and regression or manual-review evidence.

## Applicability

All language packs that implement `review_materials` should index, reference, and satisfy this document before the capability is considered complete.

This document is shared guidance for:

- Extracting review-worthy items from source notes, classroom notes, daily notes, pasted material, or user requests.
- Keeping vocabulary, grammar, pronunciation, and error cards in their correct language-pack-owned roots.
- Searching before creating cards.
- Preserving source provenance and manual note content.
- Separating review-card creation from source-note generation, speaking-card creation, listening transcription, and review rollover.
- Routing writes through the core write guard.

Language packs may define their own card types, fields, paths, templates, and display rules. Japanese fields such as `reading`, `accent_display`, `kanji_diff`, and `kanji_diff_pairs` are reference behavior, not generic core fields.

## Ownership Boundary

Core owns:

- Vault context loading.
- Language-pack manifest loading.
- Capability enablement and stability checks.
- Vault-relative write guards.
- `FileMutation` preview/apply execution.
- Atomic file-application semantics and blocked-write reporting.

Language packs own:

- Natural-language agent instructions for extracting review material.
- Path roles for vocabulary, grammar, pronunciation, and error cards.
- Card templates and required fields.
- Duplicate-search and routing policy.
- Language-specific vocabulary, grammar, pronunciation, and error-card rules.
- Decisions about source-note, daily checklist, and review-card boundaries.
- Pack-level regression tests and manual review cases.

## User Stories

### 1. Search Before Creating Review Cards

As a learner, I want the agent to search existing review material before creating a new card, so I do not get duplicate cards for the same learning point.

Acceptance criteria:

- The workflow searches the active review layer before the long-term vocabulary layer.
- A new vocabulary item creates a focus review card only when neither layer has a match.
- If a vocabulary item already exists in the focus review layer, update that card instead of creating a duplicate.
- If a vocabulary item exists only in the base lexicon, restore or create a focus review card for active review instead of stopping at the base card.
- Search should be targeted to configured path roles rather than a broad vault scan when a role-scoped search is enough.

Japanese reference:

- This is the old skill's focus-first search order.
- Focus review means `<focus_vocab_root>`.
- Base lexicon means `<base_vocab_root>`.

Regression coverage:

- `test_lookup_cases_preserve_focus_first_and_routing_decisions`

### 2. Route Different Review Items To The Correct Card Type

As a learner, I want vocabulary, grammar, pronunciation, and mistakes to become the right kind of review card, so each item is reviewed with an appropriate prompt and explanation.

Acceptance criteria:

- Vocabulary items route to the vocabulary review layer.
- Grammar items route to grammar cards.
- Concrete misunderstandings or wrong/correct contrasts route to error cards.
- Pronunciation or accent uncertainty routes to pronunciation practice cards instead of overloading ordinary vocabulary.
- Source-note generation, listening transcription, speaking-card creation, and review rollover remain separate workflows.

Japanese reference:

- `単語` routes to vocabulary.
- `文法` routes to grammar.
- `間違えた問題` may update grammar cards or create/update error cards depending on the learning point.
- Accent contrast cards belong to pronunciation accent roles, not ordinary vocabulary.

Regression coverage:

- `test_grammar_and_error_cards_do_not_route_to_vocab_layer`
- `test_review_materials_item_routes_grammar_error_and_pronunciation_cards`

### 3. Preserve Source Provenance

As a learner, I want each extracted card to remember where the learning point came from, so later review remains traceable to the original context.

Acceptance criteria:

- New or updated cards include a source reference when the source note is known.
- Existing cards append a new source reference when the same item reappears in a new note.
- Source references should use stable Obsidian links or language-pack-approved source identifiers.
- The workflow must not erase existing manually curated source references.

Japanese reference:

- Review cards use `source_notes`.
- Card bodies should keep a `## 来源` section when that is part of the local template.

Regression coverage:

- `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body`
- `test_review_materials_apply_creates_target_card`
- `test_review_materials_item_updates_existing_focus_without_duplicate_or_body_loss`

### 4. Initialize New Active Review Cards Predictably

As a learner, I want newly extracted review cards to enter the active review loop with predictable scheduling fields, so they appear in the daily review queue.

Acceptance criteria:

- New active cards are initialized with `status: active`.
- New active cards start at `review_stage: day0`.
- `done_today` starts as false unless the user explicitly asks for a different state.
- `next_review` is initialized to the creation or extraction date according to the language pack's review policy.
- Required review fields are present before writing.

Japanese reference:

- Focus vocabulary cards use `track: class_review`, `item_type: vocab`, `status`, `priority`, `done_today`, `review_stage`, `next_review`, and `last_reviewed`.
- Grammar and error cards use the same active-review scheduling family.

Regression coverage:

- `test_review_materials_apply_creates_target_card`
- `test_review_materials_item_creates_initialized_focus_vocab_card`
- `test_review_materials_item_routes_grammar_error_and_pronunciation_cards`
- `test_validator_stubs_accept_synthetic_public_fixtures`

### 5. Reactivate Known Material When It Reappears

As a learner, I want a mastered or base-lexicon item that reappears as a weakness to return to active review, so old material can be relearned when needed.

Acceptance criteria:

- If a base-lexicon item appears in a new source context, create or restore an active focus card.
- If a mastered focus card reappears as a weakness, switch it back to active review.
- Reactivated cards reset to `review_stage: day0` and `next_review` at the current extraction date.
- The base lexicon keeps the long-term record and should not be deleted.

Japanese reference:

- Base-only match action is `restore_focus_card`.
- Mastered reappearance resets the focus card to `day0`.

Regression coverage:

- `test_lookup_cases_preserve_focus_first_and_routing_decisions`
- `test_review_materials_item_reactivates_mastered_focus_card`

### 6. Keep Base Lexicon Sink Out Of Daily Extraction

As a learner, I want ordinary classroom extraction to create active focus cards first, so base vocabulary promotion happens only after review mastery, not during material extraction.

Acceptance criteria:

- Ordinary new vocabulary extraction creates or updates the focus review layer first.
- A base-only match restores or creates an active focus card instead of treating the item as already handled.
- Daily extraction must not directly sink new vocabulary into base vocabulary.
- Focus-to-base promotion is owned by `review_rollover` when a focus vocabulary card completes the full memory curve.
- Extraction must not erase existing base-card manual content.

Japanese reference:

- Completed focus vocabulary can sink into the base lexicon with `status: promoted` during `review_rollover`.
- `review_materials` only uses base vocabulary for duplicate detection and focus restoration.

Regression coverage:

- `test_review_materials_item_restores_base_only_vocab_to_focus_without_touching_base`
- `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body`

### 7. Preserve Language-Specific Review Cues

As a learner, I want review cards to keep the language-specific cues I need during review, so the card is useful rather than just a dictionary entry.

Acceptance criteria:

- Vocabulary cards preserve the language pack's pronunciation, reading, meaning, collocation, and confusion fields when applicable.
- Grammar cards preserve meaning, formation, usage, examples, and contrast metadata when applicable.
- Error cards preserve a clear wrong/correct pair and the reason for the mistake.
- Uncertain core fields block creation or are marked for confirmation according to the pack's policy.
- The workflow should not invent plausible-looking collocations, accent data, or comparison links.

Japanese reference:

- `reading` stays clean kana.
- `accent_display` holds kana plus pitch accent and may be blank when unknown.
- `kanji-difference` review uses `kanji_diff` and `kanji_diff_pairs`.
- Useful comparisons use `confusable_with` or `contrast_with`, but dangling links should be avoided.

Regression coverage:

- `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body`
- `test_review_materials_item_updates_existing_focus_without_duplicate_or_body_loss`
- `test_review_materials_item_preserves_vocab_review_cues`

### 8. Handle Image-Backed Vocabulary Conservatively

As a learner, I want vocabulary visible only in a source image to be extracted only when it is readable, so the system does not create wrong cards from uncertain OCR.

Acceptance criteria:

- Image-backed vocabulary may be extracted only after inspecting the local attachment.
- Clearly readable items can enter the normal duplicate-search flow.
- Items already present as text in the same source note should not be duplicated from the image.
- Unclear, blurred, handwritten, or uncertain OCR should be reported for user confirmation instead of creating cards.

Japanese reference:

- Old `jp-review-material-maintainer` treated images embedded under `## 単語` as possible vocabulary sources.

Regression coverage:

- `test_review_materials_item_blocks_uncertain_image_backed_extraction`
- `test_review_materials_item_accepts_clearly_readable_image_backed_extraction`

### 9. Keep Daily Checklist Separate From Review Cards

As a learner, I want daily checklist updates to remain a lightweight execution log, so they do not become a second review-card system.

Acceptance criteria:

- Daily checklist updates use the user's dated note only when explicitly requested.
- Checklist text should summarize completed work and blockers, not duplicate full card content.
- Checklist updates must not change SRS state fields such as `done_today`, `review_stage`, or `next_review`.
- Review-card extraction can report created/updated cards without writing the daily checklist by default.

Japanese reference:

- The old skill used `## 每日学习清单`, `## 今日完成`, `## 今日卡点`, and `## 简短复盘` for lightweight daily summaries.

Regression coverage:

- `test_review_materials_item_does_not_touch_daily_checklist`

### 10. Confirm Before Risky Merge, Move, Or Overwrite

As a learner, I want the agent to ask before merging, moving, overwriting, or making uncertain review-state changes, so manually curated study material is not lost.

Acceptance criteria:

- Low-risk new-card creation can proceed through the workflow after duplicate checks.
- Merges, moves, overwrites, broad rewrites, or uncertain card classification require user confirmation before writing.
- Existing manual body sections must be preserved unless the user explicitly asks to replace them.
- If the card type, headword, meaning, formation, or correct answer is uncertain, stop and ask rather than writing a confident-looking card.

Regression coverage:

- `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body`
- `test_review_materials_item_blocks_duplicate_existing_matches`
- `test_review_materials_item_blocks_target_path_collision`
- `test_review_materials_item_blocks_missing_core_title`
- Agent-skill contract checks in `test_phase25_switch_completion`
- `test_review_material_agent_skill_requires_confirmation_for_risky_writes`

### 11. Route Writes Through Core Guardrails

As a maintainer, I want review-material writes to use the core mutation path, so language-pack workflows cannot write outside declared scope.

Acceptance criteria:

- Review-material workflows create `FileMutation` objects instead of writing Vault files directly.
- `run_file_mutations` checks the selected language-pack manifest and capability.
- The target vault must enable `review_materials`.
- Paths must be vault-relative and inside guarded roots.
- Preview mode returns planned writes without changing files.

Regression coverage:

- `test_review_materials_previews_target_vault_without_writes`
- `test_review_materials_apply_creates_target_card`
- `tests/lingotrace/core/test_mutations.py`
- `tests/lingotrace/core/test_capabilities.py`

## Migration Test Matrix

| Behavior | Reference Japanese coverage | Coverage status | Required for every language pack |
| --- | --- | --- | --- |
| Focus-first duplicate search | `test_lookup_cases_preserve_focus_first_and_routing_decisions` | Covered | Yes |
| Base-only match restores focus card | `test_lookup_cases_preserve_focus_first_and_routing_decisions` | Covered | Yes |
| Mastered reappearance resets to day0 | `test_lookup_cases_preserve_focus_first_and_routing_decisions` | Covered | Yes |
| Grammar and error routing | `test_grammar_and_error_cards_do_not_route_to_vocab_layer` | Covered | Yes |
| Pronunciation routing | `test_review_materials_item_routes_grammar_error_and_pronunciation_cards` | Covered for structured items | Yes, if the pack supports pronunciation cards |
| Source provenance | `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body` | Covered | Yes |
| New active card initialization | `test_review_materials_item_creates_initialized_focus_vocab_card` | Covered for structured items | Yes |
| Base-only restore does not rewrite base card | `test_review_materials_item_restores_base_only_vocab_to_focus_without_touching_base` | Covered | Yes |
| Focus-to-base sink on mastery | `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body` | Covered by `review_rollover` | Yes |
| Japanese kanji-difference metadata | `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body` | Covered for Japanese | No, language-specific |
| Image-backed vocabulary extraction | `test_review_materials_item_blocks_uncertain_image_backed_extraction`; `test_review_materials_item_accepts_clearly_readable_image_backed_extraction` | Covered for structured items | If supported |
| Daily checklist separation | `test_review_materials_item_does_not_touch_daily_checklist` | Covered for default extraction | If supported |
| Risky merge or overwrite confirmation | `test_review_materials_item_blocks_duplicate_existing_matches`; `test_review_materials_item_blocks_target_path_collision`; `test_review_material_agent_skill_requires_confirmation_for_risky_writes` | Covered for structured items and agent contract | Yes |
| Core write guard | Core mutation and capability tests | Covered | Yes |

## Language-Pack Implementation Checklist

Before adding `review_materials` to a new language pack:

- Declare the capability in the language-pack manifest.
- Define path roles for every card family the pack supports.
- Define language-owned fields in `fields.json`; do not copy Japanese field names mechanically.
- Define card templates for vocabulary, grammar, pronunciation, and error cards as applicable.
- Add duplicate-search rules and target-card routing rules.
- Decide which source-note and daily-checklist behaviors are supported.
- Add pack-level tests mapped to every required row in the migration matrix.
- Document unsupported card families with user-facing failure reasons.

## Maintenance Rule

When changing `review_materials`, update this document and add or adjust a regression test in the same change. If a behavior is language-specific, place the test in that language pack's workflow or fixture suite. If a behavior becomes shared by multiple language packs, propose promotion to `Candidate Contract` only after the shared behavior has stable evidence.
