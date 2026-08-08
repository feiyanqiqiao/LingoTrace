# LingoTrace 更新日志 (Changelog)

版本号规则：`年月日-时分秒`（如 `20260606-065513`）。
后续开始迭代本项目时，所有的功能演进、修复与架构变动都会记录于此。

---

## [20260808-164535]
### 新增 (Added)
- English language pack 实现 `listening_notes`、`source_notes`、`review_materials`、`speaking_cards`、`review_rollover` 与 `total_training_dashboard` 全能力闭环；新增英语 grammar、error、speaking、chunk 模板和 English Vault 安全初始化计划。
- 新增完整的 English/Japanese 差距分析、文件级实施方案、验收矩阵和英语第一天使用路径。

### 变更 (Changed)
- 英语复习材料对齐 focus/base 查重与恢复、结构化图片证据、规范来源与关联链接、每日清单隔离、现有卡确认和人工正文保护，同时保留 IPA、word stress、CEFR、英英释义与 collocations 等英语专属语义。
- 英语总训练 Base 对齐日语的 today/next-day 语义和多训练线视图，覆盖口语、听力、发音、单词重音、音素、最近新增与反复出错。
- 官方听力工具按 Vault context 自动选择 `ja-JP` 或 `en-US`，英语链路不加载日语重音词典，并通过 English workflow 与 core guard 写入。
- README、用户指南、操作手册、语言包贡献指南及多语言 user-story 适用性矩阵同步反映英语完整支持。

### 测试 (Tests)
- 扩展 English pack、English Vault 初始化、官方双 ASR 英语 locale/guard 路由、dashboard 与 contributor guidance 回归；通过 LingoTrace、官方听力、架构基线和 Vault 结构测试。

## [20260807-092558]
### 变更 (Changed)
- 日语 Agent Skill 将词汇搭配、词汇例句和语法例句的生成顺序调整为“当前来源笔记 → 当前 Vault 其他已有句子 → 仅补齐缺失内容”；词汇按词头与活用形检索，语法按实际表面形、活用形与缩约形检索，并禁止硬套语义不匹配的库内句子。
- `review_materials` 的合法读取与来源链接范围扩展到听力笔记和口语卡，使复用或最小适配的库内句子能保留可追溯来源。

### 测试 (Tests)
- 新增听力笔记与口语卡可作为复习材料来源的回归覆盖，并通过 72 项日语包测试。

## [20260805-130730]
### 新增 (Added)
- 日语包正式登记 `chunk` 口语条目类型、生产性语块字段与独立 `chunk_card` 模板；总训练 Base 用“语块”显示该类型，并以 `chunk_pattern` 和 `chunk_meaning_zh` 作为训练主线索。

### 变更 (Changed)
- 听力笔记的新建区块从“可直接背的常用句”调整为 `## 常用语块`，采用 `语块 / 类型 / 素材原句 / 替换练习 / 交际作用` 契约；旧标题及人工内容在重跑时继续原样保留。
- 日语 Agent Skill 固化“精听提取、用户线下 review、后续独立转录”的两阶段边界；后续转录请求本身即为确认，同一用户任务不得直接升格口语卡。
- `speaking_cards` 对 `chunk_pattern` 做规范化查重，阻止在不同路径创建重复语块，并允许在既有卡路径上执行已 review 的保守合并。

### 测试 (Tests)
- 新增常用语块新旧标题兼容、语块模板与清单登记、Base 显示契约、缺失或重复 `chunk_pattern`、既有语块合并及复习状态保留回归测试。

## [20260715-174754]
### 变更 (Changed)
- `review_materials` 多语言 user story 与当前日语实现重新对齐：明确 `item`、完整 `card`、`daily_checklist` 三种互斥输入模式、已有目标确认边界、无载荷只读旧卡预览，以及结构化更新与完整正文替换的职责差异。
- 补充同来源不重复重置、新来源及明确弱项回到 day0、每日清单受管理区块、图片附件安全解析等验收标准；迁移矩阵改为引用真实工作流测试，并将英语图片词汇能力标记为尚未满足结构化证据契约的 `Partial`。

### 测试 (Tests)
- 扩展 user story 文档契约断言，并新增图片证据路径遍历、危险嵌入和无路径重名附件阻断用例。

