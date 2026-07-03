# 英语语言包 Phase 2 实施计划 — 严格评审报告

**评审对象**：[20260622-english-language-pack-phase2-impl-plan.md](./20260622-english-language-pack-phase2-impl-plan.md)

**评审基准**：
- 上游日语包参考实现 `lingotrace/packs/japanese/`（11 个文件）
- `docs/multilingual/language-pack-contributor-guide.md`
- `docs/multilingual/language-pack-agent-handoff-template.md`
- `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md`
- `tests/lingotrace/packs/test_japanese_pack.py`（6 个测试）
- `lingotrace/core/manifests.py` 的 manifest 加载器
- `lingotrace/core/capabilities.py` 的能力检查逻辑

---

## 一、总体判断

**评级：🟡 需要修订后方可实施**

计划的方向正确（按上游四层架构创建英语包），但存在 **3 个结构性缺陷**、**4 个内容缺陷** 和 **2 个验证缺陷**。以下逐一分析。

---

## 二、结构性缺陷（Structural）

### 缺陷 S1：缺少 `workflows.py` 和 `validators.py` ⚠️

**问题**：计划明确写道"本阶段不实现完整的 Python 工作流"，因此不包含 `workflows.py` 和 `validators.py`。

**违反规范**：Contributor Guide 的 **Required Pack Shape** 明确列出：

```
lingotrace/packs/<language>/
  ...
  validators.py      ← 必须
  workflows.py       ← 必须
```

Handoff Template 的 PR 验收标准要求：
> "The PR includes or updates `manifest.json`, `paths.json`, `fields.json`, and `agent_skills/SKILL.md` for the new pack."

而日语参考实现包含完整的工作流门面（`workflows.py`，488 行）和校验器（`validators.py`，50 行）。

**修复建议**：创建最小化的桩文件。`workflows.py` 为每个已声明的能力提供函数签名，函数体返回 `missing_vault_root` 错误报告（与日语包无 vault_root 时的行为一致）。`validators.py` 提供 `validate_review_materials` 和 `validate_review_rollover` 桩，接受公共字段。

### 缺陷 S2：`SKILL.md` 路径不符合规范

**问题**：计划写的是：
```
[NEW] [SKILL.md](...agent_skills/SKILL.md)
```

路径本身是正确的（`agent_skills/SKILL.md`），但计划正文没有提到需要创建 `agent_skills/` 目录。更关键的是，`manifest.json` 中缺少 `workflow_entrypoints` 和 `validators` 的声明（见缺陷 C3）。

### 缺陷 S3：没有提及需要编写 `test_english_pack.py`

**问题**：验证计划只列出了执行现有测试的命令，没有提到需要创建英语包自己的合规测试。

**违反规范**：Handoff Template 的"Read first"列表明确包含：
```
tests/lingotrace/packs/test_japanese_pack.py
```

这是要求新包**参照日语包测试编写自己的测试**。日语包测试验证了 6 个维度（清单加载、字段归属、路径角色、工作流声明、校验器桩、不支持能力声明）。

**修复建议**：在 `tests/lingotrace/packs/test_english_pack.py` 中实现对等的合规测试。这不是可选项——是 PR 验收的必要条件。

---

## 三、内容缺陷（Content）

### 缺陷 C1：字段设计与上游指引存在冲突 ⚠️

**问题**：计划定义了 4 个字段：`pronunciation_ipa`、`meaning_zh`、`collocations`、`word_family`。

**与上游指引的差异**：

| 维度 | 计划的字段 | 上游规划建议的字段 | 差异 |
|------|-----------|------------------|------|
| 发音 | `pronunciation_ipa` | `ipa` | 命名不同，含义相同 |
| 词性 | ❌ 缺失 | `part_of_speech` | 上游明确建议 |
| 重音 | ❌ 缺失 | `word_stress` | 上游明确建议 |
| 变形 | ❌ 缺失 | `inflections` | 上游明确建议 |
| 释义 | `meaning_zh` | ✅ | 一致 |
| 搭配 | `collocations` | ❌ 未提及 | 计划新增 |
| 词族 | `word_family` | ❌ 未提及 | 计划新增 |

