# Agent 运行兼容性报告：原生 Windows（LingoTrace 侧）

- 报告日期：2026-08-10
- 报告范围：LingoTrace 运行时在原生 Windows 上的可执行性，以及对「WorkBuddy Agent」（非原定目标 Codex）的兼容性
- 关联报告：`ListenKit/docs/agent-compatibility-report/workbuddy-agent-windows-compatibility.md`

---

## 一、我是谁

**一句话身份：我是运行在 Windows（win32）操作系统之上的「WorkBuddy」Agent 框架中的 AI 助手。**

- **Agent 框架 / 产品**：WorkBuddy —— 一个带工具调用的 LLM Agent 平台。我以「Agent Loop」方式运行：每轮观察上下文、选择工具、执行动作、回收结果并迭代，直至任务完成。框架为我提供 Bash、PowerShell、文件系统读写、MCP 连接器等工具，工作模式为 Craft（直接执行：读文件、跑命令、写产物）。
- **宿主操作系统**：Windows（系统内部标识 `win32`，本机为 Windows 11，AMD64）。我的命令执行入口是 Git Bash（MinGW64，由 WorkBuddy 托管），独立的 PowerShell 工具也由框架提供。
- **与运行时的关系**：本仓库的 `AGENTS.md` / `SKILL.md` 是写给我这类 Agent 消费的，我通过 Vault 配置接入，不依赖 `.claude/` 适配层。

在这台设备上，我承担 LingoTrace 学习 Vault 的日常执行角色：

- 我的入口是 Vault 根目录的 `AGENTS.md`，按其要求解析 `.lingotrace/vault-context.json`、`.lingotrace/paths.json` 与 `.lingotrace/runtime-connections/windows.json`；
- 随后我读取本运行时的 `lingotrace/packs/english/agent_skills/SKILL.md`，把用户的自然语言学习请求映射到英语包能力上。

也就是说，本仓库的 `SKILL.md` 是写给我这类 Agent 执行的，我是它的实际消费方。

我与既有适配器的差异需要说明：本仓库带有 `.claude/`，ListenKit 带有 `adapters/{claude,codex,cursor}`，但没有针对 WorkBuddy 的适配层。我通过 Vault 的 `AGENTS.md` 接入，不依赖 `.claude/`。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | Windows 11（10.0.26220），AMD64 |
| 默认 Shell | Git Bash（`/usr/bin/bash`，MinGW64） |
| Bash 中的 `python` | 3.13.14（WorkBuddy 托管解释器） |
| PowerShell 中的 `python` | 3.14.4（`AppData\Local\Programs\Python\Python314`） |
| `py` 启动器 | **不存在**（`Get-Command py` 返回空） |
| PowerShell | Windows PowerShell 5.1.26100.9022 |
| 本仓库 Git 状态 | `main` 分支，工作区干净，`origin` 为个人 fork、`upstream` 为官方 |

---

## 二、问题是什么

我把本运行时的能力拆成两块分别实测。**非听力链路全部健康，听力链路在原生 Windows 上完全不可执行。**

### 2.1 已验证可正常工作的部分

以下均在 Git Bash + Python 3.13.14 下实测通过：

| 能力 | 结果 |
| --- | --- |
| `python -m lingotrace.init resolve-runtime` | `accepted: true`，正确解析出运行时与 SKILL 路径 |
| `python -m lingotrace.init doctor --language english` | `exit_code: 0`，仅一条 `obsidian_desktop_not_found` 可选告警 |
| `python -m lingotrace.init resolve-listenkit` | `accepted: true`，解析出 ListenKit 根目录 |
| `python -m lingotrace.init check-update` | `status: fork_up_to_date`，fork 识别正确，未触碰工作区 |
| `lingotrace.packs.english.workflows.review_rollover(mode="preview")` | `accepted: true`，`errors: []`，核心写守卫工作正常 |
| `bash tools/git/check-public-staged-files.sh` | 正常执行并通过 |

结论：**core、english pack、init CLI、公共校验脚本在 Windows 上没有兼容性问题。**

### 2.2 P0：听力链路在原生 Windows 上必然失败

