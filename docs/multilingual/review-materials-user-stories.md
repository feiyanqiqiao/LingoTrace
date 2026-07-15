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

## Language Applicability Matrix

Labels:

- `Required`: every language pack implementing this capability should satisfy the behavior.
- `Optional`: the behavior is useful but only required when the pack declares the supporting feature.
- `Language-Specific`: the behavior depends on language-owned fields, templates, or pedagogy.
- `Covered`: current implementation or regression evidence exists.
- `Partial`: current support exists, but not all acceptance criteria are proven.
- `Planned`: expected for future implementation, but not currently covered.
- `Unsupported`: the pack does not currently support this behavior.
- `N/A`: not applicable to the pack.

| User story                                             | Shared              | Japanese  | English   | Notes                                                                                         |
| ------------------------------------------------------ | ------------------- | --------- | --------- | --------------------------------------------------------------------------------------------- |
| `US-1` Search before creating review cards             | `Required`          | `Covered` | `Partial` | English has structured creation paths; full focus/base lookup parity needs explicit coverage. |
| `US-2` Route items to the correct card type            | `Required`          | `Covered` | `Partial` | Card families differ by language pack; pronunciation routing is optional when unsupported.    |
| `US-3` Preserve source provenance                      | `Required`          | `Covered` | `Partial` | Provenance fields may use pack-owned names.                                                   |
| `US-4` Initialize new active review cards              | `Required`          | `Covered` | `Covered` | Shared SRS initialization fields are expected for active review cards.                        |
| `US-5` Reactivate known material                       | `Required`          | `Covered` | `Planned` | English should add explicit active/mastered/base reactivation tests before claiming parity.          |
| `US-6` Keep base lexicon sink out of extraction        | `Required`          | `Covered` | `Partial` | The shared boundary is required; pack-specific base restore details need coverage.            |
| `US-7` Preserve language-specific review cues          | `Language-Specific` | `Covered` | `Partial` | Japanese accent/kanji fields are not shared; English needs its own cue policy.                |
| `US-8` Image-backed vocabulary extraction              | `Optional`          | `Covered` | `Partial` | English still uses a legacy readability flag and does not yet satisfy the structured-evidence contract. |
| `US-9` Daily checklist separation                      | `Optional`          | `Covered` | `N/A`     | Required only for packs with daily checklist integration.                                     |
| `US-10` Confirm before risky merge, move, or overwrite | `Required`          | `Covered` | `Partial` | Agent confirmation policy is shared; each pack needs local examples.                          |
| `US-11` Core write guardrails                          | `Required`          | `Covered` | `Covered` | Core mutation and capability checks apply to all packs.                                       |
| `US-12` Render stable, reviewable card bodies          | `Required`          | `Covered` | `Partial` | Japanese has deterministic vocabulary, grammar, and error renderers; English needs its own templates. |
| `US-13` Prevent dangling or incorrect internal links   | `Required`          | `Covered` | `Planned` | Japanese resolves provenance and relations inside declared roles before writing.              |

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

## Capability Input Modes

`review_materials` exposes three mutually exclusive input modes. Apply calls must provide exactly one of them; providing more than one is an error.

- `item`: structured semantic fields for deterministic lookup, routing, and new-card rendering. When the target already exists, an apply requires `existing_update_confirmed=true`; the confirmed update may change only managed provenance and review-lifecycle state, and must not replace manually curated semantic frontmatter or body sections.
- `card`: a complete caller-supplied card path, frontmatter field set, and readable body. A new card may be created after validation; replacing an existing card requires `existing_update_confirmed=true` and may replace that one card's body only within its declared review role.
- `daily_checklist`: a structured lightweight update to one existing dated daily note. Apply always requires `existing_update_confirmed=true`; it must not create a daily note or change review-card SRS state.