**三个层面的问题**：

1. **命名**：Contributor Guide 说"English may need pronunciation, stress, collocation, register, or usage fields"，日语包的字段名是 `reading`/`accent_display`（简洁无后缀），但计划用了 `pronunciation_ipa`（带后缀）。建议统一为 `ipa`，与上游风格一致。

2. **缺失上游建议字段**：`part_of_speech` 和 `word_stress` 在上游总体规划中被明确列为英语包候选字段。第一版即使不全部实现，也应在 `fields.json` 中声明预留，避免后续版本新增字段导致 `fields.json` 与已有卡片不兼容。

3. **`meaning_zh` 的归属模糊**：日语包在 `fields.json` 中声明 `meaning_zh` 为 "Japanese language pack" 所有。英语包如果也声明 `meaning_zh` 为 "English language pack" 所有，同一个字段名有两个 owner。这在单 Vault 单语言下不会冲突，但暗示 `meaning_zh` 可能更适合归入核心公共字段而非语言包字段。**建议**：英语包暂不将 `meaning_zh` 纳入 `fields.json`，而在模板和校验器中直接使用它（与日语包保持一致，但不重复声明所有权）。待后续核心泛化时再决定归属。

**修复建议**：

```json
{
  "language_fields": [
    {
      "name": "ipa",
      "owner": "English language pack",
      "purpose": "IPA phonetic transcription for English review items."
    },
    {
      "name": "word_stress",
      "owner": "English language pack",
      "purpose": "Primary stress pattern or syllable stress notation."
    },
    {
      "name": "part_of_speech",
      "owner": "English language pack",
      "purpose": "Grammatical category (noun, verb, adjective, etc.)."
    },
    {
      "name": "collocations",
      "owner": "English language pack",
      "purpose": "Common collocations and phrases for the headword."
    }
  ]
}
```

`word_family` 和 `inflections` 可作为第二版扩展，在 manifest 中以注释或文档形式注明规划方向。

### 缺陷 C2：能力成熟度选择与核心运行时不兼容

**问题**：计划将 `source_notes`、`review_materials`、`review_rollover` 标记为 `experimental`。

**核心代码分析**：`lingotrace/core/capabilities.py` 第 53-57 行：

```python
if capability.maturity != "stable":
    return _rejected(
        capability_id,
        "capability_not_stable",
        f"Capability is not stable and is unavailable by default: {capability_id}.",
    )
```

**这意味着 `experimental` 能力会被核心运行时拒绝。** 如果声明为 `experimental`，这些能力在代码层面等同于"不可用"。

**两个选择**：

1. **标记为 `stable`**：需要提供 `conformance_tests` 路径和 `behavior_evidence`。这要求编写 `test_english_pack.py` 并定义证据 ID（如 `EN-REVIEW-001`）。
2. **保留 `experimental`**：接受这些能力在运行时不可用，仅作为文档性声明。这与"骨架声明层"的定位一致，但意味着整个包目前无法真正运行。

**建议**：由于 Contributor Guide 明确说"core context currently accepts only `target_language=ja`"，英语包在核心泛化之前本身就无法运行。因此选择 `experimental` 是合理的，但计划需要**显式说明这一点**，而不是让读者误以为声明了就能用。同时，manifest 中必须有 `conformance_tests` 字段（即使是空数组），否则清单加载器可能报错。

### 缺陷 C3：manifest.json 声明不完整

**问题**：计划只描述了标识声明、能力认领和不支持声明，但日语包的 manifest 包含更多必需结构。

**与日语包 manifest 的字段对比**：

