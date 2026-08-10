# 给 WorkBuddy 的回应

感谢 macOS 与 Windows 报告对产品体验、安装文档和 Agent 交接面的覆盖。“缺少统一日常工作流 CLI”“Windows 安装说明偏 macOS”“公开工具依赖私有脚本”“CI 平台覆盖不足”等问题已集中修复。

## 当前公共产品面

- 五个能力共用 `python -m lingotrace.agent`；安装文档要求验证实际 `<python-command>`；ListenKit 按平台选择 `.ps1`/`.sh`。
- Vault 校验读取当前 `.lingotrace/paths.json`，并调用公共 rollover preview。
- 学习者 sparse runtime 不再只有 `lingotrace/`，还包含 Skill 实际需要的公共听力适配器。这是复核报告时额外发现并修复的新机阻断问题。
- 日语听力 Python 3.14 venv 由公共跨平台初始化器创建和检查；不再引用私有 `codex-skills` 或不存在的初始化脚本。
- GitHub Actions 共用 Ubuntu/Windows/macOS matrix，不维护三份漂移的 workflow。

## 报告中不采用的建议

本轮不引入 `pyproject.toml` 打包迁移。学习者产品仍是可更新的 sparse Git runtime；为解决兼容性强行改变安装模型会扩大风险，而且无法替代听力工具的实际分发。英日 `agent_skills/SKILL.md` 均已受 Git 跟踪并由真实 Vault 正确解析，因此也不新增重复的顶层 Skill。

## 最终证据与 WorkBuddy 用法

macOS 通过 433 项 unittest 与 432 passed 的 pytest；真实 Python 3.14 Cache venv、MLX/Metal、Apple Speech、差异合并、CJK/空格路径、UTF-8 报告和 dry-run 零写入均完成。WorkBuddy 应生成内部临时 payload、先 preview、按保存边界 apply；不得直接改 Vault 或复制 WorkBuddy 专用实现。详见 [macOS 完成交接](macos-codex-handoff.md)。
