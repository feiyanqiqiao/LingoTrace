# 验证指南：采用 Spec Kit 工程治理

## 前置条件

- 当前目录为 `/Users/jiezhengj/Documents/Project/LingoTrace` 的 topic branch。
- 已安装当前验证过的 `specify 0.16.6.dev0`。
- 使用 Python 3.14；macOS/Linux 本地命令使用 `python3`。

## 1. 验证 Spec Kit 集成

```bash
specify integration status --json
```

预期：`status` 为 `ok`，默认集成为 `codex`，`missing_managed_files`、`modified_managed_files`、`invalid_manifest_paths` 和 `unchecked_manifests` 均为 0。

## 2. 验证公共文件范围

```bash
git status --short --branch
git diff --check
bash tools/git/check-public-staged-files.sh
```

预期：当前工作区处于 topic branch；没有空白错误；暂存文件只包含公共 allowlist 文件。

## 3. 运行四组现有测试

```bash
python3 -m unittest discover -s tests/lingotrace -p 'test_*.py'
python3 -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'
python3 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
python3 -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
```

预期：runtime 270 项、architecture baseline 42 项、vault structure 23 项、listening 112 项，其中 listening 保持既有 1 项 skip。

## 4. 核对迁移内容

```bash
git diff --stat main...HEAD
git diff --name-status main...HEAD
git diff --check main...HEAD
```

预期：既有公共源代码、测试、能力契约和架构文档没有无理由删除；新增文件集中在 `.specify/`、受管 `.agents/skills/speckit-*`、`specs/`、中文治理文档和 CHANGELOG；没有旧结构备份或同一事实的全文副本。

## 5. 发布前验证

```bash
git status --short --branch
git diff --cached --name-status
git log --oneline --decorate -3
```

预期：提交只发生在 `codex/adopt-spec-kit`；PR 指向上游 `feiyanqiqiao/LingoTrace:main`，并附带本指南中的测试证据。