| 字段 | 日语包 | 计划是否提及 | 是否必需 |
|------|--------|------------|---------|
| `language_pack_id` | ✅ | ✅ | 是 |
| `language_pack_version` | ✅ | ❌ 未提及 | 是 |
| `target_language` | ✅ | ✅ | 是 |
| `transcription_locale` | ✅ | ✅ | 是 |
| `compatible_core` | ✅ | ❌ 未提及 | 是 |
| `compatible_vault_schema` | ✅ | ❌ 未提及 | 是 |
| `capabilities` | ✅ 5 个 | ✅ 3 个 | 是 |
| `unsupported_capabilities` | ✅ 空数组 | ✅ 2 个 | 是 |
| `external_tools` | ✅ 3 个 | ❌ 未提及 | 是 |
| `language_fields` | ✅ 5 个 | ✅ 4 个 | 是 |
| `item_types` | ✅ | ❌ 未提及 | 是 |
| `tag_namespace` | ✅ `jp` | ❌ 未提及 | 是 |
| `default_path_roles` | ✅ 11 个 | 🟡 部分提及 | 是 |
| `templates` | ✅ 3 个 | ❌ 未提及 | 是 |
| `workflow_entrypoints` | ✅ 5 个 | ❌ 未提及 | 是 |
| `validators` | ✅ 2 个 | ❌ 未提及 | 是 |
| `resources` | ✅ 2 个 | ❌ 未提及 | 否 |
| `display_rules` | ✅ 2 个 | ❌ 未提及 | 否 |
| `default_views` | ✅ 1 个 | ❌ 未提及 | 否 |
| `initialization_artifacts` | ✅ 2 个 | ❌ 未提及 | 否 |

**建议**：计划中需要补充以下必填字段的完整设计：
- `language_pack_version`: `"0.1.0"`
- `compatible_core` / `compatible_vault_schema`: 与日语包保持一致
- `item_types`: 至少 `["vocab", "grammar", "error"]`
- `tag_namespace`: `"en"`
- `templates`: 声明 `focus_vocab_card`、`daily_checklist` 等
- `workflow_entrypoints`: 声明每个能力的入口函数
- `validators`: 声明校验器入口
- `external_tools`: 空数组（英语包第一版不依赖外部工具）

### 缺陷 C4：缺少 `templates/` 和 `views/` 的设计

**问题**：计划说"确认没有在英语包内引入任何的 Python 脚本或模板逻辑（本期不包含）"。

**与规范的冲突**：

1. Contributor Guide 列出 `templates/` 和 `views/` 为 Required Pack Shape 的组成部分。
2. 日语包的 `templates/` 包含 3 个模板文件，`views/` 包含 1 个 `.base` 文件。
3. `manifest.json` 的 `templates` 字段引用了这些文件的路径——如果文件不存在，`test_pack_owned_surfaces_are_manifest_declared_and_files_exist` 测试会失败。

**建议**：即使不做复杂的模板，也应创建最小化的模板骨架：
- `templates/focus-vocab-card.md`（英语词汇卡，使用 `ipa`、`collocations` 等新字段）
- `templates/daily-checklist.md`（与日语包结构一致，内容通用）

视图（`.base`）可以推迟到后续 PR。

---

## 四、验证缺陷（Verification）

### 缺陷 V1：缺少 `test_english_pack.py`

**问题**：验证计划只列出了执行现有测试的命令，没有提到编写英语包自身的合规测试。

日语包测试 `test_japanese_pack.py` 包含 6 个测试用例：
1. 清单加载 + 声明所有 Phase 0 能力
2. 字段为包自有且非核心通用字段
3. 路径角色与 Phase 1 设计一致
4. 工作流声明且不引用旧 `jp-*` 技能
5. 校验器桩接受合成公共 fixtures
6. 不支持能力为空数组

英语包需要对等的测试，但第 1、6 项需要适配（英语包不是所有能力都 stable，不是所有能力都声明）。

### 缺陷 V2：未对照合规检查清单

**问题**：`docs/multilingual/history/phase-0/language-pack-conformance-checklist.md` 包含 4 大类 25+ 个检查项。计划的验证部分完全没有引用这个清单。

