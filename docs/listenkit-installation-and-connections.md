# ListenKit 安装位置与设备级连接

ListenKit 是 LingoTrace 的可选媒体依赖，负责音视频获取、转写和切片。它不是 Vault 内容，也不属于某个语言包。本文定义 LingoTrace 在安装、发现、保存和恢复 ListenKit 程序目录时必须遵守的产品契约。

下文的 `<python-command>` 指本机实际验证可用、版本至少为 3.11 的 Python launcher；Windows 通常是 `python`，macOS/Linux 通常是 `python3`。

## 1. 安装前必须确认位置

Agent 在下载或安装 ListenKit 前，必须先解析当前设备的 LingoTrace 运行时。ListenKit 的默认建议永远是 **LingoTrace 运行时所在目录的同级 `ListenKit`**，同时允许用户指定其他绝对路径。

| 场景 | 已解析的 LingoTrace 运行时 | ListenKit 程序建议目录 |
| --- | --- | --- |
| macOS 开发仓库示例 | `/Users/name/Documents/Project/LingoTrace` | `/Users/name/Documents/Project/ListenKit` |
| macOS 普通运行时 | `~/Library/Application Support/LingoTrace/runtime` | `~/Library/Application Support/LingoTrace/ListenKit` |
| Windows 普通运行时 | `%LOCALAPPDATA%\LingoTrace\runtime` | `%LOCALAPPDATA%\LingoTrace\ListenKit` |
| Linux 普通运行时 | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/runtime` | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/ListenKit` |

建议目录只是默认选项，不是强制目录。Agent 必须显示解析后的绝对路径并让用户确认。用户可以选择开发目录、独立磁盘或其他位置，只要该目录与私人 Vault 分离且不会覆盖已有文件。

用户同意安装后，Agent 仍须读取 ListenKit 上游当前 README 和安装说明，不得根据旧记忆猜测依赖或命令。任何克隆、下载、系统包安装和运行时初始化都需要用户同意。

## 2. 保存设备级默认连接

可用的 ListenKit 根目录至少包含 `README.md`，并包含当前操作系统对应的入口：

```text
README.md
Windows:     cli/generate-markdown.ps1
macOS/Linux: cli/generate-markdown.sh
```

Windows 原生链路只调用 PowerShell 入口，不探测 `/bin/bash`、WSL launcher 或 Git Bash 来运行 `.sh`。

验证通过后，Agent 先预览、再登记设备级默认连接；该操作与任何语言 Vault 无关：

```bash
<python-command> -m lingotrace.init connect-listenkit \
  --listenkit-root /absolute/path/to/ListenKit

<python-command> -m lingotrace.init connect-listenkit \
  --listenkit-root /absolute/path/to/ListenKit \
  --apply
```

设备级连接按当前操作系统保存在用户应用数据目录：

```text
macOS:   ~/Library/Application Support/LingoTrace/connections/listenkit.json
Windows: %LOCALAPPDATA%\LingoTrace\connections\listenkit.json
Linux:   ${XDG_DATA_HOME:-~/.local/share}/lingotrace/connections/listenkit.json
```

测试、便携安装或受控部署可以用 `LINGOTRACE_DATA_HOME` 覆盖 `LingoTrace` 数据根目录。普通用户不需要设置该环境变量。

同一设备上的英语、日语和未来语言 Vault 默认共享这份连接。新建 Vault 时只登记 LingoTrace 运行时，不接收或写入 ListenKit 路径。

## 3. 可选的 Vault 覆盖

只有某个 Vault 明确需要不同的 ListenKit checkout 时，才保存 Vault 覆盖：

```bash
<python-command> -m lingotrace.init connect-listenkit \
  --scope vault \
  --vault /absolute/path/to/Vault \
  --listenkit-root /absolute/path/to/ListenKit

<python-command> -m lingotrace.init connect-listenkit \
  --scope vault \
  --vault /absolute/path/to/Vault \
  --listenkit-root /absolute/path/to/ListenKit \
  --apply
```

Vault 覆盖继续使用原有跨平台路径：

```text
.lingotrace/listenkit-connections/macos.json
.lingotrace/listenkit-connections/windows.json
.lingotrace/listenkit-connections/linux.json
```

这些文件不再是默认连接位置。现有 Vault 文件不会被删除或改写；升级后会自然作为高优先级覆盖继续生效。需要让多个 Vault 共享同一路径时，再用默认的 `connect-listenkit` 命令登记一次设备连接即可。

## 4. 连接格式与候选位置

设备默认和 Vault 覆盖使用相同的连接结构，每个平台可以保存多个候选位置。登记新位置只追加当前平台候选，不自动删除旧路径。

```json
{
  "listenkit_connection_schema_version": 1,
  "platform": "windows",
  "connections": [
    {
      "listenkit_root": "C:\\Users\\name\\Documents\\Project\\ListenKit",
      "source": "user-confirmed"
    }
  ]
}
```

设备连接是本机配置，不进入 LingoTrace 公共仓库。Vault 覆盖属于私人 Vault 配置，也不得进入公共仓库。

## 5. 日常解析顺序

音视频导入或转写前，Agent 从已经解析出的 LingoTrace 运行时执行：

```bash
<python-command> -m lingotrace.init resolve-listenkit \
  --vault /absolute/path/to/Vault
```

解析顺序固定为：

1. 本次命令显式提供的 `--listenkit-root`；
2. 当前 Vault 的可选覆盖；
3. 当前设备的共享默认连接；
4. 已验证可用的 LingoTrace 运行时同级 `ListenKit`。

找到可用目录时返回 `listenkit_root`、`generate_markdown` 和 `connection_scope`。显式路径只用于本次解析，不自动保存。运行时同级目录必须实际包含 ListenKit 标志文件才会成为兜底结果；不存在时只作为建议位置报告。

如果全部来源都不可用，Agent 必须向用户提供两条人话选项：

1. **重新安装 ListenKit**：显示当前已解析的 LingoTrace 运行时同级建议目录，同时允许用户另选位置；取得同意后读取上游最新安装说明并执行。
2. **指定已经安装的 ListenKit**：请用户提供目录，验证后登记为设备默认；仅在用户明确要求时登记 Vault 覆盖。

Agent 不得根据任意文件夹名称或历史记忆猜测新位置。ListenKit 失联只阻止需要媒体工具的任务，不阻止阅读、词汇、语法、口语卡或复习结算等文本学习任务。

## 6. Python/ASR 环境边界

本文保存的是 ListenKit **程序根目录**。ListenKit 自己的 Python/ASR 环境由 ListenKit 项目负责初始化、升级和检查，不写入上述连接文件，也不与 LingoTrace Python 环境混装。

LingoTrace 当前只验证了 macOS 听力运行时隔离。Windows 或 Linux 能保存和恢复 ListenKit 程序连接，不等于对应平台的原生 ASR 依赖已经得到验证；实际安装仍以 ListenKit 上游当前平台说明为准。
