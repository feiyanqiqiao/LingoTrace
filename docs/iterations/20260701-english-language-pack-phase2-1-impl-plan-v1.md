# 英语包 Phase 2.1 实施计划 (Alignment with Core Contracts)

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

## User Review Required

> [!IMPORTANT]
> 核心上下文放宽限制（Core Context Generalization）：为使英语包的代码不仅是“骨架”，而是能真正在本地 Vault 跑通测试，本次实施将打破 `SUPPORTED_TARGET_LANGUAGE = "ja"` 的硬编码，正式接纳 `"en"` 为受支持的目标语言。此改动虽小，但属于 Core 层的正式架构解耦，特此向您确认。

## Open Questions

> [!WARNING]
> 在设计英语版全景训练看板（`total-training.base`）时，除了 `ipa`（音标）、`part_of_speech`（词性）、`collocations`（常见搭配），您是否希望在看板默认优先展示英英释义（English Definition），还是传统的中文释义（`meaning_zh`）？
> *当前计划*：为了向后兼容且最快落地，将默认保留使用 `meaning_zh` 作为后备显示内容。您可以随时提出修改意见。

---

## Proposed Changes

### 1. 核心架构解耦 (Core Architecture)

#### [MODIFY] [context.py](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/core/context.py)
- 将 `SUPPORTED_TARGET_LANGUAGE = "ja"` 扩展为 `SUPPORTED_TARGET_LANGUAGES = ("ja", "en")`。
- 修改 `_parse_context` 中的校验逻辑，使其支持加载目标语言为英语的 Vault Context。这样才能为后续的集成测试扫清路障。

---

### 2. 补齐能力声明与验证边界 (Manifest & Agent Skills)

#### [MODIFY] [manifest.json](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/packs/english/manifest.json)
- 在 `capabilities` 数组中，正式添加对 `total_training_dashboard` 能力的声明。
- 在 `templates` 中，补充声明 `"id": "total_training_base"` 的路径映射。

#### [MODIFY] [SKILL.md](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/packs/english/agent_skills/SKILL.md)
- 重写 Agent Operating Rules：
  - **意图隔离**：严格要求 Agent 区分“结算复习 (Review Rollover)”和“优化总训练表显示 (Dashboard Maintenance)”指令；遇到模棱两可的指令（如“看看总训练表”）必须请求确认。
  - **免二次确认机制**：明确对于清晰的结算指令（“今天复习结束了，帮我结算”），Agent 应自动在后台执行预览 (Preview) -> 写入 (Apply) -> 二次预览，全过程不向用户发起多余的确认弹窗。

---

### 3. 实现全景复习看板 (Total Training Dashboard)

#### [NEW] [total-training.base](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/packs/english/templates/total-training.base)
- 基于日语版的参考架构，专门针对英语场景编写全景训练看板的 `.base` 模板。
- **界面铁律**：确保表格第一列固定为 `file.name`，第二列为 `done_today`，并沿用稳定排序逻辑。
- **英语专属优雅降级公式**：
  - 核心内容 (`core_text`)：如果有 `ipa`（音标）则优先展示，否则回退到 `headword`，最终回退到文件名。
  - 辅助说明 (`support_text`)：如果有 `collocations`（常见搭配）优先展示，否则回退到中文释义 `meaning_zh`。

---

### 4. 落地记忆曲线业务逻辑与拦截器 (Workflows & Validators)

#### [MODIFY] [workflows.py](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/packs/english/workflows.py)
- 移除 `review_rollover` 中的“Not yet implemented”桩代码。
- 实现硬编码的艾宾浩斯变体阶段状态机 (`day0 -> day1 -> day3 -> day7 -> day14 -> day30 -> day90 -> day180 -> mastered`)。
- 遵循契约：实现逾期保护逻辑（如果 overdue days 大于允许的延迟天数，只推迟下次复习日期而不晋升阶段）；确保对每日笔记 (Daily Notes) 默认“只读不碰”。

#### [MODIFY] [validators.py](file:///Users/jiezhengj/Documents/Project/LingoTrace/lingotrace/packs/english/validators.py)
- 强化 `validate_review_rollover`，加入对未知 `review_stage` 以及无效 `next_review` 格式的拦截（契约：脏数据当场阻断）。

---

### 5. 填补契约驱动测试用例 (Migration Matrix Tests)

#### [MODIFY] [test_english_pack.py](file:///Users/jiezhengj/Documents/Project/LingoTrace/tests/lingotrace/packs/test_english_pack.py)
- 添加测试类 `TestEnglishReviewRolloverContract`，映射《Migration Test Matrix》的全部核心故事：
  1. `test_review_rollover_previews_without_writes` (沙盒安全)
  2. `test_review_rollover_apply_advances_due_target_card` (阶段晋升)
  3. `test_review_rollover_reschedules_overdue_card` (逾期不晋升惩罚)
  4. `test_review_rollover_blocks_unknown_stage_before_write` (脏数据隔离防腐)
  5. `test_total_training_dashboard_exists_and_sorts_stably` (看板结构合法性)

---

## Verification Plan

### Automated Tests
将运行以下命令，确保英语包和底层的交互彻底过关，没有造成任何现有逻辑的退化：
- `python -m unittest tests.lingotrace.packs.test_english_pack`
- `python -m unittest discover tests` (确保放宽 target_language 没有破坏日语包的核心测试)

### Manual Verification
- 无需前端人工介入，将直接在测试报告中确认所有 `CommandReport` 输出的状态流转符合预期。
