# LingoTrace 多语言架构

本文是 LingoTrace 当前多语言架构的正式来源。它描述已经落地的运行边界，不记录实施阶段、旧框架迁移过程或历史 PR 计划。

## 1. 核心决策

LingoTrace 采用以下模型：

- 一个公共运行时支持多种目标语言；
- 每个私人 Vault 只绑定一种目标语言和一个语言包；
- 公共运行时与私人 Vault 分离；
- 日常学习以 Vault 为 Agent 工作区；
- 程序维护以公共运行时仓库为工作区；
- 同一个运行时可以服务多个 Vault，但一次操作只能绑定一个 Vault。

如果同一个人学习日语和英语，应建立两个 Vault。词汇、语法、听力资料、复习队列和私人记录不在同一个 Vault 中混合。

## 2. 四层结构

```text
公共核心
  └── 语言包（Japanese / English / Future）
        └── Vault 配置
              └── 私人学习数据
```

| 层级 | 职责 | 典型内容 | 所有者 |
| --- | --- | --- | --- |
| 公共核心 | 跨语言稳定契约 | 上下文、能力检查、路径边界、SRS、写入保护 | LingoTrace |
| 语言包 | 语言特有行为 | 字段、模板、验证器、工作流、Agent Skill | 语言包维护者 |
| Vault 配置 | 选择和绑定能力 | 目标语言、语言包版本、启用能力、路径、运行时连接 | Vault 用户 |
| 私人数据 | 实际学习记录 | 笔记、卡片、媒体、复习状态、批注 | Vault 用户 |

公共核心不能根据目录名、标签、笔记语言或历史文件猜测目标语言。目标语言必须由 Vault 上下文显式声明。

## 3. 公共运行时与私人 Vault

公共仓库保存：

- `lingotrace/core/`；
- `lingotrace/packs/`；
- Vault 初始化与迁移工具；
- 公共模板、视图、测试和文档。

私人 Vault 保存：

- `.lingotrace/` 配置；
- 模板和视图的 Vault 实例；
- 学习笔记和复习卡；
- 音频、图片、转写和私人批注；
- Obsidian 本地状态。

公共仓库不得位于私人 Vault 内，私人数据也不得提交到公共仓库。语言包升级不能通过覆盖整个 Vault 完成。

## 4. Vault 上下文与路径

`.lingotrace/vault-context.json` 回答：

- 这个 Vault 学习哪种语言；
- 使用哪个语言包及版本；
- Vault Schema 版本；
- 允许哪些能力。

`.lingotrace/paths.json` 回答：

- 词汇、语法、错题、发音、听力、来源笔记、口语卡和日记分别保存在哪里。

路径配置不能覆盖语言身份。路径解析优先使用 Vault 显式配置，再使用语言包默认值；不提供旧目录锚点或内容猜测回退。

## 5. 运行时连接

运行时位于 Vault 外部，而日常 Agent 工作区是 Vault，因此初始化必须为两者建立可发现的连接。

每个平台使用独立文件：

```text
.lingotrace/runtime-connections/macos.json
.lingotrace/runtime-connections/windows.json
.lingotrace/runtime-connections/linux.json
```

每个文件可以保存多个绝对路径候选。解析规则为：

1. 只读取当前操作系统的文件；
2. 按保存顺序查找包含 LingoTrace package 和当前语言包 Skill 的候选；
3. 找到后读取 Skill 并绑定当前 Vault；
4. 如果找不到，向用户询问本机运行时目录；
5. 验证后追加到当前平台文件；
6. 不自动删除旧候选，不修改其他平台文件。

这种分离避免通过同步软件在 Windows、macOS 和 Linux 之间同步 Vault 时相互覆盖本机绝对路径。完整操作见 [Vault 初始化与跨平台运行时连接](vault-initialization-and-runtime-connections.md)。

## 6. 语言包边界

语言包拥有：

- `manifest.json`：能力、版本、外部工具和公共资源；
- `paths.json`：默认路径角色；
- `fields.json`：语言特有字段；
- `agent_skills/SKILL.md`：自然语言操作入口；
- `validators.py`：语言特有验证；
- `workflows.py`：语言包工作流；
- `templates/` 和 `views/`：默认用户界面资产。

语言包不得回退到另一个语言包的工作流、词典、字段、路径或标签。共享逻辑只有在证明具有跨语言稳定意义后才能进入 core。

Japanese 和 English 当前均实现：

- `listening_notes`；
- `source_notes`；
- `review_materials`；
- `review_queue`；
- `review_lifecycle_migration`；
- `vocab_consolidation`；
- `speaking_cards`；
- `review_rollover`；
- `total_training_dashboard`。

