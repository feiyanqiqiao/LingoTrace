# LingoTrace Phase 1 Detailed Design

This is the Phase 1 detailed design for turning the Phase 0 contracts into an implementable four-layer framework. It is a design and implementation-planning document, not a runtime implementation.

Related inputs:

- `docs/lingotrace_multilingual_architecture_plan.md`
- `docs/lingotrace_multilingual_phase0_implementation_plan.md`
- `docs/multilingual/phase-0/architecture-contracts.md`
- `docs/multilingual/phase-0/language-pack-conformance-checklist.md`
- `docs/multilingual/phase-0/japanese-migration-contract.md`
- `docs/multilingual/phase-0/old-framework-exit-checklist.md`
- `docs/multilingual/phase-0/phase-1-entry-gate.md`
- `docs/multilingual/phase-0/current-state-baseline.md`
- `docs/multilingual/phase-0/workflow-evidence-index.md`
- `docs/multilingual/phase-0/migration-scope-and-asset-inventory.md`
- `tools/architecture-baseline/README.md`

## 1. Design Position

Phase 0 froze the contracts. Phase 1 designs and builds the minimum framework skeleton that those contracts require.

Phase 1 must produce:

- a shared core runtime skeleton
- a Japanese language pack boundary
- a new Japanese Vault scaffold flow
- a temporary migration dry-run inventory flow
- a Conformance test suite that converts Phase 0 checklist rules into executable gates
- public documentation for contributors

Phase 1 must not produce:

- no English functionality
- no real private data migration
- no daily-use cutover
- no old Vault deletion
- no runtime fallback to Japanese behavior
- no broad rename of Japanese learning fields
- no long-term old-framework compatibility mode

The old `jp-*` entries remain evidence and temporary migration sources during this phase. That is not a compatibility mode. New runtime work must enter through explicit Vault context, capability checks, and a selected language pack.

## 2. Four-Layer Runtime Shape

Phase 1 turns the planning diagram into a runnable boundary:

```text
core
  -> selected language pack
    -> explicit Vault configuration
      -> private learning data
```

The arrows mean "must validate against", not "must copy data into". Core and language packs live in the public project. Vault configuration and learning data live in the user's private Vault.

| Layer | Phase 1 design output | Write authority |
|---|---|---|
| core | loaders, capability registry, path resolver, review-card shell, write guard | public runtime only |
| Japanese language pack | manifest, fields, default paths, validators, current workflow boundary | public language pack |
| Vault configuration | explicit target language, explanation language, selected pack, versions, enabled capabilities, path overrides | private Vault |
| private learning data | notes, cards, media, review state, user edits | private Vault only |

One operation binds exactly one Vault root, one Vault context, and one capability. Cross-Vault cache reuse, path reuse, and state reuse are blocked.

## 3. Proposed Public File Layout

Phase 1 implementation should add a small Python package instead of expanding the old skill folders. The first implementation PR that creates these paths must also update the public allowlist with exact path prefixes.

```text
lingotrace/
  core/
    context.py
    manifests.py
    capabilities.py
    paths.py
    review_cards.py
    transactions.py
  packs/
    japanese/
      manifest.json
      fields.json
      paths.json
      validators.py
  init/
    japanese_vault.py
  migration/
    inventory.py
    compare.py
  cli/
    lingotrace.py

tests/
  lingotrace/
    core/
    packs/
    init/
    migration/
```

Existing Phase 0 tests under `tools/architecture-baseline/` remain contract and characterization tests. New runtime tests should live under `tests/lingotrace/` once the package exists. Phase 1 must not import `tools/architecture-baseline/tests/helpers.py` into production code because those helpers are only an independent acceptance oracle.

## 3.1 Public Allowlist And CI Changes

The first implementation PR that creates runtime files must update the public file allowlist narrowly:

- allow `lingotrace/` for public runtime source
- allow `tests/lingotrace/` for public runtime tests
- keep `tools/architecture-baseline/` as the contract and characterization test area
- keep `.lingotrace/` private to target Vaults; it must not be added to the public allowlist

