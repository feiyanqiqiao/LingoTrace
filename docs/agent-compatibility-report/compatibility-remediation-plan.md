# LingoTrace 多 Agent 跨平台兼容性整改方案

日期：2026-08-10

实施分支：`codex/windows-agent-compatibility`

输入证据：同目录下 Antigravity、Claude Code、QwenWork、TraeWork、WorkBuddy 在 Windows 与 macOS 上出具的 10 份报告

## 1. 目标与完成定义

本轮整改的目标不是给每个 Agent 增加一套专属适配器，而是把共同依赖收敛为平台感知、Agent 无关、可测试的公共契约。

Windows 阶段完成时必须满足：

1. `resolve-listenkit` 在原生 Windows 返回 `.ps1`，在 macOS/Linux 返回 `.sh`；连接有效性按当前平台入口判断。
2. LingoTrace 听力编排在原生 Windows 通过 PowerShell 调用 ListenKit，不再经过 `/bin/bash`、WSL 或 Git Bash。
3. preflight 能在真正启动转写前报告缺少的脚本、PowerShell、ffmpeg 或 ffprobe；错误包含可行动的路径或命令信息。
4. Windows 中文环境中的 CLI JSON 使用 UTF-8，并支持把完整报告原子写入显式文件，避免 Agent 必须依赖 stdout 捕获能力。
5. Agent 可以通过一个通用 CLI 调用英日语言包的五个日常能力，无需编写临时 Python、推断 import 路径或处理 PowerShell 内联引号。
6. `doctor` 报告实际正在运行 LingoTrace 的 Python，而不是把 Microsoft Store stub 路径和当前解释器版本拼成一条假阳性记录；Obsidian per-user 安装位置能被识别。
7. Windows 上自动双 ASR 不再反复尝试不可用的 Apple 引擎；系统必须如实记录当前平台只有一个独立 ASR 引擎，而不能把同一引擎重复运行伪装成独立校验。
8. 现行 `.lingotrace/paths.json` Vault 能通过公共结构校验器；已失效的私有 `codex-skills`/`zsh` 集成不能再作为公开成功路径。
9. Windows 单元测试、真实 PowerShell 入口测试和相邻 ListenKit 端到端测试通过；原有 404 项公共基线继续通过。
10. 文档、Agent Skill、CI 与实现使用同一契约；`CHANGELOG.md` 在全部测试通过后更新。

macOS 专项不在 Windows 主机上冒充完成。所有需要 Apple Silicon、MLX、Apple Speech、TCC 或 macOS Python 环境实测的事项写入交接文档，由 macOS Codex 在同一分支继续验证和实施。

## 2. 证据方法

每条报告结论按以下等级处理：

- **A：本机复现**：在当前 Windows 11 主机真实执行并得到相同结果。
- **B：源码与测试证实**：代码路径明确，且可用隔离测试稳定复现。
- **C：环境特定观察**：只在报告 Agent 的宿主或沙箱成立，不能推广为 LingoTrace 通用事实。
- **D：推断或建议**：尚无执行证据，必须先验证，不能直接转成实现。

实施后，每项结论还要标记为：已修复、已缓解、按设计保留、Agent 边界、macOS 待验证或不采纳。

## 3. 已证实的问题矩阵

