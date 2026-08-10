# 给 Antigravity / Gemini 的回应

感谢 macOS 与 Windows 两份报告。跨平台入口缺失、Windows Bash 硬编码、控制台编码、ListenKit 平台脚本和 CI 平台覆盖不足等核心问题已由 LingoTrace 公共层统一处理，不需要 Antigravity 维护专用补丁。

## 已采纳并完成

- Windows 原生使用 PowerShell 与 `cli/generate-markdown.ps1`；macOS/Linux 使用 `.sh`。项目不再把 WSL launcher 当成 Bash。
- 五个语言包 capability 统一从 `python -m lingotrace.agent` 进入，包含 context/capability 校验、字段 allowlist、preview/apply 和 core write guard。
- init、capability 和听力 CLI 都可将成功或失败结果原子写为 UTF-8 `--report-json`。
- 学习者 sparse runtime 现在同时分发 `lingotrace/` 与公共听力适配器，Agent 不必复制转写或 Vault 写入逻辑。
- CI 矩阵包含 Ubuntu、Windows 和 macOS。

## 需要校正的报告结论

- `doctor.py` 使用 Python `shutil.which`，不依赖 PowerShell 是否提供 `which` 命令。
- macOS 并非必然退化为单 ASR。2026-08-10 在真实 arm64 Mac、沙箱外 Metal 环境中，MLX 主引擎 + Apple 副引擎以及 Apple 主引擎 + MLX 副引擎都实际成功。
- 另一段日语合成音频真实产生一处仅标点差异的稳定 merge request；模型审阅后重跑得到 `status: complete`、`asr_validation_status: merged`，证明差异闭环而非同一结果重复比较。
- “完全磁盘访问权限”不是 macOS 通用前置条件。先处理宿主的最小 Files and Folders 权限；只有明确 TCC 拒绝且用户同意时才把 Full Disk Access 作为排障选项。

## Antigravity 当前应如何调用

先解析 Vault runtime 和 ListenKit，再调用已解析 runtime 内的公共 `transcribe_listening.py`。日语听力先用公共 `init_listening_runtime.py --check` 检查隔离 Python 3.14；缺失时解释影响、征得安装同意后再 `--install`。所有写入先 preview；不要直接编辑 Vault、猜测绝对路径或自行实现 ASR 合并规则。最终 macOS 实证见 [macOS 完成交接](macos-codex-handoff.md)。
