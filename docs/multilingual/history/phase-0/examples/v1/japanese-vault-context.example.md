# Japanese Vault Context Example

This is a synthetic Phase 0 example. It shows the shape of an explicit single-target-language Vault context and is not a runnable configuration file.

```yaml
vault_schema_version: draft-v1
target_language: ja
explanation_language: zh
language_pack: lingo-japanese
language_pack_version: 0.1.0
enabled_capabilities:
  - listening_notes
  - source_notes
  - review_materials
  - speaking_cards
  - review_rollover
paths:
  config_root: Config
  review_root: Learning/Review
  source_root: Learning/Sources
  media_root: Media
write_policy: fail_on_missing_capability
```
