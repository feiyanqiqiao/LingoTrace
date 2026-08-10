# Agent 运行兼容性报告：macOS（LingoTrace 侧）

- 报告日期：2026-08-10
- 报告范围：LingoTrace 运行时在 macOS（Apple Silicon）上的可执行性，以及对「Claude Code Agent」（非原定目标 Codex）的兼容性
- 报告者：Claude Code（Anthropic 的 Agent CLI），运行于 macOS 27.0（arm64），shell 为 zsh
- 关联报告：`ListenKit/docs/agent-compatibility-report/claude-code-agent-macos-compatibility.md`
- 用户给出的目标目录是 Windows 风格 `C:\Users\...\LingoTrace\docs\agent-compatibility-report`；本机为 macOS，等价路径为 `~/Documents/Project/LingoTrace/docs/agent-compatibility-report/`

---

## 一、我是谁

**一句话身份：我是运行在 macOS（darwin，arm64 / Apple Silicon）操作系统之上的「Claude Code」Agent 框架中的 AI 助手，是 LingoTrace 学习 Vault 的日常执行 Agent 之一，也是本仓库 `SKILL.md` / `AGENTS.md` 的实际消费方。**

- **Agent 框架 / 产品**：Claude Code —— Anthropic 官方的命令行 Agent CLI（终端/桌面/IDE 均可运行）。我以「Agent Loop」方式运行：每轮读取指令与工具结果、选择工具、执行、回收输出并迭代。框架为我提供 Bash（zsh）、文件系统读写、Grep/Glob 检索、Web 检索等工具；我的 Bash 工具可以完整读取子进程 stdout/stderr。
- **宿主操作系统**：macOS 27.0（Build 26A5388g），`uname -m` = arm64（Apple Silicon）。命令执行入口是 zsh（macOS 默认 shell）。系统自带 `/bin/bash` 为 GNU bash 3.2.57（2007 年旧版），`/bin/zsh` 为默认。
- **与运行时的关系**：我通过 Vault 根的 `AGENTS.md` 接入：解析 `.lingotrace/vault-context.json`、`.lingotrace/paths.json` 与 `.lingotrace/runtime-connections/macos.json`，读取本运行时 `lingotrace/packs/english/agent_skills/SKILL.md`，把用户的自然语言学习请求映射到英语包能力上。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | macOS 27.0（26A5388g），arm64（Apple Silicon） |
| 默认 Shell | `/bin/zsh`（macOS 默认） |
| 系统 bash | `/bin/bash` = GNU bash 3.2.57 |
| `python3` | 3.14.4（`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`） |
| `/usr/bin/python3` | **Python 3.9.6**（macOS CLT 自带）—— 与 PATH 中 3.14 并存 |
| brew | Homebrew 6.0.15，位于 `/opt/homebrew`（Apple Silicon 路径） |
| ffmpeg / ffprobe / yt-dlp | 均在 `/opt/homebrew/bin/` |
| Obsidian Desktop | `/Applications/Obsidian.app` 存在 |
| ListenKit 托管运行时 | `~/Library/Caches/ListenKit/venvs/cpython-314`，健康（faster-whisper 1.2.1、mlx 0.32.0 / Metal 就绪） |
| LingoTrace Git 状态 | `main` 分支；`origin` 为个人 fork、`upstream` 为官方（`feiyanqiqiao/LingoTrace`）；工作区有一处已删除的 `tests/lingotrace/__init__.py` 与未跟踪的 `docs/agent-compatibility-report/` |

---

## 二、问题是什么

我把本运行时的能力拆成「非听力链路」与「听力链路」两块，分别做了代码审计与真实运行验证。

**结论先行：非听力链路（init CLI、core、英语包、公共校验脚本）在 macOS 上全部健康；听力链路在 macOS 上端到端可用（我实测跑通了转写与写入）。macOS 上没有「必然失败」的代码缺陷（P0=无），但存在两处影响「全新 macOS 机器首次使用」的 P1 级引导/版本问题，以及若干 P2 级体验与跨平台声明问题。对 Claude Code 而言，运行时契约（`python -m lingotrace.init ...` + JSON 报告）完全可执行，无需新增适配层。**

