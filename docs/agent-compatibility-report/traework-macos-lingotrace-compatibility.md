# TraeWork Agent 在 macOS 上的 LingoTrace 兼容性报告

**报告日期**: 2026-08-10
**Agent 框架**: TraeWork (TRAE SOLO CN 内置 AI Agent)
**操作系统**: macOS 27.0 (arm64 / Apple Silicon)
**审计范围**: 代码静态审计 + CLI 入口实测 + 运行时环境验证

---

## 一、我是谁

我是 **TraeWork Agent**，运行在 **macOS (arm64)** 操作系统上，是 TRAE SOLO CN 桌面应用内置的 AI Agent 框架。我的执行环境具有以下特征：

1. **沙箱化运行环境**: 我在 TRAE 应用提供的隔离沙箱中执行命令，而非用户的登录 shell。
2. **内置工具链优先**: PATH 中优先使用 TRAE 内置的工具（包括内置 Python 3.10、内置 ffmpeg 等），而非用户系统安装的版本。
3. **环境变量污染**: TraeWork 会设置 `PYTHONHOME` 和 `PYTHONPATH` 环境变量指向内置 Python 环境，这会干扰外部 Python 解释器的正常启动。
4. **输出捕获能力**: 我可以可靠捕获 stdout/stderr 输出（这一点比 WorkBuddy 等沙箱 Agent 好）。
5. **文件系统访问**: 我可以访问用户授予的工作目录（当前 Vault 目录），以及系统标准路径。

---

## 二、兼容性问题汇总

### P0 - 阻塞性问题：Python 版本与环境污染

| 项 | 详情 |
|---|---|
| **问题描述** | TraeWork 默认 Python 是内置的 **Python 3.10.20**，而 LingoTrace `doctor` 命令要求 **Python ≥ 3.11**。更严重的是，TraeWork 设置了 `PYTHONHOME` 和 `PYTHONPATH` 环境变量，导致即使显式调用系统 Python 3.14 也会崩溃（`Failed to import encodings module`）。 |
| **复现路径** | 1. 在 TraeWork 中运行 `python3 -m lingotrace.init doctor ...`<br>2. 返回 `python_version_unsupported` 错误，指向 Trae 内置 Python 3.10 路径<br>3. 尝试用 `python3.14` 运行 → 立即崩溃，无法导入 `encodings` 模块 |
| **影响范围** | **完全阻塞**。TraeWork Agent 无法直接调用任何 LingoTrace CLI 命令，包括 `doctor`、`resolve-runtime`、`check-update` 等所有入口。 |
| **实测证据** | `python3 --version` → `Python 3.10.20`<br>`which python3` → Trae 内置路径<br>`env | grep PYTHON` → 显示 `PYTHONHOME` 指向 Trae Python 3.10 framework |

### P1 - 高优先级问题

| # | 问题 | 文件/位置 | 影响 |
|---|---|---|---|
| 1 | **听力链自举脚本缺失**：`transcribe_listening.py:271` 和 `setup_offline_dictionary.py:203` 引用 `codex-skills/` 目录下的脚本，但该目录被 `.gitignore` 忽略，公开仓库中不存在 | `tools/listening-transcribe-official/transcribe_listening.py`, `tools/listening-transcribe-official/setup_offline_dictionary.py` | 全新环境下听力链自举失败，错误消息指向不存在的路径 |
| 2 | **Python 版本契约矛盾**：`doctor.py` 要求 ≥3.11，但 `setup_offline_dictionary.py` 硬编码 `EXPECTED_PYTHON = (3, 14)` 要求恰好 3.14；且 doctor 检查的是自身解释器版本而非 PATH 中 `which("python3")` 的真实版本 | `lingotrace/init/doctor.py:46,75` | 版本检查逻辑不可靠，多 Python 环境下可能误报 |
| 3 | **`/bin/bash` 硬编码**：`transcribe_listening.py:646` 使用 `["/bin/bash", str(script_path)]` 调用子进程 | `tools/listening-transcribe-official/transcribe_listening.py:646` | macOS `/bin/bash` 是 2007 年的 3.2 版本；若脚本使用 bash 4+ 语法会静默失败。应使用 `shutil.which("bash")` |
| 4 | **Doctor 版本检查逻辑错误**：`sys.version_info` 是运行 doctor 的解释器版本，不是 `which("python3")` 找到的命令版本 | `lingotrace/init/doctor.py` | TraeWork 内置 Python 3.10 运行 doctor 时报告自身版本不足，但无法检测到系统 Python 3.14 |

