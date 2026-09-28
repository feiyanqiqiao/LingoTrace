---
name: speckit-governance-discovery-cold-start-review
description: Request isolated cold-start validation of representative tiny-model tasks
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: SpecKitReference maintainers
  source: extension:governance-discovery
---

# Governance Discovery Cold Start Review Skill

# Cold-start review

The user input is:

```text
$ARGUMENTS
```

Extract and validate `feature_id=<id>` as described by `speckit.governance-discovery.discovery`. Read the latest task-readiness report and select at least three representative implementation tasks: one domain or data task, one UI or API integration task, and one migration, security, or failure-handling task. If a category is absent, select the highest-risk remaining task and state why.

For each selected task, prepare an isolated review packet containing only:

- the task's complete detail block;
- the task's explicitly declared read-only references;
- read-only repository access instructions.

Do not include the original conversation, a summary of undocumented design decisions, other task discussions, or approval credentials. Ask the independent reviewer to return exactly one of `EXECUTABLE`, `NEEDS_CONTEXT`, `HIDDEN_DECISION`, `CONFLICT`, or `UNVERIFIABLE` with concise evidence.

Write reviewer findings, selected task IDs, immutable artifact hashes, and any declared limitations to `docs/spec-kit/features/<id>/COLD_START_VALIDATION.json`. Do not record an approval. Any result other than `EXECUTABLE` makes the task package `CHANGES_REQUESTED`; return to task authoring and readiness audit. If every result is `EXECUTABLE`, report that the user must still approve the `TASK_PACKAGE` at the next human gate.
