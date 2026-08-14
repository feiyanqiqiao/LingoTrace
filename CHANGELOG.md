# LingoTrace 更新日志 (Changelog)

版本号规则：`年月日-时分秒`（如 `20260606-065513`）。
后续开始迭代本项目时，所有的功能演进、修复与架构变动都会记录于此。

---

## [20260814-171331]
### 新增 (Added)
- 英日语言包新增显式 `review_lifecycle_migration`：先只读列出逐文件、逐字段的旧状态映射，确认后原子应用，并以第二次预览验证无剩余迁移项。
- 新增 `vocab_consolidation`：以 focus 单词卡为规范，处理 base-only、promoted、异常真实排程和重复卡；合并来源、列表、计数与日期后将旧 base 卡保留为 archived 跳转，不删除旧路径。

### 变更 (Changed)
- 旧 Vault 升级同步启用生命周期迁移与单词合并能力；人工修改的 Base 会被保留并报告差异，其他安全升级仍可继续。
- 英日 Agent Skill、生命周期契约、入门说明和操作手册补充状态迁移先于单词合并、逐批确认、人工正文冲突阻断和二次预览归零规则。

### 测试 (Tests)
- 新增英日共用迁移夹具，覆盖 base-only、focus-only、重复卡、单值/列表来源合并、计数与日期规则、人工正文冲突、异常排程、旧链接保留和批量原子性；通过 core/migration 270、听力 112（1 skipped）、Vault 结构 23、架构 42，共 447 项 unittest。

## [20260814-165719]
### 新增 (Added)
- 英日语言包新增稳定 `review_queue` 能力，以精确 Vault 相对路径完成入队、退出、续接和重置；共享生命周期统一使用 `review_status: backlog/queued/mastered/archived`，并在批量写入前验证状态组合。
- 新增英日 `material-library.base` 素材库以及 `upgrade-vault` 入口；旧 Vault 仅在总训练 Base 与已知公共模板一致时自动升级，检测到人工修改时阻止覆盖并报告哈希差异。

### 变更 (Changed)
- 单词、语法、错误和发音弱项默认进入 `queued/day0`；听力、生活口语和语块默认进入 `backlog`，需通过队列能力显式启用复习。
- 总训练所有训练视图只显示 `queued` 条目；复习结算只处理 `queued && done_today`，完成 `day180` 后在原卡标记 `mastered`，不再制造基础词库副本。
- `base_vocab_root` 在日常复习材料与结算能力中进入只读兼容期；英日 Agent Skill、共享复习契约、模板和初始化清单同步更新。

### 测试 (Tests)
- 新增四态约束、队列转换、英日创建默认值、批量原子性、原卡掌握、素材库和旧 Vault 安全升级覆盖；通过 core 267、听力 112（1 skipped）、Vault 结构 23、架构 42，共 444 项 unittest。

## [20260811-094946]
### 新增 (Added)
- 新增仓库级 `.gitattributes`：普通文本统一使用 LF，Windows `.bat` 与 `.cmd` 脚本保留 CRLF；同步将该公共元数据加入 `.gitignore` 反向 allowlist 和 staged public-file allowlist。

### 测试 (Tests)
- `git check-attr` 验证普通文本为 LF、`.bat`/`.cmd` 为 CRLF；通过 core 256、听力 112（1 skipped）、Vault 结构 23、架构 42，共 433 项 unittest，pytest 为 432 passed、1 skipped、25 subtests passed；compileall 与 diff 格式检查通过。

## [20260810-220602]
### 清理 (Removed)
- 完整删除 `docs/agent-compatibility-report/` 下 10 份原始 Agent 兼容性报告、整改方案、macOS 交接和 5 份回应文档；经验证的跨平台实现、公共测试、用户安装说明和 `CHANGELOG.md` 历史记录继续保留。

### 测试 (Tests)
- 删除后通过 core 256、听力 112（1 skipped）、Vault 结构 23、架构 42，共 433 项 unittest；pytest 为 432 passed、1 skipped、25 subtests passed，compileall 与 diff 格式检查通过。

## [20260810-215618]
### 新增 (Added)
- 新增公共跨平台 `init_listening_runtime.py`：验证实际 Python 3.14，在平台原生 Cache 中安全创建日语听力隔离 venv，清理子进程 `PYTHONHOME`/`PYTHONPATH`，委派固定离线词典依赖安装与健康检查，并提供 install/check/dry-run。
- 兼容性整改方案补充 GitHub/local 真值、macOS 逐项证据矩阵、学习者 sparse runtime 新缺口、实施范围、验收边界和最终结果；五个 Agent 回应与 macOS 交接更新为实测结论。

