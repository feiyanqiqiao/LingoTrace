# 语言包能力指引

英文版本：[Language Pack Capability Guidance](language-pack-capability-guidance.md)

## 目的

本文是语言包能力指引的共享入口。它用于帮助不同维护者在开发语言包时，对齐用户体验标准、core 边界和测试预期，而不是把 Japanese pack 当成可以直接复制的代码模板。

这些文档当前首先是指引。只有当多个语言包用稳定测试证明了同一行为后，它们才应该逐步升级为更严格的契约。

## 成熟度层级

`Reference Guidance`

- 新语言包开发的推荐标准。
- 新语言包应阅读、尽量遵循，并记录任何差异。
- 它本身不阻断 PR。

`Candidate Contract`

- 某个行为已经在至少两个语言包中成立，或者已经有经过评审的跨语言设计。
- 新语言包应把它视为设计目标；如果不遵循，需要记录例外。
- 应有语言包级测试，或已接受的人工评审案例。

`Enforced Contract`

- 某个行为已经由 core 测试或 conformance tests 验证。
- 新语言包在声明支持该能力前，必须满足它。
- 例外需要经过契约变更评审。

## 如何使用这个索引

在开始或评审语言包 PR 前：

- 识别该语言包实现了哪些能力，哪些能力声明为 unsupported。
- 阅读每个已实现能力对应的指引。
- 在 PR 描述中列出适用的指引文件。
- 对每一项标明：已遵循、不适用，或语言包特例。
- 语言特有字段、模板、自然度规则应保留在 language pack 内。
- 在至少两个语言包证明同一规则，并且该规则有清晰 conformance 路径前，不要把行为上移到 core。

## 能力指引地图

| 范围 | 指引状态 | 指引文件 |
| --- | --- | --- |
| `review_rollover` | Reference Guidance | `docs/multilingual/review-rollover-user-stories.md` |
| `total_training_dashboard` | Reference Guidance | `docs/multilingual/total-training-dashboard-user-stories.md` |
| `listening_notes` | Planned Reference Guidance | `listening-notes-user-stories.md` 尚未创建 |
| `source_notes` | Planned Reference Guidance | `source-notes-user-stories.md` 尚未创建 |
| `review_materials` | Reference Guidance | `docs/multilingual/review-materials-user-stories.md` |
| `speaking_cards` | Planned Reference Guidance | `speaking-cards-user-stories.md` 尚未创建 |
| `agent_skill_policy` | Planned Reference Guidance | `agent-skill-policy-user-stories.md` 尚未创建 |

## Core 边界规则

单一语言需要的行为默认属于 language pack。这包括字段、模板、展示规则、词典逻辑、发音规则、source note 风格和 agent 表达方式。

只有满足以下条件时，才可以提议把行为上移到 core：

- 至少两个语言包需要同一行为；
- 共享行为可以在不依赖语言特有字段的情况下表述清楚；
- 该行为可以通过 core 测试或 conformance tests 验证；
- 已记录对现有语言包的迁移影响。

## PR 预期

新的语言包 PR 应说明：

- 已实现的能力；
- unsupported 能力及用户可理解的失败原因；
- 本索引中适用的指引文档；
- 不适用项；
- 语言包特例；
- 已实现行为的测试或人工评审证据。

已有语言包变更如果改变了用户可见的能力行为，应同步更新对应指引文档。
