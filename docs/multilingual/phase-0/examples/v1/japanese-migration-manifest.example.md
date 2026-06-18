# Japanese Migration Manifest Example

This is a synthetic Phase 0 example. It illustrates classification, not real private data.

```yaml
manifest_version: phase0-example-v1
source_vault: source-japanese-vault
target_vault: target-japanese-vault
source_manifest:
  generated_after_write_freeze: true
  entries:
    - path: Learning/Review/example-card.md
      classification: preserved
      content_hash: sha256:source-example
target_manifest:
  entries:
    - path: Learning/Review/example-card.md
      classification: preserved
      content_hash: sha256:target-example
preserve_data:
  - category: review_cards
    source: Learning/Review
    target: Learning/Review
    compare: frontmatter_and_body
    content_hash: required_when_bytes_should_match
  - category: media
    source: Media
    target: Media
    compare: hash
    content_hash: required
  - category: source_artifacts
    source: Learning/Sources
    target: Learning/Sources
    compare: links_and_hashes
recreate_from_pack:
  - vault_context
  - path_config
  - templates
  - default_views
  - japanese_pack_skills
transform_with_map:
  - source: OldConfig/custom-view.base
    target: Config/views/custom-view.base
    reason: reviewed_target_config_location
    before: OldConfig/custom-view.base
    after: Config/views/custom-view.base
    dry_run: pass
    preview_result: no_link_or_hash_change
    conflict_status: resolved
    accepted_by_user: true
    acceptance_result: accepted
remove_after_cutover:
  - embedded_public_repo
  - old_jp_entrypoints
  - temporary_migration_adapters
excluded_with_user_approval:
  - path: Archive/obsolete-example.md
    reason: user_confirmed_not_learning_data
    approved_by: vault_owner
conflicts:
  - path: Learning/Review/example-conflict.md
    status: blocked
    reason: target_path_collision
verification_report:
  preserved_count: 3
  recreated_count: 5
  transformed_count: 1
  removed_count: 3
  excluded_with_user_approval_count: 1
  failed_comparison_count: 0
  unclassified_entry_count: 0
  missing_user_approval_count: 0
  unresolved_conflicts: 1
  acceptance_result: blocked_until_conflict_resolution
```
