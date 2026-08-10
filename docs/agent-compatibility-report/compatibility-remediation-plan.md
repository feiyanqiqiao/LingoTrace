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
| W-18 | 公开错误信息指向不存在的私有 `codex-skills` 自举脚本 | B | 错误信息改为公共跨平台 `init_listening_runtime.py` 与隔离文档；不再依赖私有 wrapper |
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

## 11. macOS 二次证据审计与实施方案

### 11.1 GitHub 与本地真值

2026-08-10 的 macOS 接手先直接查询 GitHub，而不是相信本地分支缓存：

- `origin/codex/windows-agent-compatibility` 的 GitHub head 为 `652d97792206ffacb76a154c181861a55c5c006f`；
- 分支包含 `12bcfc5`（跨平台兼容层）和 `652d977`（按宿主平台选择 ListenKit 测试路径）；
- GitHub 当时没有该分支的 Pull Request，也没有分支级 Actions 运行；workflow 只在 PR 或 `main` push 触发；
- `origin/main` 与 canonical `upstream/main` 都是 `8c118fd`，canonical main 没有在 Windows 交接后移动；
- 本地最初是云同步造成的混合 index/worktree，且 Git 对象不完整。先强制从 GitHub 重取对象，把混合状态保存为可恢复 stash，再将现有分支快进到 `652d977`；没有用混合工作树覆盖 GitHub。

相邻 ListenKit 本地 checkout 的 POSIX 脚本曾被跨设备同步为 CRLF，但 `origin/codex/agent-compatibility-hardening` 的干净 GitHub 克隆是 LF。LingoTrace 的 macOS 集成测试使用该临时干净克隆，不修改相邻仓库，也不把本地 CRLF 污染误判为 LingoTrace 或 GitHub 缺陷。

### 11.2 报告结论复核矩阵