The same PR must update CI only after tests exist for the new runtime tree. The new CI step should run:

```bash
python -m unittest discover -s tests/lingotrace -p 'test_*.py'
```

CI must continue running the existing `Japanese Baseline` and `Public File Allowlist` gates. A runtime PR cannot bypass those gates by limiting workflow paths.

## 4. Core Interfaces

### 4.1 Vault Context Loader

The Vault context loader reads an explicit context file from the target Vault. Phase 1 should use a standard-library-readable JSON file for runtime configuration:

```text
.lingotrace/vault-context.json
```

Required fields:

- `vault_schema_version`
- `target_language`
- `explanation_language`
- `language_pack`
- `language_pack_version`
- `enabled_capabilities`

Rules:

- Missing file stops every write-capable workflow before write.
- Unknown `vault_schema_version` stops before write.
- `target_language` is never inferred from folder, tag, card content, or old Japanese path names.
- The loader returns a typed context object and a list of validation findings.
- Validation findings are deterministic strings suitable for CLI output and tests.

### 4.1.1 Runtime Config Schemas

Phase 1 fixes the first runtime configuration shape as JSON so loaders can be implemented with the Python standard library.

Vault context file path:

```json
{
  "path": ".lingotrace/vault-context.json",
  "vault_schema_version": 1,
  "target_language": "ja",
  "explanation_language": "zh",
  "language_pack": "lingo-japanese",
  "language_pack_version": "0.1.0",
  "enabled_capabilities": [
    "listening_notes",
    "source_notes",
    "review_materials",
    "speaking_cards",
    "review_rollover"
  ]
}
```

Field rules:

- `vault_schema_version` is an integer. Phase 1 accepts only `1`.
- `target_language` is a lowercase BCP-47 primary language subtag. Phase 1 accepts `ja` for the Japanese pack.
- `explanation_language` is a lowercase BCP-47 primary language subtag. Phase 1 accepts `zh`.
- `language_pack` must match exactly one first-party pack ID.
- `language_pack_version` is an exact version pin, not a range.
- `enabled_capabilities` is a list of unique fixed capability IDs.

Vault path configuration file path:

```json
{
  "path": ".lingotrace/paths.json",
  "path_roles": [
    {
      "role": "focus_vocab_root",
      "relative_path": "review/focus/vocab",
      "source": "vault_config"
    },
    {
      "role": "base_vocab_root",
      "relative_path": "review/base/vocab",
      "source": "vault_config"
    },
    {
      "role": "grammar_root",
      "relative_path": "review/grammar",
      "source": "vault_config"
    },
    {
      "role": "error_root",
      "relative_path": "review/errors",
      "source": "vault_config"
    },
    {
      "role": "speaking_card_root",
      "relative_path": "speaking/cards",
      "source": "vault_config"
    },
    {
      "role": "speaking_guide_root",
      "relative_path": "speaking/guides",
      "source": "vault_config"
    },
    {
      "role": "listening_root",
      "relative_path": "listening",
      "source": "vault_config"
    },
    {
      "role": "pronunciation_accent_root",
      "relative_path": "review/pronunciation/accent",
      "source": "vault_config"
    },
    {
      "role": "pronunciation_phoneme_root",
      "relative_path": "review/pronunciation/phoneme",
      "source": "vault_config"
    },
    {
      "role": "source_notes_root",
      "relative_path": "sources",
      "source": "vault_config"
    },
    {
      "role": "daily_notes_root",
      "relative_path": "daily",
      "source": "vault_config"
    }
  ]
}
```

Path rules:

- `role` must match a role declared by the selected language pack.
- `relative_path` must be Vault-relative and must not contain `..`.
- `source` is `vault_config` for explicit Vault overrides and `language_pack_default` for resolved defaults.
- A resolver report must show which roles came from Vault config and which came from pack defaults.

Japanese pack manifest file path:

```json
{
  "path": "lingotrace/packs/japanese/manifest.json",
  "language_pack_id": "lingo-japanese",
  "language_pack_version": "0.1.0",
  "target_language": "ja",
  "transcription_locale": "ja-JP",
  "compatible_core": {
    "minimum": "0.1.0",
    "maximum_exclusive": "0.2.0"
  },
  "compatible_vault_schema": {
    "minimum": 1,
    "maximum": 1
  },
  "capabilities": [
    {
      "id": "listening_notes",
      "maturity": "stable",
      "depends_on": [],
      "external_tools": ["listenkit_markdown", "listenkit_slice_export"],
      "behavior_evidence": ["JP-LISTEN-001", "JP-LISTEN-002", "JP-LISTEN-003", "JP-LISTEN-004", "JP-LISTEN-005", "JP-LISTEN-007"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": []
    },
    {
      "id": "source_notes",
      "maturity": "stable",
      "depends_on": [],
      "external_tools": ["listenkit_markdown"],
      "behavior_evidence": ["JP-SOURCE-001", "JP-SOURCE-003", "JP-SOURCE-004", "JP-SOURCE-005", "JP-SOURCE-006"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["source-note direction selection remains a human or reviewer-accepted semantic judgment"]
    },
    {
      "id": "review_materials",
      "maturity": "stable",
      "depends_on": [],
      "external_tools": ["japanese_dictionary"],
      "behavior_evidence": ["JP-REVIEW-001", "JP-REVIEW-005", "JP-REVIEW-006", "JP-REVIEW-009"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["semantic routing for grammar, error, accent, and phoneme cards"]
    },
    {
      "id": "speaking_cards",
      "maturity": "stable",
      "depends_on": ["review_materials"],
      "external_tools": [],
      "behavior_evidence": ["JP-SPEAK-001", "JP-SPEAK-002", "JP-SPEAK-003", "JP-SPEAK-004", "JP-SPEAK-005"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["naturalness and immediate-usefulness acceptance"]
    },
    {
      "id": "review_rollover",
      "maturity": "stable",
      "depends_on": [],
      "external_tools": [],
      "behavior_evidence": ["JP-ROLLOVER-001", "JP-ROLLOVER-002", "JP-ROLLOVER-003", "JP-ROLLOVER-004", "JP-ROLLOVER-005", "JP-ROLLOVER-006"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": []
    }
  ],
  "external_tools": [
    {
      "id": "listenkit_markdown",
      "minimum_required": "generate-markdown command is available",
      "failure_policy": "stop_before_write"
    },
    {
      "id": "listenkit_slice_export",
      "minimum_required": "deterministic slice export command is available",
      "failure_policy": "stop_before_write"
    },
    {
      "id": "japanese_dictionary",
      "minimum_required": "offline dictionary lookup is available",
      "failure_policy": "stop_before_write"
    }
  ],
  "language_fields": [
    {"name": "reading", "owner": "Japanese language pack"},
    {"name": "accent_display", "owner": "Japanese language pack"},
    {"name": "meaning_zh", "owner": "Japanese language pack"},
    {"name": "kanji_diff", "owner": "Japanese language pack"},
    {"name": "kanji_diff_pairs", "owner": "Japanese language pack"}
  ],
  "item_types": ["vocab", "grammar", "pronunciation", "error", "speaking_card"],
  "tag_namespace": "jp",
  "default_path_roles": {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily"
  }
}
```

The first implementation PR may adjust values only when it records the reason and updates the corresponding conformance tests. It must not remove a Phase 0 capability from the Japanese pack without a reviewed replacement decision.

### 4.1.2 Stable Capability Evidence Gate

The Japanese pack can mark a capability as `stable` only when the manifest record carries enough reviewable evidence to connect the Phase 0 baseline with Phase 1 tests. The fields are:

- `behavior_evidence`: Phase 0 behavior IDs or an explicit Phase 1 replacement decision.
- `conformance_tests`: executable public tests that assert the runtime contract or synthetic fixture behavior.
- `manual_review_cases`: accepted reviewer checks for semantic quality that cannot be fully proven by deterministic tests.

Rules:

- no capability can be marked `stable` without at least one `behavior_evidence` entry.
- A stable capability must have either executable `conformance_tests` or an accepted `manual_review_cases` entry.
- Evidence must name concrete Phase 0 IDs such as `JP-REVIEW-001` and `JP-ROLLOVER-001`, not a broad workflow title.
- Missing external adapter preflight, unresolved ownership conflicts, or incomplete path-role coverage prevents stable maturity.
- A behavior marked `candidate` in Phase 0 can support a stable capability only when Phase 1 records the accepted manual review case or replacement decision that upgrades it.

### 4.1.3 Experimental By Default Rule

If any evidence field is missing, ambiguous, or contradicted by the Phase 0 baseline, the capability must stay `experimental` and unavailable by default in new Vault context. Experimental capabilities may be present in the manifest for design visibility, but the write transaction guard treats them as disabled unless a later reviewed PR changes the maturity and updates the conformance tests.

### 4.2 Language Pack Manifest Loader

The Language pack manifest loader reads a selected first-party pack manifest from the public project. Phase 1 should use:

```text
lingotrace/packs/japanese/manifest.json
```

Required manifest surfaces:

- `language_pack_id`
- `language_pack_version`
- `target_language`
- `transcription_locale`
- `compatible_core`
- `compatible_vault_schema`
- `capabilities`
- `external_tools`
- `language_fields`
- `item_types`
- `tag_namespace`
- `default_path_roles`

Rules:

- A Vault can bind only one language pack.
- Only `experimental`, `stable`, and `deprecated` maturity values are accepted.
- Unsupported capabilities stop before write.
- A pack cannot claim core fields as language fields.
- External pack installation is outside Phase 1.

### 4.3 Capability Registry

The Capability registry combines Vault context and pack manifest into an operation-ready capability record.

Fixed Phase 1 capability IDs:

- `listening_notes`
- `source_notes`
- `review_materials`
- `speaking_cards`
- `review_rollover`

Registry rules:

- A capability is available only when it appears in both `enabled_capabilities` and the selected pack manifest.
- A capability with missing external dependencies is unavailable for write.
- `deprecated` capabilities are readable only when the operation explicitly allows deprecated reads.
- Core never silently replaces an unavailable capability with an old `jp-*` entry.

### 4.4 Path Role Resolver

The Path role resolver produces concrete Vault-relative paths from two sources:

```text
Vault explicit path configuration
  > language-pack default path roles
```

Phase 1 should use:

```text
.lingotrace/paths.json
```

Minimum Japanese path role set for Phase 1:

| Role | Target new-Vault default | Phase 0 source behavior |
|---|---|---|
| `focus_vocab_root` | `review/focus/vocab` | Focus-first vocabulary review |
| `base_vocab_root` | `review/base/vocab` | Long-term vocabulary sink |
| `grammar_root` | `review/grammar` | Grammar card routing |
| `error_root` | `review/errors` | Error card routing |
| `speaking_card_root` | `speaking/cards` | Survival speaking review cards |
| `speaking_guide_root` | `speaking/guides` | Long speaking scene guides kept out of review |
| `listening_root` | `listening` | Fixed listening notes and slice artifacts |
| `pronunciation_accent_root` | `review/pronunciation/accent` | Accent contrast cards |
| `pronunciation_phoneme_root` | `review/pronunciation/phoneme` | Phoneme contrast cards |
| `source_notes_root` | `sources` | Flexible source notes and provenance |
| `daily_notes_root` | `daily` | Daily checklist writeback |

These defaults describe the target new Japanese Vault. They do not force the current old Vault to move files in Phase 1. Real private data paths are preserved by Phase 2 migration manifests unless a reviewed transform mapping is accepted.

Resolver rules:

- Paths must be Vault-relative.
- Path traversal outside the Vault is invalid.
- Historical old-Vault paths are accepted only by temporary migration inventory code.
- Tags and prose examples are not path authority.
- Resolver output includes source metadata showing whether each path came from Vault config or pack defaults.

### 4.5 Review-Card Shell Service

The Review-card shell service owns only the shared card lifecycle fields:

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

Rules:

- Japanese fields remain Japanese pack fields.
- `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs` are preserved as Japanese fields.
- Unknown frontmatter fields are preserved.
- Manual Markdown body content is preserved.
- Core validation can reject invalid core lifecycle state, but it does not rewrite language-owned fields.

### 4.6 Write Transaction Guard

The Write transaction guard is the mandatory entry point for write-capable workflows.

Required sequence:

1. bind Vault root, Vault context, selected pack, and capability
2. run read-only preflight checks
3. build a pending write plan
4. run core validation
5. run language-pack validation
6. run external adapter preflight if the capability requires it
7. write files only after every required check passes
8. report changed, skipped, and blocked files

Failure rules:

- External adapter failure stops before write.
- Missing capability stops before write.
- Version mismatch stops before write.
- Ambiguous target language stops before write.
- Validation failure stops before write.
- Partial SRS advancement is not allowed.

### 4.7 Command Surface

Phase 1 should expose one standard-library CLI wrapper around the runtime package. The initial command surface is:

```bash
python -m lingotrace.cli.lingotrace validate-vault --vault <vault-root>
python -m lingotrace.cli.lingotrace validate-pack --pack lingo-japanese
python -m lingotrace.cli.lingotrace init-japanese-vault --target <target-vault> --dry-run
python -m lingotrace.cli.lingotrace migration-inventory --source <source-vault> --dry-run
```

Rules:

- Every command defaults to read-only or dry-run behavior until an implementation PR explicitly adds a write flag and tests it.
- `validate-vault` reads `.lingotrace/vault-context.json` and `.lingotrace/paths.json`.
- `validate-pack` reads `lingotrace/packs/japanese/manifest.json`.
- `init-japanese-vault --dry-run` reports the scaffold write plan and conflicts without creating files.
- `migration-inventory --dry-run` reads the source Vault in read-only mode and emits an inventory report without copying files.
- Commands return non-zero status for missing context, unsupported capability, version mismatch, invalid path role, external adapter preflight failure, or unresolved conflict.

### 4.8 Legacy Bridge Rule

Core runtime must not import or call old `jp-*` Skills. The Japanese pack may link to those Skills as evidence while Phase 1 is being implemented, and the temporary migration module may read old Skill documents or old Vault structure in read-only mode to build inventory evidence.

This rule keeps old entries out of the target runtime:

- old `jp-*` Skills are not core APIs
- old Vault-embedded repository layout is not a target deployment model
- old path guessing is not a runtime fallback
- temporary source readers must be removable before Phase 2 cutover acceptance

## 5. Japanese Language Pack Boundary

The first language pack is Japanese because it migrates the current verified workflow. It must be implemented as a pack boundary, not as a direct rename of old code.

### 5.1 Japanese Pack Manifest

The Japanese pack manifest declares:

- `language_pack_id: lingo-japanese`
- `target_language: ja`
- `explanation_language` compatibility with Chinese explanations
- `transcription_locale: ja-JP`
- the five fixed capabilities
- Japanese-owned fields
- Japanese-owned item types
- Japanese tag namespace
- default path roles
- external adapter expectations for ListenKit and deterministic slice export

The manifest may point to old `jp-*` Skills as migration evidence, but new runtime operations cannot call those paths as the long-term interface.

### 5.2 Japanese Fields

Japanese fields remain Japanese pack fields:

- `reading`
- `accent_display`
- `meaning_zh`
- `kanji_diff`
- `kanji_diff_pairs`

Phase 1 must not rename them into generic `reading_text`, `accent`, or `meaning` fields. English and later language packs will define their own fields after the core/Japanese boundary is accepted.