`SKILL.md` 的「Listening Notes」是本运行时最核心的日常能力之一，它在原生 Windows 上 100% 失败。

**根因 1：硬编码 `/bin/bash` 绝对路径**

`tools/listening-transcribe-official/transcribe_listening.py:645-658`：

```python
command = [
    "/bin/bash",
    str(script_path),
    ...
]
```

原生 Windows 上不存在 `/bin/bash` 这个可被 Win32 `CreateProcess` 解析的路径。我的实测复现：

```
EXCEPTION: FileNotFoundError [WinError 2] 系统找不到指定的文件。
```

注意：设备上 **bash 是存在的**（Git Bash 位于 `C:\Users\jiezhengj\.workbuddy\vendor\PortableGit\bin\bash.exe`，且 `shutil.which("bash")` 可以找到）。失败的唯一原因是这里写死了 POSIX 绝对路径，而不是做解释器发现。

**根因 2：跨运行时契约违背——在 Windows 上仍指向 `.sh`**

以下四处把 ListenKit 入口硬编码为 `.sh`，没有任何平台分支：

- `tools/listening-transcribe-official/transcribe_listening.py:451`（校验）
- `tools/listening-transcribe-official/transcribe_listening.py:457`（路径构造）
- `lingotrace/init/listenkit_connections.py:329`（有效性判定）
- `lingotrace/init/listenkit_connections.py:341`（返回给 Agent 的 `generate_markdown` 工件）

而 ListenKit 自己的 `LLM_INTEGRATION.md` 明确规定：

> Use `.sh` on macOS/Linux/WSL and `.ps1` on native Windows. Do not route native Windows through WSL.

我实测 `resolve-listenkit` 在 Windows 上的实际返回：

```json
"generate_markdown": "C:\\Users\\jiezhengj\\Documents\\Project\\ListenKit\\cli\\generate-markdown.sh"
```

这不只是「少了一个分支」——它是**主动把我这个 Agent 引导到了对方契约明令禁止的入口上**。我如果照做，就违反了 ListenKit 的集成契约。

**根因 3：这个坑比看起来更深——不能只改 `/bin/bash`**

这是我最想强调的一点。直觉上把 `/bin/bash` 换成 `shutil.which("bash")` 就能修好，但我实测证明**那样只会把失败推迟到更隐蔽的地方**：

Git Bash 下 `cli/generate-markdown.sh --help` 是能正常输出的，看起来一切正常。但继续往下走：

```
$ bash cli/check-runtime.sh
ListenKit runtime is missing: /c/Users/jiezhengj/Library/Caches/ListenKit/venvs/cpython-314/bin/python
Repair: .../cli/init-faster-whisper.sh
```

