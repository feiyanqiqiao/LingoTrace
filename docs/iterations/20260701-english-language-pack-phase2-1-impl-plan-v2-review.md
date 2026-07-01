# 英语包 Phase 2.1 实施计划 V2 评审报告

**评审对象**: `20260701-english-language-pack-phase2-1-impl-plan-v2.md`
**评审日期**: 2026-07-01
**评审结论**: 🔴 需要修改后重新提交

---

## 评审依据

| 契约/代码 | 路径 | 用途 |
|---|---|---|
| 能力指引 | `docs/multilingual/language-pack-capability-guidance.zh.md` | 三级成熟度模型与能力边界 |
| 看板契约 | `docs/multilingual/total-training-dashboard-user-stories.md` | 看板格式、意图隔离、字段降级 |
| 结转契约 | `docs/multilingual/review-rollover-user-stories.md` | 十项用户故事与测试矩阵 |
| 项目规范 | `AGENTS.md` | 修改与 Changelog 记录 |
| Core manifests | `lingotrace/core/manifests.py` | manifest 解析格式与校验规则 |
| Core capabilities | `lingotrace/core/capabilities.py` | PHASE0_CAPABILITY_IDS 白名单 |
| Core context | `lingotrace/core/context.py` | Vault context 加载与校验 |
| 日语 workflows | `lingotrace/packs/japanese/workflows.py` | 唯一通过契约的参考实现 |
| 日语 total-training.base | `lingotrace/packs/japanese/views/total-training.base` | Obsidian Base 原生格式参考 |
| 日语 SKILL.md | `lingotrace/packs/japanese/agent_skills/SKILL.md` | Agent 指令骨架参考 |
| 英语 manifest | `lingotrace/packs/english/manifest.json` | 当前实现格式 |
| 英语 fields | `lingotrace/packs/english/fields.json` | 当前字段 schema |
| 核心测试 | `tests/lingotrace/core/test_context.py` | core 解耦影响面 |

---

## V1→V2 改进确认

上一轮评审的 3 个阻断项部分修复：

| V1 Blocker | V2 状态 | 评估 |
|---|---|---|
| B1: dashboard 路径错误 | 路径改为 `views/total-training.base` | ✅ 已修复 |
| B2: 测试覆盖 36% | 10 个测试，覆盖约 93% Matrix | ⚠️ 仍缺 1 个 |
| B3: core context 影响面未分析 | 新增 §1.2 修复 test_context.py | ⚠️ 遗漏其他 5 个测试文件 |

---

## 阻断项 (Blockers)

### B1. manifest.json capability 声明格式不兼容

**计划 §2.2 写**:
```json
"capabilities": {
  "total_training_dashboard": {
    "maturity": "stable",
    ...
  }
}
```

**实际格式是数组**（`manifests.py:77` → `capability_payloads = payload.get("capabilities", [])`，`manifests.py:94` → `for raw in capability_payloads`，`manifests.py:95` → `isinstance(raw, dict)`）。

dict 作迭代 → key 字符串 → `isinstance("total_training_dashboard", dict)` = `False` → 每个 key 产生 `invalid_capability_shape` 错误 → 整份 manifest 加载失败 → `test_manifest_loads_through_core_loader` 必然失败。

**正确格式**（对齐现有 `capabilities` 数组）:
```json
{
  "id": "total_training_dashboard",
  "maturity": "experimental",
  "depends_on": [],
  "read_path_roles": [
    "focus_vocab_root", "base_vocab_root", "grammar_root",
    "error_root", "pronunciation_accent_root", "pronunciation_phoneme_root",
    "daily_notes_root"
  ],
  "write_path_roles": [],
  "external_tools": [],
  "behavior_evidence": [],
  "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
  "manual_review_cases": []
}
```

---

### B2. `total_training_dashboard` 不在 PHASE0_CAPABILITY_IDS 白名单中

`lingotrace/core/capabilities.py:10-16`:
```python
PHASE0_CAPABILITY_IDS = {
    "listening_notes",
    "source_notes",
    "review_materials",
    "speaking_cards",
    "review_rollover",
}
```

`CapabilityRegistry.require()` 第 31 行：
```python
if capability_id not in PHASE0_CAPABILITY_IDS:
    return _rejected(capability_id, "unknown_capability", ...)
```

