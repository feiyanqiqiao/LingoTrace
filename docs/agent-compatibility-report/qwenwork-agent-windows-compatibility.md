# Agent 运行兼容性报告（Windows · 千问办公）

审计日期：2026-08-10
审计对象：本仓库（LingoTrace 运行时），由学习 Vault `C:\Users\jiezhengj\Documents\Obsidian\LingoTrace-English` 经 `.lingotrace/runtime-connections/windows.json` 绑定。

> 落位说明：本报告位于 `docs/agent-compatibility-report/qwenwork-agent-windows-compatibility.md`，符合本仓库公共白名单（`docs/` 在允许列表内）。同目录另有其他 Agent 撰写的报告（workbuddy / traework 前缀）；本文件是**千问办公（QwenWork）**的独立审计报告。双方对听力链 `/bin/bash` 硬编码与 `.sh` 入口契约问题结论一致；本报告额外覆盖：双 ASR 次引擎在 Windows 被选为 macOS 专属 apple 的契约两难（P2）、`ensure_ascii=False` JSON 输出与 `_run_git` 的 gbk 编码风险（P3）、五个日常能力缺通用 agent 调用契约（P4）、doctor 漏检 `%LOCALAPPDATA%\Programs\Obsidian` 官方默认安装位（P5）、CI 无 Windows 矩阵（P7）。

## 我是谁

我是千问办公（QwenWork），运行在用户这台 Windows 设备上的桌面智能体，也是这个 LingoTrace-English 学习 Vault 的日常驱动者：按照 Vault 根 `AGENTS.md` 与 `lingotrace/packs/english/agent_skills/SKILL.md` 的约定，为用户完成听力素材、来源笔记、复习卡、口语卡、复习结算和看板维护等学习任务。所有写操作都通过本运行时的 core 写守卫与英语包能力进行。

本次审计中我的执行环境：

- Windows 11（10.0.26220），shell 为 bash 风格（Git Bash），可另行调用 powershell.exe；
- Python 3.14.4（`C:\Users\jiezhengj\AppData\Local\Programs\Python\Python314\python.exe`，无 py launcher）；
- git 2.55.0、gh、ffmpeg/ffprobe 9.0、yt-dlp 2026.07.04 均在 PATH；
- GPU 为 GTX 1660 SUPER，ListenKit CUDA 运行时已就绪；
- 管道捕获时 stdout 默认编码实测为 `gbk`。

## 结论摘要

文本学习链路（Vault 初始化、运行时/ListenKit 连接解析、doctor、复习材料、复习结算、来源笔记）在我这里可驱动。**听力链路在 Windows 上完全不可用**（阻塞级），另有编码、能力调用契约与依赖探测三类问题。详见下文，全部为 2026-08-10 实测。

## 审计方法与证据分级

为避免夸大，明确区分两类证据：

**真实执行（实跑取得）**

- `python -m lingotrace.init resolve-runtime / resolve-listenkit / doctor`，JSON 输出逐字段核对。
- 五个日常能力 preview 模式真跑（2026-08-10 补测）：`review_rollover`、`source_notes`、`listening_notes`、`speaking_cards` 均 `accepted=true`、`changed_files=[]`、`planned_writes` 路径正确；`review_materials` 实测触发链接守卫，以结构化错误 `missing_source_note_target` 拦截（其接受路径由上游单测 `test_review_materials_item_creates_initialized_focus_vocab_card` 覆盖）。
- ListenKit 端到端转写真跑（补测）：经 `python -m listenkit_cli generate-markdown` 对 8 秒合成英语语音转写成功，`engine=faster-whisper`、`device=cuda`、`compute_type=float16`、`timing_complete=true`，转写文本准确——**证明 P1 建议方案在 Windows 实际可行**。
- 针对性复现实验：`/bin/bash` 子进程 FileNotFoundError、管道 stdout 默认 `gbk`、运行时根外执行 ModuleNotFoundError、`python <脚本>` 方式 cwd 不进 `sys.path`（必须 PYTHONPATH 或 `-m`）。

**代码审计（未端到端执行）**

- `transcribe_listening.py` 完整听力流程（双 ASR 编排、llm_merge 往返）：失败结论基于根因复现 + 代码路径分析，不是整链实跑。
- `check-update` 网络路径：当日状态文件已存在，为不消耗日检标记未重复执行。
- `apply-update`：fork checkout 按设计拒绝，不应执行。

## 对我这个 Agent 的兼容性（Codex 出身盘点）

本运行时最初围绕 Codex 开发（README/operator-manual 以"Codex 或兼容 AI agent"表述），但对非 Codex agent 的兼容面是明确且有测试守护的：

**兼容面（我可以直接使用）**

- llm_merge 契约 provider-neutral：英语包 SKILL.md 明文 "whether the caller is Codex, Gemini, or another compatible agent"，不要求 provider 专用 API——与我的能力完全匹配（读 JSON、模型判断、回填模板、带参重跑）。
- `docs/getting-started.md` 明确列举可接入 Agent（含 QoderWork 等通用桌面 agent）；Vault 根 AGENTS.md 即我的实际入口，无需 `.claude/` 或专用适配器。
- 架构基线测试（`test_public_entry_contract.py`）强制公共 SKILL.md 不得引用 `codex-skills/`——通用面有回归守护。

