# Language Pack Agent Handoff Template

Use this template when handing a new language-pack task to Codex, Claude Code, Trae, or another agent. Fill the bracketed values in the message you send to that agent.

## Handoff

Target language: `[language name and BCP-47 primary subtag]`

Explanation language: `[language name and BCP-47 primary subtag]`

Initial capabilities:

```text
source_notes
review_materials
review_rollover
```

Capabilities to mark unsupported unless explicitly approved:

```text
listening_notes
speaking_cards
```

Goal:

Create the first language-pack slice for `[target language]` without changing private Vault data and without reusing Japanese runtime behavior.

Allowed directories:

```text
lingotrace/packs/[language]/
tests/lingotrace/packs/
tools/architecture-baseline/tests/
docs/multilingual/
README.md
AGENTS.md
```

Forbidden directories:

```text
codex-skills/
学习系统/
系统配置/
.obsidian/
private Vault roots
media, transcript, cache, or generated study-output directories
```

Read first:

```text
docs/multilingual/language-pack-contributor-guide.md
docs/multilingual/language-pack-capability-guidance.md
docs/lingotrace_multilingual_architecture_plan.md
docs/multilingual/phase-0/language-pack-conformance-checklist.md
docs/multilingual/review-rollover-user-stories.md
docs/multilingual/total-training-dashboard-user-stories.md
lingotrace/packs/japanese/manifest.json
lingotrace/packs/japanese/agent_skills/SKILL.md
tests/lingotrace/packs/test_japanese_pack.py
```

Implementation rules:

- Do not edit private Vault data.
- Do not implement English support by reusing Japanese runtime.
- Do not fall back to Japanese workflow, Japanese dictionary, Japanese accent logic, Japanese paths, or Japanese tags.
- Do not copy Japanese fields mechanically. `reading`, `accent_display`, `kanji_diff`, and `kanji_diff_pairs` are Japanese-owned unless a separate design justifies equivalent fields for the target language.
- Declare unsupported capabilities with explicit user-facing reasons.
- Keep user interaction natural-language-first through `agent_skills/SKILL.md`.
- Route writes through the core write guard when implementing a workflow.
- Stop before writing if Vault context, capability declaration, path role, or external tooling is missing.
- Use `docs/multilingual/language-pack-capability-guidance.md` as the capability guidance index.
- For each implemented capability, state whether the relevant guidance is followed, not applicable, or a language-specific exception.
- Do not promote language-specific behavior into core unless it meets the guidance index's cross-language promotion rule.

Current infrastructure caveats:

- Core context is still Japanese-only and must be generalized before a real non-Japanese Vault can run.
- Vault initialization is still Japanese-specific and must become pack-driven before real non-Japanese initialization.
- Listening tooling is still Japanese-specific and must not be reused directly for another language.

Required checks:

```bash
python -m unittest discover -s tests/lingotrace -p 'test_*.py'
python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh
git diff --check
```

PR acceptance criteria:

- The PR states the target language and explanation language.
- The PR lists implemented and unsupported capabilities.
- The PR cites applicable capability guidance documents.
- The PR lists not-applicable guidance items or language-specific exceptions.
- The PR includes or updates `manifest.json`, `paths.json`, `fields.json`, and `agent_skills/SKILL.md` for the new pack.
- Unsupported capabilities include `failure_reason`.
- The Agent Skill contains natural user examples and does not ask users to say internal workflow names.
- No private Vault files, media, transcripts, generated notes, or cache files are committed.
- No runtime dependency on `lingotrace/packs/japanese` exists in the new pack.
- All required checks pass.
