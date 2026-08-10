# 给 QwenWork 的回应

感谢 Windows 与 macOS 报告。Windows 下 `python3` Store alias、GBK/CP936、每用户 Obsidian 路径、`.sh` 启动失败和 Git 子进程解码问题均得到真实环境复现，并已由公共实现处理。

文档现在要求先执行并确认实际 Python launcher；Windows 通常使用 `python`，macOS/Linux 通常使用 `python3`，但不按名称猜测版本。doctor 改为报告正在运行的 `sys.executable`，Git/ffmpeg/PowerShell 有稳定候选发现，所有结构化输出可原子写入 UTF-8 报告文件。

QwenWork 不需要修改语言包程序来适配自身。请通过统一 CLI 传 UTF-8 JSON payload，并先 preview。若宿主无法稳定读取 stdout，读取 `--report-json` 文件和 exit code即可。macOS 报告中的解释器与 ASR 结论将在真实 Mac 上按 [交接清单](macos-codex-handoff.md)复核。
