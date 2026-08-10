# Agent 运行兼容性报告：原生 Windows（LingoTrace 侧）

- 报告日期：2026-08-10
- 报告范围：LingoTrace 运行时在原生 Windows 上的可执行性，以及对「Claude Code Agent」（非原定目标 Codex）的兼容性
- 报告者：Claude Code（Anthropic 的 Agent CLI），运行于 Windows 11，shell 为 Git Bash
- 关联报告：`ListenKit/docs/agent-compatibility-report/claude-code-agent-windows-compatibility.md`

---

## 一、我是谁

**一句话身份：我是运行在 Windows（win32）操作系统之上的「Claude Code」Agent 框架中的 AI 助手，是 LingoTrace 学习 Vault 的日常执行 Agent 之一，也是本仓库 `SKILL.md` / `AGENTS.md` 的实际消费方。**

- **Agent 框架 / 产品**：Claude Code —— Anthropic 官方的命令行 Agent CLI（终端/桌面/IDE 均可运行）。我以「Agent Loop」方式运行：每轮读取指令与工具结果、选择工具、执行、回收输出并迭代。框架为我提供 Bash（Git Bash）、文件系统读写、Grep/Glob 检索、Web 检索等工具；与 WorkBuddy 沙箱不同，我的 Bash 工具**可以**从 bash 调用 PowerShell（`powershell`/`pwsh`）并完整读取其 stdout。
- **宿主操作系统**：Windows 11（系统内部标识 `win32`，Build 10.0.26220，AMD64）。我的命令执行入口是 Git Bash（`/usr/bin/bash`，GNU bash 5.3.15，MSYS2/MINGW64 环境），与 WorkBuddy 的托管 Git Bash 类似，但工具能力不同。
- **与运行时的关系**：我通过 Vault 根的 `AGENTS.md` 接入：解析 `.lingotrace/vault-context.json`、`.lingotrace/paths.json` 与 `.lingotrace/runtime-connections/windows.json`，读取本运行时 `lingotrace/packs/english/agent_skills/SKILL.md`，把用户的自然语言学习请求映射到英语包能力上。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | Windows 11（10.0.26220），AMD64（主机名 GeekPro） |
| 默认 Shell | Git Bash（MSYS2/MINGW64，`/usr/bin/bash`） |
| PowerShell | Windows PowerShell **5.1**.26100.9022（`powershell`，可从 Bash 调用并捕获 stdout） |
| PowerShell 7 | **pwsh 7.6.4** 可用（`shutil.which("pwsh")` 可解析） |
| `python`（真实） | 3.14.4（`%LOCALAPPDATA%\Programs\Python\Python314\python.exe`） |
| `python3` | **Microsoft Store 别名 stub**（`AppInstallerPythonRedirector.exe`，调用即 exit 49、无输出） |
| `py` 启动器 | **不存在** |
| `bash` 解析 | `shutil.which("bash")` → `C:\Program Files\Git\usr\bin\bash.EXE`（**可被找到**） |
| git / gh | 均在 PATH（`C:\Program Files\Git\...`、`GitHub CLI`） |
| ffmpeg / ffprobe / yt-dlp | 均在 PATH（WinGet Links） |
| ListenKit 托管运行时 | `%LOCALAPPDATA%\ListenKit\venvs\cpython-314`，**健康**（CUDA float16、faster-whisper 1.2.1、model small 已缓存） |
| 本仓库 Git 状态 | `main` 分支，工作区干净（除 `docs/agent-compatibility-report/` 未跟踪外）；`origin` 为个人 fork、`upstream` 为官方 |

---

## 二、问题是什么

我把本运行时的能力拆成「非听力链路」与「听力链路」两块，分别做了代码审计与真实运行验证。

**结论先行：非听力链路（init CLI、core、英语包、公共校验脚本）在 Windows 上全部健康；听力链路（SKILL.md 中最靠前的「把音频做成精听稿」能力）在原生 Windows 上必然失败，且失败点不止一处。**

### 2.1 已验证可正常工作的部分（实测通过）

