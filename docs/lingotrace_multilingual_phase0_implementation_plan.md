# LingoTrace 多语言架构阶段 0 实施方案

> **For agentic workers:** 实施本方案时，使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务推进，并在每个 Pull Request 合并前完成独立评审。

**Goal:** 冻结当前日语系统事实，区分必须迁移的学习语义与已知缺陷，建立可执行的迁移验收基线，并固化阶段 1 必须遵守的多语言架构和日语迁移契约。

**Architecture:** 阶段 0 采用“现状与资产基线 -> 日语特征和迁移验收测试 -> 目标与迁移契约”的顺序推进。冻结表示所有行为变化都必须经过显式评审并同步更新证据，不表示停止项目迭代，也不冻结私人学习资料的日常新增。此阶段不建立多语言运行时、不执行私人数据迁移，也不删除旧框架；阶段 0 自身的三个 PR 不主动改变现有日语工作流行为，发现的缺陷通过独立修复 PR 处理。

**Tech Stack:** Markdown、Obsidian Frontmatter、Python `unittest`、Shell、GitHub Actions。

---

## 1. 文档定位

本文是 [LingoTrace 多语言架构总体规划方案](lingotrace_multilingual_architecture_plan.md) 的阶段 0 实施来源，负责定义阶段 0 的交付物、Pull Request 顺序、测试策略、协作门槛和完成标准。

文档状态：**规划已确认，尚未进入实施阶段**。

相关现状来源：

- [功能模块与用户旅程审计报告](lingotrace_audit_report.md)
- [产品需求与架构白皮书](lingotrace_product_document.md)
- [多语言与多 Agent 早期研究](lingotrace_multilingual_multiagent_design.md)
- `codex-skills/jp-listening-script-generator/SKILL.md`
- `codex-skills/jp-source-note-generator/SKILL.md`
- `codex-skills/jp-review-material-maintainer/SKILL.md`
- `codex-skills/jp-survival-speaking-card-generator/SKILL.md`
- `codex-skills/jp-next-day-review-updater/SKILL.md`

本文不替代上述 Skills。记录当前工作流事实时，Skills、模板、脚本和现有测试仍是行为证据来源。

## 2. 阶段目标与边界

阶段 0 必须完成：

1. 记录五个日语工作流的当前输入、输出、状态变化、失败方式和完成标准。
2. 标记当前实现中的核心候选、Japanese 专属逻辑和混合区域。
3. 建立不依赖私人学习数据的日语行为特征测试。
4. 固化 Vault 上下文、语言包声明、公共复习卡外壳、能力状态、字段所有权、路径优先级和写入安全契约。
5. 区分必须迁移的私人学习资料、由新框架重建的系统资产、需要显式转换的内容、临时迁移工具和切换后删除的旧框架资产。
6. 定义全新 Japanese Vault 的源到目标迁移契约、验收证据和旧框架退出清单。
7. 建立阶段 1 的准入门槛，使后续贡献者可以一致判断需求归属。

阶段 0 明确不实施：

- 不建立 Vault 配置加载器或语言包运行时。
- 不创建 English 语言包、英语模板或英语学习功能。
- 不重命名 `codex-skills` 或现有 `jp-*` Skills。
- 不改写 `reading`、`accent_display`、`kanji_diff` 等日语字段。
- 不移动现有日语路径、模板或私人学习数据。
- 不初始化正式的新日语 Vault，不执行私人数据复制、切换或删除。
- 不为旧框架设计长期运行模式、隐式配置回退或永久兼容层。
- 不把 PR #14 作为代码基底继续扩展。
- 不用测试或文档改动顺带重构现有工作流。

### 2.1 “冻结”的准确含义

阶段 0 冻结的是**未经评审即可变化的行为**，不是冻结仓库或停止日语学习系统的正常迭代。

当前私人 Vault 可以继续学习、录入和复习。阶段 0 只定义数据分类和源清单格式，不把某一天的私人数据内容固化进公共仓库。真正的源 Vault 写入冻结、最终清单生成和迁移执行属于阶段 2 的短期切换窗口。

阶段 0 期间仍然允许：

- 修复已确认缺陷。
- 补充现有日语工作流的测试、验证器和文档。
- 在不改变用户可见行为的前提下维护脚本和依赖。
- 继续进行与多语言架构无关、且不会触碰同一文件的独立小范围迭代。
- 经评审后调整现有日语行为，并在同一个 PR 中同步更新基线、证据、自动测试或人工案例。

行为变化按照以下规则处理：

