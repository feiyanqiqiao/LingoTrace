# LingoTrace Phase 2 Migration Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the current Japanese learning system into a new Japanese Vault that uses the shared LingoTrace core and Japanese language pack, while preserving private learning data by default and exiting the old framework only after accepted evidence.

**Architecture:** Phase 2 is a gated migration program, not a single broad refactor. The public repository may add migration tooling, tests, runbooks, and release artifacts; private Vault data, private manifests, and real migration outputs stay outside Git. Each execution stage binds an explicit source Vault, an explicit target Vault, one selected Japanese language pack, and a machine-checkable report.

**Tech Stack:** Python 3.14 standard library, `unittest`, JSON migration manifests, Obsidian Markdown and Bases files, existing `lingotrace/core`, `lingotrace/packs/japanese`, `lingotrace/init`, and `lingotrace/migration` modules.

---

## 1. Scope

Phase 2 starts after Phase 1 completion gate acceptance. It plans and executes the real Japanese Vault migration, but it does not allow uncontrolled daily-use switching, unreviewed transforms, or automatic old Vault deletion.

Phase 2 owns:

- final private source manifest generation during a short write freeze
- empty target Japanese Vault creation from the Phase 1 initializer
- private learning data copy, comparison, and conflict reporting
- explicit transform-map execution for reviewed exceptions only
- five-workflow acceptance on the target Vault
- cutover readiness review
- old Vault read-only observation entry
- old-framework exit evidence

Phase 2 does not automatically approve:

- English language support
- multi-target-language Vaults
- path or field normalization for cosmetic reasons
- copying the old framework as a supported target runtime
- deleting or archiving the old Vault without a separate user confirmation
- committing private notes, media, manifests, personal paths, or migration artifacts to the public repository

## 2. Required Inputs

The execution owner must provide these inputs locally when a migration run starts. They must not be committed:

- explicit source Vault root
- explicit empty or initialized target Vault root
- accepted Phase 1 `main` commit
- selected Japanese language pack ID: `lingo-japanese`
- selected Japanese language pack version: `0.1.0`
- approved transform map file, if any transforms are needed
- approved exclusion list, if any entries are excluded with user approval
- write-freeze start and end timestamps

The public repository should store only synthetic fixtures, code, tests, runbooks, and schema documentation. Real source and target manifests are private artifacts.

## 3. Safety Invariants

Every Phase 2 implementation PR and real run must preserve these invariants:

- Source and target Vault roots are explicit inputs. They are never inferred from directory names, tags, note content, or historical Japanese paths.
- Private learning data is `preserve-data` unless a contract-backed exception is recorded.
- System assets are `recreate-from-pack` from the selected release, not copied wholesale from the old framework.
- `transform-with-map` requires source path, target path, reason, before value, after value, preview result, conflict status, and acceptance result.
- unclassified entries block cutover.
- Missing user approval blocks cutover.
- Missing attachments, missing transcript artifacts, unresolved links, ambiguous field ownership, and non-repeatable transforms block the affected asset.
- The target Vault must keep `target_language=ja`, `explanation_language=zh`, `language_pack=lingo-japanese`, and exactly one target-language context.
- Old `jp-*` entries may be read as migration evidence or temporary source readers only. They are not target runtime entry points.
- The old Vault enters read-only observation only after target acceptance.
- Final old Vault deletion or archival requires separate explicit user confirmation after read-only observation.

## 4. Public File Plan

Phase 2 execution should be split into dependency-ordered PRs. The following files are expected public surfaces; private artifacts must stay outside this list.

