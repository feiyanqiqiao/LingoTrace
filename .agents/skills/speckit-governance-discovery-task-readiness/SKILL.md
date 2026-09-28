---
name: speckit-governance-discovery-task-readiness
description: Run the read-only task-package readiness audit before implementation
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: SpecKitReference maintainers
  source: extension:governance-discovery
---

# Governance Discovery Task Readiness Skill

# Task-package readiness

The user input is:

```text
$ARGUMENTS
```

Extract and validate `feature_id=<id>` as described by `speckit.governance-discovery.discovery`. Read `specs/<id>/spec.md`, `plan.md`, `tasks.md`, the Discovery snapshot, and the review ledger if present. Do not modify `.specify/**`, `specs/**`, native Agent files, source code, or the review ledger.

Invoke the project-local Reference manager's read-only `audit-feature-readiness --feature-dir docs/spec-kit/features/<id>` command when it is available and records a compatible companion capability. Capture its complete structured report in `docs/spec-kit/features/<id>/TASK_READINESS.json`; otherwise report `COMPANION_CAPABILITY_UNAVAILABLE` and stop before implementation. Do not invent a passing report.

The report must distinguish mechanical findings from semantic findings. Mechanical checks include task IDs, required tiny-model fields, safe exact paths, traceability, dependency cycles, verification commands, expected results, and hash-bound approval state. Semantic findings include hidden product decisions, untestable outcomes, conflicting instructions, or unspecified failure behavior.

If any error exists, request corrections to the task package and return to task authoring. If no error exists, report the exact `TASK_PACKAGE` review object: `tasks.md`, current readiness report, and traceability evidence. A validator pass is not human approval and must not start `speckit.implement`.