| ID | 问题 | 证据 | 决策 |
| --- | --- | --- | --- |
| W-01 | `transcribe_listening.py` 硬编码 `/bin/bash` | A+B：Windows `CreateProcess` 不能启动该路径；源码第一个子进程即失败 | 平台感知生成完整命令；Windows 使用 PowerShell + `.ps1` |
| W-02 | `resolve-listenkit` 无条件返回 `.sh` | A+B：本机报告与源码一致 | 连接解析、验证、返回工件统一按目标平台选择入口 |
| W-03 | 仅把 `/bin/bash` 改为 `which("bash")` 仍不正确 | A：本机 `shutil.which("bash")` 首先命中 `System32\\bash.exe`（WSL launcher），不是 Git Bash；ListenKit `.sh` 又使用 POSIX 运行时布局 | Windows 永不探测或调用 bash；不采用“发现 bash 后继续跑 .sh”方案 |
| W-04 | Windows `os.access(..., X_OK)` 对普通存在文件给出假绿灯 | A+B | Windows 校验文件存在及宿主解释器；POSIX 才检查执行位 |
| W-05 | 文档普遍使用 `python3`，本机命中不可执行的 Store alias | A+B：`python3` exit 9009，`python` 为 3.14.4 | 文档使用 `<python-command>` 并给出平台解析规则；Windows 优先当前可用 `python` |
| W-06 | doctor 的 Python 路径与版本来自两个不同解释器 | A+B | 直接报告 `sys.executable` 与 `sys.version_info`；它们代表已经成功启动当前命令的解释器 |
| W-07 | Windows 默认 stdout 为 GBK/cp936 | A：本机 `sys.stdout.encoding == gbk` | 公共 JSON 输出显式 UTF-8；增加 `--report-json`，文件始终 UTF-8 |
| W-08 | `_run_git(text=True)` 使用本地默认编码 | B | Git 输出显式按 UTF-8 解码，并用替换策略保留可诊断内容 |
| W-09 | doctor 漏检 `%LOCALAPPDATA%\\Programs\\Obsidian\\Obsidian.exe` | A+B：本机安装位置即该路径 | 增加候选与回归测试 |
| W-10 | 默认字典缓存固定为 macOS `~/Library/Caches` | B | Windows 使用 `%LOCALAPPDATA%\\LingoTrace\\Caches`，Linux 使用 `XDG_CACHE_HOME`，保留环境变量覆盖 |
| W-11 | 默认双 ASR 在 Windows 总是选择 Apple Speech | B | `auto` 只选择当前平台真正独立且受支持的第二引擎；Windows 无第二引擎时生成明确的受控单引擎状态 |
| W-12 | 五个日常能力没有公共 CLI | A+B：只能从测试推断 payload 并直接 import | 新增通用、语言包感知的 JSON CLI；保留核心 preview/apply 与写守卫 |
| W-13 | 部分 Agent 无法可靠捕获 PowerShell stdout | C：WorkBuddy 特定限制，但文件读取是共同能力 | CLI 与听力工具提供 `--report-json`；不为 WorkBuddy 写专属适配器 |
| W-14 | `validate_vault_structure.py` 不识别 `.lingotrace/paths.json` | B，且 macOS 报告已实跑复现 | 优先现行 schema，兼容遗留 schema；增加英日现行布局 fixture |
| W-15 | `--run-integrations` 调用不存在的私有 `codex-skills` + `zsh` | B | 公共工具不得调用私有脚本；改为公共、Python 内部可执行的校验或明确移除失效入口 |
| W-16 | `tests/lingotrace/__init__.py` 遮蔽真实包 | macOS A，当前工作树已保存删除；Windows 无 pytest 可复测 | 保留删除；以 macOS 交接复测 pytest，以 unittest 404 项保证当前基线 |
| W-17 | LingoTrace `--engine` 不接受 ListenKit 已支持的 `mlx` | B | 对齐 `auto/faster-whisper/mlx/apple`；平台是否可用由 ListenKit 给出结构化失败 |
| W-18 | 公开错误信息指向不存在的私有 `codex-skills` 自举脚本 | B | 错误信息改为公开工具与文档；Windows 提供可执行的本机 runtime 指引，macOS 自举脚本交接继续完善 |
| W-19 | CI 没有 Windows 行为腿 | B | 增加 Windows Python 3.14 基线 job，执行不依赖 Unix shell 的四组测试与编译检查 |

## 4. 不准确或不采纳的报告建议

### 4.1 “PowerShell 没有 which，所以 doctor 的 which 会失败”

不准确。源码使用 `shutil.which()`，不是 shell 内置命令。真正问题是 PATH 可能不含 Git/Python，以及 doctor 把 `which("python3")` 的路径与 `sys.version_info` 的版本混用。

### 4.2 为 Python、Git、ffmpeg 硬编码 `Python314` 等版本目录

不采纳版本号硬编码。Python 由已经启动 CLI 的 `sys.executable` 表示；Git、ffmpeg、ffprobe 可以在 PATH 之外补充稳定的 Windows 安装根候选，但不能绑定具体 Python 小版本目录。

### 4.3 在 `lingotrace.init` 内清除 `PYTHONHOME` 来修复 TraeWork

不能解决“解释器启动前”发生的 `Failed to import encodings`。Python 进入 `lingotrace.init` 之前已经读取 `PYTHONHOME`；模块代码没有机会修复启动失败。此项属于 Agent 宿主环境边界。项目侧可提供清晰的 launcher 选择说明和 `--report-json`，但不能宣称已修复 TraeWork 的进程环境污染。

