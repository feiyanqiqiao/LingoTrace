# LingoTrace × WorkBuddy（macOS）兼容性报告

> 文件名体现：WorkBuddy（Agent 框架）+ macOS（操作系统）
> 生成日期：2026-08-10
> 报告人：WorkBuddy（见下方"我是谁"）

---

## 一、我是谁（身份声明）

- **Agent 框架**：WorkBuddy（腾讯出品的 AI 助手 / Agent 框架）。本仓库原本针对 **Codex**（OpenAI 的 Agent 框架）开发，本报告检查其对"macOS + WorkBuddy"的兼容性。
- **操作系统**：macOS 27.0（arm64，Apple Silicon），Aqua GUI 会话。
- **执行环境**：由 WorkBuddy Agent 沙箱执行命令；宿主进程 `com.workbuddy.workbuddy`。
- **本机 Python**：3.13.12（WorkBuddy 托管）/ 3.14.4（系统）；运行时实际通过 `python3.14`（系统 3.14.6）执行 `lingotrace` 包。
- **目标 Vault**：`/Users/jiezhengj/Documents/Obsidian/LingoTrace-English`（target_language=en，language_pack=lingo-english）。

本报告的检查方法：**既审计代码，也实际完整跑过运行时**（init 子命令、单元测试套件、端到端听力转写、双 ASR 校验）。

---

## 二、macOS 兼容性实测（实际跑过）

以下命令均在 macOS 27.0 arm64 下真实执行并验证：

| 检查项 | 命令 | 结果 |
|---|---|---|
| 解析运行时 | `python -m lingotrace.init resolve-runtime` | ✅ 成功，解析出 `runtime_root` |
| 解析 ListenKit | `python -m lingotrace.init resolve-listenkit` | ✅ `generate_markdown = …/ListenKit/cli/generate-markdown.sh` |
| 自检 | `python -m lingotrace.init doctor` | ✅ exit 0，健康 |
| 更新检查 | `python -m lingotrace.init check-update` | ✅ `fork_up_to_date`（已写 `.lingotrace/runtime-update-checks/macos.json`） |
| 单元测试（复现 CI 四步） | listening-transcribe-official / vault-structure / architecture-baseline / tests/lingotrace | ✅ 100 / 18 / 42 / 244 全过（Python 3.13.12 与 3.14.4 均 OK） |
| 端到端听力链路 | `invoke_listenkit()` | ✅ `engine=mlx-whisper, device=metal, compute_type=float16, model=mlx-community/whisper-small-mlx`，`full_text` 正确 |
| 双 ASR 校验 | 主引擎 mlx-whisper | ⚠️ 主引擎成功；次引擎 apple → `secondary_unavailable`，`secondary.error="Apple Speech helper finished without producing JSON output…"`（见 ListenKit 报告） |

**结论**：LingoTrace 在 macOS 上核心功能健康，端到端转写链路可用。

---

## 三、Agent 框架兼容性（相对 Codex）问题与需求

### 问题 A（Codex 残留路径，死代码/坏引用）
- `tools/listening-transcribe-official/transcribe_listening.py:271`
  `init_script = vault_root / "codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh"`
  → 该目录在本机不存在，也未被 git 追踪。本 Agent 的日常入口 `lingotrace/packs/english/agent_skills/SKILL.md` 并不依赖此路径，但脚本内部仍引用它。
- `tools/listening-transcribe-official/tests/test_transcribe_listening.py:27`
  `WRAPPER_PATH = … / "codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh"`
  → 同样指向不存在的路径；同文件 L134 还用 `git ls-files codex-skills/…` 做存在性校验。

**需求**：移除 Codex 专属残留路径，改为与本 Agent 框架无关的中性约定，或基于当前 Vault 配置动态解析。

### 问题 B（macOS POSIX 硬编码，缺平台分支）
- `transcribe_listening.py:451-452` `configure_project_roots`：`if not (root / "cli" / "generate-markdown.sh").is_file()`（硬编码 `.sh`）
- `transcribe_listening.py:457` `listenkit_generate_markdown_script_path()`：返回 `listenkit_root() / "cli" / "generate-markdown.sh"`
- `transcribe_listening.py:646` `invoke_listenkit`：`command = ["/bin/bash", str(script_path), …]`（硬编码 `/bin/bash`）
- `lingotrace/init/listenkit_connections.py:329` 与 `:341`：硬编码返回 `generate-markdown.sh`

