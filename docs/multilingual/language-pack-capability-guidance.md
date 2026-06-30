# Language Pack Capability Guidance

Chinese version: [语言包能力指引](language-pack-capability-guidance.zh.md)

## Purpose

This index is the shared entry point for language-pack capability guidance. It helps different maintainers build language packs with the same user-facing standards, core boundaries, and testing expectations without treating the Japanese pack as code to copy.

These documents are guidance first. They can become stricter contracts only after multiple language packs prove the same behavior with stable tests.

## Maturity Levels

`Reference Guidance`

- A recommended standard for new language-pack work.
- New packs should read it, follow it where applicable, and document any differences.
- It does not block a PR by itself.

`Candidate Contract`

- A behavior has worked across at least two language packs or has a reviewed cross-language design.
- New packs should treat it as a required design target unless they document an exception.
- It should have pack-level tests or accepted manual review cases.

`Enforced Contract`

- A behavior is validated by core or conformance tests.
- New packs must satisfy it before claiming support for the capability.
- Exceptions require a reviewed contract change.

## How To Use This Index

Before starting or reviewing a language-pack PR:

- Identify the capabilities the pack implements or declares unsupported.
- Read the guidance for each implemented capability.
- In the PR description, list which guidance documents apply.
- Mark each item as followed, not applicable, or language-specific exception.
- Keep language-specific fields, templates, and naturalness rules inside the language pack.
- Do not move behavior into core until at least two language packs prove the same rule and the rule has a clear conformance path.

## Capability Guidance Map

| Area | Guidance status | Guidance file |
| --- | --- | --- |
| `review_rollover` | Reference Guidance | `docs/multilingual/review-rollover-user-stories.md` |
| `total_training_dashboard` | Reference Guidance | `docs/multilingual/total-training-dashboard-user-stories.md` |
| `listening_notes` | Planned Reference Guidance | `listening-notes-user-stories.md` is not created yet |
| `source_notes` | Planned Reference Guidance | `source-notes-user-stories.md` is not created yet |
| `review_materials` | Reference Guidance | `docs/multilingual/review-materials-user-stories.md` |
| `speaking_cards` | Planned Reference Guidance | `speaking-cards-user-stories.md` is not created yet |
| `agent_skill_policy` | Planned Reference Guidance | `agent-skill-policy-user-stories.md` is not created yet |

## Core Boundary Rule

Single-language behavior belongs in the language pack by default. This includes fields, templates, display rules, dictionary logic, pronunciation rules, source-note style, and agent wording.

A behavior can be proposed for core only when:

- at least two language packs need the same behavior;
- the shared behavior can be stated without language-specific fields;
- the behavior can be tested through core or conformance tests;
- the migration impact for existing packs is documented.

## PR Expectations

New language-pack PRs should state:

- implemented capabilities;
- unsupported capabilities and user-facing failure reasons;
- applicable guidance documents from this index;
- any not-applicable items;
- any language-specific exceptions;
- tests or manual review evidence for implemented behavior.

Existing pack changes should update the relevant guidance document when they change user-facing capability behavior.