`.sh` 链路整条都是 macOS 形状（详见 ListenKit 侧报告）。真实的 Windows 运行时在 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe` 且**完全健康**（CUDA float16、faster-whisper 1.2.1），但 `.sh` 链路看不见它，会报「运行时缺失」并建议重新初始化——也就是在已有健康运行时的情况下，去重复下载构建第二套 CUDA 环境。

所以修复必须是「平台感知地选择入口」，而不是「让 bash 能被找到」。

### 2.3 P1：Windows 上的 preflight 是假绿灯

`transcribe_listening.py:464-466`：

```python
def require_executable_file(path: Path, description: str) -> None:
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"{description} is missing or not executable: {path}")
```

`os.access(..., os.X_OK)` 在 Windows 上对任何存在的文件都返回 `True`（我实测对 `generate-markdown.sh` 返回 `True`）。于是 `preflight_listenkit_generate_tooling()` 会顺利通过，把失败推迟到 `subprocess.run` 才以 `[WinError 2] 系统找不到指定的文件` 的形式爆出来。

对我的实际影响：这条报错既没有指出是哪个文件、也没有说明是平台问题。如果不是我逐行读了源码，我只能向用户转述一句无从下手的系统错误。**preflight 的价值就是提前给出可行动的诊断，这里它没有做到。**

### 2.4 P2：`python` 解释器归属不确定

`AGENTS.md` 与 `SKILL.md` 都写作 `python -m lingotrace.init ...`，但未定义 `python` 如何解析。本机同一条命令：

- 在 Git Bash 中 → 3.13.14（托管解释器）
- 在 PowerShell 中 → 3.14.4（系统解释器）

本仓库的 `__pycache__` 是 `cpython-314`，说明历史上是用 3.14 跑的。目前两者都能跑通（我已用 3.13.14 验证全部非听力链路），所以这不是故障，但它是**不确定性**：不同 Agent、不同 shell 会落到不同解释器上，一旦将来引入版本相关行为就会变成难以复现的问题。

对照之下，ListenKit 的 `cli/listenkit.ps1` 显式定义了候选顺序（`LISTENKIT_CLI_PYTHON` → `py -3.14` → `python3.14` → `python`）并校验 `>= 3.10`，这是更稳妥的做法。

---

## 三、我的需求

按优先级排列，说明我需要什么才能在这台 Windows 设备上完整履行 `SKILL.md` 规定的职责：

1. **一条在原生 Windows 上真正可执行的听力链路。** 目前我可以完成复习卡、口语卡、来源笔记、复习结算的全部能力，唯独「请把这段音频做成精听稿」这类请求我必须直接告诉用户做不了。这是 `SKILL.md` 列在最前面的意图族之一。

2. **`resolve-listenkit` 返回当前平台正确的入口。** 我遵循「以运行时返回值为准、不自行猜路径」的原则（这也是 `SKILL.md` 第 96 行的明确要求：*"Use only the returned `listenkit_root`... do not guess a path"*）。既然要求我不猜，那么返回值就必须是当前平台可用的那个。现在它返回的 `.sh` 是对方契约禁止的入口，我处于「照做就违约、不照做就违反本仓库指令」的两难。

3. **失败时给我可转述的诊断。** 我面对的是学习者，不是开发者。我需要的是「当前平台缺少 X，请执行 Y」这种可以直接翻译成中文告诉用户的信息，而不是 `[WinError 2]`。

4. **明确的解释器契约。** 请在文档中写清 `python` 的解析顺序与最低版本，让我在任何 shell 下都能落到同一个解释器。

5. **（可选）承认 WorkBuddy 这一接入方式。** 我不通过 `.claude/` 接入，而是通过 Vault 的 `AGENTS.md`。目前这条路径是通的，无需改代码，但如果文档能提及「任意遵循 AGENTS.md 的 Agent 均可接入」，会减少后续 Agent 的试探成本。

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
            raise RuntimeError(
                "PowerShell is required to run ListenKit on Windows. "
                "Install PowerShell or set LISTENKIT_ENTRYPOINT explicitly."
            )
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
- `listenkit_connections.py:329` 的 `_is_valid_listenkit_root` 同上；
- `listenkit_connections.py:341` 返回的 `generate_markdown` 改为按当前平台给出对应入口，让我拿到即可用的路径。

补充说明：`-ExecutionPolicy Bypass` 用于避免用户机器的执行策略导致脚本被拒；若项目倾向更保守，可改为先探测策略再决定是否附加该参数。

### 方案 B（过渡，已实测可用）：为 `.sh` 链路注入 Windows 运行时环境变量

如果不便立刻改动入口解析逻辑，可以走这条已被我验证的路：ListenKit 的 `transcribe-audio.sh` 支持 `LISTENKIT_FASTER_WHISPER_VENV_DIR` 与 `LISTENKIT_FASTER_WHISPER_VENV_PYTHON` 覆盖。

我的实测记录：

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR=".../AppData/Local/ListenKit/venvs/cpython-314" \
LISTENKIT_FASTER_WHISPER_VENV_PYTHON=".../Scripts/python.exe" \
bash cli/transcribe-audio.sh --audio-path probe.wav --locale en \
     --engine faster-whisper --output probe.json
```

产出 JSON 确认：`engine=faster-whisper, device=cuda, compute_type=float16, model=small`。**即 `.sh` 链路在 Windows 上是可以跑通的，只要把 macOS 默认路径覆盖掉。**

