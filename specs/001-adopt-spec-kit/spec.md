# 功能规格：采用 Spec Kit 工程治理

**功能分支**：`codex/adopt-spec-kit`

**创建日期**：2026-08-21

**状态**：已实现，待 PR 审查

**输入**：用户要求将 LingoTrace 迁移为标准 Spec Kit 项目，统一项目文档语言，并通过 GitHub PR 发布。

## 用户场景与测试

### 用户故事 1：维护者可以从 Spec Kit 工件理解项目约束（优先级：P1）

作为 LingoTrace 维护者，我希望项目有正式的 Constitution、规格、计划、任务和验证入口，以便后续 substantive engineering work 可以按统一生命周期推进。

**优先级理由**：这是迁移的核心价值，决定后续需求、实现和验证能否追踪。

**独立测试**：在仓库根目录运行 `specify integration status --json`，并检查 Constitution、基线规格、计划、任务和质量检查单均存在且无未填写占位符。

**验收场景**：

1. **给定** 项目已经包含现有 core、语言包、测试和架构文档，**当** 维护者查看 Spec Kit 项目状态，**那么** Codex 集成和 shared infrastructure 均可被 CLI 识别。
2. **给定** 维护者要开始下一项功能，**当** 其读取项目宪章和迁移基线规格，**那么** 能够知道原则、范围、验收标准和验证入口，而不必依赖对话历史。

### 用户故事 2：贡献者使用中文项目文档（优先级：P2）

作为中文项目贡献者，我希望本项目维护的文档统一使用中文，同时保留必要的代码、命令、字段和外部原文，以便规格和工程规则可以直接执行。

**优先级理由**：语言统一降低项目维护和 Agent 交接成本，同时不破坏技术标识符的精确性。

**独立测试**：检查 `AGENTS.md`、Constitution 和本次新增的 Spec Kit 项目工件；确认规则明确、内容为中文，受管 Agent skill 未被手工修改。

**验收场景**：

1. **给定** 贡献者新增或修改项目规格，**当** 其遵循 `AGENTS.md`，**那么** 文档正文使用中文，命令、路径、协议字段和测试名称保持可执行原文。
2. **给定** Spec Kit CLI 生成的 `.agents/skills/` 文件为上游受管内容，**当** 贡献者检查集成状态，**那么** 这些文件的哈希仍与 manifest 一致。

### 用户故事 3：迁移不损失既有价值且不制造重复规范（优先级：P3）

作为维护者，我希望迁移只新增必要的治理工件，并把既有架构、能力契约、用户故事、测试和 Git 规则连接起来，不删除有价值内容，也不为旧结构制作冗余备份。

**优先级理由**：迁移的质量取决于内容保真和规范来源清晰，而不是文件数量。

**独立测试**：审查迁移分支的文件清单、差异和测试结果，确认既有公共内容没有无理由删除，新增工件没有重复复制现有完整契约。

**验收场景**：

1. **给定** 现有 `docs/multilingual/` 用户故事和 `manifest.json` 行为证据，**当** 迁移完成，**那么** 它们仍保留为当前能力契约或被明确链接，而不是被无依据删除。
2. **给定** Spec Kit 需要新工件，**当** 迁移者建立 `specs/` 和 `.specify/`，**那么** 不创建旧文档的副本、备份目录或同一事实的第二套竞争规范。

## 边界情况

- 如果 `.agents/` 包含 Agent 私密状态，Git 必须只允许受管的 `speckit-*` skill 文件进入提交。
- 如果 Spec Kit CLI 版本升级导致 managed file 哈希变化，必须使用 CLI 的 integration upgrade 流程，不手工编辑受管 skill。
- 如果既有英文契约与中文项目规则产生冲突，必须保留精确的代码/字段/测试标识，并在用户可读的规范说明中提供中文维护文本，而不是删除领域证据。
- 如果测试在本机缺少 `python` 命令，应使用仓库文档认可的 `python3` 验证，同时记录 CI 与本地 launcher 差异。

## 需求

### 功能需求

- **FR-001**：项目 MUST 在根目录包含由当前 Spec Kit CLI 生成并可通过 `specify integration status --json` 验证的 `.specify/` 基础设施。
- **FR-002**：项目 MUST 提供无未解释占位符的中文 Constitution，覆盖核心原则、边界、工程流程、质量门禁和治理规则。
- **FR-003**：`AGENTS.md` MUST 明确项目维护文档使用中文，并定义代码、命令、路径、协议字段、测试名称、外部原文及上游受管 skill 的语言例外。
- **FR-004**：项目 MUST 提供本次迁移的 `spec.md`、`plan.md`、`tasks.md`、研究记录、数据模型、quickstart 和需求质量检查单，并通过稳定的功能范围相互追踪。
- **FR-005**：迁移 MUST 保留现有公共源代码、用户故事、架构文档、能力 manifest、测试和 Git 安全规则；不得创建仅用于备份的旧结构副本。
- **FR-006**：迁移 MUST 通过 runtime、architecture baseline、vault structure 和 listening 测试，以及 Spec Kit 集成状态检查。
- **FR-007**：Git 提交 MUST 只包含公共 Spec Kit 基础设施、项目规格和必要的中文治理更新，不得包含 `.agents/` 私密状态、Vault 内容、媒体或缓存。
- **FR-008**：发布前 MUST 更新 `CHANGELOG.md`，并通过 topic branch 推送到 `origin` 后向上游 `main` 创建 PR。

### 关键实体

- **项目宪章**：定义 LingoTrace 的不可妥协原则、边界和治理方式。
- **功能规格**：描述本次 Spec Kit 迁移的用户场景、需求和成功标准。
- **设计工件**：包括计划、研究、数据模型和 quickstart，记录如何验证迁移范围。
- **任务清单**：按用户故事组织、带依赖和文件路径的可执行工作项。
- **既有能力契约**：`docs/multilingual/` 用户故事、语言包 manifest、测试和架构基线。

## 成功标准

### 可衡量结果

- **SC-001**：`specify integration status --json` 返回 `status=ok`、`default_integration=codex`、managed files 缺失数为 0，且未发现 modified managed files。
- **SC-002**：本次新增的项目维护文档中，至少 100% 的正文为中文；命令、路径、字段、测试名称和上游受管 skill 的例外均有明确说明。
- **SC-003**：迁移分支保留迁移前所有已跟踪公共源代码、测试、架构文档和能力契约；差异审查不出现无理由删除或备份副本。
- **SC-004**：四组现有测试全部通过：runtime 270 项、architecture baseline 42 项、vault structure 23 项、listening 112 项（允许既有 1 项 skip）。
- **SC-005**：规格、计划、任务、检查单和 quickstart 能通过文件路径和 FR/US 标识互相追踪，且任务清单中的每项任务均有明确文件路径或验证命令。
- **SC-006**：topic branch 成功推送到 `origin`，上游仓库存在对应 PR，PR 正文包含变更摘要、用户影响、测试证据和未自动验证事项。

## 假设

- 本次迁移使用当前验证过的 Spec Kit CLI `0.16.6.dev0` 和 Codex 集成。
- LingoTrace 继续使用 Python unittest、Markdown、GitHub Actions 和现有仓库结构；本次不引入新的应用运行时依赖。
- 现有英文能力契约继续作为精确领域证据；本次只新增中文维护性规范，不进行大规模机械翻译。
- GitHub CLI 或等效 GitHub API 可用于推送分支、创建 PR 和读取上游仓库状态；若权限不足，必须报告阻塞而不伪造完成。