With no payload, preview is a read-only discovery operation. It may recognize readable legacy cards that do not satisfy the latest new-card schema, but it must not migrate, normalize, or write them. Apply without a payload is an error.

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
- `test_review_materials_item_stops_after_focus_match_even_when_base_has_duplicate_history`

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
- `test_review_materials_item_resets_reappearing_active_focus_to_day0_without_body_loss`

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
- If an active focus card reappears in a new source note, treat the reappearance as a fresh learning signal instead of only appending provenance.
- If an active focus card is reported again from the same canonical source note, preserve its current schedule instead of resetting it repeatedly.
- If a mastered focus card reappears as a weakness, switch it back to active review.
- Reappearing active cards and reactivated mastered cards reset to `review_stage: day0` and `next_review` at the current extraction date.
- A repeated error card or an explicitly reported grammar or vocabulary weakness is also a fresh learning signal: increment the managed counters, raise priority, and reset it to day0 after confirmation.
- Resetting to day0 also clears `last_reviewed` or otherwise makes the card visible in the same-day review queue according to the pack's dashboard policy.
- The base lexicon keeps the long-term record and should not be deleted.

Japanese reference:

- Base-only match action is `restore_focus_card`.
- Active focus reappearance should update the existing focus card, append the new source note, reset scheduling to `day0`, and preserve manual body content.
- The same-source active focus path updates only when another managed change is required; it does not reset the schedule merely because the same source was submitted again.
- Mastered reappearance resets the focus card to `day0`.

Regression coverage:

- `test_lookup_cases_preserve_focus_first_and_routing_decisions`
- `test_review_materials_item_resets_reappearing_active_focus_to_day0_without_body_loss`
- `test_review_materials_item_does_not_reset_active_focus_for_same_source_note`
- `test_review_materials_item_resets_reappearing_errors_and_grammar_weaknesses`
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
- `test_review_materials_item_resets_reappearing_active_focus_to_day0_without_body_loss`
- `test_review_materials_item_preserves_vocab_review_cues`

### 8. Handle Image-Backed Vocabulary Conservatively

As a learner, I want vocabulary visible only in a source image to be extracted only when it is readable, so the system does not create wrong cards from uncertain OCR.

Acceptance criteria:

- Image-backed vocabulary may be extracted only after inspecting the local attachment.
- Structured image input includes `image_evidence` with an exact Vault-relative attachment path, `inspection_method`, `readability`, the observed text, and the normalized headword; when normalization changes the visible form, `observed_form` records the exact token seen in the image.
- `review_materials` verifies that the attachment exists in the target Vault and is embedded inside the resolved source note's `## 単語` section; a caller-supplied `image_readable: true` flag alone is not evidence.
- Attachment evidence and embeds must use safe Vault-relative paths to supported local image files. A pathless embed is accepted only when its filename resolves to exactly one Vault attachment; ambiguous, traversing, malformed, or outside-Vault targets block extraction instead of being guessed.
- Clearly readable items can enter the normal duplicate-search flow.
- Items already present as text in the same source note should not be duplicated from the image.
- Unclear, blurred, handwritten, or uncertain OCR should be reported for user confirmation instead of creating cards.

Japanese reference:

- Old `jp-review-material-maintainer` treated images embedded under `## 単語` as possible vocabulary sources.

Regression coverage:

- `test_review_materials_item_blocks_uncertain_image_backed_extraction`
- `test_review_materials_item_accepts_clearly_readable_image_backed_extraction`
- `test_review_materials_item_requires_real_image_inspection_evidence`
- `test_review_materials_item_does_not_repeat_vocab_already_written_in_source_text`

### 9. Keep Daily Checklist Separate From Review Cards

As a learner, I want daily checklist updates to remain a lightweight execution log, so they do not become a second review-card system.

Acceptance criteria:

