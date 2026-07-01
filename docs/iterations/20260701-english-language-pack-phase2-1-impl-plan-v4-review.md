# 英语包 Phase 2.1 实施计划 V4 评审报告

**评审对象**: `20260701-english-language-pack-phase2-1-impl-plan-v4.md`
**评审日期**: 2026-07-01
**评审结论**: 🟢 通过（附 4 项补充建议）

---

## 评审依据

| 契约/代码 | 路径 | 用途 |
|---|---|---|
| 能力指引 | `docs/multilingual/language-pack-capability-guidance.zh.md` | 三级成熟度模型 |
| 看板契约 | `docs/multilingual/total-training-dashboard-user-stories.md` | 看板格式、列排序铁律 |
| 结转契约 | `docs/multilingual/review-rollover-user-stories.md` | 用户故事（含 US-4/US-5 Mastery Sink 规则） |
| 项目规范 | `AGENTS.md` | 修改与 Changelog 记录 |
| Core capabilities | `lingotrace/core/capabilities.py` | PHASE0_CAPABILITY_IDS 白名单 |
| Core manifests | `lingotrace/core/manifests.py` | manifest 校验规则 |
| 日语 workflows | `lingotrace/packs/japanese/workflows.py` | Mastery Sink 参考实现 (L288-303, L628-691) |
| 日语 validators | `lingotrace/packs/japanese/validators.py` | 校验职责边界参考 |
| 日语 SKILL.md | `lingotrace/packs/japanese/agent_skills/SKILL.md` | Agent 指令完整骨架 |
| 日语测试 | `tests/lingotrace/packs/test_japanese_workflow_previews.py` | Mastery Sink 测试参考 |
| 英语 manifest | `lingotrace/packs/english/manifest.json` | 现有能力声明与 template 格式 |

---

## 上游变更确认

上游合并的 19 个文件（+2309 行）与 V4 的对齐情况：

