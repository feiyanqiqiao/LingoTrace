# Phase 0 Migration Scope And Asset Inventory

- Baseline commit: `a7ecbd8cb05241c5efc24938c37d1cb84b68d4e4`
- Baseline date: `2026-06-14`
- Inventory level: public paths and private data categories only
- Private filenames, counts, content, and absolute paths: excluded

The migration rule is: rebuild the system layer, preserve the data layer. Every known asset belongs to exactly one migration class below.

## Migration Classes

| Class | Meaning |
|---|---|
| `preserve-data` | Private learning data is copied with relative path and content preserved by default. |
| `recreate-from-pack` | The new core or Japanese pack creates the target version; the source copy is not migrated. |
| `transform-with-map` | A forced exception requires an explicit map, dry-run, change record, and acceptance evidence. |
| `temporary-migration` | A source scanner, copier, comparator, or adapter used only during migration and deleted after acceptance. |
| `remove-after-cutover` | Old framework or local runtime material is not copied and must no longer be used after cutover. |

## Preserve Data

| Data category | Default handling | Required evidence |
|---|---|---|
| personal daily and classroom notes | preserve relative path and bytes | source/target manifest and hash comparison |
| vocabulary, grammar, error, pronunciation, listening, and speaking cards | preserve path, Frontmatter, body, and review state | field-aware and content-hash comparison |
| audio, video, images, PDFs, and source attachments | preserve relative path and bytes | size and content-hash comparison |
| ListenKit transcript Markdown, structured transcript artifacts, and reviewed slice manifests | preserve when referenced by learning data | reference and hash comparison |
| generated learning slices referenced by notes | preserve relative path and non-empty content | embed resolution and hash comparison |
| Wikilinks, embeds, source backlinks, and comparison links | preserve without rewriting when relative paths remain valid | link-resolution report |
| `review_stage`, `next_review`, `last_reviewed`, `done_today`, history counts, and status | preserve exactly | SRS field comparison |
| manually curated sentences, examples, explanations, accent confirmations, and review reflections | preserve exactly | body and field comparison |
| Japanese data fields and `jp/` tags still owned by the Japanese pack | preserve as official Japanese schema | field inventory and language-pack declaration |

## Recreate From Pack

| Current public asset | Target handling | Reason |
|---|---|---|
| `系统配置/paths.json` | generate from explicit new Vault configuration and Japanese defaults | target paths must be explicit and must not inherit source discovery behavior |
| `系统配置/模板/**` | instantiate from the Japanese pack, then preserve later user edits | templates are system assets, not private learning records |
| `系统配置/复习流程.md` | generate current user guidance from the release | prevents stale old-entry instructions |
| `学习系统/总训练.base` | generate from core and Japanese pack declarations | dashboard fields depend on target contracts |
| target `AGENTS.md` or equivalent Vault guidance | generate from the new release | new entry points and ownership rules must replace old paths |
| Vault context and language-pack pin | create explicitly during initialization | no target-language guessing is allowed |
| Japanese pack Skills, validators, resources, and default views | install from the Japanese pack | old `jp-*` project copies are migration sources, not target runtime files |

## Transform With Map

No transform is allowed merely for naming consistency. A file enters this class only when one of these conditions is proven:

- its path escapes the target Vault or collides with a generated system asset;
- a Wikilink or embed cannot resolve under preserved relative paths;
- a source field conflicts with a core-reserved field;
- a target configuration contract requires a structural change;
- a user explicitly approves a content or path conversion.

Every transform record must include source path, target path, reason, old value, new value, preview result, conflict status, and acceptance result. Japanese fields such as `reading`, `accent_display`, `meaning_zh`, `kanji_diff`, and `kanji_diff_pairs` are not transforms; they remain Japanese-pack data.

Potentially allowlisted transforms:

| Asset | Constraint |
|---|---|
| selected Obsidian plugin settings | copy only explicitly reviewed files; never overwrite the entire target `.obsidian` directory |
| path collisions with generated templates or configuration | move only through an approved path map and update all affected references |
| invalid or ambiguous source links | stop the affected file and require a recorded resolution |

## Temporary Migration

These tools do not exist yet and must be kept in one removable migration module during Phase 1:

- source Vault inventory and risk scanner;
- include/exclude classifier;
- data copier with dry-run support;
- explicit field/path transformer;
- source and target manifest generator;
- hash, Frontmatter, Wikilink, attachment, and SRS comparator;
- old/new five-workflow comparison harness;
- source-side adapter only where required to read old configuration.

The independent acceptance oracle defined in PR B may remain as a test and audit tool, but it must not start the old framework or become a runtime compatibility layer.

## Remove After Cutover

| Current asset or pattern | Final handling |
|---|---|
| the source Vault's embedded `.git` directory and public repository checkout | keep the public repository outside the target Vault; do not copy the embedded checkout |
| `codex-skills/jp-*` old entry paths and installed-copy synchronization scripts | use only as migration evidence or temporary source entry; remove after workflow parity is accepted |
| `tools/listening-transcribe-official/**` old Vault-coupled renderer location | replace with core/Japanese-pack ownership in Phase 1; do not copy as a target Vault tool directory |
| `tools/vault-structure/**` old in-place layout migration | retain only in source history; do not use it to create the new Vault |
| old wrappers that assume the public repository is inside the Vault | replace with the shared external runtime |
| implicit language detection, historical path fallback, or Japanese default fallback | prohibit in the target runtime |
| local virtual environments, caches, `__pycache__`, temporary transcription files, and generated debug output | exclude from migration |
| full source `.obsidian` state, workspaces, and transient plugin data | exclude unless an individual setting file is explicitly allowlisted as a transform |
| old public documentation that instructs users to invoke removed entry points | update or delete before final release |

## Public Repository Coverage

The current tracked public tree is covered as follows:

- repository metadata and `docs/**`: remain in the external public repository; the embedded source-Vault copy is `remove-after-cutover`;
- `.github/**`: remains public-repository automation and is not copied into the target Vault;
- `codex-skills/**`: `remove-after-cutover` as old entry paths, with learning semantics rebuilt in the Japanese pack;
- `tools/listening-transcribe-official/**`: `remove-after-cutover` from the target Vault and rebuilt under target ownership;
- `tools/vault-structure/**`: historical evidence only, `remove-after-cutover` from the target Vault;
- `tools/git/**`: remains public-repository governance and is not a Vault asset;
- `系统配置/**`: `recreate-from-pack`;
- `学习系统/总训练.base`: `recreate-from-pack`.

## Phase 2 Final Inventory

This document does not freeze live private data. At the start of the Phase 2 migration window, the source Vault must briefly stop writes and generate a private final source manifest. Every source entry must be copied, recreated, transformed, excluded by rule, or explicitly excluded with user approval. Unclassified entries block cutover.
