> 本文是面向本地 AI Agent 的可执行安装协议。用户无需懂 Git、Python 或命令行。Agent 必须完整阅读本文，再开始操作。

# 你的任务

帮助用户从零安装上游正式版 LingoTrace，初始化第一个英语或日语 Obsidian Vault，并验证用户能从 Vault 工作区开始学习。不要 fork 仓库，不要创建开发分支，不要把私人 Vault 放进运行时。

上游仓库固定为：

- 页面：`https://github.com/feiyanqiqiao/LingoTrace`
- Git：`https://github.com/feiyanqiqiao/LingoTrace.git`
- 正式分支：`main`

# 强制交互原则

1. 先用普通语言告诉用户将检查哪些项目、哪些操作可能需要安装软件。
2. 检测和只读检查可以直接执行。
3. 下载、克隆、安装软件、创建目录、写入 Vault、打开桌面应用前，先说明动作和影响并取得用户同意。
4. 不覆盖已有文件，不删除用户资料，不把 Vault 初始化到 LingoTrace 运行时内部。
5. 缺少 Obsidian 或 ListenKit 时允许用户选择“现在安装”或“以后再装”；说明角色影响并继续可行部分。
6. LingoTrace 运行时、Python 和成功初始化的 Vault 是开始使用的必要条件。
7. 命令失败时先报告真实错误并诊断，不要用降低安全性的替代命令绕过。

# 第 1 步：确认语种和位置

询问用户第一个 Vault 学英语还是日语。当前只接受：

- `english`：英语；
- `japanese`：日语。

给出以下建议位置，同时允许用户指定其他绝对路径：

| 平台 | Vault | LingoTrace 运行时 | ListenKit 程序 |
| --- | --- | --- | --- |
| macOS | `~/Documents/Obsidian/LingoTrace-English` | `~/Library/Application Support/LingoTrace/runtime` | `~/Library/Application Support/LingoTrace/ListenKit` |
| Windows | `%USERPROFILE%\Documents\Obsidian\LingoTrace-English` | `%LOCALAPPDATA%\LingoTrace\runtime` | `%LOCALAPPDATA%\LingoTrace\ListenKit` |
| Linux | `~/Documents/Obsidian/LingoTrace-English` | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/runtime` | `${XDG_DATA_HOME:-~/.local/share}/lingotrace/ListenKit` |

日语把目录名改为 `LingoTrace-Japanese`。显示解析后的绝对路径并让用户确认。Vault 和运行时必须分开，且不能互相嵌套。ListenKit 默认建议始终是实际 LingoTrace 运行时所在目录的同级 `ListenKit`；如果用户为运行时选择了其他位置，应随之重新计算，而不是继续使用表中的示例。ListenKit 建议目录不是强制值，用户可以选择其他绝对路径。

# 第 2 步：只读预检

识别当前操作系统，检查：

- Python 3.11 或更高版本，用于核心 runtime 和 Vault 初始化；日语听力的本地词典扩展另用独立的 Python 3.14 runtime；
- Git；
- Obsidian **桌面客户端**，不要把 Obsidian CLI 当成桌面客户端；
- 用户选择的运行时和 Vault 路径是否已经存在；
- ListenKit CLI 或仓库。

常见 Obsidian 桌面位置包括：

- macOS：`/Applications/Obsidian.app`、`~/Applications/Obsidian.app`；
- Windows：`%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`、`%LOCALAPPDATA%\Obsidian\Obsidian.exe`、Program Files 下的 Obsidian；
- Linux：PATH 中的 `obsidian`、AppImage、Snap 或 Flatpak 安装位置。

如果缺少 Python 或 Git，解释它们分别用于运行初始化器和获取/更新正式运行时，然后在用户同意后按当前平台的可信包管理方式安装。不要在本文硬编码未经验证的第三方下载站；优先使用 Python、Git、Obsidian 官方发布渠道或系统自带包管理器。

# 第 3 步：安装最小正式运行时

运行时目标不存在或为空时，在用户同意后使用 Git sparse checkout，只取核心包和公开听力适配器：

```bash
git clone --filter=blob:none --no-checkout https://github.com/feiyanqiqiao/LingoTrace.git <runtime-root>
git -C <runtime-root> sparse-checkout init --no-cone
git -C <runtime-root> sparse-checkout set /lingotrace/ /tools/listening-transcribe-official/
git -C <runtime-root> checkout main
```

这些命令中的 `<runtime-root>` 必须替换为用户确认的绝对路径，并使用适合当前 shell 的参数传递方式。不要通过字符串拼接执行未经验证的用户输入。

如果目标已是 LingoTrace Git checkout：

1. 验证 remote 指向上游或用户明确认可的可信镜像；
2. 检查工作区是否干净；
3. 干净时才能执行 `git pull --ff-only origin main`；
4. 有本地改动、分支不明或 remote 异常时停止并说明，不覆盖。

如果 Git 无法使用但 Python 可用，可以在获得同意后从上游 `main` 下载官方源码归档作为降级方案；必须验证归档中存在 `lingotrace/__init__.py` 和 `tools/listening-transcribe-official/transcribe_listening.py`，并告知用户以后不能用 Git 增量更新。

先选定一个实际可用、版本至少为 3.11 的 Python launcher，并在本次安装中始终用 `<python-command>` 代替它。Windows 通常是 `python`（或经验证可用的 `py -3`），macOS/Linux 通常是 `python3`；必须以 `<python-command> -c "import sys; print(sys.executable); print(sys.version)"` 的实际输出为准。不要因为 PATH 中存在 Windows Store 的 `python3.exe` 别名就认定它可用，也不要硬编码某个用户目录或 Python 3.14 安装路径。

初始化完成后，每天第一次学习请求前执行 `<python-command> -m lingotrace.init check-update --vault <vault-root> --runtime-root <runtime-root>`。当天已经检查时命令不会再次联网。有更新时根据结构化 commit 信息，用一至三点中文概括新增、修复或维护内容，询问是否现在更新，并明确用户可以忽略、继续学习。

只有用户清楚地说“更新”或同等明确表达后，才执行 `<python-command> -m lingotrace.init apply-update --vault <vault-root> --runtime-root <runtime-root> --apply`。正式 sparse checkout 只有在 `main` 干净且可以快进时才会更新；识别为个人 fork 时不得自动 pull、merge、rebase、stash 或 reset，应请用户在开发仓库自行同步。检查失败或用户不更新都不阻止学习。

# 第 4 步：运行统一诊断

从运行时根目录执行，并沿用第 3 步已经验证的 launcher：

```bash
<python-command> -m lingotrace.init doctor \
  --language <english-or-japanese> \
  --vault <absolute-vault-path> \
  --runtime-root <absolute-runtime-path>
