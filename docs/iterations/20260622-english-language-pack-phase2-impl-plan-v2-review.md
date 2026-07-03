# 英语语言包 Phase 2 实施计划 V2 — 严格评审报告

**评审对象**：[20260622-english-language-pack-phase2-impl-plan-v2.md](./20260622-english-language-pack-phase2-impl-plan-v2.md)

**评审基准**：与 V1 评审相同（上游日语包参考实现、Contributor Guide、Handoff Template、合规检查清单、manifest 加载器代码），额外增加：
- V1 评审报告（9 个缺陷项）
- V1 评审中的替代方案（6.3–6.10 节的具体文件内容设计）
- `lingotrace/core/context.py` 的 `SUPPORTED_TARGET_LANGUAGE = "ja"` 硬编码

---

## 一、总体判断

**评级：🟢 方向正确，需补充实施细节后可执行**

V2 对 V1 的全部 9 个缺陷做出了回应，概念层面已完全合规。但 V2 是一份**架构设计文档**，不是**实施规格文档**——它描述了要构建什么，但没有提供足够信息让实施者（或 Agent）直接编写代码。以下逐一分析。

---

## 二、V1 缺陷的修复确认

| V1 缺陷 | V2 是否回应 | 评估 |
|----------|------------|------|
| S1：缺少 `workflows.py` 和 `validators.py` | ✅ 第 2 节明确包含 | 概念完整，缺少具体代码 |
| S2：manifest 未声明 entrypoints | ✅ 第 1 节提及"接口挂载" | 未提供具体 JSON 结构 |
| S3：缺少 `test_english_pack.py` | ✅ 第 4 节明确包含 7 个测试 | 未列出测试用例名称和断言 |
| C1：字段命名与上游指引冲突 | ✅ 改用 `ipa`/`word_stress`/`part_of_speech`/`collocations` | 完全采纳 |
| C2：experimental 能力需显式说明 | ✅ 开头说明 + "运行时的说明" | 完全采纳 |
| C3：manifest 缺少 10+ 字段 | ✅ 提及 `compatible_core`/`compatible_vault_schema`/`templates`/`workflow_entrypoints`/`validators` | 未提供完整 JSON |
| C4：缺少 `templates/` 设计 | ✅ 第 3 节包含 2 个模板 | 未提供模板内容 |
| V1：缺少合规测试 | ✅ 第 4 节包含 | 未提供测试代码 |
| V2：未对照合规检查清单 | ✅ 包含 4 项检查 | 覆盖不完整（见缺陷 N1） |

**结论**：V1 的全部结构性和方向性缺陷已被修复。剩余问题集中在**实施粒度不足**。

---

## 三、V2 的新缺陷

### 缺陷 N1：合规检查清单只覆盖 4/25+ 项 ⚠️

**问题**：V2 的 "Conformance Checklist Compliance" 小节只有 4 个检查项：

```markdown
- [x] Manifest 结构完整且合法。
- [x] 包内部不存在任何 japanese 硬编码引用。
- [x] fields.json 未越权占用其它语言的特有字段。
- [x] 测试覆盖率达标，包含独立于 test_japanese_pack 的测试文件。
```

但 `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md` 包含 **4 大类 25+ 个检查项**。V2 只覆盖了其中约 4 项，且措辞模糊（如"测试覆盖率达标"未定义具体标准）。

**V1 替代方案（6.12 节）的处理方式**：逐项声明每个检查点的通过/跳过/不适用状态，包含 Identity And Versions（7 项）、Capabilities（7 项）、Pack-Owned Surface（7 项）、Core Boundary（6 项）。

**修复建议**：将合规检查清单的完整逐项对照纳入计划。至少覆盖以下关键项：

| 类别 | V2 是否覆盖 | 缺失的关键项 |
|------|------------|-------------|
| Identity And Versions | 🟡 部分 | 是否声明 `transcription_locale`？是否不猜测目标语言？ |
| Capabilities | 🟡 部分 | `unsupported_capabilities` 是否有 `fallback: "none"`？是否声明 `failure_policy`？是否声明 `external_tools`（空数组）？ |
| Pack-Owned Surface | ❌ | 是否列出 `workflow_entrypoints`？是否列出 `validators`？是否声明 `item_types` 和 `tag_namespace`？ |
| Core Boundary | ❌ | 是否使用核心 review-card shell？是否保留未知 frontmatter？是否不导入私人数据？ |

### 缺陷 N2：缺少具体文件内容（实施规格不足）

**问题**：V2 描述了每个文件的职责和设计意图，但没有提供任何文件的实际内容。以下文件缺少可直接执行的内容：

