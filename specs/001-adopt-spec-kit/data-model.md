# 数据模型：采用 Spec Kit 工程治理

本次变更没有新增运行时数据模型，新增的是可版本控制的工程治理工件。

## 项目治理工件

| 实体 | 位置 | 作用 | 关系 |
| --- | --- | --- | --- |
| 项目宪章 | `.specify/memory/constitution.md` | 稳定原则、边界和治理规则 | 约束所有规格、计划、任务和实现 |
| 功能规格 | `specs/001-adopt-spec-kit/spec.md` | 用户故事、FR、SC 和范围 | 由计划和任务实现 |
| 研究记录 | `specs/001-adopt-spec-kit/research.md` | 记录迁移决策和替代方案 | 解释计划中的治理选择 |
| 实施计划 | `specs/001-adopt-spec-kit/plan.md` | 技术上下文、结构和门禁 | 指导任务清单 |
| 需求检查单 | `specs/001-adopt-spec-kit/checklists/requirements.md` | 审查规格质量 | 在计划前确认输入完整 |
| 任务清单 | `specs/001-adopt-spec-kit/tasks.md` | 带 ID、用户故事和路径的工作项 | 逐项对应 FR/US/SC |
| 受管集成 | `.specify/integration.json`、`.specify/integrations/` | 记录 Codex 与 Spec Kit 文件哈希 | 由 `specify integration status` 校验 |

## 既有契约实体

- **能力契约**：`docs/multilingual/*user-stories.md`，定义学习能力的用户故事和验收标准。
- **语言包 manifest**：`lingotrace/packs/*/manifest.json`，把能力、行为证据和 conformance tests 联系起来。
- **架构基线**：`tools/architecture-baseline/`，使用公开合成 fixture 验证当前行为。

## 保持的关系

1. 功能规格的用户故事引用既有能力契约，不复制完整正文。
2. 计划和任务引用真实源文件、测试目录和 CLI 验证命令。
3. Constitution 约束公共/私人边界、中文文档、写入保护、测试和 Git 流程。
4. `.specify/feature.json` 只记录当前 checkout 的本机 feature 指针，不进入公共提交。
