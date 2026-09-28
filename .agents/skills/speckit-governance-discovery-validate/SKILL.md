---
name: speckit-governance-discovery-validate
description: Run feature validation and produce evidence without claiming final approval
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: SpecKitReference maintainers
  source: extension:governance-discovery
---

# Governance Discovery Validate Skill

# Feature validation

The user input is:

```text
$ARGUMENTS
```

Extract and validate `feature_id=<id>` as described by `speckit.governance-discovery.discovery`. Read the approved task package, implementation evidence, relevant contracts, and project validation instructions. Do not change approval evidence, task definitions, or upstream artifacts merely to make a check pass.

Run the approved verification commands and any mandatory project validation. Record command, exit status, concise result, and evidence path in `docs/spec-kit/features/<id>/VALIDATION_REPORT.md`. Redact secrets, credentials, and personal data. If validation fails, report the failure with the owning task or requirement, then return to remediation; do not continue to convergence or completion review.

If validation passes, report the evidence path and residual risks. Passing validation proves only the checks that ran. It is not a user approval, a release authorization, or permission to suppress an unresolved requirement.
