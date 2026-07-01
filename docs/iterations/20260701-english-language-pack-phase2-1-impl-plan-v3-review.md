# 英语包 Phase 2.1 实施计划 V3 评审报告

**评审对象**: `20260701-english-language-pack-phase2-1-impl-plan-v3.md`
**评审日期**: 2026-07-01
**评审结论**: 🟡 条件通过（修正 2 个阻断项后可执行）

---

## 评审依据

| 契约/代码 | 路径 | 用途 |
|---|---|---|
| 能力指引 | `docs/multilingual/language-pack-capability-guidance.zh.md` | 三级成熟度模型 |
| 看板契约 | `docs/multilingual/total-training-dashboard-user-stories.md` | 看板格式、列排序铁律 |
| 结转契约 | `docs/multilingual/review-rollover-user-stories.md` | 十四项迁移测试矩阵 |
| 项目规范 | `AGENTS.md` | 修改与 Changelog 记录 |
| Core capabilities | `lingotrace/core/capabilities.py` | PHASE0_CAPABILITY_IDS |
| Core manifests | `lingotrace/core/manifests.py` | manifest 校验规则 |
| 英语 manifest | `lingotrace/packs/english/manifest.json` | 现有 templates 字段命名 |
| 日语 total-training.base | `lingotrace/packs/japanese/views/total-training.base` | Obsidian Base 参照 |
| 日语 SKILL.md | `lingotrace/packs/japanese/agent_skills/SKILL.md` | Agent 指令参照 |

---

## V2→V3 改进确认

V2 的 5 个阻断项，V3 修复 3 个：

| V2 Blocker | V3 状态 |
|---|---|
| B1: manifest capabilities dict→数组 | ✅ 已修复（明确写"数组追加"） |
| B2: PHASE0_CAPABILITY_IDS 缺失 | ✅ 已修复（§1.2 追加） |
| B3: Base 格式不兼容 Obsidian | ✅ 已修复（原生 YAML-like 4 段式） |
| B4: sort 缺 file.name | ✅ 已修复（sort 以 file.name ASC 收尾） |
| B5: core context 影响面 | ⚠️ 部分修复（列出 6 个文件但未给具体修改指引） |

---

## 阻断项（修正后解除）

### B1. View 缺少 `order` 字段 — 违反契约 US-2

**V3 view 定义**:
```yaml
views:
  - type: table
    name: 今日总训练
    filters: ...
    sort: ...
    columnSize: ...
```

**日语版每个 view 包含独立的 `order` 字段**:
```yaml
views:
  - type: table
    name: 今日总训练
    filters: ...
    order:
      - file.name
      - done_today
      - formula.track_label
      - item_type
      - formula.core_text
      - formula.support_text
      - next_review
      - priority
      - error_count
      - seen_count
      - attempt_count
    sort: ...
    columnSize: ...
```

**契约依据**（`total-training-dashboard-user-stories.md` US-2）:
> file.name remains the first column in the daily review view.
> done_today remains the second column.

在 Obsidian Base 中，`order` 控制视图列的显示顺序和可见性，`sort` 控制排序。无 `order` 字段 → Obsidian 使用默认列顺序（按 properties 声明顺序或文件元数据默认顺序） → 契约要求无法保证。

**修正**: 在 view 定义中添加 `order` 数组：
```yaml
order:
  - file.name
  - done_today
  - item_type
  - formula.core_text
  - formula.support_text
  - next_review
```

---

### B2. templates 条目字段名不一致

**现有 templates 条目**（`manifest.json:125-136`）:
```json
{
  "id": "focus_vocab_card",
  "capability_id": "review_materials",
  "path": "lingotrace/packs/english/templates/focus-vocab-card.md",
  "artifact_class": "recreate-from-pack"
}
```

**V3 新条目**:
```json
{
  "id": "total_training_base",
  "path": "lingotrace/packs/english/views/total-training.base",
  "category": "recreate-from-pack"
}
```

两个差异：
1. **旧用 `artifact_class`，新用 `category`** — 字段名不一致。`test_pack_owned_surfaces_exist` 测试不区分字段名（仅遍历 `templates` 检查 path 存在），不造成功能阻断；但搜索/自动化工具无法统一识别 "recreate-from-pack" 类目。
2. **旧有 `capability_id`，新缺失** — 丢失能力归属。虽然 manifest loader 当前不校验 template 的 `capability_id`，但 `total_training_dashboard` 能力应能反向索引到其拥有的模板。

**修正**: 对齐现有字段：
```json
{
  "id": "total_training_base",
  "capability_id": "total_training_dashboard",
  "path": "lingotrace/packs/english/views/total-training.base",
  "artifact_class": "recreate-from-pack"
}
```

---

## 重要缺陷

### M1. properties 中公式字段缺少 `formula.` 前缀

**V3 properties**:
```yaml
properties:
  core_text:
    displayName: 核心内容
  support_text:
    displayName: 辅助说明
```