因此过渡方案为：`/bin/bash` 改为 `shutil.which("bash")`，并在 Windows 分支下向 `env` 注入上述两个变量（取值可由 ListenKit 的 `doctor` 输出解析得到）。

但请注意方案 B 的局限：`cli/check-runtime.sh` **没有**提供同名环境变量逃生口（其第 6 行是无条件硬编码），所以这条路只覆盖转写，不覆盖运行时体检。方案 B 适合作为止血，方案 A 才是终局。

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

### 方案 D：文档层面固化解释器契约

建议在 `AGENTS.md` 与 `docs/learner-agent-setup.md` 中补一节，明确：

- 最低 Python 版本；
- 解析顺序，建议对齐 ListenKit：`LINGOTRACE_CLI_PYTHON` → `py -3.14` → `python3.14` → `python`；
- 说明在 Windows 上 Git Bash 与 PowerShell 的 `python` 可能不同，建议显式设置 `LINGOTRACE_CLI_PYTHON`。

### 建议的验证方式

改动后，在原生 Windows 上按以下顺序验证：

1. `python -m lingotrace.init resolve-listenkit --vault <vault>` → `generate_markdown` 应指向 `.ps1`；
2. 用一段 2 秒测试音频跑通完整听力链路，确认 `device=cuda`；
3. 故意把 ListenKit 路径指向不存在的目录，确认报错是「当前平台缺少 X」而不是 `WinError 2`；
4. 在 macOS 上回归，确认 `.sh` 分支未被破坏。

---

## 五、文档落位说明

本文件放在 `docs/` 下，符合 `tools/git/check-public-staged-files.sh` 的公共白名单（`docs/` 在允许列表内），不会导致提交校验失败。

我没有修改本仓库的任何代码，没有创建分支，也没有执行提交。按 `AGENTS.md` 的 Git 工作流，`main` 是受保护分支，任何改动都应经由 topic branch 与 pull request；本报告仅作为问题记录留存，是否采纳与如何实施由维护者决定。

本次检查中我执行的唯一写入是 `python -m lingotrace.init check-update`，它按设计更新了 Vault 内的 `.lingotrace/runtime-update-checks/windows.json` 日检状态标记，未触碰本仓库。

---

## 六、附录：WorkBuddy Agent 兼容性专项（相对原定目标 Codex 的对照）

> 本节把上一版嵌在「Windows 兼容性」里的 Agent 维度单独成轴。两个运行时原本是为 **Codex** 开发的（证据见下），而我实际是 **WorkBuddy** Agent。操作系统兼容性与 Agent 框架兼容性是两个独立轴，不能混为一谈。

### 6.1 为什么需要这一节

两个运行时的目标 Agent 是 Codex，而非通用 Agent：

- ListenKit 仓库含 `adapters/codex/`（`SKILL.md` + `agents/openai.yaml`）、`adapters/claude/`、`adapters/cursor/`，以及通用 `adapters/agent/listenkit-agent-instructions.md`；
- LingoTrace 仓库含 `.claude/`（`settings.local.json`）与 `agent-skills/`（`listening-script-generator`、`next-day-review-updater`）；
- 我本次核对：`adapters/codex/SKILL.md` 与 `adapters/agent/listenkit-agent-instructions.md` 的**行为契约完全一致**（都是「Windows 用 `.ps1`、macOS/Linux/WSL 用 `.sh`」），区别只在**打包格式**（`openai.yaml` 是 Codex 的技能描述格式）。因此没有"Codex 专用逻辑"被我漏掉；但"面向 Codex 的隐含前提"确实存在，且对我（WorkBuddy）不成立。

### 6.2 双轴定义

- **轴一 · 操作系统兼容性（Windows vs macOS/Linux）**：路径分隔符、shell 解释器（bash vs pwsh）、平台专用入口（`.sh` vs `.ps1`）。本报告 §二已覆盖。
- **轴二 · Agent 框架兼容性（Codex 假设 vs WorkBuddy 实际）**：运行时对「调用方是一个能自由跑 shell 并捕获其子进程 stdout 的 Agent」这一隐含前提是否成立。这层与操作系统无关，却是本报告最容易被误读成"只是 Windows 问题"的地方。

