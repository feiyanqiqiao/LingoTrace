# LingoTrace 用户操作指南

这份指南面向已经会使用 Obsidian，并愿意配合 Codex 或类似 AI agent 维护学习材料的用户。

当前项目以日语学习为主线。你可以把它改造成英语或其他外语学习系统，但不要假设现有 `jp-*` skills 可以不改就直接适用于所有语言。

## 1. 项目定位

LingoTrace 不是一套完整课程，也不是教材内容仓库。它提供的是一套学习系统骨架：

```text
原始材料
  -> 学习笔记
  -> 复习卡
  -> 定期复习
  -> 输出练习
```

它适合用来管理：

- 课堂或自学中遇到的词汇、语法和错题。
- 音频 / 视频材料转成的听力笔记。
- 可复用的表达、生活口语和写作素材。
- 需要间隔复习的学习卡片。

它不提供：

- 私人学习内容。
- 教材音频、视频、PDF 或完整转写稿。
- 通用 ASR 引擎。
- 语言无关的全自动学习系统。

## 2. 准备工作

你需要：

- Obsidian。
- Git 或 GitHub 下载能力。
- Codex 或兼容的 AI agent。
- Python，用于运行部分工具。
- 可选：ListenKit，用于音视频导入和转写。

推荐目录关系：

```text
your-workspace/
  LingoTrace/
  ListenKit/          # 可选，用于听力转写
  your-private-vault/ # 你的私人 Obsidian 学习库
```

不要把自己的私人学习库直接当作公开仓库提交。公开仓库只应保留可复用工具、skill 和说明文档。

## 3. 下载后怎么开始

1. 下载或 clone `LingoTrace`。
2. 用 Obsidian 创建或打开你自己的学习 vault。
3. 阅读 `README.md` 和本指南，了解仓库边界。
4. 参考 `系统配置/` 中的路径角色、模板和复习流程，建立自己的学习结构。
5. 在 Obsidian 中打开或复制 `学习系统/总训练.base`，作为主训练面板 scaffold。
6. 根据需要复制、安装或参考 `codex-skills/` 中的 skills。
7. 如果要做听力转写，下载并配置 sibling 项目 `ListenKit`。
8. 先用少量材料试跑，不要一开始批量导入大量笔记。

如果你只是想学习这套方法，可以先不用运行脚本，先阅读各个 `SKILL.md`，理解它们分别负责什么。

## 4. 公开 scaffold

本仓库公开了两类可直接参考的 Obsidian scaffold。

`系统配置/` 包含：

- `paths.json`：学习系统中的路径角色配置。
- `复习流程.md`：复习阶段、延迟规则和 Bases 使用注意。
- `模板/`：单词卡、语法卡、课堂笔记、每日学习清单等模板。

`学习系统/总训练.base` 是主训练面板配置。它只保存 Obsidian Bases 的筛选、列和视图设置，不包含你的真实学习卡片。这份文件可以作为公共模板提交和迭代，但提交前应确认变更属于面向所有用户的默认训练面板改进，例如 filter、view、formula、列顺序、列宽或排序规则。

日常学习中临时拖动列、调整排序、折叠视图等个人使用痕迹，不应提交回公开仓库。使用时建议先复制并改造，不要把自己的私人学习内容提交回公开仓库。

## 5. 主要 skill 分工

### `jp-review-material-maintainer`

用于维护复习材料：

- 词汇卡。
- 语法卡。
- 发音卡。
- 错题卡。
- 每日学习清单。

它负责搜索、去重、建卡和更新卡片状态。创建词汇前应先查重，语法卡应保持清晰的接续、用法和例句。

### `jp-listening-script-generator`

用于生成固定听力笔记。

适合：

- 一个本地音频。
- 一个媒体 URL。
- 目标是生成 `学习系统/听力` 下的泛听或精听 note。

默认是泛听。只有你明确需要逐句或逐组打磨时，才使用精听模式。精听笔记需要真实音频切片，不能只生成 Markdown 结构。

### `jp-source-note-generator`

用于生成灵活 source note。

适合：

- 视频。
- 音频。
- ListenKit 转写稿。
- 原始脚本。
- 混合学习材料。

它不固定正文结构，但必须保留来源记录，包括原始材料、最终音频、Obsidian embed 和转写脚本附录。

### `jp-survival-speaking-card-generator`

用于维护生活口语句库。

适合把已经人工确认过、可以直接说出口的表达整理成短卡片。不要把刚转写出来、还没确认自然性的句子自动加入生活口语库。

### `jp-next-day-review-updater`

用于每日复习 rollover。

它是确定性的状态更新工具，不负责创建新卡。使用时先跑 dry-run，确认结果合理后再执行写入。

## 6. 日常学习流程

### 词汇和语法

推荐流程：

