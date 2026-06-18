# Phase 0 Baseline Discrepancies

- Baseline commit: `a7ecbd8cb05241c5efc24938c37d1cb84b68d4e4`
- Baseline date: `2026-06-14`
- Private data: excluded

## Resolution Rules

- `implementation-gap`: target behavior is not implemented yet and is assigned to a later phase.
- `behavior-discrepancy`: runtime behavior conflicts with the accepted current workflow.
- `contract-conflict`: two current authorities require mutually exclusive behavior.
- `documentation-drift`: prose or evidence links lag behind unchanged runtime behavior.

PR C cannot merge while a `behavior-discrepancy` or `contract-conflict` remains unresolved.

## Register

| ID | Type | Finding | Resolution | Status |
|---|---|---|---|---|
| `DISC-001` | `documentation-drift` | `jp-review-material-maintainer` listed the primary sink fields but omitted `kanji_diff` and `kanji_diff_pairs`; the rollover implementation and tests already preserve and merge them. | Update the Sink Flow prose in PR A without changing runtime behavior. | resolved in PR A |
| `DISC-002` | `implementation-gap` | Flexible source-note behaviors have no dedicated public characterization fixtures or validator tests. | Add synthetic source-note contract fixtures and tests in PR B. | assigned to PR B |
| `DISC-003` | `implementation-gap` | Review maintenance has executable sink coverage but no dedicated public tests for Focus-first search, Base reactivation, routing, and card structure. | Add synthetic contract fixtures and structural checks in PR B; do not create a new production abstraction. | assigned to PR B |
| `DISC-004` | `implementation-gap` | Speaking-card validation exists only as a Vault-oriented shell validator and has no isolated public fixture suite. | Add synthetic speaking-card contract fixtures and tests in PR B. | assigned to PR B |
| `DISC-005` | `implementation-gap` | Current runtime has no explicit Vault context, language-pack manifest, capability declaration, or version negotiation. | Define non-runtime contract examples in PR C; implement only in Phase 1. | assigned to PR C and Phase 1 |
| `DISC-006` | `implementation-gap` | The public workflow only enforces the private-file allowlist; the Japanese baseline is not a required GitHub status check. | Add `Japanese Baseline` workflow in PR B using Python 3.14, then configure the required check. | assigned to PR B |
| `DISC-007` | `implementation-gap` | Current `jp-*` Skills, installed-copy synchronization, implicit Japanese behavior, and Vault-embedded repository topology are old-framework mechanisms. | Treat them as migration evidence or temporary source-side entry points only; list their deletion conditions in PR C. | assigned to PR C and Phase 2 |
| `DISC-008` | `implementation-gap` | Current Vault layout migration tooling predates the new-Vault migration decision and can move or rewrite system layout in place. | Keep it as historical evidence only. New Japanese migration tooling must be separately designed in Phase 1 and must target an initialized new Vault. | assigned to Phase 1 |
| `DISC-009` | `implementation-gap` | Current tests do not provide an independent source-to-target migration acceptance oracle for hashes, links, attachments, SRS fields, exclusions, and approved transforms. | Add a synthetic acceptance oracle in PR B and define the manifest contract in PR C. | assigned to PR B and PR C |

## Review Result

No unresolved `behavior-discrepancy` or `contract-conflict` was found at PR A baseline time. The current executable suites pass with the system Python runtime. The gaps above describe missing migration architecture or missing evidence; they are not reported as already implemented capabilities.