1. 纯实现重构且用户可见行为不变：保留原行为编号，更新证据位置并运行完整基线。
2. 修复与 Skill、模板或已确认契约不一致的缺陷：保留对应行为编号，在差异台账中记录修复结论，并更新测试证据。
3. 有意改变用户可见行为：PR 必须说明旧行为、新行为、迁移影响和回退方式；旧行为标记为被替代，新行为使用新编号，并同步更新迁移验收基线。
4. 只改变私人学习数据：不更新公共基线，也不得进入公共仓库。
5. 变更触及阶段 0 当前正在编辑的同一文件时：先合并较早 PR，后续分支更新到最新 `main` 再继续，不维持长期并行修改。

阶段 0 的三个架构 PR 仍保持严格顺序；普通项目迭代可以在其间合并，但后续阶段 0 分支必须更新到最新 `main` 并重新运行相关验证。

## 3. 前置条件与协作规则

阶段 0 开始前：

- 总体规划必须已经通过评审并合并到 `main`。
- 本地 `main` 必须跟踪最新 `origin/main`，工作区保持干净。
- 郑杰的 PR #14 保留为早期原型参考，阶段 0 期间停止追加，不合并，也不作为新分支的起点。

三个实施 Pull Request 必须严格顺序执行：

```text
PR A：现状事实基线
  -> 合并到 main
PR B：日语行为特征测试
  -> 合并到 main
PR C：目标契约与阶段 1 门槛
  -> 合并到 main
```

每个 Pull Request 都必须：

- 从已经包含前序成果的最新 `main` 创建独立 topic branch。
- 只包含该 Pull Request 的公开允许文件。
- 由项目维护者与郑杰共同确认后合并。PR 作者的提交视为作者确认，另一方必须留下批准评审或明确的同意评论。
- 通过 `bash tools/git/check-public-staged-files.sh --range origin/main...HEAD`。
- 合并后切回 `main`、更新本地分支并清理已完成 topic branch。

阶段 0 期间的其他 Pull Request：

- 若不改变已记录行为，按现有 `AGENTS.md` 流程正常评审和合并。
- 若改变已记录行为，必须同步修改行为基线和对应测试或人工案例。
- 若只是把实现恢复到已经声明并确认的 SRS 或路径行为，可以作为独立缺陷修复 PR 推进。
- 若要改变公共卡片外壳、SRS 语义、Vault 上下文、语言包接口或公共路径角色，必须等待 PR C 的契约评审，不能以普通维护 PR 绕过架构边界。

## 4. PR A：冻结日语现状

**Branch:** `codex/phase0-japanese-baseline`

### 4.1 预定新增文件

- `docs/multilingual/phase-0/current-state-baseline.md`
- `docs/multilingual/phase-0/workflow-evidence-index.md`
- `docs/multilingual/phase-0/baseline-discrepancies.md`
- `docs/multilingual/phase-0/migration-scope-and-asset-inventory.md`

`current-state-baseline.md` 记录工作流事实；`workflow-evidence-index.md` 维护行为编号与 Skill、模板、脚本、测试之间的证据映射；`baseline-discrepancies.md` 记录实现、Skill、模板和测试之间的差异及其处理结论；`migration-scope-and-asset-inventory.md` 记录公开系统资产和私人数据类别在迁移中的去向。即使未发现差异，也保留差异文件并明确记录审查结果为无未解决项。

四个文件的页首都必须记录 PR A 创建时的 `origin/main` 提交 SHA 和基线日期。该 SHA 是初始事实快照，不随 PR A 的文档提交变化；后续行为变化通过修订记录更新，不覆盖初始快照身份。

### 4.2 行为编号

使用稳定前缀标识五个工作流：

```text
JP-LISTEN-*    固定听力笔记
JP-SOURCE-*    灵活来源笔记
JP-REVIEW-*    复习材料维护
JP-SPEAK-*     生活口语卡维护
JP-ROLLOVER-*  每日复习结算
```

编号一经 PR A 合并不得复用。纯实现变化继续使用原编号；用户可见语义发生变化时，旧编号保留并标记为 `superseded`，新行为使用新编号。

### 4.3 每项行为的记录结构

每个行为条目必须包含：

- 行为编号和名称。
- 用户触发条件与工作流入口。
- 输入、前置检查和可选参数。
- 确定性脚本步骤与模型判断步骤。
- 输出文件、Frontmatter 和正文结构。
- 状态变化、路径角色和外部工具依赖。
- 明确失败、待人工确认和完成条件。
- 重复执行、查重和人工内容保留规则。
- 当前证据来源。
- 证据状态和迁移状态。
- 所属边界分类。

证据状态只允许：

```text
declared   仅由 Skill、模板或文档声明，尚无可执行或人工案例证据
observed   已通过当前脚本、样例或只读操作复现
verified   已有自动测试或版本化人工案例稳定验证
```

迁移状态只允许：