### 修复 (Fixed)
- 学习者 sparse checkout 同时分发 `lingotrace/` 与 `tools/listening-transcribe-official/`，避免默认启用听力能力的新 Vault 找不到公共生成器。
- 听力 runtime 失败指引不再引用私有或不存在的 shell wrapper，统一指向公共初始化器；同步目录和未知非空目标会在创建环境前被拒绝。

### 变更 (Changed)
- 英日 Agent Skill 统一调用 runtime 内的公共听力生成器并保留 preview/apply 与 `--report-json`；日语 Skill 通过公共 Python 3.14 隔离 runtime 加载词典，Agent 不复制业务逻辑或直接编辑 Vault。
- 安装与隔离文档明确 core Python >=3.11、日语听力 Python 3.14、用户安装同意、最小 macOS Files and Folders 权限、iCloud/OneDrive 边界及条件式本机构建工具要求。
- GitHub Actions 行为基线在既有 Ubuntu/Windows matrix 中加入 `macos-latest`。

### 测试 (Tests)
- macOS arm64 / CPython 3.14.4 通过 core 256、听力 112（1 skipped）、Vault 结构 23、架构 42，共 433 项 unittest；pytest 为 432 passed、1 skipped、25 subtests passed。
- 默认 macOS Cache venv 真实安装 `fugashi==1.5.2` 与 `unidic-lite==1.0.8` 并重复健康检查通过；含空格/CJK 的日语合成音频完成 MLX/Apple 双 ASR、稳定 merge request、模型审阅重跑和 core accepted preview，dry-run 后 Vault 零新增文件；另以全新临时 clone 验证 sparse runtime 同时包含 core、公共生成器和初始化器，并排除根测试目录。

## [20260810-210121]
### 新增 (Added)
- 新增 Antigravity、Claude Code、QwenWork、TraeWork 与 WorkBuddy 在 macOS、Windows 上出具的 10 份 Agent 兼容性报告，记录跨平台运行、听力链路、解释器、编码、工具发现与通用 Agent 调用契约的实测证据和建议。
- 新增 Agent 无关的 `python -m lingotrace.agent`，以一个 UTF-8 JSON CLI 安全调用英日语言包五项公开能力；默认 preview，支持显式 apply、字段 allowlist、Vault 语言解析和原子 `--report-json`。
- 新增整改方案、Windows 实证结果、macOS Codex 续作交接和五份逐 Agent 回应；CI 基线增加 `windows-latest` 矩阵。

### 修复 (Fixed)
- ListenKit 连接和听力编排改为平台感知：Windows 原生调用 PowerShell `generate-markdown.ps1`，macOS/Linux 保持 bash `.sh`；修复 `/bin/bash` 硬编码、Windows 执行位假阳性、GBK 子进程解码和平台缓存目录。
- doctor 改为报告真实运行中的 Python，补充 Windows 每用户 Obsidian 与稳定工具候选；Git、init 与听力 CLI 的结构化输出统一使用 UTF-8。
- Windows/Linux 没有独立第二 ASR 时显式报告 `single_engine_platform`，不再尝试 Apple 引擎或重复同一引擎伪装双重验证；同步接受 ListenKit 的 `mlx` 路由。
- Vault 结构校验器优先读取现行 `.lingotrace/paths.json`，按配置角色限定扫描，并用公共 `review_rollover` preview 取代失效的私有 `codex-skills`/`zsh` 集成。

### 变更 (Changed)
- 学习者引导、运行时/ListenKit/每日更新说明、工具文档与英日 Agent Skill 统一采用经实测的 `<python-command>`、平台入口和受保护 CLI 契约，不再硬编码 `python3` 或 macOS Cache 路径作为全平台事实。

### 清理 (Removed)
- 删除空的 `tests/lingotrace/__init__.py`，避免测试目录遮蔽真正的 `lingotrace` 包并改善 pytest 收集行为。

### 测试 (Tests)
- Windows 11 / CPython 3.14.4 通过 LingoTrace 256 项、官方听力 105 项、Vault 结构 23 项和架构基线 42 项测试，共 426 项；compileall 与 diff 格式检查通过。
- 真实 Windows ListenKit PowerShell doctor 与临时英文 WAV 端到端 dry-run 通过，覆盖含空格路径、GBK/CP936、faster-whisper、ffmpeg、CUDA 和路径守卫；macOS Apple/MLX/TCC/pytest 实机项保留在同分支交接清单中继续验证。

