# 实施计划：采用 Spec Kit 工程治理

**分支**：`codex/adopt-spec-kit` | **日期**：2026-08-21 | **规格**：[spec.md](spec.md)

**输入**：采用 Spec Kit、统一中文项目文档、保留既有价值内容并通过上游 PR 发布。

## 摘要

在不重写既有能力契约和用户文档的前提下，将当前 LingoTrace checkout 初始化为 Spec Kit Codex 项目，建立中文 Constitution 和一次迁移基线规格，并把 Spec Kit 工件纳入公共 Git allowlist。通过 CLI managed-file 检查、四组现有测试、差异核对和 PR 证据验证迁移。

## 技术上下文

**语言/版本**：Python 3.14（core 兼容 Python 3.11+）

**主要依赖**：Spec Kit CLI 0.16.6.dev0、Codex integration、Python unittest、GitHub Actions

**存储**：Markdown、JSON、Git；不新增运行时数据库

**测试**：`python3 -m unittest discover`、Spec Kit integration status、公共文件 allowlist、`git diff --check`

**目标平台**：macOS、Windows、Linux 的公共运行时和 GitHub Actions

**项目类型**：Python 公共运行时、Markdown/Obsidian 学习系统、Agent 集成和工程文档

**性能目标**：本次不改变运行时性能；Spec Kit 状态检查必须在本地可重复完成

**约束**：中文维护文档、公共/私人隔离、受管 skill 不手工修改、不提交 main、保留既有契约和测试

**范围**：一次项目治理迁移；不新增学习能力、不删除旧能力、不机械翻译全部历史英文契约

## Constitution Check

| 原则 | 设计回应 | 状态 |
| --- | --- | --- |
| 用户价值优先 | 规格以维护者和贡献者的可追溯工程体验为目标 | 通过 |
| 核心与语言包分离 | 只增加工程治理，不改变语言包运行时边界 | 通过 |
| 安全写入与内容保真 | 保留既有文档、代码和测试；allowlist 隔离 Agent 状态 | 通过 |
| 规格先行 | 先建立 spec、plan、checklist、tasks，再完成迁移核对 | 通过 |
| 可执行证据 | 使用 CLI 状态、四组测试、diff 和公共文件检查 | 通过 |
| 公共/私人隔离 | 只提交受管 Spec Kit 文件和公共治理文档 | 通过 |

## 设计阶段

### 研究决策

研究结论记录在 [research.md](research.md)：使用当前 CLI 生成集成；保留既有契约；只放行共享 Spec Kit 文件；中文规则同时进入 AGENTS 和 Constitution。

### 数据与契约

本次没有新增运行时实体或外部 API。治理工件及其关系记录在 [data-model.md](data-model.md)。现有能力契约继续由 `docs/multilingual/`、language-pack manifest 和 architecture baseline 提供证据。

### 验证设计

端到端验证步骤记录在 [quickstart.md](quickstart.md)，包括 Spec Kit 状态、公共文件范围、四组测试、差异审查和发布前核对。

## 项目结构

```text
.specify/
├── memory/constitution.md
├── integrations/                  # CLI 生成的 manifest
├── scripts/bash/                  # CLI 生成的共享脚本
├── templates/                     # CLI 生成的工件模板
└── workflows/                    # CLI 生成的工作流
.agents/skills/speckit-*/SKILL.md  # Codex 受管 Spec Kit skills
specs/001-adopt-spec-kit/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
AGENTS.md                          # 中文文档和工程约束
docs/README.md                     # 文档索引增加 Spec Kit 入口
CHANGELOG.md                       # 记录框架迁移
```

**结构决策**：将 Spec Kit 项目基础设施放在 CLI 约定的 `.specify/`，将 Codex 受管 skill 放在 `.agents/skills/`，将每项工程变更放在 `specs/<编号>-<短名>/`。不移动现有 `docs/`、`lingotrace/` 或 `tests/`，避免破坏既有路径和用户入口。

## 复杂度记录

无 Constitution 例外。迁移复用现有文档、测试和 allowlist；没有新增应用层依赖或运行时复杂度。
