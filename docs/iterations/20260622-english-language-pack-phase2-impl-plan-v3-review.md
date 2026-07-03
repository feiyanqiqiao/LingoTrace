# 英语语言包 Phase 2 实施计划 V3 — 严格评审报告

**评审对象**：[20260622-english-language-pack-phase2-impl-plan-v3.md](./20260622-english-language-pack-phase2-impl-plan-v3.md)

**评审基准**：与前两轮评审相同。本轮额外增加了对 V3 提供的所有代码内容的**逐行语法和运行时兼容性验证**。

---

## 一、总体判断

**评级：🟢 通过，可执行**

V3 是一份完整的、自包含的实施规格文档。所有文件内容已提供，所有设计决策已记录，合规检查清单已逐项覆盖。以下为逐项验证结果。

---

## 二、V2 缺陷的修复确认

| V2 缺陷 | V3 是否修复 | 评估 |
|----------|------------|------|
| N1：合规检查清单只覆盖 4/25+ 项 | ✅ | 4 大类全部覆盖，措辞具体 |
| N2：缺少所有文件的具体内容 | ✅ | 全部 10 个文件提供了完整内容 |
| N3：unsupported 缺少 `failure_policy` | ✅ | 已包含 `"failure_policy": "stop_before_write"` |
| N4：`item_types` 未覆盖 `pronunciation` | ✅ | 已添加，设计决策记录说明了理由 |
| N5：Open Questions 消失未记录决策 | ✅ | "设计决策记录"章节覆盖全部 4 项 |
| N6：测试用例未列出名称和断言 | ✅ | 7 个测试用例提供了完整代码 |

---

## 三、逐文件验证

### 3.1 manifest.json — ✅ 通过

逐字段验证 `lingotrace/core/manifests.py` 的 `_parse_manifest` 校验逻辑：

| 字段 | V3 值 | 加载器校验点 | 结果 |
|------|-------|-------------|------|
| `language_pack_id` | `"lingo-english"` | `str(payload.get(...))` | ✅ |
| `language_pack_version` | `"0.1.0"` | `str(payload.get(...))` | ✅ |
| `target_language` | `"en"` | `str(payload.get(...))` | ✅ |
| `capabilities` (3 个) | `source_notes`, `review_materials`, `review_rollover` | ① `isinstance(list)` ② 每个 `isinstance(dict)` ③ `id` 非空 ④ `maturity` in `{"stable","experimental","deprecated"}` ⑤ `experimental` 跳过证据校验 | ✅ |
| `unsupported_capabilities` (2 个) | `listening_notes`, `speaking_cards` | ① `isinstance(list)` ② `fallback == "none"` | ✅ |
| `default_path_roles` | 11 个角色 | `isinstance(dict)` | ✅ |
| 能力 ID 并集 | 5 个 = `PHASE0_CAPABILITY_IDS` | 测试 `issubset` | ✅ |
| `external_tools` | `[]` | 不由加载器校验（包级元数据） | ✅ |
| `language_fields` | 4 个 | 不由加载器校验（包级元数据） | ✅ |
| `templates` | 2 个 | 不由加载器校验（包级元数据） | ✅ |
| `workflow_entrypoints` | 3 个 | 不由加载器校验（包级元数据） | ✅ |
| `validators` | 2 个 | 不由加载器校验（包级元数据） | ✅ |

### 3.2 fields.json — ✅ 通过

- 4 个字段：`ipa`、`word_stress`、`part_of_speech`、`collocations`
- 每个字段有 `name`、`owner`（`"English language pack"`）、`purpose`
- 不包含 `reading`、`accent_display`、`kanji_diff`（日语字段）
- 不包含 `meaning_zh`（避免与日语包归属冲突——设计决策 #3）

### 3.3 paths.json — ✅ 通过

- 11 个路径角色，与日语包完全一致
- 路径值为跨语言通用的英文路径（如 `review/focus/vocab`）

### 3.4 workflows.py — ✅ 通过

- 5 个函数签名与日语包 `workflows.py` 对应函数一致
- `listening_notes` 和 `speaking_cards` 直接返回 `unsupported_capability` 错误
- `source_notes`、`review_materials`、`review_rollover` 在无 `vault_root` 时返回 `missing_vault_root`，有 `vault_root` 时返回 `not_yet_implemented`
- 不包含 `japanese`、`jp-`、`codex-skills` 引用
- 导入仅依赖 `lingotrace.core.reports`（标准接口）