```

读取 JSON 报告：

- `errors` 是继续初始化前必须解决的问题；
- `warnings` 是可以延期的能力；
- `dependencies` 记录发现的 Python、Git、GitHub CLI、Obsidian、ListenKit 和运行时。

如果 `dependencies.listenkit` 已经返回有效程序根目录，向用户确认是否使用该目录；确认后在第 5 步把它登记为设备级默认连接。不要把同一路径重复写入每个语言 Vault。

不要因为 Obsidian、GitHub CLI 或 ListenKit 缺失而谎称整个初始化失败。GitHub CLI 只对开发协作有用，学习者不需要它。

# 第 5 步：可选安装 Obsidian 与 ListenKit

## Obsidian Desktop

未发现桌面客户端时，向用户解释 Obsidian 桌面端作为**官方图形界面（GUI）与多媒体终端**的作用（提供排版阅读、音频切片点读跟读，以及基于 `.base` 文件的全景复习看板渲染），并询问用户是否现在安装：

- 同意：使用 Obsidian 官方下载或当前系统可信包管理器，安装后重新检测；
- 暂不安装：继续初始化 Vault，向用户明确说明：底层笔记文件和卡片仍可正常生成，但日常直观查看看板和点击播放音频切片需要 Obsidian Desktop 才能获得完整体验。

## ListenKit

ListenKit 负责媒体获取、ASR 和切片。未发现时，询问用户是否现在安装：

- 同意：先读取 `https://github.com/feiyanqiqiao/ListenKit` 当前官方 README/安装说明，再按其最新流程安装；不要依赖模型记忆猜测命令；
- 暂不安装：继续文本学习能力，明确首次请求音视频导入或转写时 Agent 应再次提示。

LingoTrace 与 ListenKit 应使用独立运行环境，不要把彼此的 Python 依赖混装。

如果用户选择日语并要启用听力功能，Agent 应先确认有一个实际可运行的 Python 3.14 launcher，然后说明将在当前用户的本机 Cache 中创建独立 venv 并安装固定版本的离线词典包。只有用户同意后才执行：

