# Phase 0 Language Pack Conformance Checklist

This checklist defines what a language pack must prove before Phase 1 treats it as a target architecture component. It is a review checklist, not a runtime validator.

## Identity And Versions

- [ ] Declares `language_pack_id`.
- [ ] Declares `language_pack_version`.
- [ ] Declares exactly one `target_language`.
- [ ] Declares `transcription_locale` when media or transcription workflows are present.
- [ ] Declares compatible core version range.
- [ ] Declares compatible Vault Schema version range.
- [ ] Does not require target-language guessing from path, tag, folder, or content.

## Capabilities

- [ ] Uses only reviewed capability IDs: `listening_notes`, `source_notes`, `review_materials`, `speaking_cards`, `review_rollover`.
- [ ] Declares each capability as `experimental`, `stable`, or `deprecated`.
- [ ] Declares dependencies between capabilities when one workflow hands off to another.
- [ ] Declares read paths and write paths for each capability.
- [ ] Declares external tool requirements, minimum required interfaces, and failure policy for media, ASR, slicing, dictionary, or pronunciation dependencies.
- [ ] Stops before write when a required external tool, dependency, version, or locale check fails.
- [ ] Declares unsupported capabilities explicitly instead of falling back to Japanese logic.

## Pack-Owned Surface

- [ ] Lists templates owned by the pack.
- [ ] Lists Skill or workflow entry points owned by the pack.
- [ ] Lists validators owned by the pack.
- [ ] Lists dictionaries, pronunciation resources, and other language resources.
- [ ] Lists default path roles and allows explicit Vault path configuration to override those defaults.
- [ ] Lists language-specific fields, item types, tag namespace, and display rules.
- [ ] Declares initialization artifacts and limits them to capabilities actually declared by the pack.

## Core Boundary

- [ ] Uses the core review-card shell for lifecycle fields.
- [ ] Keeps language fields outside the core shell.
- [ ] Preserves unknown frontmatter fields and Markdown body content.
- [ ] Treats missing version, missing capability, or missing language pack as a stop condition.
- [ ] Does not import private learning data into the public repository.
- [ ] Does not persist undeclared cross-Vault path, cache, deduplication, or review state.

## Japanese Pack Phase 1 Minimum

- [ ] Registers Japanese fields such as `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs`.
- [ ] Registers Japanese item types and `jp` tag namespace that remain valid in migrated data.
- [ ] Preserves current five Japanese workflows as migration obligations unless a Phase 1 decision explicitly supersedes a behavior.
- [ ] Covers vocabulary, grammar, pronunciation, error-card, and daily study checklist ownership under `review_materials`.
- [ ] Keeps ListenKit or other media tooling at an external adapter boundary.
- [ ] Keeps old `jp-*` entries only as migration evidence or temporary source readers until cutover.

## Evidence

- [ ] Links each stable Japanese capability to a Phase 0 behavior ID or a Phase 1 replacement decision.
- [ ] Links each stable capability to an executable test or accepted manual review case.
- [ ] Records any experimental capability as unavailable by default.
- [ ] Records any deprecated capability with a removal condition.
