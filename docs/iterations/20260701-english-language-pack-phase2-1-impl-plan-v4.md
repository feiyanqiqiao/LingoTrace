# 英语包 Phase 2.1 实施计划 (V4 Final Execution Edition - Upstream Synced)

本计划旨在全面修复目前 `feature/english-learning` 分支中的初步英语包实现与最新多语言能力契约之间的冲突。
此版本为最终的“无脑执行版”，完美兼容 Obsidian Base 渲染机制与 LingoTrace 前后端异构架构，**并已实时同步了上游最新的 Phase 2.5 结转沉淀（Mastery Sink）架构更新**。执行者无需任何前置上下文，请**严格**按照此文档中的精确路径和代码片段逐项落实。

---

## 📖 实施背景与前因后果 (Background & Context)
近期，LingoTrace 上游代码库发生了一次重大的架构升级，合入了一系列用于规范语言包（Language Pack）行为的“核心约束契约”。
在拉取最新上游代码后，我们发现日语包已正式实装了 Phase 2.5 的核心特性：**结转沉淀（Mastery Sink）**。这意味着卡片毕业（day180 -> mastered）不再仅仅是修改状态，而是要求自动沉淀到 Base 词汇库。

经过多轮审计与上游同步，英语包主要遗留问题为：
1. **全景看板与前端语法脱节**：看板未严格遵守 Obsidian Base 原生 YAML 语法（特别是列排序 `order` 声明、`formula.` 前缀机制）。
2. **底层白名单拦截**：`total_training_dashboard` 必须在 Core 层注册。
3. **前后端状态计算混淆**：前端通过公式计算“是否逾期”，而后端状态机必须扫描纯 Frontmatter 自己实现判定。
4. **毕业沉淀缺失（Mastery Sink）**：英语包尚未实现最新的 day180 毕业下沉 Base 库的逻辑。
5. **硬核测试真空**：缺失了《迁移矩阵（Migration Test Matrix）》中要求的全部核心测试（包含最新的 Mastery Sink 测试）。

本实施计划旨在完美填补这些债务。

## 🤖 评审 Agent 前置阅读指南 (Prerequisite Reading for Reviewing Agents)
> [!IMPORTANT]
> 1. `docs/multilingual/language-pack-capability-guidance.zh.md`
> 2. `docs/multilingual/total-training-dashboard-user-stories.md`
> 3. `docs/multilingual/review-rollover-user-stories.md` (重点阅读 US-4 与 US-5 的 Mastery Sink 规则)
> 4. 本项目的 `AGENTS.md` (理解项目修改与 Changelog 记录的强制规范)

---

## 1. 核心架构解耦与防腐 (Core Architecture & Safelisting)

### 1.1 修改 `lingotrace/core/context.py`
**目标**: `lingotrace/core/context.py`
- 将 `SUPPORTED_TARGET_LANGUAGE = "ja"` 改为 `SUPPORTED_TARGET_LANGUAGES = ("ja", "en")`。
- 修改 `_parse_context` 的判断条件：`if target_language not in SUPPORTED_TARGET_LANGUAGES:`。

### 1.2 修改 `lingotrace/core/capabilities.py`
**目标**: `lingotrace/core/capabilities.py`
- 在 `PHASE0_CAPABILITY_IDS` 集合中追加 `"total_training_dashboard"`。

### 1.3 修复 6 个受影响的核心层测试文件
- `tests/lingotrace/core/test_context.py`: 寻找 `test_rejects_unsupported_target_language`，将其中的 `payload["target_language"] = "en"` 改为 `"fr"`。
- **说明**：以下 5 个测试文件不受常量改动直接影响，但因 `PHASE0_CAPABILITY_IDS` 增加了新能力，必须确保测试在跨能力依赖时仍然通过：
  - `tests/lingotrace/core/test_capabilities.py`
  - `tests/lingotrace/core/test_paths.py`
  - `tests/lingotrace/core/test_manifests.py`
  - `tests/lingotrace/core/test_mutations.py`
  - `tests/lingotrace/packs/test_japanese_workflow_previews.py`

---

## 2. 字段与能力声明 (Fields & Manifest)

### 2.1 追加英英释义字段 `fields.json`
**目标**: `lingotrace/packs/english/fields.json`
追加：
```json
{
  "name": "english_definition",
  "owner": "English language pack",
  "purpose": "Primary English-to-English definition fallback."
}
```

### 2.2 补全 `manifest.json` 声明
**目标**: `lingotrace/packs/english/manifest.json`
- 在现有的 `capabilities` **数组**中追加（状态为 experimental）：
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
- 在现有的 `templates` **数组**中追加（严格对齐现有键名）：
  ```json
  {
    "id": "total_training_base",
    "capability_id": "total_training_dashboard",
    "path": "lingotrace/packs/english/views/total-training.base",
    "artifact_class": "recreate-from-pack"
  }
  ```

---

## 3. 全景看板模板实现 (Total Training Dashboard)

