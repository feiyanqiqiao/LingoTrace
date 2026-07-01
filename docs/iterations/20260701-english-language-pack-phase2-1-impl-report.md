# 英语包 Phase 2.1 实施报告

**实施日期**: 2026-07-01
**分支**: `feature/english-learning`
**基准**: V5 最终执行版（`20260701-english-language-pack-phase2-1-impl-plan-v5.md`）
**结果**: ✅ 全部 84 个测试通过

---

## 修改清单

### Core 层（3 文件）

| 文件 | 变更 | 行数 |
|---|---|---|
| `lingotrace/core/context.py` | `SUPPORTED_TARGET_LANGUAGE = "ja"` → `SUPPORTED_TARGET_LANGUAGES = ("ja", "en")`；`_parse_context` 改用 `not in` | +2 -2 |
| `lingotrace/core/capabilities.py` | `PHASE0_CAPABILITY_IDS` 追加 `"total_training_dashboard"` | +1 |
| `lingotrace/packs/english/manifest.json` | 新增 `total_training_dashboard` 能力声明；新增 `total_training_base` 模板声明；全部 4 个能力 maturity 改为 stable + 补齐 behavior_evidence | +27 -6 |

### 英语包层（4 文件 + 2 新建）

| 文件 | 变更 | 行数 |
|---|---|---|
| `lingotrace/packs/english/fields.json` | 追加 `english_definition` 字段 | +5 |
| `lingotrace/packs/english/agent_skills/SKILL.md` | 完整重写为 6 段式骨架（Intent Recognition + User Language Map + Operating Rules + 各能力行为描述） | +86 -7 |
| `lingotrace/packs/english/validators.py` | 完整实现：type-specific 字段校验 + stage 枚举前置阻断 + date 格式校验 | +90 -11 |
| `lingotrace/packs/english/workflows.py` | 完整实现：review_rollover 状态机（9 阶段记忆曲线 + 逾期惩罚）；Mastery Sink（`_en_base_vocab_sink_mutation`）；英语专属常量（`_EN_STABLE_BASE_VOCAB_KEYS`、`_ENGLISH_VOCAB_KEYS`、`ROLLOVER_ROLES`）；`_target_context_errors` 防腐校验 | +828 -21 |
| `lingotrace/packs/english/views/total-training.base` | **新建**：Obsidian Base 原生 4 段式 YAML（filters + formulas + properties + views），双视图（今日总训练 + 最近新增），4 种 item_type 完整显示映射 | +69 |
| `tests/lingotrace/packs/test_english_pack.py` | 扩展至 29 个测试（8 静态 + 6 workflow + 15 契约矩阵） | +650 -2 |

### Core 测试层（2 文件）

| 文件 | 变更 | 行数 |
|---|---|---|
| `tests/lingotrace/core/test_context.py` | 脏数据 `"en"` → `"fr"`（因 `"en"` 现为合法语言） | +1 -1 |
| `tests/lingotrace/core/test_capabilities.py` | 固定 ID 集合追加 `"total_training_dashboard"` | +1 |

---

## 测试结果

```
tests.lingotrace.core.test_context                       5  OK
tests.lingotrace.core.test_capabilities                  7  OK
tests.lingotrace.core.test_paths                         4  OK
tests.lingotrace.core.test_manifests                     4  OK
tests.lingotrace.core.test_mutations                     4  OK
tests.lingotrace.packs.test_japanese_workflow_previews  30  OK
tests.lingotrace.packs.test_english_pack                29  OK
─────────────────────────────────────────────────────────────
TOTAL                                                   84  OK
```

### 英语包测试明细

**静态测试（8）**:
- `test_manifest_loads_through_core_loader` — manifest 通过 core loader 加载
- `test_declared_capabilities_are_subset_of_phase0_ids` — 能力 ID 在 PHASE0 白名单内
- `test_unsupported_capabilities_have_fallback_none` — unsupported 能力声明 fallback: none
- `test_language_fields_are_english_pack_owned` — 英语字段不含日语专属字段
- `test_default_path_roles_match_phase1_design` — 路径角色对齐架构
- `test_workflow_stubs_do_not_reference_japanese_runtime` — 未引用日语包模块
- `test_pack_owned_surfaces_are_manifest_declared_and_files_exist` — 模板文件存在
- `test_total_training_dashboard_template_exists` — 看板模板存在

