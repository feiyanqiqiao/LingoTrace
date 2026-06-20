# LingoTrace Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Each implementation PR must start from a current `main`, keep one workstream owner, and record validation evidence in the PR body.

**Goal:** Build the minimum Phase 1 runtime skeleton that turns the Phase 0 contracts and Phase 1 detailed design into testable public code without moving private learning data.

**Architecture:** Phase 1 is implemented as five dependency-gated PRs. PR 1 creates the shared core contract skeleton; PR 2 adds the Japanese pack boundary; PR 3 adds a new Japanese Vault initializer; PR 4 adds temporary migration inventory dry-runs; PR 5 documents contributor usage after real commands exist.

**Tech Stack:** Python 3.14 standard library, `unittest`, JSON configuration files, GitHub Actions, conservative public-file allowlist.

---

## 1. Inputs

This plan is executable guidance for the design already accepted in:

- `docs/multilingual/phase-1/detailed-design.md`
- `docs/multilingual/phase-0/architecture-contracts.md`
- `docs/multilingual/phase-0/language-pack-conformance-checklist.md`
- `docs/multilingual/phase-0/japanese-migration-contract.md`
- `docs/multilingual/phase-0/old-framework-exit-checklist.md`
- `docs/multilingual/phase-0/phase-1-entry-gate.md`
- `docs/multilingual/phase-0/current-state-baseline.md`
- `docs/multilingual/phase-0/workflow-evidence-index.md`
- `tools/architecture-baseline/README.md`

The Phase 1 detailed design remains the source of truth for interfaces. This document turns it into PR-sized execution.

## 2. Phase 1 Non-Goals

Every Phase 1 PR must keep these out of scope:

- English functionality.
- Real private data migration.
- Daily-use cutover.
- Old Vault deletion.
- Old-framework removal.
- Runtime fallback to Japanese behavior.
- Broad renaming of Japanese learning fields.
- Long-term compatibility mode for old `jp-*` entries.

The old `jp-*` skills remain evidence and temporary migration sources only.

## 3. Branch And PR Rules

