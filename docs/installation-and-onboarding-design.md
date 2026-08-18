本文定义 LingoTrace 当前的安装、初始化和开发者上手契约。它不是一次性实施日志，而是后续安装器、文档和 Agent 行为必须持续满足的产品设计。

# 1. 用户分类

LingoTrace 面向两类用户：

1. **学习者**：只想使用上游正式版本学习，不修改公共源码。
2. **开发者**：会 fork 上游并修改功能或语言包。其中又分为准备向上游提交 PR 的贡献者，以及只维护自己 fork 的个人开发者。

开发者也是学习者。两类用户使用相同的运行时安装、Vault 初始化和日常学习入口；开发者只是在此基础上额外拥有源码仓库、测试、分支与协作流程。

# 2. 目标体验与角色模型

系统的整体体验基于三位一体协作模型：**Agent 大脑与执行器 + 本地 Vault 知识库 + Obsidian 桌面端 GUI 看板与播放器**。

## 2.1 学习者

用户只需向具备本地文件和命令执行能力的 Agent 发送一条引导口令：

> 请阅读并严格执行 https://raw.githubusercontent.com/feiyanqiqiao/LingoTrace/main/docs/learner-agent-setup.md ，帮我安装 LingoTrace 并初始化第一个学习 Vault。

Agent 必须从上游 `main` 读取最新引导，而不是依赖模型记忆。之后依次完成：

1. 说明将检查和可能改变的内容；
2. 询问学习语种，目前支持 `english` 和 `japanese`；
3. 给出 Vault、运行时与 ListenKit 的跨平台建议位置，并让用户确认或指定；
4. 检测 Python、Git、Obsidian 桌面客户端、LingoTrace 运行时和 ListenKit；
5. 对任何软件安装、下载或系统级变更先征得用户同意；
6. 安装最小 LingoTrace 运行时；
7. 先预览、再初始化 Vault；
8. 验证 Vault 能解析运行时和目标语言 Agent Skill；
9. 告诉用户以 Vault 为日常 Agent 工作区，并在 Obsidian 桌面端打开该 Vault，给出第一条学习请求。

Obsidian 桌面客户端负责提供可视化的 Markdown 渲染、音频切片点读跟读与 `.base` 全景复习看板，是完整学习闭环的必备官方图形端。Agent 必须清楚向用户说明并引导安装。LingoTrace 运行时、可用 Python、Obsidian 桌面端和完成初始化的 Vault 是获得完整体验的标配条件。

## 2.2 开发者

开发者把 Agent 工作区设为 fork 的源码仓库，完成账号、Git/GitHub CLI、fork、remote、topic branch、测试、推送和 PR 初始化。私人学习 Vault 始终位于仓库外；日常学习时仍把 Vault 作为 Agent 工作区。

准备向上游贡献的开发者使用：

- `origin`：自己的 GitHub fork；
- `upstream`：`https://github.com/feiyanqiqiao/LingoTrace.git`；
- `main`：只跟踪和同步，不直接开发；
- `codex/<topic>` 或其他清晰的 topic branch：承载每次改动；
- PR：从个人 fork 的 topic branch 提交到上游 `main`。

只打算自用的开发者可以不向上游开 PR，但仍应使用 topic branch，避免未来同步上游时把私有改动和 `main` 历史纠缠在一起。

# 3. 目录与分发边界

推荐位置如下；用户可以选择其他绝对路径。

| 平台 | 学习 Vault | 普通用户运行时 | ListenKit 程序 |
| --- | --- | --- | --- |
| macOS | `~/Documents/Obsidian/LingoTrace-English` | `~/Library/Application Support/LingoTrace/runtime` | `~/Library/Application Support/LingoTrace/ListenKit` |
| Windows | `%USERPROFILE%\Documents\Obsidian\LingoTrace-English` | `%LOCALAPPDATA%\LingoTrace\runtime` | `%LOCALAPPDATA%\LingoTrace\ListenKit` |
| Linux | `~/Documents/Obsidian/LingoTrace-English` | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/runtime` | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/ListenKit` |

日语 Vault 使用 `LingoTrace-Japanese`。Vault 与运行时不能相同，也不能互相嵌套。Vault 可以由用户自己的同步工具同步；平台绝对路径继续按 `.lingotrace/runtime-connections/<platform>.json` 分开保存。

ListenKit 默认建议由实际 LingoTrace 运行时动态推导：取运行时所在目录的同级 `ListenKit`，因此开发者的 `/path/to/Project/LingoTrace` 会得到 `/path/to/Project/ListenKit`。建议位置允许用户覆盖。实际安装位置默认保存在当前系统的用户应用数据目录，供所有语种 Vault 共享；Vault 内只保留显式覆盖和旧连接兼容。找不到时必须让用户选择重新安装或指定已有目录。完整契约见 [ListenKit 安装位置与设备级连接](listenkit-installation-and-connections.md)。

