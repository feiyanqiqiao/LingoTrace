# Agent 运行兼容性报告（macOS · 千问办公）

审计日期：2026-08-10
审计对象：本仓库（LingoTrace 运行时），由学习 Vault `/Users/jiezhengj/Documents/Obsidian/LingoTrace-English` 经 `.lingotrace/runtime-connections/macos.json` 绑定。

> 落位说明：本报告位于 `docs/agent-compatibility-report/qwenwork-agent-macos-compatibility.md`，是千问办公（QwenWork）在 macOS 上的独立审计报告，与同目录 `qwenwork-agent-windows-compatibility.md`（同一 Agent 的 Windows 报告）互补。本报告为纯新增文档，未修改任何代码，未提交任何 git 变更。本次审计新发现：**P1 `validate_vault_structure.py` 与现行标准 Vault 布局（`.lingotrace/paths.json`）不兼容，实跑即崩**；其余为既有问题在 macOS 侧的复核与补充。

## 我是谁

我是千问办公（QwenWork），一个运行在用户这台 Mac 上的桌面 Agent 框架，也是这个 LingoTrace-English 学习 Vault 的日常驱动者之一：按照 Vault 根 `AGENTS.md` 与 `lingotrace/packs/english/agent_skills/SKILL.md` 的约定，为用户完成听力素材、来源笔记、复习卡、口语卡、复习结算等学习任务，所有写操作通过本运行时的 core 写守卫与英语包能力进行。

本次审计中我的执行环境：

- macOS 27.0（arm64，Apple Silicon），默认 shell 为 zsh，我以子进程方式执行 bash/zsh/python3/git 命令并捕获 stdout/stderr；
- Python 3.14.4（python.org 安装，`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`，为默认 `python3`），另有 Homebrew python3；
- git、ffmpeg/ffprobe、yt-dlp 均在 PATH（后三者经 Homebrew 安装）；
- ListenKit 托管运行时已就绪（`~/Library/Caches/ListenKit/venvs/cpython-314`，MLX/Metal ready），由 `resolve-listenkit` 成功解析。

我不是 OpenAI Codex CLI：没有 `~/.codex` 生态，不消费 Codex 技能打包格式，也不依赖任何 Codex 专属审批 API。我的审批/确认流程靠自身的用户交互能力实现，与本仓库 AGENTS.md 的行为契约（先描述计划、征得确认、preview→apply）天然匹配。

## 结论摘要

**总体结论：千问办公在 macOS 上可完整驱动本运行时的文本学习链路与日常运维入口，无阻塞级问题；听力链路在本机可启动入口、其下游 ListenKit 已实跑端到端成功，但听力链的"全新机器自举"仍有既有缺陷（P5）。** 另实跑发现一个新的工具级缺陷 P1（Vault 结构校验器与现行布局脱节）。macOS 平台侧无任何阻塞项——此前 Windows 报告中的 P0/P1（`/bin/bash` 硬编码、`.sh` 入口契约、gbk 编码）在 macOS 上均不成立。

## 审计方法与证据分级

**真实执行（2026-08-10 实跑取得，均在本机）**