| 文件 | V2 描述了什么 | 缺少什么 |
|------|-------------|---------|
| `manifest.json` | 字段列表和设计意图 | 完整 JSON（含 `capabilities` 数组结构、`unsupported_capabilities` 格式、`workflow_entrypoints` 列表、`default_path_roles` 字典） |
| `fields.json` | 4 个字段名和目的 | 完整 JSON |
| `paths.json` | "扁平化路径角色" | 完整 JSON（11 个角色的键值对） |
| `workflows.py` | 函数行为描述 | Python 代码（函数签名、返回值结构、错误码） |
| `validators.py` | 校验字段列表 | Python 代码 |
| `SKILL.md` | 功能描述 | Markdown 内容 |
| `templates/*.md` | 字段列表 | Markdown 模板内容 |
| `test_english_pack.py` | "7 个测试用例" | 测试代码（用例名、断言内容） |

**评估**：对于一个需要交给 Agent 执行的实施计划，这个粒度是不够的。Handoff Template 的设计初衷就是让 Agent 能直接执行，而不需要再做设计决策。

**但有一个重要的上下文**：V1 替代方案（6.3–6.10 节）已经提供了所有文件的完整内容。如果 V2 的意图是"采纳替代方案的内容 + 本文件的结构描述"，那么两者合并后就是完整的实施规格。**建议**：在 V2 中明确引用替代方案的文件内容，或直接将内容嵌入。

### 缺陷 N3：manifest 的 `unsupported_capabilities` 格式需要验证

**问题**：V2 说 `unsupported_capabilities` 要提供 `fallback: "none"` 和 `failure_reason`。

**manifest 加载器的实际校验逻辑**（`_parse_unsupported_capability`，第 164-180 行）：

```python
def _parse_unsupported_capability(raw, findings):
    fallback = str(raw.get("fallback", ""))
    if fallback != "none":
        findings.append(Finding(
            code="unsupported_capability_fallback_not_none",
            message="Unsupported capabilities must declare fallback as none.",
        ))
        return None
    return UnsupportedCapability(
        id=str(raw.get("id", "")),
        failure_reason=str(raw.get("failure_reason", "")),
        failure_policy=str(raw.get("failure_policy", "")),  # ← 也被读取
        fallback=fallback,
    )
```

加载器还会读取 `failure_policy` 字段（虽然不强制校验）。日语包的 unsupported 列表为空所以没有示例，但 V1 替代方案包含了完整的格式：

```json
{
  "id": "listening_notes",
  "failure_reason": "English listening transcription tools are not yet available.",
  "failure_policy": "stop_before_write",
  "fallback": "none"
}
```

V2 没有提及 `failure_policy`。虽然加载器不会因缺失而报错（默认为空字符串），但 `UnsupportedCapability` 数据类有此字段，不填会导致运行时该字段为空。

**修复建议**：在 manifest 设计中明确包含 `failure_policy: "stop_before_write"`。

### 缺陷 N4：`item_types` 范围需要确认

**问题**：V2 声明 `item_types: ["vocab", "grammar", "error"]`，但日语包有 5 个 item_types：`vocab`, `grammar`, `pronunciation`, `error`, `speaking_card`。

英语包的字段设计包含了 `ipa` 和 `word_stress`——这些是发音相关字段。如果未来要做发音练习卡（`pronunciation` item_type），现在不声明会导致后续版本扩展时需要修改 manifest。

**评估**：这是一个设计决策点，不是缺陷。`speaking_card` 排除是合理的（`speaking_cards` 能力不支持）。`pronunciation` 是否需要取决于英语包是否计划覆盖发音训练。V2 应该对此做出明确决策并记录理由。

**建议**：添加 `pronunciation` 到 `item_types`（声明意图但不要求本 PR 实现对应能力），或在计划中显式说明"不包含 pronunciation item_type，理由是…"。

### 缺陷 N5：Open Questions 消失但未记录决策

**问题**：V1 有两个 Open Questions：

1. `transcription_locale` 设 `en-US` 是否合适？
2. 核心字典字段是否覆盖初期需求？

V2 删除了 Open Questions 章节。从 manifest 设计来看，V2 隐式选择了 `en-US` 并扩展了字段（增加了 `word_stress` 和 `part_of_speech`）。但这些决策没有显式记录。

**建议**：保留 Open Questions 章节，或将其转化为"设计决策记录"，说明每个决策的理由。

### 缺陷 N6：测试用例未列出具体内容

**问题**：V2 说"7 个合规测试用例"但没有列出用例名称或断言内容。