### 4.4 为 Antigravity、Claude Code、QwenWork、TraeWork、WorkBuddy 各建适配目录

不采纳。五个 Agent 的共同最小能力是：执行一个命令、读写一个文件、解析 JSON。公共 CLI、平台入口选择和报告落盘比五套容易漂移的专属文档更可靠。回应文档只解释兼容状态，不成为运行期依赖。

### 4.5 在 Windows 重复运行 faster-whisper 作为“双 ASR”

不采纳。同一模型、同一引擎的重复运行不是独立交叉校验。Windows 当前应如实标记“平台只有一个受支持的独立引擎”，保留用户显式指定第二引擎的能力；未来 ListenKit 增加 Windows 第二引擎后，自动策略可直接启用。

### 4.6 修改 `.claude/settings.local.json`

不纳入公共整改。该文件被忽略且属于本机私有配置；公共兼容性不能依赖它，也不应把用户本地权限规则提交到仓库。

### 4.7 仅为兼容性新增 `pyproject.toml`

本轮暂不采用。学习者分发明确使用只包含 `lingotrace/` 的 sparse checkout，当前模块调用契约是从 runtime root 执行。打包化会改变安装、更新和依赖边界，应作为独立设计，不在 Windows 修复中顺带引入。

## 5. 实施设计

### 5.1 公共 JSON 输出

新增一个轻量输出模块，负责：

- 把 stdout 配置为 UTF-8；
- 以同一序列化函数输出 `ensure_ascii=False` 的 JSON；
- 当提供 `--report-json` 时，以 UTF-8 原子写入 Vault 外或用户指定路径；
- 报告路径写入失败时返回明确错误，不静默丢失；
- init CLI、通用工作流 CLI、听力 CLI 复用同一行为。

`--report-json` 是 Agent 兼容层，不是学习数据存储。调用方读取后可删除，LingoTrace 不把它写进 Vault 或复习状态。

### 5.2 通用 Agent 工作流 CLI

计划入口：

```text
<python-command> -m lingotrace.agent <capability> \
  --vault <vault-root> \
  --payload <payload.json> \
  [--apply] \
  [--report-json <report.json>]
```

行为：

1. 从 Vault 的 `.lingotrace/vault-context.json` 解析 `language_pack`，不让 Agent 重复指定语言。
2. 只允许五个公开能力：`listening_notes`、`source_notes`、`review_materials`、`speaking_cards`、`review_rollover`。
3. payload 必须是 JSON object；字段作为关键字参数传给已存在的语言包工作流。
4. CLI 自己注入 `vault_root` 与 `mode`，payload 不能覆盖这两个安全边界。
5. 默认 preview，只有 `--apply` 才应用；核心写守卫、已有文件确认和路径角色校验保持不变。
6. `review_rollover` 的“preview → apply → second preview”仍由 Agent Skill 编排，CLI 不绕过确认语义。

### 5.3 ListenKit 平台入口

公共解析规则：

| 平台 | 必需脚本 | 宿主命令 |
| --- | --- | --- |
| Windows | `cli/generate-markdown.ps1` | `pwsh`，否则 `powershell` |
| macOS/Linux | `cli/generate-markdown.sh` | `bash` |