Each PR starts from a clean, current `main`:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/phase1-prN-short-name
```

Each PR body must include:

- scope summary
- explicit non-goals
- validation commands and results
- changed public allowlist or CI rules, if any
- dependency evidence from previous PRs

Each PR must run:

```bash
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
/opt/homebrew/bin/python3.14 -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
git diff --check
git diff --cached --check
bash tools/git/check-public-staged-files.sh
```

After PR 1 creates `tests/lingotrace/`, every implementation PR must also run:

```bash
/opt/homebrew/bin/python3.14 -m unittest discover -s tests/lingotrace -p 'test_*.py'
```

## 4. Dependency-Gated PR Sequence

| PR | Branch | Owner | Dependency | Merge Gate |
|---|---|---|---|---|
| PR 1: Core Contract Skeleton | `codex/phase1-pr1-core-contract-skeleton` | core | Accepted Phase 1 design and this plan | Core loaders, registry, path resolver, review-card shell, write guard, and report envelope pass synthetic tests |
| PR 2: Japanese Pack Boundary | `codex/phase1-pr2-japanese-pack-boundary` | Japanese language pack | PR 1 merged | Japanese manifest, fields, defaults, validators, views, and unsupported-capability declarations pass pack tests |
| PR 3: New Japanese Vault Initialization | `codex/phase1-pr3-japanese-vault-init` | new Vault initialization | PR 1 and PR 2 merged | Initializer dry-run and synthetic scaffold tests pass without overwriting existing files |
| PR 4: Temporary Migration Inventory | `codex/phase1-pr4-migration-inventory` | temporary migration | PR 1 and PR 3 merged | Source and target dry-run manifests, comparison report, and old-framework exit ledger pass synthetic tests |
| PR 5: Contributor Documentation | `codex/phase1-pr5-contributor-docs` | public documentation | PR 1 through PR 4 merged | Contributor docs point to real commands and do not imply English support or real migration |

No PR may combine core runtime, Japanese pack boundary, new Vault initialization, temporary migration, and contributor documentation as one implementation change.

## 5. PR 1: Core Contract Skeleton

### Scope

PR 1 creates the shared runtime contract layer only. It does not add a Japanese manifest, real workflow adapters, Vault initialization, migration inventory, or CLI entrypoint beyond testable library interfaces.

### Public Files

Create:

- `lingotrace/__init__.py`
- `lingotrace/core/__init__.py`
- `lingotrace/core/reports.py`
- `lingotrace/core/context.py`
- `lingotrace/core/manifests.py`
- `lingotrace/core/capabilities.py`
- `lingotrace/core/paths.py`
- `lingotrace/core/review_cards.py`
- `lingotrace/core/transactions.py`
- `tests/lingotrace/__init__.py`
- `tests/lingotrace/core/__init__.py`
- `tests/lingotrace/core/test_reports.py`
- `tests/lingotrace/core/test_context.py`
- `tests/lingotrace/core/test_manifests.py`
- `tests/lingotrace/core/test_capabilities.py`
- `tests/lingotrace/core/test_paths.py`
- `tests/lingotrace/core/test_review_cards.py`
- `tests/lingotrace/core/test_transactions.py`

Modify:

- `tools/git/check-public-staged-files.sh`
- `.github/workflows/japanese-baseline.yml`

Do not modify:

- `codex-skills/`
- `系统配置/`
- `学习系统/总训练.base`
- private notes, media, PDFs, images, or Obsidian state

### PR 1 APIs

`lingotrace/core/reports.py` owns machine-checkable command reports:

- `Finding(code, message, severity="error", path=None)`
- `CommandReport(command, mode, exit_code=0, errors=None, warnings=None, read_files=None, planned_writes=None, changed_files=None, skipped_files=None, blocked_files=None, artifacts=None)`
- `CommandReport.accepted`
- `CommandReport.to_dict()`

`lingotrace/core/context.py` owns Vault context loading:

- `VaultContext(vault_schema_version, target_language, explanation_language, language_pack, language_pack_version, enabled_capabilities)`
- `ContextLoadResult(context, findings, report)`
- `load_vault_context(vault_root)`

`lingotrace/core/manifests.py` owns language-pack manifest loading:

- `CapabilityDeclaration(id, maturity, depends_on, read_path_roles, write_path_roles, external_tools, behavior_evidence, conformance_tests, manual_review_cases)`
- `UnsupportedCapability(id, failure_reason, failure_policy, fallback)`
- `LanguagePackManifest(...)`
- `ManifestLoadResult(manifest, findings, report)`
- `load_language_pack_manifest(path)`

`lingotrace/core/capabilities.py` owns capability decisions:

- `PHASE0_CAPABILITY_IDS`
- `CapabilityDecision(capability_id, accepted, findings)`
- `CapabilityRegistry(manifest)`
- `CapabilityRegistry.require(capability_id, context)`

`lingotrace/core/paths.py` owns path role config and resolution:

- `PathRole(role, relative_path, source)`
- `PathResolution(role, relative_path, source)`
- `PathConfigLoadResult(path_roles, findings, report)`
- `load_path_config(vault_root)`
- `resolve_path_roles(manifest, path_roles)`

`lingotrace/core/review_cards.py` owns review-card field preservation:

- `ReviewCardShell(frontmatter, body)`
- `merge_review_card_fields(existing, updates)`

`lingotrace/core/transactions.py` owns stop-before-write behavior:

- `WritePlanEntry(path, action, reason)`
- `WriteTransactionGuard(capability_decision, report)`
- `WriteTransactionGuard.preview(entries)`
- `WriteTransactionGuard.apply(entries)`

### PR 1 Task Checklist

- [ ] Write `test_reports.py` first. Assert report output contains `command`, `mode`, `accepted`, `exit_code`, `errors`, `warnings`, `read_files`, `planned_writes`, `changed_files`, `skipped_files`, `blocked_files`, and `artifacts`; assert `accepted` is true only when exit code is zero and no errors remain.
- [ ] Implement `reports.py` with deterministic ordering and no absolute path expansion.
- [ ] Write `test_context.py`. Cover missing `.lingotrace/vault-context.json`, unsupported schema version, unsupported target language, duplicate capabilities, and valid context loading.
- [ ] Implement `context.py` using only `json`, `dataclasses`, and `pathlib`.
- [ ] Write `test_manifests.py`. Cover invalid JSON, invalid maturity, duplicate capability IDs, unsupported capability fallback not equal to `none`, missing stable evidence, and valid manifest loading.
- [ ] Implement `manifests.py`.
- [ ] Write `test_capabilities.py`. Cover unknown capability, disabled capability, unsupported capability, experimental capability, dependency missing from context, and stable enabled capability.
- [ ] Implement `capabilities.py`.
- [ ] Write `test_paths.py`. Cover missing path config, Vault config overriding pack defaults, rejected `..` relative paths, unknown roles, and deterministic resolver output.
- [ ] Implement `paths.py`.
- [ ] Write `test_review_cards.py`. Cover preserving unknown fields, preserving language-owned fields not included in updates, updating public shell fields, and retaining body text.
- [ ] Implement `review_cards.py`.
- [ ] Write `test_transactions.py`. Cover preview mode with no writes, blocked apply when capability decision is rejected, and deterministic planned write report.
- [ ] Implement `transactions.py`.
- [ ] Update `tools/git/check-public-staged-files.sh` to allow `lingotrace/` and `tests/lingotrace/`.
- [ ] Update `.github/workflows/japanese-baseline.yml` to run `python -m unittest discover -s tests/lingotrace -p 'test_*.py'`.
- [ ] Run all baseline and runtime tests.
- [ ] Commit and open PR 1 with the validation evidence.

### PR 1 Acceptance

PR 1 is accepted only when:

- Vault context loader rejects missing or incompatible context before write.
- Language pack manifest loader rejects invalid maturity, duplicate capabilities, and missing stable evidence.
- Capability registry rejects undeclared, unsupported, disabled, experimental, and dependency-incomplete capabilities.
- Path role resolver uses Vault config before pack defaults and rejects unsafe relative paths.
- Review-card shell preserves unknown fields.
- Write transaction guard can preview without writing and blocks apply when capability checks fail.
- Shared command report envelope is deterministic and safe for public CI logs.
- Public allowlist and CI include the new runtime package and tests.

## 6. PR 2: Japanese Pack Boundary

### Scope

PR 2 adds the Japanese pack as data and validators on top of PR 1. It does not migrate private Vault files or call old `jp-*` skills at runtime.

### Public Files

Create:

- `lingotrace/packs/__init__.py`
- `lingotrace/packs/japanese/__init__.py`
- `lingotrace/packs/japanese/manifest.json`
- `lingotrace/packs/japanese/fields.json`
- `lingotrace/packs/japanese/paths.json`
- `lingotrace/packs/japanese/workflows.py`
- `lingotrace/packs/japanese/validators.py`
- `lingotrace/packs/japanese/templates/focus-vocab-card.md`
- `lingotrace/packs/japanese/templates/speaking-card.md`
- `lingotrace/packs/japanese/templates/daily-checklist.md`
- `lingotrace/packs/japanese/views/total-training.base`
- `tests/lingotrace/packs/__init__.py`
- `tests/lingotrace/packs/test_japanese_pack.py`

Modify:

- `tools/git/check-public-staged-files.sh` only if the PR 1 allowlist is insufficient for pack templates or views.

### Tasks

- [ ] Write tests asserting the Japanese manifest declares all five Phase 0 capability IDs: `listening_notes`, `source_notes`, `review_materials`, `speaking_cards`, and `review_rollover`.
- [ ] Write tests asserting Japanese fields remain pack-owned: `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs`.
- [ ] Write tests asserting default path roles match the Phase 1 detailed design.
- [ ] Write tests asserting unsupported capabilities are explicit and empty for the Japanese pack.
- [ ] Implement manifest, fields, path defaults, templates, views, and validator stubs.
- [ ] Run all baseline and runtime tests.

### Acceptance

PR 2 is accepted only when:

- Japanese pack declarations load through PR 1 core loaders.
- All five Phase 0 capability IDs are declared.
- Japanese pack fields are not renamed into generic core fields.
- Pack-owned templates and views are public artifacts, not private Vault data.
- Workflow entrypoints are declarative and not direct old-skill calls.

## 7. PR 3: New Japanese Vault Initialization

### Scope

PR 3 adds a dry-run-first initializer for a brand-new Japanese Vault target. It does not copy or transform existing private learning data.

### Public Files

Create:

- `lingotrace/init/__init__.py`
- `lingotrace/init/japanese_vault.py`
- `tests/lingotrace/init/__init__.py`
- `tests/lingotrace/init/test_japanese_vault.py`

Modify:

- `lingotrace/core/transactions.py` only if initializer previews expose a missing general-purpose report field.

### Tasks

- [ ] Write tests for empty target dry-run that reports `.lingotrace/vault-context.json`, `.lingotrace/paths.json`, scaffold folders, templates, and views as planned writes.
- [ ] Write tests for non-empty target conflicts.
- [ ] Write tests proving dry-run writes no files.
- [ ] Implement initializer planning using PR 1 write guard and PR 2 pack artifacts.
- [ ] Run all baseline and runtime tests.

### Acceptance

PR 3 is accepted only when:

- Dry-run writes no files.
- Generated context binds exactly one target language and one pack.
- Existing files are not overwritten without explicit conflict records.
- Scaffold assets are classified as `recreate-from-pack`.

## 8. PR 4: Temporary Migration Inventory

### Scope

PR 4 adds read-only synthetic migration inventory tools. It does not execute real migration, cut over daily use, or remove old framework assets.

### Public Files

Create:

- `lingotrace/migration/__init__.py`
- `lingotrace/migration/inventory.py`
- `lingotrace/migration/compare.py`
- `tests/lingotrace/migration/__init__.py`
- `tests/lingotrace/migration/test_inventory.py`
- `tests/lingotrace/migration/test_compare.py`

### Tasks

- [ ] Write tests for explicit `source_vault` and `target_vault` binding.
- [ ] Write tests for `preserve-data`, `recreate-from-pack`, `transform-with-map`, `remove-after-cutover`, and `excluded_with_user_approval` classifications.
- [ ] Write tests for comparison strategies: `content_hash`, `frontmatter_and_body`, `links_and_hashes`, and `field_aware`.
- [ ] Write tests that unclassified entries block acceptance.
- [ ] Implement read-only inventory and comparison reports on synthetic fixtures.
- [ ] Run all baseline and runtime tests.

### Acceptance

PR 4 is accepted only when:

- Manifest includes source Vault, target Vault, source manifest, target manifest, and verification report.
- Preserve-data entries keep relative paths, content hashes, frontmatter, and references.
- Transform entries require explicit mapping.
- Old-framework exit ledger records temporary-migration and remove-after-cutover candidates.
- Conflicts and unclassified entries block acceptance.

## 9. PR 5: Contributor Documentation

### Scope

PR 5 documents the Phase 1 public entry points after they exist. It does not introduce new runtime behavior.

### Public Files

Create or modify:

- `docs/multilingual/phase-1/contributor-guide.md`
- `tools/README.md`
- `README.md` only if a short pointer is useful.

### Tasks

- [ ] Document how contributors run Phase 1 tests.
- [ ] Document accepted PR scopes and blocked scopes.
- [ ] Document that old `jp-*` entries are migration evidence, not new runtime entry points.
- [ ] Document that English support has not shipped in Phase 1.
- [ ] Run documentation validation and public allowlist checks.

### Acceptance

PR 5 is accepted only when:

- Docs point to real Phase 1 entry points and commands.
- Docs do not instruct contributors to start new work from old `jp-*` entries.
- Docs do not imply English support, real migration, cutover, old Vault deletion, or old-framework removal has shipped.

## 10. Phase 1 Completion Gate

Phase 1 is complete only when all five PRs are merged and the following are true on `main`:

- Core can load and validate explicit Vault context.
- Core can load and validate the Japanese pack manifest.
- Capability checks enforce the five fixed Phase 0 capability IDs.
- Capability registry reports explicit unavailable-capability failure codes.
- Path resolution follows Vault config before language-pack defaults.
- Command report envelope is deterministic and contains no personal absolute paths.
- Review-card shell updates preserve language-owned and unknown fields.
- Write-capable operations use preflight and preview paths before writing.
- Japanese pack declares and validates migrated Japanese fields.
- Japanese pack workflow entrypoints, display rules, default views, and initialization artifacts are manifest-declared.
- New Japanese Vault initialization works on synthetic targets and reports conflicts.
- Migration inventory dry-run works on synthetic source and target fixtures.
- Migration dry-run emits manifest schema, comparison report, and old-framework exit ledger on synthetic fixtures.
- Temporary migration readers remain outside runtime and have recorded removal conditions.
- Old framework exit items remain tracked for Phase 2.
- Main branch checks are green.
- The project owner accepts that Phase 2 can start migration execution planning.

Phase 1 completion does not mean real private learning data has moved.