**日语包测试的 6 个用例**（可作为参照）：
1. `test_manifest_loads_through_core_loader_and_declares_all_phase0_capabilities`
2. `test_language_fields_are_japanese_pack_owned_and_not_generic_core_fields`
3. `test_default_path_roles_match_phase1_design`
4. `test_pack_owned_surfaces_are_manifest_declared_and_files_exist`
5. `test_workflows_are_declarative_and_do_not_call_old_jp_skills`
6. `test_validator_stubs_accept_synthetic_public_fixtures`
7. `test_unsupported_capabilities_are_explicitly_empty_for_japanese_pack`

**英语包需要适配的差异**：
- 测试 1 需要适配：英语包不是所有能力都 stable，不要求声明全部 Phase 0 能力为 stable
- 测试 6 需要适配：英语包的校验器不检查日语专属字段
- 测试 7 需要适配：英语包有 2 个 unsupported 能力（非空）

**建议**：列出 7 个测试用例的名称和核心断言，确保实施者不需要自行设计测试逻辑。

---

## 四、额外发现：核心上下文的硬编码

V2 开头提到"当前核心的上下文（`core/context.py`）只接受 `ja`"。实际代码确认：

```python
# lingotrace/core/context.py 第 13-14 行
SUPPORTED_TARGET_LANGUAGE = "ja"
SUPPORTED_EXPLANATION_LANGUAGE = "zh"
```

`load_vault_context()` 在第 82-85 行强制校验：
```python
if target_language != SUPPORTED_TARGET_LANGUAGE:
    findings.append(Finding(code="unsupported_target_language", ...))
if explanation_language != SUPPORTED_EXPLANATION_LANGUAGE:
    findings.append(Finding(code="unsupported_explanation_language", ...))
```

**这意味着**：即使英语包的 manifest 和测试全部通过，当实际加载一个 `target_language: en` 的 Vault 上下文时，核心会拒绝。

**对本 PR 的影响**：无。本 PR 不修改核心代码，英语包的 `experimental` 能力在核心层面本来就被拒绝（`CapabilityRegistry.require()` 第 53 行）。但 V2 应该在"运行时的说明"中补充：**泛化 `context.py` 不仅需要放开 `target_language`，还需要放开 `explanation_language`（因为英语包的解释语言也是 `zh`，这一点恰好兼容，但未来其他语言包可能需要不同的解释语言）**。

---

## 五、V2 与 V1 替代方案的关系

V2 在结构设计上与 V1 替代方案（评审报告 6.3–6.10 节）高度一致：

| 维度 | V2 计划 | V1 替代方案 |
|------|---------|-----------|
| 文件清单 | 描述了 10 个文件 | 列出了 11 个文件（含 `__init__.py`） |
| manifest 设计 | 描述了结构 | 提供了完整 JSON（98 行） |
| 字段设计 | 4 个字段 | 4 个字段（完全一致） |
| workflows.py | 描述了行为 | 提供了完整代码（66 行） |
| validators.py | 描述了行为 | 提供了完整代码（30 行） |
| templates | 描述了 2 个模板 | 提供了完整 Markdown 内容 |
| test | "7 个用例" | 提供了完整测试代码（80 行） |
| 合规检查 | 4 项 | 25+ 项逐项对照 |

**建议**：V2 的结构设计 + V1 替代方案的具体内容 = 完整可执行的实施规格。建议将两者合并，或在 V2 中显式引用 V1 替代方案的文件内容作为附录。

---

## 六、检查清单汇总

| # | 类型 | 缺陷 | 严重度 | 修复建议 |
|---|------|------|--------|---------|
| N1 | 内容 | 合规检查清单只覆盖 4/25+ 项 | 🟡 中 | 补充完整逐项对照 |
| N2 | 结构 | 缺少所有文件的具体内容 | 🟡 中 | 嵌入或引用 V1 替代方案内容 |
| N3 | 内容 | unsupported 缺少 `failure_policy` | 🟢 低 | 明确包含 `failure_policy` |
| N4 | 内容 | `item_types` 未覆盖 `pronunciation` | 🟢 低 | 做出显式决策并记录理由 |
| N5 | 内容 | Open Questions 消失未记录决策 | 🟢 低 | 转化为设计决策记录 |
| N6 | 内容 | 测试用例未列出名称和断言 | 🟡 中 | 列出 7 个用例的具体内容 |

**总体评价**：V2 比 V1 有质的提升——从"有结构性缺陷的骨架声明"进化为"概念完整但缺少实施细节的最小可测试包设计"。剩余的 6 个缺陷全部是**内容补充型**，不涉及方向调整。将 V2 的设计意图与 V1 替代方案的具体文件内容合并后，即可得到一份可直接交给 Agent 执行的完整实施计划。