| 能力 | 结果 |
| --- | --- |
| `python -m lingotrace.init resolve-runtime --vault <vault>` | `accepted: true`，正确解析运行时与 SKILL 路径 |
| `python -m lingotrace.init doctor --language english ...` | `exit_code: 0`，仅 `obsidian_desktop_not_found` 告警（见 2.4 问题 5） |
| `python -m lingotrace.init resolve-listenkit --vault <vault>` | `accepted: true`，解析出 ListenKit 根，但 `generate_markdown` 返回 `.sh`（见 2.2 问题 2） |
| `python -m lingotrace.init check-update ...` | `status: already_checked_today`，fork 识别正确，未触碰工作区 |
| 英语包 `review_rollover(mode="preview")` | `accepted: true`，`errors: []`，核心写守卫工作正常 |
| `bash tools/git/check-public-staged-files.sh` | Git Bash 下正常执行（无 `/bin/bash`、无 Unix-only 命令；CRLF 风险见附录） |

结论：`lingotrace/core/*`、英语/日语包、`init` CLI 在 Windows 上没有兼容性问题——代码审计确认核心与语言包中**没有任何** `subprocess`、`shell=True`、`os.access(X_OK)`、硬编码 POSIX 路径（详见附录审计范围）。

### 2.2 P0：听力链路在原生 Windows 上必然失败

`SKILL.md` 的「Listening Notes」是本运行时最核心的日常能力，它在原生 Windows 上 100% 失败。我实测复现。

**问题 1：硬编码 `/bin/bash` 绝对路径**

`tools/listening-transcribe-official/transcribe_listening.py:646`：

```python
command = [
    "/bin/bash",
    str(script_path),
    ...
]
```

原生 Windows 上 `/bin/bash` 不是可被 Win32 `CreateProcess` 解析的路径（会退化成 `\bin\bash`）。我的实测复现（直接调用 `invoke_listenkit`）：

```
invoke EXCEPTION: FileNotFoundError : [WinError 2] 系统找不到指定的文件。
```

注意：**这台设备上 bash 是存在的**（`shutil.which("bash")` → `C:\Program Files\Git\usr\bin\bash.EXE`），失败的唯一原因就是硬编码了 POSIX 绝对路径而不是做解释器发现。这是纯粹的平台问题，与具体 Agent 无关。

**问题 2：跨运行时契约违背——在 Windows 上仍返回 `.sh` 入口**

`lingotrace/init/listenkit_connections.py:341` 的 `_resolved_report` 无条件返回：

```python
"generate_markdown": str(Path(listenkit_root) / "cli" / "generate-markdown.sh"),
```

我实测 `resolve-listenkit` 在 Windows 上的实际返回：

```json
"generate_markdown": "C:\\Users\\jiezhengj\\Documents\\Project\\ListenKit\\cli\\generate-markdown.sh"
```

而 ListenKit 自己的集成契约（`adapters/agent/listenkit-agent-instructions.md:5-8`、`adapters/codex/SKILL.md:14`、`adapters/claude/CLAUDE.md:3`）全部明确规定：**原生 Windows 用 `.ps1`，`.sh` 仅用于 macOS/Linux/WSL**。

这不是「少了一个分支」，而是**主动把 Agent 引导到对方契约明令禁止的入口上**。`SKILL.md` 第 96 行又明确要求 *"Use only the returned `listenkit_root`... do not guess a path"*——我处于「照做就违约、不照做就违反本仓库指令」的两难。

附带问题：`listenkit_connections.py:329` 的 `is_usable_listenkit_root` 只校验 `.sh` 存在：

```python
return (root / "README.md").is_file() and (root / "cli" / "generate-markdown.sh").is_file()
```

它在 Windows 上同样会通过（真实 checkout 里 `.sh` 和 `.ps1` 都在），但它验证的是「一个可用 bash 入口」，而不是「一个当前平台可用的入口」。

**问题 3：preflight 是假绿灯**

`transcribe_listening.py:464-466`：

```python
def require_executable_file(path: Path, description: str) -> None:
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"{description} is missing or not executable: {path}")
```

`os.access(..., os.X_OK)` 在 Windows 上对任何存在的文件都返回 `True`。我实测对 `generate-markdown.sh` 返回 `True`。于是 `preflight_listenkit_generate_tooling()` 顺利通过，把失败推迟到 `subprocess.run` 才以 `[WinError 2]` 爆出。这条报错既不指出是哪个文件，也不说明是平台问题——对面向学习者的 Agent 不可转述。

**问题 4：这条坑比看起来更深——不能只改 `/bin/bash`**

