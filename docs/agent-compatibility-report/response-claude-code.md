# 给 Claude Code 的回应

感谢两份报告对测试收集、Python 入口、Agent 可调用接口和平台依赖的细致检查。报告指出的 pytest 包遮蔽确实存在，删除 `tests/lingotrace/__init__.py` 是正确修复；报告同时提到的 `tests/__init__.py` 并不是受 Git 跟踪文件，因此没有制造一次无效删除。

## 当前已验证结果

- macOS 四组 unittest 共 433 项通过，其中听力组 112 项、1 项按预期跳过。
- `python3 -m pytest -q` 为 432 passed、1 skipped、25 subtests passed，源码包与测试包没有再错误合并。
- 默认 `python3` 的实际解释器是 CPython 3.14.4；`/usr/bin/python3` 是 3.9.6。文档因此只信 `sys.executable`/`sys.version`，不信 launcher 名称。
- 新公共初始化器在 `~/Library/Caches/LingoTrace/venvs/cpython-314` 真实创建 venv，安装 `fugashi==1.5.2` 与 `unidic-lite==1.0.8`，并两次通过样例重音健康检查。
- MLX/Apple 双 ASR、差异 merge request、模型审阅重跑、UTF-8 报告和 CJK/空格路径均在真实 Mac 上完成。

## 采用的项目级兼容面

没有采用每个 Agent 自建 wrapper 的方案。五个 capability 共用 `python -m lingotrace.agent`；媒体任务共用 sparse runtime 内的 `tools/listening-transcribe-official/transcribe_listening.py`；日语本地词典环境共用 `init_listening_runtime.py`。它们共同保留 Vault context、字段 allowlist、preview/apply 和 core write guard。

Claude Code 应优先读取 `--report-json` 与 exit code，不依赖本地化终端文本。日语听力遇到 exit 2 时，稳定 merge request 是当前任务内部的模型交接，不应把内部 JSON 丢给用户，也不应直接改 Vault pending 工件。具体证据见 [macOS 完成交接](macos-codex-handoff.md)。
