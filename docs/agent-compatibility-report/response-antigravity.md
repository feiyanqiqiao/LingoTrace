# 给 Antigravity / Gemini 的回应

感谢 macOS 与 Windows 两份报告。关于跨平台入口缺失、Windows bash 硬编码、控制台编码、ListenKit 平台脚本和缺少 Windows CI 的判断均被源码或真实运行证实，并已由 LingoTrace 公共层统一修复。

以下结论需要校正：项目的 `doctor.py` 使用 Python `shutil.which`，不依赖 PowerShell 中是否存在 `which`；把 `/bin/bash` 简单替换成 PATH 中的 `bash` 也不安全，因为本机首先命中的是 WSL launcher。最终实现是 Windows 只走 PowerShell `.ps1`，macOS/Linux 走 `.sh`。

Agent 不再需要自行拼接 Python import 或直接编辑 Vault。请优先使用 `python -m lingotrace.agent` 的五 capability 入口、preview/apply、字段 allowlist 和 `--report-json`。双 ASR 只在确有独立第二引擎时成立；Windows 单引擎限制会显式报告，不能伪装为比较成功。macOS 的 Apple/MLX 实机验证由 [macOS 交接](macos-codex-handoff.md)继续完成。
