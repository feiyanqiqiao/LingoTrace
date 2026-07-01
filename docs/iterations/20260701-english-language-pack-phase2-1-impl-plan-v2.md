# 英语包 Phase 2.1 实施计划 (V2 Standalone Edition)

本计划旨在全面修复目前 `feature/english-learning` 分支中的初步英语包实现与最新多语言能力契约之间的冲突。
此版本为高度保真实施手册，无需任何前置上下文，请执行者**严格**按照此文档中的精确路径和代码清单逐项落实。

---

## 📖 实施背景与前因后果 (Background & Context)
近期，LingoTrace 上游代码库发生了一次重大的架构升级，合入了一系列用于规范语言包（Language Pack）行为的“核心约束契约”。这些契约不再是软性的设计建议，而是具备严格的代码级沙盒拦截和流水线测试（CI）强制力的底线规则。

我们在此前提交的 `feature/english-learning` 分支虽然搭建了英语包的初步骨架（Phase 2.0），但经审计，它严重脱离了最新的契约标准。主要冲突如下：
1. **全景看板缺失**：新契约强制要求语言包提供带有类型专属回退逻辑的 `total-training.base` 看板，而当前英语包毫无声明。
2. **Agent 意图越界风险**：新契约严厉区分了“结算数据（Rollover）”和“维护看板（Dashboard Maintenance）”指令，并要求明确启用“免二次确认的后台沙盒预览写入”。当前 `SKILL.md` 的指引过于简陋，未能建立起这道防线。
3. **测试真空与脏数据隐患**：当前测试仅包含格式检验，彻底缺失了《迁移矩阵（Migration Test Matrix）》中要求的硬核业务逻辑（如 180天满级、逾期惩罚、脏数据物理阻断等）。

本实施计划旨在全面填补这些债务，使英语包完全融入最新的 LingoTrace 多语言标准。

## 🤖 评审 Agent 前置阅读指南 (Prerequisite Reading for Reviewing Agents)
> [!IMPORTANT]
> 如果您是负责 Review 本实施计划的其他 Agent，在评估本计划的合理性之前，请**务必首先读取**以下三份最新的架构契约文档：
> 1. `docs/multilingual/language-pack-capability-guidance.zh.md` (理解三级成熟度模型与能力边界)
> 2. `docs/multilingual/total-training-dashboard-user-stories.md` (理解看板排序、意图隔离与字段降级铁律)
> 3. `docs/multilingual/review-rollover-user-stories.md` (理解复习结转的十项用户故事与测试矩阵)
> 4. 本项目的 `AGENTS.md` (理解项目修改与 Changelog 记录的强制规范)

---

## 1. 核心上下文解耦 (Core Context Generalization)

打破底层只允许 `"ja"` 的硬编码，正式接纳英语。

### 1.1 修改 `lingotrace/core/context.py`
**目标文件**: `lingotrace/core/context.py`
- 将第 13 行的 `SUPPORTED_TARGET_LANGUAGE = "ja"` 改为：
  `SUPPORTED_TARGET_LANGUAGES = ("ja", "en")`
- 将 `_parse_context` 函数中的：
  ```python
  if target_language != SUPPORTED_TARGET_LANGUAGE:
      findings.append(Finding(code="unsupported_target_language", message="Unsupported target language."))
  ```
  改为：
  ```python
  if target_language not in SUPPORTED_TARGET_LANGUAGES:
      findings.append(Finding(code="unsupported_target_language", message="Unsupported target language."))
  ```

### 1.2 修复核心层测试 `tests/lingotrace/core/test_context.py`
**目标文件**: `tests/lingotrace/core/test_context.py`
因为我们接纳了 `"en"`，原本用来测试“拒绝非法语言”的用例会失败，必须把脏数据改为真正的非法语言（如法语 `"fr"`）。
- 找到 `test_rejects_unsupported_target_language` 方法：
  ```python
  def test_rejects_unsupported_target_language(self) -> None:
      ...
      payload["target_language"] = "en"  # [DELETE]
      payload["target_language"] = "fr"  # [NEW]
  ```