| Stage | Public files | Responsibility |
|---|---|---|
| PR 2.0 Planning Gate | `docs/multilingual/phase-2/migration-execution-plan.md`, `tools/architecture-baseline/tests/test_phase2_migration_execution_plan.py` | Freeze this execution plan and document the gates. |
| PR 2.1 Migration Schema And Private Artifact Guard | `lingotrace/migration/schema.py`, `lingotrace/migration/private_artifacts.py`, `tests/lingotrace/migration/test_schema.py`, `tests/lingotrace/migration/test_private_artifacts.py` | Validate manifest shape and reject personal absolute paths in public reports. |
| PR 2.2 Final Source Inventory Runner | `lingotrace/migration/source_inventory.py`, `tests/lingotrace/migration/test_source_inventory.py` | Generate a private final source manifest from an explicit source Vault during write freeze. |
| PR 2.3 Target Vault Rehearsal Runner | `lingotrace/migration/target_rehearsal.py`, `tests/lingotrace/migration/test_target_rehearsal.py` | Create a dry-run target plan from the Japanese pack and compare it with generated target system assets. |
| PR 2.4 Data Copy And Transform Preview | `lingotrace/migration/copy_plan.py`, `lingotrace/migration/transform_plan.py`, `tests/lingotrace/migration/test_copy_plan.py`, `tests/lingotrace/migration/test_transform_plan.py` | Plan byte-preserving copies and reviewed transforms without committing private output. |
| PR 2.5 Comparator And Workflow Acceptance | `lingotrace/migration/verification.py`, `lingotrace/migration/workflow_acceptance.py`, `tests/lingotrace/migration/test_verification.py`, `tests/lingotrace/migration/test_workflow_acceptance.py` | Verify hashes, fields, links, attachments, SRS fields, and the five Japanese workflows on synthetic fixtures. |
| PR 2.6 Cutover And Observation Runbook | `docs/multilingual/phase-2/cutover-runbook.md`, `docs/multilingual/phase-2/read-only-observation-runbook.md`, architecture-baseline doc tests | Define owner approval, daily-use switch, observation, rollback, and final-removal gates. |

No PR may combine real private migration artifacts with public code or documentation.

## 5. Execution PR Sequence

### PR 2.0: Planning Gate

**Files:**

- Create: `docs/multilingual/phase-2/migration-execution-plan.md`
- Create: `tools/architecture-baseline/tests/test_phase2_migration_execution_plan.py`

- [ ] **Step 1: Write the documentation guard test**

Create `tools/architecture-baseline/tests/test_phase2_migration_execution_plan.py` with assertions that the plan exists, has no unresolved markers, contains no personal absolute path markers, and names the write-freeze, manifest, transform, cutover, observation, and final-removal gates.

- [ ] **Step 2: Run the documentation guard test and verify it fails before the plan exists**

Run:

```bash
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_phase2_migration_execution_plan.py'
```

Expected result before the plan file exists: FAIL with a missing document assertion.

- [ ] **Step 3: Add the Phase 2 migration execution plan**

Create this plan under `docs/multilingual/phase-2/migration-execution-plan.md` and include the required gates, PR sequence, validation commands, and non-goals.

- [ ] **Step 4: Run architecture baseline tests**

Run:

```bash
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
```

Expected result: all tests pass.

- [ ] **Step 5: Commit PR 2.0**

Run:

```bash
git add docs/multilingual/phase-2/migration-execution-plan.md tools/architecture-baseline/tests/test_phase2_migration_execution_plan.py
git commit -m "docs: add phase 2 migration execution plan"
```

### PR 2.1: Migration Schema And Private Artifact Guard

**Files:**

- Create: `lingotrace/migration/schema.py`
- Create: `lingotrace/migration/private_artifacts.py`
- Create: `tests/lingotrace/migration/test_schema.py`
- Create: `tests/lingotrace/migration/test_private_artifacts.py`

- [ ] **Step 1: Write schema tests for the final manifest**

Cover required keys: `source_vault`, `target_vault`, `source_manifest`, `target_manifest`, `preserve_data`, `recreate_from_pack`, `transform_with_map`, `remove_after_cutover`, `excluded_with_user_approval`, `conflicts`, and `verification_report`.

- [ ] **Step 2: Write private artifact guard tests**

Assert that public reports reject personal absolute-path markers, user names, source Vault absolute paths, target Vault absolute paths, and real migration artifact paths. Assert that Vault-relative paths and synthetic fixture paths are accepted.