- `python -m lingotrace.init resolve-runtime --vault <真实 Vault>`：`accepted=true`，正确解析出 runtime_root 与英语包 SKILL.md。
- `doctor --language english`：`accepted=true`，0 errors、0 warnings。
- `check-update`：常规路径命中 `already_checked_today`；`--force` 走真实远端路径，正确识别 `checkout_type=fork`，与 upstream 对比（`fork_up_to_date`，heads 均为 8c118fd），状态写入仅落在审计用临时 Vault，未消耗真实 Vault 的当日标记。
- `apply-update` 预览：按设计以结构化错误 `fork_update_requires_user_action` 拒绝自动更新个人 fork——与 Vault 根 AGENTS.md 第 7 条一致，行为正确。
- `resolve-listenkit`：解析到 `/Users/jiezhengj/Documents/Project/ListenKit`，入口 `cli/generate-markdown.sh`。
- 五个日常能力 preview 真跑（仓库根直接 import `lingotrace.packs.english.workflows`）：`listening_notes`、`source_notes`、`review_rollover` 一次通过；`speaking_cards`、`review_materials` 经结构化校验错误（`invalid_artifact_body`、`missing_field: ipa/meaning_zh`）逐步补全后 `accepted=true`，`planned_writes` 路径全部落在正确角色目录，`changed_files=[]`。
- 全量测试（CI 同款命令）：`tests/lingotrace` 244 个、`tools/listening-transcribe-official/tests` 100 个、`tools/vault-structure/tests` 18 个、`tools/architecture-baseline/tests` 42 个，共 **404 个全部通过**。
- `bash tools/git/check-public-staged-files.sh --range HEAD~1...HEAD`：通过。
- `transcribe_listening.py --help`：入口可启动。
- **缺陷复现**：`python3 tools/vault-structure/validate_vault_structure.py --vault-root <真实 Vault>` 实跑抛 `RuntimeError: paths.json was not found`（详见 P1）。

**代码审计（未端到端执行）**

- 听力转写全链（双 ASR 编排、llm_merge 往返）未整链实跑：其下游 ListenKit 已由本次审计在同一台机器上端到端实跑成功（见姊妹报告 `ListenKit/docs/agent-compatibility-report/qwenwork-agent-macos-compatibility.md`），本仓库侧入口已验证可启动。
- `connect-runtime` / `vault` 初始化的 apply 路径未执行（会写 Vault/连接文件，超出兼容性审计范围；其预览/解析路径已有上游单测覆盖）。

## 对我这个 Agent 的兼容性（Codex 出身盘点）

本运行时最初围绕 Codex 开发，但对非 Codex agent 的兼容面是明确且有测试守护的，我在 macOS 上全部直接可用：

**兼容面（我可以直接使用）**

- 接入面是纯行为契约：Vault 根 `AGENTS.md` + `resolve-runtime` + 语言包 `SKILL.md`，无任何 Codex 专属工具名、权限文件或审批 API。`.claude/` 目录为本地私有残留，我无需也不应消费它。
- llm_merge 契约 provider-neutral：英语包 SKILL.md 第 101 行明文 "whether the caller is Codex, Gemini, or another compatible agent"——我属于 "another compatible agent"，完全满足。
- `docs/getting-started.md:31` 官方列举可接入通用桌面 Agent；架构基线测试（`tools/architecture-baseline/tests/test_public_entry_contract.py`）强制公共 SKILL.md/AGENTS.md 不得引用私有 `codex-skills/`，通用面有回归守护。
- 所有命令输出统一 JSON 报告（`CommandReport`），我能稳定解析 stdout——macOS 默认 UTF-8，不存在 Windows 侧的 gbk 编码风险。
- AGENTS.md 的确认契约（第 39 行）与 preview→apply 二段式（复习结算）可由我的用户交互能力直接实现。

**Codex 出身残留（构成障碍或噪音）**

- 三处运行期引用私有 `codex-skills/` 脚本（公开 checkout 不存在）：`transcribe_listening.py:271`、`setup_offline_dictionary.py:203`（错误修复指引指向私有脚本）、`validate_vault_structure.py:174`（仅 `--run-integrations` 时触发）。
- 根目录 `agent-skills/` 为空壳（仅 .DS_Store 与 .pyc 残留），真正入口在 `lingotrace/packs/*/agent_skills/SKILL.md`——新 agent 易被误导（本次我依靠 Vault 根 AGENTS.md 指引未受影响）。
- 五个日常能力无 CLI：我需自行编写 Python 并保证在仓库根执行（实测可用，但调用姿势无官方文档，见 P2）。
- 分支命名示例 `codex/<topic>` 仅存在于文档示例，无功能影响。

## macOS 平台兼容性

平台侧无阻塞项，且若干设计在 macOS 上是加分项：