### 2.1 已验证可正常工作的部分（实测通过）

| 能力 | 结果 |
| --- | --- |
| `import lingotrace` | ✅ 正常 |
| `python -m lingotrace.init resolve-runtime --vault <vault>` | ✅ `accepted: true`，正确解析 `macos.json` 并返回英语包 SKILL 路径 |
| `python -m lingotrace.init doctor --language english ...` | ✅ `exit_code: 0`，所有依赖 `found`（含 `/Applications/Obsidian.app`、`/opt/homebrew/bin/gh`、ListenKit、Python 3.14.4），`platform: macos` |
| `python -m lingotrace.init resolve-listenkit --vault <vault>` | ✅ `accepted: true`，返回 `.sh` 入口（**macOS 上这是正确入口**，与 ListenKit 契约一致；对照 Windows 侧此处在返回 `.ps1` 上存在缺陷） |
| `python -m lingotrace.init check-update ...`（临时 Vault） | ✅ `fork_up_to_date`，正确识别 fork 且不触碰工作区，只写 `.lingotrace/runtime-update-checks/macos.json` |
| 测试套件 `PYTHONPATH=. python -m unittest discover -s tests/lingotrace` | ✅ **244 / 244 通过** |
| `tools/architecture-baseline/tests`（unittest） | ✅ 42 / 42 通过 |
| `tools/listening-transcribe-official/tests`（unittest） | ✅ 100 / 100 通过 |
| 听力链路 `transcribe_listening.py ... --dry-run`（MLX 转写） | ✅ `status: complete`，识别稿预览通过 core write guard，`mlx-whisper` 引擎 |
| 听力链路 `... --apply`（写入临时 Vault） | ✅ `apply.accepted: true`，4 个文件（3 artifacts + 识别稿）正确落盘 |

### 2.2 P1：影响全新 macOS 机器首次使用的引导/版本问题

**问题 1：听力链自举脚本不在公开仓库内，全新 macOS 机器无法自举**

`tools/listening-transcribe-official/setup_offline_dictionary.py:12,157,200`：

```python
EXPECTED_PYTHON = (3, 14)
...
if runtime_python_version(runtime) != EXPECTED_PYTHON or not runtime.get("in_venv"):
    print("Refusing to install outside a Python 3.14 virtual environment. "
          "Run codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh.", ...)
```

`tools/listening-transcribe-official/transcribe_listening.py:271`：

```python
init_script = vault_root / "codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh"
```

`codex-skills/` 在本仓库中被 `.gitignore` 忽略，公开 clone 里不存在该目录。即：听力链要求「恰好 Python 3.14 的 venv」，但创建该 venv 的引导脚本不在公开仓库内。**当前这台开发机上可用**（venv 已预先建好，见 `tools/architecture-baseline/runtime-snapshot-lingotrace-python314.txt`），但换一台新 Mac、按公开仓库自举时，听力链没有可执行的引导入口，且错误提示指向一个不存在的脚本。这是「全新环境」问题，不是「本机」问题。

**问题 2：`EXPECTED_PYTHON = (3, 14)` 与 macOS 自带 `python3`（3.9.6）冲突，无降级路径**

`doctor.py:75` 只要求 `sys.version_info >= (3, 11)`，而听力链命令一律要求 `== (3, 14)`。macOS 默认 `/usr/bin/python3` 是 CLT 自带的 **3.9.6**，若 PATH 中没有用户安装的 3.14，`python3 -m lingotrace.init doctor` 会通过（3.11+ 检查），但听力链命令会拒绝执行，且没有自动降级或清晰的安装指引。

### 2.3 P2：macOS 本机可用但脆弱的平台问题

**问题 3：`invoke_listenkit` 硬编码 `/bin/bash`（transcribe_listening.py:646）**

```python
command = ["/bin/bash", str(script_path), ...]
```