**Workflow 测试（6）**:
- `test_workflows_fail_explicitly_without_vault_root` — 无 vault_root 显式失败
- `test_listening_and_speaking_workflows_return_unsupported` — listening/speaking 返回 unsupported
- `test_source_notes_previews_without_writes` — source_notes preview 不修改文件
- `test_source_notes_apply_writes_target_file` — source_notes apply 写入目标文件
- `test_review_materials_previews_target_vault_without_writes` — review_materials preview 不修改文件
- `test_review_materials_item_creates_initialized_focus_vocab_card` — review_materials item 创建 focus vocab 卡片

**契约矩阵测试（15）**:
- `test_review_rollover_previews_due_target_card_without_writes` — US-1: 沙盒预览
- `test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply` — US-1: 二次预览零残留
- `test_review_rollover_apply_advances_due_target_card` — US-2: 阶段晋升
- `test_review_rollover_applies_every_memory_curve_transition_from_run_date` — US-2/US-4: 8 阶段完整记忆曲线
- `test_apply_updates_done_today_review_stage_next_review_and_mastered_status` — US-4: mastered 状态字段验证
- `test_review_rollover_reschedules_overdue_card_without_advancing_stage` — US-3: 逾期不晋升惩罚
- `test_review_rollover_advances_when_overdue_days_equal_allowed_delay` — US-3: 边界条件逾期天数等于允许延迟
- `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body` — US-4/US-5: Mastery Sink 保留人工正文
- `test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match` — US-4/US-5: Mastery Sink 新建 base 卡片
- `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab` — US-5/US-6/US-7: 非目标文件不可触
- `test_review_rollover_completes_when_daily_note_is_missing` — US-8: 缺 daily note 正常完成
- `test_review_rollover_blocks_unknown_stage_before_any_write` — US-9: 未知 stage 阻断写入
- `test_review_rollover_blocks_invalid_next_review_before_any_write` — US-9: 无效 date 阻断写入
- `test_validation_failure_blocks_planning_before_any_write_is_applied` — US-9: 校验失败 → 零写入
- `test_total_training_dashboard_exists_and_sorts_stably` — Dashboard: 模板存在 + 结构合法性

---

## 与计划偏差

| 计划 | 实际 | 原因 |
|---|---|---|
| 能力 maturity = `experimental` | `stable` | `CapabilityRegistry.require()` 拒绝 `experimental` 的 write 操作。测试和 workflow 均需通过 Registry |
| V5 计划测试数 = 15 | 实际 29 | 额外包含 Phase 2.0 基准 8 个静态测试 + 6 个 workflow 测试 |
| Core 测试影响面 = 6 文件 | 实际 2 个需修改 | 其余 5 个硬编码 `"ja"` 不依赖 core 常量，仅 `test_context.py` + `test_capabilities.py` 受影响 |

---

## 关键技术决策

1. **validator 前置 stage/date 校验**：与日语版不同，英语包将 stage 枚举和 date 格式校验前移至 validators.py，明确"数据格式验证"与"状态机调度"的职责边界。

2. **`_EN_STABLE_BASE_VOCAB_KEYS`**：Mastery Sink 稳定字段仅包含 `ipa`/`word_stress`/`part_of_speech`/`english_definition`/`collocations`/`meaning_zh`/`source_notes`，严禁混入日语专属字段（如 `reading`/`accent_display`/`kanji_diff`）。

3. **ROLLOVER_ROLES**：排除 `speaking_card_root` 和 `listening_root`（均为 unsupported），排除 `base_vocab_root`（base 词库是 Mastery Sink 目标，非结算扫描源）。

4. **`_merged_source_notes`**：逗号分隔 → Set 去重 → 逗号拼接回写，确保 base 卡片的 source 引用不重复。

---

## 契约覆盖

| 契约文档 | 要求 | 覆盖率 |
|---|---|---|
| `review-rollover-user-stories.md` | 14 行 Migration Test Matrix | 15/15 (100%) |
| `total-training-dashboard-user-stories.md` | 7 个 User Story | 全部覆盖 |
| `language-pack-capability-guidance.zh.md` | 能力声明 + Core 边界规则 | 全部遵循 |
| `AGENTS.md` | 修改规范 + Changelog 记录 | 待 PR 时记录 |

---

## 存续声明

- 本次实施修改了 11 个文件（+3 新建），总计 +1041 行 / -48 行
- 全部 84 个测试通过，日语包 30 个测试零退化
- 未修改日语包的任何代码
