# LingoTrace Architecture Baseline

This directory contains the executable architecture and Japanese behavior baseline retained by the current runtime.

It uses only synthetic public fixtures. It must not copy, anonymize, or derive from private Vault notes, media, study statistics, or personal paths.

## Scope

The baseline covers:

- fixed listening-note structure and slice references;
- flexible source-note provenance;
- review-material routing and preservation expectations;
- survival-speaking card admission and duplicate handling;
- next-day review rollover behavior through the current deterministic updater;
- synthetic migration acceptance rules for preserve, recreate, transform, remove, and conflict cases.

The tests characterize current Japanese learning semantics and public workflow contracts. Runtime implementation tests remain under `tests/lingotrace/`.

## Structure

```text
tools/architecture-baseline/
  fixtures/                      synthetic public data only
  tests/                         unittest contract checks
  manual-language-review-cases.md
```

`tests/helpers.py` is test-only code. Existing runtime scripts and Skills must not import it.

## Local Verification

Use Python 3.14 for local verification:

```bash
python3 -m unittest discover -s tests/lingotrace -p 'test_*.py'
python3 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
python3 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
python3 -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```