- [ ] **Step 3: Implement schema validation and private path rejection**

Use standard-library `dataclasses`, `json`, `pathlib`, and `re`. Return `CommandReport` findings with deterministic codes:

- `migration_manifest_missing_key`
- `migration_manifest_invalid_classification`
- `migration_manifest_invalid_comparison_strategy`
- `private_path_in_public_report`
- `personal_absolute_path_rejected`

- [ ] **Step 4: Run runtime migration tests**

Run:

```bash
python -m unittest discover -s tests/lingotrace/migration -p 'test_*.py'
```

Expected result: all migration tests pass.

- [ ] **Step 5: Commit PR 2.1**

Run:

```bash
git add lingotrace/migration/schema.py lingotrace/migration/private_artifacts.py tests/lingotrace/migration/test_schema.py tests/lingotrace/migration/test_private_artifacts.py
git commit -m "feat: validate migration manifest schema"
```

### PR 2.2: Final Source Inventory Runner

**Files:**

- Create: `lingotrace/migration/source_inventory.py`
- Create: `tests/lingotrace/migration/test_source_inventory.py`

- [ ] **Step 1: Write inventory tests for explicit source binding**

Assert that the runner requires `source_vault`, `write_freeze_started_at`, and `output_dir`. Assert that it refuses to scan when source and target roots are the same.

- [ ] **Step 2: Write inventory classification tests**

Use synthetic fixtures for `preserve-data`, `recreate-from-pack`, `transform-with-map`, `temporary-migration`, `remove-after-cutover`, and `excluded_with_user_approval`. Assert unclassified files create blocking findings.

- [ ] **Step 3: Implement read-only source inventory**

The runner may read the source tree and write a private artifact only to the provided private output directory. It must not write into the source Vault, target Vault, or public repository.

- [ ] **Step 4: Run source inventory tests**

Run:

```bash
python -m unittest tests.lingotrace.migration.test_source_inventory
```

Expected result: all source inventory tests pass.

- [ ] **Step 5: Commit PR 2.2**

Run:

```bash
git add lingotrace/migration/source_inventory.py tests/lingotrace/migration/test_source_inventory.py
git commit -m "feat: add final source inventory runner"
```

### PR 2.3: Target Vault Rehearsal Runner

**Files:**

- Create: `lingotrace/migration/target_rehearsal.py`
- Create: `tests/lingotrace/migration/test_target_rehearsal.py`

- [ ] **Step 1: Write target rehearsal tests**

Assert that the target rehearsal uses `plan_japanese_vault_initialization`, records `recreate-from-pack` assets, and blocks existing target conflicts.

- [ ] **Step 2: Write pack-version binding tests**

Assert generated target context binds `target_language=ja`, `explanation_language=zh`, `language_pack=lingo-japanese`, and `language_pack_version=0.1.0`.

- [ ] **Step 3: Implement target rehearsal report**

Return a `CommandReport` with planned target system assets, conflict files, and no `changed_files` in rehearsal mode.

- [ ] **Step 4: Run target rehearsal tests**

Run:

```bash
python -m unittest tests.lingotrace.migration.test_target_rehearsal
```

Expected result: all target rehearsal tests pass.

- [ ] **Step 5: Commit PR 2.3**

Run:

```bash
git add lingotrace/migration/target_rehearsal.py tests/lingotrace/migration/test_target_rehearsal.py
git commit -m "feat: add target vault rehearsal report"
```

### PR 2.4: Data Copy And Transform Preview

**Files:**

- Create: `lingotrace/migration/copy_plan.py`
- Create: `lingotrace/migration/transform_plan.py`
- Create: `tests/lingotrace/migration/test_copy_plan.py`
- Create: `tests/lingotrace/migration/test_transform_plan.py`

- [ ] **Step 1: Write copy-plan tests**

Assert preserved entries copy by relative path, retain `content_hash`, reject path traversal, reject target system asset collisions, and report missing source assets as conflicts.

- [ ] **Step 2: Write transform-plan tests**