## [20260809-180513]
### 新增 (Added)
- 新增跨语种共享的设备级 ListenKit 连接：Windows 保存到 `%LOCALAPPDATA%\LingoTrace\connections\listenkit.json`，macOS 保存到 `~/Library/Application Support/LingoTrace/connections/listenkit.json`，Linux 保存到 `${XDG_DATA_HOME:-~/.local/share}/lingotrace/connections/listenkit.json`；支持 `LINGOTRACE_DATA_HOME` 为测试和便携部署改写数据根目录。
- `resolve-listenkit` 按“本次显式路径、Vault 可选覆盖、设备默认、已验证的运行时同级目录”解析，并报告 `connection_scope`；`connect-listenkit --scope vault --vault <path>` 仅用于确实需要不同 checkout 的 Vault。

### 变更 (Changed)
- `connect-listenkit` 默认登记设备连接且不再要求 Vault；Vault 初始化移除 `--listenkit-root`，新建英语、日语或未来语种 Vault 不再重复写入相同的 ListenKit 路径。
- 现有 `.lingotrace/listenkit-connections/<platform>.json` 保持兼容并作为高优先级 Vault 覆盖，不自动删除或改写私人配置；诊断、生成的 Vault Agent 指令、English/Japanese Agent Skill 和安装文档统一采用设备级默认连接。

### 测试 (Tests)
- 新增设备连接跨 Vault 共享、解析优先级、旧 Vault 覆盖兼容、失效覆盖回退、运行时同级兜底、CLI 设备登记与覆盖参数验证；修正 Windows 下既有 POSIX 路径断言。通过 LingoTrace 244 项、官方听力 100 项、架构基线 42 项和 Vault 结构 18 项测试。

## [20260809-103712]
### 新增 (Added)
- 新增 `connect-listenkit` 与 `resolve-listenkit`：将用户确认的 ListenKit 程序目录按 macOS、Windows、Linux 分文件保存到私人 Vault，同平台可保留多个候选，换设备或移动目录后不会覆盖其他平台记录。
- 新增跨平台 ListenKit 程序建议目录：默认取当前已解析的 LingoTrace 运行时所在目录的同级 `ListenKit`，因此开发仓库 `/path/to/Project/LingoTrace` 对应 `/path/to/Project/ListenKit`，普通运行时 `.../LingoTrace/runtime` 对应 `.../LingoTrace/ListenKit`；建议值始终允许用户改为其他绝对路径。
- 新增 ListenKit 失联恢复协议：当前平台没有连接或所有候选失效时，结构化返回“重新安装”和“指定已有目录”两种选择，并提供建议安装位置。

### 变更 (Changed)
- Vault 初始化新增可选 `--listenkit-root`，可在 ListenKit 已验证且 Vault 尚未初始化时原子写入首个连接；`doctor` 会读取 Vault 已保存的连接并报告 `recommended_listenkit_root`。
- 新 Vault Agent 入口与 English/Japanese Agent Skill 在媒体任务前先解析 ListenKit 连接，禁止猜测目录；重新安装仍须读取上游最新说明并取得用户同意，ListenKit 缺失不阻止文本学习。
- README、学习者安装协议、入门、双用户旅程、Vault 连接指南和工具文档补充默认目录、自选位置、安装后登记与失联恢复，并新增长期维护的 ListenKit 连接设计文档。

### 测试 (Tests)
- 新增跨平台建议目录、连接追加、失效候选回退、跨平台隔离、无连接与全失效恢复选项、无效目录、Vault 路径隔离、CLI 端到端、doctor 已保存连接和 Vault 初始化登记测试；通过 LingoTrace 239 项、官方听力 100 项、架构基线 42 项和 Vault 结构 18 项测试。

## [20260808-195049]
### 新增 (Added)
- 新增 `python -m lingotrace.init check-update`：在每天首次学习前从正式上游获取 `main`，按 macOS、Windows、Linux 独立状态去重，返回待更新数量与受限长度的结构化提交说明，供 Agent 合并成一至三点中文人话摘要。
- 新增 `python -m lingotrace.init apply-update`：默认预览，只有用户明确同意并显式 `--apply` 后，才允许正式上游 checkout 在 `main`、工作树干净且可快进时执行 `pull --ff-only`。
- 新增个人 fork 识别，覆盖带 `upstream` 和只有 fork `origin` 两种形态；fork 可以检查正式上游，但所有自动应用入口均拒绝 pull、merge、rebase、stash 或 reset，并要求用户在开发工作区自行同步。