## [20260715-163028]
### 变更 (Changed)
- `review_materials` 的图片词汇输入新增结构化 `image_evidence` 门禁：验证真实 Vault 附件、视觉或人工检查方式、清晰度、观察文本、规范词头和来源笔记 `## 単語` 内的实际嵌入；单独声明 `image_readable: true` 不再允许写卡，来源正文已经出现的词也不会从图片重复提取。
- 词汇查重在 focus 命中后立即停止，不再让 base 层的历史重名阻断现有 focus 卡更新。
- 新增显式 `daily_checklist` 输入，只能在确认后更新既有日期笔记中的受管理轻量清单区块；人工清单默认保留，复习卡 SRS 字段不会被清单操作修改。

### 测试 (Tests)
- 新增真实图片证据、缺失附件、OCR-only、来源正文去重、focus/base 同名历史、每日清单 preview/确认/路径/文本注入/人工内容保护及 SRS 隔离回归测试，并将多语言 user story 覆盖矩阵改为引用真实工作流证据。

## [20260715-155752]
### 修复 (Fixed)
- `review_materials` 的现有卡预览恢复旧 schema 兼容，不要求用户为新模板批量迁移旧卡；新卡和完整重排仍执行严格元数据与非空正文校验。
- 来源去重改为比较完整 Vault 相对路径：不同目录的同名笔记不再互相覆盖，旧式无路径链接仅在唯一解析时与规范链接合并，歧义时保留人工链接并追加已验证来源。
- 既有错题再次出现或语法/词汇被明确标记为弱项时，正确增加出现与错误计数、提高优先级，并重置到当天 `day0` 复习，不覆盖人工正文。
- 语法空用法分支不再产生空标题；数字、日期和 YAML 隐式词形的文本标量会安全加引号，读取后保持字符串语义。
- 长错误句生成可读前缀加稳定摘要的安全文件名；完整 `card` 路径新增遍历、控制字符和长度保护，未解析关联统一保留在 `## 待补卡`。

### 测试 (Tests)
- 新增旧卡无迁移预览、同名来源与歧义旧链接、错题及语法弱项复发、空语法分支、YAML 隐式类型、长文件名、完整卡片路径与关联降级回归测试。

## [20260715-152146]
### 新增 (Added)
- 日语 `review_materials` 新增结构化词汇卡、语法卡与错题卡渲染器，补齐统一复习元数据、安全 YAML 列表、按需章节和 Obsidian 错题重点标记；公共初始化新增语法卡与错题卡模板。
- 新增 Vault 角色范围内的来源与关联卡链接解析：来源缺失、重名、越界、格式错误或自引用时阻断写入；缺失或重名的可选关联保留普通文本并通过 `unresolved_related_items` 报告，不再生成悬空 wikilink。

### 变更 (Changed)
- `review_materials` 新增 `existing_update_confirmed` 门禁；结构化 `item` 更新已有卡时只维护已确认的来源和复习生命周期，不覆盖人工语义字段或正文，完整重排继续通过显式确认的 `card` 载荷执行。
- 新卡文件名拒绝会改变 Obsidian 链接语义的字符；公开 Agent skill、卡片格式与链接契约、review-material user story 同步更新。

### 测试 (Tests)
- 新增三类参考卡 golden fixtures，以及来源和关联链接唯一解析、缺失、重名、越界、自引用、YAML 注入、可选章节、已有卡确认和正文保护回归；全量 LingoTrace 测试覆盖初始化与复习结算兼容性。

## [20260713-144452]
### 修复 (Fixed)
- preview/dry-run 检出双 ASR 差异时，将 LLM 合并请求复制到权限隔离的稳定临时路径，避免 staging 清理后 Agent 无法继续同任务合并；第二阶段通过 `--reviewed-transcript` 与 `--merge-request` 成对重跑。
- 稳定 handoff 同步保留首轮原始 ListenKit、标准化 ASR 与差异报告，并在共识重跑时交由 core write guard 持久化；精听切片报告改用可迁移的 `attach/...` 相对路径，避免 staging 临时路径进入 Vault 工件。
- LLM 共识必须绑定真实待处理请求，并校验音频哈希、请求 ID、片段身份、时间戳以及 `decision` 与 `selected_text` 的对应关系；不再允许凭格式正确的伪造 ID 绕过双 ASR。
- 两路 ASR 完全一致时明确通知用户“无需模型合并”，第二引擎不可用时明确报告受控单 ASR 降级。

### 测试 (Tests)
- 新增 preview 清理后的稳定请求及完整 ASR 工件可读性测试，以及 provider-neutral 的两阶段 Gemini/Codex 形态共识端到端 fixture，覆盖请求读取、模型裁决、跳过重复 ASR、guarded rerun、可迁移切片报告和最终笔记写入。