即使用正确的数组格式声明能力，任何通过 `CapabilityRegistry` 的校验都会拒绝 `total_training_dashboard`。

**两个选择**:
- **方案 A**: 在 `PHASE0_CAPABILITY_IDS` 中加入 `"total_training_dashboard"`
- **方案 B**: 在计划中注明 `total_training_dashboard` 不通过 Registry 校验（看板是 Base 模板渲染，不走能力注册路径）

方案 A 会引入一个新 Phase0 ID，影响 `test_declared_capabilities_are_subset_of_phase0_ids`。建议选 A 并在计划中补充 `capabilities.py` 的修改项。

---

### B3. total-training.base 格式与 Obsidian Base 不兼容

**V2 计划**使用简化 JSON：
```json
{
  "type": "database",
  "views": [{ "columns": [...], "filters": [...], "sort": [...] }],
  "formulas": {
    "core_text": "ifs(item_type=='vocab', ...)",
    "support_text": "ifs(item_type=='vocab', ...)"
  }
}
```

**日语包实际格式**是 Obsidian Base 原生结构（YAML-like，4 个顶层区块）：

```yaml
filters:          # 全局过滤
  and:
    - file.ext == "md"
    - or:
        - track == "class_review"
        ...
formulas:         # 公式定义
  core_text: 'if(item_type == "vocab", if(accent_display, ...), ...)'
properties:       # 字段显示名映射
  done_today:
    displayName: 今日完成
views:            # 视图定义（每个 view 含 filters/sort/columnSize）
  - type: table
    name: 今日总训练
    filters: ...
    sort:
      - property: first_seen
        direction: DESC
      - property: file.name
        direction: ASC
    columnSize:
      file.name: 260
```

**三个致命差异**：

| 维度 | V2 计划 | Obsidian Base 实际 | 后果 |
|---|---|---|---|
| 公式语法 | `ifs(cond, val, ...)` | `if(cond, true_val, false_val)` | 公式不执行，看板无内容 |
| 结构层次 | 3 段（views/formulas 顶层） | 4 段（filters/formulas/properties/views） | properties 缺失 = 字段无 displayName |
| 视图过滤 | 在 view 内用 `{"field": "due_flag", "operator": "==", "value": true}` | 在 view 内用 `filters: next_day_flag == true` | 过滤不生效 |

**修正方向**: 以日语 `total-training.base` 为模板，替换为英语字段名和各类型的 display mapping。

---

### B4. 看板 sort 违反契约铁律

**契约 US-2**:
> Sorting remains deterministic and ends with file.name.

**V2 sort**:
```json
"sort": [
  {"field": "done_today", "direction": "asc"},
  {"field": "item_type", "direction": "asc"},
  {"field": "next_review", "direction": "asc"}
]
```

末尾没有 `file.name`。日语版 sort 以 `{"property": "file.name", "direction": "ASC"}` 收尾。必须追加。

---

### B5. Core context 变更影响面仍不完整

**计划 §1.2** 只修 `tests/lingotrace/core/test_context.py` 的 `test_rejects_unsupported_target_language`。

**遗漏的 5 个测试文件**（均含 `target_language: "ja"` 硬编码）：

| 测试文件 | 行号 | 影响 |
|---|---|---|
| `tests/lingotrace/core/test_capabilities.py` | L13, L47 | `VaultContext` 构造参数 |
| `tests/lingotrace/core/test_paths.py` | L16 | `VaultContext` 构造参数 |
| `tests/lingotrace/core/test_manifests.py` | L15 | `target_language` 断言 |
| `tests/lingotrace/core/test_mutations.py` | L21, L37 | `vault-context.json` payload |
| `tests/lingotrace/packs/test_japanese_workflow_previews.py` | L22 | `vault-context.json` payload |

这些文件不直接依赖 `context.py` 的常量（它们硬编码 `"ja"`），但需验证在上下文解耦后仍能通过。计划 §7 已列出回归测试命令，覆盖这些文件，但未在计划正文中分析影响面。

---

## 重要缺陷 (Major Issues)

### M1. maturity "stable" 不满足校验条件且语义不对

`manifests.py:140-146`:
```python
if maturity == "stable" and (not behavior_evidence or not (conformance_tests or manual_review_cases)):
    findings.append(Finding(code="stable_capability_missing_evidence", ...))
```