---

## 2. 字段与能力声明 (Fields & Manifest)

引入纯正的英英释义产品体验，并在清单中声明看板能力。

### 2.1 追加英英释义字段 `fields.json`
**目标文件**: `lingotrace/packs/english/fields.json`
在 `language_fields` 数组中追加：
```json
{
  "name": "english_definition",
  "type": "string",
  "description": "English definition of the word",
  "owner": "English language pack",
  "required": false
}
```

### 2.2 补全 `manifest.json` 声明
**目标文件**: `lingotrace/packs/english/manifest.json`
- 在 `capabilities` 字典中添加：
  ```json
  "total_training_dashboard": {
    "maturity": "stable",
    "depends_on": [],
    "read_path_roles": ["daily_notes_root", "focus_vocab_root", "base_vocab_root", "grammar_root", "error_root", "pronunciation_accent_root", "pronunciation_phoneme_root"],
    "write_path_roles": [],
    "external_tools": [],
    "behavior_evidence": ["EN-DASHBOARD-001"],
    "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
    "manual_review_cases": []
  }
  ```
- 在顶层追加 `templates` 数组：
  ```json
  "templates": [
    {
      "id": "total_training_base",
      "path": "lingotrace/packs/english/views/total-training.base",
      "category": "recreate-from-pack"
    }
  ]
  ```

---

## 3. 全景看板模板实现 (Total Training Dashboard)

严格遵守看板路径要求和优雅降级铁律。

### 3.1 创建 `views/total-training.base`
**创建新文件**: `lingotrace/packs/english/views/total-training.base`
内容必须包含以下 4 种 `item_type` 的完整映射公式，且列排序绝对稳定：
```json
{
  "type": "database",
  "views": [
    {
      "id": "today_total",
      "name": "今日总训练",
      "columns": [
        {"name": "file.name", "visible": true},
        {"name": "done_today", "visible": true},
        {"name": "review_stage", "visible": true},
        {"name": "core_text", "visible": true},
        {"name": "support_text", "visible": true},
        {"name": "item_type", "visible": true},
        {"name": "next_review", "visible": true}
      ],
      "filters": [
        {"field": "due_flag", "operator": "==", "value": true},
        {"field": "review_stage", "operator": "!=", "value": "mastered"}
      ],
      "sort": [
        {"field": "done_today", "direction": "asc"},
        {"field": "item_type", "direction": "asc"},
        {"field": "next_review", "direction": "asc"}
      ]
    }
  ],
  "formulas": {
    "due_flag": "next_review <= today()",
    "core_text": "ifs(item_type=='vocab', if(not(empty(ipa)), ipa, if(not(empty(english_definition)), english_definition, if(not(empty(headword)), headword, meaning_zh))), item_type=='grammar', if(not(empty(meaning_zh)), meaning_zh, pattern), item_type=='error', correct_form, item_type=='pronunciation', target_text, file.name)",
    "support_text": "ifs(item_type=='vocab', if(not(empty(collocations)), collocations, meaning_zh), item_type=='grammar', formation, item_type=='error', if(not(empty(wrong_form)), wrong_form, reason), item_type=='pronunciation', issue_tags, '')"
  }
}
```
*(注意公式中对 `english_definition` 的优先引用，以及四种类型的完整覆盖)*

---

## 4. Agent 指令重塑 (SKILL.md)

**目标文件**: `lingotrace/packs/english/agent_skills/SKILL.md`
**操作**: 清空原有内容，参考日语包，重写为具备完整防腐骨架的指引：
1. **Intent Recognition**: 明确告诉模型如何分类用户的意图（复习资料生成、口语卡片生成、结算总训练表、修改总训练表配置）。
2. **User Language**: 必须针对 English Pack 设定专有的自然语言回复（例如对于 `listening_notes` 请求，Agent 要回答“English listening transcription is currently unsupported”）。
3. **Write Guards**: 强调一切修改只能操作 review-card frontmatter，绝对禁止创建并行的 `review-state.json`，且所有写入必须走核心的 file_mutations guard。
4. **意图隔离与沙盒**: 明确规定 `review_rollover` 必须无弹窗后台静默 Preview -> Apply -> Preview；而涉及 `total-training.base` 看板结构的修改，必须弹窗确认。

