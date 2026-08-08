# LingoTrace 开发者初始化协议（交给 Agent 执行）

> 本文面向想 fork、改造或贡献 LingoTrace，但不一定熟悉 GitHub 协作的开发者。Agent 必须先解释每个外部写操作，再代用户执行。

## 1. 先确认开发目标

询问用户属于哪种情况：

1. **准备向上游贡献**：改动完成后从个人 fork 向 `feiyanqiqiao/LingoTrace` 提交 PR；
2. **只维护个人版本**：长期使用自己的 fork，不计划提交上游。

两者都使用 topic branch，不在 `main` 直接开发。两者都把私人学习 Vault 放在源码仓库外，并按照 [学习者安装协议](learner-agent-setup.md) 初始化实际学习环境。

## 2. 账号与本机工具预检

只读检查：

- 用户是否已有 GitHub 账号；
- `git --version`；
- `gh --version`；
- `gh auth status`；
- Git 的 `user.name` 与 `user.email`；
- Python 版本。

GitHub CLI 不是 Git 本身，但强烈推荐，因为 Agent 可以用它创建 fork、PR 和检查 CI。缺失或未登录时，在用户同意后从 [GitHub CLI 官方说明](https://cli.github.com/)安装并执行 `gh auth login`。登录需要用户本人完成浏览器或设备授权，Agent 不得索取或记录令牌。

## 3. 创建 fork 与完整 checkout

上游固定为：

```text
https://github.com/feiyanqiqiao/LingoTrace.git
```

如果用户尚未 fork，在用户授权后使用 GitHub 页面或 GitHub CLI 创建 fork。完整开发仓库建议放在：

- macOS/Linux：`~/Documents/Project/LingoTrace` 或 `~/Documents/Projects/LingoTrace`；
- Windows：`%USERPROFILE%\Documents\Projects\LingoTrace`。

克隆个人 fork，随后配置 remote：

```bash
git clone https://github.com/<github-user>/LingoTrace.git <developer-repo>
git -C <developer-repo> remote add upstream https://github.com/feiyanqiqiao/LingoTrace.git
git -C <developer-repo> remote -v
```

目标状态：

- `origin` 指向用户自己的 fork，并拥有推送权限；
- `upstream` 指向正式上游，只用于获取和比较；
- 私人 Vault 不在 `<developer-repo>` 内。

已有仓库时先检查现有 remote，不盲目覆盖。remote 名称或方向不同，应向用户说明并取得同意后调整。

## 4. 第一次改动前

每次新任务开始时，Agent 都必须：

1. 检查 `git status --short --branch`；
2. 执行 `git fetch --all --prune`；
3. 比较本地 `main`、`origin/main` 和 `upstream/main`；
4. 如果上游有更新，告诉用户差异，并询问是否现在同步；
5. 工作区干净且用户确认后，把 fork 的 `main` 快进到上游：

```bash
git switch main
git pull --ff-only upstream main
git push origin main
```

6. 从当前 `main` 创建 topic branch，例如：

```bash
git switch -c codex/add-korean-pack
```

不要在有未识别改动时切分支、合并或覆盖。已有工作属于用户，必须先理解和保留。

## 5. 开发、测试和隐私检查

Agent 必须先读仓库根 `AGENTS.md`，再读所改子系统的 Skill、源码、文档和测试。实现过程中：

- 先写或更新实施设计，再改代码；
- 语言包改动遵循 [语言包贡献指南](multilingual/language-pack-contributor-guide.md)；
- 框架变更在测试通过后、提交前更新 `CHANGELOG.md`；
- 不提交 Vault 笔记、音视频、`.obsidian/`、缓存、密钥或转写产物；
- 提交前运行 `bash tools/git/check-public-staged-files.sh`；
- 运行与改动风险相称的目标测试和全量公共测试。

只维护个人版本的用户也应保留这些安全检查。个人特有配置不要硬编码进公共语言包；优先保存在 Vault 本地配置或个人 fork 明确隔离的文件中。

## 6. 提交并推送个人 fork

提交前向用户概括改动、测试和 staged 文件。然后：

```bash
git add <confirmed-public-files>
bash tools/git/check-public-staged-files.sh
git commit -m "<type(scope): summary>"
git push -u origin <topic-branch>
```

不要使用 `git add .` 掩盖 staged 范围，不强推共享分支，不把 topic branch 推到上游仓库。

## 7. 向上游提交 PR

仅“准备向上游贡献”的用户执行本节。推送后，在用户授权下创建 PR：

```bash
gh pr create \
  --repo feiyanqiqiao/LingoTrace \
  --base main \
  --head <github-user>:<topic-branch> \
  --title "<clear title>" \
  --body "<summary, tests, risks>"
```

PR 正文至少包含：

- 解决的问题；
- 用户可见行为；
- 关键实现与边界；
- 实际运行的测试及结果；
- 未自动验证或依赖人工验证的部分。

创建后立即检查：

```bash
gh pr view <pr-number> --repo feiyanqiqiao/LingoTrace
gh pr checks <pr-number> --repo feiyanqiqiao/LingoTrace --watch
```

只有所有必需 CI 通过，才能报告“PR 已通过自动检查”。PR 仍需维护者 review 和 merge；CI 通过不等于已合并。失败时读取日志、修复同一 topic branch、重新测试并推送，不新开重复 PR。

## 8. PR 后续与下一次开发

PR 打开期间保留 topic branch，定期检查 review、CI 和 merge 状态。上游 `main` 更新且影响当前 PR 时，先解释冲突风险，再按仓库规则更新分支并重测。

PR 合并后：

```bash
git switch main
git pull --ff-only upstream main
git push origin main
git branch -d <topic-branch>
git push origin --delete <topic-branch>
```

删除前确认 PR 已合并、工作区干净且分支无未合并提交。下一次改动重新从“第一次改动前”开始，不能沿用已经合并的旧 topic branch。

只维护个人版本的用户不必创建上游 PR，但下一次开发前仍要 fetch 并比较上游；由 Agent 告诉用户是否有更新、可能冲突哪些改动，并由用户决定是否合并或 rebase。