V2 提供 `"behavior_evidence": ["EN-DASHBOARD-001"]` 和 conformance_tests，语法上可过。但语义上：
- `total_training_dashboard` 在 `language-pack-capability-guidance.zh.md` 中状态为 **Reference Guidance**（底线：不阻断 PR）
- 所有现有英语能力（source_notes / review_materials / review_rollover）均为 `"experimental"`
- 设为 `"stable"` 不一致且不诚实

建议: `"maturity": "experimental"`。

---

### M2. templates 声明方式错误

`manifest.json:124` 已存在 `templates` 数组：
```json
"templates": [
  {"id": "focus_vocab_card", ...},
  {"id": "daily_checklist", ...}
]
```

计划写"在顶层追加 templates 数组"→ 会产生两个 `templates` key，第二个覆盖第一个，丢失 focus_vocab_card 和 daily_checklist 声明。

改为"在现有 `templates` 数组中追加一项"。

---

### M3. SKILL.md 重写仍过于笼统

V2 计划列出 4 点要求（Intent Recognition / User Language / Write Guards / 意图隔离），但无具体结构和内容。日语 SKILL.md 108 行包含：

- 6 个意图家族（Intent Families）+ 对应短语路由规则
- 完整 User Language 映射表（5 种请求 → Agent 任务 → 能力）
- 风险分级操作规则（新建自动 / 合并确认 / 结算免二次确认）
- 各能力的详细行为描述（搜索策略、去重、确认策略、报告格式）
- 明确的禁止项（并行 review-state.json、直写 Vault 文件）

V2 未回应这些需求。若执行者仅按 4 点概括自行发挥，产出的 SKILL.md 大概率与日语版差距巨大。

---

### M4. total-training.base 缺失关键结构

与日语版对比，V2 缺失：

| 缺失结构 | 契约要求 | 后果 |
|---|---|---|
| `filters` 全局区块 | 无明确要求，但日语版有 track 过滤 | 看板包含非英语包记录 |
| `next_day_flag` 公式 | US-1: "filters on formula.next_day_flag == true" | 今日总训练视图无过滤条件 |
| `properties` 区块 | 所有 displayName 映射 | 看板列无中文显示名 |
| `columnSize` 配置 | US-2: "file.name has a stable width limit" | 文件名列宽度不固定 |
| `due_flag` 公式 | US-1: daily review queue 需要 | `next_day_flag` 依赖它 |

V2 有 `due_flag` 公式但放在顶层 `formulas` 中，它实际上需要 `next_review` 和 `last_reviewed` 的完整逻辑。

---

### M5. 测试仍缺一个 Matrix 行

V2 列出 10 个测试，对应 Matrix 14 行。上次缺失 6 个，本次缺 1 个：

| Matrix 行 | 对应测试 | V2 状态 |
|---|---|---|
| test_review_rollover_blocks_unknown_stage_before_any_write | ✅ | 已列出 |
| test_review_rollover_blocks_invalid_next_review_before_any_write | ✅ | 已列出 |
| **test_validation_failure_blocks_planning_before_any_write_is_applied** | ❌ | **缺失** |

US-9 的第三个测试：验证校验失败后计划阶段不产生任何写入，与"阻断未知 stage"和"阻断无效 next_review"是不同的测试维度。

---

### M6. fields.json 新增字段 schema 不兼容

计划 §2.1 新增字段：
```json
{
  "name": "english_definition",
  "type": "string",
  "description": "English definition of the word",
  "owner": "English language pack",
  "required": false
}
```

现有 `fields.json` 字段格式：
```json
{
  "name": "ipa",
  "owner": "English language pack",
  "purpose": "IPA phonetic transcription for English review items."
}
```

现有 schema 无 `type`、`description`、`required` 字段。需对齐现有格式或更新 fields.json schema。

---

## 小问题 (Minor Issues)

### m1. 工作计划过度强调"自动静默"机制

V2 §4.4：
> review_rollover 必须无弹窗后台静默 Preview -> Apply -> Preview

契约规定：
- "今天复习结束了，帮我结算" → 免二次确认 ✅
- "处理一下总训练表" / "总训练表有点问题" → 必须澄清 ❌ V2 未区分