Windows 命令形状：

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File <generate-markdown.ps1> ...
```

不通过 WSL，不把 `.sh` 当作 Windows fallback。POSIX 分支不假定 bash 4+，但 macOS 最终应由交接任务验证 `shutil.which("bash")` 选择是否符合项目政策。

### 5.4 Windows 工具发现

- Python：当前命令使用的 `sys.executable`，这是唯一已被真实证明能启动 LingoTrace 的解释器。
- Git：PATH；再检查 `%ProgramFiles%\\Git\\cmd\\git.exe`、`%ProgramFiles(x86)%` 和用户级稳定安装根。
- PowerShell：PATH 中 `pwsh` 或 `powershell`；再检查系统 Windows PowerShell 的稳定路径。
- ffmpeg/ffprobe：PATH；再检查 WinGet Links、Scoop shims、Chocolatey bin 等稳定链接目录。
- 不搜索 `Python311`/`Python314` 等版本目录，不遍历整个磁盘。

### 5.5 双 ASR 平台策略

自动策略只选择不同实现的第二引擎：

- macOS：Apple、MLX、faster-whisper 之间按已验证可用性选择；具体优先级由 macOS 交接实测确定。
- Windows/Linux：当前 ListenKit 只有 faster-whisper 可用时，不启动 Apple/MLX；生成 `single_engine_platform` 比较状态和用户可转述说明。
- 显式 `--compare-engine` 保留，调用方明确指定时照常尝试并记录 `secondary_unavailable`。
- `--single-asr` 仍表示用户显式退出校验；它与“平台无第二引擎”在报告中使用不同状态。

### 5.6 Vault 结构校验

现行 schema：

```json
{
  "path_roles": [
    {"role": "listening_root", "relative_path": "listening", "source": "vault_config"}
  ]
}
```

校验器优先读取 `.lingotrace/paths.json`，检查：

- `path_roles` 是列表；
- role 与 relative_path 为非空字符串；
- relative_path 为安全的 Vault 相对路径；
- 每个配置角色目标存在；
- 重复角色被报告；
- 遗留 `roles` object schema 继续兼容，但不再要求现行 schema 具有旧镜像字段。

听力布局和 note 扫描不再硬编码中文根目录，优先使用解析后的路径角色；遗留 Vault 保持旧行为。

`--run-integrations` 不再执行私有脚本。若没有公开等价集成，则该 flag 返回明确的“已移除/请使用公共语言包测试”错误并从文档成功路径删除；更优方案是在本文件内调用公开校验逻辑。

## 6. 文件级改动计划

### 6.1 运行时

- `lingotrace/init/listenkit_connections.py`：平台入口解析、平台有效性、工件返回。
- `lingotrace/init/doctor.py`：真实解释器、Windows 工具候选、Obsidian per-user 路径。
- `lingotrace/init/runtime_updates.py`：共享 Git 解析与 UTF-8 解码。
- `lingotrace/init/__main__.py`：UTF-8 JSON 与 `--report-json`。
- `lingotrace/agent.py`：五能力公共 CLI。
- 可选新增 `lingotrace/core/json_output.py` 与 `lingotrace/init/executables.py`，避免重复实现。

### 6.2 听力与 Vault 工具

- `tools/listening-transcribe-official/transcribe_listening.py`：PowerShell 入口、preflight、mlx 契约、平台缓存、ASR 策略、报告落盘。
- `tools/listening-transcribe-official/setup_offline_dictionary.py`：平台缓存与公开修复指引。
- `tools/vault-structure/validate_vault_structure.py`：现行路径 schema、平台无关集成。
- 删除空的 `tests/lingotrace/__init__.py`。

### 6.3 测试

- `tests/lingotrace/init/`：Windows ListenKit、doctor、UTF-8、report-json。
- `tests/lingotrace/agent/` 或等价测试文件：五能力 CLI、非法 payload、语言解析、preview/apply 边界。
- `tools/listening-transcribe-official/tests/`：Windows 命令、preflight、单引擎平台状态、mlx。
- `tools/vault-structure/tests/`：现行英日 Vault 配置与遗留配置。
- `.github/workflows/japanese-baseline.yml`：Windows job。

### 6.4 文档

- learner/developer onboarding、安装设计、ListenKit 连接、运行时连接、daily update：解释器占位符与平台规则。
- `tools/README.md`、`docs/listening-runtime-isolation.md`：Windows 命令、缓存与公开修复入口。
- 英日 `agent_skills/SKILL.md`：通用 CLI、报告文件、平台 ASR 语义。
- 同目录新增 macOS Codex 交接和五份 Agent 回应。
- 全部完成并测试后更新 `CHANGELOG.md`。

## 7. 验证计划

### 7.1 自动测试

1. `python -m unittest discover -s tests/lingotrace -p 'test_*.py'`
2. `python -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'`
3. `python -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'`
4. `python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'`
5. `python -m compileall -q lingotrace tools/listening-transcribe-official tools/vault-structure`
6. 文档路径与内部链接检查。
7. `bash tools/git/check-public-staged-files.sh`。

### 7.2 Windows 集成测试

