# Phase 0 Old Framework Exit Checklist

The final state keeps one new framework, one Japanese language pack, and one migrated Japanese Vault. It does not keep the old framework as a supported mode.

This checklist records exit obligations. It does not authorize deletion by itself.

## Exit Candidates

- [ ] Embedded public repository checkout inside the source Japanese Vault is no longer used as runtime.
- [ ] Old `codex-skills/jp-*` paths are no longer daily entry points.
- [ ] Old installed-copy synchronization scripts are not part of target operation.
- [ ] Old path fallback and configless Japanese detection are removed from target workflows.
- [ ] Old wrappers that assume the public repository is inside the Vault are replaced by shared runtime entry points.
- [ ] Old Vault-coupled listening renderer location is replaced by core or Japanese-pack ownership.
- [ ] Old in-place Vault structure migration scripts are no longer needed for target Vault creation.
- [ ] Temporary migration adapters are deleted or marked outside runtime after acceptance.
- [ ] Daily learning entry points, scheduled jobs, and external-tool wrappers point to the new Vault and new framework.
- [ ] Public docs no longer instruct users to invoke removed entry points.

## Data Safety Before Exit

- [ ] Source and target manifests are complete.
- [ ] Preserved learning data has hash or field-aware comparison evidence.
- [ ] Referenced attachments and slice files resolve in the target Vault.
- [ ] SRS fields match the accepted migration report.
- [ ] Manual notes, curated sentences, examples, and reflections are preserved.
- [ ] Known conflicts are resolved or explicitly excluded with user approval.

## Read-Only Observation

After target acceptance, the old Vault enters read-only observation. During this period:

- no new learning data is written to the old Vault
- the target Vault handles daily learning
- any missing asset discovered in the old Vault is copied through a recorded migration fix, not by reviving the old framework

## Final Removal

Final removal requires explicit user confirmation after read-only observation. Without confirmation, the old Vault remains archived and untouched.

The public repository may still keep historical evidence documents and tests. It must not keep operational instructions that require the old framework after cutover.