macOS 上 `/bin/bash` 存在，不会像 Windows 那样抛 `[WinError 2]`，但它是 **bash 3.2**（2007 年）。当前 ListenKit 的 `generate-markdown.sh` 只用 bash 3.2 支持的语法，实测可用；但只要该脚本未来引入 bash 4+ 语法（关联数组等），这里就会静默失败。更稳妥的是 `shutil.which("bash")` 或依赖脚本 shebang。同文件其他外部命令（ffmpeg/ffprobe）已正确走 `shutil.which`，唯独此处写死绝对路径。

**问题 4：macOS 专属缓存路径无条件硬编码（setup_offline_dictionary.py:21、transcribe_listening.py:354）**

```python
return Path.home() / "Library" / "Caches" / "jp-listening-dicts"
```

macOS 本机使用正确；但代码无 `platform.system()` 分支，Linux/Windows 上会生成系统不认识的 `~/Library/Caches/...` 目录（有 `JP_LISTENING_DICT_DIR` 逃生口，但默认值错误）。跨平台声明不实。

**问题 5：`doctor.py:46,75` 版本检查校验的是「当前解释器」而非 `which("python3")` 解析到的解释器**

```python
python_command = which("python3") or which("python")
...
elif sys.version_info < (3, 11):
    errors.append(Finding(code="python_version_unsupported", ...))
```

`sys.version_info` 是运行 doctor 模块的解释器版本，不是 `which` 找到的 `python_command` 的真实版本。在 macOS「系统 3.9 + 用户 3.14 并存」的环境最易踩中：报告可能把 3.9 的路径标记为 `found`/合格。

**问题 6：`apple` 引擎无平台门禁，默认双 ASR 在非 macOS 上必然 `secondary_unavailable`**

`transcribe_listening.py:397,598,1890`：`--engine apple` 无 `platform.system() != "darwin"` 拦截；默认双 ASR 逻辑（`:1890`）只要主引擎不是 apple，副引擎就固定选 `apple`。macOS 本机正常；Linux/Windows 上每次默认转写都会尝试 Apple Speech 并降级。

**问题 7：打包/依赖元数据缺失 + macOS 编译前提未声明**

仓库无 `pyproject.toml`/`setup.py`/根 `requirements.txt`，只有 `tools/listening-transcribe-official/requirements-listening.txt`（含 `fugashi==1.5.2`、`unidic-lite==1.0.8`）。`fugashi` 是带 C++ 扩展的包，Python 3.14 很可能没有预编译 wheel，全新 macOS 机器需要 Xcode CLT（clang）才能源码构建；文档未声明这一 macOS 前提。`python -m lingotrace.init` 依赖运行时根在 `sys.path` 上（`PYTHONPATH=.` 或 cwd），属隐性约定。

**问题 8：TCC / 全磁盘访问未文档化**

默认 Vault 在 `~/Documents/Obsidian/LingoTrace-*`，日常流程读写 `~/Documents`、`~/Library/Application Support`、`~/Library/Caches`。现代 macOS 上，终端/Agent 宿主进程访问 `~/Documents` 等目录需要「完全磁盘访问」或至少一次授权；代码对 iCloud-backed venv 有 `/Library/Mobile Documents/` 检测（macOS 意识正确），但 docs 未提 TCC 授权步骤。

**问题 9：`agent-skills/` 目录只剩被忽略的 `.pyc`，无源码**

`agent-skills/` 仅含 `__pycache__/*.cpython-314*.pyc`，`git ls-files agent-skills/` 为空。真实实现存在于私有 `codex-skills/`。公开检出缺功能，残留 `.pyc` 佐证开发机是 Python 3.14。

### 2.4 Agent（Claude Code）兼容性专项：Codex → Claude Code

两个运行时原本面向 **Codex** 开发。对我（Claude Code）而言，实测结论如下：