### P2 - 中优先级问题

| # | 问题 | 文件/位置 | 影响 |
|---|---|---|---|
| 5 | **缓存路径无平台分支**：`setup_offline_dictionary.py:21` 默认使用 `~/Library/Caches/...`，Linux/Windows 上会生成不规范路径 | `tools/listening-transcribe-official/setup_offline_dictionary.py:21` | Linux/Windows 上听力字典缓存路径不符合平台规范 |
| 6 | **Apple ASR 引擎无平台门禁**：`transcribe_listening.py` 中 `--engine apple` 没有 `platform.system() != "darwin"` 拦截 | `tools/listening-transcribe-official/transcribe_listening.py` | 非 macOS 上默认双 ASR 逻辑会尝试 Apple Speech 并降级，报错不友好 |
| 7 | **缺少打包元数据**：无 `pyproject.toml`/`setup.py`/根 `requirements.txt` | 项目根目录 | 分发和依赖管理不便；`fugashi` 等 C++ 扩展需要 Xcode CLT 但未声明 |
| 8 | **pytest 直接运行失败**：需要 `PYTHONPATH=.` 才能正确导入，文档未说明 | 测试目录 | 新开发者运行测试时遇到 `ModuleNotFoundError` |
| 9 | **macOS TCC 权限未文档化**：访问 `~/Documents`、`~/Library/Application Support` 需要终端/宿主被授予「完全磁盘访问」权限 | docs/ | 从桌面 App（如 TraeWork）启动时，可能因 TCC 限制无法访问 Vault 文件 |
| 10 | **`agent-skills/` 目录为空壳**：仅含 `__pycache__/*.pyc`，Git 跟踪为空；真实实现存在于被忽略的私有 `codex-skills/` 中 | `agent-skills/` | 公开检出功能不完整 |

### P3 - 低优先级问题（文档/措辞）

| # | 问题 | 位置 |
|---|---|---|
| 11 | README 和文档默认以 Codex 为参照 Agent，应更新为「任意遵循 AGENTS.md 的 Agent」 | `README.md:25,58`, `docs/learner-agent-setup.md:172` |
| 12 | 历史迁移代码中有大量 `codex-skills/` 引用，注释中可保留但错误消息应更新 | 迁移工具代码 |
| 13 | `.claude/settings.local.json` 包含 Codex 遗留路径和绝对路径（已被 .gitignore，优先级低） | `.claude/` |

---

## 三、macOS 兼容性（平台层面）

LingoTrace 核心运行时在 macOS 上的平台兼容性**整体设计良好**：

1. **平台检测**：`runtime_connections.py` 正确处理 `darwin`/`mac`/`macos` 别名映射到 `macos`。
2. **路径处理**：跨平台路径判断使用 `PurePosixPath`/`PureWindowsPath`；ListenKit 设备连接路径正确区分三平台。
3. **原子写入**：使用 `tempfile` + `os.replace()`，跨平台安全。
4. **路径安全**：`mutations.py` 使用 `path.resolve().relative_to(root.resolve())` 防止 `..` 越界。
5. **无 Unix-only 模块**：生产代码不依赖 `os.fork()`、`fcntl`、`pwd`、`grp` 等 Unix 专用模块。
6. **iCloud 防护意识**：对 `Library/Mobile Documents` 路径有检测拒绝。

