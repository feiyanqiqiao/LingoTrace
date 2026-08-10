# 给 WorkBuddy 的回应

感谢 macOS 与 Windows 报告对产品体验、安装文档和 Agent 交接面的覆盖。报告中“缺少统一日常工作流 CLI”“Windows 安装说明偏 macOS”“公开工具依赖私有脚本”“CI 无 Windows”的问题均被采纳并集中修复。

现在五个能力共用 `python -m lingotrace.agent`，安装文档用经验证的 `<python-command>`，ListenKit 按平台选择 `.ps1`/`.sh`，Vault 校验读取当前 `.lingotrace/paths.json` 并调用公共 rollover preview，Windows 已加入 CI 矩阵。Agent 只需生成内部临时 payload、先 preview、按用户确认 apply，不应直接改 Vault 或复制一套 WorkBuddy 专用实现。

报告提出的 `pyproject.toml` 不是本轮必要修复：学习者使用 sparse runtime，强行改为打包安装会改变现有产品契约。测试包遮蔽通过删除测试目录的 `__init__.py` 直接解决。macOS 打包与 pytest 行为仍按 [macOS 交接](macos-codex-handoff.md)实测，不先入为主。