- Daily checklist updates use an existing note inside the configured daily-note role only when explicitly requested; the workflow never creates a daily note implicitly.
- The target filename must be a supported date form such as `YYYY-MM-DD.md` or `YYYY.M.D.md`.
- Explicit updates use the separate `daily_checklist` input rather than being inferred from `item` or `card` extraction.
- The structured payload is limited to `completed`, `blockers`, and `reflection`; entries are short, single-line plain text that summarize execution rather than duplicate full card content.
- The workflow owns only the content between its managed checklist markers and replaces only that block on later confirmed updates.
- Checklist updates must not change SRS state fields such as `done_today`, `review_stage`, or `next_review`.
- Review-card extraction can report created/updated cards without writing the daily checklist by default.
- Existing unmarked manual checklist sections are preserved and block managed replacement; migration remains a separate explicit user action.
- Every apply requires `existing_update_confirmed=true` because the target is an existing user-authored note.

Japanese reference:

- The old skill used `## 每日学习清单`, `## 今日完成`, `## 今日卡点`, and `## 简短复盘` for lightweight daily summaries.

Regression coverage:

- `test_review_materials_item_does_not_touch_daily_checklist`
- `test_review_materials_daily_checklist_requires_explicit_confirmed_structured_update`
- `test_review_materials_daily_checklist_replaces_only_managed_block_and_rejects_unsafe_payloads`

### 10. Confirm Before Risky Merge, Move, Or Overwrite

As a learner, I want the agent to ask before merging, moving, overwriting, or making uncertain review-state changes, so manually curated study material is not lost.

Acceptance criteria:

- Low-risk new-card creation can proceed through the workflow after duplicate checks.
- Every apply that targets an existing card through `item` or `card` requires `existing_update_confirmed=true`, even when the proposed mutation is narrow.
- A confirmed `item` update may change only managed provenance, counters, priority, and review-lifecycle fields; caller-supplied semantic fields must not overwrite existing manual semantic frontmatter or body sections.
- A confirmed full `card` payload may replace the target card body and fields, but only for that single validated path inside the declared review roles.
- A `daily_checklist` apply also requires confirmation and follows the separate managed-block contract in US-9.
- Merges, moves, broad rewrites, or uncertain card classification require user confirmation before writing.
- If the card type, headword, meaning, formation, or correct answer is uncertain, stop and ask rather than writing a confident-looking card.

Regression coverage:

- `test_existing_cards_require_confirmation_and_keep_manual_semantic_content`
- `test_confirmed_full_card_payload_can_replace_one_existing_body_but_not_escape_review_roles`
- `test_review_materials_daily_checklist_requires_explicit_confirmed_structured_update`
- `test_review_materials_item_blocks_duplicate_existing_matches`
- `test_review_materials_item_blocks_target_path_collision`
- `test_review_materials_item_blocks_missing_core_title`
- `test_review_material_agent_skill_requires_confirmation_for_risky_writes`

### 11. Route Writes Through Core Guardrails

As a maintainer, I want review-material writes to use the core mutation path, so language-pack workflows cannot write outside declared scope.

Acceptance criteria:

- Review-material workflows create `FileMutation` objects instead of writing Vault files directly.
- `run_file_mutations` checks the selected language-pack manifest and capability.
- The target vault must enable `review_materials`.
- Paths must be vault-relative and inside guarded roots.
- Preview mode returns planned writes without changing files.
- `daily_checklist` changes also use `FileMutation` and are restricted to the configured daily-note role.
- No-input legacy discovery is preview-only; apply without one of the three payloads is rejected.

Regression coverage:

- `test_review_materials_previews_target_vault_without_writes`
- `test_review_materials_apply_creates_target_card`
- `tests/lingotrace/core/test_mutations.py`
- `tests/lingotrace/core/test_capabilities.py`

### 12. Render Stable, Reviewable Card Bodies

As a learner, I want structured review fields to produce a consistent card I can actually study from, so new cards do not look like metadata-only stubs.

Acceptance criteria:

- Vocabulary, grammar, and error items use language-pack-owned deterministic renderers.
- Semantic fields appear in the readable body instead of only in frontmatter.
- Optional sections are omitted when no reliable content exists; empty headings are not emitted.
- New cards include complete active-review metadata and typed list fields.
- Existing cards are not reformatted by structured-item updates; full reformatting requires explicit confirmation.
- Confirmed `item` updates preserve the existing readable body, while confirmed complete `card` payloads are the explicit replacement path.
- No-input preview can surface readable legacy cards without requiring a schema migration.