## [20260713-142905]
### 变更 (Changed)
- 日语听力脚本生成统一默认启用双 ASR 验证，不再只对精听、短选择题等高风险素材自动启用；普通泛听、本地音频和 URL 输入均走相同的交叉比对与模型共识流程。
- `--single-asr` 保留为用户明确要求时的主动降级选项；第二 ASR 运行时不可用时仍可受控降级，并向用户报告限制。
- 更新日语 Agent Skill、多语言听力 user story 与契约测试，确保 Codex、Gemini 等调用方不会为普通素材绕过双 ASR 默认值。

## [20260713-142300]
### 新增 (Added)
- 双 ASR 出现差异时生成 provider-neutral 的 `llm-merge-request.json`，包含两路候选、上下文、风险分类和可直接填写的共识模板；Codex、Gemini 等调用方模型可在同一任务内自动裁决并重跑听力流程，无需在脚本中绑定模型厂商 API。
- LLM 共识新增音频哈希、合并请求 ID、片段 ID、时间戳、决定、置信度和理由校验；低置信度或被篡改的片段继续阻断最终笔记写入。

### 变更 (Changed)
- 听力 CLI 以结构化状态和通知报告待合并差异数、完成合并的模型及最终结果；Agent skill 明确不得把内部合并请求直接丢给用户，而应自动处理，仅在确有低置信度时请求确认。
- 补充双 ASR 一致直通、模型合并请求、模型共识重跑跳过重复 ASR、身份校验、低置信度阻断以及 Codex/Gemini 中立调用契约测试。

## [20260713-134631]
### 新增 (Added)
- `tools/listening-transcribe-official/transcribe_listening.py`: 新增显式 Vault、LingoTrace 与 ListenKit 根目录参数，支持从任意工作目录统一准备本地音频和 URL 素材；新增带音频哈希、引擎、语言、完整时间戳的标准化 ASR 工件。
- `tools/listening-transcribe-official/transcribe_listening.py`: 高风险精听默认使用 faster-whisper 主转写与 Apple 辅助转写，按时间重叠和文本相似度对齐，保存差异分类、比对报告和待审核共识；未解决差异阻止最终笔记写入，辅助引擎不可用时则明确记录单 ASR 降级限制。
- `lingotrace.core.mutations` 与日语 `listening_notes` workflow：支持 Markdown、JSON、音频切片组成的多文件 bundle，经统一 preview/apply 写入保护进行原子提交和失败回滚。

### 变更 (Changed)
- 听力生成器不再直接写入已配置的 LingoTrace Vault；本地音频与 URL 均先在临时区生成，再校验 `listening_root` 路径边界、现有笔记覆盖确认和人工共识状态后提交。
- 精听流程继续保留人工维护的常用句与自定义段落；reviewed manifest 强制非重叠，最终笔记的学习块、音频嵌入、切片报告与 `segment_count` 必须数量一致且对应真实非空音频文件。
- 补充双 ASR 分段对齐、人工共识门禁、URL 双引擎、本地降级、二进制原子写入、覆盖确认、越界阻断和真实切片不变量的自动化测试。

## [20260703-164000]
### 变更 (Changed)
- `docs/multilingual/`: 对历史阶段文档进行了结构重构。创建了 `docs/multilingual/history/` 目录并将已完成的 `phase-0`、`phase-1` 和 `phase-2` 完整移入归档。
- `docs/multilingual/phase-1/contributor-guide.md`: 添加了明确的 `[OBSOLETE]` 弃用声明，重定向至正式的语言包贡献指南。
- `docs/lingotrace_multilingual_phase0_implementation_plan.md`: 将其移至 `docs/multilingual/history/phase-0/implementation-plan.md`，修复了脱离其专属阶段目录的问题。
- `docs/runtime-snapshot-lingotrace-python314.txt`: 从文档根目录移至 `tools/architecture-baseline/` 目录下。
- `tools/README.md` 与全项目其余 Markdown 文档均执行了全局相对路径链接修复。
- `docs/multilingual/review-materials-user-stories.md` 与 `lingotrace.packs.japanese.workflows:review_materials`: 补充并实现“已存在 active focus 卡在新来源笔记中再次出现时，应作为新的学习信号重置为 `day0`”的规则，确保重新出现的词卡回到当天复习队列，同时保留人工正文和来源合并。

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
