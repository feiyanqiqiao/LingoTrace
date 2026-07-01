# 英语包 Phase 2.1 实施计划评审报告

**评审对象**: `20260701-english-language-pack-phase2-1-impl-plan.md`
**评审日期**: 2026-07-01
**评审结论**: 🔴 需要修改后重新提交

---

## 评审依据

本次评审以以下契约为基准：

| 契约文档 | 状态 | 用途 |
|---|---|---|
| `docs/multilingual/language-pack-capability-guidance.zh.md` | Reference Guidance | 三级成熟度模型与能力边界 |
| `docs/multilingual/total-training-dashboard-user-stories.md` | Reference Guidance | 看板排序、意图隔离、字段降级铁律 |
| `docs/multilingual/review-rollover-user-stories.md` | Reference Guidance | 复习结转十项用户故事与测试矩阵 |
| `AGENTS.md` | 项目规范 | 修改与 Changelog 记录强制规范 |
| 日语包 `workflows.py` / `SKILL.md` / `views/total-training.base` | 参考实现 | 唯一通过契约验证的参考实现 |

---

## 阻断项 (Blockers)

### B1. 看板模板路径与契约冲突

**计划写**:
```
lingotrace/packs/english/templates/total-training.base
```

**契约要求**:
```
lingotrace/packs/<language>/views/total-training.base
```

证据：
- `total-training-dashboard-user-stories.md` §Ownership Boundary: `lingotrace/packs/<language>/views/total-training.base`
- 日语包实际路径: `lingotrace/packs/japanese/views/total-training.base`
- 英语包当前 `templates/` 目录下只有 `daily-checklist.md` 和 `focus-vocab-card.md`，无 Base 文件

**修正**: 路径改为 `lingotrace/packs/english/views/total-training.base`。同时在 `manifest.json` 的 `templates` 数组中声明此 artifact，类目为 `recreate-from-pack`。

---

### B2. 测试覆盖率仅为矩阵要求的 36%

Migration Test Matrix（`review-rollover-user-stories.md` §Migration Test Matrix）列出 14 行必测行为。计划列出 5 个测试，对应关系：

| 计划测试 | 覆盖 Matrix 行 | 状态 |
|---|---|---|
| `test_review_rollover_previews_without_writes` | Internal preview before write | ✅ |
| `test_review_rollover_apply_advances_due_target_card` | Fixed memory-curve advancement | ✅ |
| `test_review_rollover_reschedules_overdue_card` | Delayed overdue reschedule | ✅ |
| `test_review_rollover_blocks_unknown_stage_before_write` | Invalid card blocks apply (部分) | ⚠️ |
| `test_total_training_dashboard_exists_and_sorts_stably` | Canonical dashboard template + stable filename column | ✅ |

**缺失的 6 个必测行为**:

| Matrix 行 | 缺失测试 | 对应 User Story |
|---|---|---|
| Second preview after apply returns zero | `test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply` | US-1 |
| Every memory-curve transition (含 day180→mastered) | `test_review_rollover_applies_every_memory_curve_transition_from_run_date` | US-2, US-4 |
| overdue_days == allowed_delay advances | `test_review_rollover_advances_when_overdue_days_equal_allowed_delay` | US-3 |
| Base vocab / daily notes untouched | `test_review_rollover_does_not_touch_base_vocab_or_daily_notes` | US-5, US-6, US-7 |
| Missing daily note does not block | `test_review_rollover_completes_when_daily_note_is_missing` | US-8 |
| Invalid next_review blocks apply | `test_review_rollover_blocks_invalid_next_review_before_any_write` | US-9 |

此外，测试命名应与日语包保持一致——契约矩阵中的测试名称是共享契约的一部分，随意重命名会破坏可追溯性。

---

### B3. Core context 变更影响面未分析

计划修改 `lingotrace/core/context.py`:
```python
# 第 13 行
SUPPORTED_TARGET_LANGUAGE = "ja"
# → SUPPORTED_TARGET_LANGUAGES = ("ja", "en")

# 第 82 行
if target_language != SUPPORTED_TARGET_LANGUAGE:
# → 需要改为 if target_language not in SUPPORTED_TARGET_LANGUAGES:
```

此修改直接影响以下 **8 个测试文件**中的硬编码 `target_language: "ja"`：

| 测试文件 | 影响行 |
|---|---|
| `tests/lingotrace/core/test_capabilities.py` | L13, L47 |
| `tests/lingotrace/core/test_paths.py` | L16 |
| `tests/lingotrace/core/test_manifests.py` | L15 |
| `tests/lingotrace/core/test_context.py` | L20 |
| `tests/lingotrace/core/test_mutations.py` | L21, L37 |
| `tests/lingotrace/packs/test_japanese_workflow_previews.py` | L22 |

日语包 `workflows.py` 的 `_target_context_errors()` 中有硬编码校验 `target_language: "ja"`，不受 core 变更影响（它在 pack 层独立校验），但需要确认。

计划对此完全没有覆盖分析，声称"此改动虽小"——实际影响 6+ 测试文件。

---

## 重要缺陷 (Major Issues)

### M1. SKILL.md 重写范围过窄

**当前状态**: 英语 SKILL.md 仅 19 行，日语版 108 行。
**计划修改**: 仅追加"意图隔离"和"免二次确认"两条规则。

缺失的关键模块：