```text
candidate           已识别，但尚未决定是否必须在新框架中复现
migration-required  双方确认且已有 verified 证据，新框架必须复现学习语义或经过显式替代评审
known-defect        已确认与预期不一致，不进入迁移承诺，必须在 PR C 前解决
superseded          已被新行为替代，仅保留历史记录
```

状态约束：

- `migration-required` 必须同时具备 `verified` 证据。
- 版本化人工评审案例只有在双方记录接受结果后才能计为 `verified`。
- 用户可见的现有工作流行为不能长期停留在 `candidate`；阶段 0 完成时必须成为 `migration-required`、`superseded`，或先以 `known-defect` 修复后再归类。
- `candidate` 只允许用于非用户可见的实现细节或尚无第二语言证据的核心候选，并必须记录不进入迁移承诺的原因。

边界分类只允许：

```text
core-candidate       跨语言语义可能稳定，但尚未进入公共核心
japanese-specific    日语模板、字段、词典、自然度或语言规则
mixed-current        当前代码同时承担通用与日语职责，阶段 1 前不得直接抽取
migration-source     仅作为迁移来源、行为证据或迁移期入口，不进入目标运行时
remove-after-cutover 仅服务旧框架，完成切换后必须删除
external-tool        ListenKit 或其他外部工具边界
```

### 4.4 迁移资产分类

`migration-scope-and-asset-inventory.md` 必须把已知资产归入且只归入以下一类：

```text
preserve-data        私人学习资料、媒体、人工内容、来源关系和 SRS 状态，默认原样迁移
recreate-from-pack   新核心或 Japanese 包重新生成的模板、配置、Bases 和系统文件
transform-with-map   只有满足明确强制条件时才转换，并要求映射、预览和验收证据
temporary-migration  只在清单、复制、对比或切换期间使用，验收后删除
remove-after-cutover 旧仓库、旧 Skills、旧包装脚本、隐式配置和其他旧框架资产
```

资产清单必须覆盖当前公开仓库结构、五个工作流入口、模板与配置、测试与工具，以及私人 Vault 中需要保留的数据类别。公共文件只记录类别、规则和公开路径，不记录真实私人文件名、内容、数量或个人绝对路径。

### 4.5 差异分类与处理

审查当前事实时，必须区分：

```text
implementation-gap   目标架构尚未实现，例如当前没有语言包加载器
behavior-discrepancy 当前代码行为与 Skill、模板或已确认用户行为不一致
contract-conflict    两个规范来源对所有权、状态或失败规则给出互斥要求
documentation-drift  文档路径、命令或描述落后，但运行行为没有改变
```

处理规则：

- `implementation-gap` 分配到阶段 1 或后续阶段，不视为阶段 0 冲突，也不得在阶段 0 提前实现。
- `documentation-drift` 在 PR A 中修正文档或证据链接，不改变运行行为。
- `behavior-discrepancy` 标记关联行为为 `known-defect`，通过独立修复 PR 解决并补充测试。
- `contract-conflict` 必须由双方明确选择唯一规则，并同步修正冲突来源。
- PR C 合并前不得存在未解决的 `behavior-discrepancy` 或 `contract-conflict`；允许存在已经明确归属后续阶段的 `implementation-gap`。

### 4.6 五个工作流的最低记录范围

#### 固定听力笔记

- 本地音频和 URL 输入路径。
- ListenKit 产物和来源关系。
- 泛听、精听和切片生命周期。
- `segment_count`、`### SNN`、音频嵌入和真实切片文件的一致性。
- 重跑时保留人工挑选句和额外章节。
- ASR、时间戳、字典或导出工具异常时的停止条件。

#### 灵活来源笔记

- 纯文本、ListenKit Markdown、媒体和 URL 输入。
- 原始来源、最终音频、转写 Markdown、结构化 JSON 和音频嵌入的追踪关系。
- 正文结构可变但转写附录必须保留的约束。
- 一篇或多篇笔记的用户决策点。
- 来源笔记完成后再进入复习卡工作流的边界。

#### 复习材料维护

- Focus 层优先、Base 层其次的检索顺序。
- 词汇、语法、错题和发音材料的路由。
- 新建、更新、重新激活、查重和词汇下沉。
- 日语字段、来源、对比链接和人工正文保留。
- 不确定词头、核心含义或语法接续时的停止条件。

#### 生活口语卡维护

- 只接受人工确认材料或用户直接提供表达。
- `jp_text` 和核心表达防重。
- 场景子目录、说话角色、功能、来源和音频引用。
- 场景指南与复习卡队列隔离。
- 自然度、礼貌、语域和实用价值的人工判断边界。

#### 每日复习结算

