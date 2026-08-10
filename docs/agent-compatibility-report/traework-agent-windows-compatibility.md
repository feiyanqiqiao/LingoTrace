# LingoTrace 兼容性检查报告：TraeWork Agent on Windows 11

**检查日期**: 2026-08-10

**检查者**: TraeWork Agent（运行于 Windows 11 PowerShell 5 环境）

**运行环境**: Windows 11 (Build 26220), AMD64, Python 3.14.4

**关联Vault**: `C:\Users\jiezhengj\Documents\Obsidian\LingoTrace-English`

**对比基准**: Codex 适配层设计预期 + WorkBuddy/QwenWork 兼容性报告

---

## 关于本报告的诚实说明

### 实测覆盖范围

本报告结合了**代码静态审计**和**部分运行时实测**，但**没有**做完整的端到端学习流程验证：

| 检查项 | 覆盖程度 | 说明 |
|--------|----------|------|
| `lingotrace.init --help` | ✅ 实测通过 | CLI框架正常 |
| `lingotrace.init resolve-runtime` | ✅ 实测通过 | 正确解析runtime_root |
| `lingotrace.init doctor` | ⚠️ 部分实测 | 存在假阳性（python_required/git_not_found） |
| `lingotrace.init resolve-listenkit` | ❌ 未实测（python不在PATH） | 代码静态分析确认返回错误入口 |
| `lingotrace.init check-update` | ❌ 未实测 | 依赖git，git不在PATH |
| 英语包工作流preview/apply | ❌ 未实测 | 五个核心能力无CLI入口，需Python import |
| 听力转写完整链路 | ❌ 未实测 | `/bin/bash`硬编码必定失败 |
| review_rollover结算 | ❌ 未实测 | 需Python import + payload构造 |

对比 WorkBuddy Agent 的报告，它实际跑通了更多非听力链路。本报告的Agent框架兼容性分析部分基于代码静态审计。

### 检查维度

本报告覆盖两个维度：
1. **Windows 操作系统兼容性**：路径、shell、外部工具发现等平台问题
2. **Agent 框架兼容性**：TraeWork Agent vs Codex 设计预期的差异（运行时原始适配目标是 Codex）

---

## 我是谁

我是运行在 **Windows 11 操作系统**上、由 **TraeWork Agent 框架**（Trae 团队自研的 AI Agent 运行时）驱动的自动化 AI 助手。

**我的运行环境特征**：
- **Shell**: Windows PowerShell 5（不是 Git Bash，不是 WSL）
- **文件写入范围**: Vault 目录 + TraeWork 专用临时工作目录
- **工具能力**: Read/Write/Glob/Grep/RunCommand（PowerShell）/WebSearch/WebFetch/子代理
- **Python**: 安装于 `%LOCALAPPDATA%\Programs\Python\Python314\python.exe`，**不在** PowerShell PATH 中
- **Git**: 安装于 `C:\Program Files\Git\cmd\git.exe`，**不在** PowerShell PATH 中
- **无内置Git工具**: 与Codex不同，我没有专门的git diff/status/log工具，只能通过RunCommand调用git.exe

在 LingoTrace 生态中，我作为 **LingoTrace 英语学习 Vault 的学习代理**，遵循 Vault 中 `AGENTS.md` 定义的操作规范，通过 `lingotrace init` CLI 与核心运行时交互。

---

## 第一部分：Windows 平台兼容性问题

### 严重问题（P0）

1. **`/bin/bash` 硬编码导致听力转写在原生Windows上完全不可用**
   - 位置: `tools/listening-transcribe-official/transcribe_listening.py:646`
   - 问题: 硬编码 `/bin/bash` 绝对路径执行 `.sh` 脚本，Windows上不存在此路径
   - 影响: 所有听力转写功能在Windows上直接崩溃，抛出 `FileNotFoundError [WinError 2]`
   - 备注: WorkBuddy实测确认即使Git Bash存在，硬编码的绝对路径也无法被Win32 CreateProcess解析