| ID | 报告结论 | macOS 证据 | 最终判断与措施 |
| --- | --- | --- | --- |
| M-01 | 核心 runtime、英日语言包和 init CLI 在 macOS 健康 | A：最终 433 项 unittest 通过；`resolve-runtime`、`resolve-listenkit`、`doctor` 在真实英语 Vault 均 accepted | 已证实；保持现有公共契约 |
| M-02 | 删除 `tests/lingotrace/__init__.py` 可修复 pytest 包遮蔽 | A：最终 `python3 -m pytest -q` 为 432 passed、1 skipped、25 subtests passed | 已证实；保留删除。报告同时建议删除 `tests/__init__.py`，但该文件不受 Git 跟踪，不制造额外删除 |
| M-03 | macOS `resolve-listenkit` 应返回 `.sh` | A：真实报告返回 `cli/generate-markdown.sh`；完整转写成功 | 已证实；Windows `.ps1` 分支没有破坏 macOS |
| M-04 | `/bin/bash` 硬编码脆弱 | B+A：Windows 分支已改为发现 Bash；本机解析 `/bin/bash` 3.2.57，当前 ListenKit 脚本真实可运行 | 已修复；不要求 Bash 4，不把 Homebrew 路径硬编码为所有用户默认 |
| M-05 | Apple Speech 在 macOS 必然失败，默认双 ASR 等价单 ASR | A：真实 MLX 主引擎 + Apple 副引擎、Apple 主引擎 + MLX 副引擎均成功且 agreed | 报告在当前版本已过期/错误；保留两个独立引擎，回应文档记录当前实证 |
| M-06 | `--engine mlx` 契约缺失 | A：Windows 实现已增加；macOS 真实反向组合证实 `--compare-engine mlx` 成功透传 | 已修复并实证 |
| M-07 | 全新 Mac 的 LingoTrace 日语听力词典 runtime 无公开自举入口 | A+B：本机预期 Cache venv 实际不存在；现有文档从一个尚不存在的 venv Python 开始，iCloud 错误仍指向不存在的 `init-listening-runtime.sh` | 已证实；新增公共跨平台 Python 自举器，创建平台 Cache venv、安装 pinned requirements、运行健康检查，不依赖私有 `codex-skills` |
| M-08 | core Python >=3.11 与听力 Python 3.14 是矛盾 | A+B：默认 Python 3.14.4、系统 Python 3.9.6 并存；core 与原生词典扩展的边界不同 | 不是代码矛盾，是双层契约；文档明确 core >=3.11、完整日语听力隔离 runtime 当前固定 3.14 |
| M-09 | macOS 需要完全磁盘访问 | C：当前 Codex 可访问真实 Vault，无 TCC 阻塞；不同宿主首次访问 `Documents` 可能触发 Files and Folders 授权 | 报告措辞过强；文档先说明最小 Files and Folders 授权，Full Disk Access 只作为用户明确接受的故障排查选项 |
| M-10 | `agent_skills/SKILL.md` 未跟踪、公共发布缺入口 | B：英日两个 `lingotrace/packs/*/agent_skills/SKILL.md` 均受 Git 跟踪且真实解析成功 | 报告错误；不新增顶层重复入口 |
| M-11 | `validate_vault_structure.py` 不支持现行 `.lingotrace/paths.json` | A：Windows 实现后，对临时标准英语 Vault及 `--run-integrations` 实跑通过 | 已修复并实证；保留 legacy schema 兼容 |
| M-12 | 五个 capability 无公共 CLI | A：新增 CLI 测试通过；英日 Skill 已引用 provider-neutral 入口 | 已修复；各 Agent 不应复制项目业务逻辑 |
| M-13 | TraeWork 的 `PYTHONHOME` 可由 LingoTrace 模块启动后清除 | B：`Failed to import encodings` 发生在模块加载前 | 报告建议不可实现；子进程环境已清理，宿主首个 Python 进程仍需 Agent/用户选择干净 launcher |
| M-14 | macOS CI 缺失 | B：Windows 分支矩阵只有 Ubuntu 与 Windows | 已证实；在同一 matrix 增加 `macos-latest`，让纯公共基线持续回归 |
| M-15 | JSON 文件输出、路径空格/CJK 与 dry-run 未证实 | A：成功和失败报告均为 UTF-8 JSON；临时 Vault、音频与报告路径同时覆盖空格和中文；dry-run 后 Vault 只保留输入音频 | 已证实；把命令、exit code 和边界写入交接与回应 |
| M-16 | 学习者 sparse runtime 可直接执行听力 Skill | B：安装协议只取 `/lingotrace/`，但 Skill 所需生成器位于 `/tools/listening-transcribe-official/`；默认 Vault 又启用 `listening_notes` | 已证实为新机阻断级缺口；sparse 分发同时包含 core 与公开听力适配器，不把业务逻辑复制到各 Agent |

### 11.3 macOS 剩余实现范围

本阶段只实现以下仍有真实缺口的公共能力：

1. 新增 `tools/listening-transcribe-official/init_listening_runtime.py`：
   - 用实际运行验证选择 Python 3.14 bootstrap；
   - 默认 runtime 为 macOS `~/Library/Caches/LingoTrace/venvs/cpython-314`、Windows `%LOCALAPPDATA%\\LingoTrace\\venvs\\cpython-314`、Linux XDG cache；
   - 在创建 venv 前拒绝同步目录和不安全目标，不删除或重建未知现有环境；
   - 清理传给子 Python 的 `PYTHONHOME`/`PYTHONPATH`，固定 UTF-8；
   - 创建 venv 后调用公开 `setup_offline_dictionary.py --install`，再执行同一健康检查；
   - 提供 `--check`、`--dry-run`、`--runtime-dir` 与 `--bootstrap-python`，使 Agent 不需要写自己的 shell wrapper。
2. 更新 `setup_offline_dictionary.py` 和听力错误消息，所有修复指引只指向公共自举器与公共文档；删除测试中未使用的私有 wrapper 路径常量。
3. 更新安装、隔离和学习者文档：明确双层 Python 契约、可复制的自举/检查命令、Xcode Command Line Tools 条件、最小 TCC 授权与 iCloud 边界；修正 sparse checkout，同时分发 `lingotrace/` 和公开听力适配器。
4. GitHub Actions matrix 加入 `macos-latest`，不复制 macOS 专属 workflow。
5. 为公共自举器增加隔离单测，覆盖三平台默认路径、3.14 拒绝、已有环境复用、创建命令、安装/检查委派、iCloud 拒绝和污染环境清理。
6. 完成后更新五份 Agent 回应、macOS 交接、本文实施结果与 `CHANGELOG.md`。