- 完整 SRS 阶段链和延期规则。
- 只处理 `status: active` 且 `done_today: true` 的项目。
- `last_reviewed`、`review_stage`、`next_review` 和 `done_today` 更新。
- `day180` 词汇下沉及日语扩展字段保留。
- 每日学习清单的局部改写边界。
- 缺失字段、未知阶段和路径异常时停止写入。

### 4.7 PR A 验收

- [ ] 五个工作流均包含完整行为条目。
- [ ] 每个行为编号至少链接一项真实证据。
- [ ] 每个行为编号都有证据状态、迁移状态和边界分类。
- [ ] 所有已知系统资产和私人数据类别均有唯一迁移资产分类。
- [ ] 旧 `jp-*` 入口、旧配置发现方式和 Vault 内嵌仓库均已登记为迁移来源或切换后删除项，而非目标接口。
- [ ] 实现差距、行为差异、契约冲突和文档漂移已经分别登记。
- [ ] 当前实现、目标架构和未来阶段没有混写。
- [ ] 文档不包含私人笔记内容、媒体、个人统计或绝对个人路径。
- [ ] 项目维护者与郑杰共同确认现状描述准确。
- [ ] 公开文件允许列表检查通过。

## 5. PR B：建立可执行日语基线

**Branch:** `codex/phase0-japanese-characterization`

### 5.1 预定新增文件结构

```text
tools/architecture-baseline/
  README.md
  fixtures/
    listening/
    source-notes/
    review-materials/
    speaking-cards/
    review-rollover/
    migration-preservation/
  tests/
    helpers.py
    test_listening_contract.py
    test_source_note_contract.py
    test_review_material_contract.py
    test_speaking_card_contract.py
    test_review_rollover_contract.py
    test_migration_acceptance_oracle.py
  manual-language-review-cases.md

.github/workflows/japanese-baseline.yml
tools/git/check-public-staged-files.sh
```

所有 fixtures 必须是合成公开数据。不得复制或匿名改写私人 Vault 中的真实笔记、音频、学习统计和个人路径。

`tests/helpers.py` 只提供测试使用的 Markdown、Frontmatter 和引用关系读取函数，不得被现有运行时或 Skills 导入。阶段 0 不借测试辅助代码建立新的生产抽象。

`migration-preservation/` 使用完全合成的源目录、目标目录和预期清单，覆盖原样保留、由语言包重建、显式转换、排除和冲突五类结果。`test_migration_acceptance_oracle.py` 只实现独立验收方使用的比较逻辑，不实现数据复制，也不得被后续迁移运行时直接导入。

PR B 必须同步更新 `tools/git/check-public-staged-files.sh` 的公开允许列表，只新增 `tools/architecture-baseline/` 这一精确目录。不得借此放宽 `tools/` 整体范围，也不得允许媒体、私人笔记或生成缓存。

### 5.2 测试层级

#### 层级一：确定性回归测试

直接测试 Python 和 Shell 可确定判断的行为：

- SRS 状态推进、延期、下沉和 dry-run。
- 路径角色解析和 Vault 边界。
- 听力模式、产物关系、切片清单和完整性检查。
- Frontmatter 字段保留、查重和状态不变量。
- 验证失败时不产生部分写入。

这里只冻结当前已声明且可以复现的日语行为。目标架构尚未实现的能力，例如语言包发现、版本协商和新 Vault 初始化，不得伪装成当前运行时测试；这些内容在 PR C 中以契约样例和合规清单表达。

#### 层级二：结构特征测试

使用合成 Markdown、Frontmatter 和 ListenKit artifact 验证：

- 必备来源信息存在。
- 必备章节、字段和引用关系成立。
- 未知扩展字段和人工正文不丢失。
- 重复执行更新原目标，不制造重复内容。
- Agent 工作流输出满足结构契约。

测试不比较模型输出是否逐字一致，也不固定允许用户定制的正文措辞。

结构 fixture 通过只能证明样例符合已写明的结构规则，不能单独证明 Agent 在真实执行中稳定遵守该规则。Agent 工作流行为只有在具备确定性验证器，或完成双方确认的版本化人工端到端案例后，才能从 `observed` 升级为 `verified`。

#### 层级三：人工语言评审案例

`manual-language-review-cases.md` 记录不能可靠自动化的案例：

- 日语表达是否自然。
- 可背句是否具有复用价值。
- 礼貌、语域和文化使用边界。
- ASR 结果是否适合作为记忆材料。

每个案例必须包含输入、接受条件、拒绝条件和对应行为编号，不包含私人原文。

#### 层级四：迁移验收预演

使用合成源 Vault 与目标 Vault 验证独立验收规则：

