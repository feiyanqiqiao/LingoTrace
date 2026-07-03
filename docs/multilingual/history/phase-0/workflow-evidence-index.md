# Phase 0 Workflow Evidence Index

- Baseline commit: `a7ecbd8cb05241c5efc24938c37d1cb84b68d4e4`
- Baseline date: `2026-06-14`
- Private data: excluded

Evidence references use repository-relative public paths and stable section or symbol names rather than line numbers.

## Evidence Sources

| Evidence ID | Public source | Evidence type |
|---|---|---|
| `EV-LISTEN-SKILL` | `codex-skills/jp-listening-script-generator/SKILL.md` | declared workflow, output, preservation, and failure rules |
| `EV-LISTEN-WRAPPER` | `codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh` | observable entry and ListenKit delegation |
| `EV-LISTEN-TOOL` | `tools/listening-transcribe-official/transcribe_listening.py` | deterministic rendering and validation implementation |
| `EV-LISTEN-TESTS` | `tools/listening-transcribe-official/tests/test_transcribe_listening.py` | 74 executable characterization tests |
| `EV-LISTEN-README` | `tools/README.md` | public operator contract and slice consistency rules |
| `EV-SOURCE-SKILL` | `codex-skills/jp-source-note-generator/SKILL.md` | declared flexible-note and provenance rules |
| `EV-SOURCE-WRAPPER` | `codex-skills/jp-source-note-generator/scripts/prepare-source-note-material.sh` | observable material preparation entry |
| `EV-REVIEW-SKILL` | `codex-skills/jp-review-material-maintainer/SKILL.md` | declared Focus/Base, routing, schema, and update rules |
| `EV-VOCAB-TEMPLATE` | `系统配置/模板/单词卡模板.md` | vocabulary structure and Japanese fields |
| `EV-GRAMMAR-TEMPLATE` | `系统配置/模板/课堂语法卡模板.md` | grammar structure |
| `EV-TEMPLATE-INDEX` | `系统配置/模板/录入模板索引.md` | error, speaking, listening, and pronunciation templates |
| `EV-SPEAK-SKILL` | `codex-skills/jp-survival-speaking-card-generator/SKILL.md` | declared card admission and maintenance rules |
| `EV-SPEAK-VALIDATOR` | `codex-skills/jp-survival-speaking-card-generator/scripts/validate-survival-speaking-cards.sh` | read-only observable validation boundary |
| `EV-ROLLOVER-SKILL` | `codex-skills/jp-next-day-review-updater/SKILL.md` | declared end-of-day contract |
| `EV-ROLLOVER-CODE` | `codex-skills/jp-next-day-review-updater/scripts/update_next_day_review.py` | deterministic SRS and pending-write implementation |
| `EV-ROLLOVER-TESTS` | `codex-skills/jp-next-day-review-updater/tests/test_update_next_day_review.py` | 8 executable characterization tests on the updated PR A branch; 6 existed at the initial baseline commit |
| `EV-PATHS` | `系统配置/paths.json` | current path-role configuration |
| `EV-REVIEW-FLOW` | `系统配置/复习流程.md` | current human-facing review schedule |
| `EV-DAILY-TEMPLATE` | `系统配置/模板/每日学习清单模板.md` | checklist structure |
| `EV-VAULT-CODE` | `tools/vault-structure/validate_vault_structure.py` | current path, link, and layout validation |
| `EV-VAULT-TESTS` | `tools/vault-structure/tests/` | 18 executable structure and migration tests on the updated PR A branch; 16 existed at the initial baseline commit |

## Behavior Mapping

| Behavior IDs | Primary evidence | Current executable coverage |
|---|---|---|
| `JP-LISTEN-001` to `JP-LISTEN-008` | `EV-LISTEN-SKILL`, `EV-LISTEN-WRAPPER`, `EV-LISTEN-TOOL`, `EV-LISTEN-README` | `EV-LISTEN-TESTS`; semantic selection still needs manual cases |
| `JP-SOURCE-001` to `JP-SOURCE-006` | `EV-SOURCE-SKILL`, `EV-SOURCE-WRAPPER` | no dedicated characterization suite at baseline |
| `JP-REVIEW-001` to `JP-REVIEW-009` | `EV-REVIEW-SKILL`, templates, `EV-PATHS` | path roles via `EV-VAULT-TESTS`; sink behavior via `EV-ROLLOVER-TESTS`; remaining maintenance behavior needs PR B fixtures |
| `JP-SPEAK-001` to `JP-SPEAK-005` | `EV-SPEAK-SKILL`, `EV-SPEAK-VALIDATOR`, `EV-TEMPLATE-INDEX` | validator is observable; dedicated fixture tests are absent |
| `JP-ROLLOVER-001` to `JP-ROLLOVER-006` | `EV-ROLLOVER-SKILL`, `EV-ROLLOVER-CODE`, `EV-REVIEW-FLOW` | `EV-ROLLOVER-TESTS` |

## Baseline Commands

```bash
/usr/bin/python3 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
```

Initial result at the PR A baseline commit: 74 listening tests, 6 rollover tests, and 16 Vault-structure tests passed.

Result after updating PR A onto `main` commit `4cd72448ecdaec3eefb091dd9c7fb52c7f66816a`: 74 listening tests, 8 rollover tests, and 18 Vault-structure tests passed.

PR B must rerun the same suites and the new architecture-baseline suite with Python 3.14 in GitHub Actions. The PR A local result is a starting-point check, not the future required status check.
