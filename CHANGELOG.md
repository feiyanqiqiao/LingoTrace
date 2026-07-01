# LingoTrace 更新日志 (Changelog)

版本号规则：`年月日-时分秒`（如 `20260606-065513`）。
后续开始迭代本项目时，所有的功能演进、修复与架构变动都会记录于此。

---

## [20260701-135000]
### 新增 (Added)
- `lingotrace.packs.english`: 英语包完成 Phase 2.1 实施与契约对齐：
  - 新增 `total-training.base` 全景看板模板，采用严谨的 4 段式 Obsidian Base 原生 YAML 格式。
  - 新增 `total_training_dashboard` 核心底层能力声明与模板映射。
  - 新增 `review_rollover` 后端纯净状态机，并同步上游 Phase 2.5 最新契约，实现英语专属 `_EN_STABLE_BASE_VOCAB_KEYS` 控制下的 Mastery Sink 毕业词库下沉。
  - 新增 `english_definition` 英英释义字段支持。
  - 完成 29 个英语包独立自动化测试，15 条契约矩阵测试（Migration Test Matrix）100% 覆盖。

### 变更 (Changed)
- `lingotrace.core.context` 与 `lingotrace.core.capabilities`: Core 核心层放开 `SUPPORTED_TARGET_LANGUAGES` 白名单，正式允许 `en` 环境，并注册看板能力。
- `lingotrace.packs.english.agent_skills.SKILL.md`: 完整重构英语日常学习 Agent 指令骨架，增加 5 行标准意图路由表，并对未支持的听口能力建立标准拒绝防腐话术。

## [20260701-080000]
### 新增 (Added)
- `lingotrace.packs.japanese.workflows:review_rollover`: day180 focus 词汇卡结算为 mastered 时，受控沉淀到 base vocabulary；无 base 记录时创建 promoted base 词卡，已有 base 记录时更新稳定字段和来源，同时保留人工正文。

### 变更 (Changed)
- `docs/multilingual/review-rollover-user-stories.md` 与日语 Agent Skill：明确结算可以执行 day180 词汇 mastery sink，但 broader base 维护、移动、删除、合并和 daily note 汇总仍需单独内容维护请求。

## [20260630-161500]
### 新增 (Added)
- `docs/multilingual/review-materials-user-stories.md`: 对照旧版 `jp-review-material-maintainer` 和当前 `review_materials` 能力，补充复习材料提取与维护的多语言 user story、验收标准和测试矩阵。
- `lingotrace.packs.japanese.workflows:review_materials`: 支持结构化复习条目输入，补齐 focus/base 查重恢复、新卡初始化、mastered 重新激活、语法/错题/发音路由、来源追加、重复匹配阻断、图片不确定阻断和 daily checklist 分离的可执行路径。

### 变更 (Changed)
- `lingotrace.packs.japanese.validators:validate_review_materials`: 从最小字段检查扩展为按 vocab / grammar / error / pronunciation 类型校验核心字段和 SRS 初始化字段。
- `lingotrace/packs/japanese/agent_skills/SKILL.md`: 明确自然语言复习材料请求应先提炼为结构化 review item，再交给 `review_materials` 执行确定性查重、路由和写入保护。

## [20260630-133230]
### 变更 (Changed)
- `AGENTS.md`: 明确了 Agent 编写 Changelog 的触发条件和时机边界，要求修改项目框架级内容（源码、配置、模板、核心文档等）后必须在执行 `git commit` 前原子化地更新本日志；明确排除日常用户卡片和笔记的生成任务。

## [20260606-065513]
### 新增 (Added)
- 创建了统一的版本更新文档（CHANGELOG.md）。
- 增加了产品与系统的详细白皮书文档（包含于 `docs/` 目录中）：
  - 功能模块与用户旅程审计报告
  - 产品需求与架构白皮书
  - 早期用户画像与自查问卷
  - 多语种与多 Agent 终端演进架构设计方案
- 更新了项目 README.md 简介与使用指南。