### 5.3 Japanese Validators

The Japanese pack owns validators for:

- required Japanese fields for each item type
- Japanese tag namespace usage
- Japanese pronunciation and accent card placement
- vocabulary, grammar, pronunciation, error, and daily checklist structures
- current workflow-specific constraints that Phase 0 marked as `migration-required`

Validators must be deterministic and testable with synthetic public fixtures.

## 6. New Japanese Vault Initialization

Phase 1 designs a new Vault initialization flow, but it does not switch daily use to the new Vault.

The initializer creates or previews:

- `.lingotrace/vault-context.json`
- `.lingotrace/paths.json`
- language-pack default template instances
- Obsidian-facing scaffold folders required by the selected Japanese pack
- a validation report

The initializer must support an initializer dry-run mode that reports planned files without writing them. The first implementation target should use synthetic temporary directories in tests. Real personal Vault initialization remains a reviewed operation and does not imply private data migration.

Rules:

- The target directory must be explicit.
- Non-empty target directories require validation before write.
- Existing files are never overwritten without a planned conflict report.
- Generated scaffold files are `recreate-from-pack` assets.
- Private learning files are never generated by the initializer.

## 7. Temporary Migration Design

Phase 1 adds temporary migration tooling only far enough to produce a dry-run inventory and comparison report. It does not copy real private learning data.

### 7.1 Migration Dry-Run Inventory

The migration inventory dry-run reads a source Vault in read-only mode and classifies entries as:

- `preserve-data`
- `recreate-from-pack`
- `transform-with-map`
- `temporary-migration`
- `remove-after-cutover`

The scanner output must include:

- source-relative path
- classification
- reason
- detected references
- required user approval when applicable
- content hash when a file is eligible for preservation comparison

### 7.2 Comparison Report

The comparison report validates a synthetic source and synthetic target first. It checks:

- `preserve-data` content is preserved
- `recreate-from-pack` assets are not mistaken for private data
- `transform-with-map` changes are listed with before and after values
- `remove-after-cutover` entries are absent from target runtime assets
- conflict records block acceptance

Phase 2 owns real private data migration, final source manifest generation, daily-use cutover, old Vault read-only observation, and old Vault deletion.

## 8. External Adapter Boundary

Phase 1 does not redesign ListenKit. It defines how the new core asks an external adapter whether a capability can proceed.

External adapter boundary responsibilities:

- report tool identity and version
- report required command availability
- report required locale availability
- report whether deterministic slicing is available
- report that the preflight has no package installation or upgrade side effect
- stop before write when a required adapter check fails

Core does not perform ASR itself. Language packs can declare adapter requirements, and the write guard enforces them before write.

## 9. Workstream Ownership Matrix

| Workstream | Owner | Phase 1 deliverable | Must not include |
|---|---|---|---|
| Core runtime skeleton | core | context loader, manifest loader, Capability registry, Path role resolver, Review-card shell service, Write transaction guard | Japanese text rules or English fields |
| Japanese pack boundary | Japanese language pack | Japanese pack manifest, Japanese field ownership, deterministic validators, default path roles | broad field rename or old runtime mode |
| New Japanese Vault scaffold | new Vault initialization | initializer dry-run, scaffold write plan, synthetic initialization tests | private data copy or daily-use cutover |
| Migration dry-run inventory | temporary migration | read-only inventory, synthetic comparison report, classification rules | real private data migration |
| External adapter checks | external adapter boundary | preflight contract for ASR, dictionary, and slice export dependencies | ASR implementation inside core |
| Contributor-facing docs | public documentation | Phase 1 contributor guide and PR decomposition | instructions to run old framework as the target |

Tasks that touch more than one owner must be split into dependency-ordered PRs. A single PR must not simultaneously change core runtime, Japanese pack validators, migration tooling, and user-facing docs unless it is a documentation-only review of the already accepted design.

## 10. Implementation PR Sequence

