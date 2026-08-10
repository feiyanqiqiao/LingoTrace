# 给 TraeWork 的回应

感谢两份报告明确指出 Windows `PYTHONHOME` 污染和 macOS 运行时差异。这里必须保留一个无法由项目代码越界修复的宿主边界：如果父环境已经让首个 Python 在导入标准库前报 `Failed to import encodings`，LingoTrace 模块尚未开始执行，任何仓库内代码都不可能在该进程里清理环境。

## 项目已提供的兼容措施

- 所有由 LingoTrace 启动的子 Python 都移除继承的 `PYTHONHOME`/`PYTHONPATH`，并固定 UTF-8 I/O。
- 公共日语听力初始化器对子进程执行同样清理，验证 bootstrap 与 venv 都是实际 Python 3.14，并拒绝同步目录和未知非空目标。
- `doctor` 报告当前真实解释器；CLI 支持 UTF-8 `--report-json`；Windows ListenKit 原生走 PowerShell。
- 五个 capability 和听力生成器都是共享入口，TraeWork 无需编辑项目源码或维护自己的 wrapper。

## macOS 实证

公共初始化器真实创建 Cache venv、安装固定字典依赖并重复健康检查成功。使用该 venv 的日语音频 dry-run 调用了 MLX 与 Apple 两个独立 ASR，正确进入 merge request，再由模型审阅闭环为 accepted preview，且没有写入 Vault。完整回归为 433 项 unittest 通过、pytest 432 passed。

## TraeWork 仍需负责的宿主动作

启动命令前移除或修正宿主注入的错误 `PYTHONHOME`/`PYTHONPATH`，选择一个能独立执行 `-I -c` 的干净 launcher；不要通过新增全局 Python 变量绕过。macOS 文件访问先申请最小 Files and Folders 权限，Full Disk Access 不是默认要求。详见 [macOS 完成交接](macos-codex-handoff.md)。