直觉上把 `/bin/bash` 换成 `shutil.which("bash")` 就能修好，但我实测证明**那样只会把失败推迟到更隐蔽的地方**。因为 `.sh` 链路整条都是 macOS 形状（详见 ListenKit 侧报告）：

```
$ bash cli/check-runtime.sh
ListenKit runtime is missing: /c/Users/jiezhengj/Library/Caches/ListenKit/venvs/cpython-314/bin/python
Repair: .../cli/init-faster-whisper.sh
```

真实的 Windows 运行时在 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe` 且完全健康（我已实测 CUDA float16 转写），但 `.sh` 链路看不见它，会报「运行时缺失」并建议重新初始化——也就是在已有健康运行时的情况下，去重复下载构建第二套 CUDA 环境。所以修复必须是**平台感知地选择入口**（Windows 用 `.ps1`），而不是「让 bash 能被找到」。

### 2.3 P1：文档中的 `python3` 在本机是失败的 Store stub

本仓库文档（`docs/learner-agent-setup.md`、`docs/daily-runtime-update-design.md`、`docs/listenkit-installation-and-connections.md`、`docs/vault-initialization-and-runtime-connections.md`、`docs/installation-and-onboarding-design.md`）的命令示例全部写作：

```bash
python3 -m lingotrace.init connect-listenkit --listenkit-root ...
python3 -m lingotrace.init check-update ...
```

而本机 `python3` 是 Microsoft Store 别名 stub（`AppInstallerPythonRedirector.exe`），调用即失败（`python3 --version` → 无输出、exit 49）。**一个按文档逐字执行的 Agent 会直接失败，且看不到任何错误信息。** 相比之下，Vault 的 `AGENTS.md` 和 `SKILL.md` 都用 `python -m`，这是对的；问题只在文档示例。

同源的还有 `lingotrace/init/doctor.py:46`：

```python
python_command = which("python3") or which("python")
```

它优先 `which("python3")`，于是本机 doctor 把 python 依赖报告为：

```json
"python": {"path": "C:\\Users\\jiezhengj\\AppData\\Local\\Microsoft\\WindowsApps\\python3.EXE",
           "status": "found", "version": "3.14.4"}
```

路径是 Store stub，版本却取**当前运行解释器**的 3.14.4——报告内部不一致，且该 stub 不可执行。`doctor` 的「python 已就绪」结论在带 Store stub 的 Windows 机器上是假阳性。

### 2.4 P1：其他平台相关的误报与硬编码

**问题 5：Obsidian Desktop 检测缺 per-user 安装路径**

`doctor.py:231-234` 的 Windows 候选只检查 `%LOCALAPPDATA%\Obsidian\Obsidian.exe`、`%ProgramFiles%\Obsidian\Obsidian.exe`、`%ProgramFiles(x86)%\Obsidian\Obsidian.exe`，**缺少** `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`（Windows 安装器的 per-user 默认路径）。本机 Obsidian 就装在那里，我实测 `_find_obsidian('windows', ...)` 返回 `None`，doctor 因此报 `obsidian_desktop_not_found` 误报。

**问题 6：听力链路的 macOS 形状路径**

- `transcribe_listening.py:354` 与 `setup_offline_dictionary.py:21`：日语词典缓存默认 `Path.home() / "Library" / "Caches" / "jp-listening-dicts"`——macOS 形状，Windows 上会在 `C:\Users\<user>\Library\Caches\...` 建一个系统不认识、也不会清理的目录（有 `JP_LISTENING_DICT_DIR` 逃生口，但默认值错误）。
- `setup_offline_dictionary.py:161,207` 的 iCloud 路径防护（`"/Library/Mobile Documents/"`）在 Windows 上是死代码。

**问题 7：dual-ASR 默认契约在 Windows 上不可满足**

`transcribe_listening.py:1890`：副引擎默认选 `apple`（Apple Speech/MLX，macOS 专属）：

```python
compare_engine = "faster-whisper" if primary_engine == "apple" else "apple"
```

`SKILL.md` 要求「dual-ASR validation enabled by default for every listening note」。在 Windows 上这会优雅降级为 `secondary_unavailable`（不崩溃），但**双引擎校验这一能力在 Windows 上永远无法达成**，且按 SKILL 要求必须向用户报告「fallback caused by an unavailable secondary engine」——体验上永远带着一条降级告警。

**问题 8：`tools/vault-structure/validate_vault_structure.py:174` 硬编码 `zsh`**

```python
["zsh", "codex-skills/jp-survival-speaking-card-generator/scripts/validate-survival-speaking-cards.sh", run_date],
```

Windows Git Bash 只有 bash、没有 zsh。该调用被 `--run-integrations` 开关门控，故为 P1 而非 P0。

### 2.5 P2：`.claude/settings.local.json` 是 macOS + Codex 形状的本地文件

`.claude/settings.local.json`（被 `.gitignore` 忽略，未跟踪）的权限规则写满了 macOS/Codex 路径：

```json
"Read(//private/tmp/**)", "Read(//dev/**)",
"Bash(PYTHONPATH=/Users/jiezhengj/Documents/Project/LingoTrace python -c ...)",
"Bash(ls -la ~/.codex/skills/ ...)"
```

对在 Windows 上打开本仓库的 Claude Code 而言，这些规则静默失效（`//private/tmp`、`/Users/...` 在 Windows 上不匹配任何路径），而 `~/.codex/skills/` 是 Codex 的约定。净效果：作者本想授予的部分权限在 Windows 上不生效，且文件暴露了它是为 macOS + Codex 开发环境编写的。这是 Agent 框架兼容性问题，不是 Windows 故障——但它会在 Windows + Claude Code 用户身上造成「权限规则莫名不匹配」的困惑。