**Codex 出身残留（对我构成障碍或噪音）**

- 三处引用私有 `codex-skills/` 脚本：`setup_offline_dictionary.py:203`（错误提示指向公开仓库中不存在的脚本）、`validate_vault_structure.py:174`（zsh + 私有脚本，Windows 必挂）、`transcribe_listening.py:271`（指向 Vault 内日语私有技能）。
- 根目录 `agent-skills/` 为空壳（仅 .DS_Store 与 .pyc 残留），真正入口在语言包内——新 agent 易被误导。
- 五个能力无 CLI：我必须自写 Python 并处理 `sys.path`（已实测可用，但调用姿势无任何官方文档，见 P4）。

## 问题清单

### P1（阻塞）听力转写链在 Windows 第一步即断：硬编码 /bin/bash

- `tools/listening-transcribe-official/transcribe_listening.py` 第 645–658 行：调用 ListenKit 的命令为 `["/bin/bash", str(script_path), ...]`。
- 同文件第 456–457 行 `listenkit_generate_markdown_script_path()` 固定返回 `cli/generate-markdown.sh`；第 451–452 行对 ListenKit 根的有效性判据也要求该 `.sh` 存在。
- 实测：Windows 上 Python `subprocess.run(["/bin/bash", ...])` 抛 FileNotFoundError（即使本机装有 Git Bash，Win32 CreateProcess 也无法解析 `/bin/bash`）。
- 后果：SKILL.md「Listening Notes」全流程（精听稿、泛听笔记、音频切片、双 ASR 校验、llm_merge 流程）在本机全部不可执行，而听力是英语包的核心能力之一。

### P2（阻塞）双 ASR 默认契约在 Windows 上不可满足

- 第 1889–1890 行：`compare_engine == "auto"` 且主引擎为 faster-whisper 时，次引擎被选为 `"apple"`。
- apple 引擎是 macOS 专属（ListenKit 在 Windows 上对其明确报错）。
- SKILL.md 要求默认双 ASR、仅用户显式要求才可 `--single-asr`，且次引擎回退必须向用户报告。
- 后果：即使修复 P1，Windows 上每次听力任务的次引擎都必然失败回退，agent 永远处于"违反 SKILL.md 或反复向用户报降级"的两难。需要一个明确的平台策略。

### P3（高）JSON 输出与 git 子进程的编码风险

- `lingotrace/init/__main__.py` 第 123 行以 `ensure_ascii=False` 打印含中日文的报告；本机管道 stdout 默认编码实测为 `gbk` —— 输出含 CJK 字符时存在 UnicodeEncodeError 风险（我目前靠 `PYTHONUTF8=1` 规避，实测有效）。
- `lingotrace/init/runtime_updates.py` 第 603–610 行 `_run_git()` 使用 `subprocess.run(text=True)` 且未指定 encoding；上游日语提交说明经 gbk 解码会乱码甚至解码失败。
- CI workflow 自己设置了 `PYTHONUTF8: "1"`，但面向 agent/用户的文档没有任何 Windows 编码指引。

### P4（中）五个日常能力没有面向通用 agent 的稳定调用契约

- `listening_notes / source_notes / review_materials / speaking_cards / review_rollover` 均无 CLI 入口，只能由 agent 自行编写 Python 代码 `import lingotrace.packs.english.workflows` 调用。
- 实测（补测）：该调用姿势可行——五个能力 preview 全部按契约返回结构化 JSON；但存在未文档化的坑：`python <脚本路径>` 方式执行时 cwd 不进 `sys.path`（ModuleNotFoundError），必须显式 `PYTHONPATH=<运行时根>` 或用 `python -m`。
- 实测 `python -m lingotrace.init` 在运行时根之外执行即 ModuleNotFoundError（包未安装、无 pyproject/requirements）；也没有文档告诉通用 agent 应如何设置工作目录/PYTHONPATH、构造 payload、走 preview→apply。
- 我靠阅读 `tests/lingotrace/packs/test_english_pack.py` 才拼出 payload 形状；对任何新接入的 agent 这都是高门槛且易错的。

### P5（中）doctor 找不到默认安装的 Obsidian Desktop

- `lingotrace/init/doctor.py` 第 230–234 行：Windows 候选仅有 `%LOCALAPPDATA%\Obsidian\Obsidian.exe`、`ProgramFiles`、`ProgramFiles(x86)` 与 `which("obsidian")`。
- 本机 Obsidian 实际安装在 `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe` —— 这是 Obsidian 官方 per-user 安装器的默认位置。
- 实测 doctor 因此报 `obsidian_desktop_not_found` 警告，会诱导 agent 向用户建议"安装 Obsidian"，属于误报。

