# Japanese Language Pack Manifest Example

This is a synthetic Phase 0 example. It describes declared ownership; it is not a loaded runtime manifest.

```yaml
language_pack_id: lingo-japanese
language_pack_version: 0.1.0
target_language: ja
transcription_locale: ja-JP
compatible_core: ">=0.1.0 <0.2.0"
compatible_vault_schema: "draft-v1"
capabilities:
  - id: listening_notes
    maturity: stable
    depends_on:
      - external_media_adapter
  - id: source_notes
    maturity: stable
    depends_on:
      - external_media_adapter
  - id: review_materials
    maturity: stable
    depends_on: []
  - id: speaking_cards
    maturity: stable
    depends_on:
      - review_materials
  - id: review_rollover
    maturity: stable
    depends_on:
      - review_materials
external_tools:
  - id: external_media_adapter
    tool: ListenKit
    minimum_required:
      transcript_markdown: true
      structured_transcript: true
      deterministic_slice_export: true
    failure_policy: stop_before_write
templates:
  - listening_note
  - source_note
  - vocab_card
  - grammar_card
  - error_card
  - survival_speaking_card
skills:
  - listening_notes
  - source_notes
  - review_materials
  - speaking_cards
  - review_rollover
validators:
  - japanese_review_card_validator
  - japanese_speaking_card_validator
resources:
  - accent_dictionary
  - tokenizer_dictionary
language_fields:
  - headword
  - reading
  - accent_display
  - meaning_zh
  - kanji_diff
  - kanji_diff_pairs
  - jp_text
  - scene
  - function
  - speaker_role
item_types:
  - vocab
  - grammar
  - error
  - pronunciation
  - sentence
tag_namespace: jp
default_path_roles:
  focus_vocab_root: Learning/Review/Vocabulary
  base_vocab_root: Learning/Base/Vocabulary
  grammar_root: Learning/Review/Grammar
  error_root: Learning/Review/Errors
  listening_root: Learning/Listening
  speaking_root: Learning/Speaking
```