### 3.5 validators.py — ✅ 通过

- `validate_review_materials`：检查 `item_type` 和 `review_stage`
- `validate_review_rollover`：检查 `review_stage`、`next_review`、`done_today`
- 返回 `CommandReport`（与日语包校验器一致）
- 不包含日语专属字段检查（如 `reading`、`accent_display`）

### 3.6 agent_skills/SKILL.md — ✅ 通过

- 包含用户请求→能力映射表
- 明确声明 listening 和 speaking 不支持
- 操作规则强调提取 `ipa`、`word_stress`、`part_of_speech`、`collocations`
- 不要求用户说内部工作流名称

### 3.7 templates/focus-vocab-card.md — ✅ 通过

- frontmatter 使用公共字段（`track`、`item_type`、`status`、`review_stage`、`next_review`）
- 英语专属字段：`headword`、`ipa`、`word_stress`、`part_of_speech`、`collocations`、`meaning_zh`
- 不包含日语字段

### 3.8 templates/daily-checklist.md — ✅ 通过

- 与日语包 `daily-checklist.md` 结构一致（通用模板）

### 3.9 test_english_pack.py — ✅ 通过

7 个测试用例与日语包 `test_japanese_pack.py` 对等：

| # | 英语包测试 | 日语包对等测试 | 适配点 |
|---|-----------|--------------|--------|
| 1 | `test_manifest_loads_through_core_loader` | `test_manifest_loads_through_core_loader_and_declares_all_phase0_capabilities` | 不要求所有能力 stable |
| 2 | `test_declared_capabilities_are_subset_of_phase0_ids` | 同上（部分） | 并集 = `PHASE0_CAPABILITY_IDS` |
| 3 | `test_unsupported_capabilities_have_fallback_none` | `test_unsupported_capabilities_are_explicitly_empty_for_japanese_pack` | 反转：英语包有 2 个 unsupported |
| 4 | `test_language_fields_are_english_pack_owned` | `test_language_fields_are_japanese_pack_owned_and_not_generic_core_fields` | 字段名和 owner 不同 |
| 5 | `test_default_path_roles_match_phase1_design` | `test_default_path_roles_match_phase1_design` | 路径角色完全一致 |
| 6 | `test_workflow_stubs_do_not_reference_japanese_runtime` | `test_workflows_are_declarative_and_do_not_call_old_jp_skills` | 不检查函数调用行为（桩） |
| 7 | `test_pack_owned_surfaces_exist` | `test_pack_owned_surfaces_are_manifest_declared_and_files_exist` | 不检查 `default_views`（未声明） |

**运行时兼容性确认**：
- 测试导入 `lingotrace.core.capabilities.PHASE0_CAPABILITY_IDS` 和 `lingotrace.core.manifests.load_language_pack_manifest` — 这些模块已存在于本地
- 测试读取 JSON 文件和 Python 源码（不执行工作流函数）— 不触发 `context.py` 的 `target_language` 检查
- 测试不导入 `test_japanese_pack` 或任何日语模块

---

## 四、合规检查清单逐项验证

对照 `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md`：

### Identity And Versions

| 检查项 | 状态 | 证据 |
|--------|------|------|
| Declares `language_pack_id` | ✅ | `"lingo-english"` |
| Declares `language_pack_version` | ✅ | `"0.1.0"` |
| Declares exactly one `target_language` | ✅ | `"en"` |
| Declares `transcription_locale` | ✅ | `"en-US"`（设计决策 #1） |
| Declares compatible core version range | ✅ | `0.1.0`–`0.2.0` |
| Declares compatible Vault Schema version range | ✅ | `1`–`1` |
| No target-language guessing | ✅ | Vault 显式声明 |

### Capabilities

