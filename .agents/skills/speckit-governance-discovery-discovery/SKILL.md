---
name: speckit-governance-discovery-discovery
description: Collect and review the mandatory Discovery snapshot before upstream specification
  authoring
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: SpecKitReference maintainers
  source: extension:governance-discovery
---

# Governance Discovery Discovery Skill

# Discovery protocol

Use this command for a substantive feature before `speckit.specify`. Read the request, current repository, constitution, existing related specifications, and project governance documents before asking the user about facts that the repository can establish.

The user input is:

```text
$ARGUMENTS
```

Extract `feature_id=<id>` from the input. Accept only lowercase letters, digits, and hyphens; reject an empty value, path separators, `.` segments, or a value that does not correspond to the feature directory selected by the upstream workflow. Set `FEATURE_DIR=specs/<id>` and `EVIDENCE_DIR=docs/spec-kit/features/<id>`. Refuse if either resolved path escapes the project root or reaches a symlinked ancestor. Create only `EVIDENCE_DIR` when it is safe and absent.

Do not create `spec.md`, `plan.md`, `tasks.md`, `.specify/**`, source code, a review approval, or a fabricated user decision.

## Discovery ledger

Create or revise `EVIDENCE_DIR/DISCOVERY.md`. Preserve user-confirmed content from an existing file. Do not overwrite a reviewed snapshot without explaining the changed facts and requesting another review.

The file must use the following sections and classifications:

```markdown
# Scope and business outcome

## Confirmed facts

## User decisions

## Assumptions pending approval

## Open questions

## Actors and journeys

## Data lifecycle and ownership

## Failure, recovery, and edge cases

## Security, privacy, and compliance

## Scale, platform, accessibility, and localization constraints

## Dependencies and degraded modes

## Scope boundaries and deferred work

## Acceptance, release gate, and evidence
```

For every listed item, prefix the classification exactly as one of `CONFIRMED_FACT`, `USER_DECISION`, `ASSUMPTION_PENDING_APPROVAL`, `OPEN_QUESTION`, `OUT_OF_SCOPE`, or `DEFERRED_WITH_OWNER`.

## Interview rules

Ask about one logical topic per turn. Rank unanswered topics by impact on product scope, security, data handling, public interfaces, acceptance, and release. You may recommend a choice, but record a recommendation as an assumption until the user explicitly decides. Do not use an industry default to decide product behavior, security exceptions, data retention, or release scope.

Continue the discovery conversation until all exit criteria are met, or the user explicitly accepts a recorded assumption and risk. A user asking for a plan is not itself approval of an unreviewed Discovery snapshot.

## Exit criteria and handoff

Before requesting review, verify and report each item:

- no blocking `OPEN_QUESTION` remains;
- high-impact assumptions are approved, explicitly accepted with risk, or excluded;
- at least one primary journey has a Given/When/Then skeleton;
- in-scope, out-of-scope, and deferred work are distinct;
- acceptance evidence and failure behavior are definable.

When all criteria hold, summarize the snapshot, its path, unresolved non-blocking risks, and the exact next approval object: `DISCOVERY` for `docs/spec-kit/features/<id>/DISCOVERY.md`. Stop for the workflow's human review gate. Do not write `REVIEW_LEDGER.json`; only the manager may append user approval evidence.