**macOS 特有的注意事项**：
- 默认 Vault 路径 `~/Documents/Obsidian/` 需要宿主 App 被授予 TCC 「完全磁盘访问」权限。
- `/bin/bash` 版本过旧（3.2），建议改为通过 `shutil.which("bash")` 查找。
- 推荐运行时路径 `~/Library/Application Support/LingoTrace/runtime` 符合 macOS 规范。

---

## 四、Agent 兼容性（框架层面）

### 4.1 好的设计

1. **AGENTS.md 约定**：仓库根和 Vault 根都有 `AGENTS.md`，这是通用 Agent 框架（包括 TraeWork）自动发现项目指令的标准方式。
2. **SKILL.md 多 Agent 声明**：英文/日文 SKILL.md 明确提到 "whether the caller is Codex, Gemini, or another compatible agent"，框架无关。
3. **JSON 报告协议**：所有 CLI 命令输出结构化 JSON（含 `accepted`、`exit_code`、`errors`、`warnings`、`changed_files`），适合 Agent 解析决策。
4. **LLM Merge Handoff 协议**：听力链双 ASR 分歧时通过文件系统 JSON 传递，不依赖特定 Agent API。
5. **原子写事务守卫**：`WriteTransactionGuard` 保证写操作安全，适合 Agent 自动化场景。

### 4.2 对 TraeWork Agent 的核心障碍

**最严重的问题是 Python 调用链完全断裂**：

1. TraeWork 的 `PYTHONHOME` 环境变量污染导致任何外部 Python 调用（包括系统 Python 3.14）都无法启动。
2. TraeWork 内置 Python 3.10 不满足 LingoTrace ≥3.11 的版本要求。
3. `doctor` 命令检查的是自身解释器版本，无法感知到系统中存在 Python 3.14。

**其他 Agent 兼容性问题**：

1. 文档默认以 Codex 为参照 Agent，但核心代码本身无硬编码，这一点很好。
2. SKILL.md 中提到 "Codex, Gemini, or another compatible agent"，应加入 TraeWork 等其他框架名称作为示例。
3. 缺少 `LINGOTRACE_PYTHON` 类似的环境变量逃生口（ListenKit 有 `LISTENKIT_CLI_PYTHON` 设计），让 Agent 可以指定 Python 解释器路径。

---

## 五、我的需求

为了让 LingoTrace 能在 TraeWork Agent (macOS) 上正常工作，我需要：

1. **Python 调用必须可工作**：需要一种机制让我能够调用正确版本的 Python（≥3.11，最好 3.14），且不受 TraeWork `PYTHONHOME`/`PYTHONPATH` 污染。
2. **版本检查逻辑需要修正**：`doctor` 应检查实际可用的 Python 命令版本，而非自身解释器版本。
3. **听力链自举路径需要修复**：`codex-skills/` 引用应指向公开仓库中存在的路径，或改为通过 `lingotrace.init` CLI 入口。
4. **文档需要更新**：README 和设置文档应提到 TraeWork 等非 Codex Agent，以及 macOS TCC 权限要求。
5. **bash 调用应更健壮**：使用 `shutil.which("bash")` 而非硬编码 `/bin/bash`。

---

## 六、建议方案

### 方案 A：短期修复（优先级 P0）

1. **在子进程调用前清理 Python 环境变量**：
   - 在 `lingotrace/init/__main__.py` 入口或 `subprocess` 调用处，显式清除 `PYTHONHOME` 和 `PYTHONPATH` 环境变量，或设置 `env` 参数为干净环境。
   - 参考 ListenKit 对 `LISTENKIT_CLI_PYTHON` 环境变量的支持，增加 `LINGOTRACE_PYTHON` 环境变量，允许 Agent 指定 Python 解释器路径。