### P6（信息）本机 checkout 为个人 fork，运行时自更新不可用（设计使然）

- 当日 `check-update` 写入的状态文件 `.lingotrace/runtime-update-checks/windows.json` 实测记录 `checkout_type=fork`、`result=fork_up_to_date`（我未重复执行该命令，以免消耗当日检查标记）。
- 我遵守规则：不会对本 fork 执行 pull/merge 等操作，仅在用户询问时提示其在开发工作区手动同步上游。列在此处只为让维护者知晓 agent 侧的实际行为。

### P7（低）其他平台残留与 CI 覆盖缺口

- `tools/vault-structure/validate_vault_structure.py --run-integrations` 依赖 `zsh` 与未公开脚本，Windows 不可用（不带该 flag 时无碍）。
- `setup_offline_dictionary.py` 的默认词典缓存为 `~/Library/Caches/...` macOS 路径（日语工具，英语包不受影响）。
- CI 仅 `ubuntu-latest`，无 Windows 矩阵：本报告的 P1–P3 都属于上游测试未覆盖区。

## 我的需求

1. 在 Windows 上能完成听力任务：至少 faster-whisper 单引擎 + 音频切片的完整路径可执行。
2. 一个明确的"Windows 双 ASR 不可满足"的官方策略与话术，使我既不违反 SKILL.md 也不必每次都向用户报错。
3. CLI/JSON 交互在中文 Windows 下无编码陷阱（或文档明确 `PYTHONUTF8=1` 为必选调用姿势）。
4. 五个日常能力有一份面向通用 agent 的调用说明（工作目录/PYTHONPATH、payload 最小示例、preview→apply 流程），最好有 CLI。
5. doctor 的依赖探测结果可信，不产生误导性警告。

## 建议方案

1. **P1**：`invoke_listenkit()` 增加平台分支——Windows 上改为 `[sys.executable, "-m", "listenkit_cli", "generate-markdown", ...]`（cwd 设为 ListenKit 根或注入 PYTHONPATH），或经 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File cli\generate-markdown.ps1` 调用。ListenKit 官方已提供跨平台 `python -m listenkit_cli` 与原生 `.ps1`，并在其 LLM_INTEGRATION.md 明确"Windows 不走 .sh"。**补测已实跑验证**：`python -m listenkit_cli generate-markdown` 在本机对合成语音端到端转写成功（CUDA float16、timing_complete=true），该方案落地即可用。ListenKit 根有效性判据（第 451 行）同步放宽为"存在 `cli/generate-markdown.sh` 或 `listenkit_cli` 包"。
2. **P2**：在 `effective_compare_engine()`（第 3454 行）或其上游增加平台感知：Windows 上自动降级为单引擎，并把降级原因写入报告（第 1916 行已有次引擎错误捕获结构可复用）；同时在英语包 SKILL.md 中写明"Windows 当前为单引擎 + 显式降级报告"，消除 agent 的契约两难。
3. **P3**：`__main__.py` 打印前执行 `sys.stdout.reconfigure(encoding="utf-8")`（Python ≥3.7 可用）；`_run_git()` 显式传 `encoding="utf-8"`；并在 README/agent 文档中注明 Windows 调用建议带 `PYTHONUTF8=1`。
4. **P4**：为五个能力增加 CLI（如 `python -m lingotrace.workflows <capability> --payload-json ...`，沿用现有 preview/apply + JSON 报告风格）；短期替代方案是在 `docs/` 增加一篇 "generic agent invocation recipe"，给出可直接复制的最小调用示例。
5. **P5**：`_find_obsidian()` 的 Windows 候选加入 `%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`（官方默认安装位置），可选再探测 Microsoft Store 包位置。
6. **P7**：CI 增加 `windows-latest` 矩阵（至少 compileall + `tests/lingotrace` 纯逻辑用例），把 Windows 回归纳入上游。

## 已验证可用的部分（避免误解）

- `python -m lingotrace.init resolve-runtime / resolve-listenkit / doctor` 均实测成功，JSON 契约清晰（带 `PYTHONUTF8=1`）。
- `resolve-listenkit` 经设备共享连接（`%LOCALAPPDATA%\LingoTrace\connections\listenkit.json`）正确解析到 `C:\Users\jiezhengj\Documents\Project\ListenKit`。
- doctor 正确识别 python / git / gh / listenkit / runtime，仅 Obsidian 误报（见 P5）。
- 每日更新状态机在 Windows 正常工作（`fork_up_to_date`，每本地日一次）。
- Python 3.14.4 同时满足 ≥3.11 与听力链 3.14 两档要求；git/ffmpeg/ffprobe/yt-dlp 全部就绪。
- 补测：五个日常能力 preview 模式我可真实驱动（4/5 accepted、changed_files=[]，review_materials 守卫契约实测生效）；`python -m listenkit_cli` 端到端转写实测成功——即"文本链 + ListenKit 原生入口"组合在我这里完全可用，缺的只是本仓库听力编排层的平台分支（P1/P2）。

—— 千问办公（QwenWork），2026-08-10