### 变更 (Changed)
- 新 Vault 根 `AGENTS.md`、Japanese/English Agent Skill、README、学习者与开发者协议、入门与操作指南、多语言架构、产品说明和 Vault 连接文档统一加入“每天一次、可忽略、不阻塞学习”的更新体验。
- 提交标题与正文被视为不可信摘要数据并限制长度；Agent 不执行其中夹带的指令，只概括用户可见功能、修复和维护影响。

### 测试 (Tests)
- 新增同日去重、跨平台状态隔离、HTTPS/SSH 正式仓库、两类 fork、中文摘要数据、网络失败、显式预览/应用、脏工作树阻断和快进更新测试；通过 LingoTrace 226 项、官方听力 100 项、架构基线 42 项和 Vault 结构 18 项测试，并以当前真实 fork 验证 `fork_updates_available` / `manual_fork_sync` 路由。

## [20260808-193014]
### 新增 (Added)
- 新增可直接交给任意本地 Agent 的学习者安装协议：从上游 GitHub Raw 单句入口开始，确认语种与路径，经同意后安装最小 sparse 运行时、检测 Obsidian Desktop 与 ListenKit、预览并初始化第一个 Vault、解析语言 Skill 后交付日常学习工作区。
- 新增开发者 Agent 初始化协议，覆盖 GitHub 账号与 `gh` 授权、个人 fork、`origin`/`upstream`、上游同步、topic branch、测试与隐私检查、推送、上游 PR、CI 状态和合并后清理；个人自用 fork 与上游贡献两种路线均有明确边界。
- 新增 `python -m lingotrace.init doctor` 只读诊断，输出 Python、Git、GitHub CLI、Obsidian Desktop、ListenKit、运行时和跨平台推荐位置；阻止无效运行时、非绝对 Vault 路径及 Vault/运行时嵌套。

### 变更 (Changed)
- README、入门指南、操作手册、贡献指南、AGENTS、多语言架构、产品说明、用户画像、文档索引和 Vault 连接指南按“学习者最小运行时 / 开发者完整仓库”双旅程重新分流。
- Vault 根 Agent 指令在首次需要 Base 看板或音视频能力且对应可选依赖缺失时，向用户解释影响并在征得同意后提供安装，不阻塞无关文本学习。

### 测试 (Tests)
- 新增跨平台推荐路径、必要与可选依赖、ListenKit 真实 CLI 标记、路径隔离、CLI JSON 和双用户文档契约测试；通过 LingoTrace 216 项、官方听力 100 项、架构基线 42 项和 Vault 结构 18 项测试，并实际验证最小 sparse checkout 只检出 `lingotrace/`。

## [20260808-184251]
### 新增 (Added)
- Vault 初始化新增可实际执行的 `python -m lingotrace.init` 入口，支持 English/Japanese 的 preview、apply、运行时连接追加和连接解析；初始化结果包含 Vault 根 `AGENTS.md`、上下文、路径、模板、视图及当前平台运行时连接。
- 新增 macOS、Windows、Linux 分文件的多候选运行时连接配置。当前平台找不到可用路径时，Agent 会询问用户并追加本机路径，不覆盖其他平台或同平台已有候选。
- 新增跨平台连接解析、无覆盖追加、失效候选回退、CLI 端到端和真实初始化写入测试，以及 Vault 初始化与运行时连接正式指南。

### 变更 (Changed)
- 日常使用边界统一为“私人 Vault 是 Agent 工作区，公共 LingoTrace 仓库是 Vault 外运行时”；Japanese 与 English Agent Skill 均加入运行时发现和跨设备重新连接规则。
- 多语言架构、产品说明、README、入门指南、操作手册、用户画像、贡献指南和工具文档全部按当前 Japanese/English 全能力实现与跨平台初始化流程更新。
- 公共能力集合使用现行名称 `PUBLIC_CAPABILITY_IDS`，保留旧名称作为兼容别名。

### 清理 (Removed)
- 删除 44 份已被当前实现取代的迭代计划、逐版评审、迁移阶段清单、历史差距分析和重复审计材料；文档从 59 份收敛为 17 份当前规范与指南。
- 删除 6 个只验证已完成 Phase 文档的历史文档测试，保留真实运行时、语言包、用户故事和当前行为基线测试。

### 测试 (Tests)
- 通过 LingoTrace 206 项、官方听力 100 项、当前架构基线 42 项和 Vault 结构 18 项测试。

## [20260808-175928]
### 变更 (Changed)
- 按用户明确授权，将仓库根目录 `LICENSE` 删除纳入本次上游同步 PR，保持 fork 与上游提交内容一致。

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
