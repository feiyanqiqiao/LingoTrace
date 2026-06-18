# Phase 0 Japanese Migration Contract

The migration target is a new Japanese Vault that runs on the shared core and the Japanese language pack. The migration source is the current Japanese Vault and its verified learning behavior. The source framework is evidence and a data source; it is not preserved as a long-term runtime.

This contract defines migration obligations for Phase 1 design and Phase 2 execution. It does not perform the migration.

## Required Manifest Terms

Migration tooling must receive both `source_vault` and `target_vault` explicitly. The tool must not discover the target language from directory names, tags, note content, or historical layout.

The migration manifest must include:

- `source_vault`
- `target_vault`
- `source_manifest`
- `target_manifest`
- `preserve_data`
- `recreate_from_pack`
- `transform_with_map`
- `remove_after_cutover`
- `excluded_with_user_approval`
- `conflicts`
- `verification_report`

## Preservation Rule

The default rule is to preserve private learning data. In review language: preserve private learning data unless a contract-backed exception exists.

Preserve by default:

- personal learning notes and classroom notes
- vocabulary, grammar, pronunciation, error, listening, and speaking cards
- frontmatter, Markdown body, Wikilinks, embeds, backlinks, and source relationships
- audio, video, image, PDF, transcript, structured artifact, slice manifest, and referenced slice files
- SRS state fields such as `done_today`, `review_stage`, `next_review`, `last_reviewed`, counters, and status
- manually curated examples, explanations, accent confirmations, sentence selections, and reflections
- Japanese fields and `jp` tag namespace that are owned by the Japanese language pack

Byte preservation is preferred when the target relative path is valid. Field-aware comparison is required when the migration tool must inspect frontmatter. Every preserved file or asset must have a `content_hash` comparison strategy or a documented field-aware comparison strategy in the source and target manifests.

## Recreate From Pack

System assets are recreated from the target release:

- Vault context and language-pack pin
- path-role configuration
- templates and default Bases views
- target Vault guidance
- Japanese language-pack Skills, validators, resources, and default views
- user-facing workflow documentation for the new framework

The rule is: do not copy old framework wholesale. Old system directories may be read to build evidence, but the target system layer comes from the new core and the Japanese pack.

## Transform With Map

No transform is allowed for cosmetic normalization. A transform requires a recorded reason and a dry-run preview.

Allowed reasons:

- source path collides with a generated target system asset
- relative path escapes the target Vault
- a Wikilink or embed cannot resolve after a preserved relative copy
- a source field conflicts with a core-reserved field
- target configuration requires a structural change
- the user explicitly approves a content or path conversion

Every transform must record source path, target path, reason, before value, after value, preview result, acceptance result, and conflict status. Transform execution must be repeatable.

Japanese fields such as `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs` are not transform candidates merely because they are Japanese-specific. They remain Japanese language-pack fields.

## Conflict Handling

Conflicts stop the affected file or asset. The migration tool may continue read-only analysis for unrelated files, but it must not write a guessed result.

Conflict categories include:

- target path already occupied by a different preserved asset
- target path already occupied by a generated system asset
- unresolved link, missing attachment, or missing transcript artifact
- ambiguous field ownership
- non-repeatable transform result

Each conflict must appear in `conflicts` and in the final `verification_report`.

## Manifest And Verification Structure

The `source_manifest` records the frozen source inventory generated during the Phase 2 write freeze. The `target_manifest` records the target inventory after migration or recreation. Both manifests must use repository-relative or Vault-relative paths, never personal absolute paths.

Each manifest entry records:

- relative path or generated asset ID
- classification: preserved, recreated from pack, transformed with map, removed after cutover, or excluded with user approval
- comparison strategy, such as `content_hash`, `frontmatter_and_body`, `links_and_hashes`, or `field_aware`
- source hash and target hash when bytes should match
- exclusion reason and approver when the entry is excluded with user approval

The `verification_report` summarizes counts, failed comparisons, unresolved conflicts, excluded entries, and the exact acceptance result. A report with unresolved conflicts, unclassified entries, or missing user approvals blocks cutover.

## Final Source Manifest

Phase 2 requires a short write freeze before the final source manifest is generated. The manifest must classify every source entry as preserved, recreated from pack, transformed with map, removed after cutover, or explicitly excluded with user approval.

Unclassified entries block cutover.

## Acceptance

The target new Japanese Vault is accepted only after:

- all five Japanese workflows pass the accepted baseline or explicit Phase 1 replacement checks
- private learning data preservation reports are complete
- no unknown target-language fallback exists
- old runtime entry points are no longer required for daily use
- the user confirms the old Vault can move to read-only observation