Assert transforms require a non-empty explicit map, before/after values, reason, preview result, conflict status, and acceptance result. Assert cosmetic renaming is rejected without user approval.

- [ ] **Step 3: Implement copy and transform preview**

Preview functions produce planned writes and conflicts only. Real writes require a later explicit apply command and all acceptance checks passing.

- [ ] **Step 4: Run copy and transform tests**

Run:

```bash
python -m unittest tests.lingotrace.migration.test_copy_plan tests.lingotrace.migration.test_transform_plan
```

Expected result: all copy and transform tests pass.

- [ ] **Step 5: Commit PR 2.4**

Run:

```bash
git add lingotrace/migration/copy_plan.py lingotrace/migration/transform_plan.py tests/lingotrace/migration/test_copy_plan.py tests/lingotrace/migration/test_transform_plan.py
git commit -m "feat: add migration copy and transform preview"
```

### PR 2.5: Comparator And Workflow Acceptance

**Files:**

- Create: `lingotrace/migration/verification.py`
- Create: `lingotrace/migration/workflow_acceptance.py`
- Create: `tests/lingotrace/migration/test_verification.py`
- Create: `tests/lingotrace/migration/test_workflow_acceptance.py`

- [ ] **Step 1: Write verification tests**

Assert comparison strategies cover `content_hash`, `frontmatter_and_body`, `links_and_hashes`, and `field_aware`. Assert failed hash, missing attachment, unresolved link, SRS mismatch, missing user approval, and unclassified entry block acceptance.

- [ ] **Step 2: Write workflow acceptance tests**

Use synthetic fixtures to verify the five Japanese workflow capabilities: `listening_notes`, `source_notes`, `review_materials`, `speaking_cards`, and `review_rollover`.

- [ ] **Step 3: Implement verification reports**

Produce a deterministic `verification_report` with counts for preserved entries, recreated entries, transformed entries, excluded entries, unresolved conflicts, missing approvals, failed comparisons, and final accepted status.

- [ ] **Step 4: Run verification and workflow acceptance tests**

Run:

```bash
python -m unittest tests.lingotrace.migration.test_verification tests.lingotrace.migration.test_workflow_acceptance
```

Expected result: all verification and workflow acceptance tests pass.

- [ ] **Step 5: Commit PR 2.5**

Run:

```bash
git add lingotrace/migration/verification.py lingotrace/migration/workflow_acceptance.py tests/lingotrace/migration/test_verification.py tests/lingotrace/migration/test_workflow_acceptance.py
git commit -m "feat: add migration verification and workflow acceptance"
```

### PR 2.6: Cutover And Observation Runbook

**Files:**

- Create: `docs/multilingual/phase-2/cutover-runbook.md`
- Create: `docs/multilingual/phase-2/read-only-observation-runbook.md`
- Create: `tools/architecture-baseline/tests/test_phase2_cutover_runbooks.py`

- [ ] **Step 1: Write runbook guard tests**

Assert the runbooks require owner approval, green verification report, no unresolved conflicts, no missing approvals, target daily-use smoke checks, rollback path, read-only observation entry, and separate final-removal confirmation.

- [ ] **Step 2: Add cutover runbook**

Document the exact sequence: freeze source writes, generate final source manifest, initialize target, migrate preserved data, apply approved transforms, compare manifests, run five workflow checks, request owner acceptance, switch daily entry points, and keep rollback available.

- [ ] **Step 3: Add read-only observation runbook**

Document the observation period: old Vault read-only, no new source writes, target Vault handles daily learning, missing assets are copied through recorded migration fixes, and final removal requires separate user confirmation.

- [ ] **Step 4: Run architecture baseline tests**

Run:

```bash
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
```

Expected result: all architecture baseline tests pass.

- [ ] **Step 5: Commit PR 2.6**

Run:

```bash
git add docs/multilingual/phase-2/cutover-runbook.md docs/multilingual/phase-2/read-only-observation-runbook.md tools/architecture-baseline/tests/test_phase2_cutover_runbooks.py
git commit -m "docs: add phase 2 cutover runbooks"
```

