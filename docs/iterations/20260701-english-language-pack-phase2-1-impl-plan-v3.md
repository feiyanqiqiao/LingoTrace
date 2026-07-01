# 英语包 Phase 2.1 实施计划 (V3 Ultimate Standalone Edition)

本计划旨在全面修复目前 `feature/english-learning` 分支中的初步英语包实现与最新多语言能力契约之间的冲突。
此版本为经历两次严格评审后的**终极实施手册**。执行者无需任何前置上下文，请**严格**按照此文档中的精确路径、代码片段（特别是底层的原生语法要求）逐项落实。

---

## 📖 实施背景与前因后果 (Background & Context)
近期，LingoTrace 上游代码库发生了一次重大的架构升级，合入了一系列用于规范语言包（Language Pack）行为的“核心约束契约”。这些契约不再是软性的设计建议，而是具备严格的代码级沙盒拦截和流水线测试（CI）强制力的底线规则。

我们在此前提交的 `feature/english-learning` 分支虽然搭建了英语包的初步骨架（Phase 2.0），但经审计，它严重脱离了最新的契约标准。主要冲突如下：
1. **全景看板缺失**：新契约强制要求语言包提供带有类型专属回退逻辑的 `total-training.base` 看板，且必须兼容 Obsidian Base 的原生 YAML-like 语法。
2. **底层白名单拦截**：`total_training_dashboard` 未被 Core 层信任。
3. **测试真空与脏数据隐患**：当前测试彻底缺失了《迁移矩阵（Migration Test Matrix）》中要求的 14 项硬核业务逻辑（如 180天满级、逾期惩罚、脏数据物理阻断等）。

本实施计划旨在全面填补这些债务，使英语包完全融入最新的 LingoTrace 多语言标准。

## 🤖 评审 Agent 前置阅读指南 (Prerequisite Reading for Reviewing Agents)
> [!IMPORTANT]
> 如果您是负责 Review 本实施计划的其他 Agent，在评估本计划的合理性之前，请**务必首先读取**以下三份最新的架构契约文档：
> 1. `docs/multilingual/language-pack-capability-guidance.zh.md`
> 2. `docs/multilingual/total-training-dashboard-user-stories.md`
> 3. `docs/multilingual/review-rollover-user-stories.md`
> 4. 本项目的 `AGENTS.md` (理解项目修改与 Changelog 记录的强制规范)

---

## 1. 核心架构解耦与防腐 (Core Architecture & Safelisting)

打破底层只允许 `"ja"` 的硬编码，同时将新看板能力加入白名单。

### 1.1 修改 `lingotrace/core/context.py`
**目标**: `lingotrace/core/context.py`
- 将 `SUPPORTED_TARGET_LANGUAGE = "ja"` 改为 `SUPPORTED_TARGET_LANGUAGES = ("ja", "en")`。
- 修改 `_parse_context`：`if target_language not in SUPPORTED_TARGET_LANGUAGES:`。

### 1.2 修改 `lingotrace/core/capabilities.py`
**目标**: `lingotrace/core/capabilities.py`
- 在 `PHASE0_CAPABILITY_IDS` 集合中追加 `"total_training_dashboard"`，使其通过 Registry 白名单拦截。

### 1.3 修复 6 个受影响的核心层测试文件
由于核心上下文从单语言变更为多语言，修改以下测试以修复硬编码：
- `tests/lingotrace/core/test_context.py`: 寻找 `test_rejects_unsupported_target_language`，将其中的 `payload["target_language"] = "en"` 改为 `"fr"`。
- 对以下 5 个文件，确保其测试环境在 `target_language` 为 `"ja"` 或 `"en"` 时仍能通过（修改相关的硬编码校验或 mock）：
  - `tests/lingotrace/core/test_capabilities.py`
  - `tests/lingotrace/core/test_paths.py`
  - `tests/lingotrace/core/test_manifests.py`
  - `tests/lingotrace/core/test_mutations.py`
  - `tests/lingotrace/packs/test_japanese_workflow_previews.py`