把"静默"设为默认规则会覆盖需要澄清的场景。

### m2. FileMutation action 命名不对齐

V2 §5.2 写"动作皆为 `update`"。日语 `review_rollover` 用 `action="apply_review_rollover"`。建议对齐。

### m3. `_target_context_errors` 缺少 capability enablement 检查

计划说检查 `target_language` 和 `language_pack`。日语版还检查 `capability_id in enabled_capabilities`。缺失此检查 → workflow 可能在禁用能力的 Vault 上运行。

### m4. 公式中 `english_definition` 引用不一致

§3.1 `core_text` 公式：
```
ifs(item_type=='vocab', if(not(empty(ipa)), ipa, if(not(empty(english_definition)), english_definition, if(not(empty(headword)), headword, meaning_zh))), ...)
```

回退链为 `ipa → english_definition → headword → meaning_zh`，合理。但 `english_definition` 字段尚未在 `fields.json` 中定义（计划 §2.1 添加），且日语 Base 用的是 `if(not(..., ""))` 而非 `not(empty(...))`。Obsidian 的 `empty()` 函数行为需要确认。

---

## 建议修改清单

| 优先级 | 修改项 | 章节 |
|---|---|---|
| P0 | manifest capabilities 从 dict 改为数组（对齐现有格式） | §2.2 |
| P0 | PHASE0_CAPABILITY_IDS 加入 `total_training_dashboard`（或注明绕过策略） | §2.2 |
| P0 | total-training.base 改为 Obsidian Base 原生 4 段式（filters/formulas/properties/views） | §3.1 |
| P0 | sort 末尾追加 `file.name ASC` | §3.1 |
| P1 | 补充 core context 变更影响面分析（6 个测试文件） | §1.2 |
| P1 | maturity 改为 "experimental" + 移除 behavior_evidence | §2.2 |
| P1 | templates 改为"追加到现有数组" | §2.2 |
| P1 | total-training.base 补充 filters/properties/columnSize/next_day_flag | §3.1 |
| P1 | total-training.base 公式语法 `ifs` → `if` | §3.1 |
| P1 | SKILL.md 提供具体结构骨架（6 段 × 108 行对标日语版） | §4 |
| P2 | fields.json 新增字段对齐现有 schema | §2.1 |
| P2 | 补 `test_validation_failure_blocks_planning_before_any_write_is_applied` | §6 |
| P2 | FileMutation action `update` → `apply_review_rollover` | §5.2 |
| P2 | `_target_context_errors` 加入 capability enablement 检查 | §5.2 |
| P2 | 区分"免二次确认"与"必须澄清"的意图路由规则 | §4 |

---

## 附录：total-training.base 结构对照

### 日语版（参考实现）

```
filters:          ← 全局过滤（track 白名单）
formulas:         ← 公式定义（core_text/support_text/due_flag/next_day_flag/...）
properties:       ← 字段 displayName 映射（30+ 字段）
views:            ← 视图数组（9 个视图，每个含 filters/sort/columnSize）
```

### V2 计划（当前）

```
views:            ← 视图数组（1 个视图，含 columns/filters/sort 但格式错误）
formulas:         ← 公式定义（2 个公式，语法错误）
```

### 建议最小结构

```
filters:
  and:
    - file.ext == "md"
formulas:
  due_flag: if(status == "active" && next_review && date(next_review) <= today() && !(last_reviewed && date(last_reviewed) >= today()), true, false)
  next_day_flag: if(status == "active" && next_review && date(next_review) <= today() + "1d" && !(last_reviewed && date(last_reviewed) >= today()), true, false)
  core_text: (4-item_type 完整映射)
  support_text: (4-item_type 完整映射)
properties:
  file.name:
    displayName: 文件名
  done_today:
    displayName: 今日完成
  ... (所有 view 中出现的字段)
views:
  - type: table
    name: 今日总训练
    filters:
      and:
        - formula.next_day_flag == true
    sort:
      - property: file.name
        direction: ASC
    columnSize:
      file.name: 260
      done_today: 96
```

---

## 存续声明

- 本次评审生成了新文件 `20260701-english-language-pack-phase2-1-impl-plan-v2-review.md`
- 未修改任何现有代码或文档
- 验证依据的代码均通过 Read/Bash 工具读取并交叉验证
