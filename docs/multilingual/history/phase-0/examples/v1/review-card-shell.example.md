# Review Card Shell Example

This is a synthetic Phase 0 example. It separates core lifecycle fields from Japanese language-pack extensions.

```yaml
core_fields:
  - track
  - item_type
  - status
  - priority
  - done_today
  - review_stage
  - next_review
  - last_reviewed
  - first_seen
  - last_seen
  - seen_count
  - error_count
  - source_notes
language_fields:
  - headword
  - reading
  - accent_display
  - meaning_zh
  - kanji_diff
  - kanji_diff_pairs
unknown_language_fields: preserve
example_frontmatter:
  track: class_review
  item_type: vocab
  status: active
  priority: normal
  done_today: false
  review_stage: day0
  next_review: 2026-01-02
  last_reviewed: ""
  first_seen: 2026-01-01
  last_seen: 2026-01-01
  seen_count: 1
  error_count: 0
  source_notes:
    - "[[Learning/Sources/example-source]]"
  headword: 例
  reading: れい
  accent_display: れい①
  meaning_zh: 例子
  kanji_diff: false
  kanji_diff_pairs: []
```