1. 建立临时 ListenKit checkout marker，分别验证 Windows 只接受 `.ps1`、macOS/Linux 只接受 `.sh`。
2. 用真实 `pwsh` 和 `powershell.exe` 运行一个隔离的 fake `generate-markdown.ps1`，确认参数含空格/CJK 路径时不破坏。
3. 从真实 `resolve-listenkit` 获取相邻 ListenKit 路径，确认返回 `.ps1`。
4. 生成一段本地合成英语 WAV，通过 LingoTrace → ListenKit → faster-whisper 完整转写；验证 JSON、Markdown、引擎、设备和时间信息。
5. 在临时英语 Vault 运行听力 preview；确认不写 Vault，且 Windows 自动 ASR 状态不是 Apple fallback。
6. 通用 Agent CLI 对五能力各运行至少一个 preview；选择低风险临时 Vault验证一次 apply，再检查写守卫和二次 preview。
7. 在 GBK 父进程环境下验证 stdout 与 `--report-json` 文件均为有效 UTF-8 JSON。
8. 故意隐藏 PowerShell、ffmpeg、ListenKit 入口，确认错误可行动且发生在 preflight。

### 7.3 macOS 交接验证

macOS Codex 必须在同分支完成：

- `.sh` 路径与 bash 选择回归；
- MLX/Apple/faster-whisper 自动第二引擎策略；
- Apple helper 当前失败是否属于 ListenKit；
- Python 3.14 字典 runtime 自举；
- TCC 权限文档；
- 删除 `tests/lingotrace/__init__.py` 后 pytest collection；
- 四组 404 项基线与至少一次真实 MLX 听力链。

## 8. 提交与交付顺序

1. 完成实现与目标测试。
2. 运行四组公共基线和 Windows 真实集成。
3. 写五份 Agent 回应，逐条说明采纳、修正、拒绝和仍待 macOS 验证的内容。
4. 写 macOS Codex 交接，包含当前分支、未完成事项、命令、预期输出和禁止假定的结论。
5. 更新 `CHANGELOG.md`。
6. 审查 staged 文件，只保留公共 allowlist 文件。
7. 运行 `bash tools/git/check-public-staged-files.sh`。
8. 提交专题分支、推送 fork，并按仓库规则创建 PR；若 macOS 工作尚未完成，PR 保持 draft 并在正文注明依赖。

## 9. 风险与回滚边界

- 不修改私人 Vault，不把真实音频或转写产物加入 Git。
- 真实集成测试只在临时目录运行，结束后由临时目录生命周期清理。
- 不修改相邻 ListenKit 仓库；LingoTrace 只能消费其公开入口契约。
- 不删除用户已有分支或未识别改动。
- 不把 Windows 修复包装成 macOS 已验证；macOS 结论以交接后的实测为准。
- 若实际 ListenKit 入口参数与当前 checkout 不一致，停止在契约层修复，不通过 WSL 或私有脚本绕过。

## 10. Windows 实施结果

截至 2026-08-10，W-01 至 W-19 的 Windows 项已按本方案实施；W-16 的 pytest 结论与所有 Apple/MLX/TCC 项仍明确留给 macOS 实机复核。

自动化结果：

| 测试组 | 结果 |
| --- | --- |
| `tests/lingotrace` | 256 passed |
| `tools/listening-transcribe-official/tests` | 105 passed |
| `tools/vault-structure/tests` | 23 passed |
| `tools/architecture-baseline/tests` | 42 passed |
| 合计 | 426 passed |

额外实证：

- Windows 11、CPython 3.14.4、继承 GBK/CP936 console 环境下，CLI stdout 与 `--report-json` 都可作为 UTF-8 JSON 读取。
- 真实 `resolve-listenkit` 返回相邻 ListenKit 的 `cli/generate-markdown.ps1`。
- 真实 ListenKit doctor 识别 faster-whisper 1.2.1、ffmpeg/ffprobe、GTX 1660 SUPER CUDA float16 和已就绪的 `small` 模型。
- 系统合成英文 WAV 在带空格的临时 Vault 内完成 PowerShell → ListenKit → LingoTrace guarded dry-run，最终 `status: complete`；临时目录随后清理。
- 同一实验先后将音频放到 Vault 外、再放到 Vault 内但 `listening_root` 外，两次都在转录前被路径守卫拒绝。这两次失败属于安全契约的正向验证，不是未解决故障。
- Python compileall 与 `git diff --check` 通过。公开 staged allowlist、提交和远端 CI 在最终 Git 收口步骤执行。