### 2.6 P2：解释器契约未定义

`AGENTS.md` 与 `SKILL.md` 都写作 `python -m lingotrace.init ...`，但未定义 `python` 如何解析。本机同一条命令在 Git Bash 与 PowerShell 下可能落到不同解释器（本机因 `python`=3.14.4 恰好一致）。对照 ListenKit 的 `cli/listenkit.ps1` 有显式候选顺序与 `>=3.10` 校验，这是更稳妥的做法。

---

## 三、我的需求

按优先级排列，说明我需要什么才能在这台 Windows 设备上完整履行 `SKILL.md` 规定的职责：

1. **一条在原生 Windows 上真正可执行的听力链路。** 目前我可以完成来源笔记、复习卡、口语卡、复习结算的全部能力，唯独「请把这段音频做成精听稿」这类请求我必须直接告诉用户做不了——而这是 `SKILL.md` 列在最前面的意图族之一。
2. **`resolve-listenkit` 返回当前平台正确的入口。** 我遵循「以运行时返回值为准、不自行猜路径」的原则（`SKILL.md` 第 96 行的明确要求）。既然要求我不猜，返回值就必须是当前平台可用的那个。现在返回的 `.sh` 是对方契约禁止的入口，我处于两难。
3. **失败时给我可转述的诊断。** 我面对的是学习者，不是开发者。我需要「当前平台缺少 X，请执行 Y」这种可直接翻译成中文告诉用户的信息，而不是 `[WinError 2]`。
4. **文档示例使用可执行的 `python`，并明确定义解释器契约。** 现在文档里的 `python3` 在本机是失败 stub，逐字照做会死。
5. **（可选）承认 Claude Code 这一接入方式。** 我通过 Vault 的 `AGENTS.md` 接入，不依赖 `.claude/`。这条路径目前是通的，无需改代码；如果文档能提及「任意遵循 AGENTS.md 的 Agent 均可接入」，会减少后续 Agent 的试探成本。

---

## 四、我的建议方案

### 方案 A（推荐）：平台感知地选择 ListenKit 入口

在 `transcribe_listening.py` 中引入统一的入口解析，`.ps1` 与 `.sh` 各归其位：

```python
import platform, shutil

def listenkit_generate_markdown_invocation() -> list[str]:
    """返回可直接传给 subprocess 的完整命令前缀。"""
    root = listenkit_root()
    if platform.system() == "Windows":
        script = root / "cli" / "generate-markdown.ps1"
        if not script.is_file():
            raise RuntimeError(f"ListenKit Windows entrypoint not found: {script}")
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh is None:
            raise RuntimeError("PowerShell is required to run ListenKit on Windows.")
        return [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    script = root / "cli" / "generate-markdown.sh"
    if not script.is_file():
        raise RuntimeError(f"ListenKit POSIX entrypoint not found: {script}")
    bash = shutil.which("bash") or "/bin/bash"
    return [bash, str(script)]
```

调用点相应改为 `command = [*listenkit_generate_markdown_invocation(), f"--{source_kind}", ...]`，删除硬编码的 `"/bin/bash"`。

同步修改：

