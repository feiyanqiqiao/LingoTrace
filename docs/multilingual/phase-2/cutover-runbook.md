# Phase 2 Cutover Runbook

This runbook defines the operational gate for switching daily Japanese learning from the source Vault to the new target Vault. It is used after the public Phase 2 migration tooling PRs are merged and after the project owner chooses a migration window.

It does not delete, archive, or mutate the old Vault by itself. It also does not approve English support or multi-target-language use in one Vault.

## Preconditions

Cutover may start only when all of the following are true:

- The source Vault and target Vault paths are explicit in the private migration command inputs.
- The source Vault is ready for a short write freeze.
- The target Vault has been initialized from the new core and Japanese pack.
- The final source manifest command, target rehearsal command, copy preview, transform preview, verification command, and workflow acceptance command are available.
- Every transform has an approved map, before value, after value, preview result, conflict status, and acceptance result.

## Required Gates

The cutover decision requires all of these gates:

- owner approval for the migration window and daily-use switch.
- green verification report from `migration-verification`.
- no unresolved conflicts in the final source manifest or verification report.
- no missing approvals for excluded entries or transforms.
- target daily-use smoke checks for the selected target Vault.
- rollback path documented before daily entry points are switched.
- read-only observation entry accepted by the owner.
- separate final-removal confirmation reserved for a later decision.

If any gate fails, stop the cutover and keep daily use on the source Vault.

## Cutover Sequence

Run these steps in order:

1. Announce the migration window and freeze source writes.
2. generate final source manifest from the explicit source Vault.
3. initialize target Vault from the new core and Japanese pack.
4. migrate preserved data using the accepted copy preview.
5. apply approved transforms using the accepted transform preview.
6. compare manifests with `migration-verification`.
7. run five workflow checks with `migration-workflow-acceptance`.
8. Run target daily-use smoke checks.
9. Request owner acceptance for the target Vault.
10. switch daily entry points to the target Vault.
11. Enter read-only observation entry for the old Vault.
12. Keep rollback available until the read-only observation period is accepted.

The five workflow checks are:

- fixed listening notes
- flexible source notes
- review material maintenance
- survival-speaking cards
- review rollover

## Target Daily-Use Smoke Checks

The target daily-use smoke checks confirm that the target Vault can support a normal learning day before the switch:

- open the target Vault context and confirm the target language is Japanese.
- create or preview one review material write through the new framework.
- open one listening note with its attachment evidence.
- open one source note with its source metadata.
- open one speaking card that has manual review evidence.
- run or preview review rollover without writing to the source Vault.

Smoke checks must not repair data silently. Any issue becomes a recorded migration fix or a blocked cutover finding.

## Rollback Path

The rollback path keeps the source Vault as the daily-use source until target acceptance is complete. If a cutover gate fails before daily entry points switch, continue using the source Vault and record the failed gate.

If a problem appears after daily entry points switch but before read-only observation is accepted:

- stop new writes to the target Vault if the issue risks data loss.
- keep the old Vault unchanged and readable.
- repair the target through a recorded migration fix.
- rerun verification and workflow acceptance before resuming.

Rollback does not mean reviving the old framework as the target runtime. It means delaying or reverting the daily-use switch until the new target passes the gates again.

## Cutover Evidence

The cutover record must include:

- source Vault identifier and target Vault identifier.
- final source manifest timestamp.
- verification report result.
- workflow acceptance report result.
- target daily-use smoke checks result.
- owner approval timestamp.
- rollback path summary.
- read-only observation entry timestamp.

The record stays outside the public repository if it contains private Vault paths, personal notes, media names, or study data.