**创建新文件**: `lingotrace/packs/english/views/total-training.base`
严格采用 Obsidian Base 原生 4 段式语法，补齐 properties 的 `formula.` 前缀，添加双视图与 order 序列：

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
  formula.core_text:
    displayName: 核心内容
  formula.support_text:
    displayName: 辅助说明
  item_type:
    displayName: 题型
  next_review:
    displayName: 下次复习
  formula.due_flag:
    displayName: 到期标记
  formula.next_day_flag:
    displayName: 次日入口
views:
  - type: table
    name: 今日总训练
    filters:
      and:
        - formula.next_day_flag == true
    order:
      - file.name
      - done_today
      - item_type
      - formula.core_text
      - formula.support_text
      - next_review
    sort:
      - property: done_today
        direction: DESC
      - property: next_review
        direction: ASC
      - property: item_type
        direction: ASC
      - property: file.name
        direction: ASC
    columnSize:
      file.name: 260
      done_today: 96
      formula.core_text: 320
      formula.support_text: 420
  - type: table
    name: 最近新增
    filters:
      and:
        - status == "active"
    order:
      - file.name
      - item_type
      - formula.core_text
      - next_review
    sort:
      - property: file.name
        direction: ASC
    columnSize:
      file.name: 260
```

---

## 4. Agent 指令重塑 (SKILL.md)

**目标文件**: `lingotrace/packs/english/agent_skills/SKILL.md`
清空原有内容，注入严谨的 Intent Routing 模板：

```markdown
# English Language Pack Daily Study Agent Skill

## 1. Intent Families & Routing
- **Dashboard Maintenance**: If user says "处理一下总训练表" or "总训练表有问题", you MUST CLARIFY before applying changes.
- **Review Rollover**: If user says "今天复习结束了，结算吧" or "结算复习", this triggers silent `review_rollover`. DO NOT ASK for confirmation. Apply directly.

## 2. User Language Mapping
- `listening_notes`: Reply "English listening transcription is currently unsupported."
- `speaking_cards`: Reply "English speaking cards generation is currently unsupported."
- For valid intents, reply in natural language (e.g. "Okay, calculating your review schedules...").

## 3. Risk-Level Operations
- **Silent Apply**: `review_rollover`
- **Confirm First**: modifying templates, manual dashboard restructuring.

## 4. Data Single Source of Truth
- Modify `frontmatter` directly. 
- NEVER create a parallel `review-state.json`.

## 5. Write Guards
- Any physical file modification MUST go through `lingotrace.core.mutations`.
```

---

## 5. 工作流与校验器实现 (Workflows & Validators)

### 5.1 补全 `validators.py`
**目标**: `lingotrace/packs/english/validators.py`
在 `validate_review_rollover` 中增加：
- 校验 `review_stage` 是否在 `("day0", "day1", "day3", "day7", "day14", "day30", "day90", "day180", "mastered")`，不在则返回 `invalid_review_stage` 错误。
- 校验 `next_review` 是否符合 `YYYY-MM-DD` 格式。

### 5.2 补全 `workflows.py`
**目标**: `lingotrace/packs/english/workflows.py`
- 新增 `_target_context_errors` 防腐函数，检查 `target_language == "en"`, `language_pack == "lingo-english"`, 且 `capability_id in enabled_capabilities`。在首行拦截。
- **纯后端状态机实现**（禁止依赖 base 公式）：
  - 扫描 Frontmatter：找出所有 `fields.get("status") == "active"` 且 `fields.get("done_today") == True` 且 `date(next_review) <= run_date` 的笔记。
  - **正常晋升**：`overdue_days <= 允许延迟`，晋升下一阶段。
  - **逾期惩罚**：`overdue_days > 允许延迟`，不晋升，重置复习时间。
  - **毕业结转沉淀 (Mastery Sink)**：
    - 如果是从 `day180` 晋升，设置 focus card 的 `status = "mastered"`，清空 `next_review`。
    - **如果是 vocab 类型卡片，必须触发向 `base_vocab_root` 的沉淀**：
      - 若 Base 库无同名卡片，则新建 promoted base 卡。
      - 若 Base 库已有同名卡片，则安全更新稳定字段、合并来源（sources），并**严格保留 Base 卡片的人工正文（manual body）**。
  - 所有操作包装为 `FileMutation(action="apply_review_rollover")`。

---

## 6. 十七条契约矩阵测试 (Migration Matrix Tests)

**目标**: `tests/lingotrace/packs/test_english_pack.py`
追加 `TestEnglishReviewRolloverContract`，包含这 17 个最新的契约级测试：

```python
class TestEnglishReviewRolloverContract(unittest.TestCase):
    # US-1
    def test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply(self): ...
    # US-2, US-4
    def test_review_rollover_applies_every_memory_curve_transition_from_run_date(self): ...
    # US-3
    def test_review_rollover_advances_when_overdue_days_equal_allowed_delay(self): ...
    def test_review_rollover_reschedules_overdue_card_without_advancing_stage(self): ...
    # US-4, US-5: Mastery Sink tests (New from Phase 2.5)
    def test_apply_updates_done_today_review_stage_next_review_and_mastered_status(self): ...
    def test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body(self): ...
    def test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match(self): ...
    # US-5, US-6, US-7
    def test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab(self): ...
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
# 验证核心解耦没有破坏现有架构
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
