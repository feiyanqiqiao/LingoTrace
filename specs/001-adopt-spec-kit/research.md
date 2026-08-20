# 研究记录：采用 Spec Kit 工程治理

## 决策 1：使用当前 CLI 初始化，不手工复制旧版集成

**结论**：使用 `specify 0.16.6.dev0` 在仓库根目录安装 Codex 集成，并以 `specify integration status --json` 作为集成状态来源。

**理由**：本地 Spec Kit 参考要求以当前 CLI 和项目 integration status 为运行时权威。手工复制 Agent skill 会破坏 manifest 哈希和升级路径。

**考虑过的替代方案**：只创建 `.specify/`，不安装 Codex skill；放弃该方案，因为当前项目以 Codex 作为主要 Agent，需要项目级入口。

## 决策 2：保留现有 docs/multilingual 契约，不复制到 specs

**结论**：`specs/` 保存每项工程变更的可追踪规格、计划和任务；现有能力用户故事、语言包 manifest 和架构基线继续作为当前行为契约，并从新规格中引用。

**理由**：现有文档已包含大量验收标准和测试矩阵。复制全文会制造两个竞争来源，违反项目已有的文档生命周期规则。

**考虑过的替代方案**：把全部现有 docs 重写为 Spec Kit 功能目录；放弃该方案，因为会增加无风险的机械改写并可能损失领域证据。

## 决策 3：只纳入可共享的 Spec Kit 文件

**结论**：公共 Git allowlist 纳入 `.specify/` 和 `.agents/skills/speckit-*` 受管文件，明确忽略 `.specify/feature.json` 和其他 Agent 本机状态。

**理由**：现有仓库默认全部忽略并显式 allowlist 公共文件；Spec Kit 基础设施需要进入版本控制，而凭据和本机状态不能进入公共仓库。

**考虑过的替代方案**：全部忽略 `.agents/`；放弃该方案，因为 Codex integration manifest 将 `speckit-*` skill 作为受管项目入口，无法在干净 checkout 中复现当前集成。

## 决策 4：将中文规则写入 AGENTS.md 和 Constitution

**结论**：`AGENTS.md` 规定项目维护文档使用中文，Constitution 将其提升为工程治理原则；代码标识、命令、路径、字段、测试名称和外部原文保留精确形式。

**理由**：语言规则需要同时影响日常 Agent 操作和 Spec Kit 规格治理，单独放在某一份文档中容易漂移。

**考虑过的替代方案**：机械翻译全部既有英文能力契约；放弃该方案，因为这些文件含有精确领域术语和既有测试证据，且用户要求迁移而非大规模内容重写。