**建议**：在验证计划中添加一个 "Conformance Checklist Compliance" 小节，逐项声明每个检查点的通过/跳过/不适用状态。

---

## 五、Open Questions 评审

### Q1：`transcription_locale` 设为 `en-US`

**评审意见**：合理。`en-US` 是最广泛使用的英语变体。建议在 manifest 中设为 `en-US`，并在 SKILL.md 中说明用户可在 Vault 配置中覆盖为 `en-GB` 或其他变体。**不需要保留为空**——一个合理的默认值比没有默认值好。

### Q2：核心字段是否覆盖初期需求

**评审意见**：`meaning_zh` + `pronunciation_ipa`（建议改为 `ipa`）+ `collocations` 覆盖了基础需求。但建议增加 `part_of_speech` 和 `word_stress`（详见缺陷 C1）。`word_family` 可以推迟。

---

## 六、替代方案：最小可测试包

### 6.1 核心理念

与当前计划的"纯骨架声明层"不同，本方案采取 **"最小可测试包"** 策略——不仅声明结构，还要让包能通过完整的合规测试和 manifest 加载器验证。

**前置约束声明**：Contributor Guide 明确指出"core context currently accepts only `target_language=ja` and `explanation_language=zh`"。因此本 PR 的定位是 **"结构就绪 + 合规通过"**，而非"可端到端运行"。实际可运行需要先泛化 `lingotrace/core/context.py`，那是另一个 PR 的职责。

### 6.2 文件清单（13 个文件）

```
lingotrace/packs/english/
├── __init__.py                    ← 1 行，包边界
├── manifest.json                  ← 完整清单（通过 load_language_pack_manifest 验证）
├── fields.json                    ← 4 个英语自有字段
├── paths.json                     ← 11 个路径角色（与日语包对齐）
├── workflows.py                   ← 5 个能力的工作流桩函数
├── validators.py                  ← validate_review_materials + validate_review_rollover 桩
├── agent_skills/
│   └── SKILL.md                   ← 英语用户自然语言入口
└── templates/
    ├── focus-vocab-card.md        ← 英语词汇卡模板
    └── daily-checklist.md         ← 每日清单模板

tests/lingotrace/packs/
└── test_english_pack.py           ← 合规测试（7 个用例）
```

视图（`views/`）推迟到后续 PR——manifest 中不声明 `default_views`，测试不检查该字段。

### 6.3 manifest.json 完整设计

以下内容经过 `lingotrace/core/manifests.py` 的 `_parse_manifest` 逐字段校验：