| 提交 | 内容 | V4 对齐状态 |
|---|---|---|
| `29f9930` Sink mastered vocab (#53) | day180 vocab 毕业沉淀到 base 词库 | ✅ §5.2 已纳入 |
| `cc99c20` Complete review materials (#52) | review_materials 完整迁移 | ✅ 不影响英语包实现 |
| `f794206` Cover user story review contracts (#50) | 契约更新（US-4/US-5 Mastery Sink 规则） | ✅ 已引用最新契约 |
| `8a56fcf` Add multilingual capability guidance (#49) | 能力指引文档 | ✅ 已在评审前置指南中引用 |

---

## V3 阻断项修复确认

| V3 Blocker | V4 状态 |
|---|---|
| B1: View 缺 `order` 字段 | ✅ 已添加，含 file.name / done_today / item_type / formula.core_text / formula.support_text / next_review |
| B2: Template 字段名不一致 (`category` vs `artifact_class`) | ✅ 已对齐为 `artifact_class` + `capability_id` |

---

## V2→V3→V4 改进确认

| 维度 | V3 状态 | V4 状态 |
|---|---|---|
| formula. 前缀 | ❌ 缺失 | ✅ §3 properties 中 `formula.core_text` / `formula.support_text` / `formula.due_flag` / `formula.next_day_flag` |
| sort done_today 方向 | ❌ ASC（已完成排前） | ✅ DESC（未完成排前） |
| 双视图 | ❌ 仅"今日总训练" | ✅ 新增"最近新增"视图 |
| Mastery Sink | ❌ 未提及 | ✅ §5.2 完整行为描述 |
| Core 影响面分析 | ⚠️ 仅列出文件 | ✅ §1.3 标注其他 5 个文件不受常量变更直接影响 |

---

## 重要缺陷

### M1. Mastery Sink 缺少英语专属稳定字段定义

**V4 §5.2** 描述了沉淀行为（"如果是 vocab 类型卡片，必须触发向 `base_vocab_root` 的沉淀"），但未指定 `_base_vocab_sink_mutation` 需要的关键参数。

**日语版参考实现**（`workflows.py:670-691`）:
```python
def _base_vocab_fields_from_focus(focus_fields: dict[str, str], title: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "track": "base_vocab",
        "item_type": "vocab",
        "status": "promoted",
        "headword": title,
    }
    for key in (
        "reading",
        "accent_display",
        "meaning_zh",
        "collocations",
        "confusable_with",
        "contrast_with",
        "kanji_diff",
        "kanji_diff_pairs",
        "source_notes",
    ):
        value = focus_fields.get(key)
        if value not in (None, ""):
            fields[key] = value
    return fields
```

**英语包需要定义自己的稳定字段列表**，基于 `fields.json` 声明的语言特有字段：
- `ipa`
- `word_stress`
- `part_of_speech`
- `english_definition`
- `collocations`
- `meaning_zh`
- `source_notes`

**风险**: 无此定义 → 执行者可能复制日语版的 key 列表 → `reading`、`accent_display`、`kanji_diff` 等日语专属字段被错误写入英语 base 卡片。

**建议**（补充到 §5.2）:
```python
_EN_STABLE_BASE_VOCAB_KEYS = (
    "ipa", "word_stress", "part_of_speech", "english_definition",
    "collocations", "meaning_zh", "source_notes",
)
```

---

### M2. ROLLOVER_ROLES 未在计划中定义

日语版 `workflows.py:23-31` 定义了 `ROLLOVER_ROLES` 元组，控制 `_cards_for_roles()` 的扫描范围。英语包需要对应定义：

```python
ROLLOVER_ROLES = (
    "focus_vocab_root",
    "grammar_root",
    "error_root",
    "pronunciation_accent_root",
    "pronunciation_phoneme_root",
)
```

需要注意：
- `base_vocab_root` 不应出现在 ROLLOVER_ROLES 中（base 词库是 Mastery Sink 的**目标**，不应被结算扫描）
- `speaking_card_root` 和 `listening_root` 在英语包 manifest 中均为 unsupported，不应纳入
- 日语版包含 `speaking_card_root` 和 `listening_root` 但英语包不应复制

**风险**: 如果执行者直接复制日语版 ROLLOVER_ROLES，会因 unsupported 路径角色不存在而报错。

**建议**: 在 §5.2 中增加此常量定义。

---

### M3. validators.py 中的 stage/date 校验边界变动需要注明

**V4 §5.1** 计划在 `validate_review_rollover` 中增加：
- `review_stage` 枚举校验（是否在已知阶段中）
- `next_review` 日期格式校验（是否匹配 YYYY-MM-DD）

**日语版**这两个校验在 `workflows.py` 中而非 `validators.py`:
```python
# workflows.py L224-245
if review_stage not in STAGE_ADVANCEMENT:
    errors.append(Finding(code="unknown_review_stage", ...))
...
try:
    original_next_review = dt.date.fromisoformat(next_review_raw)
except ValueError:
    errors.append(Finding(code="invalid_next_review", ...))
```

日语版 `validate_review_rollover` 仅校验字段存在性：
```python
def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    errors = _missing_field_errors(card, ("review_stage", "next_review", "done_today"))
    return _validation_report("validate-review-rollover", errors)
```

**差异评估**: 将 stage/date 校验前移到 validator 是合理的架构改进——validator 负责"数据格式与取值范围"，workflow 负责"状态机调度"。但计划应注明这一差异及设计意图，避免评审时的困惑。

---

### M4. 测试数量 17 与实际 15 不一致

**V4 §6** 标题写"十七条契约矩阵测试"，代码清单实际列出 15 个测试函数：

| # | 测试函数 | 来源 |
|---|---|---|
| 1 | `test_review_rollover_second_preview_has_no_remaining_planned_writes_after_apply` | US-1 |
| 2 | `test_review_rollover_applies_every_memory_curve_transition_from_run_date` | US-2/US-4 |
| 3 | `test_review_rollover_advances_when_overdue_days_equal_allowed_delay` | US-3 |
| 4 | `test_review_rollover_reschedules_overdue_card_without_advancing_stage` | US-3 |
| 5 | `test_apply_updates_done_today_review_stage_next_review_and_mastered_status` | US-4 |
| 6 | `test_review_rollover_sinks_day180_focus_vocab_to_base_without_losing_manual_body` | US-4/US-5 |
| 7 | `test_review_rollover_creates_base_vocab_when_day180_focus_vocab_has_no_base_match` | US-4/US-5 |
| 8 | `test_review_rollover_does_not_touch_daily_notes_or_non_mastered_base_vocab` | US-5/US-6/US-7 |
| 9 | `test_review_rollover_completes_when_daily_note_is_missing` | US-8 |
| 10 | `test_review_rollover_blocks_unknown_stage_before_any_write` | US-9 |
| 11 | `test_review_rollover_blocks_invalid_next_review_before_any_write` | US-9 |
| 12 | `test_validation_failure_blocks_planning_before_any_write_is_applied` | US-9 |
| 13 | `test_review_rollover_previews_due_target_card_without_writes` | Safety |
| 14 | `test_review_rollover_apply_advances_due_target_card` | Safety |
| 15 | `test_total_training_dashboard_exists_and_sorts_stably` | Dashboard |

新增的 Mastery Sink 测试（#5-#8）与最新契约的 Matrix 行完全对齐。契约 Matrix 共 16 行，其中 `Capability/write guard` 由 core 层测试覆盖，其余 15 行均已有对应测试。

**建议**: 标题改为"十五条契约矩阵测试"。

---

## 小问题

### m1. STAGE_ADVANCEMENT 和 STAGE_DAYS 未在计划中显式给出

`workflows.py` 依赖这两个字典实现记忆曲线状态机。日语版定义（`workflows.py:32-51`）：

```python
STAGE_ADVANCEMENT = {
    "day0": ("day1", 1), "day1": ("day3", 3), "day3": ("day7", 7),
    "day7": ("day14", 14), "day14": ("day30", 30), "day30": ("day90", 90),
    "day90": ("day180", 180), "day180": ("mastered", 0),
}
STAGE_DAYS = {
    "day0": 0, "day1": 1, "day3": 3, "day7": 7, "day14": 14,
    "day30": 30, "day90": 90, "day180": 180,
}
```

这些常量语言无关，英语包应原样复用。计划 §5.2 描述了行为但未给出常量定义。

### m2. `_merged_source_notes` 合并策略未说明

V4 §5.2 写"安全更新稳定字段、合并来源（sources）"，但未说明合并策略：
- 逗号拼接？wikilink 格式？
- 去重策略？（同一来源同时出现在 focus 和 base 中 → 保留一份）

日语版实现（`workflows.py:647-650`）:
```python
merged_fields["source_notes"] = _merged_source_notes(
    str(base_fields.get("source_notes", "")),
    focus_fields.get("source_notes"),
)
```

执行者需自行实现 `_merged_source_notes`，计划应给出合并规则。

### m3. SKILL.md User Language 映射表不完整

V4 §4 相比日语版缺失：

| 缺失模块 | 日语版行号 |
|---|---|
| User Language 映射表（5 行 × 3 列） | L39-L45 |
| 用户界面语言文案（5 条） | L47-L54 |
| review_materials 详细路由规则（type-specific fields） | L96-L107 |
| review_rollover 结算后报告格式 | L117-L119 |

当前 V4 SKILL.md 对所有 unsupported 能力仅有 "English listening transcription is currently unsupported." 一条通用拒绝文案。建议补全：

| User request | Agent task | Capability |
|---|---|---|
| 帮我整理这篇英语阅读材料 | Source note task | `source_notes` |
| 把这个生词加入复习 | Review material task | `review_materials` |
| 今天复习结束了，帮我结算 / 结算复习 | Review rollover task | `review_rollover` |
| 请把这段音频做成精听稿 | Unsupported | → politely reject |
| 这句话很实用，帮我做成口语卡 | Unsupported | → politely reject |

---

## 全链路对比

| 维度 | V1 | V2 | V3 | V4 | 状态 |
|---|---|---|---|---|---|
| manifest 能力格式 | ❌ | ❌ | ✅ | ✅ | ✅ |
| PHASE0 白名单 | ❌ | ❌ | ✅ | ✅ | ✅ |
| Base 原生语法 | ❌ | ❌ | ✅ | ✅ | ✅ |
| 公式语法 (`ifs` → `if`) | ❌ | ❌ | ✅ | ✅ | ✅ |
| sort 末尾 file.name | ❌ | ❌ | ✅ | ✅ | ✅ |
| order 字段 | ❌ | ❌ | ❌ | ✅ | ✅ |
| template 字段一致性 | ❌ | ❌ | ❌ | ✅ | ✅ |
| formula. 前缀 | ❌ | ❌ | ❌ | ✅ | ✅ |
| sort done_today DESC | ❌ | ❌ | ❌ | ✅ | ✅ |
| 双视图 | ❌ | ❌ | ❌ | ✅ | ✅ |
| columnSize 补全 | ❌ | ❌ | ❌ | ✅ | ✅ |
| Mastery Sink 行为 | ❌ | ❌ | ❌ | ✅ | ✅ |
| Mastery Sink 英语专属字段 | ❌ | ❌ | ❌ | ⚠️ | 待补 |
| ROLLOVER_ROLES 定义 | ❌ | ❌ | ❌ | ❌ | 待补 |
| SKILL.md 完整度 | ❌ | ❌ | ⚠️ | ⚠️ | 可行偏薄 |
| 测试覆盖 | 5/14 (36%) | 10/14 (71%) | 11/14 (79%) | 15/15 (100%) | ✅ |

---

## 建议修改清单

| 优先级 | 修改项 | 章节 |
|---|---|---|
| **实施前** | 补充 `ROLLOVER_ROLES` 常量定义（英语包范围） | §5.2 |
| **实施前** | 补充 Mastery Sink 稳定字段列表（`_EN_STABLE_BASE_VOCAB_KEYS`） | §5.2 |
| **实施前** | 补充 `STAGE_ADVANCEMENT` / `STAGE_DAYS` 常量 | §5.2 |
| 实施时注意 | validators.py 的 stage/date 校验前移是合理的架构差异，注明即可 | §5.1 |
| 实施时注意 | `_merged_source_notes` 合并策略需明确（逗号拼接 + 去重） | §5.2 |
| 可选 | 测试标题 17 → 15 | §6 |
| 可选 | SKILL.md 补全 User Language 映射表 | §4 |

---

## 结论

**通过。V4 是四个版本中第一个所有遗留阻断项均已修复的版本。上游 Mastery Sink 变更正确同步，V3 全部阻断项修复确认完成。4 个重要缺陷为实施层面的补充细节，3 个可选改进可在执行过程中按需采纳。建议执行者在实现前先落实 ROLLOVER_ROLES、稳定字段列表和 STAGE 常量，避免实施时参照日语版而误用日语专属字段。**

---

## 存续声明

- 本次评审生成了新文件 `20260701-english-language-pack-phase2-1-impl-plan-v4-review.md`
- 未修改任何现有代码或文档
- 验证依据的代码均通过 Read/Bash 工具读取并交叉验证
- 上游变更（#50/#52/#53）的 Mastery Sink 实现（`_base_vocab_sink_mutation`、`_base_vocab_fields_from_focus`、测试函数）已完整审查