1. 从课堂笔记、自学材料或 source note 中发现学习点。
2. 让 AI agent 使用 `jp-review-material-maintainer` 搜索已有卡片。
3. 如果不存在，再创建新卡。
4. 卡片进入复习流程。
5. 每天复习后再由 rollover 工具更新下一次复习日期。

原则：

- 先查重，再建卡。
- 不确定核心含义或主要接续时，不要强行建卡。
- 例句要服务复习，不要写成长篇讲义。

### 听力材料

推荐流程：

1. 准备一个音频文件或媒体 URL。
2. 选择目标材料目录。
3. 使用 `jp-listening-script-generator` 生成泛听稿。
4. 如果需要逐句练习，再明确要求精听。
5. 生成后阅读脚本，挑选 `0-5` 条真正值得背的常用句。

泛听适合大多数材料。精听成本更高，适合需要跟读、复听和发音打磨的材料。

### 视频或文章材料

推荐流程：

1. 判断目标是不是固定听力稿。
2. 如果不是，使用 `jp-source-note-generator`。
3. 先准备可追溯的素材包。
4. 根据材料内容写灵活学习笔记。
5. 把完整转写文本放在正文之后作为附录。
6. 如需复习卡，再交给对应卡片 skill。

source note 的重点不是“总结视频”，而是让材料来源、学习价值和后续卡片都可追溯。

### 生活口语

推荐流程：

1. 从人工确认过的常用句或用户提供的日常表达开始。
2. 判断它是否真的能在生活场景中直接使用。
3. 搜索已有生活口语卡，避免重复。
4. 创建一张短小、场景明确的口语卡。

不要把教材操练句、ASR 不稳定句或过度泛化句直接放入口语库。

## 7. 如何用于英语或其他外语

这个项目可以迁移到其他外语，但迁移的是系统思想，不是直接复用日语实现。

可以复用：

- Obsidian 管理方式。
- source note -> review cards -> review rollover 的流程。
- AI agent 协作方式。
- 公开仓库和私人 vault 分离的安全边界。
- 听力材料、口语句库、错题卡等模块划分。

需要改造：

- skill 名称和说明，例如从 `jp-*` 改成目标语言前缀。
- 词汇卡模板，例如英语要关注词性、搭配、例句、发音和常见语块。
- 语法卡模板，例如英语可能更关注句型、时态、语气、语域和常见错误。
- 发音资源，例如日语重音不适用于英语，需要换成音标、重音、连读、弱读等规则。
- 听力转写语言参数和后处理规则。
- 示例句、标签和目录命名。

建议先选择一个小范围试点，例如“英语听力 source note + 词汇卡”，不要一次性把所有日语规则改成通用规则。

## 8. ListenKit 配置

如果你要处理音频或视频，推荐把 ListenKit 放在 LingoTrace 旁边：

```text
your-workspace/
  LingoTrace/
  ListenKit/
```

听力工具默认会查找：

```bash
../ListenKit/cli/generate-markdown.sh
```

如果你的 ListenKit 在其他位置，可以设置：

```bash
export LISTENKIT_ROOT=/path/to/ListenKit
```

ListenKit 负责通用音视频转写。LingoTrace 负责把转写结果变成学习笔记和复习材料。

两个项目使用彼此独立的 Python 3.14 虚拟环境，不能共享或跨环境加载 Python 包：

```bash
# 在 LingoTrace 根目录初始化分词和重音环境
codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh

# 检查 LingoTrace、ListenKit、JSON 与媒体工具的完整链路
codex-skills/jp-listening-script-generator/scripts/check-listening-chain.sh
```

正常转写不会临时安装依赖。环境缺失时，命令会停止并给出明确的初始化命令。详细边界与升级规则见 `docs/listening-runtime-isolation.md`。

## 9. 安全边界

请把公开仓库和私人学习内容分开。

不要提交：

- 私人日记和学习记录。
- 课堂原始笔记。
- 教材音频、视频、PDF、截图。
- 商业教材完整转写稿。
- Obsidian 本地工作区状态。
- 临时转写产物、缓存和媒体文件。

提交前运行：

```bash
bash tools/git/check-public-staged-files.sh
```

如果你在分支上检查相对 `main` 的差异：

```bash
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

## 10. 推荐上手路径

第一次使用时，建议按这个顺序：

1. 只阅读 `README.md` 和本指南。
2. 选择一个小材料，例如一段短音频或一页自学笔记。
3. 生成一个 source note 或听力 note。
4. 从里面手动确认几个词汇或语法点。
5. 再创建少量复习卡。
6. 跑一次 rollover dry-run。
7. 确认流程顺手后，再逐步扩大使用范围。

这套系统的重点不是一次性自动生成很多内容，而是把学习材料稳定地沉淀成可复习、可追溯、可长期维护的结构。