最小学习运行时需要仓库中的 `lingotrace/` 以及公开听力适配器 `tools/listening-transcribe-official/`。普通学习者默认使用 Git sparse checkout 只获取这两个目录；不需要下载 `tests/`、其他 `tools/`、`.github/`、贡献指南或产品设计文档。运行时保留 `.git` 元数据，以便后续 `git pull --ff-only` 更新。否则默认启用 `listening_notes` 的 Vault 会找不到公开生成器。

开发者必须使用完整 checkout，因为开发需要测试、工具、文档和 GitHub 工作流。

# 4. 同意与安全边界

Agent 可以在征得一次明确同意后执行一组已经解释过的同类安装命令，但不得静默进行以下操作：

- 安装 Obsidian、Git、Python、GitHub CLI、ListenKit 或系统包；
- 克隆或下载仓库；
- 创建用户指定位置的 Vault 或运行时目录；
- 登录 GitHub、创建 fork、推送分支或提交 PR；
- 覆盖或删除已有文件。

初始化器仍默认 dry-run，并且不覆盖已有文件。目标已有内容或路径关系不安全时必须停止，让用户决定如何处理。

# 5. 可执行入口

运行时安装后，Agent 使用统一诊断入口：

```bash
<python-command> -m lingotrace.init doctor \
  --language english \
  --vault /absolute/path/to/LingoTrace-English \
  --runtime-root /absolute/path/to/runtime
```

诊断输出 JSON，区分必要错误和可延期警告，并给出当前平台、依赖发现结果及建议路径。初始化继续使用：

```bash
<python-command> -m lingotrace.init vault --language english --vault /absolute/path/to/Vault --apply
<python-command> -m lingotrace.init resolve-runtime --vault /absolute/path/to/Vault
```

`<python-command>` 必须是预检中实际执行成功且版本至少为 3.11 的 launcher：Windows 通常为 `python`，macOS/Linux 通常为 `python3`。诊断必须报告正在运行的 `sys.executable` 与版本，不能用另一个 PATH 候选冒充当前解释器。

核心 runtime 的 Python >=3.11 与日语听力扩展的独立 Python 3.14 venv 是两层契约。后者只在用户同意安装日语听力依赖后，由 sparse runtime 内的 `tools/listening-transcribe-official/init_listening_runtime.py` 创建和检查；不得把依赖装入 core Python 或 Vault。

文档入口分为：

- `docs/learner-agent-setup.md`：可从 GitHub Raw 直接交给 Agent 的学习者安装编排；
- `docs/getting-started.md`：普通用户安装后的日常使用；
- `docs/developer-agent-setup.md`：可交给 Agent 的开发者初始化与协作流程；
- `CONTRIBUTING.md` 与 `AGENTS.md`：持续约束每次公共仓库变更；
- `docs/vault-initialization-and-runtime-connections.md`：Vault 与运行时连接的技术契约。

# 6. 验收标准

- macOS、Windows 和 Linux 均能生成稳定的推荐路径并检测常见 Obsidian 桌面安装位置。
- macOS、Windows 和 Linux 均能生成 ListenKit 程序建议目录；用户可覆盖，确认后的路径保存为设备级默认并跨语种共享。
- ListenKit 路径失效时返回“重新安装”与“指定已有目录”两种恢复选项，不影响无关文本学习。
- 诊断不会安装软件或写文件；缺少 Obsidian、Git 或 ListenKit 时给出可延期警告。
- 缺少 Python、运行时无效、Vault 路径非绝对或 Vault/运行时互相嵌套时阻止继续。
- 普通用户安装文档不会要求 fork、理解 PR 或运行开发测试。
- 普通用户的 sparse runtime 同时包含 core 包与公开听力适配器，日语听力隔离 runtime 有可重复执行的公开初始化/检查入口。
- 开发者文档明确区分个人 fork、上游仓库、topic branch、CI 和下一次改动前的上游同步。
- 初始化仍先预览、不覆盖，并验证生成的 Vault 可以解析当前平台运行时和语言 Skill。
- README 和文档索引在首屏清楚分流学习者与开发者。

# 7. 每日更新延续

初始化不是一次性安装后就失去上游联系。两类用户在每天第一次学习前都执行一次轻量上游检查；正式 checkout 可在用户明确同意后安全快进，个人 fork 只提示自行同步。用户可以忽略更新并继续学习。完整状态、话术、fork 识别和更新保护见 [每日首次学习的运行时更新设计](daily-runtime-update-design.md)。
