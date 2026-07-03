# Phase 2 Read-Only Observation Runbook

This runbook defines the observation period after cutover. It verifies that the new target Vault can carry daily Japanese learning while the old Vault remains available as historical reference only.

Observation starts only after owner acceptance of the cutover result. It does not authorize final removal of the old Vault.

## Entry Conditions

Read-only observation may start only when:

- the cutover runbook has completed.
- owner acceptance remains valid for the target Vault.
- verification and workflow acceptance reports are green.
- daily entry points already point to the target Vault.
- the old Vault read-only rule has been announced.

## Operating Rules

During observation:

- Keep the old Vault read-only.
- Allow no new source writes in the old Vault.
- The target Vault handles daily learning, including new notes, review updates, listening notes, speaking cards, and review rollover.
- Do not copy ad hoc files from the old Vault into the target Vault.
- Do not revive old `jp-*` entry points as daily-use runtime.
- Do not delete or archive the old Vault during observation.

If a learner needs a missing asset from the old Vault, use a recorded migration fix. The fix must state the source entry, target entry, reason, comparison evidence, and whether verification or workflow acceptance needs to be rerun.

## Observation Checks

Run these checks during the observation period:

- target daily learning creates no writes in the old Vault.
- review rollover updates target review material only.
- listening notes and attachments open from the target Vault.
- source notes preserve source metadata in the target Vault.
- speaking cards remain manually reviewed before formal use.
- new migration fixes are reviewed and recorded.

Any failure blocks final removal and returns the affected asset to migration repair.

## Repair Rules

A recorded migration fix is required when observation finds:

- a missing attachment.
- an unresolved link.
- a preserved note missing from the target Vault.
- an SRS field mismatch.
- a transform that was not covered by the approved map.
- a user-approved exclusion that was recorded incorrectly.

After a recorded migration fix:

1. Update the private migration evidence.
2. Rerun the affected comparison or workflow acceptance check.
3. Keep owner acceptance pending if the fix changes daily-use behavior.
4. Continue observation only after the target Vault is green again.

## Exit Conditions

Observation can exit only when:

- the target Vault handles daily learning without source writes.
- no recorded migration fix remains open.
- verification and workflow acceptance remain green.
- the owner accepts the observation result.

Final removal requires separate user confirmation. This separate user confirmation must happen after observation exit and must name the exact removal action, such as archive old Vault, delete old Vault, or keep old Vault as historical reference.

Until final removal is confirmed, the old Vault remains read-only and available for audit.
