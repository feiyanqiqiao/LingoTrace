# Phase 0 To Phase 1 Entry Gate

Phase 1 starts only when Phase 0 evidence and contracts are merged and reviewed. Passing this gate allows detailed design and implementation planning for the new framework. It does not approve English functionality, real migration, or production cutover.

## Required Inputs

- [ ] PR A is merged: current Japanese state, migration inventory, and risk baseline are recorded.
- [ ] PR B is merged: Japanese Baseline tests and manual review cases are available.
- [ ] PR C is merged: architecture contracts, language-pack checklist, migration contract, old-framework exit checklist, and examples are available.
- [ ] The `Japanese Baseline` workflow passes on `main`.
- [ ] Referenced public paths in Phase 0 documents exist.
- [ ] No Phase 0 document contradicts the current five `SKILL.md` workflow descriptions.
- [ ] The conformance checklist can be converted into Phase 1 tests without adding new product decisions.
- [ ] The migration contract and old-framework exit checklist are confirmed by maintainers before runtime work begins.

## Required Decisions

- [ ] The core contract is limited to lifecycle, provenance, path roles, validation, version handling, and shared failure rules.
- [ ] The Japanese language pack owns templates, Japanese fields, dictionaries, pronunciation and accent behavior, naturalness rules, and current Japanese workflow semantics.
- [ ] The new Vault initialization work is separate from data migration work.
- [ ] The temporary migration module is separate from runtime.
- [ ] English work remains blocked until the core/Japanese boundary is accepted.

## Blocked Work Before This Gate

- no English functionality
- no real migration
- no daily-use cutover
- no old Vault deletion
- no new runtime fallback to Japanese behavior
- no broad field rename of Japanese learning data
- no public commit containing private learning notes, media, generated transcripts, or personal review records

## Phase 1 Work Categories

Every Phase 1 task must be assigned to exactly one category:

- core
- Japanese language pack
- new Vault initialization
- temporary migration
- external adapter boundary
- public documentation

Tasks that touch more than one category need an explicit dependency order and review checkpoint before implementation.

## Phase 1 Output Requirement

Phase 1 must produce a detailed design and implementation plan before code changes that affect runtime behavior. The plan must preserve the Phase 0 rule: rebuild the system layer, preserve the data layer, and exit the old framework after acceptance.
