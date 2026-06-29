# Language Pack Contributor Guide

This guide is for project members and external agents that build a new LingoTrace language pack. It is the short entry point before starting English, Korean, German, or any future language work.

The goal is to make a language pack understandable without reading the full migration history. Do not treat the Japanese pack as a folder to copy. Use it as a reference implementation for shape, tests, and boundaries.

Before designing or reviewing a capability, read [Language Pack Capability Guidance](language-pack-capability-guidance.md). Chinese readers can use [语言包能力指引](language-pack-capability-guidance.zh.md). It is the soft guidance index for capability-level user stories, current reference behavior, planned guidance, and future contract promotion.

## Runtime Boundary

LingoTrace has four layers:

| Layer | Owner | Responsibility |
| --- | --- | --- |
| core | public LingoTrace runtime | reports, manifest loading, capability checks, path roles, review shells, guarded writes |
| language pack | pack maintainer | language fields, templates, Agent Skill, validators, workflow facade, language resources |
| Vault config | private user library | selected target language, explanation language, selected pack, enabled capabilities, path overrides |
| private data | user | notes, cards, media, review state, daily records, manual edits |

New language work belongs in the language pack unless a behavior is proven useful across at least two languages and has a clear core contract. English experiments, language-specific templates, pronunciation rules, dictionaries, text cleanup, and naturalness rules must stay out of core.

## Required Pack Shape

Create new first-party language packs under:

```text
lingotrace/packs/<language>/
  manifest.json
  paths.json
  fields.json
  agent_skills/SKILL.md
  templates/
  views/
  validators.py
  workflows.py
```

Responsibilities:

- `manifest.json`: declares pack ID, version, target language, compatible core/schema range, capabilities, unsupported capabilities, external tools, templates, views, and workflow entrypoints.
- `paths.json`: declares default Vault-relative path roles for this language.
- `fields.json`: declares language-specific fields owned by the pack. These fields do not become core fields by default.
- `agent_skills/SKILL.md`: gives agents the natural-language operating entry for daily use. Users should not need to say internal function names or write modes.
- `templates/`: contains reusable note, card, checklist, or source templates owned by the pack.
- `views/`: contains reusable Obsidian Bases or other pack-owned views.
- `validators.py`: validates language-owned card and workflow data.
- `workflows.py`: exposes a stable facade for declared capabilities and must route file changes through the core write guard.

Do not place new runtime work in old root folders. Do not create private Vault files in the public repository.

## Capabilities And Maturity

The shared capability IDs come from `PHASE0_CAPABILITY_IDS`:

- `listening_notes`
- `source_notes`
- `review_materials`
- `speaking_cards`
- `review_rollover`

Pack-owned dashboard views, such as a total-training dashboard, are not workflow capability IDs, but they still need capability guidance and pack-level tests when provided.

A new pack does not need to implement all five capabilities in the first PR. The recommended first slice is:

- `source_notes`
- `review_materials`
- `review_rollover`

If a capability is not ready, declare it under `unsupported_capabilities` with a clear `failure_reason`. Do not leave it undeclared and do not silently fall back to Japanese behavior.

Use maturity deliberately:

- `stable`: available by default and covered by conformance tests or manual review cases.
- `experimental`: documented but not available by default.
- `unsupported`: explicitly unavailable with a user-readable reason.

Capability guidance uses a separate maturity path:

- `Reference Guidance`: recommended behavior that new packs should read and either follow or explain.
- `Candidate Contract`: behavior that has cross-language evidence and should be treated as a design target.
- `Enforced Contract`: behavior covered by core or conformance tests.

New language-pack PRs should cite applicable guidance documents and state any not-applicable items or language-specific exceptions.

## Japanese Reference Boundary

Do not copy Japanese fields mechanically into a new pack. Fields such as `reading`, `accent_display`, `kanji_diff`, and `kanji_diff_pairs` are Japanese-owned fields, not generic vocabulary fields.

If another language needs comparable concepts, design them in that pack using the target language's own learning model. For example, English may need pronunciation, stress, collocation, register, or usage fields, but those should not be named or shaped merely by copying Japanese pitch-accent and kanji comparison fields.

Do not fall back to Japanese runtime. A new pack must not depend on:

- Japanese workflow implementation.
- Japanese dictionary.
- Japanese accent logic.
- Japanese text cleanup rules.
- Japanese path names or tags.

When a capability is not ready, fail explicitly through `unsupported_capabilities` and `failure_reason`.

## Current Infrastructure Limits

The current public runtime is not yet fully pack-generic:

- core context currently accepts only `target_language=ja` and `explanation_language=zh`.
- initializer is still Japanese-specific through `lingotrace/init/japanese_vault.py`.
- listening tooling is still Japanese-specific and cannot be used directly for English, Korean, or German.
- `PHASE0_CAPABILITY_IDS` is reusable as the public capability set, but each pack can implement only a subset.
- migration tooling and target rehearsal still assume Japanese pack inputs unless explicitly generalized.

Before implementing a real non-Japanese pack, first plan the required core context and pack-driven initializer generalization. Do not work around these limits by hardcoding a second language into Japanese-specific modules.

## Agent Skill Requirements

Every pack must include `agent_skills/SKILL.md`.

The Agent Skill must:

- describe how users naturally ask for the language tasks;
- map those requests to declared capabilities;
- say what information the agent should ask for when input is missing;
- describe when to save immediately and when to confirm first;
- route actual writes through the declared workflow and core write guard;
- avoid asking users to say internal workflow names, function names, data envelopes, or write modes.

The Agent Skill is user-experience policy. It must not be a shell script, migration plan, or private Vault instruction.

## PR Rules

New language pack PRs must be narrow:

- one language per PR series;
- no private Vault data, media, transcripts, or generated study notes;
- no broad core refactor unless the PR is explicitly the core-generalization prerequisite;
- no Japanese data migration mixed with new language work;
- no fallback to Japanese runtime for unsupported capability behavior.

The PR body must state:

- target language and explanation language;
- implemented capabilities and unsupported capabilities;
- capability guidance documents followed;
- not-applicable guidance items or language-specific exceptions;
- user-facing Agent Skill examples;
- changed public files;
- validation commands and results.

Required checks:

```bash
python -m unittest discover -s tests/lingotrace -p 'test_*.py'
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh
git diff --check
```

If the PR changes listening, migration, or vault-structure tooling, also run the matching tool tests.
