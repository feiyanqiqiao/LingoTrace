# LingoTrace 产品需求与架构白皮书 (PRD)

## 1. 产品愿景与定位 (Product Vision & Positioning)
### 1.1 产品目标
LingoTrace 是一个完全构建在 Obsidian 知识库之上的、端到端的日语学习与记忆管理工作流系统。它的核心目标是：将任何来源的日语输入（如播客、YouTube、教材录音）自动化转化为可阅读、可交互的结构化笔记，并通过内建的间隔重复系统（SRS）和图谱关联，将这些信息提纯为用户的长时记忆与真实的口语输出能力。

### 1.2 产品设计理念
1. **输入与加工解耦**：底层音频处理和语音识别（ASR）完全外包给子项目 ListenKit，LingoTrace 仅作为“记忆的加工厂”。
2. **人机协作的边界感**：系统极大地缩减了排版、查词、标记和时间戳对齐等体力活，但在“常用句挑选”、“重音确认”等强关乎语感和肌肉记忆的节点，强制保留“人类确认”的环节。
3. **知识流转的生命周期**：一条信息在系统内的流转不是孤立的。听力素材 -> 变成笔记 -> 提取出词汇/语法 -> 进入每日复习 -> 180 天后下沉为基础图谱（Sink）/ 提取为口语生存卡，整个流程高度闭环。

---

## 2. 核心模块详细说明 (Detailed Module Specifications)

LingoTrace 系统由五个核心的 Codex Skills 组成，下面对每个模块的产品逻辑进行逆向剖析。

### 2.1 听力剧本生成模块 (`jp-listening-script-generator`)
**定位**：将固定篇幅的听力音频/视频转化为可作为基座的“精听或泛听笔记”。

#### 2.1.1 核心业务流
1. **触发处理**：传入本地音频文件或 URL，调用 ListenKit 进行 ASR 识别。
2. **多模式支持**：
   - **泛听模式 (Extensive - 默认)**：生成一份带有本地词典离线重音候选（`accent_display`）的纯文本脚本（`## 脚本`）。不生成切片，保持全文连贯。
   - **精听模式 (Intensive)**：基于 ListenKit 产出的时间戳切片集（`.slices.json`），将整个语料切割。生成 `## 精听学习包` 区域，每个学习块由 `### SNN` 标题、一段带重音标记的句子以及一个单独裁剪的 `.m4a` 语音嵌入组成，完美解决传统播放器“拖进度条跟读定位难”的痛点。
3. **强制提纯提取**：系统不仅生成原始转写，还必须执行“第二阶段审核”：让模型挑选 0-5 句兼具可复用性和结构的“可直接背的常用句”，并输出对应的“可替换骨架”和“使用场景”。

#### 2.1.2 异常与特殊处理
- **离线词典依赖**：重音查询必须依赖本地离线词典（如 `fugashi` 和 `unidic-lite`），以防止过度联想，并且必须处理多音和无对应词的情况（未知时打上“待确认”标记）。
- **短句选择题适配**：如果音频是选择题模式（如 1/2/3 选项），系统会自动适配并保留选项题号结构，而非强制合并为段落。

---

### 2.2 泛学习来源处理模块 (`jp-source-note-generator`)
**定位**：针对非固定格式的音视频资源（科普视频、脱口秀等）的泛知识萃取引擎。

#### 2.2.1 核心业务流
1. **生成材料包**：生成 Artifact 目录，存放原始文件、Markdown Transcript 和 JSON Transcript。
2. **协商与定制**：由于源材料内容不可预知，大模型在生成笔记前，需分析材料并与用户确认：这份材料的核心是偏向语法、词汇、表达方式，还是偏向全文脉络？
3. **数据血缘 (Provenance) 绑定**：不管笔记的主体形态如何千变万化，必须在附录（如 `## 附录：转写脚本`）完整保留 ListenKit 生成的原始识别文本、音视频来源 URL 及本地存档嵌入 `![[audio.m4a]]`。

---

### 2.3 复习卡片库与图谱维护模块 (`jp-review-material-maintainer`)
**定位**：系统的“数据库网关”，负责提炼、新建、更新知识卡片，并防范冲突。

#### 2.3.1 核心业务流与双层架构
维护器最大的特色是其独创的**双层词汇系统（Dual-Layer Vocabulary）**：
1. **Focus Review 层 (焦点复习区)**：新遇见的生词或再次做错的旧词进入此区域，带有严格的 `review_stage` 属性（如 day0），每天参与排期。
2. **Base Lexicon 层 (基础词汇库)**：作为知识的长时存储库。

#### 2.3.2 卡片检索与防重逻辑
- 当系统需要保存新词时，执行强制检索顺序：
  1. 优先检索焦点区（Focus Root）。若匹配，视为复习任务，增加 `seen_count`，重置进度。
  2. 检索基础区（Base Root）。若匹配，将卡片“捞出”，将 Base 卡标记为 `promoted`，在 Focus 区重建卡片并重置 `review_stage: day0`。
  3. 两者都不存在，才创建新 Focus 卡片。

#### 2.3.3 支持的特殊卡片类型
- **汉字差异卡 (`kanji_diff`)**：专门针对“日文汉字”与“简体中文”容易混淆的现象（如 複/复），不记录全词，只记录确切的字对 `kanji_diff_pairs`。
- **关联比较图谱**：系统遇到近义词或容易错的组合时，填充 `confusable_with` (词汇) 或 `contrast_with` (语法) 属性，建立 Obsidian Wikilink 实现双向链接。
- **错题卡 (Error Cards)**：固定模板 `## 错误理解` -> `## 正确理解` -> `## 为什么错`，强调复盘机制。