| 维度 | 结论 |
| --- | --- |
| 接入入口 | ✅ 我通过 Vault 根 `AGENTS.md` 接入（`AGENTS.md` → 解析 runtime connections → 读 `SKILL.md`），不依赖 `.claude/`。这条路径对任何遵循 `AGENTS.md` 的 Agent 都通，实测通过 |
| CLI 契约 | ✅ `python -m lingotrace.init <cmd>` + JSON 报告（`accepted`/`errors`/`changed_files`）对 Claude Code 完全可执行，实测全部跑通 |
| 语言包 SKILL.md | ✅ 自然语言操作入口，多 Agent 友好。`english/agent_skills/SKILL.md:101` 明确写 "whether the caller is Codex, Gemini, or another compatible agent"。english 与 japanese 两份 SKILL 结构一致，差异仅语言内容 |
| 听力链路编排 | ✅ `invoke_listenkit` 调用 ListenKit 的完整链路（MLX/Metal 转写 + 写守卫）对 Claude Code 实测可用（dry-run 与 apply 均通过） |
| **pytest 测试路径坑** | ⚠️ 直接 `python -m pytest tests/` 会因缺 PYTHONPATH 配置产生 **30 个 collection ERROR**（`ModuleNotFoundError: No module named 'lingotrace.core.capabilities'`）；`PYTHONPATH=. python -m pytest tests/` 则正常收集 244 项；项目官方方式是 `PYTHONPATH=. python -m unittest discover -s tests/lingotrace`。**一个按直觉跑 pytest 的 Agent 会误判项目测试全挂**，文档未说明正确测试方式 |
| `.claude/settings.local.json` | ⚠️ 是 macOS + Codex 形状：含 `Read(//private/tmp/**)`（macOS 有效）、绝对 `/Users/jiezhengj/...` 路径、`~/.codex/skills/`、`Bash(python -m pytest tools/ codex-skills/ ...)`（指向私有目录）。在本机这些规则部分有效、部分失效，暴露了为 Codex + 本开发机编写的事实。它被 `.gitignore` 忽略，非公共内容 |
| 文档表述 | ⚠️ `docs/learner-agent-setup.md:172` 写「在 Codex 或兼容 Agent 中把 Vault 目录设为日常学习工作区」——已承认非 Codex Agent 可用，但默认表述仍以 Codex 为参照 |
| 代码审计（agent 能力轴） | ✅ 生产代码无 `shell=True`、无 `os.system`、无 `os.fork`/`resource`/`fcntl`/`pwd`/`grp`；所有路径 join 走 pathlib；文本读写显式 `encoding="utf-8"`（与 Windows 侧报告结论一致）。`platform.system()` 归一化（`darwin→macos`）正确 |

### 2.5 对 macOS 兼容性的总体评估

**在 macOS（arm64）+ Python 3.14 上，LingoTrace 核心运行时可用度很高（约 85–90%）。** 平台抽象层（current_platform + 三平台路径 + iCloud 检测 + POSIX 文件操作）设计扎实；开发机上完整听力链实测可用；CI 在 Ubuntu 上全量通过，说明核心包、migration、packs 与 workflows 的跨平台基线可信。**最可能失败/受阻的点按顺序为：①全新 macOS 机器的听力链自举（P1-1）；②macOS 默认 python3 3.9.6 与听力链「恰好 3.14」的版本冲突（P1-2）；③TCC/全磁盘访问的首次授权（P2-8）。**

---

## 三、我的需求

按优先级排列，说明我需要什么才能在这台 macOS 设备上完整履行 `SKILL.md` 规定的职责：

1. **公开仓库内提供听力链的自举入口。** 目前我在这台机器上可以完成精听稿、来源笔记、复习卡、口语卡、复习结算的全部能力；但换新 Mac 后，听力链（`SKILL.md` 最靠前的能力）没有可执行的引导脚本。请把创建 Python 3.14 venv 的 `init-listening-runtime.sh` 收进公开仓库（或提供官方等价安装文档）。
2. **听力链的 Python 版本门槛从「恰好 3.14」降为「>= 3.11 且 3.14 优先」，或提供清晰降级。** 现在 `doctor` 的 3.11+ 检查会通过、听力链命令却拒绝执行，两者不一致；我面对学习者时无法转述这种矛盾。
3. **明确测试运行方式。** 我按直觉 `python -m pytest tests/` 会看到 30 个 collection 错误；请把「`PYTHONPATH=. python -m unittest discover -s tests/lingotrace`」写进 `README.md` 或 `CONTRIBUTING.md`，避免 Agent 误判项目状态。
4. **（可选）收敛 `.claude/settings.local.json` 的 Codex 遗留。** 它现在只对「本机 + Codex」有意义；对 Claude Code 或其他机器部分规则静默失效。若保留，建议移除 `~/.codex/skills/` 与私有路径规则，或改写成框架无关的说明。
5. **（可选）文档把「Codex 或兼容 Agent」的表述更新为对等措辞。** 我已通过 `AGENTS.md` 接入，无需改代码；如文档能明确「任意遵循 AGENTS.md 的 Agent 均可接入」，会减少后续 Agent 的试探成本。