Phase 1 implementation should be split into small PRs after this detailed design is accepted.

### PR 1: Core Contract Skeleton

Owner: core

Deliverables:

- `lingotrace/core/context.py`
- `lingotrace/core/manifests.py`
- `lingotrace/core/capabilities.py`
- `lingotrace/core/paths.py`
- `lingotrace/core/review_cards.py`
- `lingotrace/core/transactions.py`
- core tests using synthetic fixtures
- public allowlist update for the new package and tests

Acceptance:

- Vault context loader rejects missing or incompatible context.
- Language pack manifest loader rejects invalid maturity and owner conflicts.
- Capability registry rejects undeclared capabilities.
- Path role resolver uses Vault config before pack defaults.
- Review-card shell preserves unknown language fields.
- Write transaction guard can run in preview mode and stop before write.

### PR 2: Japanese Pack Boundary

Owner: Japanese language pack

Deliverables:

- Japanese pack manifest
- Japanese field declaration file
- Japanese default path roles
- Japanese validators
- conformance tests derived from `language-pack-conformance-checklist.md`

Acceptance:

- Japanese pack declares all five Phase 0 capabilities.
- Japanese fields remain Japanese pack fields.
- Japanese validators accept synthetic Phase 0 fixtures.
- Unsupported capability and external adapter failures stop before write.

### PR 3: New Japanese Vault Initialization

Owner: new Vault initialization

Deliverables:

- initializer dry-run command
- empty-target scaffold write plan
- conflict report for non-empty targets
- synthetic target Vault fixture tests

Acceptance:

- Dry-run writes no files.
- Scaffold assets are classified as `recreate-from-pack`.
- Existing files are not overwritten without an explicit conflict.
- Generated context binds exactly one target language and one pack.

### PR 4: Temporary Migration Inventory

Owner: temporary migration

Deliverables:

- read-only source inventory scanner
- classification output
- synthetic comparison report
- conflict and user-approval records

Acceptance:

- Synthetic preserve-data entries keep relative paths, content hashes, frontmatter, and references.
- System assets are classified as `recreate-from-pack` or `remove-after-cutover`.
- Transform entries require an explicit mapping.
- Conflicts block acceptance.

### PR 5: Contributor Documentation

Owner: public documentation

Deliverables:

- contributor-facing Phase 1 guide
- examples of accepted Phase 1 PR scope
- examples of blocked scope
- update to tool index if new commands are introduced

Acceptance:

- Documentation points to new framework entry points.
- Documentation does not instruct users to start new work from old `jp-*` entries.
- Documentation does not imply English support has shipped.

## 11. Phase 1 Validation Strategy

Phase 1 must keep two validation layers:

1. Existing Japanese behavior baseline stays green and proves the old Japanese behavior has not been accidentally changed.
2. New framework tests prove the new core and Japanese pack boundaries work on synthetic public data.

Minimum local validation after each implementation PR:

```bash
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

The `tests` command applies only after the new runtime test tree exists. Before that tree exists, the command is omitted and the reason is recorded in the PR.

## 12. Phase 1 Completion Gate

Phase 1 is complete only when all of the following are true:

- Core can load and validate explicit Vault context.
- Core can load and validate the Japanese pack manifest.
- Capability checks enforce the five fixed Phase 0 capability IDs.
- Path resolution follows Vault config before language-pack defaults.
- Review-card shell updates preserve language-owned and unknown fields.
- Write-capable operations use a preflight and preview path before writing.
- Japanese pack declares and validates the migrated Japanese fields.
- New Japanese Vault initialization works on synthetic targets and reports conflicts.
- Migration inventory dry-run works on synthetic source and target fixtures.
- Old framework exit items remain tracked for Phase 2.
- Main branch checks are green.
- Maintainers and Zheng Jie accept that Phase 2 can start migration execution planning.

Phase 1 completion does not mean real data has moved. It means the new framework skeleton is ready for Phase 2 migration execution planning.