---

### 2.4 生存口语卡片提炼模块 (`jp-survival-speaking-card-generator`)
**定位**：系统唯二的输出节点，将精听后的“常用句”升维成真实的“肌肉记忆”。

#### 2.4.1 核心业务流
1. **准入评估**：不是所有的“漂亮句子”都能成为卡片。系统遵循保守策略：句子必须具有极其明确的真实场景（如“点餐”、“看病”、“职场”）、特定的发话者角色（self / staff / other），并且能在 1 秒钟内脱口而出。
2. **挂载发音锚点**：对于从 Shadowing 笔记中提升的句子，系统可以直接引用原句的精听音频切片（如 `![[audio_stem_SNN.m4a]]`），让口语卡片具备天然的原声带。
3. **独立收纳**：归入独立的“生活口语句库”特定场景文件夹下。

---

### 2.5 SRS 次日复习更新引擎 (`jp-next-day-review-updater`)
**定位**：取代 Anki 的 Obsidian 本地内建间隔重复调度中心（Cron Job / Runner）。

#### 2.5.1 核心排期算法
所有的 Review 卡片都挂载了以下核心属性：`status`, `review_stage`, `done_today`, `last_reviewed`, `next_review`。
- **进阶链条**：完成当日复习的卡片（`done_today: true`），按固定天数推进：`day0 -> day1 -> day3 -> day7 -> day14 -> day30 -> day90 -> day180 -> mastered`。
- **惩罚/容差机制 (Delay Rule)**：
  如果用户几天没复习，系统会计算 `overdue_days` 和 `allowed_delay` (当前阶段的间隔期)：
  - 如果超期时间不严重（`<= allowed_delay`），顺利晋升下一级。
  - 如果严重拖延（`> allowed_delay`），不予晋升，卡片停留在当前 Stage，并将下一次复习时间往后顺延。这种算法非常宽容，防范了 Anki 常见的“积累几千张卡片导致复习破产”的问题。

#### 2.5.2 词汇“下沉”机制 (Sink Flow)
一旦词汇类卡片突破了 180 天的考核期（完成 `day180`），引擎会自动触发“归档下沉”：
1. 将 Focus 卡片的属性改为 `status: mastered`，清理调度属性。
2. 在 Base Lexicon 创建/更新对应的实体，标记为 `status: promoted`。
3. 该词汇彻底脱离日常苦海，成为用户长期记忆词典的一分子。

#### 2.5.3 闭环交付日志
所有的状态变更都会在当日的学习日记中（`笔记/YYYY.M/YYYY.M.D.md`）自动写入尾部数据报表：
- `## 今日完成`
- `## 今日卡点`
- `## 简短复盘`
做到当日事当日毕，学习流向透明。

---

## 3. 核心实体与元数据约束 (Core Entities Data Dictionary)

LingoTrace 高度依赖 YAML Frontmatter 进行数据治理，以下是关键卡片的强制数据结构：

### 3.1 词汇卡片 (Vocabulary Card)
```yaml
track: class_review         # 学习主轨
item_type: vocab            # 类别
status: active              # 状态: active / mastered
priority: normal            # 优先级: normal / high
done_today: false           # 当日是否复习
headword: "言葉"            # 词头
reading: "ことば"            # 假名发音
accent_display: "ことば②"   # 重音数据，来自离线词库或人工确认
meaning_zh: "语言；话语"     # 释义
source_notes:               # 溯源：初次遇见的笔记，或后续多次犯错的笔记
  - "[[笔记/2026.4/2026.4.14]]"
first_seen: 2026-04-14
last_seen: 2026-04-14
seen_count: 1               # 统计遇到频率
error_count: 0              # 统计错误频率，决定 priority
review_stage: day0          # SRS 阶段
next_review: 2026-04-14
last_reviewed: ""
confusable_with: []         # 混淆词关联
kanji_diff: false           # 是否包含中日汉字字形差异
kanji_diff_pairs: []        
tags:
  - jp/vocab
  - jp/class_review
```

### 3.2 语法卡片 (Grammar Card)
独有属性：
- `pattern`: 核心语法点。
- `formation`: **YAML List 格式** 的接续规则。
- `contrast_with`: 近义语法对比图谱锚点。
- Tags 可包含 `jp/high_risk` 代表测试常错的高频危险语法。

### 3.3 错题卡片 (Error Card)
独有属性：
- `wrong_form`: 用户的错误写法或理解。
- `correct_form`: 正确答案。
- `reason`: 原因解析复盘。
- `related_items`: 触及的知识点关联。

---

## 4. 产品护城河与非功能性设计 (Non-Functional Requirements)

1. **强防御性执行（Dry-run First）**
   对于修改量极大的操作（尤其是 SRS 的 `jp-next-day-review-updater` 排期引擎），系统被设计为默认必须跑 `--dry-run` 空跑模式。等待观察输出数据量、阶段转换指标合理后，再执行真实的覆盖，防范批量污染。
2. **不可篡改的单向流动**
   系统的操作指令是单向流动的。生词必定是从源笔记 -> Focus -> Base 下沉，只有发生错误时才会逆流。通过 `obsidian-cli` 执行精细化的 `property:set` 而不是粗暴地覆盖整个文件，保护了用户的自定义注解不丢失。
3. **权限与沙箱策略**
   涉及到 Apple Speech 引擎的麦克风或识别调用，以及可能产生跨目录调用的动作，要求显式进行 Escalated Execution 权限授予，确保 Obsidian Vault 环境的代码安全。