- `transcribe_listening.py:451` 的 `configure_project_roots` 校验，改为「`.sh` 与 `.ps1` 任一存在即视为有效 ListenKit」；
- `listenkit_connections.py:329` 的 `is_usable_listenkit_root` 同上；
- `listenkit_connections.py:341` 返回的 `generate_markdown` 改为按当前平台给出对应入口，让我拿到即可用的路径。

补充说明：`-ExecutionPolicy Bypass` 用于避免用户机器的执行策略导致脚本被拒；若项目倾向更保守，可改为先探测策略再决定是否附加该参数。我在本机已实测：`powershell -NoProfile -ExecutionPolicy Bypass -File ./cli/generate-markdown.ps1 ...` 端到端转写成功（详见附录实测记录）。

### 方案 B（过渡，已实测可用）：为 `.sh` 链路注入 Windows 运行时环境变量

如果不便立刻改动入口解析逻辑，可以走这条已被我验证的路：ListenKit 的 `transcribe-audio.sh` 支持 `LISTENKIT_FASTER_WHISPER_VENV_DIR` 与 `LISTENKIT_FASTER_WHISPER_VENV_PYTHON` 覆盖。我的实测：

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR="C:/Users/jiezhengj/AppData/Local/ListenKit/venvs/cpython-314" \
LISTENKIT_FASTER_WHISPER_VENV_PYTHON="C:/Users/jiezhengj/AppData/Local/ListenKit/venvs/cpython-314/Scripts/python.exe" \
bash cli/transcribe-audio.sh --audio-path probe.wav --locale en --engine faster-whisper --output probe.json
```

产出 JSON 确认：`engine=faster-whisper, device=cuda, compute_type=float16, model=small`。**即 `.sh` 链路在 Windows 上可以跑通，只要把 macOS 默认路径覆盖掉。**

因此过渡方案为：`/bin/bash` 改为 `shutil.which("bash")`，并在 Windows 分支下向 `env` 注入上述两个变量（取值可由 ListenKit `doctor` 输出解析）。但注意 `cli/check-runtime.sh` 没有同名环境变量逃生口（其第 6 行是无条件硬编码），所以方案 B 只覆盖转写、不覆盖运行时体检。方案 B 适合止血，方案 A 才是终局。

### 方案 C：修复 preflight 的平台语义

```python
def require_executable_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"{description} is missing: {path}")
    # Windows 上 os.access(X_OK) 对任何存在的文件恒为 True，检查它没有意义
    if platform.system() != "Windows" and not os.access(path, os.X_OK):
        raise RuntimeError(f"{description} is not executable: {path}")
