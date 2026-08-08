# LingoTrace 文档索引

公共文档只保留当前仍可执行的产品说明、架构约束、用户指南和语言包契约。已经完成的实施计划、逐版评审稿、迁移阶段清单和 PR 过程报告应留在 Git 历史或对应 PR 中，不继续作为当前文档维护。

## 用户与运行

- [学习者 Agent 安装协议](learner-agent-setup.md)：普通用户的一句话安装编排入口
- [用户使用指南](getting-started.md)
- [Agent 操作指南](operator-manual.md)
- [Vault 初始化与跨平台运行时连接](vault-initialization-and-runtime-connections.md)
- [Listening Runtime Isolation](listening-runtime-isolation.md)

## 开发与贡献

- [开发者 Agent 初始化协议](developer-agent-setup.md)
- [安装与双用户旅程设计](installation-and-onboarding-design.md)
- [项目贡献规则](../CONTRIBUTING.md)

## 产品与架构

- [产品与能力说明](lingotrace_product_document.md)
- [多语言架构](lingotrace_multilingual_architecture_plan.md)
- [早期用户画像与准入门槛](lingotrace_user_persona.md)

## 语言包贡献与能力契约

- [语言包贡献指南](multilingual/language-pack-contributor-guide.md)
- [语言包 Agent 交接模板](multilingual/language-pack-agent-handoff-template.md)
- [语言包能力指引](multilingual/language-pack-capability-guidance.zh.md)
- [Language Pack Capability Guidance](multilingual/language-pack-capability-guidance.md)
- [听力笔记用户故事](multilingual/listening-notes-user-stories.md)
- [复习材料用户故事](multilingual/review-materials-user-stories.md)
- [复习结算用户故事](multilingual/review-rollover-user-stories.md)
- [总训练看板用户故事](multilingual/total-training-dashboard-user-stories.md)
- [Japanese Review Card Format and Link Contract](multilingual/japanese-review-card-format-and-links.md)

## 文档生命周期

以下内容适合进入公共文档：

- 当前用户能够执行的步骤；
- 当前代码已经实现并由测试验证的行为；
- 仍然约束未来变更的架构或数据契约；
- 语言包贡献者必须遵守的边界。

以下内容不应长期留在 `docs/`：

- 同一实施计划的 v1、v2、v3 和逐版评审稿；
- 已完成阶段的 entry gate、cutover checklist 和 PR acceptance matrix；
- 已由当前代码和正式架构取代的预实现差距分析；
- 只对某次提交有意义的测试数量、分支名和临时路径。

框架变更如果改变用户行为，更新对应的当前文档和 `CHANGELOG.md`。纯过程证据保留在 Git 提交、PR 说明和 CI 记录中。
