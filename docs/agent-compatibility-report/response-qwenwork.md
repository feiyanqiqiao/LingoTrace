# 给 QwenWork 的回应

感谢 Windows 与 macOS 报告。Windows Store alias、GBK/CP936、每用户 Obsidian 路径、`.sh` 启动失败和 Git 子进程解码问题已在公共实现中处理；QwenWork 不需要修改语言包代码来兼容自身。

## 已证实与已修复

- launcher 必须通过真实执行确认。Windows 通常是 `python`，macOS/Linux 通常是 `python3`，但 `doctor` 最终报告当前 `sys.executable` 和版本。
- Windows 走 PowerShell `.ps1`，macOS/Linux 走 `.sh`；结构化输出固定为 UTF-8，并支持原子 `--report-json`。
- Vault validator 已在当前 `.lingotrace/paths.json` schema 和公共 `review_rollover` preview 上实际通过，同时保留旧 schema 兼容。
- 普通学习者 sparse checkout 已包含公共听力生成器；全新 Mac 的日语词典环境由公共初始化器创建，不再依赖不存在或私有的 shell wrapper。
- macOS 用含空格/CJK 的临时 Vault 和日语音频完成双 ASR、merge request、模型合并及零写入 preview；四组 unittest 共 433 项、pytest 432 passed。

## QwenWork 的稳定调用方式

通过 `python -m lingotrace.agent` 传 UTF-8 JSON payload，并先 preview。媒体任务先调用 `resolve-listenkit`，再使用返回的实际 checkout 与当前 runtime 内的公共生成器。若 stdout 在宿主里不稳定，以 `--report-json` 和 exit code 为准；exit 2 表示需要在同一任务内完成模型合并，不代表写入失败。

不要自行硬编码 Python、ListenKit、Cache 或 Vault 路径，不要直接改学习文件，也不要新增 QwenWork 专用业务 wrapper。详见 [macOS 完成交接](macos-codex-handoff.md)。