| 检查项 | 状态 | 证据 |
|--------|------|------|
| Uses only reviewed capability IDs | ✅ | 5 个全部来自 `PHASE0_CAPABILITY_IDS` |
| Declares maturity per capability | ✅ | 3 `experimental` + 2 unsupported |
| Declares dependencies | ✅ | 均为 `depends_on: []` |
| Declares read/write paths | ✅ | 每个能力声明了路径角色 |
| Declares external tools | ✅ | `external_tools: []` |
| Stops before write on missing tool | ✅ | `failure_policy: "stop_before_write"` |
| No Japanese fallback | ✅ | 源码无日语引用（测试 #6 验证） |
| Unsupported have `fallback: "none"` | ✅ | manifest 和测试 #3 验证 |

### Pack-Owned Surface

| 检查项 | 状态 | 证据 |
|--------|------|------|
| Lists templates | ✅ | 2 个模板 |
| Lists workflow entry points | ✅ | 3 个入口 |
| Lists validators | ✅ | 2 个校验器 |
| Lists default path roles | ✅ | 11 个角色 |
| Lists language-specific fields | ✅ | 4 个字段 |
| Lists item types and tag namespace | ✅ | `["vocab","grammar","error","pronunciation"]` + `"en"` |
| Declares initialization artifacts | ✅ | 2 个产物 |
| Template files exist on disk | ✅ | 测试 #7 验证 |

### Core Boundary

| 检查项 | 状态 | 证据 |
|--------|------|------|
| Uses core review-card shell | ✅ | 模板使用 `track`/`status`/`review_stage` 等公共字段 |
| Keeps language fields outside core | ✅ | `ipa` 等仅在包内声明 |
| Preserves unknown frontmatter | ✅ | 桩函数不修改任何文件 |
| Stop on missing version/capability | ✅ | 加载器 + 能力检查 |
| No private data in public repo | ✅ | 无 Vault 数据 |
| No cross-Vault state | ✅ | 无缓存或状态持久化 |

---

## 五、与日语包的对齐性验证

| 维度 | 日语包 | 英语包 | 对齐度 |
|------|--------|--------|--------|
| manifest 加载通过 | ✅ | ✅ | ✅ |
| 能力覆盖 | 5/5 stable | 3 experimental + 2 unsupported | ✅ 合理差异 |
| 字段声明 | 5 个日语字段 | 4 个英语字段 | ✅ |
| 路径角色 | 11 个 | 11 个（完全一致） | ✅ |
| 工作流函数数 | 5 个 | 5 个（桩） | ✅ |
| 校验器函数数 | 2 个 | 2 个（桩） | ✅ |
| 模板数 | 3 个 | 2 个 | 🟡 差 1 个（无口语卡模板，因 speaking_cards 不支持） |
| views | 1 个 `.base` | 0 个 | 🟡 推迟到后续 PR（已记录） |
| 测试用例数 | 6 个 | 7 个 | ✅ |
| `__init__.py` | ✅ | ✅ | ✅ |

---

## 六、遗留的微小建议（非阻断）

以下不是缺陷，是可选的改进点：

1. **`import importlib` 未使用**：测试文件第 464 行导入了 `importlib` 但未使用。日语包测试用它来动态导入 `workflows` 模块（`importlib.import_module("lingotrace.packs.japanese.workflows")`），英语包测试不需要（用源码文本检查代替）。可以移除该导入以保持代码清洁。

2. **SKILL.md 的用户请求示例偏少**：日语包 SKILL.md 有 5 个场景映射，英语包只有 3 个（因为 listening 和 speaking 不支持）。当前数量是合理的，但后续扩展时可补充更多自然语言变体（如"这个单词怎么读？"→`review_materials` 中提取 `ipa`）。

3. **PR 描述模板**：Handoff Template 要求 PR body 包含 "target language and explanation language"。建议在实际提交 PR 时在描述中显式写明 "Target language: en, Explanation language: zh"。

---

## 七、结论

V3 是一份**可直接交给 Agent 执行的完整实施规格**。从 V1（9 个缺陷）到 V2（6 个缺陷）到 V3（0 个阻断性缺陷），迭代收敛过程健康。

**验证通过标准全部满足**：
- ✅ manifest 加载器验证通过
- ✅ 合规检查清单 25+ 项全部通过
- ✅ 7 个自动化测试设计正确
- ✅ 10 个文件内容完整且可执行
- ✅ 无日语运行时依赖
- ✅ 无私人数据泄漏风险
