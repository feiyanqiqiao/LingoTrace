# LingoTrace 更新日志 (Changelog)

版本号规则：`年月日-时分秒`（如 `20260606-065513`）。
后续开始迭代本项目时，所有的功能演进、修复与架构变动都会记录于此。

---

## [20260703-162500]
### 变更 (Changed)
- `docs/user-guide.md` 与 `docs/USER_GUIDE.md`: 为了消除文件名相近导致的混淆，将其分别重命名为更具有自解释性的 `docs/getting-started.md` (面向新手的入门与故事指南) 与 `docs/operator-manual.md` (面向 Agent 及高阶极客的系统与操作手册)。
- `README.md`: 更新了对应指南文档的导流入口，为普通用户和 Agent 分别指明了阅读路径。

## [20260702-212405]
### 新增 (Added)
- `docs/multilingual/listening-notes-user-stories.md`: 对照旧版听力素材模板、当前 `jp-listening-script-generator` 和 listening contract tests，补充听力剧本生成模块的多语言 user story、验收标准、Agent use cases、覆盖矩阵和开放缺口。
- `docs/multilingual/listening-notes-user-stories.md`: 补充日语重音标记与多 ASR 交叉比对 user story，明确重音标记属于语言包自有发音提示；新生成的日语精听块默认采用 `こいし＼い` 这类下跌点写法，历史笔记不批量回填，双转写更适合作为高价值精听或低置信场景的质量门。
- `docs/multilingual/listening-notes-user-stories.md`: 补齐旧听力 skill 中尚未落入 user story 的短选择题结构、听力 frontmatter/总训练表可见性、对话与编号对话渲染、dry-run/命名/不确定输出门禁、单条处理与默认禁用批量写入规则。
- `docs/multilingual/*user-stories.md`: 为现有多语言 user story 补充 Language Applicability Matrix，按用例标记共享要求、日语覆盖、英语覆盖和语言包例外，并新增文档测试防止后续指引遗漏适用语言声明。

### 变更 (Changed)
- `docs/multilingual/language-pack-capability-guidance.md` 与中文索引：将 `listening_notes` 从 planned guidance 升级为 Reference Guidance，并把 handoff 模板加入该指引。
- `tools/listening-transcribe-official/transcribe_listening.py`: 精听学习包对可信来源命中的纯假名重音词优先渲染为划断式下跌点（如 `こいし＼い`），同时保留圆圈重音号作为词卡/看板稳定显示样式；新增测试覆盖该行为，并补齐素材说明、低质量泛听中间产物、旧精听笔记模式推断等迁移规则的文档契约断言。
- `tools/listening-transcribe-official/transcribe_listening.py`: 本地音频转写新增可选 `--compare-engine` 对比入口，生成 `artifacts/<audio>.asr-comparison.json`，记录主/副 ASR 的引擎、片段数量和句级差异；默认仍以主转写作为生成来源。
- `lingotrace/packs/english/views/total-training.base`: 补强英语总训练表 `core_text` / `support_text` 的类型化显示和空值兜底，确保 vocabulary、grammar、error、pronunciation 卡片均符合 dashboard user story；新增英语公式契约测试。
- `tools/architecture-baseline/tests/test_language_pack_contributor_kit.py`: 新增 user story 测试引用一致性检查，确保多语言 user story 文档中引用的 `test_*` 名称都对应真实测试函数。

## [20260701-143000]
### 新增 (Added)
- `docs/user-guide.md`: 新增面向普通语言学习者的《LingoTrace 用户使用指南》，以纯用户视角介绍原理解构、输入输出闭环与全景训练看板（Total Training Dashboard）的使用方法，并更新了 `README.md` 提供显眼导流入口。

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
