# LingoTrace English Language Pack 实施计划 (Phase 2 第一步) v2

本文档阐述了在遵循上游最新的四层多语言架构规范下，创建并引入 `English` 语言包第一版（最小可测试包）的实施细节。本方案已吸收了 V1 版本评审中的所有合规性反馈，确保能通过上游严格的清单加载器与自动化测试。

## 🎯 目标描述

在不破坏现有日语包、不复用日语特有逻辑，且不修改通用核心引擎的前提下，建立标准合规的英语语言包。本阶段定位为 **“最小可测试包” (Minimal Testable Pack)**：不实现真正的英语 Python 业务逻辑（因为核心引擎暂不支持），但必须提供完整的结构声明、空壳桩函数 (stubs) 以及对应的自动化测试，确保语言包能在结构层面 100% 通过上游架构验证。

> **关于运行时的说明**
> 由于当前核心的上下文（`core/context.py`）只接受 `ja`，本 PR 不追求业务端到端可运行，而仅仅作为“结构就绪”的里程碑。真正可运行需要依赖后续的核心泛化 PR。

## 🛠️ Proposed Changes

所有的修改都将严格限制在 `lingotrace/packs/english/` 和 `tests/lingotrace/packs/` 目录中。

### 1. English Language Pack Skeleton (清单与配置)

#### [NEW] manifest.json
声明完整的语言包契约，严格满足 `lingotrace/core/manifests.py` 的校验逻辑：
- **标识声明**：`language_pack_id: lingo-english`, `version: 0.1.0`, `target_language: en`, `transcription_locale: en-US`。
- **兼容性**：声明 `compatible_core` 和 `compatible_vault_schema`（与日语包一致）。
- **能力认领**：
  - `source_notes`, `review_materials`, `review_rollover` 标记为 `experimental`（此时不需要 `behavior_evidence`）。
  - `unsupported_capabilities` 列入 `listening_notes` 和 `speaking_cards`，并严格遵守规范提供 `fallback: "none"` 和 `failure_reason`。
- **资源绑定**：声明 `item_types: ["vocab", "grammar", "error"]`，`tag_namespace: "en"`。
- **接口挂载**：声明 `templates`, `workflow_entrypoints`, `validators` 的路径。

#### [NEW] fields.json
定义纯正的英语知识模型字段：
- `ipa`: 国际音标。
- `word_stress`: 单词重音模式。
- `part_of_speech`: 词性。
- `collocations`: 常见搭配。
*(注意：`meaning_zh` 不在这里声明所有权，以避免与日语包冲突，但在模板中可直接使用。)*

#### [NEW] paths.json
提供与跨语言惯例一致的扁平化路径角色声明（如 `review/focus/vocab`）。

### 2. Python Stubs (工作流与校验器桩)

#### [NEW] workflows.py
为 5 个能力提供函数签名桩。每个函数返回标准 `CommandReport`：
- 对于未实现的能力，返回带有 `not_yet_implemented` 错误码的 Report。
- 对于不支持的能力，返回带有 `unsupported_capability` 错误码的 Report。
- 不引入任何对 `japanese` 模块的依赖。

#### [NEW] validators.py
提供 `validate_review_materials` 和 `validate_review_rollover` 的最小实现，仅检查必须存在的公共字段（如 `item_type`, `review_stage`），返回 `CommandReport`。

### 3. Agent 与模板层 (用户交互面)

#### [NEW] agent_skills/SKILL.md
为 AI Agent 编写的英语语种操作手册。映射用户的自然语言指令，同时指示 Agent 在处理英语数据时应提取 `ipa` 和 `collocations`。

#### [NEW] templates/
- `focus-vocab-card.md`: 渲染 `ipa`, `word_stress`, `collocations`, `meaning_zh` 等字段的卡片模板。
- `daily-checklist.md`: 每日复习清单模板。

### 4. 测试与验证层

#### [NEW] test_english_pack.py
对照日语包编写英语包专属的 7 个合规测试用例（如清单加载测试、字段归属测试、不支持能力声明格式测试、代码无日语依赖测试等）。

## 🧪 Verification Plan

验证通过标准：**合规性测试 100% 通过**，且符合 Phase 0 检查清单。

### Automated Tests
1. 运行核心架构级测试：`python -m unittest discover -s tests/lingotrace -p 'test_*.py'`
2. 运行基线测试：`python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'`
3. 检查白名单：`bash tools/git/check-public-staged-files.sh`

### Conformance Checklist Compliance
对照 `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md` 进行以下检查：
- [x] Manifest 结构完整且合法。
- [x] 包内部不存在任何 `japanese` 硬编码引用。
- [x] `fields.json` 未越权占用其它语言的特有字段（放弃占用 `meaning_zh`）。
- [x] 测试覆盖率达标，包含独立于 `test_japanese_pack` 的测试文件。
