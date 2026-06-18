# LingoTrace Architecture Baseline

This directory contains the Phase 0 PR B executable Japanese baseline.

It uses only synthetic public fixtures. It must not copy, anonymize, or derive from private Vault notes, media, study statistics, or personal paths.

## Scope

The baseline covers:

- fixed listening-note structure and slice references;
- flexible source-note provenance;
- review-material routing and preservation expectations;
- survival-speaking card admission and duplicate handling;
- next-day review rollover behavior through the current deterministic updater;
- synthetic migration acceptance rules for preserve, recreate, transform, remove, and conflict cases.

The tests characterize current Japanese learning semantics. They do not implement the multilingual runtime, language-pack loading, new Vault initialization, or real private data migration.

## Structure

```text
tools/architecture-baseline/
  fixtures/                      synthetic public data only
  tests/                         unittest contract checks
  manual-language-review-cases.md
```

`tests/helpers.py` is test-only code. Existing runtime scripts and Skills must not import it.

## Local Verification

Use Python 3.14 for the final PR B gate:

```bash
BASELINE_PYTHON="${LINGOTRACE_BASELINE_PYTHON:-/opt/homebrew/bin/python3.14}"
"$BASELINE_PYTHON" -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

## PR B Boundary

PR B may add tests, synthetic fixtures, this documentation, the `Japanese Baseline` GitHub Actions workflow, and the exact public allowlist entry for this directory.

PR B must not change user-visible Japanese workflow behavior. If a new characterization test exposes a real behavior defect, keep the failing evidence and fix the behavior in a separate pull request.
