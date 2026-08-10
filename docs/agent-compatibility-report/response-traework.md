# 给 TraeWork 的回应

感谢两份报告明确指出 Windows `PYTHONHOME` 污染和 macOS 运行时差异。需要划清边界：如果 `PYTHONHOME` 在 Python 启动前已导致 `Failed to import encodings`，LingoTrace 模块尚未执行，项目代码不可能在进程内自救；这属于宿主解释器选择或环境注入问题。

项目能做且已经做的是：所有由 LingoTrace 启动的子 Python 进程都会移除继承的 `PYTHONHOME`/`PYTHONPATH`，并设置 UTF-8 I/O；doctor 报告当前真实解释器；文档要求先验证 launcher；CLI 可用 `--report-json` 避免宿主终端编码差异。请不要再通过设置新的全局 Python 环境变量来绕过问题。

其余 Windows 平台缺陷由共享 PowerShell ListenKit 路由、可执行文件发现和统一 capability CLI 解决，不要求 TraeWork 自改项目文件。macOS 宿主行为将在 [macOS 交接](macos-codex-handoff.md)中继续实证。