---

## 四、我的建议方案

### 方案 A（推荐）：公开听力链自举脚本

把 `codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh`（以及 `check-listening-chain.sh`、`run-listening-transcribe.sh`）收进公开仓库（例如 `tools/listening-transcribe-official/`），并让 `setup_offline_dictionary.py:203` 与 `transcribe_listening.py:271` 指向仓库内路径。同时：

- `tools/listening-transcribe-official/README.md` 写清楚：需要 Python 3.14、需要 Xcode CLT（`fugashi` 源码编译）、TCC/全磁盘访问授权步骤；
- 保留 `EXPECTED_PYTHON = (3, 14)` 的强校验，但把「如何安装 3.14」的命令示例写进文档。

### 方案 B（推荐）：统一 Python 版本契约

在 `doctor.py` 中同时报告「PATH 上 `python3` 解析到的解释器版本」与「当前运行解释器版本」，并在两者不一致时给出 warning。把 `EXPECTED_PYTHON = (3, 14)` 改为「主推 3.14，最低 3.11」，听力链命令在非 3.14 时打印可执行的安装指引（如 `brew install python@3.14`），而不是只报一个指向不存在脚本的提示。

### 方案 C：修复 `invoke_listenkit` 的解释器发现

```python
bash = shutil.which("bash") or "/bin/bash"
command = [bash, str(script_path), ...]
```

同时在 `preflight` 阶段校验 `bash` 存在，让失败在 preflight 阶段以可读信息暴露。这同时修复跨平台声明（Windows 上 `/bin/bash` 不存在）。

### 方案 D：文档与配置收敛

1. `README.md`/`CONTRIBUTING.md` 补「如何运行测试」一节，写明 `PYTHONPATH=. python -m unittest discover -s tests/lingotrace -p 'test_*.py'`。
2. `.claude/settings.local.json` 移除 `~/.codex/skills/` 与私有绝对路径规则，或标注「本机开发专用」。
3. `docs/learner-agent-setup.md:172` 等处的「Codex 或兼容 Agent」改为「任一遵循 AGENTS.md 的 Agent（如 Codex、Claude Code 等）」。

### 建议的验证方式

改动后，在 macOS 上按以下顺序验证：

1. 空环境跑 `setup_offline_dictionary.py` 应给出可执行的安装指引而非指向不存在脚本；
2. `PYTHONPATH=. python -m unittest discover -s tests/lingotrace` 全绿；
3. 用 4 秒测试音频跑通 `transcribe_listening.py --apply` 完整写入路径；
4. 在 Windows/Linux 上回归，确认 `.sh`/`.ps1` 与缓存路径分支未被破坏。

---

## 五、文档落位说明

本文件放在 `docs/agent-compatibility-report/` 下，符合 `tools/git/check-public-staged-files.sh` 的公共白名单（`docs/` 在允许列表内），不会导致提交校验失败。

我没有修改本仓库的任何代码，没有创建分支，也没有执行提交。按 `AGENTS.md` 的 Git 工作流，`main` 是受保护分支，任何改动都应经由 topic branch 与 pull request；本报告仅作为问题记录留存，是否采纳与如何实施由维护者决定。

本次检查中我对本仓库的唯一写入是运行 `python -m lingotrace.init check-update`（在临时 Vault 上执行，写入 `/tmp/lt-test-vault/.lingotrace/runtime-update-checks/macos.json`，未触碰本仓库或真实 Vault 的工作区）。其余操作均为只读命令与在 `/tmp` 临时目录下的转写测试。