- `preserve-data` 文件的相对路径、内容哈希、Frontmatter、Wikilink、附件引用和 SRS 状态一致。
- `recreate-from-pack` 和 `remove-after-cutover` 资产不得被误判为私人资料并复制到目标。
- `transform-with-map` 差异必须出现在显式映射和变更清单中。
- 未声明差异、重复目标、路径越界、缺失附件或人工内容冲突必须使验收失败。
- 同一源、目标和规则重复验收得到一致结果。

该层级建立阶段 1 和阶段 2 共用的独立验收标准，不表示阶段 0 已经实现迁移工具或执行真实数据迁移。

### 5.3 五个工作流的最低自动覆盖

#### 固定听力笔记

- 泛听不生成精听包和切片。
- 精听要求有效学习块、嵌入和非空切片文件。
- 编号对话、普通对话和句子模式遵守当前分组规则。
- 不可靠时间戳明确失败或进入待人工确认状态。
- 重跑保留 `daily_use_sentences`、人工挑选章节和额外人工内容。

#### 灵活来源笔记

- 来源 URL 或路径、最终音频、转写 Markdown 和音频嵌入可追踪。
- 有转写文本时，附录位于学习正文之后。
- 纯文本且没有音频时明确记录无音频，不伪造引用。
- 来源笔记本身不自动创建复习卡。

#### 复习材料维护

- Focus 搜索先于 Base 搜索。
- 两层均无匹配时才创建新卡。
- Base 已存在时创建或恢复 Focus 卡。
- mastered 卡重新出现时恢复为 `day0`。
- 下沉保留 Skill 已声明的 `reading`、`meaning_zh`、`accent_display`、来源、时间与计数字段，并保留人工正文。
- 当前脚本和测试已经覆盖 `kanji_diff`、`kanji_diff_pairs`；PR A 必须把 Skill 未枚举这两个字段登记为文档漂移并同步证据，之后再将其标记为 `migration-required`。
- 语法和错题材料不被误写入词汇层。

#### 生活口语卡维护

- 未经人工确认的听力候选不能直接进入正式卡库。
- 卡片位于一个场景分类子目录中。
- 必备字段、正文段落、来源和音频引用有效。
- 重复 `jp_text` 或等价核心表达被拒绝或合并。
- 场景指南不能带 `track: survival_speaking`。

#### 每日复习结算

- 覆盖 `day0` 至 `mastered` 的完整阶段链。
- 覆盖正常推进和超期重排。
- 非 active 或未完成项目保持不变。
- 未知阶段和缺失必填字段导致失败。
- dry-run 不修改文件。
- 任一项目验证失败时，不留下部分状态推进。

### 5.4 GitHub Actions 门禁

`.github/workflows/japanese-baseline.yml` 必须：

- 工作流名称固定为 `Japanese Baseline`，job ID 固定为 `japanese-baseline`，job 显示名称固定为 `Japanese behavior baseline`。
- 对所有指向 `main` 的 Pull Request 和所有推送到 `main` 的提交执行，不配置 `paths` 过滤。
- 使用 `ubuntu-latest`。
- 使用 `actions/checkout@v6`、`actions/setup-python@v6` 和明确的 `python-version: '3.14'` 运行标准库测试。
- 设置 `permissions: contents: read`、`PYTHONUTF8=1` 和固定测试时区 `TZ=UTC`。
- 不读取仓库外私人 Vault。
- 不下载模型、不运行真实 ASR、不安装语言资源。
- 运行现有听力、复习结算、Vault 结构和新增架构基线测试。
- 任何失败都阻止合并，不使用 `continue-on-error` 掩盖失败。
- 同时运行公开文件允许列表检查。

工作流合并后，在 GitHub `main` 分支保护或 Ruleset 中把 `Japanese behavior baseline` 配置为 required status check。只有工作流文件存在但未设为 required，不满足“必跑门禁”的验收要求。

实施时的最低验证命令：

