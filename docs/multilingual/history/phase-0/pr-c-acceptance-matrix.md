# Phase 0 PR C Acceptance Matrix

This matrix maps the PR C acceptance criteria from `docs/lingotrace_multilingual_phase0_implementation_plan.md` to concrete Phase 0 evidence. It is a review aid, not a Phase 0 completion claim.

Phase 0 PR C remains contract-only. It does not implement runtime loading, new Vault initialization, real migration, English functionality, daily-use cutover, or old-framework removal.

## Status Vocabulary

| Status | Meaning |
|---|---|
| Covered by PR C | The branch contains the requested contract, example, or test evidence. |
| External review required | Maintainers and Zheng Jie must explicitly accept the gate before Phase 1 starts. |
| Out of PR C scope | The item belongs to Phase 1, Phase 2, or overall Phase 0 completion rather than PR C document output. |

## Matrix

| ID | PR C acceptance criterion | Evidence | Status |
|---|---|---|---|
| AC-01 | All contract fields, capabilities, and responsibilities have a unique owner. | `architecture-contracts.md` defines Vault context fields, fixed capability IDs, core review-card fields, a Contract Ownership Matrix, and a demand ownership table. `test_contract_examples.py` checks the fixed fields and ownership markers. | Covered by PR C |
| AC-02 | Version incompatibility, missing capability, and external tool failure have explicit failure rules. | `architecture-contracts.md` defines stop conditions for missing Vault context, version mismatch, missing capability, ambiguous target language, and external tool failure. `japanese-language-pack-manifest.example.md` declares `minimum_required` and `failure_policy: stop_before_write`. | Covered by PR C |
| AC-03 | Examples align with the overall plan but do not pretend to be implemented formats. | `japanese-vault-context.example.md`, `japanese-language-pack-manifest.example.md`, `review-card-shell.example.md`, and `japanese-migration-manifest.example.md` state they are synthetic Phase 0 examples. `architecture-contracts.md` includes an Implementation Gap Register, and `phase-1-entry-gate.md` blocks runtime work, real migration, English functionality, daily-use cutover, and old Vault deletion. | Covered by PR C |
| AC-04 | Contract example consistency tests pass. | `tools/architecture-baseline/tests/test_contract_examples.py` checks required documents, YAML fences, fixed capability IDs, maturity values, Vault context, review-card shell, migration manifest fields, exit checklist gates, and private path markers. | Covered by PR C |
| AC-05 | The language-pack conformance checklist covers identity, capabilities, fields, paths, versions, and external tools. | `language-pack-conformance-checklist.md` covers identity and versions, capabilities, pack-owned surface, core boundary, Japanese pack minimum, and evidence links. | Covered by PR C |
| AC-06 | The Japanese migration contract defines source, target, include, exclude, transform, conflict, manifest, and acceptance rules. | `japanese-migration-contract.md` defines explicit source and target Vaults, preserve/recreate/transform/remove/exclude/conflict categories, source and target manifests, hash or field-aware comparison strategy, verification report, final source manifest, and acceptance. `japanese-migration-manifest.example.md` shows the corresponding synthetic structure. | Covered by PR C |
| AC-07 | The old-framework exit checklist covers old entry points, implicit config, historical path fallback, temporary migration code, public docs, and old Vault handling. | `old-framework-exit-checklist.md` includes old repository topology, old `codex-skills/jp-*` entries, installed-copy sync scripts, configless Japanese detection, historical path fallback, temporary migration adapters, public docs, read-only observation, explicit user confirmation, and archived old Vault handling. | Covered by PR C |
| AC-08 | The demand ownership table can classify representative core, Japanese, temporary migration, exit, and external-tool demands. | `architecture-contracts.md` includes the demand ownership decision table and Contract Ownership Matrix, covering private data, old Japanese entries, language-pack-owned fields and templates, external adapters, candidate core, and core-candidate-only demands. | Covered by PR C |
| AC-09 | Current implementation, Skills, and target contracts have no unresolved behavior conflict; target gaps are registered as future work. | `current-state-baseline.md`, `baseline-discrepancies.md`, `migration-scope-and-asset-inventory.md`, and `architecture-contracts.md` separate current implementation from target architecture and register target runtime, language-pack loading, new Vault initialization, migration tooling, English work, and cutover as later-stage gaps. | Covered by PR C |
| AC-10 | Project maintainers and Zheng Jie approve the Phase 1 entry gate. | `phase-1-entry-gate.md` requires project maintainers and Zheng Jie approval before implementation starts. PR #21 remains draft until that review happens. | External review required |

## Non-Completion Notes

PR C acceptance is not the same as full Phase 0 completion. Overall Phase 0 still requires PR A, PR B, and PR C merged to `main`, `Japanese Baseline` green on `main`, and maintainer confirmation of the Phase 0 evidence set.

The matrix intentionally keeps AC-10 as External review required. That status is not a defect in the PR C documents; it is the explicit human decision gate before Phase 1.
