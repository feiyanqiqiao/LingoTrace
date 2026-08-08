# English Pack 与 Japanese Pack 全功能对齐实施文档

日期：2026-08-08  
实施分支：`codex/english-pack-japanese-parity`  
目标基线：同步后的 `origin/main`

## 1. 目标与完成定义

本次工作把 English language pack 从“来源笔记、复习材料和复习结算基本可用”提升为可承担日常学习的完整语言包。完成后，用户应能用与日语相同的自然语言入口完成：

1. 音频或 URL 到泛听/精听笔记；
2. 文章、字幕、粘贴文本或截图内容到来源笔记；
3. 词汇、语法、错题、发音材料到可复习卡片；
4. 经用户复核的常用语块到英语口语卡；
5. 当日复习结算、延期、毕业和基础词库下沉；
6. 在 Obsidian 总训练 Base 中查看所有训练线。

“可用”的验收边界如下：

- 仓库具备英语 manifest、Skill、模板、路径、初始化计划、工作流、校验器、官方听力入口和自动化测试；
- 英语写入必须通过 core context、capability、path role 和 mutation guard；
- 英语包不得导入 Japanese pack，也不得在英语听力时加载日语词典或输出 `jp/*` 标签；
- 私人英语 Vault 仍需在实际学习库中落地 `.lingotrace` 配置、目录、模板和 Base，并准备 ListenKit/ASR 运行时；仓库代码通过不等于某个未提供路径的私人 Vault 已初始化；
- 真实音频的转写准确度、语块自然度和低置信度专名仍需 Agent 或用户基于实际材料验收。

## 2. 上游与分支基线

实施前先同步上游主线并审计本地、fork 和 upstream 分支。同步结果以 `origin/main` 为本次主题分支起点；同步 PR 只包含上游变化，不混入英语实现。

分支处理原则：

- 已是主线祖先的分支：删除引用，不重复合并；
- `git cherry` 判定为 patch-equivalent 的分支：视为内容已进入主线，删除引用；
- 文件内容已被当前主线吸收的旧实现分支：不合并旧历史，删除分支；
- 基于旧架构且会倒退当前 core/pack 边界的分支：明确判定为 superseded，不合并；
- upstream 仍在进行、尚未进入 upstream main 的依赖更新分支：保留上游所有权，不抢先合并；
- 被另一个工作树检出且带用户未提交状态的分支：不强制切换或删除，避免破坏用户工作区。

## 3. 实施前差距盘点

| 能力 | Japanese 基线 | English 实施前 | 差距 | 本次处理 |
| --- | --- | --- | --- | --- |
| `listening_notes` | stable，官方双 ASR、精听切片、保留人工内容 | manifest 不支持，官方工具默认日语且调用日语 workflow | 阻断日常听力 | 完整实现，并按 Vault 自动选 `en-US` 和 English workflow |
| `source_notes` | stable，来源可追溯、路径受 guard 保护 | 基础支持 | 缺少与后续卡片契约的完整说明 | 对齐 Skill、manifest 和测试 |
| `review_materials` | stable，查重、恢复、图片证据、链接、每日清单、稳定正文 | 只有较窄的词卡路径 | 多数高风险契约缺失 | 对齐工作流与校验器，保留英语字段模型 |
| `speaking_cards` | stable，复核后提升、chunk 去重、保留人工内容 | manifest 不支持 | 无英语主动输出闭环 | 实现 speaking card 与 chunk 两条路径 |
| `review_rollover` | stable，完整阶段、延期、mastery sink、二次 preview | 已有主要状态机 | 需要纳入听力/口语/发音并验证一致性 | 与当前 Japanese 行为对齐，保持英语毕业字段白名单 |
| `total_training_dashboard` | 多训练线、多专用视图、今天/次日语义 | 只有简化类型展示 | 听力、口语、发音在看板不可操作 | 补齐英语多训练线视图和英语字段公式 |
| Agent Skill | 五类自然语言任务与风险确认策略 | 对听力、口语使用拒绝话术 | 用户无法用一致方式操作 | 改为完整英语日常操作入口 |
| Vault 初始化 | Japanese dry-run planner | 无 English planner | 无安全脚手架计划 | 新增 English dry-run planner，行为与 Japanese 相同 |

## 4. 对齐原则

### 4.1 对齐行为，不复制语言学字段

共享行为包括 SRS 生命周期、写入保护、来源追踪、查重顺序、preview/apply、人工内容保护和看板到期语义。语言专属内容留在 pack：