语言特有差异保留在语言包内。例如 Japanese 拥有假名、音调重音和汉字差异规则；English 拥有 IPA、单词重音、英英释义、搭配和英语语块规则。

## 7. Agent 工作模型

日常学习不要求用户记函数名、Payload 或写入模式。用户只需表达学习意图，例如：

- “请把这段音频做成精听稿。”
- “帮我把这篇文章整理成英语学习笔记。”
- “把这个词加入复习。”
- “这句话很实用，帮我做成口语卡。”
- “今天复习结束了，帮我结算。”

初始化生成的 Vault 根 `AGENTS.md` 负责：

1. 发现当前平台运行时；
2. 在当天首次学习前检查正式上游，按平台状态去重；
3. 有更新时用中文概括并询问，允许忽略；
4. 正式 checkout 经明确同意后安全快进，个人 fork 只提示自行同步；
5. 读取 Vault 上下文和路径；
6. 加载目标语言的 Agent Skill；
7. 把任务绑定到当前 Vault；
8. 要求所有写入通过 core 和语言包能力执行。

Agent 可以做语义判断、内容整理和不确定性分析；路径边界、状态推进、重复检查和写入保护应由确定性代码执行。

每日检查失败、用户忽略或 fork 拒绝自动更新都不得阻止原学习任务。完整协议见 [每日首次学习的运行时更新设计](daily-runtime-update-design.md)。

## 8. 写入安全

所有会修改 Vault 的工作流遵守：

```text
读取 Vault 上下文
  -> 验证语言包和版本
  -> 验证能力已启用
  -> 解析路径角色
  -> 检查输入和冲突
  -> 预览变更
  -> 受保护写入
  -> 验证结果
```

新增文件在目标不存在时可以按明确请求写入。覆盖、合并、移动、批量重写和已有复习状态修改需要用户确认；明确的每日复习结算按 Skill 规定执行内部预览、应用和第二次预览。

运行时不能扫描未绑定的其他 Vault，也不能把一个 Vault 的缓存、查重结果或状态带入另一个 Vault。

## 9. 初始化契约

初始化默认只输出 dry-run 报告。显式应用后生成：

- Vault 根 `AGENTS.md`；
- Vault 上下文；
- 路径配置；
- 当前平台运行时连接；
- 语言包声明的目录、模板和默认视图。

初始化不得覆盖已有文件。同步到新设备后，如果本机运行时路径不同，Agent 必须询问用户并追加本机连接，而不是覆盖其他设备的配置。

### 9.1 分发与用户旅程

学习者与开发者共用同一套语言包、Vault 初始化和日常 Skill，但使用不同 checkout：

- 学习者通过 Git sparse checkout 只获取 `lingotrace/`，将其作为可更新的最小运行时；
- 开发者获取完整仓库，使用测试、工具、文档和 GitHub 工作流；
- 开发者的真实学习 Vault 仍位于仓库外，并使用学习者初始化流程。

上游 GitHub Raw 文档是仓库尚未下载时的 bootstrap 入口。Agent 读取最新的 [学习者安装协议](learner-agent-setup.md)，经用户同意后安装运行时，再调用 `python -m lingotrace.init doctor` 和 Vault 初始化器。完整设计见 [安装与双用户旅程设计](installation-and-onboarding-design.md)。

## 10. 版本与升级

- 运行时和语言包使用语义化版本；
- Vault Schema 使用单调递增整数；
- Vault 固定已验证的语言包版本；
- 不兼容时必须在写入前停止；
- 模板升级必须区分语言包默认模板与用户已修改实例；
- 升级不能静默启用新能力或重写私人内容。

## 11. 外部工具

ListenKit 负责媒体导入、ASR 和切片；LingoTrace 负责学习笔记、复习材料和状态。外部工具必须通过显式 Artifact 契约接入，不能绕过 Vault 上下文、能力检查和写入保护。

ListenKit 程序位置是设备级、跨语种配置，由已解析的 LingoTrace 运行时从用户应用数据目录读取。Vault 默认不保存重复连接；只有特定 Vault 明确需要不同 checkout 时才使用 Vault 覆盖。解析顺序为本次显式路径、Vault 覆盖、设备默认、已验证的运行时同级目录。

听力运行时的 Python 环境隔离见 [Listening Runtime Isolation](listening-runtime-isolation.md)。

## 12. 验证要求

公共变更至少覆盖：

- core 单元测试；
- Japanese 与 English 语言包一致性测试；
- Vault 初始化和跨平台连接测试；
- 当前用户故事与 Agent Skill 契约；
- 公开文件 allowlist；
- GitHub Actions 中的现行检查。

历史实施计划、评审草稿和已完成迁移阶段不属于现行规范。需要了解演进过程时应查看 Git 历史和已合并 PR；公共文档只保留当前可执行行为和仍有效的设计约束。