- 平台判定：`runtime_connections.py:14-29` 将 darwin 归一为 macos，连接文件按平台分存，跨平台互不污染。
- `/bin/bash` 硬编码（`transcribe_listening.py:645-658`）在 macOS 原生成立；ListenKit 入口 `.sh` 在 macOS 是正确形态。
- 双 ASR 副引擎 `apple`（Apple Speech，`transcribe_listening.py:1889-1890`）为 macOS 专属优势。
- 设备级连接路径 `~/Library/Application Support/LingoTrace/...`、doctor 推荐路径、Obsidian 探测（`/Applications/Obsidian.app`）均为 macOS 正确形状。
- 全链路 UTF-8 输出（`ensure_ascii=False`）在 macOS 终端无风险。
- 风险小项：工作树散落 `.DS_Store`（已被 .gitignore 兜底，但遍历目录的代码未过滤它）；无显式大小写不敏感文件系统防护（当前布局不受影响）。

## 问题清单

### P1（缺陷，本次新发现）`validate_vault_structure.py` 与现行标准 Vault 布局不兼容，实跑即崩

**现象**：对标准英语 Vault（`lingotrace.init vault --language english` 产物）运行 `python3 tools/vault-structure/validate_vault_structure.py --vault-root <vault>`，直接抛 `RuntimeError: paths.json was not found`。

**根因**（`tools/vault-structure/validate_vault_structure.py:93-102`）：`find_paths_config` 只搜索三个遗留中文布局候选——`系统配置/paths.json`、`学习系统/系统/配置/paths.json`、`学习系统/系统配置/paths.json`，不搜索现行的 `.lingotrace/paths.json`。即便找到也不兼容：`validate_roles`（第 105-120 行）期望 `roles` 字典 + `base_vocab_root`/`daily_notes_root` 镜像字段的旧 schema，而现行 Vault 的 `.lingotrace/paths.json` 是 `path_roles` 数组 schema（角色对象列表，source 标注 vault_config）。

**影响**：任何 agent（不限框架与平台）对现行布局 Vault 运行这个公开维护工具都会失败；该工具的 18 个单测全过，说明测试 fixture 停留在旧布局，工具与产品现状脱节且无回归守护。

**我的需求**：作为日常驱动 Vault 的 agent，我需要一个能对现行布局给出可信"结构健康"结论的校验入口，否则我无法在结构漂移时自检。

**建议方案**：`find_paths_config` 增加 `.lingotrace/paths.json` 候选并适配 `path_roles` schema（角色名→relative_path 映射），保留旧 schema 兼容；或若该工具已废弃，请在 `tools/README.md` 明确标注并给出替代入口。同时为该测试组补一个现行英语 Vault 布局的 fixture，防止再次脱节。

### P2（集成契约）包未安装化、五个能力无 CLI，agent 调用姿势靠口口相传

**现象**：无 `pyproject.toml`/`setup.py`，`python -m lingotrace.init` 必须在仓库根执行（否则 ModuleNotFoundError）；五个日常能力只能靠 agent 自行 import `lingotrace.packs.english.workflows` 并处理 `sys.path`（我已实测可行）。

**影响**：对具备 shell 能力的 agent（包括我）可用但无官方文档背书；对无法自由执行 shell 的 agent 则完全不可用。Windows 版报告亦提出同一问题（P4）。

**我的需求**：一个稳定、可发现、平台无关的能力调用契约，不依赖"恰好在仓库根执行"这种隐性前提。

**建议方案**：短期在 SKILL.md 或 `tools/README.md` 明文写出"仓库根执行 + import 姿势"的官方调用示例；中期提供 `pyproject.toml` 与 `console_scripts`（如 `lingotrace`），并把五个能力纳入 `python -m lingotrace <capability>` 子命令面。

### P3（测试人体工学）pytest 直接跑会失败；`tests/lingotrace/__init__.py` 删除未提交