### 6.3 对照表：Codex 能力假设 → WorkBuddy 实际限制

| # | Codex（原定目标）的能力假设 | WorkBuddy（实际调用方）的限制 | 对调用的影响 | 本报告位置 |
| --- | --- | --- | --- | --- |
| 1 | Agent 可自由执行 shell，包括从 bash 调用 PowerShell | 我的 Bash 工具**拒绝从 Bash 调用 PowerShell**（安全拦截） | ListenKit 唯一官方 Windows 入口 `.ps1` 对我「能触发但读不到结果」 | ListenKit 报告 §2.3 |
| 2 | Agent 能捕获子进程 stdout | 我的 PowerShell 工具在本机返回**空 stdout**，需 `Out-File` 落盘再读 | `generate-markdown` 的执行结论（status/device/fallback）无法直接转述给用户 | ListenKit 报告 §2.3 |
| 3 | Agent 通过适配层（`.claude/` 或 `adapters/codex`）接入 | 我走 Vault 的 `AGENTS.md`，**无专属适配层** | 接入通路可用，但契约文档未承认「任意遵循 AGENTS.md 的通用 Agent」这一路径 | 本报告 §一 |
| 4 | `resolve-listenkit` 返回的入口对当前 Agent 可用 | 它返回 `.sh`，而 ListenKit 契约禁止原生 Windows 走 `.sh` | 编排 Agent 落入「照做即违约 / 不照做即违反本仓指令」的两难 | 本报告 §2.2 根因 2 |
| 5 | 单一解释器约定（`python -m ...`） | Git Bash 下 `python`=3.13.14、PowerShell 下 `python`=3.14.4，且无 `py` 启动器 | 跨 shell 解释器归属不确定，未来易引入难复现的版本问题 | 本报告 §2.4 |

### 6.4 关键洞见：真正断点不在"Windows vs macOS"，而在"Codex 的 shell/stdout 能力 vs WorkBuddy 的沙箱约束"

即使上游把 Windows 路径全部修好，只要运行时仍要求调用方**直接执行 `.ps1` 并读取其 stdout**，我在原生 Windows 上依旧受阻——因为第 1、2 行的限制与 Windows 无关，只与"我是 WorkBuddy"有关。

因此，让运行时对"任意 Agent 框架"而非仅 Codex 鲁棒的关键设计是：**所有面向 Agent 的入口都提供 `--report-json <path>` 落盘能力**（见 ListenKit 报告方案 C）。读文件是普适能力，捕获子进程 stdout 不是。这比"支持更多 shell"更治本。

### 6.5 诚实缺口（未演示项）

本报告**真实执行了运行时各组件**——含 LingoTrace 的 `lingotrace.init` 四个子命令、英语包 `review_rollover` 的 `preview`、以及 ListenKit 的一次**真实 GPU 转写**（`device=cuda, compute_type=float16`）。但**没有演示一条从 LingoTrace 编排层直达 ListenKit 的端到端精听链路**：`transcribe_listening.py:645` 硬编码 `/bin/bash`，在原生 Windows 上先于 ListenKit 就抛 `WinError 2`，到不了 ListenKit。

该 happy path 的"绿色演示"依赖上游先修复（本报告 §四 方案 A / 方案 B）。此缺口**不影响"各组件可独立运行"的结论**，但意味着"全链路开箱即用"尚未被本 Agent 验证。我未在源码上打补丁去强行演示。

### 6.6 给维护者的补充建议（在 §四 之上）

若希望运行时对 Codex 之外的 Agent 也鲁棒：

1. 所有面向 Agent 的入口都提供 `--report-json` 落盘（不只转写内容，含本次执行的 `status` / `fallback` 诊断）；
2. 在 `AGENTS.md` / `LLM_INTEGRATION.md` 显式列出"支持的 Agent 接入方式"，承认「任意遵循 AGENTS.md 的通用 Agent」这一路径，减少后续 Agent 的试探成本；
3. 入口选择交给运行时按平台返回（平台感知），而非让 Agent 自行判断 `.sh` 还是 `.ps1`。