```bash
BASELINE_PYTHON="${LINGOTRACE_BASELINE_PYTHON:-/opt/homebrew/bin/python3.14}"
"$BASELINE_PYTHON" -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s codex-skills/jp-next-day-review-updater/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
"$BASELINE_PYTHON" -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

本地默认使用 Homebrew Python 3.14；其他环境通过 `LINGOTRACE_BASELINE_PYTHON` 显式指定 Python 3.14。CI 统一使用 `actions/setup-python` 提供的 `python` 命令。

规划修订时仓库中发现的现有测试规模：

- 听力转写测试：74 项。
- 每日复习结算测试：6 项。
- Vault 结构测试：16 项。
- 生活口语卡验证器包含只读验证和复习结算 dry-run 检查。

这些数量只说明当前发现范围，不构成通过证据。PR B 必须在可用的隔离 Python 3.14 运行时重新执行并记录结果；新增测试后不得以固定总数作为长期断言，只要求所有发现的测试通过。

### 5.5 缺陷处理

如果新增特征测试暴露当前实现缺陷：

1. 保留能够重现缺陷的失败测试。
2. 判断缺陷是否影响日语迁移验收基线或公共契约。
3. 使用独立修复 Pull Request 解决，不在 PR B 中夹带行为重构。
4. 修复合并后，从最新 `main` 更新 PR B 并重新运行完整基线。
5. 不通过跳过测试、放宽断言或静默回退把缺陷登记为通过。

### 5.6 PR B 验收

- [ ] 五个工作流都映射到自动测试或人工语言评审案例。
- [ ] 合成迁移样例覆盖保留、重建、转换、排除和冲突，并由独立验收测试验证。
- [ ] 测试仅使用合成公开数据。
- [ ] 公开文件允许列表只新增 `tools/architecture-baseline/`，并继续拒绝私人路径、媒体和生成缓存。
- [ ] 现有日语用户可见行为没有改变。
- [ ] CI 在所有 Pull Request 上执行且失败会阻止合并。
- [ ] GitHub 分支保护或 Ruleset 已将 `Japanese behavior baseline` 设为 required status check。
- [ ] main 上现有测试和新增测试全部通过。
- [ ] 项目维护者与郑杰共同确认测试代表当前日语学习语义和迁移验收基线。

## 6. PR C：冻结目标契约

**Branch:** `codex/phase0-architecture-contracts`

### 6.1 预定新增文件

```text
docs/multilingual/phase-0/architecture-contracts.md
docs/multilingual/phase-0/language-pack-conformance-checklist.md
docs/multilingual/phase-0/japanese-migration-contract.md
docs/multilingual/phase-0/old-framework-exit-checklist.md
docs/multilingual/phase-0/phase-1-entry-gate.md
docs/multilingual/phase-0/examples/v1/japanese-vault-context.example.md
docs/multilingual/phase-0/examples/v1/japanese-language-pack-manifest.example.md
docs/multilingual/phase-0/examples/v1/review-card-shell.example.md
docs/multilingual/phase-0/examples/v1/japanese-migration-manifest.example.md
tools/architecture-baseline/tests/test_contract_examples.py
```

样例文件使用当前 Japanese 系统作为唯一参考语言，以 Markdown 解释字段语义，并包含非约束性的 YAML 代码块。它们描述未来如何登记现有 Japanese 能力，不代表 Japanese 语言包运行时已经存在。`v1` 表示契约样例修订版，不表示已经实现 `vault_schema_version: 1`。阶段 0 不把 YAML、JSON 或其他序列化方式确定为最终运行格式，也不实现解析器。

`test_contract_examples.py` 只检查样例使用的公共字段、能力标识和成熟度值与契约文档一致，不尝试加载语言包或模拟阶段 1 运行时。

### 6.2 Vault 上下文契约

必须表达：

```text
vault_schema_version
target_language
explanation_language
language_pack
language_pack_version
enabled_capabilities
```

契约必须规定：

- 目标语言和解释语言分别声明。
- 每个 Vault 只绑定一个目标语言和一个语言包。
- 新 Vault 不从路径、标签或内容猜测目标语言。
- Vault 固定已验证的语言包版本。
- 只允许启用语言包已声明且依赖完整的能力。
- 缺少配置、版本不兼容或能力缺失时，在正式写入前失败。
- 新框架不存在无配置运行模式，也不得通过旧目录、标签或内容识别日语。
- 迁移工具必须分别显式接收源 Vault 和目标 Vault，不得把源 Vault 的旧配置发现逻辑带入目标运行时。

### 6.3 语言包清单契约

每个语言包必须声明：

- 稳定唯一 ID 和语言包版本。
- 目标语言和默认转写 locale。
- 兼容的核心与 Vault Schema 范围。
- 已实现能力、依赖和成熟度。
- 外部工具及其最低要求。
- 模板、Skills、验证器和语言资源入口。
- 语言专属字段、`item_type` 和标签命名空间。
- Vault 初始化所需的默认路径角色。

成熟度只允许：

```text
experimental
stable
deprecated
```

### 6.4 公共能力契约

稳定能力标识固定为：

```text
listening_notes
source_notes
review_materials
speaking_cards
review_rollover
```

未声明能力视为不支持。核心或 Agent 不得自动回退到 Japanese 逻辑，也不得静默启用未声明依赖。

### 6.5 语言包合规检查清单

`language-pack-conformance-checklist.md` 必须逐项检查：

- 身份、目标语言和语言包版本是否唯一且稳定。
- 核心版本和 Vault Schema 兼容范围是否明确。
- 每项能力是否声明成熟度、依赖和外部工具。
- 模板、Skills、验证器和语言资源入口是否存在且责任一致。
- 语言专属字段、`item_type` 和标签是否声明所有权且不覆盖核心保留字段。
- 默认路径角色是否完整，是否允许 Vault 显式覆盖。
- 缺失能力、版本不兼容和外部工具失败是否在写入前停止。
- 未知语言扩展字段和人工正文是否原样保留。
- 初始化产物是否只包含当前语言包已声明能力。
- 包内不包含私人学习数据、个人绝对路径或未声明的跨 Vault 状态。

阶段 0 的该清单是评审门槛，不是已实现的运行时合规测试。阶段 1 必须以此为输入建立可执行的语言包合规测试。

### 6.6 公共复习卡外壳

公共核心只拥有：

```text
track
item_type
status
priority
done_today
review_stage
next_review
last_reviewed
first_seen
last_seen
seen_count
error_count
source_notes
```

核心读取、更新或下沉卡片时必须：

- 保持上述字段语义稳定。
- 原样保留不认识的 Frontmatter 字段。
- 原样保留人工维护正文和来源。
- 不把 `reading`、`accent_display`、`kanji_diff*` 等 Japanese 字段改名为公共字段。
- 不通过 `jp/`、`en/` 等标签决定语言身份或 SRS 状态。

### 6.7 路径与写入安全契约

路径优先级固定为：

```text
Vault 显式路径配置
  > 语言包默认路径