**现象**：无 PYTHONPATH 配置，`pytest tests/` collection 报 ModuleNotFoundError；官方姿势是 `python -m unittest discover`（CI 同款）。antigravity-macos 报告建议的修复（删除错放的 `tests/lingotrace/__init__.py`）目前只存在于工作树（`git status` 显示 ` D tests/lingotrace/__init__.py`），未提交。

**我的需求**：agent 做回归验证时能以最常见姿势（pytest）一键跑通，减少试错。

**建议方案**：提交该删除；如需兼容 pytest，添加最小配置（pyproject 中 `[tool.pytest.ini_options] pythonpath = ["."]` 或 pytest.ini）。

### P4（CI 覆盖）CI 仅 ubuntu-latest，macOS 行为零覆盖

**现象**：`.github/workflows/japanese-baseline.yml:21` 与 `public-file-allowlist.yml` 均只跑 ubuntu；macOS 上的行为（含本报告的 404 测试结论）纯靠各 agent 本机实测背书。

**建议方案**：为 `japanese-baseline` 增加 `macos-latest` 矩阵腿（测试本身纯标准库、无外部依赖，成本极低）；若资源受限，至少保持一份"最近一次 macOS 实测"的机制（本目录的报告即承担此职能）。

### P5（听力链，复核既有问题）全新机器自举指引指向私有脚本；Python 版本双契约

**现象**：听力链失败时的修复指引指向私有 `codex-skills/` 脚本（`transcribe_listening.py:271`、`setup_offline_dictionary.py:203`），公开 checkout 无此脚本；doctor 声明 Python ≥3.11（`doctor.py:75`），而听力链 venv 强制 3.14（`setup_offline_dictionary.py:200-206`）。本机 Python 恰好为 3.14 且 ListenKit 运行时就绪，故未受影响；但全新 Mac 上 agent 按公开文档无法完成自举。

**建议方案**：将听力链 bootstrap 脚本公开化（或在错误信息中给出公开替代步骤）；统一并显著标注"运行时 ≥3.11 / 听力链 3.14"的双契约。

### P6（噪音）顶层 `agent-skills/` 空壳与 `.DS_Store` 残留

顶层 `agent-skills/` 无任何 git 跟踪文件，易误导新 agent 把它当入口；工作树多处 `.DS_Store`。建议删除空壳目录或在其放置指向 `lingotrace/packs/*/agent_skills/` 的 README；`.DS_Store` 已被 .gitignore 兜底，可选地在目录遍历代码中过滤。

## 我的需求（汇总）

作为这个 Vault 的日常驱动 agent，我在 macOS 上需要：一个对现行布局可用的结构校验入口（P1）；一个稳定可发现的能力调用契约（P2）；一键可跑的回归测试姿势（P3）；以及听力链在新机器上可按公开文档自举（P5）。以上均不改变本仓库"agent 通过行为契约接入、写操作走 core 守卫"的既有架构。

## 附录：实跑结果速览

| 项目 | 命令 | 结果 |
|---|---|---|
| 运行时解析 | `python -m lingotrace.init resolve-runtime` | accepted=true，正确定位英语包 SKILL.md |
| 体检 | `doctor --language english` | accepted=true，0 errors / 0 warnings |
| 更新检查 | `check-update` / `--force` | 正常；正确识别 fork、fork_up_to_date |
| 更新应用 | `apply-update`（预览） | 按设计拒绝 fork 自动更新 |
| ListenKit 解析 | `resolve-listenkit` | 正确解析路径与 `.sh` 入口 |
| 运行时契约测试 | unittest discover `tests/lingotrace` | 244 通过 |
| 听力工具测试 | unittest discover | 100 通过 |
| 结构工具测试 | unittest discover | 18 通过 |
| 架构基线测试 | unittest discover | 42 通过 |
| 白名单检查 | `check-public-staged-files.sh` | 通过 |
| 五能力 preview | import workflows 逐个执行 | 5/5 accepted=true（2 个经结构化校验补全） |
| Vault 结构校验 | `validate_vault_structure.py` | **失败（P1）** |
