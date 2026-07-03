# English Language Pack Phase 2.2: Capability Parity Implementation Plan

## 1. 背景与目标 (Background & Objective)
目前 LingoTrace 的英语语言包（English Pack）已完成 Phase 2.1 的建设，支持了 `source_notes`、`review_materials`、`review_rollover` 和 `total_training_dashboard`。
然而，与日语语言包相比，英语包在 `manifest.json` 中明确声明了以下缺失能力（Unsupported Capabilities）：
1. **Listening Notes (`listening_notes`)**: 因缺乏英语专属听力转写工具链支持而暂未开放。
2. **Speaking Cards (`speaking_cards`)**: 因英语口语卡片校验逻辑与模板尚未实现而暂未开放。
3. **External Tools 集成**: 缺乏离线词典及打轴工具（如 `listenkit`）的英语原生适配。

**本项目标（Phase 2.2）**：补齐英语包的 `listening_notes` 和 `speaking_cards` 能力，实现与日语包在 Core Capabilities 上的对齐（Parity）。提供相应的英语专属 Agent 技能、字段、模板及自动化测试，使英语包成为完全成熟（Maturity: Stable）的多维度语言学习引擎。

## 2. 引用与参考文档 (References & Citations)
在执行本计划前，实施 Agent 必须阅读并严格遵守以下项目级别与多语言指引文档：
- `docs/multilingual/language-pack-capability-guidance.zh.md` & `.md`: 语言包能力指引与 Core 边界规则（了解哪些行为可以上卷，哪些必须留在包内）。
- `docs/multilingual/language-pack-contributor-guide.md`: 语言包贡献者指南，重点关注 “Runtime Boundary” 与 “Japanese Reference Boundary”（严禁直接复制或依赖日语包的运行时代码）。
- `docs/multilingual/language-pack-agent-handoff-template.md`: Agent 交接标准与测试要求。
- `lingotrace/packs/english/manifest.json`: 英语包当前能力清单（基线）。
- `lingotrace/packs/japanese/manifest.json`: 日语包能力清单（对标参考）。

## 3. 详细实施步骤 (Step-by-Step Execution Plan)

### Step 1: 制定多语言 User Stories (Reference Guidance)
由于 `language-pack-capability-guidance.zh.md` 表明 `listening_notes` 和 `speaking_cards` 的 User Stories 尚未创建，必须首先填补框架空白：
- **1.1** 创建 `docs/multilingual/listening-notes-user-stories.md`。记录通用多语言听力精听的输入输出标准（如音频切片约定、原文对照格式、生词高亮规则）。
- **1.2** 创建 `docs/multilingual/speaking-cards-user-stories.md`。记录通用多语言口语输出卡片的标准（如场景 Usage Scenario、发音提示、母语者表达、刻意练习闭环）。
- **1.3** 更新 `docs/multilingual/language-pack-capability-guidance.zh.md` 和 `.md`，将上述两项能力的指引状态从 "Planned Reference Guidance" 更新为 "Reference Guidance" 并建立文件内链。

### Step 2: 英语包专属模板与字段扩展 (Templates & Fields)
- **2.1** 更新 `lingotrace/packs/english/fields.json`，新增口语卡所需的专属字段（如 `usage_scenario` 适用场景、`native_expression` 地道表达、`cultural_nuance` 文化语境），并复用已有的 `ipa` 和 `collocations` 字段。
- **2.2** 创建 `lingotrace/packs/english/templates/speaking-card.md`。基于英语思维设计，不照抄日语模板，包含场景描述与发音（IPA/Word Stress）的强提示版块。

### Step 3: 核心工作流与校验器实现 (Workflows & Validators)
- **3.1** 修改 `lingotrace/packs/english/validators.py`：
  - 新增 `validate_speaking_cards` 校验器，确保生成的口语卡包含目标句子、IPA、英文释义及地道搭配。
  - 修改 `validate_review_materials` 等现有入口，允许并放行 `speaking_card` 这一 Item Type。
- **3.2** 修改 `lingotrace/packs/english/workflows.py`：
  - 实现 `listening_notes(context, request, ...)`: 接收音视频或转写输入，调用支持英语的外部工具（或提供 LLM Fallback），输出精听稿，严格通过 core write guard 保存至 `listening_root`。
  - 实现 `speaking_cards(context, request, ...)`: 接收用户自然语言请求（如“把这句话做成口语卡”），生成结构化卡片并保存至 `speaking_card_root`。

### Step 4: 清单文件状态更新 (Manifest Updates)
修改 `lingotrace/packs/english/manifest.json`，正式启用新能力：
- **4.1** 从 `unsupported_capabilities` 列表中彻底移除 `listening_notes` 和 `speaking_cards`。
- **4.2** 将 `listening_notes` 和 `speaking_cards` 注册到 `capabilities` 数组中，设置 maturity 为 `stable`，并绑定依赖关系和 Path Roles。
- **4.3** 在 `item_types` 数组中追加 `"speaking_card"`。
- **4.4** 在 `templates` 中注册新的 `speaking-card.md` 模板配置。
- **4.5** 在 `workflow_entrypoints` 中注册 `listening_notes_workflow` 和 `speaking_cards_workflow`。
- **4.6** 若集成了英语专属外部词典或听力工具（如 whisper-en），需在 `external_tools` 中显式声明。

### Step 5: Agent Skill 更新 (User Experience Policy)
修改 `lingotrace/packs/english/agent_skills/SKILL.md`，定义纯用户交互入口：
- **5.1** 增加听力处理的自然语言入口说明及对话范例（如："I have this English podcast audio, please make it an intensive listening note"）。
- **5.2** 增加口语卡的自然语言入口说明（如："I want to practice this sentence for speaking, create a speaking card"）。
- **5.3** 再次强化 Agent 纪律：绝对不要要求用户说出系统内部工作流名称（如 `listening_notes`）。

### Step 6: 一致性测试与质量保障 (Conformance Tests)
- **6.1** 修改 `tests/lingotrace/packs/test_english_pack.py`：
  - 增加 `test_listening_notes_capability`，验证听力工作流拦截、输入参数与执行路由逻辑。
  - 增加 `test_speaking_cards_capability`，验证口语卡的专属校验器、字段验证一致性与写入保护。
- **6.2** 本地运行测试以验证代码健壮性：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/lingotrace -p 'test_*.py'
  ```

### Step 7: 验收准则与提交流程 (PR Acceptance)
- **7.1** 确认所有代码变更均存在于 `lingotrace/packs/english/` 及对应测试目录下，未污染 `japanese` pack 或发生跨包耦合（禁止 hardcode 依赖日语）。
- **7.2** 运行 `bash tools/git/check-public-staged-files.sh`，确保没有私有笔记（Vault Files）和多媒体缓存文件被 stage。
- **7.3** 更新 `CHANGELOG.md`，使用原子化规范记录本次新增的英语 `listening_notes` 和 `speaking_cards` 能力后，再执行 Git Commit。