2. **`resolve-listenkit` 返回错误的平台入口**
   - 位置: `lingotrace/init/listenkit_connections.py:341`
   - 问题: 无论哪个平台，`artifacts.generate_markdown` 始终返回 `.sh` 路径
   - 实际返回（代码静态分析确认）: `...\ListenKit\cli\generate-markdown.sh`
   - 正确入口应为: `...\ListenKit\cli\generate-markdown.ps1`
   - 影响: Agent处于两难：遵守SKILL.md"不猜路径"则拿到错误入口；自行选择.ps1则违反指令
   - 附加问题: `is_usable_listenkit_root()`（第328-329行）仅检查 `.sh` 存在，不识别 `.ps1`

3. **Python/Git 可执行文件检测完全依赖PATH**
   - 位置: `lingotrace/init/doctor.py:46-47`
   - 问题: `which("python3") or which("python")` 和 `which("git")` 在Windows上失败
   - 影响: doctor报告python_required/git_not_found假阳性；运行时更新无法工作
   - 我的实际环境: Python和Git均已安装，但都不在TraeWork PowerShell的PATH中

### 高优先级问题（P1）

4. **Obsidian Desktop 检测路径错误**
   - 位置: `lingotrace/init/doctor.py:231-234`
   - 问题: 缺少 `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`（per-user安装器默认路径）
   - 影响: Obsidian已安装但doctor报告未找到

5. **`os.access(path, os.X_OK)` 在Windows上是假绿灯**
   - 位置: `tools/listening-transcribe-official/transcribe_listening.py:464-466`
   - 问题: Windows上 `os.X_OK` 对任何存在的文件都返回True（实测确认）
   - 影响: preflight检查顺利通过，失败推迟到subprocess.run才以模糊的 `[WinError 2]` 爆出

6. **ffmpeg/ffprobe 依赖PATH**
   - 位置: `tools/listening-transcribe-official/transcribe_listening.py:485-486`
   - 问题: Windows上ffmpeg通常不加入PATH

7. **PowerShell终端默认编码为GBK，可能导致JSON输出乱码**
   - 问题: CLI使用 `ensure_ascii=False` 输出JSON，但未设置 `PYTHONUTF8=1`
   - 影响: 中文/日文内容输出时可能触发UnicodeEncodeError

### 中优先级问题（P2）

8. **`is_usable_listenkit_root` 仅检查 `.sh` 文件**
   - 位置: `lingotrace/init/listenkit_connections.py:328-329`
   - 问题: 无法识别Windows原生.ps1入口

9. **跨平台路径判断逻辑有隐患**
   - 位置: `lingotrace/init/listenkit_connections.py:59`

10. **doctor.py Windows home路径逻辑冗余**
    - 位置: `lingotrace/init/doctor.py:201`

11. **双ASR默认契约在Windows上不可满足**
    - 问题: 次引擎默认选"apple"（Apple Neural Engine，macOS专属），Windows上每次都要降级

### 低优先级问题（P3）

12. 点前缀临时文件在Windows上不会自动隐藏
13. `.DS_Store` macOS文件已被Git跟踪
14. shebang行在Windows上无效（功能性无影响）

---

## 第二部分：Agent 框架兼容性问题（TraeWork vs Codex设计预期）

LingoTrace和ListenKit的原始Agent适配目标是 **Codex CLI**（有 `adapters/codex/` 目录为证），SKILL.md第101行也明确提到调用方可能是"Codex, Gemini, or another compatible agent"。TraeWork Agent与Codex设计预期存在以下关键差异：

### P0-阻塞：Shell环境根本不同