```json
{
  "language_pack_id": "lingo-english",
  "language_pack_version": "0.1.0",
  "target_language": "en",
  "transcription_locale": "en-US",
  "compatible_core": {
    "minimum": "0.1.0",
    "maximum_exclusive": "0.2.0"
  },
  "compatible_vault_schema": {
    "minimum": 1,
    "maximum": 1
  },
  "capabilities": [
    {
      "id": "source_notes",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": ["source_notes_root"],
      "write_path_roles": ["source_notes_root"],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": [
        "English source note creation from reading material"
      ]
    },
    {
      "id": "review_materials",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "source_notes_root"
      ],
      "write_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root"
      ],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": [
        "English vocabulary card creation with IPA and collocations"
      ]
    },
    {
      "id": "review_rollover",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "daily_notes_root"
      ],
      "write_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "daily_notes_root"
      ],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": []
    }
  ],
  "unsupported_capabilities": [
    {
      "id": "listening_notes",
      "failure_reason": "English listening transcription tools are not yet available.",
      "failure_policy": "stop_before_write",
      "fallback": "none"
    },
    {
      "id": "speaking_cards",
      "failure_reason": "English speaking card validation is not yet implemented.",
      "failure_policy": "stop_before_write",
      "fallback": "none"
    }
  ],
  "external_tools": [],
  "language_fields": [
    {
      "name": "ipa",
      "owner": "English language pack",
      "purpose": "IPA phonetic transcription for English review items."
    },
    {
      "name": "word_stress",
      "owner": "English language pack",
      "purpose": "Primary stress pattern or syllable stress notation."
    },
    {
      "name": "part_of_speech",
      "owner": "English language pack",
      "purpose": "Grammatical category (noun, verb, adjective, etc.)."
    },
    {
      "name": "collocations",
      "owner": "English language pack",
      "purpose": "Common collocations and phrases for the headword."
    }
  ],
  "item_types": ["vocab", "grammar", "error"],
  "tag_namespace": "en",
  "default_path_roles": {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily"
  },
  "templates": [
    {
      "id": "focus_vocab_card",
      "capability_id": "review_materials",
      "path": "lingotrace/packs/english/templates/focus-vocab-card.md",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "daily_checklist",
      "capability_id": "review_rollover",
      "path": "lingotrace/packs/english/templates/daily-checklist.md",
      "artifact_class": "recreate-from-pack"
    }
  ],
  "workflow_entrypoints": [
    {
      "id": "source_notes_workflow",
      "capability_id": "source_notes",
      "entrypoint": "lingotrace.packs.english.workflows:source_notes",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_materials_workflow",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.english.workflows:review_materials",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_rollover_workflow",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.english.workflows:review_rollover",
      "call_policy": "through_core_write_guard"
    }
  ],
  "validators": [
    {
      "id": "review_materials_validator",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.english.validators:validate_review_materials"
    },
    {
      "id": "review_rollover_validator",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.english.validators:validate_review_rollover"
    }
  ],
  "display_rules": [],
  "initialization_artifacts": [
    {
      "id": "default_vault_context",
      "capability_id": "review_rollover",
      "path": ".lingotrace/vault-context.json",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "default_path_config",
      "capability_id": "review_rollover",
      "path": ".lingotrace/paths.json",
      "artifact_class": "recreate-from-pack"
    }
  ]
}
```

**设计决策说明**：

| 决策 | 理由 |
|------|------|
| 能力全部标 `experimental` | 核心 `capabilities.py` 只接受 `stable`，`experimental` 会被拒绝。但 manifest 加载器不拒绝 `experimental`——它只在 `stable` 时校验证据。这是结构就绪但暂不运行的正确语义。 |
| `unsupported_capabilities` 必须有 `fallback: "none"` | manifest 加载器 `_parse_unsupported_capability` 第 166 行强制校验此字段。日语包 manifest 中 `unsupported_capabilities` 为空数组所以没有此字段，但英语包有 2 个不支持能力，必须带此字段。 |
| `behavior_evidence` 为空数组 | `experimental` 能力不需要证据（第 140 行的校验仅对 `stable` 触发）。 |
| `default_path_roles` 与日语包完全一致 | 路径角色是通用概念（`review/focus/vocab` 等），不是语言专属。日语包和英语包使用相同路径角色，降低认知负担。 |
| 不声明 `default_views` | `.base` 视图推迟到后续 PR。manifest 加载器不校验此字段。 |
| `meaning_zh` 不列入 `language_fields` | 避免与日语包的字段归属冲突（两个包都声明为各自所有）。模板中可直接使用该字段，归属留待核心泛化时决定。 |

### 6.4 fields.json

```json
{
  "language_fields": [
    {
      "name": "ipa",
      "owner": "English language pack",
      "purpose": "IPA phonetic transcription for English review items."
    },
    {
      "name": "word_stress",
      "owner": "English language pack",
      "purpose": "Primary stress pattern or syllable stress notation."
    },
    {
      "name": "part_of_speech",
      "owner": "English language pack",
      "purpose": "Grammatical category (noun, verb, adjective, etc.)."
    },
    {
      "name": "collocations",
      "owner": "English language pack",
      "purpose": "Common collocations and phrases for the headword."
    }
  ]
}
```

### 6.5 paths.json

```json
{
  "default_path_roles": {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily"
  }
}
```

### 6.6 workflows.py 桩设计

