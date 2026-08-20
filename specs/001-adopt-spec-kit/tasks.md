# 任务清单：采用 Spec Kit 工程治理

**输入**：`spec.md`、`plan.md`、`research.md`、`data-model.md`、`quickstart.md`

**任务状态**：本分支中的迁移任务已完成；复选框用于记录实际执行状态。

## Phase 1：初始化与公共文件范围

**目的**：建立可复现、可共享的 Spec Kit 项目基础设施。

- [x] T001 在项目根目录使用当前 CLI 初始化 Codex Spec Kit 集成，生成 `.specify/` 和 `.agents/skills/speckit-*/SKILL.md`
- [x] T002 [P] 在 `.gitignore` 中放行共享 `.specify/` 和受管 Spec Kit skills，同时忽略 `.specify/feature.json` 等本机状态

## Phase 2：治理基础

**目的**：建立后续规格、计划和任务必须遵守的项目原则。

- [x] T003 编写 `.specify/memory/constitution.md`，纳入现有架构、写入保护、公共/私人隔离、测试和 Git 规则
- [x] T004 [P] 在 `AGENTS.md` 中明确项目维护文档使用中文，并定义代码、命令、路径、字段和受管 skill 的例外
- [x] T005 [P] 在 `docs/README.md` 中增加中文 Spec Kit 宪章和迁移规格入口

## Phase 3：用户故事 1——可追溯的 Spec Kit 工程入口（优先级：P1）

**目标**：维护者能够从版本控制中的 Spec Kit 工件理解迁移范围和治理原则。

**独立测试**：运行 `specify integration status --json`，检查 `.specify/memory/constitution.md`、`spec.md`、`plan.md`、`tasks.md` 和检查单均存在且无模板占位符。

- [x] T006 [US1] 创建 `specs/001-adopt-spec-kit/spec.md`，定义用户故事、FR、SC、边界和既有内容保留规则
- [x] T007 [US1] 创建 `specs/001-adopt-spec-kit/checklists/requirements.md`，完成需求质量审查
- [x] T008 [US1] 创建 `specs/001-adopt-spec-kit/plan.md`，记录技术上下文、Constitution Check、结构决策和验证设计
- [x] T009 [US1] 创建 `specs/001-adopt-spec-kit/research.md` 与 `specs/001-adopt-spec-kit/data-model.md`，记录迁移决策和工件关系
- [x] T010 [US1] 创建 `specs/001-adopt-spec-kit/quickstart.md`，记录 CLI、测试、allowlist、diff 和发布前验证命令

## Phase 4：用户故事 2——中文项目文档（优先级：P2）

**目标**：新增和维护的项目治理文档使用中文，同时保持技术标识符精确。

**独立测试**：审查 `AGENTS.md`、Constitution 和 `specs/001-adopt-spec-kit/` 的中文正文，并确认 `.agents/skills/` managed-file 哈希未被修改。

- [x] T011 [US2] 在 `AGENTS.md` 中建立中文文档规范和 Spec Kit 受管 skill 边界
- [x] T012 [US2] 将 Constitution、迁移规格、计划、研究、数据模型、quickstart、任务和检查单写成中文

## Phase 5：用户故事 3——保真迁移与验证（优先级：P3）

**目标**：保留既有公共价值，不创建冗余备份，并以自动证据完成迁移验收。

**独立测试**：审查 `git diff main...HEAD`、运行四组测试和公共文件检查，确认无无理由删除、无重复备份、无私人材料。

- [x] T013 [US3] 对比迁移前后的跟踪文件清单和差异，确认既有 `lingotrace/`、`tests/`、`docs/multilingual/`、manifest 和架构基线未被无理由删除
- [x] T014 [US3] 运行 `specify integration status --json` 并确认 managed files、manifest paths 和 integration state 均有效
- [x] T015 [US3] 运行 runtime、architecture baseline、vault structure 和 listening 四组 unittest，并记录结果
- [x] T016 [US3] 运行 `git diff --check` 与 `bash tools/git/check-public-staged-files.sh`，确认公共文件边界
- [x] T017 [US3] 在测试通过后更新 `CHANGELOG.md`，记录 Spec Kit 初始化、中文治理规则和迁移验证证据
- [ ] T018 [US3] 提交 topic branch，推送到 `origin`，并创建指向上游 `main` 的 PR

## 依赖与执行顺序

- 初始化与公共文件范围（Phase 1）无依赖。
- 治理基础（Phase 2）依赖 Phase 1，阻塞后续规格工件。
- US1 依赖 Phase 2；US2 可与 US1 的内容编写并行，但最终都必须服从 Constitution。
- US3 依赖 US1 和 US2，并在提交前完成。
- T017 必须在测试通过后、最终 commit 前执行；T018 依赖所有前置任务完成。

## 并行机会

- T002、T004、T005 可在初始化成功后分别修改不同文件。
- T006、T007、T008、T009、T010 分属不同工件，可并行草拟，最后统一做追踪审查。
- T014、T015、T016 可在内容写入完成后并行验证；最终 staged allowlist 检查必须在暂存后再次执行。

## 实施策略

1. 先完成 CLI 初始化和 Constitution，确保所有后续工件有治理依据。
2. 以 US1 形成最小可用 Spec Kit 工程入口。
3. 以 US2 统一本次新增治理文档语言。
4. 以 US3 做保真、重复、测试和发布收敛，然后再提交 PR。
