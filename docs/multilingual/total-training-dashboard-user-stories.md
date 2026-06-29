# Multilingual Total Training Dashboard User Stories and Acceptance Tests

Status: `Reference Guidance`

Maturity path: `Reference Guidance -> Candidate Contract -> Enforced Contract`

Related guidance index: [Language Pack Capability Guidance](language-pack-capability-guidance.md)

## Purpose

This document defines the user-facing behavior that must survive changes to total-training dashboards across language packs. A total-training dashboard is a language-pack-owned Obsidian Base view backed by ordinary review-card frontmatter.

The rule is simple: dashboard behavior is not considered stable until it has a user story, acceptance criteria, and regression coverage.

## Applicability

All language packs that provide a total-training dashboard should index, reference, and satisfy this document before the dashboard is considered complete.

This document is a shared contract for:

- Reading review-card frontmatter directly.
- Avoiding generated review-state snapshots or parallel state stores.
- Showing a focused daily review queue.
- Keeping checkbox interactions stable.
- Preserving a clear boundary between review settlement and dashboard maintenance.
- Keeping reusable pack templates aligned with deployed vault views.
- Testing dashboard behavior as a contract, not just checking that template files exist.

Language packs must provide their own card-type display mapping. The Japanese fields in this document are the current reference mapping, not mandatory field names for English or future language packs.

## Ownership Boundary

Core owns:

- Language-pack manifest loading.
- Recreate-from-pack artifact handling.
- Vault-relative path and write-guard primitives.

Language packs own:

- Dashboard templates such as `lingotrace/packs/<language>/views/total-training.base`.
- Language-specific fields used by dashboard formulas.
- Card-type display rules.
- Pack-level dashboard regression tests.

Agents own:

- Intent recognition for ambiguous total-training requests.
- Recognizing local settlement phrases such as "更新总训练表" and "请更新总训练表" as review rollover, not dashboard maintenance.
- Choosing review rollover versus dashboard/view maintenance before writing.
- Reporting dashboard changes in user-facing language.

## Agent Use Cases

### 1. Clear Review Settlement Request

Examples:

- "结算复习"
- "结算总训练表"
- "更新总训练表"
- "请更新总训练表"
- "今天复习结束了，帮我结算"

Expected agent behavior:

- Treat the request as review rollover, not dashboard maintenance.
- Run internal preview first.
- If preview is accepted and has no errors, apply immediately without a second user confirmation.
- Run a second preview and report changed card counts, transition summary, blocked files, and verification result.
- Do not edit `total-training.base` as part of settlement.

### 2. Clear Dashboard/View Maintenance Request

Examples:

- "优化总训练表显示"
- "调整今日总训练的列"
- "词汇卡要显示重音和常见搭配"
- "语法卡核心内容显示中文意思，说明显示接续"

Expected agent behavior:

- Treat the request as dashboard/view maintenance.
- Inspect the current Base template before editing.
- Update the relevant language-pack template and, when explicitly working in the active vault, keep the deployed vault view aligned.
- Validate the Base YAML and run dashboard contract tests.
- Do not change review-card SRS frontmatter such as `done_today`, `review_stage`, `next_review`, or `last_reviewed`.

### 3. Ambiguous Total-Training Request

Examples:

- "处理一下总训练表"
- "看看总训练表"
- "总训练表有点问题"

Expected agent behavior:

- Ask one short clarification question before writing.
- Offer the two likely intents: review settlement or dashboard/view maintenance.
- Treat "更新总训练表" and "请更新总训练表" as clear review settlement requests.
- If context clearly describes columns, filters, display text, formulas, or sorting, choose dashboard/view maintenance.

### 4. Dashboard Bug Report

Examples:

- "done_today 勾选好像影响了旁边的行"
- "今日总训练显示了已经复习过的卡"
- "词汇卡没有显示常见搭配"
- "语法卡显示的内容不对"

Expected agent behavior:

- Reproduce or inspect the current Base behavior from the template and representative card frontmatter.
- Fix the dashboard contract, not the underlying review state, unless the evidence shows card data is wrong.
- Preserve the stable row-targeting pattern: `file.name` first, `done_today` second, deterministic sorting, and fixed filename width.
- Add or update regression tests for the reported behavior.

### 5. Review-State or Snapshot Regression Report

Examples:

- "views/review-state 又出现了"
- "总训练表是不是还在读 review-state.json"
- "是不是又生成了一份临时卡片"

Expected agent behavior:

- Confirm the dashboard reads real card frontmatter directly.
- Remove or ignore generated snapshot surfaces from runtime behavior.
- Do not reintroduce `views/review-state` as an intermediate dashboard source.
- Add a regression check if the Base template or workflow references review-state snapshots.

## User Stories

### 1. Show Today's Review Queue

As a learner, I want the daily review view to show only active cards due today or by the next day, so the table stays focused on the immediate review loop.

Acceptance criteria:

- The Base scans Markdown review cards through frontmatter, not generated snapshot notes.
- The global scope includes the language pack's configured review tracks.
- The daily review view filters on `formula.next_day_flag == true`.
- A card already reviewed today is not shown again through the next-day flag.

Japanese reference:

- The daily review view is named `今日总训练`.
- The Japanese scope includes class review, survival speaking, listening, and pronunciation tracks.

Regression coverage:

- Existing: `test_total_training_view_has_single_canonical_source`.
- Required: parse the Base template and assert the `next_day_flag` formula and daily-review-view filter.

### 2. Keep Checkbox Interaction Stable

As a learner, I want checking `done_today` to affect the intended card, so review completion does not accidentally update a neighboring row.

Acceptance criteria:

- `file.name` remains the first column in the daily review view.
- `done_today` remains the second column.
- `file.name` has a stable width limit.
- Sorting remains deterministic and ends with `file.name`.

Regression coverage:

- Existing: `test_total_training_view_has_single_canonical_source`.
- Required: assert the daily review view order begins with `file.name`, then `done_today`, and `columnSize.file.name == 260`.

### 3. Surface Type-Specific Review Cues

As a learner, I want the same two compact columns to show the most useful review cue for each card type, so the table stays narrow but still useful.

Acceptance criteria:

- Each language pack defines the display mapping for its own card types and fields.
- The dashboard keeps a compact primary cue column and a compact supporting cue column.
- Missing language-specific fields fall back to stable generic fields instead of leaving unreadable blank cells.

Japanese reference mapping:

- The primary cue column is `核心内容`.
- The supporting cue column is `说明`.
- Vocabulary cards show accent-marked text in `核心内容` and prefer `collocations` in `说明`.
- Grammar cards show `meaning_zh` in `核心内容` and `formation` in `说明`.
- Error cards show `correct_form` in `核心内容` and `wrong_form` in `说明`.
- Speaking cards show `jp_text` in `核心内容` and use `meaning_zh` plus `reply_hint` in `说明`.
- Listening cards prefer `daily_use_sentences` in `核心内容` and use `practice_focus` or `weak_points` in `说明`.
- Pronunciation cards show `target_text` in `核心内容` and `issue_tags` in `说明`.

Regression coverage:

- Existing: `test_total_training_dashboard_surfaces_type_specific_review_cues`.
- Required: strengthen the test from string presence to parsed formula-contract assertions for each card type.

### 4. Fall Back Gracefully When Optional Fields Are Missing

As a learner, I want the table to remain readable even when a card is missing optional display fields, so incomplete cards do not break the dashboard.

Acceptance criteria:

- Each language pack defines fallback order for every displayed card type.
- Fallbacks should end in stable generic fields such as headword/title/file name.
- Formula fields should use null-safe `if(...)` guards or the equivalent supported by the Base format.

Japanese reference fallback mapping:

- Vocabulary cards without `collocations` fall back to `meaning_zh`.
- Vocabulary cards without `accent_display` fall back to `headword`, then `file.name`.
- Grammar cards without `meaning_zh` fall back to `pattern`.
- Listening cards without `daily_use_sentences` fall back to `practice_focus`, then `file.name`.

Regression coverage:

- Required: formula-contract tests covering missing optional fields through synthetic expression fixtures or template assertions.

### 5. Keep Dashboard Source of Truth on Card Frontmatter

As a maintainer, I want the total-training dashboard to read real card frontmatter directly, so the system does not reintroduce duplicate snapshot notes or stale review-state exports.

Acceptance criteria:

- The Base template does not reference `views/review-state`.
- The dashboard does not depend on `.lingotrace/review-state/*.json`.
- The displayed state fields remain ordinary card frontmatter fields such as `done_today`, `next_review`, `review_stage`, `last_reviewed`, and `status`.

Regression coverage:

- Existing: `test_total_training_view_has_single_canonical_source`.
- Required: assert no `review-state` path references exist in the Base template.

### 6. Preserve Intent Boundary Between Settlement and View Maintenance

As a learner, I want the agent to distinguish review settlement from dashboard editing, so local settlement phrases update review state while display-change requests edit the dashboard.

Acceptance criteria:

- Clear settlement requests run review rollover.
- "更新总训练表" and "请更新总训练表" are clear settlement requests.
- Clear dashboard requests update the Base template or view behavior.
- Other ambiguous total-training requests require a short clarification before writing.
- Dashboard maintenance must not hand-edit review-card SRS state.

Regression coverage:

- Existing: intent-recognition checks in `test_phase25_switch_completion`.
- Required: docs/skill tests that preserve the settlement-versus-dashboard clarification rule.

### 7. Keep Pack Template and Real Vault View Aligned

As a maintainer, I want the reusable pack template and the deployed vault view to stay aligned, so future initialization or recreation does not lose dashboard behavior.

Acceptance criteria:

- The pack template is the canonical reusable source.
- The real vault Base should be recreated from or compared with the pack template during maintenance.
- Template changes should include regression tests before being merged.

Regression coverage:

- Existing: manifest declares `total_training_dashboard` as a recreate-from-pack default view.
- Required: test that the manifest path exists and the template contains the required formulas, properties, and daily review view.

## Test Matrix

| Behavior | Reference Japanese coverage | Required next coverage |
| --- | --- | --- |
| Canonical dashboard template exists | `test_pack_owned_surfaces_are_manifest_declared_and_files_exist` | Keep |
| Single source and stable filename column | `test_total_training_view_has_single_canonical_source` | Add parsed order/width assertions |
| Type-specific cues | `test_total_training_dashboard_surfaces_type_specific_review_cues` | Upgrade to formula-contract assertions |
| Today/next-day queue filtering | Partial template coverage | Add parsed `next_day_flag` and daily-view-filter assertions |
| Optional-field fallbacks | None | Add synthetic formula-contract or template assertions |
| No review-state snapshots | Partial architecture docs | Add direct Base-template assertion |
| Intent boundary | Intent-recognition tests | Keep and mention dashboard maintenance explicitly |

## Language-Pack Implementation Checklist

Before adding a total-training dashboard to a new language pack:

- Declare the dashboard artifact in the language-pack manifest.
- Create a pack-owned `views/total-training.base` template.
- Define the review-card roots or query scope used by the dashboard.
- Reuse shared review-state fields such as `status`, `done_today`, `review_stage`, `next_review`, and `last_reviewed`.
- Define language-specific display mapping for each supported `item_type`.
- Define fallback order for optional fields.
- Preserve stable row targeting: file identity first, `done_today` second, deterministic sorting.
- Add dashboard contract tests mapped to this document.
- Keep agent instructions clear about settlement versus dashboard/view maintenance.

## Maintenance Rule

When changing any language pack's `total-training.base`, update this document or that pack's linked dashboard contract and add or adjust a regression test in the same change. If the change affects user-facing dashboard behavior, test the dashboard contract, not only the presence of strings in the template.
