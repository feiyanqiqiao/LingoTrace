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
      workflows.py
      validators.py
      templates/
      views/
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
      "read_path_roles": ["listening_root"],
      "write_path_roles": ["listening_root"],
      "external_tools": ["listenkit_markdown", "listenkit_slice_export"],
      "behavior_evidence": ["JP-LISTEN-001", "JP-LISTEN-002", "JP-LISTEN-003", "JP-LISTEN-004", "JP-LISTEN-005", "JP-LISTEN-007"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": []
    },
    {
      "id": "source_notes",
      "maturity": "stable",
      "depends_on": [],
      "read_path_roles": ["source_notes_root", "listening_root"],
      "write_path_roles": ["source_notes_root"],
      "external_tools": ["listenkit_markdown"],
      "behavior_evidence": ["JP-SOURCE-001", "JP-SOURCE-003", "JP-SOURCE-004", "JP-SOURCE-005", "JP-SOURCE-006"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["source-note direction selection remains a human or reviewer-accepted semantic judgment"]
    },
    {
      "id": "review_materials",
      "maturity": "stable",
      "depends_on": [],
      "read_path_roles": ["focus_vocab_root", "base_vocab_root", "grammar_root", "error_root", "pronunciation_accent_root", "pronunciation_phoneme_root", "source_notes_root", "daily_notes_root"],
      "write_path_roles": ["focus_vocab_root", "base_vocab_root", "grammar_root", "error_root", "pronunciation_accent_root", "pronunciation_phoneme_root", "daily_notes_root"],
      "external_tools": ["japanese_dictionary"],
      "behavior_evidence": ["JP-REVIEW-001", "JP-REVIEW-005", "JP-REVIEW-006", "JP-REVIEW-009"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["semantic routing for grammar, error, accent, and phoneme cards"]
    },
    {
      "id": "speaking_cards",
      "maturity": "stable",
      "depends_on": ["review_materials"],
      "read_path_roles": ["speaking_card_root", "speaking_guide_root", "listening_root", "source_notes_root"],
      "write_path_roles": ["speaking_card_root"],
      "external_tools": [],
      "behavior_evidence": ["JP-SPEAK-001", "JP-SPEAK-002", "JP-SPEAK-003", "JP-SPEAK-004", "JP-SPEAK-005"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": ["naturalness and immediate-usefulness acceptance"]
    },
    {
      "id": "review_rollover",
      "maturity": "stable",
      "depends_on": [],
      "read_path_roles": ["focus_vocab_root", "base_vocab_root", "grammar_root", "error_root", "speaking_card_root", "listening_root", "pronunciation_accent_root", "pronunciation_phoneme_root", "daily_notes_root"],
      "write_path_roles": ["focus_vocab_root", "base_vocab_root", "grammar_root", "error_root", "speaking_card_root", "listening_root", "pronunciation_accent_root", "pronunciation_phoneme_root", "daily_notes_root"],
      "external_tools": [],
      "behavior_evidence": ["JP-ROLLOVER-001", "JP-ROLLOVER-002", "JP-ROLLOVER-003", "JP-ROLLOVER-004", "JP-ROLLOVER-005", "JP-ROLLOVER-006"],
      "conformance_tests": ["tools/architecture-baseline/tests/test_phase1_detailed_design.py"],
      "manual_review_cases": []
    }
  ],
  "unsupported_capabilities": [],
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
  },
  "templates": [
    {
      "id": "focus_vocab_card",
      "capability_id": "review_materials",
      "path": "lingotrace/packs/japanese/templates/focus-vocab-card.md",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "speaking_card",
      "capability_id": "speaking_cards",
      "path": "lingotrace/packs/japanese/templates/speaking-card.md",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "daily_checklist",
      "capability_id": "review_rollover",
      "path": "lingotrace/packs/japanese/templates/daily-checklist.md",
      "artifact_class": "recreate-from-pack"
    }
  ],
  "workflow_entrypoints": [
    {
      "id": "listening_notes_workflow",
      "capability_id": "listening_notes",
      "entrypoint": "lingotrace.packs.japanese.workflows:listening_notes",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "source_notes_workflow",
      "capability_id": "source_notes",
      "entrypoint": "lingotrace.packs.japanese.workflows:source_notes",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_materials_workflow",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.japanese.workflows:review_materials",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "speaking_cards_workflow",
      "capability_id": "speaking_cards",
      "entrypoint": "lingotrace.packs.japanese.workflows:speaking_cards",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_rollover_workflow",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.japanese.workflows:review_rollover",
      "call_policy": "through_core_write_guard"
    }
  ],
  "validators": [
    {
      "id": "review_materials_validator",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.japanese.validators:validate_review_materials"
    },
    {
      "id": "review_rollover_validator",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.japanese.validators:validate_review_rollover"
    }
  ],
  "resources": [
    {
      "id": "japanese_dictionary",
      "capability_id": "review_materials",
      "resource_type": "dictionary",
      "failure_policy": "stop_before_write"
    },
    {
      "id": "pitch_accent_data",
      "capability_id": "listening_notes",
      "resource_type": "pronunciation",
      "failure_policy": "preserve_unknown_without_confirmation"
    }
  ],
  "display_rules": [
    {
      "id": "accent_display_rule",
      "field": "accent_display",
      "owner": "Japanese language pack",
      "rule": "display pitch-accent hints without confirming generated candidates"
    },
    {
      "id": "meaning_language_rule",
      "field": "meaning_zh",
      "owner": "Japanese language pack",
      "rule": "Chinese explanation field remains separate from target-language content"
    }
  ],
  "default_views": [
    {
      "id": "total_training_dashboard",
      "capability_id": "review_rollover",
      "path": "lingotrace/packs/japanese/views/total-training.base",
      "artifact_class": "recreate-from-pack"
    }
  ],
  "initialization_artifacts": [
    {
      "id": "default_vault_context",
      "capability_id": "review_rollover",
      "path": ".lingotrace/vault-context.json",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "default_path_config",
      "capability_id": "review_rollover",
      "path": ".lingotrace/paths.json",
      "artifact_class": "recreate-from-pack"
    }
  ]
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

### 4.1.4 Unsupported Capability Declaration

The manifest must distinguish "not supported by this pack" from "forgotten by the manifest". The Japanese pack supports all five Phase 0 capability IDs in Phase 1, so its manifest sets `"unsupported_capabilities": []`.

A reviewed capability ID absent from `capabilities` must appear in `unsupported_capabilities` with this shape:

```json
{
  "id": "listening_notes",
  "failure_reason": "this language pack has no accepted media workflow yet",
  "failure_policy": "stop_before_write",
  "fallback": "none"
}
```

Failure codes exposed by the capability registry:

| Case | Registry code | Write behavior |
|---|---|---|
| Capability appears in `unsupported_capabilities` | `unsupported_capability` | stop before write |
| Capability is supported by the pack but absent from Vault `enabled_capabilities` | `not_enabled_in_vault` | stop before write |
| Capability is `experimental` and the Vault did not explicitly opt into experimental reads | `experimental_not_enabled` | stop before write |
| Capability is `deprecated` and the operation wants to write | `deprecated_write_blocked` | stop before write |

Every unsupported, unavailable, experimental, or deprecated case must report one of these explicit codes and must not fall back to Japanese behavior.

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
- `unsupported_capabilities`
- `external_tools`
- `language_fields`
- `item_types`
- `tag_namespace`
- `default_path_roles`
- `templates`
- `workflow_entrypoints`
- `validators`
- `resources`
- `display_rules`
- `default_views`
- `initialization_artifacts`

Rules:

- A Vault can bind only one language pack.
- Only `experimental`, `stable`, and `deprecated` maturity values are accepted.
- Unsupported capabilities stop before write.
- Every capability must declare both `read_path_roles` and `write_path_roles` so path access can be validated before write.
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
python -m lingotrace.cli.lingotrace migration-inventory --source <source-vault> --target <target-vault> --dry-run
```

Rules:

- Every command defaults to read-only or dry-run behavior until an implementation PR explicitly adds a write flag and tests it.
- `validate-vault` reads `.lingotrace/vault-context.json` and `.lingotrace/paths.json`.
- `validate-pack` reads `lingotrace/packs/japanese/manifest.json`.
- `init-japanese-vault --dry-run` reports the scaffold write plan and conflicts without creating files.
- `migration-inventory --dry-run` reads source and target Vault paths in read-only mode and emits source and target manifest previews without copying files; target is required even in dry-run so comparison reports cannot be inferred from source layout.
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

### 5.4 Pack-Owned Surface Registry

The Japanese pack manifest is also the registry for pack-owned templates, workflow entrypoints, validators, resources, display rules, default views, and initialization artifacts. Core code reads these records as declared surfaces; it must not discover templates, workflow functions, validators, dictionaries, views, or scaffold files by scanning arbitrary folders.

Pack-owned templates, workflow entrypoints, validators, resources, display rules, default views, and initialization artifacts must record:

- a stable `id`
- the owning `capability_id`
- the public path or Python entry point
- whether the artifact is generated from the pack or preserved from private data
- the failure policy when the artifact or resource is unavailable

Rules:

- Every capability must declare both `read_path_roles` and `write_path_roles`.
- A capability can read or write only roles listed in its own manifest record.
- Workflow entrypoints are new Japanese-pack entrypoints called only through the core write guard; old `jp-*` Skills are evidence only and are not pack workflow entrypoints.
- A template or initialization artifact with `artifact_class: recreate-from-pack` is public system material, not migrated private learning data.
- Validators are loaded from declared entry points only.
- Default views are generated pack artifacts; they are not evidence that private Obsidian view state should be migrated.
- Resources such as dictionaries and pronunciation data must keep their own failure policy and must not silently write unconfirmed generated values into learning cards.

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

### 7.2 Migration Manifest Schema

The temporary migration module must produce a manifest-shaped report even in Phase 1 dry-run mode. Phase 1 uses synthetic source and target fixtures; Phase 2 reuses the same shape for real private migration after a short write freeze.

Minimum manifest shape:

```json
{
  "source_vault": "<explicit-source-vault>",
  "target_vault": "<explicit-target-vault>",
  "source_manifest": [
    {
      "relative_path": "review/focus/vocab/example.md",
      "classification": "preserve-data",
      "comparison_strategy": "frontmatter_and_body",
      "content_hash": "sha256:<source-hash-or-empty-for-synthetic>",
      "detected_references": ["[[sources/example]]"],
      "conflict_status": "clear"
    }
  ],
  "target_manifest": [
    {
      "relative_path": "review/focus/vocab/example.md",
      "classification": "preserve-data",
      "comparison_strategy": "frontmatter_and_body",
      "content_hash": "sha256:<target-hash-or-empty-for-synthetic>",
      "comparison_result": "matches"
    }
  ],
  "preserve_data": [],
  "recreate_from_pack": [],
  "transform_with_map": [],
  "remove_after_cutover": [],
  "excluded_with_user_approval": [],
  "conflicts": [],
  "comparison_strategies": [
    "content_hash",
    "frontmatter_and_body",
    "links_and_hashes",
    "field_aware"
  ],
  "verification_report": {
    "unclassified_count": 0,
    "unresolved_conflict_count": 0,
    "missing_user_approval_count": 0,
    "accepted": false
  }
}
```

Manifest rules:

- `source_vault` and `target_vault` are explicit inputs and must not be inferred from folder names, tags, content, or historical layout.
- Manifest paths are Vault-relative or generated asset IDs; personal absolute paths are invalid.
- Valid `comparison_strategy` values are `content_hash`, `frontmatter_and_body`, `links_and_hashes`, and `field_aware`.
- `preserve-data` entries need a content hash, field-aware comparison, link-resolution report, or a recorded reason why the synthetic fixture cannot carry real bytes.
- `transform-with-map` records source path, target path, reason, before value, after value, preview result, conflict status, and acceptance result.
- `excluded_with_user_approval` records approver and reason; missing approval blocks acceptance.
- `conflicts` and `verification_report` must include unresolved links, missing attachments, missing transcript artifacts, ambiguous field ownership, and non-repeatable transform results.
- unclassified entries block cutover.

### 7.3 Comparison Report

The comparison report validates a synthetic source and synthetic target first. It checks:

- `preserve-data` content is preserved
- `recreate-from-pack` assets are not mistaken for private data
- `transform-with-map` changes are listed with before and after values
- `remove-after-cutover` entries are absent from target runtime assets
- conflict records block acceptance

Phase 2 owns real private data migration, final source manifest generation, daily-use cutover, old Vault read-only observation, and old Vault deletion.

### 7.4 Old-Framework Exit Ledger

Phase 1 migration tooling must also produce an old-framework exit ledger. This ledger is not permission to delete anything. It is a review artifact showing which old framework assets are still evidence, which are temporary migration readers, and which must disappear from target daily operation.

Minimum ledger entry shape:

```json
{
  "exit_candidate_id": "old-jp-skills",
  "source_pattern": "codex-skills/jp-*",
  "classification": "remove-after-cutover",
  "target_handling": "not copied into the target Vault",
  "replacement_owner": "Japanese language pack",
  "exit_status": "tracked",
  "required_evidence": [
    "new workflow entrypoint exists",
    "baseline or replacement check passes",
    "public docs no longer instruct this entrypoint"
  ]
}
```

Ledger rules:

- Exit candidates include old `jp-*` entry paths, installed-copy sync scripts, old Vault-coupled listening renderer paths, in-place layout migration scripts, implicit path fallback, old public docs that instruct removed entrypoints, and embedded public-repository topology.
- `exit_status` values are `tracked`, `blocked`, `ready-for-read-only-observation`, and `accepted-after-user-confirmation`.
- Entries classified as `temporary-migration` must name the read-only source reader and the condition for removal.
- Entries classified as `remove-after-cutover` are not copied into the target Vault.
- Read-only observation starts only after target acceptance; any asset discovered during read-only observation is handled through a recorded migration fix, not by reviving the old framework.
- Ledger entries with missing replacement evidence, unresolved conflicts, or missing user confirmation must be resolved before Phase 2 cutover acceptance.

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

### 8.1 External Adapter Preflight Codes

Adapter readiness is separate from capability support. External adapter failures must not be converted into an unsupported capability code, because that would hide whether the pack lacks a workflow or a required tool is unavailable.

| Case | Adapter code | Write behavior |
|---|---|---|
| Required tool or command is missing | `external_tool_unavailable` | stop before write |
| Required tool exists but cannot satisfy the declared minimum interface | `external_tool_version_mismatch` | stop before write |
| Required transcription, dictionary, or pronunciation locale is unavailable | `external_locale_unavailable` | stop before write |
| Preflight would install, upgrade, mutate cache, or otherwise have a side effect | `external_side_effect_blocked` | stop before write |
| Adapter command fails, times out, or returns an invalid readiness report | `external_adapter_failed` | stop before write |

## 9. Workstream Ownership Matrix

| Workstream | Owner | Phase 1 deliverable | Must not include |
|---|---|---|---|
| Core runtime skeleton | core | context loader, manifest loader, Capability registry, Path role resolver, Review-card shell service, Write transaction guard | Japanese text rules or English fields |
| Japanese pack boundary | Japanese language pack | Japanese pack manifest, field ownership, workflow entrypoints, validators, resources, display rules, default views, default path roles | broad field rename or old runtime mode |
| New Japanese Vault scaffold | new Vault initialization | initializer dry-run, scaffold write plan, synthetic initialization tests | private data copy or daily-use cutover |
| Migration dry-run inventory | temporary migration | read-only inventory, migration manifest, source/target manifest generator, old-framework exit ledger, synthetic comparison report, classification rules | real private data migration |
| External adapter checks | external adapter boundary | preflight contract and failure codes for ASR, dictionary, and slice export dependencies | ASR implementation inside core |
| Contributor-facing docs | public documentation | Phase 1 contributor guide and PR decomposition | instructions to run old framework as the target |

Tasks that touch more than one owner must be split into dependency-ordered PRs. A single PR must not simultaneously change core runtime, Japanese pack validators, migration tooling, and user-facing docs unless it is a documentation-only review of the already accepted design.

## 10. Implementation PR Sequence

Phase 1 implementation should be split into small PRs after this detailed design is accepted.

### Before Runtime Implementation Gate

Runtime implementation PRs cannot start until this detailed design PR is accepted by the project maintainers and Zheng Jie. The accepted design must have no unresolved review threads, green public checks, and an up-to-date PR body that records the validation evidence.

The runtime-start gate does not approve English functionality, real private migration, daily-use cutover, old Vault deletion, or old-framework removal. It only allows the Phase 1 implementation PRs below to begin.

### Dependency-Gated PR Sequence

| Implementation PR | Dependency | Dependency evidence |
|---|---|---|
| PR 1: Core Contract Skeleton | PR 1 has no runtime-code prerequisite beyond this gate. | Accepted detailed design, green public checks, and public allowlist scope. |
| PR 2: Japanese Pack Boundary | PR 2 depends on PR 1. | Core manifest loader, capability registry, path resolver, and write guard are available to test pack declarations. |
| PR 3: New Japanese Vault Initialization | PR 3 depends on PR 1 and PR 2. | Initializer can read the core context contract and generate only Japanese-pack-declared scaffold assets. |
| PR 4: Temporary Migration Inventory | PR 4 depends on PR 1 and PR 3. | Migration dry-run can bind explicit source and target Vault roots and compare against a synthetic initialized target. |
| PR 5: Contributor Documentation | PR 5 depends on accepted PR 1 through PR 4 evidence. | Contributor docs can point to real Phase 1 entry points and validation commands. |

Any dependency exception must be documented in the PR body with the reason, affected owner, and review checkpoint. Even with an exception, no PR may combine core runtime, Japanese pack boundary, new Vault initialization, temporary migration, and contributor documentation as one implementation change.

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
- Japanese workflow entrypoint registry
- Japanese validators
- Japanese display rules
- Japanese default views
- unsupported-capability failure records
- conformance tests derived from `language-pack-conformance-checklist.md`

Acceptance:

- Japanese pack declares all five Phase 0 capabilities.
- Japanese fields remain Japanese pack fields.
- Japanese validators accept synthetic Phase 0 fixtures.
- Workflow entrypoints are called only through the core write guard.
- Display rules and default views are manifest-declared and generated from the pack.
- Unsupported capability and external adapter failures stop before write.
- Unsupported, experimental, and deprecated capability failure codes are explicit and stop before write.

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
- migration manifest schema
- source and target manifest generator
- old-framework exit ledger
- classification output
- synthetic comparison report
- conflict and user-approval records

Acceptance:

- Manifest includes `source_vault`, `target_vault`, `source_manifest`, `target_manifest`, and `verification_report`.
- Comparison strategies include `content_hash`, `frontmatter_and_body`, `links_and_hashes`, and `field_aware`.
- Synthetic preserve-data entries keep relative paths, content hashes, frontmatter, and references.
- System assets are classified as `recreate-from-pack` or `remove-after-cutover`.
- Transform entries require an explicit mapping.
- Old-framework exit ledger records temporary-migration and remove-after-cutover candidates.
- PR 4 acceptance states that unclassified entries block acceptance.
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
- Capability registry reports explicit unavailable-capability failure codes.
- Path resolution follows Vault config before language-pack defaults.
- Review-card shell updates preserve language-owned and unknown fields.
- Write-capable operations use a preflight and preview path before writing.
- Japanese pack declares and validates the migrated Japanese fields.
- Japanese pack workflow entrypoints, display rules, default views, and initialization artifacts are manifest-declared.
- New Japanese Vault initialization works on synthetic targets and reports conflicts.
- Migration inventory dry-run works on synthetic source and target fixtures.
- Migration dry-run emits the manifest schema, comparison report, and old-framework exit ledger on synthetic fixtures.
- Temporary migration readers remain outside runtime and have recorded removal conditions.
- Old framework exit items remain tracked for Phase 2.
- Main branch checks are green.
- Maintainers and Zheng Jie accept that Phase 2 can start migration execution planning.

Phase 1 completion does not mean real data has moved. It means the new framework skeleton is ready for Phase 2 migration execution planning.

## 13. Phase 1 Design Review Acceptance Matrix

This matrix is a review aid, not a Phase 1 completion claim. It maps the detailed-design review criteria to concrete evidence in this PR so reviewers can decide whether runtime implementation may begin.

### Status Vocabulary

| Status | Meaning |
|---|---|
| Covered by this design PR | The design PR contains the requested design, boundary, gate, or test evidence. |
| External review required | Project maintainers and Zheng Jie must explicitly accept the decision before the next stage starts. |
| Out of this design PR scope | The item belongs to a later implementation, migration, cutover, or old-framework removal PR. |

### Matrix

| ID | Design review criterion | Evidence | Status |
|---|---|---|---|
| DD-01 | Runtime boundaries and blocked work are explicit. | Sections 1 and 2 separate core, Japanese pack, Vault configuration, and private data; they also block English functionality, real private migration, daily-use cutover, old Vault deletion, runtime Japanese fallback, broad field rename, and long-term old-framework compatibility. | Covered by this design PR |
| DD-02 | Runtime configuration schemas and command surfaces are concrete enough for PR 1 implementation. | Section 4 defines `.lingotrace/vault-context.json`, `.lingotrace/paths.json`, `lingotrace/packs/japanese/manifest.json`, and the `validate-vault`, `validate-pack`, `init-japanese-vault`, and `migration-inventory` command surfaces. | Covered by this design PR |
| DD-03 | Capability maturity, unavailable-capability behavior, and adapter failures have explicit stop-before-write rules. | Sections 4.1.2, 4.1.3, 4.1.4, and 8.1 define stable evidence, experimental-default behavior, unavailable-capability codes, and external adapter preflight codes. | Covered by this design PR |
| DD-04 | The Japanese pack boundary is implementable without preserving the old framework as runtime. | Sections 5 and 10 define Japanese-owned fields, validators, pack-owned surfaces, workflow entrypoints, and PR 2 acceptance while keeping old `jp-*` entries as evidence only. | Covered by this design PR |
| DD-05 | Target new Japanese Vault initialization is separated from data migration. | Sections 6 and 10 define initializer dry-run behavior, scaffold conflict reporting, generated context binding, and PR 3 dependency on PR 1 and PR 2. | Covered by this design PR |
| DD-06 | Temporary migration design preserves private data by default without approving real migration. | Section 7 defines preserve/recreate/transform/remove classifications, explicit source and target manifests, comparison strategies, conflict handling, and the statement that Phase 1 does not copy real private learning data. | Covered by this design PR |
| DD-07 | Old-framework exit obligations remain visible before Phase 2. | Section 7.4 defines the old-framework exit ledger, temporary-migration and remove-after-cutover handling, read-only observation rules, and Phase 2 cutover blockers. | Covered by this design PR |
| DD-08 | Workstream ownership and implementation dependencies prevent broad mixed-scope PRs. | Sections 9 and 10 define the ownership matrix, the Before Runtime Implementation Gate, the Dependency-Gated PR Sequence, and the dependency-exception rule. | Covered by this design PR |
| DD-09 | Validation strategy keeps Japanese behavior baseline and new framework tests separate. | Section 11 requires existing Japanese behavior baseline checks plus new framework tests on synthetic public data, with the new runtime test tree added only after runtime tests exist. | Covered by this design PR |
| DD-10 | Phase 1 completion criteria do not imply real migration or cutover. | Section 12 requires core, pack, initializer, migration dry-run, exit tracking, green checks, and human acceptance while explicitly stating that Phase 1 completion does not mean real data has moved. | Covered by this design PR |
| DD-11 | Runtime implementation, real private migration, English functionality, daily-use cutover, old Vault deletion, and old-framework removal are not delivered by this design PR. | The Boundary section in the PR body and sections 1, 6, 7, 10, and 12 keep these items out of design PR scope. | Out of this design PR scope |
| DD-12 | Maintainers and Zheng Jie accept this detailed design before runtime implementation starts. | Section 10 requires acceptance by project maintainers and Zheng Jie, no unresolved review threads, green public checks, and an up-to-date PR body before runtime implementation PRs can start. | External review required |