| Japanese | English | 说明 |
| --- | --- | --- |
| `reading` | `ipa` | 英语不伪造假名式读音 |
| `accent_display` / pitch accent | `word_stress` | 单词重音属于英语 pronunciation accent role |
| `jlpt` | `cefr` | 等级体系不同 |
| `jp_text` | `en_text` | 口语目标语言字段独立 |
| 日语接续、汉字差异 | 英语词性、英英释义、collocations | 不进入通用 core |
| 日语短句选择题启发式 | `N/A` | 当前为日语考试材料专属，不强行迁移 |

### 4.2 English pack 不依赖 Japanese runtime

English workflow 与 validator 可以遵循相同契约，但不能 import Japanese 模块。这样修复一个语言包时仍需显式同步另一个语言包的行为证据，避免运行时静默回退和字段污染。

### 4.3 风险确认策略保持一致

- 明确创建新听力、来源和口语材料时，在目标不存在且预览通过后可保存；
- 修改已存在笔记、合并、移动、覆盖或更新复习状态时需要确认；
- 清晰的当日复习结算不二次询问，必须执行 `preview -> apply -> second preview`；
- 听力抽取语块与把语块提升为口语卡是两次独立用户任务；
- 人工整理的正文、听力选择、来源说明和每日总结不得被窄任务覆盖。

## 5. 文件级实施方案

### 5.1 Manifest、字段与模板

修改：

- `lingotrace/packs/english/manifest.json`
- `lingotrace/packs/english/fields.json`
- `lingotrace/packs/english/templates/focus-vocab-card.md`

新增：

- `lingotrace/packs/english/templates/grammar-card.md`
- `lingotrace/packs/english/templates/error-card.md`
- `lingotrace/packs/english/templates/speaking-card.md`
- `lingotrace/packs/english/templates/chunk-card.md`

manifest 将全部 Phase 0 capability 声明为 `stable`，`unsupported_capabilities` 为空。英语字段包含 IPA、word stress、part of speech、English definition、中文释义、collocations 以及口语 chunk 字段。模板正文必须可直接复习，不能只有 frontmatter 或空标题。

### 5.2 Review materials

`lingotrace/packs/english/workflows.py` 和 `validators.py` 实现以下链路：

1. 校验 English Vault context 和 `review_materials` capability；
2. 先查 focus，再查 base，避免创建重复卡；
3. 将词汇、语法、错题、单词重音、音素对比路由到配置中的 path role；
4. 为新卡初始化 `day0`、到期日、计数和来源；
5. 对已掌握 focus 卡重新激活；base 命中时恢复到 focus，不直接污染 mastery sink；
6. 解析来源和可选关联，只生成唯一、角色正确的规范 wikilink；
7. 缺失或歧义的可选关联保留为纯文本待补项，不生成悬空链接；
8. 图片词汇只接受实际可读附件和结构化 visual/manual evidence；
9. 每日清单作为显式独立输入，只更新受管理区块，不修改卡片 SRS；
10. 对现有卡的任何 mutation 要求 `existing_update_confirmed=True`，并保留人工语义正文。

### 5.3 Speaking cards

英语口语支持两种条目：

- `speaking_card`：用户直接提供的完整实用表达；
- `chunk`：用户已经离线复核、从听力材料提升的可替换表达骨架。

工作流递归搜索 `speaking_card_root`，优先按 `chunk_pattern` 去重，再比较 `en_text`。已存在时只合并有价值的来源、音频和例句，保留复习状态与人工正文。新鲜 ASR 片段不能在同一听力任务中直接进入口语库。

### 5.4 Listening notes 与官方工具

官方入口 `tools/listening-transcribe-official/transcribe_listening.py` 进行 pack-aware 泛化：

- `--locale` 默认值改为 `auto`；
- 从 `.lingotrace/vault-context.json` 推断 Japanese `ja-JP` 或 English `en-US`；
- English 路径不加载日语重音词典和确认重音索引；
- 双 ASR 比较和 LLM merge request 保留实际 locale，并使用英语语义与功能词提示；
- 英语句子切分支持英文句号、问号和感叹号；
- 英语新笔记使用 `en/listening` 标签和“英文语块骨架”说明；
- apply 阶段按 `language_pack` 调用 English 或 Japanese `listening_notes`，未知 pack 明确失败；
- 泛听不强制切片；精听必须有可靠时间戳和真实切片引用；
- 低置信度专名、数字、同音词或边界继续阻断最终笔记，不伪造确定答案。

### 5.5 Review rollover

English rollover 扫描词汇、语法、错题、口语、听力、单词重音、音素和每日记录角色：

- `done_today: true` 且在允许延期内：进入下一阶段；
- 超过允许延期：按规则重新排期，不错误晋级；
- 未知阶段或非法日期：在规划阶段阻断全部写入；
- `day180` focus vocabulary：以英语稳定字段白名单下沉到 base，保留人工正文和来源；
- apply 后第二次 preview 必须没有剩余计划写入。

### 5.6 Total Training Dashboard