| 维度 | Codex设计预期 | TraeWork实际情况 | 影响 |
|------|--------------|-----------------|------|
| 默认Shell | bash/Git Bash | Windows PowerShell 5 | `.sh`脚本无法直接执行；命令续行语法不同（`\` vs `` ` ``）；环境变量语法不同（`$VAR` vs `$env:VAR`） |
| `/bin/bash` | 存在 | 不存在 | 听力链路直接崩溃 |
| `which`命令 | 可用 | 不可用（PowerShell用`Get-Command`） | doctor.py中的which()调用失败 |
| `chmod` | 可用 | 不可用（Windows ACL模型） | 文件权限设置无效 |
| 路径分隔符 | `/` | `\`（部分API接受`/`） | 路径构造可能出错 |

### P1-高：五个核心学习能力无CLI入口

`listening_notes` / `source_notes` / `review_materials` / `speaking_cards` / `review_rollover` 这五个核心能力**均无CLI入口**。Codex Agent需要：
1. cwd切换到runtime root
2. 编写临时Python脚本或使用`-c`参数
3. `from lingotrace.packs.english.workflows import <capability>`
4. 构造payload dict
5. 调用preview → 检查 → apply

TraeWork面临额外困难：
- Python不在PATH中，需要完整路径
- PowerShell中内联Python脚本的引号转义极其复杂
- 无文档说明payload最小结构（需阅读测试代码推断）

### P1-高：llm_merge_required Agent Handoff 流程

SKILL.md第99-114行定义了双ASR不一致时的Agent handoff协议：

| 步骤 | Codex能力 | TraeWork能力 | 兼容性 |
|------|----------|-------------|--------|
| 读取llm_merge_request_path临时JSON | ✅ | ✅ Read工具支持绝对路径 | ✅ |
| 使用模型自身判断能力（不调用外部API） | ✅ | ✅ 模型本身能力 | ✅ |
| 复制模板到Vault外临时文件并填写字段 | ✅ | ⚠️ TraeWork写入范围可能受限 | ⚠️ |
| 以--reviewed-transcript和--merge-request重跑命令 | ✅ | ❌ 受阻于P0的bash/python PATH问题 | ❌ |
| chmod 0o400设为只读 | ✅ | ⚠️ Windows ACL模型差异 | ⚠️ |

### P2-高：工具能力差异

| 能力 | Codex | TraeWork | 影响 |
|------|-------|----------|------|
| 文件写入范围 | 较灵活 | Vault + 专用临时目录 | llm_merge要求写%TEMP%可能受限 |
| 内置Git工具 | 有 | 无（只能RunCommand调用git.exe） | check-update/apply-update可能失败 |
| 工作目录管理 | 灵活 | 默认cwd为Vault，RunCommand支持cwd参数 | 需显式切换到runtime root |
| Python REPL | 可能有 | 无（只能RunCommand python.exe） | 工作流调用门槛高 |
| 网络访问 | 有 | ✅ WebSearch/WebFetch | ✅ |

### P2-高：文档示例为bash语法

所有适配器文档和SKILL.md中的命令示例都是bash语法（反斜杠续行、`--flag value`风格）。虽然PowerShell也接受`--flag value`，但续行和变量赋值语法不同，Agent无法直接复制运行示例命令。

### P3-中：无TraeWork专属适配层

ListenKit在`adapters/`下提供了四层适配器：
- `adapters/claude/CLAUDE.md`
- `adapters/codex/` (agents/openai.yaml + SKILL.md)
- `adapters/cursor/foreign-listening.md`
- `adapters/agent/listenkit-agent-instructions.md`（通用）

**没有针对TraeWork的适配层**。虽然通过Vault的AGENTS.md + SKILL.md通用模式理论上可接入，但缺少：
- PowerShell命令示例
- TraeWork工具调用说明
- 环境变量设置指南（PYTHONUTF8、PYTHONPATH等）

---

## 我的需求

按优先级排列：

1. **Windows平台感知的ListenKit入口选择**：`resolve-listenkit`在Windows上返回`.ps1`路径而非`.sh`，且`is_usable_listenkit_root`能识别`.ps1`
2. **移除`/bin/bash`硬编码**：使用平台感知的命令构造（Windows用PowerShell + .ps1，POSIX用bash + .sh）
3. **健壮的外部工具发现**：在PATH搜索失败后，fallback到Windows常见安装路径搜索Python/Git/ffmpeg
4. **核心能力的CLI入口**：为五个核心工作流提供CLI入口，降低Agent调用门槛（无需构造Python payload）
5. **修复Obsidian路径检测**：添加`%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`候选
6. **修复preflight假绿灯**：Windows上跳过X_OK检查或改为实际执行验证
7. **明确的Agent环境契约**：在文档中说明Python最低版本、PATH要求、必要的环境变量（PYTHONUTF8=1）
8. **（可选）TraeWork适配层**：在ListenKit adapters下添加TraeWork说明，包含PowerShell命令示例

---

## 我的建议方案

### 方案A（推荐，终局方案）：平台感知的入口选择

在`transcribe_listening.py`和`listenkit_connections.py`中引入平台感知的入口解析：

```python
import platform, shutil