Japanese reference:

- Vocabulary follows the `溢れる` review shape.
- Grammar follows the complete-but-optional `〜ようだ` structure.
- Error cards follow the wrong/correct/reason/avoidance structure and use Obsidian highlights.

Regression coverage:

- `test_vocab_grammar_and_error_bodies_match_golden_fixtures`
- `test_optional_sections_are_omitted_when_no_reliable_content_exists`
- `test_empty_grammar_usage_branches_fall_back_without_empty_headings`
- `test_existing_cards_require_confirmation_and_keep_manual_semantic_content`
- `test_confirmed_full_card_payload_can_replace_one_existing_body_but_not_escape_review_roles`
- `test_yaml_round_trip_preserves_special_text_and_typed_lists`
- `test_yaml_round_trip_preserves_numeric_and_implicit_scalar_text`
- `test_review_materials_preview_keeps_legacy_cards_visible_without_migration`

### 13. Prevent Dangling Or Incorrect Internal Links

As a learner, I want every generated internal link to resolve to the intended note, so review cards do not send me to a missing or similarly named card.

Acceptance criteria:

- Source input accepts a Vault-relative path or wikilink and resolves only inside declared source roles.
- Missing, ambiguous, malformed, out-of-role, or self-referential source links block writing.
- Optional review-card relations resolve only inside type-appropriate review roles.
- Unique targets render canonical Vault-relative extensionless links with friendly labels.
- Missing or ambiguous optional relations remain plain text, produce warnings, and are not written as wikilinks.
- Generated filenames reject characters that change Obsidian link semantics.
- Canonical source identity uses the complete Vault-relative path; same-name notes in different directories remain distinct.
- Pathless legacy links are matched only when unique and never used to guess across ambiguous same-name notes.
- Long generated filenames remain filesystem-safe without truncating semantic display text, and full-card paths reject traversal or oversized components.
- Full-card payloads keep unresolved relations as plain text and require a readable non-empty body.

Regression coverage:

- `test_source_links_must_resolve_uniquely_inside_source_roles`
- `test_missing_or_ambiguous_optional_relations_remain_plain_text_and_are_reported`
- `test_source_self_link_is_blocked_when_roles_overlap`
- `test_reserved_filename_characters_and_non_unique_error_focus_are_blocked`
- `test_review_materials_item_keeps_distinct_same_basename_source_paths`
- `test_review_materials_item_does_not_guess_ambiguous_legacy_source_links`
- `test_long_error_sentence_uses_bounded_filename_without_losing_display_text`
- `test_full_card_payload_rejects_traversal_empty_body_and_oversized_path`
- `test_full_card_payload_keeps_unresolved_relations_as_plain_text`
- `test_vocab_grammar_and_error_bodies_match_golden_fixtures`

## Migration Test Matrix

