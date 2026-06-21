# LingoTrace Phase 1 Contributor Guide

This guide explains how to contribute to the Phase 1 runtime skeleton after PR 1 through PR 4 have created real public entry points. It is a routing document for public repository work, not a user migration manual.

## Current Phase 1 Runtime

Phase 1 runtime work starts from these public entry points:

- `lingotrace/core`: shared runtime contracts for reports, Vault context, language manifests, capability checks, path roles, review-card shells, and guarded write plans.
- `lingotrace/packs/japanese`: Japanese language-pack boundary, including manifest declarations, field ownership, default path roles, templates, views, validators, and workflow declarations.
- `lingotrace/init/japanese_vault.py`: dry-run initializer for a new Japanese Vault scaffold.
- `lingotrace/migration`: temporary dry-run inventory and comparison helpers for later migration planning.

The old Japanese learning workflow still exists outside this new runtime skeleton, but new Phase 1 work should target the runtime package and its tests.

## Accepted PR Scopes

Keep Phase 1 changes narrow and dependency-aware:

- Core contract changes belong under `lingotrace/core` with matching tests under `tests/lingotrace/core`.
- Japanese pack declarations belong under `lingotrace/packs/japanese` with matching tests under `tests/lingotrace/packs`.
- Japanese Vault scaffold changes belong in `lingotrace/init/japanese_vault.py` with matching tests under `tests/lingotrace/init`.
- Migration inventory changes belong under `lingotrace/migration` with matching tests under `tests/lingotrace/migration`.
- Documentation changes should point to real files and commands that exist on `main`.

Do not combine core refactors, Japanese field migration, private data movement, and new language features in one PR.

## Blocked Scopes

These boundaries are deliberate:

- Do not start new runtime work from old `jp-*` entries.
- Old `jp-*` skills are migration evidence only.
- English support has not shipped in Phase 1.
- Real private data migration has not shipped in Phase 1.
- Daily-use cutover has not shipped in Phase 1.
- Old Vault deletion has not shipped in Phase 1.
- Old-framework removal has not shipped in Phase 1.

Unsupported work should fail explicitly instead of falling back to Japanese assumptions or guessing from paths, filenames, tags, or note content.

## Validation Commands

Run the runtime tests after changing Phase 1 code:

```bash
python -m unittest discover -s tests/lingotrace -p 'test_*.py'
```

Run the architecture contract tests after changing contracts, docs, or acceptance gates:

```bash
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
```

Run the existing Japanese baseline suites before opening or updating a PR:

```bash
python -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
python -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
python -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
```

Before committing public changes, verify staged files:

```bash
bash tools/git/check-public-staged-files.sh
```

Use the same command against a PR diff when reviewing remotely:

```bash
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

## Contributor Checklist

Before marking a Phase 1 PR ready:

- Confirm every referenced file path exists.
- Confirm runtime behavior has a matching test under `tests/lingotrace`.
- Confirm contract or documentation changes are covered by `tools/architecture-baseline`.
- Confirm public allowlist checks pass for the staged diff.
- Confirm the PR body states any deliberately unsupported capability.

Phase 1 is complete only after all five dependency-gated PRs are merged and `main` passes the runtime, architecture, Japanese baseline, and public allowlist checks.