---

## 2. 字段与能力声明 (Fields & Manifest)

### 2.1 追加英英释义字段 `fields.json`
**目标**: `lingotrace/packs/english/fields.json`
在 `language_fields` 数组中追加（严格对齐现有 Schema）：
```json
{
  "name": "english_definition",
  "owner": "English language pack",
  "purpose": "Primary English-to-English definition fallback."
}
```

### 2.2 补全 `manifest.json` 声明
**目标**: `lingotrace/packs/english/manifest.json`
- 在现有的 `capabilities` **数组**中（注意是追加元素，不是覆盖为字典），追加：
  ```json
  {
    "id": "total_training_dashboard",
    "maturity": "experimental",
    "depends_on": [],
    "read_path_roles": [
      "daily_notes_root", "focus_vocab_root", "base_vocab_root", 
      "grammar_root", "error_root", "pronunciation_accent_root", 
      "pronunciation_phoneme_root"
    ],
    "write_path_roles": [],
    "external_tools": [],
    "behavior_evidence": [],
    "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
    "manual_review_cases": []
  }
  ```
- 在现有的 `templates` **数组**中，追加：
  ```json
  {
    "id": "total_training_base",
    "path": "lingotrace/packs/english/views/total-training.base",
    "category": "recreate-from-pack"
  }
  ```

---

## 3. 全景看板模板实现 (Total Training Dashboard)

**创建新文件**: `lingotrace/packs/english/views/total-training.base`
严格采用 Obsidian Base 原生 4 段式语法。文件内容须如下所示（注意单层 `if` 语法）：

```yaml
filters:
  and:
    - file.ext == "md"
formulas:
  due_flag: 'if(status == "active" && next_review && date(next_review) <= today() && !(last_reviewed && date(last_reviewed) >= today()), true, false)'
  next_day_flag: 'if(status == "active" && next_review && date(next_review) <= today() + "1d" && !(last_reviewed && date(last_reviewed) >= today()), true, false)'
  core_text: 'if(item_type == "vocab", if(ipa, ipa, if(english_definition, english_definition, if(headword, headword, meaning_zh))), if(item_type == "grammar", if(meaning_zh, meaning_zh, pattern), if(item_type == "error", correct_form, if(item_type == "pronunciation", target_text, file.name))))'
  support_text: 'if(item_type == "vocab", if(collocations, collocations, meaning_zh), if(item_type == "grammar", formation, if(item_type == "error", if(wrong_form, wrong_form, reason), if(item_type == "pronunciation", issue_tags, ""))))'
properties:
  file.name:
    displayName: 文件名
  done_today:
    displayName: 今日完成
  review_stage:
    displayName: 复习阶段
  core_text:
    displayName: 核心内容
  support_text:
    displayName: 辅助说明
  item_type:
    displayName: 题型
  next_review:
    displayName: 下次复习
views:
  - type: table
    name: 今日总训练
    filters:
      and:
        - formula.next_day_flag == true
    sort:
      - property: done_today
        direction: ASC
      - property: item_type
        direction: ASC
      - property: next_review
        direction: ASC
      - property: file.name
        direction: ASC
    columnSize:
      file.name: 260
      done_today: 96
```

---

## 4. Agent 指令重塑 (SKILL.md)

**目标文件**: `lingotrace/packs/english/agent_skills/SKILL.md`
清空原有内容，注入完整的 6 段式骨架（必须包含以下模块）：

1. **Intent Recognition (意图路由规则)**:
   - "总训练表有问题" -> Dashboard 维护 -> 必须 Clarify（澄清）
   - "今天复习结束了，结算吧" -> Review Rollover -> 触发静默 Apply
