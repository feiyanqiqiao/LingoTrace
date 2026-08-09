# Vault 初始化与跨平台运行时连接

LingoTrace 的公共运行时与私人 Obsidian Vault 必须分开保存。日常学习时，Codex 或兼容 Agent 以 Vault 为工作区；需要修改程序、语言包或测试时，才以 LingoTrace 仓库为工作区。

普通学习者不需要先执行本文命令。请把 [学习者安装协议](learner-agent-setup.md)的一句话入口交给 Agent，由它完成运行时安装、依赖检查、预览、确认和验证。本文保留初始化器与跨平台连接的技术细节。

## 1. 初始化一个新 Vault

运行时安装后，可以先运行只读诊断：

```bash
python3 -m lingotrace.init doctor \
  --language english \
  --vault /absolute/path/to/LingoTrace-English \
  --runtime-root /absolute/path/to/runtime
```

诊断把 Python 和有效运行时视为必要项，把 Obsidian Desktop、Git、GitHub CLI 与 ListenKit 的发现状态写入结构化报告；可选项缺失不会阻止文本学习初始化。

在 LingoTrace 仓库根目录运行。首次执行不加 `--apply`，只预览计划：

```bash
python3 -m lingotrace.init vault \
  --language english \
  --vault /absolute/path/to/LingoTrace-English
```

Windows 可以使用同一个模块入口，例如：

```powershell
py -m lingotrace.init vault `
  --language english `
  --vault "D:\Obsidian\LingoTrace-English"
```

确认报告没有冲突后增加 `--apply`。初始化器不会覆盖已经存在的配置、Agent 入口、模板或视图；任何冲突都会在写入前阻止执行。

初始化结果包括：

```text
LingoTrace-English/
├── AGENTS.md
├── .lingotrace/
│   ├── vault-context.json
│   ├── paths.json
│   └── runtime-connections/
│       └── <current-platform>.json
├── templates/
├── views/
├── daily/
├── listening/
├── review/
├── sources/
└── speaking/
```

`AGENTS.md` 是 Vault 工作区的自然语言入口。它告诉 Agent 先识别当前平台、解析运行时连接、读取当前语言包的 `SKILL.md`，然后把所有学习写入绑定到当前 Vault。

## 2. 为什么按平台保存连接

运行时的绝对路径通常无法跨操作系统复用：

- macOS 可能是 `/Users/name/Project/LingoTrace`；
- Windows 可能是 `D:\Projects\LingoTrace`；
- Linux 可能是 `/home/name/projects/LingoTrace`。

因此连接分别保存在：

```text
.lingotrace/runtime-connections/macos.json
.lingotrace/runtime-connections/windows.json
.lingotrace/runtime-connections/linux.json
```

每个文件可以保存多个候选路径。新增连接只会追加到当前平台文件，不会删除同平台的旧候选，也不会修改其他平台文件。这样通过 iCloud、Syncthing、OneDrive 或其他同步工具在多台设备之间同步 Vault 时，一台设备保存自己的路径不会覆盖其他操作系统的连接。

连接文件示例：

```json
{
  "runtime_connection_schema_version": 1,
  "platform": "macos",
  "connections": [
    {
      "runtime_root": "/Users/name/Project/LingoTrace",
      "source": "vault-initialization"
    }
  ]
}
```

这些文件属于私人 Vault 配置，不应提交到 LingoTrace 公共仓库。

## 3. 换到另一台设备

Agent 按以下顺序处理：

1. 只读取当前平台的连接文件。
2. 依次检查候选目录是否包含 `lingotrace/__init__.py` 和当前语言包的 `agent_skills/SKILL.md`。
3. 找到可用候选后，读取对应 Skill 并继续学习任务。
4. 如果当前平台没有连接文件，或所有候选都不可用，向用户询问本机 LingoTrace 运行时目录。
5. 验证用户提供的路径后，将它追加到当前平台文件；保留其他平台和同平台的已有候选。

用户确认新路径后，也可以显式注册：

```bash
python3 -m lingotrace.init connect-runtime \
  --vault /absolute/path/to/LingoTrace-English \
  --runtime-root /absolute/path/to/LingoTrace \
  --apply
```

检查当前设备能否解析运行时：

```bash
python3 -m lingotrace.init resolve-runtime \
  --vault /absolute/path/to/LingoTrace-English
```

如果解析失败，报告会要求 Agent 询问用户，不会根据目录名称、历史路径或其他操作系统的配置猜测运行时位置。

## 4. 日常工作区边界

日常学习：

```text
Workspace / Vault root: /path/to/LingoTrace-English
Runtime root:           /path/to/LingoTrace
```

运行时维护：

```text
Workspace: /path/to/LingoTrace
```

同一个运行时可以服务多个 Vault，但一次学习操作只能绑定一个 Vault。Vault 的目标语言由 `.lingotrace/vault-context.json` 决定，资料路径由 `.lingotrace/paths.json` 决定；运行时连接只回答“本机到哪里读取 LingoTrace 程序”，不能改变目标语言或学习资料路径。

每天首次学习的上游检查另外使用 `.lingotrace/runtime-update-checks/<platform>.json`。它只保存本地日期、运行时路径、提交标识、更新数量和结果，不保存学习内容，也不覆盖其他平台状态。检查与安全应用命令见 [每日首次学习的运行时更新设计](daily-runtime-update-design.md)。

ListenKit 不在 Vault 初始化时登记。运行时解析成功后，会读取当前设备用户应用数据目录中的共享连接；`.lingotrace/listenkit-connections/<platform>.json` 只作为特定 Vault 的显式覆盖和旧配置兼容。安装目录建议、设备连接、覆盖和失联恢复见 [ListenKit 安装位置与设备级连接](listenkit-installation-and-connections.md)。

## 5. 安全边界

- 初始化默认先预览，只有显式 `--apply` 才写入。
- 初始化不覆盖已有文件。
- 运行时注册只追加当前平台候选。
- 上游检查每天、每平台最多自动运行一次；用户明确同意前不更新。
- 个人 fork 永不由日常学习 Agent 自动 pull、merge、rebase、stash 或 reset。
- Agent 不应把公共仓库当作私人 Vault。
- Agent 不应绕过 LingoTrace core 直接修改学习文件。
- 私人笔记、音频、Obsidian 状态和运行时连接不得进入公共 Git 提交。