## 6. Real Migration Runbook Gates

These gates apply after the public tooling PRs are merged. They are operational gates, not public PR merge gates.

### Gate A: Pre-Freeze Readiness

Required evidence:

- latest `main` has green `Public File Allowlist` and `Japanese Baseline`
- runtime tests pass locally
- source Vault root is explicit
- target Vault root is explicit
- target root is empty or contains only accepted scaffold conflicts
- private artifact output directory is outside the public repository
- user understands that source writes will pause during final manifest generation

Gate result:

- Pass: start write freeze.
- Block: continue daily use in the source Vault and resolve missing evidence.

### Gate B: Final Source Manifest

Required evidence:

- source writes are paused
- final source manifest exists as a private artifact
- every source entry is classified
- no unclassified entries remain
- every excluded entry has explicit user approval
- every transform has an explicit map
- personal absolute paths are absent from public reports

Gate result:

- Pass: initialize or rehearse target Vault.
- Block: keep source frozen only as long as practical; if resolution is not immediate, unfreeze source and restart the final manifest later.

### Gate C: Target Migration Preview

Required evidence:

- target context binds one Japanese language pack
- system assets are planned as `recreate-from-pack`
- preserve-data writes are relative-path safe
- target collisions are reported
- approved transforms produce deterministic preview records
- no real writes happen from preview commands

Gate result:

- Pass: apply accepted migration operations.
- Block: resolve conflicts and rerun preview.

### Gate D: Verification And Workflow Acceptance

Required evidence:

- source and target manifests exist as private artifacts
- preserved bytes, fields, links, attachments, and SRS values compare successfully
- generated pack assets match expected release artifacts
- five Japanese workflow checks pass on the target Vault
- no unknown language fallback is used
- old runtime entry points are no longer required for daily use

Gate result:

- Pass: request owner cutover acceptance.
- Block: fix target or rerun accepted migration operations.

### Gate E: Cutover Acceptance

Required evidence:

- owner accepts the migration report
- target Vault handles daily learning entry points
- rollback path is documented
- old Vault can move to read-only observation

Gate result:

- Pass: switch daily use to the target Vault and start read-only observation.
- Block: keep daily use on the source Vault.

### Gate F: Read-Only Observation

Required evidence:

- old Vault is read-only
- no new learning data is written to the old Vault
- target Vault handles real daily workflows
- missing assets discovered during observation are copied through recorded migration fixes
- old framework is not revived as a runtime fallback

Gate result:

- Pass: request separate final-removal or archive confirmation.
- Block: continue observation and resolve recorded issues.

## 7. Required Verification Commands

Every public Phase 2 PR must run:

```bash
python -m unittest discover -s tests/lingotrace -p 'test_*.py'
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
python -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
python -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
python -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
git diff --check
git diff --cached --check
bash tools/git/check-public-staged-files.sh
```

For PRs that touch migration code, also run:

```bash
python -m unittest discover -s tests/lingotrace/migration -p 'test_*.py'
```

Before opening or updating a PR, check that no private artifacts are staged:

```bash
git diff --cached --name-only
bash tools/git/check-public-staged-files.sh
```

## 8. Phase 2 Completion Gate

Phase 2 migration execution is complete only when all of the following are true:

- target Japanese Vault has an explicit accepted Vault context
- final source and target manifests are complete private artifacts
- all preserved private learning data has hash, field-aware, link, attachment, and SRS comparison evidence
- all transforms have approved maps and accepted preview records
- all exclusions have explicit user approval
- no unclassified entries remain
- no unresolved conflicts remain
- all five Japanese workflows pass on the target Vault
- target daily-use entry points no longer require old `jp-*` runtime entries
- old Vault is in read-only observation after owner acceptance
- public docs no longer instruct target users to operate the old framework
- final old Vault deletion or archival is handled only after separate user confirmation

Phase 2 completion does not mean English support has shipped. It means the Japanese migration has been accepted and daily use can run on the new framework.