2. **User Language Map**: 设置英语专有拒绝语（如 `English listening transcription is currently unsupported`）。
3. **Risk-Level Operations**: 明确规定新建自动、合并须确认、日结免确认（Silent Apply）。
4. **Data SSOT**: 强制 Agent 只能修改 Frontmatter，禁造 `review-state.json`。
5. **Write Guards**: 写入必须调用 core 的 `file_mutations`。
6. **Capability Steps**: 明确写出 `review_rollover` 的 3 步（提取 due_flag -> 计算逾期 -> 返回 CommandReport）。

---

## 5. 工作流与校验器实现 (Workflows & Validators)

### 5.1 补全 `validators.py`
**目标文件**: `lingotrace/packs/english/validators.py`
在 `validate_review_rollover` 中增加：
- 校验 `review_stage` 是否在 `("day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180", "mastered")`，不在则返回 `invalid_review_stage` 错误。
- 校验 `next_review` 是否符合 `YYYY-MM-DD` 格式。

### 5.2 补全 `workflows.py`
**目标文件**: `lingotrace/packs/english/workflows.py`
- 新增 `_target_context_errors` 防腐函数，检查 `target_language == "en"`, `language_pack == "lingo-english"`, 且 `capability_id in enabled_capabilities`。在所有 workflow 首行拦截。
- 实现真实的 `review_rollover` 状态机逻辑（替换 stub）：
  - 提取出所有 `due_flag == true` 且 `done_today == true` 的笔记。
  - **正常晋升**：如果 `overdue_days <= 允许延迟`，晋升到下一阶段。
  - **逾期惩罚**：如果 `overdue_days > 允许延迟`，不晋升，重置复习时间。
  - 所有操作必须包装为 `FileMutation`，且 `action="apply_review_rollover"`。

---

## 6. 十五条契约矩阵测试 (Migration Matrix Tests)

**目标文件**: `tests/lingotrace/packs/test_english_pack.py`
追加 `TestEnglishReviewRolloverContract` 测试类，完整覆盖全部 14+1 矩阵行为：

```python
class TestEnglishReviewRolloverContract(unittest.TestCase):
    # US-1
    def test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply(self): ...
    
    # US-2, US-4
    def test_review_rollover_applies_every_memory_curve_transition_from_run_date(self): ...
    
    # US-3
    def test_review_rollover_advances_when_overdue_days_equal_allowed_delay(self): ...
    def test_review_rollover_reschedules_overdue_card_without_advancing_stage(self): ...
    
    # US-5, US-6, US-7
    def test_review_rollover_does_not_touch_base_vocab_or_daily_notes(self): ...
    
    # US-8
    def test_review_rollover_completes_when_daily_note_is_missing(self): ...
    
    # US-9, US-10
    def test_review_rollover_blocks_unknown_stage_before_any_write(self): ...
    def test_review_rollover_blocks_invalid_next_review_before_any_write(self): ...
    def test_validation_failure_blocks_planning_before_any_write_is_applied(self): ...
    
    # Safety Check
    def test_review_rollover_previews_due_target_card_without_writes(self): ...
    def test_review_rollover_apply_advances_due_target_card(self): ...
    
    # Dashboard check
    def test_total_training_dashboard_exists_and_sorts_stably(self): ...
```

---

## 7. 验证环节 (Verification Plan)

实施完毕后，通过执行以下命令确保重构成功：

```bash
# 验证核心解耦没有破坏现有架构，包含所有被波及的文件
python -m unittest tests.lingotrace.core.test_context
python -m unittest tests.lingotrace.core.test_capabilities
python -m unittest tests.lingotrace.core.test_paths
python -m unittest tests.lingotrace.core.test_manifests
python -m unittest tests.lingotrace.core.test_mutations

# 验证日语包完全不受影响
python -m unittest tests.lingotrace.packs.test_japanese_workflow_previews

# 验证英语包的全面契约通过
python -m unittest tests.lingotrace.packs.test_english_pack
```