**影响**：macOS / Linux 可用；**原生 Windows（无 `.sh`、无 `/bin/bash`）会失败**。WorkBuddy 在 macOS 上不受影响，但若用户在 Windows 上用 WorkBuddy，则触发此问题。这是"对 macOS 兼容、但对原 Codex 跨平台假设在 Windows 上不兼容"的交叉点。

**需求**：跨平台入口不应硬编码 `.sh` / `/bin/bash`；对 Windows 提供 `.ps1` 分支，或统一改用 Python 入口调用 ListenKit 的 Python 模块。

### 问题 C（`--engine` 契约不对称）
- `transcribe_listening.py:397` 与 `:400`：`--engine` 的 `choices=["auto", "apple", "faster-whisper"]`，**缺少 `mlx`**。
- 但 ListenKit 的 `generate-markdown.sh` / `transcribe-audio.sh` 接受 `auto|faster-whisper|mlx|apple`。
- 实测：在 LingoTrace 层传 `--engine mlx` 会被 argparse 直接拒绝（`invalid choice: 'mlx'`），而 ListenKit 侧实际支持 `mlx`（端到端已验证）。两边契约漂移。

**需求**：LingoTrace 与 ListenKit 的 `--engine` 取值集合应一致（都支持 `mlx`），或 LingoTrace 透传 engine 字符串给 ListenKit 由其校验。

### 问题 D（双 ASR 次引擎在 macOS 必然降级）
- `transcribe_listening.py:1890`：`compare_engine = "faster-whisper" if primary_engine == "apple" else "apple"` —— 当主引擎非 apple 时，次引擎恒为 `apple`。
- `SKILL.md` 默认要求双 ASR 校验。但 macOS 上 Apple Speech helper 无法启动（见 ListenKit 报告 F1），次引擎恒为 `secondary_unavailable`。
- **结果**：默认的双 ASR 保障在 macOS 上必然降级为单 ASR，与"双 ASR 保障质量"的设计意图冲突。

**需求**：要么在 macOS 上修复 Apple helper 启动（见 ListenKit F1），要么在 `SKILL.md` 明确说明 macOS 默认等价于 `--single-asr`，并让 Agent 把 `secondary_unavailable` 理解为预期降级（而非错误）。

### 问题 E（agent-skills 目录空 / 发布完整性）
- `lingotrace/packs/english/agent_skills/` 当前无 git 追踪内容（仅 `.DS_Store`）。
- 本 Agent 依赖 `packs/english/agent_skills/SKILL.md` 作为日常操作入口。若该文件未随包发布（git add / 打包清单遗漏），Agent 将找不到操作入口。
- 实测当前 `SKILL.md` 存在且已被本 Agent 读取执行，但需确保它进入版本控制与发布产物。

**需求**：确保 `agent_skills/SKILL.md` 随包发布并被 git 追踪。

---

## 四、建议方案（按优先级）

1. **A / 死代码**：删除 `transcribe_listening.py:271` 与 `test_transcribe_listening.py:27` 的 `codex-skills` 引用；改为从 `.lingotrace/paths.json` 或运行时连接文件动态解析脚本路径；或在文档中声明该脚本由用户自选 Agent 提供、非运行时必需。
2. **B / 跨平台**：将 `generate-markdown.sh` 硬编码改为按 `platform.system()` 选择 `cli/generate-markdown.{sh,ps1}`；`invoke_listenkit` 用 `sys.executable` 调用 Python 包装或直接执行 `.ps1`（Windows）。最简稳健方案：提供 `lingotrace` 的 Python 入口统一调用 ListenKit 的 Python 模块，彻底规避 shell 分支。
3. **C / 契约对齐**：在 LingoTrace 的 argparse 增加 `mlx` 选项并与 ListenKit 对齐；或让 LingoTrace 透传 engine 字符串。
4. **D / 双 ASR**：先行修复 ListenKit 的 Apple helper 启动（见 ListenKit F1）；在修复前，于 `SKILL.md` 标注 macOS 默认单 ASR 行为，并让 Agent 将 `secondary_unavailable` 视为预期降级结论。
5. **E / 发布完整性**：`git add` 并确保打包清单包含 `agent_skills/SKILL.md`。

---

## 五、与 ListenKit 报告的关系

本报告中"Apple Speech helper 在 macOS 上无法启动""`--engine mlx` 契约不对称"等问题，根因与修复建议见同目录下的 `workbuddy-macos-compatibility.md`（ListenKit 报告）。两份报告应合并阅读。