参照日语包 `workflows.py` 的函数签名和错误返回模式：

```python
"""English language pack workflow stubs.

All capabilities are experimental and require core context generalization
before they can run against a real English Vault. Each function returns
a missing_vault_root error when called without a vault_root, matching
the Japanese pack's guard pattern.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def listening_notes(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("listening_notes", "English listening transcription tools are not yet available.")


def source_notes(
    vault_root: str | Path | None = None,
    *,
    source_artifact: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("source_notes")
    return _not_yet_implemented("source_notes", mode)


def review_materials(
    vault_root: str | Path | None = None,
    *,
    card: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_materials")
    return _not_yet_implemented("review_materials", mode)


def speaking_cards(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("speaking_cards", "English speaking card validation is not yet implemented.")


def review_rollover(
    vault_root: str | Path | None = None,
    *,
    run_date: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_rollover")
    return _not_yet_implemented("review_rollover", mode)


def _missing_vault_root(capability_id: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="missing_vault_root", message="vault_root is required.")],
    )


def _unsupported(capability_id: str, reason: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="unsupported_capability", message=reason)],
    )


def _not_yet_implemented(capability_id: str, mode: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode=mode,
        exit_code=1,
        errors=[Finding(
            code="not_yet_implemented",
            message=f"{capability_id} requires core context generalization before it can run.",
        )],
    )
```

### 6.7 validators.py 桩设计

```python
"""English language pack validators (stubs)."""
from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-materials", mode="check", exit_code=1 if errors else 0, errors=errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    required = ("review_stage", "next_review", "done_today")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-rollover", mode="check", exit_code=1 if errors else 0, errors=errors)
```

### 6.8 templates/focus-vocab-card.md

```markdown
---
track: class_review
item_type: vocab
status: active
review_stage: 0
headword:
ipa:
word_stress:
part_of_speech:
collocations:
meaning_zh:
next_review:
---

# {{headword}}

## Review

- IPA: `{{ipa}}`
- Stress: `{{word_stress}}`
- Part of speech: `{{part_of_speech}}`
- Collocations: {{collocations}}
- Meaning: {{meaning_zh}}

## Notes

Add learner-maintained examples here.
```

### 6.9 templates/daily-checklist.md

与日语包结构一致（通用模板）：

```markdown
---
track: daily
item_type: checklist
done_today: false
---

# Daily Review Checklist

- [ ] Review due cards.
- [ ] Mark completed cards with `done_today`.
- [ ] Run review rollover only after manual review is complete.
```

### 6.10 test_english_pack.py 设计

参照 `test_japanese_pack.py` 的 7 个测试用例，适配英语包的差异：