**日语版 properties**:
```yaml
properties:
  formula.core_text:
    displayName: 核心内容
  formula.support_text:
    displayName: 说明
```

在 Obsidian DB Folder / Base 插件中，`formula.` 前缀用于区分计算字段（由 Base 公式生成的虚拟列）和原始 frontmatter 字段。不区分会导致：
- displayName 不生效（Obsidian 不认识 `core_text` 作为属性名）
- 列头显示 `formula.core_text` 裸名而非 "核心内容"

**修正**: 在 properties 中对公式字段添加 `formula.` 前缀：
```yaml
properties:
  formula.core_text:
    displayName: 核心内容
  formula.support_text:
    displayName: 辅助说明
  formula.due_flag:
    displayName: 到期标记
  formula.next_day_flag:
    displayName: 次日入口
```

---

### M2. core_text/support_text 公式变量名不一致

**V3 formulas 中的 core_text**:
```yaml
core_text: 'if(item_type == "vocab", if(ipa, ipa, ...), ...)'
```

**V3 formulas 中的 support_text**:
```yaml
support_text: 'if(item_type == "vocab", if(collocations, collocations, ...), ...)'
```

⚠️ **日语版公式中所有 frontmatter 字段名不加引号**（如 `accent_display` 而非 `"accent_display"`），但 Obisidian Base 公式引用 frontmatter 字段时既支持裸名也支持引号——这个取决于具体的 Base 实现。如果是 Dataview 风格则需裸名，如果是 DB Folder 则两者均可。关键是要**与 `properties` 中的 key 命名一致**。

当前 properties 中声明的 `core_text`（不含 `formula.` 前缀的问题见 M1）—但公式计算的是 field 值，`properties` 负责 displayName，两者的 key 匹配机制由 Obsidian 版本决定。**这不构成阻断，但建议执行时先在本地 Obsidian 中验证公式计算正确性。**

---

### M3. 缺少 type-specific 视图

日语版 `total-training.base` 含 9 个视图：
1. 今日总训练（next_day_flag 过滤）
2. 重点复习高风险（priority/error_count 过滤）
3. 生活口语待练
4. 听力待精听
5. 发音待录音
6. アクセント待练（accent 子类型）
7. 音素待练（phoneme 子类型）
8. 最近新增（recent_flag 过滤）
9. 重复出现 / 反复出错（计数器阈值过滤）

V3 仅有 1 个视图（今日总训练）。契约不要求完全复制日语版，但英语包 `manifest.json` 声明了 `item_types: ["vocab", "grammar", "error", "pronunciation"]` — 每种类型都应至少有一个辅助视图（如"最近新增"），否则用户无法浏览"最近学了什么""哪些 card 压力大"。建议至少添加 `最近新增` 视图。

---

### M4. SKILL.md 描述仍为框架级

V3 §4 列出 6 段名称 + 一句话说明。日语版 108 行具体文本：

| V3 描述 | 实际需求 |
|---|---|
| "总训练表有问题 → 必须 Clarify" | 需要完整的两歧义意图列表 + 澄清模板 |
| "触发静默 Apply" | 需要区分"更新总训练表"="结算"（静默）vs "总训练表有点问题"（澄清）的精确短语匹配 |
| "英语专有拒绝语" | 需要覆盖 4 个能力（unsupported: listening_notes / speaking_cards / supported: 3 个）的英文/中文拒绝模板 |
| "新建自动、合并须确认、日结免确认" | 需要明确"新建"的定义边界（新建什么？）和"合并"的触发条件 |

执行者需自行填充全部内容，若对英语包不熟悉或未充分参考日语版，产出会偏离预期。**建议至少提供 Intent Recognition 的完整短语路由表。**

---

### M5. workflow 实现中 Base formula vs frontmatter 扫描混用风险

V3 §5.2 写：
> 提取出所有 `due_flag == true` 且 `done_today == true` 的笔记。

`due_flag` 是 Base 公式（`status == "active" && next_review && date(next_review) <= today()`），在 Obsidian 前端渲染。Python workflow 无法执行 Base 公式。

**日语版的正确做法**：直接扫描 frontmatter fields：
```python
if fields.get("status") != "active" or fields.get("done_today") != "true":
    continue
```

然后在构造 `next_review` 比较逻辑时自行计算 due 条件（而非引用 formula 结果）。

**修正**: §5.2 改为"扫描 frontmatter 中 `status == 'active'` 且 `done_today == true` 且 `next_review <= run_date` 的笔记"。

---

### M6. columnSize 不完整

V3 定义：
```yaml
columnSize:
  file.name: 260
  done_today: 96
```

日语版：
```yaml
columnSize:
  file.name: 260
  done_today: 96
  formula.core_text: 320
  formula.support_text: 420
```

契约 US-3 要求两列紧凑显示，宽度固定。建议补全 `formula.core_text` 和 `formula.support_text` 的宽度设置。

---

## 小问题

### m1. sort 以 `done_today` 为首排序键的设计选择

