# Antigravity Agent Windows 兼容性报告 (LingoTrace)

## 身份声明
- **操作系统**: Windows 11
- **Agent框架**: Antigravity (Google Deepmind)
- **执行环境**: 原生 Windows PowerShell (pwsh)
- **模型**: Gemini 3.1 Pro (High)

## 兼容性测试摘要
我已经完整拉取并审查了 LingoTrace 的代码，并在 Windows 环境下成功运行了 `python -m lingotrace.init doctor` 等环境检查命令。总体而言，核心 Python 代码能够在 Windows 环境下工作，但我发现了一些系统依赖和针对早期 Codex 等工具的设计遗留问题。

## 发现的问题

### 1. Windows 平台兼容性问题
- **字符编码问题 (GBK vs UTF-8)**:
  Windows 默认控制台编码常常是 GBK，在运行 `python -m lingotrace.init` 相关命令时，如果不显式设置 `PYTHONUTF8=1`，可能会在处理含有中日字符的输出或读取文件时抛出 `UnicodeEncodeError`。在我的试运行中，只有通过 `$env:PYTHONUTF8=1` 才能确保诊断流程无错。
- **硬编码的 shell 路径**:
  历史报告中及部分工具（如 `transcribe_listening.py`）里仍遗留了类似 `subprocess.run(["/bin/bash", ...])` 的硬编码。在原生 Windows 上执行该方法必然会导致 `FileNotFoundError`，因为不存在 `/bin/bash`。
- **命令调用的平台壁垒**:
  大量日常测试和开发工具被封装成了单纯的 `.sh` 脚本，并未提供跨平台或 PowerShell 版本，这会使处于原生 Windows 的 Agent 在执行某些项目内部常规维护任务时碰壁。

### 2. Agent 框架兼容性问题 (Codex vs Antigravity)
- **跨 Agent 框架的执行环境差异**:
  虽然 Codex 和 Antigravity 均为能够自主调用工具和执行多步工作流的高级智能体框架，但它们在不同宿主环境下的默认 shell 或工具链假设可能存在差异。例如，如果某些工作流假定 Agent 运行在类似 Unix 的沙箱中（从而硬编码 `/bin/bash`），这在原生 Windows 环境（如 Antigravity 默认使用的 PowerShell）下就会引发执行崩溃。
- **技能包规范泛化不足**:
  当前依赖于 `AGENTS.md` 和各语言包的 `SKILL.md` 的体系，虽然明确了不应要求用户使用开发术语，但未能清晰指引在不同操作系统和各类自主 Agent 框架下，应如何统一、安全地跨平台调用底层 API（例如指导 Agent 优先使用跨平台的 Python CLI 而非特定的 Shell 脚本）。

## 需求与建议方案

### 我的需求
1. **统一的编码处理**: 需要框架能在运行时早期内建保障标准输出和关键读取过程使用 UTF-8，减少像我这样的外部 Agent 在 Windows 环境里还要主动猜测并设定 `PYTHONUTF8=1` 的阻力。
2. **更稳健的跨平台指令调用**: 在代码中使用 Python 的原生跨平台模块（如 `sys.executable` 或者根据 `os.name` 选择后缀），杜绝对 `/bin/bash` 的硬编码假设。
3. **适用于高权限 Agent 的文档规范**: 需要让能够自主执行和查阅文件的 Agent （例如 Antigravity）拥有一个无歧义的跨平台操作指引，而不用自己去摸索应该调用 `.sh` 还是尝试翻译成 `.ps1`。

### 建议方案
- 将跨平台的日常调用核心逻辑彻底收拢到 Python 模块调用中（`python -m module`），仅在最外层暴露出针对不同平台的轻量化启动器。
- 审查 `subprocess.run` 或 `Popen` 所在的工具代码，将其替换为跨平台的调用方式。
- 在 `docs/` 下增加一个专门面向自主行动型 Agent（如 Antigravity）的跨平台实施规范，引导其优先使用跨平台的 Python CLI 接口。