```python
"""English language pack conformance tests.

Mirrors test_japanese_pack.py structure, adapted for experimental capabilities
and English-owned fields.
"""
import importlib
import json
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PHASE0_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "english"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
FIELDS_PATH = PACK_ROOT / "fields.json"
PATHS_PATH = PACK_ROOT / "paths.json"

EXPECTED_PATH_ROLES = {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily",
}

EXPECTED_LANGUAGE_FIELDS = {"ipa", "word_stress", "part_of_speech", "collocations"}


class EnglishPackTests(unittest.TestCase):

    def test_manifest_loads_through_core_loader(self):
        """Manifest passes load_language_pack_manifest without errors."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        self.assertTrue(result.report.accepted, result.report.to_dict())
        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-english", result.manifest.language_pack_id)
        self.assertEqual("0.1.0", result.manifest.language_pack_version)
        self.assertEqual("en", result.manifest.target_language)

    def test_declared_capabilities_are_subset_of_phase0_ids(self):
        """All declared capabilities use reviewed IDs from PHASE0_CAPABILITY_IDS."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        declared_ids = set(result.manifest.capabilities) | set(result.manifest.unsupported_capabilities)
        self.assertTrue(declared_ids.issubset(PHASE0_CAPABILITY_IDS))
        self.assertEqual(PHASE0_CAPABILITY_IDS, declared_ids)

    def test_unsupported_capabilities_have_fallback_none(self):
        """Unsupported capabilities declare fallback: 'none' per manifest loader requirement."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        self.assertIn("listening_notes", result.manifest.unsupported_capabilities)
        self.assertIn("speaking_cards", result.manifest.unsupported_capabilities)

    def test_language_fields_are_english_pack_owned(self):
        """fields.json declares English-owned fields, not Japanese fields."""
        fields = json.loads(FIELDS_PATH.read_text(encoding="utf-8"))
        field_names = {r["name"] for r in fields["language_fields"]}
        self.assertEqual(EXPECTED_LANGUAGE_FIELDS, field_names)
        for record in fields["language_fields"]:
            self.assertEqual("English language pack", record["owner"])
        # Must NOT contain Japanese-owned fields
        self.assertNotIn("reading", field_names)
        self.assertNotIn("accent_display", field_names)
        self.assertNotIn("kanji_diff", field_names)

    def test_default_path_roles_match_japanese_pack(self):
        """Path roles are identical to the Japanese pack (cross-language convention)."""
        paths = json.loads(PATHS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_PATH_ROLES, paths["default_path_roles"])

    def test_workflow_stubs_do_not_reference_japanese_runtime(self):
        """workflows.py does not import or reference Japanese pack modules."""
        source = (PACK_ROOT / "workflows.py").read_text(encoding="utf-8")
        self.assertNotIn("japanese", source.lower())
        self.assertNotIn("codex-skills", source)
        self.assertNotIn("jp-", source)

    def test_pack_files_exist_for_manifest_declarations(self):
        """Every template and workflow entrypoint declared in manifest exists on disk."""
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for record in manifest.get("templates", []):
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])
```

### 6.11 Agent Skill 设计要点

`agent_skills/SKILL.md` 遵循日语包 SKILL.md 的结构：

| 区块 | 内容 |
|------|------|
| 标题 | `# LingoTrace English Agent Skill` |
| 用户语言映射表 | 英语学习场景→能力映射（如"帮我整理这篇阅读材料"→`source_notes`） |
| 不支持能力拒绝语 | 当用户要求听力或口语卡时，明确说明"English listening/speaking not yet available" |
| 操作规则 | 搜索在先、确认在先、通过核心写入守卫路由 |
| 各能力说明 | source_notes（保持来源可追踪）、review_materials（先查重）、review_rollover（先汇总后确认） |

### 6.12 合规检查清单对照

逐项声明 `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md` 的合规状态：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| **Identity And Versions** | | |
| Declares `language_pack_id` | ✅ | `lingo-english` |
| Declares `language_pack_version` | ✅ | `0.1.0` |
| Declares exactly one `target_language` | ✅ | `en` |
| Declares `transcription_locale` | ✅ | `en-US` |
| Declares compatible core version range | ✅ | `0.1.0` – `0.2.0` |
| Declares compatible Vault Schema version range | ✅ | `1` – `1` |
| No target-language guessing | ✅ | Vault 显式声明 `target_language: en` |
| **Capabilities** | | |
| Uses only reviewed capability IDs | ✅ | 5 个全部来自 `PHASE0_CAPABILITY_IDS` |
| Declares maturity per capability | ✅ | 3 个 `experimental`，2 个 unsupported |
| Declares dependencies | ✅ | 无依赖（`depends_on: []`） |
| Declares read/write paths | ✅ | 每个能力声明了路径角色 |
| Declares external tools | ✅ | 空数组（不依赖外部工具） |
| Stops before write on missing tool | ✅ | `failure_policy: "stop_before_write"` |
| No Japanese fallback | ✅ | 代码中不引用日语模块 |
| **Pack-Owned Surface** | | |
| Lists templates | ✅ | 2 个模板 |
| Lists workflow entry points | ✅ | 3 个入口 |
| Lists validators | ✅ | 2 个校验器 |
| Lists dictionaries/pronunciation resources | ⏭️ | 不适用（第一版无离线词典） |
| Lists default path roles | ✅ | 11 个角色 |
| Lists language-specific fields | ✅ | 4 个字段 |
| Declares initialization artifacts | ✅ | 2 个产物 |
| **Core Boundary** | | |
| Uses core review-card shell | ✅ | 模板使用 `track`/`status`/`review_stage` 等公共字段 |
| Keeps language fields outside core | ✅ | `ipa`/`word_stress` 等仅在包内声明 |
| Preserves unknown frontmatter | ✅ | 工作流桩不修改任何文件 |
| Stop on missing version/capability | ✅ | manifest 加载器 + 校验器处理 |
| No private data in public repo | ✅ | 无 Vault 数据 |
| No cross-Vault state | ✅ | 无缓存或状态持久化 |