| 模块 | 日语版对应位置 | 必要性 |
|---|---|---|
| Intent Recognition（意图识别框架） | L7-L33 | Agent 需要知道如何从自然语言推断用户意图，不只是处理"结算复习"和"优化总训练表"两个短语 |
| User Language 映射表（完整） | L36-L46 | 当前英语版仅有 3 行映射，缺失 listening/speaking 的用戶可理解拒绝语 |
| 风险分级操作规则 | L65-L71 | 新建→自动写入 / 合并覆盖→确认 / 结算→免二次确认，三级差异 |
| Review-card frontmatter 为唯一数据源 | L61 | 防止 Agent 创建 `review-state.json` 等并行快照 |
| 各能力的详细行为描述 | L73-L108 | source_notes / review_materials / speaking_cards / review_rollover 各自的搜索、去重、确认策略 |
| 禁止写入 Vault 文件直写 | L59 | 所有写入必须经 core write guard |

**建议**: 以日语 SKILL.md 为结构模板，保留 Intent Recognition、Operating Rules、各能力行为描述的完整骨架，替换为英语特有字段（`ipa`、`word_stress`、`part_of_speech`、`collocations`）、特有短语（英语用户的中文指令习惯），并标记 `listening_notes` 和 `speaking_cards` 为 unsupported。

---

### M2. total-training.base 类型映射设计不完整

计划只设计了 vocab 卡的 `core_text`/`support_text` 回退链。契约要求为**每种 `item_type`** 定义显示映射——日语版支持 vocab/grammar/error/survival_speaking/listening/pronunciation 六种，英语版有 `item_types: ["vocab", "grammar", "error", "pronunciation"]` 四种。

缺失的类型映射：

| item_type | core_text 回退链 | support_text 回退链 |
|---|---|---|
| grammar | 未定义 | 未定义 |
| error | 未定义 | 未定义 |
| pronunciation | 未定义 | 未定义 |

参考日语版映射 + 英语包字段，建议：

| item_type | core_text | support_text |
|---|---|---|
| vocab | `ipa` → `headword` → `file.name` | `collocations` → `meaning_zh` |
| grammar | `meaning_zh` → `pattern` → `file.name` | `formation` → `""` |
| error | `correct_form` → `file.name` | `wrong_form` → `reason` → `""` |
| pronunciation | `target_text` → `file.name` | `issue_tags` → `""` |

另外需明确：
- 英语包的 `track` 过滤字段——是否沿用日语的 `class_review` / `survival_speaking` / `listening` / `pronunciation`？英语包目前 `manifest.json` 不含 track 定义
- `due_flag` / `next_day_flag` 公式中的字段名英语化

---

### M3. workflows.py 缺少 Vault Context 校验

日语 `review_rollover()` 第一步调用 `_target_context_errors()`：

```python
def _target_context_errors(root, capability_id):
    # 校验 target_language == "ja"
    # 校验 language_pack == "lingo-japanese"
    # 校验 capability_id in enabled_capabilities
```

英语包 workflow 需要相同逻辑，参数改为 `target_language="en"`、`language_pack="lingo-english"`。计划仅提到"移除桩代码并实现记忆曲线"，未提及此校验层的实现。

**风险**: 没有此校验，英语包 workflow 可能误写入日语 Vault，或写入未启用 `review_rollover` 的 Vault。

---

### M4. Open Question 的设计方向与英语包目标冲突

计划 Open Question：
> 默认保留使用 `meaning_zh` 作为后备显示内容

对于一个"英语学习"语言包而言，以中文释义作为唯一后备是设计倒退。建议：
- 新增 `english_definition` 语言字段，设为优先后备
- 回退链: `ipa` → `english_definition` → `headword` → `meaning_zh` → `file.name`

---

## 小问题 (Minor Issues)

### m1. "180天满级"表述不准

记忆曲线是 9 阶段状态机：`day0 → day1 → day3 → day7 → day14 → day30 → day90 → day180 → mastered`，"满级"是 `mastered`，与天数无关。建议改为"day180 阶段完成后晋升为 mastered"。

### m2. verification 缺少日语包回归确认

计划仅跑 `test_english_pack` 和 `discover tests`。core context 变更后，应显式列出日语包的测试套件确认无回归：

```bash
python -m unittest tests.lingotrace.packs.test_japanese_workflow_previews
python -m unittest tests.lingotrace.core.test_context
```

### m3. manifest.json 的 `templates` 声明遗漏

计划要求 `manifest.json` 声明 `"id": "total_training_base"`，但 manifest 当前结构不含 `capability_id` 字段用于 dashboard——`total_training_dashboard` 能力也尚未在 `capabilities` 数组中声明。需同步补充能力声明和 template 声明。

### m4. agent_skills 目录 vs SKILL.md 单文件

计划路径写 `agent_skills/SKILL.md`，与实际 `agent_skills/SKILL.md`（单文件，非目录）一致，无问题。但需确认计划文本中引用的路径格式。

---

## 建议修改优先级

| 优先级 | 修改项 | 类别 |
|---|---|---|
| P0 | 修正 dashboard 路径为 `views/total-training.base` | Blocker |
| P0 | 补全 6 个缺失的 Matrix 测试用例 | Blocker |
| P0 | 补充 core context 变更的影响面分析（6+ 测试文件） | Blocker |
| P1 | 按日语 SKILL.md 骨架重写英语版 | Major |
| P1 | 补全 total-training.base 四种 item_type 的完整显示映射 | Major |
| P1 | 在 workflow 计划中加入 Vault Context 校验步骤 | Major |
| P2 | 评估 english_definition 作为看板后备字段 | Minor |
| P2 | 修正"180天满级"表述 | Minor |
| P2 | 在 verification 中加入日语包回归测试 | Minor |

---

## 存续声明

- 本次评审生成了新文件 `20260701-english-language-pack-phase2-1-review-report.md`
- 未修改任何现有代码或文档
- 评审依据的契约文档均通过 Read 工具完整读取并交叉验证