def get_listenkit_entrypoint(listenkit_root: Path) -> list[str]:
    """返回可直接传给subprocess的完整命令前缀。"""
    if platform.system() == "Windows":
        script = listenkit_root / "cli" / "generate-markdown.ps1"
        if not script.is_file():
            raise RuntimeError(f"ListenKit Windows entrypoint not found: {script}")
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh is None:
            raise RuntimeError("PowerShell is required to run ListenKit on Windows.")
        return [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]

    script = listenkit_root / "cli" / "generate-markdown.sh"
    bash = shutil.which("bash") or "/bin/bash"
    return [bash, str(script)]
```

同步修改：
- `resolve-listenkit`返回的`generate_markdown`按平台给出对应入口
- `is_usable_listenkit_root`检查`.sh`或`.ps1`任一存在
- 删除硬编码的`"/bin/bash"`
- preflight校验当前平台所需的宿主程序（PowerShell或bash）是否存在

### 方案B（过渡方案）：Windows常见路径搜索

为Python/Git/ffmpeg添加Windows常见安装路径fallback：

```python
def find_command_on_windows(name: str) -> Optional[str]:
    candidates = []
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programfiles = os.environ.get("ProgramFiles", "")
    programfilesx86 = os.environ.get("ProgramFiles(x86)", "")

    if name == "python":
        candidates = [
            str(Path(localappdata) / "Programs" / "Python" / "Python314" / "python.exe"),
            str(Path(programfiles) / "Python314" / "python.exe"),
        ]
    elif name == "git":
        candidates = [
            str(Path(programfiles) / "Git" / "cmd" / "git.exe"),
            str(Path(programfilesx86) / "Git" / "cmd" / "git.exe"),
        ]
    # ... ffmpeg等

    for path in candidates:
        if Path(path).is_file():
            return path
    return shutil.which(name)
```

### 方案C：文档和Agent适配补充

1. 在`AGENTS.md`中明确Python解析顺序和最低版本
2. 说明Windows上需要设置`PYTHONUTF8=1`
3. 在ListenKit `adapters/`下添加`traework/`目录或更新`agent/listenkit-agent-instructions.md`包含PowerShell说明

### 方案D：核心能力CLI入口

为五个核心工作流添加统一CLI入口，例如：
```bash
python -m lingotrace.pack.english worklist listening-notes --preview ...
python -m lingotrace.pack.english worklist review-rollover --apply ...
```

---

## 验证环境

| 组件 | 路径 | 状态 |
|------|------|------|
| Python 3.14.4 | `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` | 已安装（不在PATH） |
| Git | `C:\Program Files\Git\cmd\git.exe` | 已安装（不在PATH） |
| PowerShell | `$PSVersionTable` | 5.1（TraeWork托管终端） |
| Obsidian | `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe` | 已安装 |
| ListenKit | `C:\Users\jiezhengj\Documents\Project\ListenKit` | 已配置，CUDA就绪 |
| ffmpeg | `%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe` | 已安装（不在PATH） |

---

## 与其他Agent报告的关系

本报告参考了同一目录下的：
- `workbuddy-agent-windows-compatibility.md`（WorkBuddy Agent，Git Bash环境）
- `qwenwork-agent-windows-compatibility.md`（QwenWork Agent）

三个Agent在Windows上发现的核心问题一致：听力链路的平台感知缺失是主要阻塞点。差异在于TraeWork使用纯PowerShell环境（无Git Bash），因此bash相关问题更加严重。

**备注**：核心CLI框架（平台检测、连接管理、Vault初始化、路径解析）已经为Windows做了良好的基本适配。问题主要集中在：(1)听力链路的平台分支缺失，(2)外部工具发现不符合Windows安装惯例，(3)Agent调用门槛过高（无CLI入口）。