---

## 5. 工作流与校验器实现 (Workflows & Validators)

### 5.1 补全 `validators.py`
**目标文件**: `lingotrace/packs/english/validators.py`
在 `validate_review_rollover` 中增加脏数据阻断：
- 校验 `review_stage` 是否存在于 `("day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180", "mastered")`，不在则返回 `invalid_review_stage` 错误。
- 校验 `next_review` 是否符合 `YYYY-MM-DD` 格式。

### 5.2 补全 `workflows.py`
**目标文件**: `lingotrace/packs/english/workflows.py`
- 新增 `_target_context_errors` 防腐函数，检查 `target_language == "en"` 和 `language_pack == "lingo-english"`，在所有 workflow 首行调用，确保沙盒安全。
- 实现真实的 `review_rollover` 状态机逻辑（替换 `_not_yet_implemented`）：
  - 提取出所有 `due_flag == true` 且 `done_today == true` 的笔记。
  - **正常晋升**：如果 `overdue_days <= 阶段允许延迟`，晋升到下一阶段，重新计算 `next_review = run_date + 下阶段天数`。
  - **逾期惩罚**：如果 `overdue_days > 阶段允许延迟`，不晋升，`next_review = run_date + 当前阶段天数`。
  - 执行完毕后返回包含所有 `FileMutation` (动作皆为 `update`) 的 `CommandReport`。

---

## 6. 十四条契约矩阵测试 (Migration Matrix Tests)

**目标文件**: `tests/lingotrace/packs/test_english_pack.py`
追加 `TestEnglishReviewRolloverContract` 测试类，必须完整实现以下所有测试函数的断言（确保覆盖 100% 契约矩阵）：

```python
class TestEnglishReviewRolloverContract(unittest.TestCase):
    # US-1: Second preview after apply returns zero
    def test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply(self): ...
    
    # US-2, US-4: Full state machine transitions
    def test_review_rollover_applies_every_memory_curve_transition_from_run_date(self): ...
    
    # US-3: Exact overdue day threshold limits
    def test_review_rollover_advances_when_overdue_days_equal_allowed_delay(self): ...
    def test_review_rollover_reschedules_overdue_card_without_advancing_stage(self): ...
    
    # US-5, US-6, US-7: Non-focus scope safety
    def test_review_rollover_does_not_touch_base_vocab_or_daily_notes(self): ...
    
    # US-8: Missing daily notes resilient
    def test_review_rollover_completes_when_daily_note_is_missing(self): ...
    
    # US-9, US-10: Dirty data isolation
    def test_review_rollover_blocks_unknown_stage_before_any_write(self): ...
    def test_review_rollover_blocks_invalid_next_review_before_any_write(self): ...
    
    # Safety Check
    def test_review_rollover_previews_due_target_card_without_writes(self): ...
    def test_review_rollover_apply_advances_due_target_card(self): ...
    
    # Dashboard check
    def test_total_training_dashboard_exists_and_sorts_stably(self): ...
```

---

## 7. 验证环节 (Verification Plan)

实施完毕后，通过执行以下命令确保重构成功，无任何退化：

```bash
# 验证核心解耦没有破坏现有架构
python -m unittest tests.lingotrace.core.test_context
python -m unittest tests.lingotrace.core.test_capabilities

# 验证日语包完全不受影响
python -m unittest tests.lingotrace.packs.test_japanese_workflow_previews

# 验证英语包的全面契约通过
python -m unittest tests.lingotrace.packs.test_english_pack
```
