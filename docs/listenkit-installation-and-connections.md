# ListenKit 安装位置与跨平台连接

ListenKit 是 LingoTrace 的可选媒体依赖，负责音视频获取、转写和切片。它不是 Vault 内容，也不是 LingoTrace Python 环境的一部分。本文定义 LingoTrace 在安装、发现、保存和恢复 ListenKit 程序目录时必须遵守的产品契约。

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

## 2. 安装成功后保存连接

可用的 ListenKit 根目录至少包含：

```text
README.md
cli/generate-markdown.sh
```

如果 Vault 已经初始化，验证通过后，Agent 先预览、再登记：

```bash
python3 -m lingotrace.init connect-listenkit \
  --vault /absolute/path/to/LingoTrace-English \
  --listenkit-root /absolute/path/to/ListenKit

python3 -m lingotrace.init connect-listenkit \
  --vault /absolute/path/to/LingoTrace-English \
  --listenkit-root /absolute/path/to/ListenKit \
  --apply
```

如果 ListenKit 在 Vault 初始化前已经安装，不要提前在空目录中写连接；直接把 `--listenkit-root` 交给初始化器，新 Vault 会同时生成当前平台连接：

```bash
python3 -m lingotrace.init vault \
  --language english \
  --vault /absolute/path/to/LingoTrace-English \
  --runtime-root /absolute/path/to/LingoTrace/runtime \
  --listenkit-root /absolute/path/to/ListenKit \
  --apply
```

## 3. 连接如何保存

ListenKit 连接与 LingoTrace 运行时连接相互独立：

通用形式是 `.lingotrace/listenkit-connections/<platform>.json`，当前支持以下三个平台文件：

```text
.lingotrace/listenkit-connections/macos.json
.lingotrace/listenkit-connections/windows.json
.lingotrace/listenkit-connections/linux.json
```

每个平台文件可以保存多个候选位置。登记新位置只追加当前平台候选，不自动删除同平台旧路径，也不修改其他平台文件。这样同一个 Vault 同步到多台电脑后，每台设备都能保留自己的 ListenKit 位置。

连接文件示例：

```json
{
  "listenkit_connection_schema_version": 1,
  "platform": "macos",
  "connections": [
    {
      "listenkit_root": "/Users/name/Documents/Project/ListenKit",
      "source": "user-confirmed"
    }
  ]
}
```

这些文件是私人 Vault 的本机配置，不应提交到 LingoTrace 公共仓库。

## 4. 日常解析与失联恢复

音视频导入或转写前，Agent 从已经解析出的 LingoTrace 运行时执行：

```bash
python3 -m lingotrace.init resolve-listenkit \
  --vault /absolute/path/to/LingoTrace-English
```

解析器只读取当前操作系统的连接文件，依次验证候选目录。找到可用目录时返回 `listenkit_root` 和 `generate_markdown` 入口。

如果当前平台没有连接，或全部候选目录失效，Agent 必须向用户提供两条人话选项：

1. **重新安装 ListenKit**：显示当前已解析的 LingoTrace 运行时同级 `ListenKit` 建议目录，同时允许用户另选位置；取得同意后读取上游最新安装说明并执行。
2. **指定已经安装的 ListenKit**：请用户提供目录，验证后通过 `connect-listenkit` 追加到当前平台连接。

Agent 不得根据文件夹名称、另一平台路径或历史记忆猜测新位置，也不得为了修复当前设备而覆盖其他平台记录。ListenKit 失联只阻止需要媒体工具的任务，不阻止阅读、词汇、语法、口语卡或复习结算等文本学习任务。

## 5. Python/ASR 环境边界

本文保存的是 ListenKit **程序根目录**。ListenKit 自己的 Python/ASR 环境由 ListenKit 项目负责初始化、升级和检查，不写入上述连接文件，也不与 LingoTrace Python 环境混装。

LingoTrace 当前只验证了 macOS 听力运行时隔离。Windows 或 Linux 能保存和恢复 ListenKit 程序连接，不等于对应平台的原生 ASR 依赖已经得到验证；实际安装仍以 ListenKit 上游当前平台说明为准。