`lingotrace/packs/english/views/total-training.base` 保留 Japanese dashboard 的 today/next-day 到期语义，并提供：

- 今日总训练；
- 重点复习高风险；
- 生活口语待练；
- 听力待精听；
- 发音待录音；
- 单词重音待练；
- 音素待练；
- 最近新增；
- 重复出现 / 反复出错。

公式使用 English pack 字段 `en_text`、`ipa`、`word_stress`、`english_definition`、`collocations`、`chunk_pattern` 和 `chunk_meaning_zh`。不得退化成仅按 `status == active` 展示的宽泛“今日训练”。

### 5.7 English Agent Skill

`lingotrace/packs/english/agent_skills/SKILL.md` 成为英语日常自然语言入口，覆盖听力、来源、复习卡、口语卡、结算和 dashboard 意图。用户无需知道 workflow 函数、JSON envelope、mode 或命令参数。

### 5.8 Vault 初始化计划

新增 `lingotrace/init/english_vault.py`，从 English manifest 和 `paths.json` 生成无写入 dry-run 计划，包括：

- `.lingotrace/vault-context.json`；
- `.lingotrace/paths.json`；
- 所有角色目录；
- pack 模板；
- `views/total-training.base`。

与 Japanese planner 一样，已有目标文件一律报告冲突，不覆盖用户内容。实际私人 Vault 的 apply 仍应由 Agent 在用户明确提供 Vault 路径后按计划执行并验证。

## 6. 验证矩阵

必须通过：

```bash
PYTHONPATH=. python3 -m unittest discover -s tests/lingotrace -p 'test_*.py'
python3 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
python3 -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh
```

英语专项证据至少覆盖：

- 六项 capability 均为 stable，且没有 unsupported capability；
- English workflow 源码不引用 Japanese runtime；
- 新听力 bundle 的 note 与 slice 只能写入 `listening_root`；
- 官方工具自动推断 `en-US`、输出英语标签，并经 English guard apply；
- vocabulary、grammar、error、word stress、phoneme 路由正确；
- focus/base 查重、mastered reactivation、现有卡确认和人工正文保护；
- 结构化图片证据与每日清单隔离；
- speaking chunk 在复核后创建并按 pattern 去重；
- rollover 全阶段、延期、非法状态阻断、day180 sink 和 second preview；
- dashboard 暴露所有训练线及 English 字段提示；
- English Vault 初始化 dry-run 完整且不覆盖已有文件。

## 7. 明天开始学习英语的最短路径

### 7.1 一次性准备

1. 更新到包含本实施的合并后 `main`。
2. 准备独立的英语 Obsidian Vault；一个 Vault 只选择一个 target language。
3. 让 Agent 根据 `plan_english_vault_initialization(<英语 Vault>)` 的预览落地配置、目录、模板和 Base；遇到已有文件时先确认，不覆盖。
4. 让 Agent 读取 `lingotrace/packs/english/agent_skills/SKILL.md` 作为日常入口。
5. 若要处理音频，按 `docs/listening-runtime-isolation.md` 准备 ListenKit 与官方听力运行时；只做文章/卡片/复习结算时不依赖 ASR。

### 7.2 第一天建议闭环

按顺序向 Agent 说：

1. “帮我把这篇材料整理成英语学习笔记。”
2. “把这几个词加入复习，并保留文章里的例句和来源。”
3. “把这段音频做成英语泛听笔记。”或“做成英语精听稿。”
4. 听完并人工选择语块后：“把我已经 review 的这些语块转入口语库。”
5. 在 `views/total-training.base` 完成今日卡片并勾选 `done_today`。
6. “今天复习结束了，帮我结算。”

### 7.3 可用性边界

- 没有实际英语 Vault 路径时，本 PR 不创建私人学习数据；
- 没有 ListenKit/ASR 时，来源笔记、复习卡、口语卡、看板和结算仍可用，音频转写会在写入前明确停止；
- 仓库测试能证明 guard、路径、状态机和渲染契约，不能替代真实音频的语言质量验收；
- 英语不实现日语 pitch-accent 标注和日语考试短句选择题专用启发式，改用英语 word stress/phoneme 卡和通用听力链；这属于语言差异，不是功能缺口。

## 8. 后续非阻断改进

以下事项不阻断明天开始真实英语学习：

- 用更多真实英语音频扩充手工质量样本，特别是专名、数字、连读和弱读；
- 在 Japanese 与 English 两个实现长期稳定后，评估把重复的纯契约代码抽到 core，避免过早泛化；
- 为 English 初始化增加独立 CLI apply 命令；当前与 Japanese 保持相同的安全 dry-run planner 边界；
- 第三语言接入时再泛化 core 支持语言列表、initializer 和 listening locale registry。
