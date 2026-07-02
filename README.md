# LingoTrace

LingoTrace 是一个完全构建在 Obsidian 之上的、高度定制化和自动化的**外语学习工作流引擎（当前深度适配日语）**。

它剥离了底层的语音识别与音视频爬取技术（已交由子项目 [ListenKit](https://github.com/feiyanqiqiao/ListenKit) 负责），专注于解决一个核心痛点：**如何将泛听素材、外语播客和视频自动化转化为结构化的个人知识图谱，并将其内化为长时记忆和主动口语输出能力。**

本仓库开源 LingoTrace 公共核心、日语语言包、初始化模板、迁移工具和公共验证测试。私人 Vault 中的真实学习资料、音频、每日记录和运行产物不属于本仓库。

---

> 🌟 **如果你是普通外语学习者（非开发者），请首先阅读 [👉 LingoTrace 用户使用指南](docs/user-guide.md)，了解如何像指挥私人助理一样在 Obsidian 中沉浸式学习！**

---

## 🚀 日常入口与核心工作流

LingoTrace 的主要使用方式是：用户用自然语言提出学习任务，由 Codex 或兼容的 AI agent 读取 Japanese language pack 内的 Agent Skill，并把任务保存到你的日语学习库。

你可以直接这样说：

- “请把这段音频做成精听稿。”
- “帮我把这篇材料整理成日语学习笔记。”
- “把这个词加入复习。”
- “这句话很实用，帮我做成口语卡。”
- “今天复习结束了，帮我结算。”

Agent Skill 会把这些自然语言请求映射到听力笔记、来源笔记、复习材料、生活口语卡和每日复习结算五个能力。底层仍由 LingoTrace core 和 Japanese language pack 负责安全检查、路径边界和保存行为；普通用户不需要记内部函数名或命令。

这些句子只是示例，不是固定提示词。Agent Skill 会先识别真实学习意图，再选择对应能力；“更新总训练表”和“请更新总训练表”是明确的每日复习结算请求。只有“处理一下总训练表”“总训练表有点问题”这类未说明是结算还是视图维护的表达，才会先确认你的意思。

新增听力笔记、来源笔记和口语卡时，系统会避免覆盖你已经手工整理过的笔记。复习材料合并、移动、覆盖或非结算状态修改会先让我确认；明确的每日复习结算请求会先内部预览，确认无错误后直接保存并报告结果。

---

## 📚 深度阅读与白皮书文档

为了更好地了解本系统的产品哲学、架构约束与适用人群，请参阅 `docs/` 目录下的详细分析报告：

- 📖 **[功能模块与用户旅程审计报告](docs/lingotrace_audit_report.md)**：将外语学习的实际痛点场景映射到 LingoTrace 系统工作流中的全周期拆解。
- 🏗️ **[产品需求与架构白皮书](docs/lingotrace_product_document.md)**：包含详细的业务流转逻辑、双层词库架构分析和元数据（Frontmatter）字典级约束。
- 👥 **[早期用户画像与准入门槛](docs/lingotrace_user_persona.md)**：目标受众分析、不适合人群说明，以及面向早期极客测试者的“一分钟自查问卷”。
- 🌐 **[多语言架构总体规划方案](docs/lingotrace_multilingual_architecture_plan.md)**：多语言演进的正式规划来源，定义单目标语言 Vault、公共核心、语言包、兼容策略和阶段门槛。
- 🧩 **[新语言包贡献指南](docs/multilingual/language-pack-contributor-guide.md)**：项目组成员和其他 Agent 开发 English、Korean、German 等语言包时的接入边界、目录结构、禁止项和验收规则。Do not use the Japanese pack as a copy template.
- 🤖 **[新语言包 Agent 交接模板](docs/multilingual/language-pack-agent-handoff-template.md)**：把新语言包任务交给 Codex、Claude Code、Trae 等 Agent 时可直接复用的任务说明模板。
- 🔮 **[多语种与多 Agent 终端演进方案](docs/lingotrace_multilingual_multiagent_design.md)**：早期研究材料，用于保留问题分析和多 Agent 讨论；其中的多语言架构建议以正式总体规划为准。

---

## 🤝 参与贡献与开源许可

本项目采用 **AGPL v3** 协议开源，鼓励极客自由分发、学习与修改。为了防范未经授权的直接商业化套壳行为，并保障早期参与者的权益，我们制定了严格的开源商业化规则：

- **贡献指南与条款**：参与项目前请务必仔细参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。
- **CLA (贡献者许可协议)**：向本项目提交有效代码（Merge PR）即代表您不可撤销地授权核心维护团队在未来的任意场景（含闭源商业化变现产品）中免费使用。
- **名誉回馈机制**：我们为社区贡献者建立了三级回馈门槛。针对提供有效代码合并的核心贡献者，除了在商业版的“致谢墙”专属展示外，未来还将获赠商业化客户端的终身免费授权（VIP）。

---

## 📂 仓库结构

- `lingotrace/`：公共核心、日语语言包、Vault 初始化和迁移支持代码。
- `tests/lingotrace/`：核心、语言包、初始化和迁移行为测试。
- `tools/git/`：公共仓库安全检查，防止私人 Vault 文件进入提交。
- `tools/architecture-baseline/`：架构契约与历史行为基线测试。
- `tools/listening-transcribe-official/`：听力链相关的公共工具和测试。
- `docs/`：产品、架构、阶段路线和 runbook 文档。

---

## ⚠️ 隐私、版权与使用声明

本仓库**仅开源系统的自动化框架、理念设计和执行脚本**，绝不包含个人金库内的实际笔记。在使用本系统构建你自己的学习库时，请务必遵守以下原则：

- **请勿提交** 任何属于你个人的 Obsidian 私人日记或打卡记录。
- **请勿提交** 任何受版权保护的商业教材音频、视频及配套的转写原始文件。
- **请勿提交** `.obsidian/` 本地工作区配置文件或工具生成的临时音频切片文件。

通用音频导入与外部语音识别，请配合部署本系统的前置依赖项目：[ListenKit](https://github.com/feiyanqiqiao/ListenKit)。

听力链使用两个隔离的 Python 3.14 虚拟环境，部署与故障排查见 [Listening Runtime Isolation](docs/listening-runtime-isolation.md)。