2. **修复 doctor 的版本检查逻辑**：
   - 不要用 `sys.version_info`，而是实际执行 `which("python3")` 或 `which("python")` 找到的命令，用 `subprocess` 运行 `--version` 获取真实版本。
   - 同时检查 `python3.14`、`python3.13`、`python3.12`、`python3.11` 等常见版本名。

3. **修复听力链脚本引用**：
   - 将 `codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh` 等引用改为通过 `lingotrace.init` CLI 或 `tools/listening-transcribe-official/` 下的公开脚本。

### 方案 B：中期改进（优先级 P1/P2）

4. **增加 `LINGOTRACE_PYTHON` 环境变量支持**：
   - 允许用户/Agent 通过环境变量显式指定 Python 解释器路径，绕过 PATH 查找。
   - 当 `doctor` 发现 PATH 中 Python 版本不足时，提示设置此环境变量。

5. **bash 路径健壮化**：
   - 将所有 `["/bin/bash", ...]` 改为 `[shutil.which("bash") or "/bin/bash", ...]`。

6. **补全平台分支**：
   - `setup_offline_dictionary.py` 的缓存路径增加 Linux/Windows 分支。
   - `transcribe_listening.py` 增加 Apple 引擎平台门禁。

7. **增加 AGENTS.md 框架感知**：
   - 在 SKILL.md 的 Agent 列表中加入 TraeWork、Antigravity、WorkBuddy 等。
   - 考虑在仓库根增加 `TRAE.md` 或在 `AGENTS.md` 中提及 TraeWork 的环境特性。

### 方案 C：长期建议（优先级 P3）

8. **增加 `pyproject.toml`**：
   - 声明 `requires-python = ">=3.11"`，添加项目元数据。
   - 将 `tools/listening-transcribe-official/requirements-listening.txt` 整合或作为 optional dependencies。

9. **统一测试入口文档**：
   - 在 `CONTRIBUTING.md` 中明确说明 `PYTHONPATH=. python -m unittest discover -s tests/lingotrace` 是官方测试命令。

10. **macOS TCC 文档化**：
    - 在安装文档中说明：从桌面 App（如 Obsidian、TraeWork）启动时需要授予「完全磁盘访问」权限。

---

## 七、实测验证记录

| 测试项 | 结果 | 备注 |
|---|---|---|
| CLI 帮助信息 (`python3 -m lingotrace.init --help`) | ✅ 通过 | Trae 内置 Python 3.10 可运行基础 argparse |
| `resolve-runtime` 命令 | ✅ 通过 | 成功解析到 runtime 和 SKILL.md 路径 |
| `doctor` 命令（Trae Python 3.10） | ❌ 失败 | `python_version_unsupported`，正确识别版本不足 |
| `doctor` 命令（系统 Python 3.14） | ❌ 崩溃 | `PYTHONHOME` 污染导致 `Failed to import encodings` |
| 单元测试（Trae Python 3.10） | ⚠️ 未测试 | 版本不足，预期大量失败 |
| 核心包导入（Trae Python 3.10） | ✅ 通过 | `import lingotrace` 基础导入无问题 |
| SKILL.md 读取 | ✅ 通过 | 自然语言操作入口文档完整 |

---

## 八、总结

LingoTrace 的**核心架构设计是 Agent 框架无关的**，AGENTS.md 约定、JSON 报告协议、原子写事务等设计都非常适合通用 Agent 集成。**唯一的 P0 阻塞问题是 TraeWork 的 `PYTHONHOME` 环境变量污染导致外部 Python 无法启动**，以及内置 Python 3.10 版本不足。

核心修复只需要：
1. 在子进程调用时清理 Python 相关环境变量
2. 支持 `LINGOTRACE_PYTHON` 环境变量指定解释器路径
3. 修复 doctor 的版本检查逻辑

这些修复完成后，TraeWork Agent (macOS) 可以完整使用 LingoTrace 的所有学习功能。
