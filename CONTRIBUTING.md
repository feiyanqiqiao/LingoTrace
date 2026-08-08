# 参与贡献 (Contributing to LingoTrace)

非常感谢您对 LingoTrace 项目的关注与支持！本项目是一个开源的高级外语学习工作流引擎。
在您提交 Pull Request (PR) 或 Issue 之前，请务必阅读以下贡献指南和开源商业化规则。

## 1. 核心协议与开源商业化声明

本项目采用 **GNU Affero General Public License v3.0 (AGPL v3)** 协议开源。
- **对社区的承诺**：您始终可以免费、自由地分发、修改和使用本项目的源代码进行个人学习或极客研究。
- **禁止未授权的商业化**：根据 AGPL v3 的传染性条款，任何将本项目核心代码包装为 SaaS 网络服务或闭源软件对外提供的行为，必须将整个产品同等开源。我们严格禁止未经明确授权的商业化套壳或售卖行为。

## 2. 贡献者许可协议 (CLA)

为了保证项目未来在法律层面的纯洁性以及能够平滑过渡到官方商业化版本，我们要求所有代码贡献者遵守以下条款：
- 当您向本项目提交 Pull Request 时，即代表您**不可撤销地授权**项目拥有者（Maintainers）在任意场景（包括未来可能的闭源商业化产品）下使用、修改、再分发您所贡献的代码。
- 您依旧保留您所贡献代码的个人版权，但不要求通过本项目获取任何直接的经济回报。

## 3. 分级名誉回馈系统 (Tiered Recognition)

我们深知极客的动力来源于互相认可。我们建立了明确的“分级名誉回馈机制”，以此回馈您的卓越贡献：

### 🥇 核心贡献者 (Core Contributors)
- **门槛标准**：提交过至少 1 个完整的核心功能模块（Feature）、解决过关键架构级 Bug，或者连续数月在社区保持高频有效代码提交。
- **回馈方式**：
  - 在未来推出的商业版付费产品的 `About（关于）` 页面核心位置单列致谢。
  - 赠送官方商业付费版本的终身免费授权（VIP）。
  - GitHub 仓库 README 顶端展示头像。

### 🥈 有效代码贡献者 (Active Contributors)
- **门槛标准**：任何一条包含**有效代码逻辑变动**的 Pull Request 被官方审核并 Merge 入主分支（排除纯文档修改和格式排版）。
- **回馈方式**：
  - 进入商业产品的“鸣谢名单（Credits）”。
  - 在每次的版本更新日志（CHANGELOG）中享受署名提及。

### 🥉 社区参与者 (Community Members)
- **门槛标准**：修改 README 错别字、多语种翻译、提交经过验证的 Bug Report、参与架构讨论等。
- **回馈方式**：
  - 在开源仓库的 README 底部名誉墙上展示（适时引入 `All Contributors` 规范发放勋章）。

## 4. 提交流程规范

如果你不熟悉 fork、GitHub CLI、分支、PR 或 CI，把 [开发者初始化协议](docs/developer-agent-setup.md)完整交给 Agent。它覆盖从 GitHub 账号和 `gh auth` 到 fork、`origin`/`upstream`、topic branch、推送、上游 PR、CI 检查和合并后清理的全过程。

核心要求：

1. **远端角色**：贡献者的 `origin` 指向自己的 fork，`upstream` 指向 `https://github.com/feiyanqiqiao/LingoTrace.git`。
2. **分支**：`main` 只用于同步上游；每次改动从最新上游 `main` 创建 topic branch，不直接提交到 `main`。
3. **环境与测试**：提交前运行与改动相匹配的目标测试和公共全量测试；支持 dry-run 的写入流程先 dry-run。
4. **代码风格**：遵循现有规范，不引入无关格式化或批量改写。
5. **安全与隐私**：绝对禁止提交个人 Vault、版权音视频、本地缓存、凭据或转写产物。暂存后必须运行 `bash tools/git/check-public-staged-files.sh`。
6. **PR 与 CI**：把 fork 的 topic branch 推送到 `origin`，从该分支向上游 `main` 提交 PR；检查所有必需 CI，通过不等于已 merge。
7. **学习环境**：开发者的私人学习 Vault 仍通过 [学习者安装协议](docs/learner-agent-setup.md)初始化，并保存在源码仓库外。

欢迎与我们一起打造终极的开源外语学习引擎！