```

并在 `preflight_listenkit_generate_tooling()` 中提前校验「当前平台所需的宿主程序（bash 或 powershell）是否存在」，让失败在 preflight 阶段以可读信息暴露，而不是留到 `subprocess` 抛 `WinError 2`。

### 方案 D：文档与 doctor 的解释器契约

1. 把文档示例中的 `python3` 统一改为 `python`（或给出解析顺序）。本机 `python3` 是 Store stub 的场景在 Windows 上非常普遍。
2. `doctor.py:46` 改为 `which("python") or which("python3")`（真实 Python 优先，Store stub 兜底），或在 Windows 分支下直接排除 `WindowsApps` 目录下的别名 stub。
3. 在 `AGENTS.md` 与 `docs/learner-agent-setup.md` 中补一节明确：最低 Python 版本、解析顺序（建议对齐 ListenKit：`LINGOTRACE_CLI_PYTHON` → `py -3.14` → `python3.14` → `python`）、Windows 上 Store stub 的坑。

### 方案 E：其他平台修正

1. Obsidian 检测增加 `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`（per-user 安装器默认路径）。
2. 日语词典缓存默认路径改为平台感知（Windows 用 `%LOCALAPPDATA%`）。
3. `--compare-engine auto` 在非 macOS 平台默认落到 `faster-whisper` 双通道（如 Intel/GPU 与 CPU 的第二次 faster-whisper 对比），避免「默认契约必然降级」。

### 建议的验证方式

改动后，在原生 Windows 上按以下顺序验证：

1. `python -m lingotrace.init resolve-listenkit --vault <vault>` → `generate_markdown` 应指向 `.ps1`；
2. 用一段 2 秒测试音频跑通完整听力链路，确认 `device=cuda`；
3. 故意把 ListenKit 路径指向不存在的目录，确认报错是「当前平台缺少 X」而不是 `WinError 2`；
4. 在 macOS 上回归，确认 `.sh` 分支未被破坏。

---

## 五、文档落位说明

本文件放在 `docs/agent-compatibility-report/` 下，符合 `tools/git/check-public-staged-files.sh` 的公共白名单（`docs/` 在允许列表内），不会导致提交校验失败。

我没有修改本仓库的任何代码，没有创建分支，也没有执行提交。按 `AGENTS.md` 的 Git 工作流，`main` 是受保护分支，任何改动都应经由 topic branch 与 pull request；本报告仅作为问题记录留存，是否采纳与如何实施由维护者决定。

本次检查中我的唯一写入是运行 `python -m lingotrace.init check-update`——它按设计返回 `already_checked_today`（当天已检查），未触碰任何文件；工作区除本报告文件与既有的 `docs/agent-compatibility-report/` 未跟踪目录外保持干净。

---

## 六、附录

### 6.1 实测记录（本次真实执行）

| 命令 | 结果 |
| --- | --- |
| `python -m lingotrace.init resolve-runtime` | ✅ `accepted: true`，SKILL 路径解析正确 |
| `python -m lingotrace.init doctor` | ✅ `exit_code: 0`，仅 `obsidian_desktop_not_found` 误报（见 2.4 问题 5） |
| `python -m lingotrace.init resolve-listenkit` | ⚠️ 返回 `.sh` 入口（见 2.2 问题 2） |
| `python -m lingotrace.init check-update` | ✅ `already_checked_today`，无写入 |
| 英语包 `review_rollover(mode="preview")` | ✅ `accepted: true`，`errors: []` |
| 直接调用 `invoke_listenkit(...)` | ❌ `FileNotFoundError [WinError 2]`（`/bin/bash` 硬编码） |
| `preflight_listenkit_generate_tooling()` | ⚠️ 假绿灯通过（`os.access(X_OK)` 对 `.sh` 返回 True） |
| ListenKit `.\cli\generate-markdown.ps1` 端到端转写 | ✅ `EXIT=0`，`faster-whisper / cuda / float16`，产出 `.md`+`.json` |
| ListenKit `.sh` 链路（注入 Windows 运行时变量后） | ✅ 真实 CUDA 转写成功（见方案 B） |

### 6.2 代码审计范围（Windows 兼容性）

对 `lingotrace/`、`tools/`、`tests/` 下全部 `.py` 做了模式扫描：生产代码中**没有** `shell=True`、`os.system`、`os.chmod`/`os.symlink`/`os.fork`/`resource`/`fcntl`/`pwd`/`grp`；所有路径 join 走 pathlib；所有文本读写显式 `encoding="utf-8"`。发现的问题集中在听力工具链（`tools/listening-transcribe-official/`、`tools/vault-structure/`）与两处 init 模块，均已列入正文。

### 6.3 Agent 兼容性专项（Codex → Claude Code）

两个运行时原本面向 **Codex** 开发。对我（Claude Code）而言：

- **能力轴差异**：与 WorkBuddy（沙箱无法读取 PowerShell stdout）不同，**我的 Bash 工具可以执行 `.ps1` 并完整读取其 stdout**（已实测）。因此 ListenKit 官方 Windows 入口 `.ps1` 对我完全可用——这一断点在「WorkBuddy vs Codex」上成立，但在「Claude Code vs Codex」上**不成立**。
- 因此对 Claude Code 来说，真正的断点只有一个：**LingoTrace 编排层在 Windows 上返回/调用错误的入口**（`resolve-listenkit` 返回 `.sh`、`transcribe_listening.py` 硬编码 `/bin/bash`）。修好这两处，Claude Code 即可端到端跑通精听链路。
- 文档示例 `python3` 是 Windows + 任意 Agent 的通用陷阱（本机为 Store stub）。
- `.claude/settings.local.json` 是 Claude Code 专属文件却写满 macOS/Codex 路径（见 2.5）。
- 现有报告已覆盖 WorkBuddy / TraeWork / QwenWork 三种环境的结论；本报告的环境（Git Bash + 可调用 PowerShell + 有 pwsh）与三份都不同，且我的实测结论是：**对 Claude Code 而言，问题收敛为「上游入口选择」与「文档示例」两处，无需为 Claude Code 新增适配层**。