| Behavior | Reference Japanese coverage | Coverage status | Required for every language pack |
| --- | --- | --- | --- |
| Focus-first duplicate search | `test_review_materials_item_stops_after_focus_match_even_when_base_has_duplicate_history` | Covered by the real workflow | Yes |
| Base-only match restores focus card | `test_review_materials_item_restores_base_only_vocab_to_focus_without_touching_base` | Covered by the real workflow | Yes |
| Mastered reappearance resets to day0 | `test_review_materials_item_reactivates_mastered_focus_card` | Covered by the real workflow | Yes |
| Active focus card reappears in a new source note and resets to day0 | `test_review_materials_item_resets_reappearing_active_focus_to_day0_without_body_loss` | Covered | Yes |
| Same-source active focus submission preserves its schedule | `test_review_materials_item_does_not_reset_active_focus_for_same_source_note` | Covered for Japanese | Yes |
| Reappearing error and explicit grammar weakness reset to day0 | `test_review_materials_item_resets_reappearing_errors_and_grammar_weaknesses` | Covered for Japanese | Yes |
| Grammar and error routing | `test_grammar_and_error_cards_do_not_route_to_vocab_layer` | Covered | Yes |
| Pronunciation routing | `test_review_materials_item_routes_grammar_error_and_pronunciation_cards` | Covered for structured items | Yes, if the pack supports pronunciation cards |
| Source provenance | `test_review_materials_apply_creates_target_card`; `test_review_materials_item_keeps_distinct_same_basename_source_paths`; `test_review_materials_item_does_not_guess_ambiguous_legacy_source_links` | Covered by the real workflow | Yes |
| New active card initialization | `test_review_materials_item_creates_initialized_focus_vocab_card` | Covered for structured items | Yes |
| Base-only restore does not rewrite base card | `test_review_materials_item_restores_base_only_vocab_to_focus_without_touching_base` | Covered | Yes |
| Focus-to-base sink on mastery | `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body` | Covered by `review_rollover` | Yes |
| Japanese kanji-difference metadata | `test_vocab_sink_preserves_japanese_fields_srs_state_and_manual_body` | Covered for Japanese | No, language-specific |
| Image-backed vocabulary extraction | `test_review_materials_item_requires_real_image_inspection_evidence`; `test_review_materials_item_does_not_repeat_vocab_already_written_in_source_text` | Covered for structured items | If supported |
| Daily checklist separation | `test_review_materials_daily_checklist_requires_explicit_confirmed_structured_update`; `test_review_materials_daily_checklist_replaces_only_managed_block_and_rejects_unsafe_payloads` | Covered for structured updates | If supported |
| Existing-card confirmation and content boundaries | `test_existing_cards_require_confirmation_and_keep_manual_semantic_content`; `test_confirmed_full_card_payload_can_replace_one_existing_body_but_not_escape_review_roles` | Covered for Japanese | Yes |
| Core write guard | Core mutation and capability tests | Covered | Yes |
| Stable review-facing card bodies | Golden vocabulary, grammar, and error fixtures | Covered for Japanese | Yes |
| Required provenance link resolution | Missing, ambiguous, malformed, out-of-role, and self-link tests | Covered for Japanese | Yes |
| Optional relation fallback | Plain-text fallback, warning, and artifact tests | Covered for Japanese | Yes |
| Legacy-card discovery without migration | `test_review_materials_preview_keeps_legacy_cards_visible_without_migration` | Covered for Japanese | Yes during schema transitions |
| Canonical same-name source identity | Same-basename and ambiguous-legacy source tests | Covered for Japanese | Yes |

## Language-Pack Implementation Checklist

Before adding `review_materials` to a new language pack:

- Declare the capability in the language-pack manifest.
- Define path roles for every card family the pack supports.
- Define language-owned fields in `fields.json`; do not copy Japanese field names mechanically.
- Define card templates for vocabulary, grammar, pronunciation, and error cards as applicable.
- Define deterministic body renderers and optional-section behavior for structured items.
- Define mutually exclusive `item`, complete `card`, and optional `daily_checklist` input modes, including existing-target confirmation and overwrite boundaries.
- Define role-scoped source and relation link resolution, including ambiguity and fallback policy.
- If image-backed extraction is supported, define structured inspection evidence plus safe attachment and embed resolution; do not treat a readability boolean as sufficient evidence.
- Add duplicate-search rules and target-card routing rules.
- Decide whether daily-checklist integration is supported; if so, define an existing dated-note role, managed markers, safe plain-text fields, and SRS isolation.
- Define no-input preview behavior for readable legacy cards and keep it migration-free and read-only.
- Add pack-level tests mapped to every required row in the migration matrix.
- Document unsupported card families with user-facing failure reasons.

## Maintenance Rule

When changing `review_materials`, update this document and add or adjust a regression test in the same change. If a behavior is language-specific, place the test in that language pack's workflow or fixture suite. If a behavior becomes shared by multiple language packs, propose promotion to `Candidate Contract` only after the shared behavior has stable evidence.