```bash
<python3.14> <runtime-root>/tools/listening-transcribe-official/init_listening_runtime.py \
  --bootstrap-python <python3.14> \
  --install
```

安装后用同一公开入口执行 `--check`。该 runtime 默认位于 macOS `~/Library/Caches/LingoTrace/venvs/cpython-314`、Windows `%LOCALAPPDATA%\LingoTrace\venvs\cpython-314` 或 Linux XDG cache；不得放入 Vault、iCloud Drive 或 OneDrive。英语听力不依赖该日语词典 runtime。

## macOS 文件访问权限

当 Agent 宿主首次访问 `Documents` 中的 Vault 时，macOS 可能请求“文件与文件夹”权限。先请用户在“系统设置 → 隐私与安全性”中只授予宿主所需的最小目录权限，然后重试只读诊断。“完全磁盘访问权限”不是通用前置条件；只有在最小权限仍明确被 TCC 拒绝、且用户理解影响并同意时，才把它作为故障排查选项。iCloud 文件尚未下载是另一类问题，应先确认素材已在本机完整可读。

安装前必须再次显示第 1 步确认的 ListenKit 目录；如果用户尚未确认，则显示 `doctor` 返回的 `recommended_listenkit_root` 并允许自选。安装后验证根目录存在 `README.md`，并验证当前平台入口：Windows 是 `cli/generate-markdown.ps1`，macOS/Linux 是 `cli/generate-markdown.sh`。再先预览、后登记设备级默认连接：

```bash
<python-command> -m lingotrace.init connect-listenkit \
  --listenkit-root <absolute-listenkit-path>

<python-command> -m lingotrace.init connect-listenkit \
  --listenkit-root <absolute-listenkit-path> \
  --apply
```

设备连接不依赖 Vault，因此可以在第 6 步初始化 Vault 之前完成。以后任意语种 Vault 的媒体任务前都运行 `resolve-listenkit --vault <current-vault>`。只有某个 Vault 明确需要不同 checkout 时，才增加 `--scope vault --vault <absolute-vault-path>` 保存覆盖。如果连接不存在或路径失效，必须让用户选择“重新安装”或“指定已经安装的目录”，不得猜测；详细契约见 [ListenKit 安装位置与设备级连接](listenkit-installation-and-connections.md)。

# 第 6 步：预览并初始化 Vault

先执行预览，不加 `--apply`：

```bash
<python-command> -m lingotrace.init vault \
  --language <english-or-japanese> \
  --vault <absolute-vault-path> \
  --runtime-root <absolute-runtime-path>
```

向用户概括将创建的 Vault 配置、模板、视图和当前平台运行时连接。如果报告无错误，再取得写入确认并增加 `--apply`。初始化器不得覆盖已存在的文件；出现 `target_conflict` 时停止，询问用户是选择新目录还是对现有 Vault 做专门迁移分析。

# 第 7 步：验证和交付

执行：

```bash
<python-command> -m lingotrace.init resolve-runtime --vault <absolute-vault-path>
```

只有同时满足以下条件才宣布完成：

- 报告 `accepted: true`；
- `runtime_root` 是本机选定运行时；
- `agent_skill` 指向目标语种 Skill；
- Vault 根存在 `AGENTS.md`、`.lingotrace/vault-context.json`、`.lingotrace/paths.json`；
- `views/total-training.base` 与模板目录存在。

如果已经安装 ListenKit，还要执行 `<python-command> -m lingotrace.init resolve-listenkit --vault <absolute-vault-path>`，并确认报告返回实际的 `listenkit_root` 与当前平台入口。Windows 不得通过 `/bin/bash`、WSL launcher 或 Git Bash 运行 `.sh` 入口。如果用户选择延期安装，不创建虚假的连接记录。

最后告诉用户：

1. 在 Obsidian Desktop 中把 Vault 目录作为 Vault 打开（用于查看看板、精听点读与自测）；
2. 在 Codex 或兼容 Agent 中把 **Vault 目录**设为日常学习工作区（用于用自然语言下达建卡与结算指令）；
3. LingoTrace 运行时目录只用于程序更新，不用于存放私人学习资料；
4. 可以从“帮我把这篇英文材料整理成学习笔记”或“请把这段日语音频做成精听稿”开始。

如果用户暂缓了 Obsidian 或 ListenKit，明确列出待办项和受影响能力，不要把“基础初始化完成”描述成“所有视觉与多媒体能力已就绪”。
