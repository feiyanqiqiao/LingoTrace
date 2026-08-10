# macOS Codex 兼容性完成与后续交接

## 0. 完成状态

macOS 工作已于 2026-08-10 完成。本文件保留 Windows 到 macOS 的原始验收边界，并补充可供后续 review/CI 使用的最终证据。所有项目改动都继续位于 Windows 创建的同一分支 `codex/windows-agent-compatibility`；没有创建第二条 macOS 分支。

GitHub 真值核对结果：接手时远端分支 head 为 `652d97792206ffacb76a154c181861a55c5c006f`，`origin/main` 与 canonical `upstream/main` 都是 `8c118fd`。本地云同步造成的混合状态没有覆盖远端；它被保存为可恢复 stash，Git 对象重新从 GitHub 获取，现有分支再快进到远端 head。

## 1. 接手目标

本工作在同一分支 `codex/windows-agent-compatibility` 上完成。Windows 端实现被保留，macOS 端使用真实环境验证跨平台行为，并只针对有证据的公共产品缺口继续修正。

先完整阅读：

- 本目录 10 份原始兼容性报告；
- [兼容性整改方案](compatibility-remediation-plan.md)；
- 本文；
- 仓库根 `AGENTS.md`；
- 英文、日文语言包各自的 `agent_skills/SKILL.md`。

不要把原始报告当成事实清单。继续使用“源码证据 + 自动化测试 + 真实运行”三级验证，并在结论中区分项目缺陷、宿主 Agent 限制和未证实推测。

## 2. Windows 已完成内容

- 新增 `python -m lingotrace.agent`，为五个语言包 capability 提供统一 preview/apply CLI、字段 allowlist、Vault 语言包解析和 UTF-8 `--report-json`。
- `lingotrace.init` 全部子命令支持 `--report-json`；stdout/stderr 在 GBK/CP936 父环境下仍输出有效 UTF-8 JSON。
- doctor 报告当前 `sys.executable` 与实际版本，补充 Windows 每用户 Obsidian、Git/GitHub CLI/PowerShell/ffmpeg 稳定路径发现。
- ListenKit 解析按平台返回 `.ps1` 或 `.sh`；Windows 原生调用 PowerShell，不使用 `/bin/bash`、WSL 或 Git Bash。
- 听力工具支持 Windows cache、`mlx` 参数透传、UTF-8 子进程、清理子 Python 的 `PYTHONHOME`/`PYTHONPATH`，并在没有独立第二 ASR 时诚实返回 `single_engine_platform`。
- Vault 结构校验优先使用 `.lingotrace/paths.json` 当前 schema，以配置角色限制扫描范围，并用公共 `review_rollover` preview 取代私有 `codex-skills`/`zsh` 集成。
- CI 已增加 `windows-latest` 矩阵；公开 allowlist shell 检查仍只在 Linux job 运行。
- 删除 `tests/lingotrace/__init__.py`，避免 pytest 把源码包与测试包错误合并；请在 macOS 上重点复核。

Windows 11 / CPython 3.14.4 已通过 426 项 unittest。真实链路还验证了：GBK 控制台、含空格路径、每用户 Obsidian、ListenKit PowerShell doctor、faster-whisper 1.2.1、ffmpeg/ffprobe、CUDA GTX 1660 SUPER、临时英文 WAV 转录和受保护 dry-run。Vault 外及 `listening_root` 外输入均被正确拒绝。

## 3. macOS 验证结果

1. 环境：macOS 27.0 arm64；默认 `python3` 为 CPython 3.14.4，stdout UTF-8；`/usr/bin/python3` 为 3.9.6；Bash 3.2.57；ffmpeg/ffprobe 8.1。
2. 自动测试：core 256、listening 112（1 skipped）、Vault structure 23、architecture 42，共 433 项 unittest 通过；pytest 为 432 passed、1 skipped、25 subtests passed。
3. 真实 Vault：`resolve-runtime`、`resolve-listenkit`、`doctor` 都 accepted；ListenKit 入口为 `cli/generate-markdown.sh`；成功/失败 `--report-json` 都能作为 UTF-8 JSON 读取。
4. ListenKit：沙箱外 doctor 报告 `mlx_runtime=ready`、`mlx_metal=ready`、`mlx==0.32.0`、`mlx-whisper==0.4.3`；沙箱内无 Metal 是宿主隔离限制，不是硬件结论。
5. 英语音频：含空格/CJK 路径下，MLX 主 + Apple 副和 Apple 主 + MLX 副都实际成功并 agreed，证实 `--compare-engine mlx` 真实透传。
6. 日语音频：公共 Python 3.14 Cache venv 加载 `fugashi==1.5.2`/`unidic-lite==1.0.8`；MLX/Apple 对一处标点产生稳定 merge request（exit 2），模型审阅后重跑为 `complete`/`merged`（exit 0）。
7. 写入边界：上述听力验证全部使用 dry-run；临时 Vault 的 listening 目录最终只有输入音频。Vault 外输入在转写前 exit 1，并生成结构化错误报告。

## 4. 不应采用的修复

- 不要为 Codex、Claude Code、Gemini/Antigravity、QwenWork、TraeWork、WorkBuddy 各复制一套工作流。
- 不要只把 `/bin/bash` 改成 PATH 中第一个 `bash`；Windows 的 `System32\bash.exe` 可能只是 WSL launcher。
- 不要从 LingoTrace 模块内宣称能修复 Python 启动前的 `PYTHONHOME` 污染。
- 不要硬编码 `/opt/homebrew/bin/python3.14`、某个用户名或单一 Cache venv 作为所有用户的入口。
- 不要为了报告好看，把同一 faster-whisper 结果标成双 ASR。
- 不要恢复公开工具对私有 Vault、私有 `codex-skills` 或 `.claude/settings.local.json` 的依赖。

## 5. 已完成的公共修复

- 新增 `init_listening_runtime.py`，跨平台创建/检查独立 Python 3.14 日语听力 runtime；拒绝同步目录和未知非空目标，清理子进程 Python 污染，委派固定依赖安装与健康检查。
- 修复学习者 sparse checkout：同时分发 `lingotrace/` 和 `tools/listening-transcribe-official/`。此前默认 Vault 虽启用听力 capability，新机 runtime 却没有实际生成器。
- 英日 Skill 统一调用 runtime 内的公共生成器；日语 Skill 使用公共隔离 runtime，不要求 Agent 编写 wrapper 或直接编辑 Vault。
- 文档区分 core Python >=3.11 与日语听力 Python 3.14，给出用户同意边界、最小 macOS TCC 授权、iCloud/OneDrive 边界和可复制命令。
- CI 在现有 matrix 中增加 `macos-latest`；五份 Agent 回应已更新为最终证据。

## 6. PR 前最终门槛

提交前仍按仓库流程执行 compileall、`git diff --check`、staged public allowlist，更新 `CHANGELOG.md`，同步 canonical main，并推送同一分支。创建 draft PR 后等待 Ubuntu/Windows/macOS matrix 全绿，更新 PR 正文的 Windows/macOS 验证矩阵，再标记 ready。任何首次 Speech/TCC 授权仍是用户/宿主边界，不能由 CI 代替。
