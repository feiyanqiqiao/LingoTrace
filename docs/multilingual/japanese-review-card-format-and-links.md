# Japanese Review Card Format and Link Contract

Status: `Enforced Japanese Pack Contract`

This document defines the public card-format and link-safety behavior implemented by `lingotrace.packs.japanese.workflows:review_materials`.

## Creation And Update Boundary

- Structured `item` input creates new vocabulary, grammar, error, and pronunciation cards after role-scoped duplicate checks.
- New queued cards receive complete scheduling metadata: `review_status`, `priority`, `done_today`, first/last-seen dates, counters, `review_stage`, `next_review`, `last_reviewed`, source links, and tags.
- Applying any mutation to an existing card requires `existing_update_confirmed=True`.
- Confirmed structured-item updates preserve the existing semantic frontmatter and body. They may append verified provenance and update lifecycle metadata.
- A full existing-card reformat must use an explicitly confirmed `card` payload. No bulk migration is implied.
- Discovery previews continue to recognize readable legacy cards without requiring the complete new-card schema; strict metadata validation remains mandatory for every newly written or fully reformatted card.
- Reappearing error cards and explicitly marked grammar or vocabulary weaknesses reset to `day0`, clear `done_today` and `last_reviewed`, and increment occurrence/error counters without replacing manual body content.
- Full `card` payloads require a non-empty readable body and a safe bounded Vault-relative Markdown path.

## Rendered Card Shapes

### Vocabulary

Vocabulary cards follow the review-facing shape established by `溢れる`:

- `## 快速复习` for meaning, reading, and high-value collocations;
- optional `## 核心` for accent and part of speech;
- optional `## 例句` for structured Japanese examples and short Chinese support;
- optional `## 易错 / 易混` for verified comparison cards or confusion notes;
- optional `## 待补卡` for unresolved comparison names;
- optional `## 来源` for verified provenance links.

### Grammar

Grammar cards follow the structure established by `〜ようだ`:

- `# <pattern>` and `## 快速复习`;
- optional register and usage-scene guidance;
- optional core-nuance explanation;
- formation, usage branches, and examples grouped under `## 接续、用法与例句`;
- optional verified contrasts, unresolved pending cards, and source provenance.

Optional sections are omitted when reliable content is unavailable. A direct user entry with no source note records `用户直接录入；大模型整理` instead of inventing provenance.

### Error

Error cards follow the wrong/correct contrast established by the 2026-07-14 `たとえ言葉に出していないとしても` card:

- `## 错误句`;
- `## 正确句`;
- `## 为什么错`;
- `## 下次怎么避免`.

Optional `wrong_focus` and `correct_focus` values must each match exactly one substring. The renderer uses Obsidian `==highlight==` syntax and blocks ambiguous focus input.

## YAML Contract

- Booleans and counters remain typed YAML values.
- Dates use `YYYY-MM-DD`.
- Source notes, tags, formations, collocations, and card relations are YAML lists.
- Text scalars and list entries are deterministically quoted when needed, including colons, brackets, quotes, line breaks, Japanese punctuation, wikilinks, numeric-looking values, dates used as text, and YAML implicit words such as `yes` or `on`.
- Existing unknown or nested frontmatter is preserved during confirmed lifecycle-only updates.

## Link Resolution Contract

`source_note` remains compatible with both a Vault-relative path and a wikilink. `source_notes` accepts a list. Both normalize to extensionless Vault-relative links.

Resolution order:

1. An input containing a path is checked as an exact Vault-relative path.
2. A filename-only input is searched inside its allowed path roles.
3. A result is accepted only when exactly one note matches.

Source provenance is required when supplied. Missing, ambiguous, malformed, out-of-role, percent-encoded, or self-referential source input blocks preview and apply.

Optional card relations use narrower roles:

- vocabulary comparisons: focus and base vocabulary roles;
- grammar contrasts: grammar role;
- error relations: declared review-material roles;
- pronunciation relations: accent and phoneme roles.

A unique relation is rendered as `[[vault/relative/path|friendly label]]`. A missing or ambiguous optional relation is omitted from frontmatter, kept as plain text under `## 待补卡`, and reported through warning findings plus the `unresolved_related_items` artifact. The workflow never guesses a target or emits a dangling relation wikilink.

Canonical links are compared by the complete Vault-relative target. Two notes with the same filename in different directories remain distinct. A pathless legacy link is considered equivalent to a canonical source only when it uniquely resolves inside the allowed source roles; ambiguous legacy links are preserved as manual text while the verified canonical source is appended.

New generated filenames reject control characters plus `#`, `|`, `[`, `]`, and `^` because those characters break files or change Obsidian link semantics. Long generated names use a readable bounded prefix plus a deterministic digest, while the complete display text remains in semantic frontmatter and the card body. Caller-supplied full-card paths reject traversal and oversized filename components before the core write guard runs.
