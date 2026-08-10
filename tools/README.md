# Tools

此目录只放可重复使用、适合纳入版本控制的工具。一次性资料修复脚本、临时转写产物与历史脚本应放入 `tmp/legacy/`，不要留在 `tools/`。

## Public Runtime

公共 runtime 位于 `lingotrace/`，测试位于 `tests/lingotrace/`。Japanese 和 English pack 均提供完整能力。Vault 初始化、跨平台 LingoTrace/ListenKit 连接和连接解析通过 `python -m lingotrace.init` 使用；贡献者应从 `docs/multilingual/language-pack-contributor-guide.md` 了解可修改范围、禁止范围、测试命令与公开提交检查。

## Listening Transcribe

目录：`tools/listening-transcribe-official/`

这组工具用于将本地音频或媒体 URL 转为听力笔记，并依需要生成逐句切片、泛听或精听内容。

### `transcribe_listening.py`

用途：

- 调用 ListenKit 取得转写结果。
- 生成或更新 Obsidian 听力笔记。
- 管理素材目录下的 `attach/` 与 `artifacts/`。
- 区分泛听与精听模式。
- 在精听模式下生成学习语块 manifest，并调用 ListenKit 导出真实切片。
- 加入可确认的重音信息，并保留既有人工修订内容。

何时使用：

- 需要把一个本地音频或媒体 URL 转为 Vault 内的固定听力笔记格式时。
- 需要更新既有听力笔记的脚本、音频引用或精听切片时。

何时不要使用：

- 不要直接把它当作日常入口。日常学习应优先通过 `lingotrace/packs/japanese/agent_skills/SKILL.md` 描述的自然语言 Agent Skill 触发。
- 不要用它生成一般来源笔记、词汇卡或生活口语卡。
- 不要让它在生成常用语块后自动转录口语卡。

实际调用链路：

```text
Japanese Agent Skill
  -> LingoTrace listening execution layer
  -> tools/listening-transcribe-official/transcribe_listening.py
  -> Windows: ../ListenKit/cli/generate-markdown.ps1 (PowerShell)
  -> macOS/Linux: ../ListenKit/cli/generate-markdown.sh (bash)
  -> ../ListenKit/cli/export-audio-slices.py
```

依赖：

- Agent Skill：`lingotrace/packs/japanese/agent_skills/SKILL.md`
- 通用转写能力：Windows 使用 `../ListenKit/cli/generate-markdown.ps1`，macOS/Linux 使用 `../ListenKit/cli/generate-markdown.sh`。Windows 不通过 WSL 或 Git Bash 转接。
- 通用时间范围切片能力：`../ListenKit/cli/export-audio-slices.py`
- 离线词典包：由 `setup_offline_dictionary.py` 安装及检查于 LingoTrace 自己的本机 Cache runtime。
- Python runtime：LingoTrace 与 ListenKit 使用彼此独立的本机 runtime，不得跨环境 import 包。macOS 已验证路径见 `docs/listening-runtime-isolation.md`；Windows 由当前 LingoTrace Python 与 ListenKit 的 PowerShell 入口分别解析，不硬编码用户名、Python 3.14 安装目录或 Store alias。

#### 精听学习语块

精听稿统一使用学习语块，不直接把 ASR chunks 当作切片单位：

- 路由依据是脚本内容，不是文件夹或文件名；`Shadowing` 路径不会强制套用对话规则。
- `dialogue/numbered` 按完整报号对话组切片，报号属于该组，作为该 `SNN` 的第一段音频与文本。
- `dialogue/exchange` 按完整问答交换切片；可靠且中间停顿不超过 `1.0` 秒的四轮问答保留为一组，否则使用两轮 A/B。
- `sentence/sentence` 按自然句切片。
- 自动切分不可靠时，使用 `--slice-manifest PATH` 提供人工校正后的时间范围。
- 使用 `--slice-profile auto|dialogue|sentence` 覆盖自动分类；优先级为 CLI 覆盖、reviewed manifest metadata、自动内容判断。

生成器会先做录音链前置检查：来源音频必须存在且非空，ListenKit 的转写与切片 CLI 必须可用，精听切片还需要 `ffmpeg`/`ffprobe`。本地音频与 URL 输入都会把 ListenKit 原始 `.listenkit.md/.json` 保存到素材目录的 `artifacts/`，避免只留下最终稿而无法回查。

生成器将 manifest 写入素材目录下的 `artifacts/<audio_stem>.slices.json`，并保存 `slice_profile` 的类型、分组、来源、编号策略和 padding。默认路径中标记为 `source: manifest` 的文件视为已人工 review，重跑时沿用其 profile 和时间范围；`source: auto|cli` 则可重新分类。之后交给 ListenKit 导出 `attach/<audio_stem>_SNN.m4a`。精听切片一律不得互相重叠；`dialogue/numbered` 使用 `0.0` 秒 padding，其他 profile 使用前后各 `0.5` 秒安全 padding，但不能跨入相邻片段。导出报告与制作记录也保存最终 profile。`segment_count`、学习包区块、embed 和实际非空文件数量必须一致。

通用文本清洗只处理标点、空白与全半角数字，不按路径套用教材专用词语修正。`何回→何階`、`奥には→お国は` 等内容校正必须进入 reviewed transcript 或 manifest。

#### 常用语块边界

`transcribe_listening.py` 为新笔记建立 `## 常用语块` 区块骨架。每项使用 `语块 / 类型 / 素材原句 / 替换练习 / 交际作用`；素材原句只承担听辨锚点作用。

新笔记生成后，由模型阅读完整脚本，保守挑选 `0-5` 个可替换、可迁移的生产性语块，再把语块骨架同步到 frontmatter 的 `daily_use_sentences`。语块没有机械长度门槛；过度具体的完整句和低信息量填充表达都不应入选。

