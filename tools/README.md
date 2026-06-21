# Tools

此目录只放可重复使用、适合纳入版本控制的工具。一次性资料修复脚本、临时转写产物与历史脚本应放入 `tmp/legacy/`，不要留在 `tools/`。

## Phase 1 Runtime

Phase 1 的公共 runtime 入口位于 `lingotrace/`，测试位于 `tests/lingotrace/`。贡献者应从 `docs/multilingual/phase-1/contributor-guide.md` 了解可修改范围、禁止范围、测试命令与公开提交检查。

这一阶段只建立核心契约、Japanese pack 边界、新 Japanese Vault dry-run scaffold、migration inventory dry-run 和贡献者文档；不代表英语支持、真实私有资料迁移、日常切换或旧框架移除已交付。

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
- 不要让它自动决选最终常用句。

实际调用链路：

```text
Japanese Agent Skill
  -> LingoTrace listening execution layer
  -> tools/listening-transcribe-official/transcribe_listening.py
  -> ../ListenKit/cli/generate-markdown.sh
  -> ../ListenKit/cli/export-audio-slices.py
```

依赖：

- Agent Skill：`lingotrace/packs/japanese/agent_skills/SKILL.md`
- 通用转写能力：`../ListenKit/cli/generate-markdown.sh`
- 通用时间范围切片能力：`../ListenKit/cli/export-audio-slices.py`
- 离线词典包：由 `setup_offline_dictionary.py` 安装及检查于 LingoTrace 自己的本机 Cache runtime。
- Python runtime：LingoTrace 固定使用 `~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python`，ListenKit 固定使用 `~/Library/Caches/ListenKit/venvs/cpython-314/bin/python`。两套环境都放在本机 Cache，避免从 iCloud 路径载入原生扩展时卡住或让 symlink 被改名；Homebrew `/opt/homebrew/bin/python3.14` 只负责初始化，两者不得跨环境 import 包。

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

#### 常用句边界

`transcribe_listening.py` 只建立 `## 可直接背的常用句` 区块骨架，不自动决定最终常用句。

新笔记生成后，仍需由人工或模型阅读完整脚本，保守挑选 `0-5` 句真正值得背、可以迁移到其他生活场景的表达，再同步更新 frontmatter 的 `daily_use_sentences`。重跑既有笔记时，工具会保留已手工修订的常用句，除非明确要求重置。

这个边界用于避免把 ASR 不稳定句、教材操练句、不自然表达或过度泛用骨架直接收入常用句池。

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

常用命令：

```bash
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python tools/listening-transcribe-official/setup_offline_dictionary.py --python ~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python --install
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python tools/listening-transcribe-official/setup_offline_dictionary.py --python ~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python --check
```

依赖：

- Homebrew Python 3.14 作为初始化器。
- LingoTrace 直接使用本机 Cache 中的 Python 包；直接依赖只由 `requirements-listening.txt` 固定。
- Vault 外部缓存目录：默认为 `~/Library/Caches/jp-listening-dicts`，只保留跨版本静态资料，例如根目录 `accent_map.json`。
- 可用 `JP_LISTENING_DICT_DIR` 覆盖默认位置。

完整环境边界与升级规则见 `docs/listening-runtime-isolation.md`。

### 测试

执行测试：

```bash
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
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
python3 tools/vault-structure/migrate_vault_layout.py --phase content
python3 tools/vault-structure/migrate_vault_layout.py --phase content --apply
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
python3 tools/vault-structure/validate_vault_structure.py \
  --baseline tmp/directory-refactor-baseline.json \
  --enforce-listening-layout \
  --run-integrations
```

更新坏链基线：

```bash
python3 tools/vault-structure/validate_vault_structure.py \
  --write-baseline tmp/directory-refactor-baseline.json
```

依赖：

- Python
- `系统配置/paths.json`
- 生活口语卡验证器
- 次日 rollover wrapper

### 测试

执行测试：

```bash
python3 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
```

## Maintenance Rules

- 新工具应有明确且可重复的用途。
- 支持预览模式的工具，先执行预览再写入。
- 大量搬移或改链前，保留备份与可核对的清单。
- 不提交音频、媒体、转写产物、缓存、`.DS_Store` 或 `__pycache__/`。
- 一次性修复脚本完成任务后移到 `tmp/legacy/`。
