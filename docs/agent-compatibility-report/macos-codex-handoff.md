# macOS Codex 兼容性续作交接

## 1. 接手目标

请在同一分支 `codex/windows-agent-compatibility` 上继续，不要另起不相关分支。Windows 端已经完成实现和验证；你的任务是用真实 macOS 环境验证跨平台行为、修正仅能在 macOS 复现的问题，并把本分支推进到可合并状态。

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

## 3. macOS 必做验证

1. 确认分支和工作树，只提交公开文件；先检查上游 `main` 是否移动。
2. 用真实 launcher 输出 `sys.executable`、`sys.version`、stdout encoding；不要假定 `python3` 一定指向目标解释器。
3. 运行四组 unittest 和 `python3 -m pytest -q`（若 pytest 未安装，记录事实；不要为了过测试污染正式 runtime）。确认删除测试包 `__init__.py` 后收集正常。
4. 在真实已初始化 Vault 上运行 `doctor --report-json`、`resolve-runtime`、`resolve-listenkit`，确认返回 `cli/generate-markdown.sh`，且 Windows `.ps1` 选择未破坏 macOS。
5. 运行 ListenKit 自身 doctor，再用一段位于配置 `listening_root` 内的真实或临时音频做完整 dry-run。路径至少覆盖空格；若可行再覆盖中文或日文字符。
6. 验证默认 Apple ASR 与 faster-whisper 是两个独立候选：一致时完成，不一致时产生稳定 merge request；不得用同一引擎跑两次冒充双 ASR。
7. 显式验证 `--engine mlx` / `--compare-engine mlx` 的透传与错误报告。只有本机 ListenKit 真正支持时才宣称 MLX 可用。
8. 复核 `~/Library/Caches/LingoTrace/...` 与 `~/Library/Caches/jp-listening-dicts` 历史路径保持不变，并验证 TCC/iCloud/原生扩展问题没有被 Windows 分支回归。
9. 用 `--report-json` 验证错误和成功报告都是 UTF-8、原子写入且 exit code 正确。
10. 更新本目录五份 Agent 回应中的“macOS 待验证”段落，记录命令、版本、结果和任何修复。

## 4. 不应采用的修复

- 不要为 Codex、Claude Code、Gemini/Antigravity、QwenWork、TraeWork、WorkBuddy 各复制一套工作流。
- 不要只把 `/bin/bash` 改成 PATH 中第一个 `bash`；Windows 的 `System32\bash.exe` 可能只是 WSL launcher。
- 不要从 LingoTrace 模块内宣称能修复 Python 启动前的 `PYTHONHOME` 污染。
- 不要硬编码 `/opt/homebrew/bin/python3.14`、某个用户名或单一 Cache venv 作为所有用户的入口。
- 不要为了报告好看，把同一 faster-whisper 结果标成双 ASR。
- 不要恢复公开工具对私有 Vault、私有 `codex-skills` 或 `.claude/settings.local.json` 的依赖。

## 5. 完成条件

- macOS 的四组 unittest、可用时的 pytest、真实 ListenKit doctor 和至少一次真实听力 dry-run均有证据；
- 发现的问题已用跨平台公共实现修复，而不是 Agent 专用补丁；
- `CHANGELOG.md`、本交接文档和各 Agent 回应已更新为最终事实；
- `git diff --check`、Python compileall 和 `bash tools/git/check-public-staged-files.sh` 通过；
- 分支已同步最新 canonical `main`，CI 全绿，draft PR 正文包含 Windows 与 macOS 的最终验证矩阵，然后才标记 ready。