### 11.4 macOS 验收边界

必须全部满足：

1. 四组 unittest 与 pytest 通过；compileall、`git diff --check`、公开 allowlist 通过。
2. 真实 `resolve-runtime`、`resolve-listenkit`、`doctor` 的 stdout 和 `--report-json` 均是 UTF-8。
3. 沙箱外 ListenKit doctor 显示 MLX/Metal ready；沙箱内无 Metal 只能记为宿主限制，不能覆盖物理机证据。
4. 一段无私人内容的临时音频完成：
   - auto/auto：MLX 与 Apple 独立比较；
   - Apple 主引擎 + MLX 副引擎：证实显式 MLX 比较透传；
   - 空格/CJK 路径；
   - core preview accepted，真实 Vault零写入。
5. Vault 外输入在转写前退出 1，并同时写出结构化 error report。
6. 公共自举器在临时 Cache runtime 完成真实创建、依赖安装与健康检查；随后默认/显式检查均可重复通过。若依赖下载受网络限制，必须保留自动测试并明确外部阻塞，不能宣称物理安装完成。
7. 本阶段不修改私人 Vault、不提交音频/模型/venv、不修改相邻 ListenKit 源码。

### 11.5 交付顺序

1. 先提交公共自举器、测试、CI 与文档修正。
2. 运行自动测试和真实 macOS 自举/E2E。
3. 仅在结果确定后更新 `CHANGELOG.md`、本方案、macOS 交接和五份回应。
4. 审查 `origin/main...HEAD` 仅含公共 allowlist 文件；从最新 canonical main 更新分支。
5. 推送同一分支，创建 draft PR，等待 Ubuntu/Windows/macOS matrix 全绿；再补充最终验证矩阵并标记 ready。

### 11.6 macOS 实施结果

代码与文档范围已经按 11.3 完成，并额外修复 M-16 的 sparse runtime 分发缺口。公共初始化器先在隔离单测中覆盖三平台路径、错误版本、创建/复用、污染环境和同步目录拒绝；随后在真实默认 macOS Cache 路径创建 Python 3.14.4 venv，安装 `fugashi==1.5.2`、`unidic-lite==1.0.8`，样例返回 `公園⓪ / 散歩⓪ / し⓪`，重复 `--check` 仍通过。

提交快照还被重新克隆到全新临时目录，并逐条执行学习者协议中的 non-cone sparse checkout。结果同时存在 `lingotrace/__init__.py`、公共 `transcribe_listening.py` 和 `init_listening_runtime.py`，根 `tests/lingotrace` 未检出，工作树干净；因此 M-16 不是只靠文档字符串测试宣称修复。

最终自动测试：

| 测试组 | 结果 |
| --- | --- |
| `tests/lingotrace` | 256 passed |
| `tools/listening-transcribe-official/tests` | 112 passed，1 skipped |
| `tools/vault-structure/tests` | 23 passed |
| `tools/architecture-baseline/tests` | 42 passed |
| pytest 全仓 | 432 passed，1 skipped，25 subtests passed |

真实日语 E2E 使用 `say -v Kyoko` 生成无私人内容音频，再转换为位于临时日语 Vault `listening_root` 内的 WAV。MLX 与 Apple 对同一句只产生逗号差异，第一次运行返回稳定 merge request 和 exit 2；按 Skill 契约生成临时 reviewed transcript 后重跑，得到 `status: complete`、`asr_validation_status: merged`、`merge_model: gpt-5`、preview accepted 和 exit 0。报告、Vault 与音频路径均包含空格/CJK；最终 Vault 未出现任何 dry-run 工件或笔记。

这组结果纠正了“macOS Apple ASR 必然失败”“双 ASR 实际只是单引擎”和“Agent Skill 未公开”等报告结论，也确认首次 Speech/TCC 授权仍属于宿主用户边界。项目提供最小权限和失败诊断，不静默扩大权限。