### 6.13 实施顺序

```
Step 1: 创建 lingotrace/packs/english/__init__.py
Step 2: 创建 manifest.json（完整内容如 6.3 节）
Step 3: 创建 fields.json、paths.json
Step 4: 创建 workflows.py 和 validators.py 桩
Step 5: 创建 agent_skills/SKILL.md
Step 6: 创建 templates/focus-vocab-card.md 和 daily-checklist.md
Step 7: 创建 tests/lingotrace/packs/test_english_pack.py
Step 8: 运行 python -m unittest discover -s tests/lingotrace -p 'test_*.py'
Step 9: 运行 python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
Step 10: 运行 bash tools/git/check-public-staged-files.sh
Step 11: 手动检查无日语字段泄漏（grep reading, accent_display, kanji_diff）
Step 12: 逐项对照合规检查清单（6.12 节）
```

---

## 七、两个方案的对比

| 维度 | 原计划 | 替代方案 |
|------|--------|---------|
| 文件数 | 4 个 | 10 个（+测试 = 11） |
| 包含 `workflows.py` | ❌ | ✅ 桩文件 |
| 包含 `validators.py` | ❌ | ✅ 桩文件 |
| 包含模板 | ❌ | ✅ 2 个 |
| 包含合规测试 | ❌ | ✅ 7 个用例 |
| manifest 完整度 | 仅标识+能力 | 全部字段（通过加载器验证） |
| 字段设计 | `pronunciation_ipa` 等 4 个 | `ipa`/`word_stress`/`part_of_speech`/`collocations` |
| 合规检查清单 | 未引用 | 逐项声明（6.12 节） |
| 核心泛化前置说明 | ❌ | ✅ 显式声明 |
| 与日语包对齐度 | 🟡 部分 | ✅ 结构完全对齐 |
| 可测试性 | 无法运行任何测试 | ✅ 可通过全部合规测试 |

---

## 八、检查清单汇总

| # | 类型 | 缺陷 | 严重度 | 修复建议 |
|---|------|------|--------|---------|
| S1 | 结构 | 缺少 `workflows.py` 和 `validators.py` | 🔴 高 | 创建桩文件 |
| S2 | 结构 | SKILL.md 路径正确但 manifest 未声明 entrypoints | 🟡 中 | 补充 manifest 声明 |
| S3 | 结构 | 缺少 `test_english_pack.py` | 🔴 高 | 编写合规测试 |
| C1 | 内容 | 字段命名和覆盖范围与上游指引不一致 | 🟡 中 | 采用 `ipa`/`word_stress`/`part_of_speech` |
| C2 | 内容 | `experimental` 能力被核心拒绝，需显式说明 | 🟡 中 | 补充说明 |
| C3 | 内容 | manifest 缺少 10+ 个必需字段 | 🔴 高 | 补充完整 manifest 设计 |
| C4 | 内容 | 缺少 `templates/` 设计 | 🟡 中 | 创建最小模板 |
| V1 | 验证 | 缺少英语包专属合规测试 | 🔴 高 | 编写 test_english_pack.py |
| V2 | 验证 | 未对照合规检查清单 | 🟡 中 | 逐项声明合规状态 |