精听任务到此结束，不得在同一任务中把刚生成的语块转入口语卡。用户线下 review 后，必须通过后续独立的口语卡转录请求才可升格；该后续请求本身即表示已确认，无需逐卡再次询问。

重跑既有笔记时，工具会保留已手工修订的 `## 常用语块`。旧笔记的 `## 可直接背的常用句` 也会连同原标题原样保留，除非用户明确要求迁移或重置。

### `setup_offline_dictionary.py`

用途：

- 检查 LingoTrace Python 3.14 环境与离线日语词典是否可用。
- 安装固定版本的 `fugashi` 与 `unidic-lite` 到 LingoTrace 本机 Cache runtime。
- 为听力笔记与词汇维护提供重音候选。

何时使用：

- 首次使用听力转写工具前。
- 听力工具提示 LingoTrace runtime 缺失或损坏时。
- 需要确认分词与重音候选是否正常时。

何时不要使用：

- 不要用它生成听力笔记。
- 不要把 runtime 或外部静态词典缓存提交到 Git。
- 不要把本地候选直接当作人工确认结果。

常用命令（用本机已验证可用的 Python launcher 或隔离环境解释器替换 `<python-command>`）：

```bash
<python-command> tools/listening-transcribe-official/setup_offline_dictionary.py --python <python-command> --install
<python-command> tools/listening-transcribe-official/setup_offline_dictionary.py --python <python-command> --check
```

依赖：

- Python 3.14 是完整听力链的已验证版本；launcher 必须以实际执行结果确认，不能只按命令名判断。
- LingoTrace 直接使用本机 Cache 中的 Python 包；直接依赖只由 `requirements-listening.txt` 固定。
- Vault 外部缓存目录：macOS 默认为 `~/Library/Caches/jp-listening-dicts`，Windows 默认为 `%LOCALAPPDATA%\LingoTrace\Caches\jp-listening-dicts`，Linux 遵循 XDG cache；只保留跨版本静态资料，例如根目录 `accent_map.json`。
- 可用 `JP_LISTENING_DICT_DIR` 覆盖默认位置。

完整环境边界与升级规则见 `docs/listening-runtime-isolation.md`。

### 测试

执行测试：

```bash
<python-command> -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
```

## Git Workflow Checks

目录：`tools/git/`

这组工具用于降低公开仓库提交时混入私有 Vault 内容的风险。

### `check-public-staged-files.sh`

用途：

- 检查 staged 文件是否只包含公开 allowlist 路径。
- 阻止笔记、Obsidian 状态、音频、图片、PDF、暂存转写产物等私有内容进入提交。
- 可在 GitHub Actions 中检查 PR diff 或 `main` push diff。

本地提交前执行：

```bash
bash tools/git/check-public-staged-files.sh
```

检查某个 Git diff 范围：

```bash
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

## Vault Structure

目录：`tools/vault-structure/`

这组工具用于预览或执行 Vault 目录迁移，以及验证角色路径、显式 wikilink、听力附件、生活口语卡与 rollover 是否正常。

### `migrate_vault_layout.py`

用途：

- 按阶段预览 Vault 目录搬移、引用改写、新建与删除清单。
- 仅在明确加上 `--apply` 时写入。
- 写入前在 `tmp/directory-refactor-backup/` 建立备份与 manifest。

何时使用：

- Vault 目录结构需要调整时。
- 需要确认既有迁移是否已完成且可重跑时。

何时不要使用：

- 不要用它处理日常建卡或复习。
- 不要跳过预览直接执行 `--apply`。
- 不要用盲目全文替换代替可核对的阶段映射。

常用命令：

迁移工具默认只预览。确认清单后，才加上 `--apply`：

```bash
<python-command> tools/vault-structure/migrate_vault_layout.py --phase content
<python-command> tools/vault-structure/migrate_vault_layout.py --phase content --apply
```

可用阶段：

- `pronunciation`
- `system`
- `listening`
- `content`

依赖：

- Python
- Vault 根目录内的既有学习内容与角色配置。

### `validate_vault_structure.py`

用途：

- 验证角色路径与兼容镜像。
- 扫描显式 wikilink 与媒体引用。
- 检查听力附件目录结构。
- 串联生活口语卡验证器与 rollover 预览。
- 产生或比较坏链基线。

何时使用：

- 目录迁移前后。
- 修改路径角色、听力附件或生活口语卡结构后。
- 需要确认是否出现新增坏链时。

何时不要使用：

- 不要把新出现的坏链直接加入基线来略过问题。
- 不要用它改写笔记；这是只读验证工具，只有 `--write-baseline` 会更新基线文件。

常用命令：

完整结构验证：

```bash
<python-command> tools/vault-structure/validate_vault_structure.py \
  --baseline tmp/directory-refactor-baseline.json \
  --enforce-listening-layout \
  --run-integrations
```

更新坏链基线：

```bash
<python-command> tools/vault-structure/validate_vault_structure.py \
  --write-baseline tmp/directory-refactor-baseline.json
```

依赖：

- Python
- 当前 Vault 的 `.lingotrace/paths.json`（旧 Vault 仍兼容历史路径配置）
- 公共 LingoTrace runtime 与当前语言包
- `review_rollover` 只读预览；不依赖私有脚本、`zsh` 或特定 Agent 目录

### 测试

执行测试：

```bash
<python-command> -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
```

## Maintenance Rules

- 新工具应有明确且可重复的用途。
- 支持预览模式的工具，先执行预览再写入。
- 大量搬移或改链前，保留备份与可核对的清单。
- 不提交音频、媒体、转写产物、缓存、`.DS_Store` 或 `__pycache__/`。
- 一次性修复脚本完成任务后移到 `tmp/legacy/`。