```

旧 Vault 的历史路径只能由迁移清单显式列出或由只读源扫描器登记，不属于新框架运行时路径解析规则。

所有修改 Vault 的工作流遵守：

1. 绑定单个 Vault、语言包和能力上下文。
2. 只读检查配置、版本、路径、依赖和输入。
3. 生成变更预览或待写入结果。
4. 核心验证公共状态，语言包验证语言专属结构。
5. 所有验证通过后执行写入并输出报告。

失败时不得：

- 把不完整笔记标记为完成。
- 留下部分推进的 SRS 状态。
- 覆盖人工修改内容。
- 在另一个 Vault 中复用当前 Vault 的路径、缓存、查重结果或状态。

### 6.8 Japanese 迁移契约

`japanese-migration-contract.md` 必须规定：

- 迁移源是当前日语 Vault，迁移目标是由新框架初始化的全新 Japanese Vault。
- 默认保持私人学习资料相对路径、内容、人工正文、Frontmatter、Wikilink、附件、来源关系和 SRS 状态。
- Japanese 专属字段作为 Japanese 包正式 Schema 原样保留，不因通用化批量改名。
- 旧仓库、旧 Skills、旧模板、旧配置、缓存和临时产物不得随私人数据整体复制。
- 允许转换必须满足强制原因、显式映射、dry-run、逐项变更记录和可重复执行要求。
- 迁移冲突按文件停止并报告，不覆盖人工内容，也不静默跳过。
- 源清单与目标清单的结构、内容哈希策略、排除原因、用户批准项和验证报告格式明确。
- 阶段 2 切换前必须重新生成真实源清单；阶段 0 的公开样例不能替代私人 Vault 的最终清单。

`japanese-migration-manifest.example.md` 使用合成路径展示清单结构，不包含真实私人文件或个人绝对路径。

### 6.9 旧框架退出清单

`old-framework-exit-checklist.md` 必须列出并验证：

- 新 Vault 不依赖 Vault 内嵌公共仓库。
- 新 Vault 不调用旧 `codex-skills` 路径或旧 `jp-*` 运行入口。
- 新核心不包含无配置日语识别、历史路径回退或日语默认回退。
- 日常学习、定时任务和外部工具只指向新 Vault。
- 临时迁移入口、转接器和只读源适配代码已经删除。
- 公开文档不再指导用户启动旧框架。
- 旧 Vault 完成只读观察并经用户确认后删除。

退出清单只定义完成条件；阶段 0 不执行删除，阶段 2 在迁移验收后逐项关闭。

### 6.10 需求归属决策表

`architecture-contracts.md` 必须包含以下判断顺序：

1. 需求是否只改变私人学习内容？如果是，不进入公共仓库。
2. 需求是否只服务旧日语入口？如果是，只能归入临时迁移工具或退出清单；无法证明迁移必要性时不进入新框架。
3. 需求是否涉及模板、语言字段、词典、自然度、语域或语言处理？如果是，属于语言包。
4. 需求是否涉及媒体导入、ASR 或确定性切片？如果是，属于外部工具适配边界。
5. 需求是否在至少两种语言中具有相同语义、状态和失败规则？如果是，可以申请成为核心。
6. 缺少第二种语言证据时，只登记为核心候选，不建立公共抽象。

任何公共卡片外壳、SRS、Vault 上下文、语言包接口或公共路径角色变更，都需要架构评审。

### 6.11 阶段 1 准入门槛

`phase-1-entry-gate.md` 必须要求：

- PR A 和 PR B 已合并。
- Japanese baseline CI 在 `main` 上全部通过。
- 五个能力、公共字段和路径规则不存在所有权冲突。
- 语言包合规检查清单已经双方确认，并可以直接转化为阶段 1 测试任务。
- 当前日语工作流的迁移承诺有测试证据，迁移资产分类不存在未决项。
- Japanese 迁移契约和旧框架退出清单已经双方确认。
- 阶段 1 每个任务可以明确归入核心、Japanese 包、新 Vault 初始化或临时迁移工具。
- 阶段 1 不包含英语功能，也不执行真实私人数据迁移、日常使用切换或旧 Vault 删除；这些属于阶段 2。
- 阶段 1 另行编写专项设计和实施方案。

### 6.12 PR C 验收

- [ ] 所有契约字段、能力和职责都有唯一所有者。
- [ ] 版本不兼容、能力缺失和外部工具异常都有明确失败规则。
- [ ] 样例与总体规划一致，但不冒充已实现格式。
- [ ] 契约样例一致性测试通过。
- [ ] 语言包合规检查清单覆盖总体规划要求的身份、能力、字段、路径、版本和外部工具声明。
- [ ] Japanese 迁移契约明确源、目标、包含、排除、转换、冲突、清单和验收规则。
- [ ] 旧框架退出清单覆盖旧入口、隐式配置、历史路径回退、临时迁移代码、文档和旧 Vault。
- [ ] 需求归属表能判断代表性核心、Japanese、临时迁移工具、退出项和外部工具需求。
- [ ] 当前实现、Skills 和目标契约之间不存在未解决的行为差异或契约冲突；尚未实现的目标架构能力已明确登记为实施差距。
- [ ] 项目维护者与郑杰共同批准阶段 1 准入门槛。

## 7. 阶段 0 总体验收

阶段 0 只有在以下条件全部满足时才完成：

- [ ] PR A、PR B、PR C 按顺序合并到 `main`。
- [ ] `main` 上 Japanese baseline CI 全部通过。
- [ ] 每个行为编号都映射到自动测试或人工评审案例。
- [ ] 每个 `migration-required` 行为都达到 `verified`，没有 `known-defect` 状态残留。
- [ ] 所有公共字段、能力和职责都有明确所有者。
- [ ] 当前实现、Skill 规则、总体规划和阶段契约不存在未解决的行为差异或契约冲突。
- [ ] 所有目标架构实施差距都已归入阶段 1 或后续阶段，没有被误报为当前已实现能力。
- [ ] 私人数据、系统资产、转换项、临时工具和退出项均有唯一迁移分类。
- [ ] Japanese 迁移契约、合成验收样例和旧框架退出清单完整且相互一致。
- [ ] 公开仓库中没有私人笔记、媒体、转写产物、个人路径或学习统计。
- [ ] 阶段 0 的三个架构 PR 没有改变现有五个 `jp-*` Skills 和旧日语 Vault 行为；旧入口已登记为迁移证据或退出项，而非长期接口。
- [ ] 项目维护者与郑杰共同确认阶段 0 完成。

任一契约仍存在冲突、所有者不清、`migration-required` 行为缺少验证证据、迁移资产去向未决或基线测试无法稳定通过时，不进入阶段 1。目标架构和真实迁移尚未实现本身不阻止阶段 0 完成，但必须已经登记为后续阶段的实施差距。

## 8. 实施停止条件

实施过程中出现以下情况时，停止当前 Pull Request 并先解决阻断问题：

- 基线文档与真实 Skill 或脚本行为不一致。
- 测试需要读取私人数据才能成立。
- 为了让测试通过必须改变现有日语用户可见行为。
- 契约要求依赖尚未确认的 English Schema。
- 同一个变更开始同时承担核心重构、真实日语数据迁移和英语功能。
- PR #14 的代码被直接复制，但无法说明其符合最新契约。
- GitHub Actions 需要忽略失败才能保持绿色。

阻断问题应通过独立调研、修复或契约评审解决，不降低阶段 0 的验收标准。

## 9. 实施完成后的下一步

阶段 0 完成后，团队重新评估最新 `main`，为阶段 1 单独制定实施方案。阶段 1 的目标只能是建立公共骨架、Japanese 语言包、全新日语 Vault 初始化能力和集中可删除的迁移工具，不直接继续 PR #14 的大范围重构，不执行真实私人数据迁移或切换，也不提前加入英语学习能力。