---

## 六、附录

### 6.1 实测记录（本次真实执行）

| 命令 | 结果 |
| --- | --- |
| `python -c "import lingotrace"` | ✅ 正常 |
| `python -m lingotrace.init resolve-runtime --vault <real-vault>` | ✅ `accepted: true`，SKILL 路径正确 |
| `python -m lingotrace.init doctor --language english --vault ... --runtime-root ...` | ✅ `exit_code: 0`，全部依赖 `found` |
| `python -m lingotrace.init resolve-listenkit --vault <real-vault>` | ✅ 返回 `.sh` 入口（macOS 正确） |
| `python -m lingotrace.init check-update --vault /tmp/lt-test-vault ...` | ✅ `fork_up_to_date`，正确识别 fork |
| `PYTHONPATH=. python -m unittest discover -s tests/lingotrace` | ✅ 244 passed |
| `PYTHONPATH=. python -m unittest discover -s tools/architecture-baseline/tests` | ✅ 42 passed |
| `PYTHONPATH=. python -m unittest discover -s tools/listening-transcribe-official/tests` | ✅ 100 passed |
| `python -m pytest tests/`（无 PYTHONPATH） | ❌ 30 collection ERROR（`ModuleNotFoundError`） |
| `PYTHONPATH=. python -m pytest tests/ --co` | ✅ 244 collected |
| 听力链路 `--dry-run`（临时 Vault，MLX 转写） | ✅ `status: complete`，preview `accepted: true` |
| 听力链路 `--apply`（临时 Vault） | ✅ `apply.accepted: true`，4 文件落盘 |
| 听力链路 preflight（`preflight_listenkit_generate_tooling` + `preflight_intensive_slice_tooling`） | ✅ 通过（ffmpeg/ffprobe 可用） |

### 6.2 代码审计范围（macOS 兼容性）

对 `lingotrace/`、`tools/`、`agent-skills/`、`tests/` 下全部 `.py` 做了模式扫描：生产代码中**没有** `shell=True`、`os.system`、`os.fork`、`resource`、`fcntl`、`pwd`、`grp`；所有路径 join 走 pathlib；文本读写显式 `encoding="utf-8"`。`platform.system()` 归一化（`darwin→macos`）与三平台路径分支完整。发现的平台问题集中在听力工具链（`tools/listening-transcribe-official/`）与引导流程，已列入正文。

### 6.3 与既有的 Windows 报告的关系

本目录已有 `claude-code-agent-windows-compatibility.md`。两份报告是同一运行时在不同宿主 OS 上的独立审计：

- **Windows 侧**：Claude Code 的断点是「LingoTrace 编排层在 Windows 上返回/调用错误入口」（`resolve-listenkit` 返回 `.sh`、`transcribe_listening.py:646` 硬编码 `/bin/bash` 在 Windows 上不存在），以及文档 `python3` 是 Store stub。
- **macOS 侧**：Claude Code 的断点收敛为「全新机器听力链自举缺失」与「Python 版本契约不一致」两处 P1；`resolve-listenkit` 返回的 `.sh` 在 macOS 上是正确入口，`/bin/bash` 在 macOS 上存在，故 Windows 侧的两个 P0 在 macOS 上都不成立。
- **两侧共享**：`pytest` 直接跑 collection 失败（无 PYTHONPATH 配置）、`.claude/settings.local.json` 的 Codex/macOS 形状、文档以 Codex 为默认表述。

### 6.4 环境交叉验证

- `doctor` 报 `platform: macos`、`python: 3.14.4`、`obsidian_desktop: /Applications/Obsidian.app`、`github_cli: /opt/homebrew/bin/gh` —— macOS 依赖检测全部命中。
- ListenKit `doctor` 报 `asr_auto_engine: mlx`、`mlx_metal: ready`，MLX small 模型已缓存；端到端转写确认 `engine=mlx-whisper, device=metal, compute_type=float16`，转写文本与原始语音 100% 一致（"Hello and welcome to today's intensive listening lesson."）。
