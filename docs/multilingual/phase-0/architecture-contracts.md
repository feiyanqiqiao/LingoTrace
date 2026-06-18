# Phase 0 Architecture Contracts

This document freezes the Phase 0 multilingual architecture contracts for review. It defines the public boundary that Phase 1 must design against. It does not implement multilingual runtime loading, new Vault initialization, language-pack execution, English functionality, or real migration.

Related Phase 0 sources:

- `docs/lingotrace_multilingual_architecture_plan.md`
- `docs/multilingual/phase-0/current-state-baseline.md`
- `docs/multilingual/phase-0/workflow-evidence-index.md`
- `docs/multilingual/phase-0/migration-scope-and-asset-inventory.md`
- `tools/architecture-baseline/README.md`

## Current, Target, And Route

Current implementation means the verified Japanese workflow described by the current-state baseline and the five existing `jp-*` Skills. It is migration evidence, not the final public interface.

Target architecture means one shared LingoTrace core plus one selected language pack per private Vault. The first target language pack is Japanese. English and later languages must enter only through the same contract shape after their own design.

Phase route means the staged work used to reach the target architecture. Temporary migration tools may read the old Japanese framework, but they must have an exit path and must not become long-term runtime compatibility.

## Vault Context Contract

Every target Vault must declare its language context explicitly before any write-capable workflow runs.

Required Vault context fields:

- `vault_schema_version`
- `target_language`
- `explanation_language`
- `language_pack`
- `language_pack_version`
- `enabled_capabilities`

Rules:

- `target_language` identifies the single target language of the Vault, such as `ja`.
- `explanation_language` identifies the learner-facing explanation language, such as `zh`.
- `language_pack` and `language_pack_version` bind the Vault to one declared pack.
- `enabled_capabilities` is the only source of enabled workflow surface.
- Do not infer target_language from path, tag, folder, or content.
- A missing Vault context is a stop condition for write-capable workflows.
- A version mismatch or missing capability is a stop condition for write-capable workflows.

## Capability IDs

The first contract set uses these fixed capability IDs:

| Capability ID | Meaning | Current Japanese source |
|---|---|---|
| `listening_notes` | fixed listening-practice notes, extensive/intensive modes, provenance, and real slice references | `jp-listening-script-generator` |
| `source_notes` | flexible source notes with mandatory provenance and transcript appendix when available | `jp-source-note-generator` |
| `review_materials` | vocabulary, grammar, pronunciation, error review material, and daily study checklist maintenance | `jp-review-material-maintainer` |
| `speaking_cards` | short daily-life speaking cards and conservative promotion rules | `jp-survival-speaking-card-generator` |
| `review_rollover` | deterministic end-of-day SRS rollover and focus-to-base sink behavior | `jp-next-day-review-updater` |

New capability IDs require a contract update and review before they appear in a language pack.

## Maturity Values

Every language-pack capability declares one maturity value:

- `experimental`: usable for limited review, not part of the stable migration guarantee.
- `stable`: covered by the language-pack checklist and accepted test or manual evidence.
- `deprecated`: still readable during a planned exit window, not a target for new work.

Core must not silently enable an `experimental` or `deprecated` capability when the Vault context did not opt in.

## Language Pack Manifest Contract

A language pack manifest must declare:

- stable pack identity: `language_pack_id`, `language_pack_version`
- target language: `target_language`
- transcription locale when media workflows need it: `transcription_locale`
- compatible version ranges: `compatible_core`, `compatible_vault_schema`
- implemented capabilities, dependencies, maturity, and read/write scope
- external tools, minimum required interfaces, failure policy, and adapter boundaries, such as ASR or deterministic audio slicing
- templates, Skills, validators, resources, and default views owned by the pack
- language-specific fields, item types, tag namespace, and default path roles

The manifest is descriptive in Phase 0. Phase 1 must design how it is loaded and validated before any runtime depends on it.

## Core Review Card Shell

The shared core owns only cross-language lifecycle fields. The first fixed core review-card shell is:

- `track`
- `item_type`
- `status`
- `priority`
- `done_today`
- `review_stage`
- `next_review`
- `last_reviewed`
- `first_seen`
- `last_seen`
- `seen_count`
- `error_count`
- `source_notes`

Japanese fields such as `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs` remain Japanese language-pack fields. They must not be mechanically renamed to generic fields during migration.

Preserve unknown frontmatter fields and body content. Core readers and writers must keep language extensions they do not understand, unless a validator returns an explicit blocking error before any write.

## Contract Ownership Matrix

| Contract surface | Owner |
|---|---|
| Vault context fields and version negotiation | core |
| capability IDs and maturity values | core contract |
| SRS lifecycle fields in the core review-card shell | core |
| Japanese templates, fields, item types, tag namespace, dictionaries, pronunciation, and accent behavior | Japanese language pack |
| Japanese review-material templates, including vocabulary, grammar, pronunciation, error, and daily study checklist structures | Japanese language pack |
| explicit Vault path configuration | private Vault configuration |
| language-pack default path roles | selected language pack |
| media import, ASR, transcript generation, and deterministic slicing | external adapter boundary |
| migration source inventory, target inventory, transform records, conflicts, and verification reports | temporary migration module |
| old `jp-*` entry points and Vault-embedded public-repository topology | old-framework exit work |
| private notes, cards, media, transcripts, review history, and personal reflections | private Vault data |

## Path And Write Contract

Path ownership order:

1. explicit Vault path configuration
2. selected language-pack defaults

This fixed order applies to Vault learning paths and generated Vault assets. Core-internal cache or temporary paths are not learning paths and must be declared separately if Phase 1 introduces them.

Prose examples, historical folders, tags, or note content are not path authority. Old Vault historical paths may only appear through a migration manifest or a read-only source inventory.

Write-capable workflows must follow this sequence:

1. bind one Vault root, one Vault context, and one capability
2. run read-only checks
3. prepare preview or pending writes
4. run core validation and language-pack validation
5. write only when all required checks pass
6. report changed files and skipped files

Unsupported capability, unknown schema version, missing language pack, or ambiguous target language must fail explicitly. It must not fall back to Japanese behavior.

External tool failure is a stop condition before write when the selected capability depends on that tool. A failed ASR adapter, missing slice exporter, missing dictionary, unsupported locale, or failed dependency check must not produce a partial note, partial SRS update, or guessed language-pack result.

## Implementation Gap Register

The following target-architecture abilities are intentionally not implemented by Phase 0:

| Gap | Earliest owner |
|---|---|
| Vault context file format and loader | Phase 1 core design |
| language-pack manifest loader and validator | Phase 1 core design |
| Japanese language-pack packaging and new entry points | Phase 1 Japanese language pack |
| new Japanese Vault initialization | Phase 1 new Vault initialization |
| source-to-target migration tooling and reports | Phase 1 temporary migration module |
| real private data migration, daily-use cutover, and old Vault read-only observation | Phase 2 |
| English language pack and English learning workflows | after core/Japanese boundary acceptance |

## Demand Ownership Decision Table

| Demand type | Owner |
|---|---|
| Private learning content | not public repo |
| Old Japanese entry only | temporary migration or exit work, not new framework unless required for migration |
| Templates, language fields, dictionaries, naturalness, register, or language processing | language pack |
| Media import, ASR, or deterministic slicing | external adapter boundary |
| Same semantics, status, and failure rules in at least two languages | candidate core |
| No second-language evidence | core-candidate only, no abstraction |

This table is the default filter for Phase 1 design review. It prevents accidental promotion of Japanese-specific behavior into shared core and prevents early English experiments from becoming core rules.

## Compatibility And Exit Position

The existing `jp-*` Skills are compatibility evidence and temporary migration sources. They are not long-term target entry points after the new Japanese Vault is accepted.

The target Japanese Vault keeps Japanese learning data and officially registers Japanese fields in the Japanese language pack. It does not preserve the old framework as a second runtime mode.

The public repository must not receive private notes, media, review records, or generated transcription artifacts. Contract examples must use synthetic data only.