V3 sort:
```yaml
sort:
  - property: done_today
    direction: ASC
  - property: item_type
    direction: ASC
  - property: next_review
    direction: ASC
  - property: file.name
    direction: ASC
```

日语版 sort:
```yaml
sort:
  - property: first_seen
    direction: DESC
  - property: formula.priority_rank
    direction: ASC
  - property: next_review
    direction: ASC
  - property: error_count
    direction: DESC
  - property: seen_count
    direction: DESC
  - property: file.name
    direction: ASC
```

V3 以 `done_today ASC` 开头意味着**已完成**卡片排在最前（done_today = false → false < true → ASC 先 false）。这与"今日总训练"的语义相反——用户想看的是**待完成**的卡片。

更合理的方案：`done_today DESC`（未完成 → true 排在前面），或像日语版用 `first_seen DESC`。

### m2. §1.3 影响面分析仍缺具体指引

V3 §1.3 列出 6 个受影响文件，但未给出每个文件的具体修改指引（仅对 `test_context.py` 给出了精确行号变更）。其余 5 个文件仅说"确保通过"。

这些文件使用硬编码字符串 `"ja"` 构造 `VaultContext`。修改 core context 的 `SUPPORTED_TARGET_LANGUAGES`（常量改为 tuple）后：
- 这些测试文件直接用 `target_language="ja"` 构造 `VaultContext`，不调用 `_parse_context` → **不受常量影响**
- 只有 `test_context.py` 中 `test_rejects_unsupported_target_language` 受影响

但 `test_capabilities.py` 中 `test_declared_capabilities_are_subset_of_phase0_ids` 有 `assertEqual(PHASE0_CAPABILITY_IDS, declared_ids)` — 现在 PHASE0 多了一个 ID，英语包 manifest 也必须声明 `total_training_dashboard`，此测试才能通过。这是个**联动依赖**：capabilities.py 加了 `total_training_dashboard`，manifest.json 也必须声明它。

### m3. `Mastered` status 处理未声明

记忆曲线 `day180 → mastered` 后的 behavior：
- `status` 设为 `"mastered"`
- `next_review` 清空（不再调度）

V3 计划未提及此逻辑（§5.2 只提晋升和惩罚）。契约 US-4 明确要求。日语版实现：`updates["status"] = "mastered"` 且 `to_next_review = ""`。

---

## 评审结论

**条件通过。修正 2 个阻断项后即可执行。**

### 必须修改（解除阻断）

| # | 修改项 | 章节 | 影响 |
|---|---|---|---|
| 1 | View 添加 `order` 字段 | §3 | 否则列顺序不保证 |
| 2 | Template 字段名对齐：`category`→`artifact_class`，补 `capability_id` | §2.2 | 否则字段不一致 |

### 强烈建议修改

| # | 修改项 | 章节 | 影响 |
|---|---|---|---|
| 3 | properties 公式字段加 `formula.` 前缀 | §3 | 否则 displayName 不生效 |
| 4 | sort `done_today ASC` → `done_today DESC` | §3 | 否则已完成卡片排在最前 |
| 5 | §5.2 修正为 frontmatter 扫描逻辑 | §5.2 | 否则执行者实现错误 |
| 6 | 补充 day180→mastered 行为 | §5.2 | 否则契约 US-4 缺失 |
| 7 | 追加 `最近新增` 视图 | §3 | 否则看板功能过于单薄 |

### 可选修改

| # | 修改项 | 章节 |
|---|---|---|
| 8 | `columnSize` 补齐 core_text / support_text | §3 |
| 9 | SKILL.md 补充完整短语路由表 | §4 |
| 10 | §1.3 标注其他 5 个测试文件不受 core 常量变更影响 | §1.3 |

---

## 全链路追踪

| 维度 | V1 | V2 | V3 | 目标 |
|---|---|---|---|---|
| manifest 能力格式 | N/A（未声明） | ❌ dict 对象 | ✅ 数组 | ✅ |
| PHASE0_CAPABILITY_IDS | N/A | ❌ 未提及 | ✅ §1.2 | ✅ |
| Base 语法 | N/A（写 templates/） | ❌ 简化 JSON | ✅ Obsidian 原生 | ✅ |
| 公式语法 | N/A | ❌ ifs() | ✅ if() | ✅ |
| sort 末尾 file.name | N/A | ❌ 缺失 | ✅ | ✅ |
| 测试覆盖 | 5/14 (36%) | 10/14 (71%) | 11/14 (79%) | ✅ 11/14 |
| View order | N/A | N/A | ❌ 缺失 | ⚠️ |
| Template 字段一致性 | N/A | N/A | ❌ 不一致 | ⚠️ |
| properties formula. 前缀 | N/A | N/A | ❌ 缺失 | ⚠️ |

---

## 存续声明

- 本次评审生成了新文件 `20260701-english-language-pack-phase2-1-impl-plan-v3-review.md`
- 未修改任何现有代码或文档
- 验证依据的代码均通过 Read/Bash 工具读取并交叉验证
