#!/usr/bin/env python3
"""Check and update approved Spec Kit components for an initialized project.

The script uses only Python's standard library and the official ``specify``
CLI. The project Agent gates startup on a successful full-check timestamp;
component remote checks are also cached for seven days. Extension updates use
the verified official catalog and the CLI's version-aware update command.
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence


CACHE_SCHEMA_VERSION = 1
CACHE_RELATIVE_PATH = Path(".agent-state/spec_kit_component_update_cache.json")
CACHE_TTL = timedelta(days=7)
APPROVED_EXTENSIONS = ("assess", "bug")
APPROVED_WORKFLOWS = ("speckit",)
OFFICIAL_EXTENSION_CATALOG = (
    "https://raw.githubusercontent.com/github/spec-kit/main/extensions/catalog.json"
)
OFFICIAL_WORKFLOW_CATALOG = (
    "https://raw.githubusercontent.com/github/spec-kit/main/workflows/catalog.json"
)
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SAFE_INTEGRATION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class UpdateError(RuntimeError):
    """A safe, user-actionable updater error."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str


@dataclass(frozen=True)
class Catalog:
    name: str
    url: str
    install_allowed: bool


def parse_version(value: Any) -> tuple[int, int, int, int] | None:
    """Parse stable dotted numeric versions; reject unknown version schemes."""
    if not isinstance(value, str):
        return None
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def classify_integration_version(
    cli_version: str, manifest_version: str
) -> str:
    """Compare the CLI release proxy with an integration manifest version."""
    current = parse_version(cli_version)
    installed = parse_version(manifest_version)
    if current is None or installed is None:
        return "unknown"
    if current == installed:
        return "current"
    if current > installed:
        return "outdated"
    return "future-manifest"


def parse_cli_version(output: str) -> str | None:
    match = re.search(r"\bspecify\s+v?(\d+\.\d+(?:\.\d+){0,2})\b", output)
    if not match or parse_version(match.group(1)) is None:
        return None
    return match.group(1)


def parse_self_check(output: str) -> tuple[str, str | None] | None:
    clean = ANSI_PATTERN.sub("", output)
    match = re.search(r"\bUp to date:\s*v?(\d+\.\d+(?:\.\d+){0,2})\b", clean)
    if match and parse_version(match.group(1)) is not None:
        return "up-to-date", match.group(1)
    match = re.search(
        r"\bUpdate available:\s*v?(\d+\.\d+(?:\.\d+){0,2})\s*[→>-]+\s*"
        r"v?(\d+\.\d+(?:\.\d+){0,2})\b",
        clean,
    )
    if match and all(parse_version(part) is not None for part in match.groups()):
        return "update-available", match.group(2)
    return None


def parse_installed_extensions(output: str) -> list[dict[str, Any]]:
    data = json.loads(output)
    if not isinstance(data, list):
        raise ValueError("extension list JSON must be an array")
    records: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("extension list contains a non-object entry")
        extension_id = item.get("id")
        version = item.get("version")
        source = item.get("source")
        if not isinstance(extension_id, str) or not isinstance(version, str):
            raise ValueError("extension list entry lacks a string id or version")
        records.append({"id": extension_id, "version": version, "source": source})
    return records


def parse_installed_integrations(output: str) -> list[str]:
    data = json.loads(output)
    if not isinstance(data, dict):
        raise ValueError("integration status JSON must be an object")
    if data.get("status") != "ok":
        raise ValueError("integration status did not report status=ok")
    installed = data.get("installed_integrations")
    if not isinstance(installed, list) or any(not isinstance(key, str) for key in installed):
        raise ValueError("integration status lacks an installed_integrations list")
    return installed


def parse_workflow_registry(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    workflows = data.get("workflows") if isinstance(data, dict) else None
    if not isinstance(workflows, dict):
        raise ValueError("workflow registry must contain a workflows object")
    if any(not isinstance(value, dict) for value in workflows.values()):
        raise ValueError("workflow registry contains an invalid entry")
    return workflows


def parse_workflow_info_version(output: str) -> str | None:
    clean = ANSI_PATTERN.sub("", output)
    matches = re.findall(r"^\s*Version:\s*(\S+)\s*$", clean, flags=re.MULTILINE)
    if len(matches) != 1 or parse_version(matches[0]) is None:
        return None
    return matches[0]


def parse_workflow_search_version(output: str, workflow_id: str) -> str | None:
    clean = ANSI_PATTERN.sub("", output)
    pattern = re.compile(
        r"^\s+.*\(([^()]+)\)\s+v(\d+\.\d+(?:\.\d+){0,2})\s*$",
        flags=re.MULTILINE,
    )
    matches = [
        version
        for found_id, version in pattern.findall(clean)
        if found_id == workflow_id
    ]
    if len(matches) != 1 or parse_version(matches[0]) is None:
        return None
    return matches[0]


def parse_extension_catalogs(output: str) -> list[Catalog]:
    """Parse the stable human-readable ``extension catalog list`` layout."""
    clean = ANSI_PATTERN.sub("", output)
    catalogs: list[Catalog] = []
    lines = clean.splitlines()
    headers = [
        (index, match.group(1).strip())
        for index, line in enumerate(lines)
        if (match := re.match(r"^\s{2}(.+?)\s+\(priority\s+\d+\)\s*$", line))
    ]
    for header_index, (start, name) in enumerate(headers):
        end = headers[header_index + 1][0] if header_index + 1 < len(headers) else len(lines)
        block = lines[start + 1 : end]
        install_allowed = any(
            re.match(r"^\s+Install:\s*install allowed\s*$", line, re.IGNORECASE)
            for line in block
        )
        url = _wrapped_catalog_url(block, extension_label=True)
        if url:
            catalogs.append(Catalog(name, url, install_allowed))
    return catalogs


def parse_workflow_catalogs(output: str) -> list[Catalog]:
    """Parse the stable human-readable ``workflow catalog list`` layout."""
    clean = ANSI_PATTERN.sub("", output)
    catalogs: list[Catalog] = []
    lines = clean.splitlines()
    header_pattern = re.compile(
        r"^\s*\[\d+\]\s+(.+?)\s+(install allowed|discovery only)\s*$",
        flags=re.IGNORECASE,
    )
    headers = [
        (index, match)
        for index, line in enumerate(lines)
        if (match := header_pattern.match(line))
    ]
    for header_index, (start, match) in enumerate(headers):
        end = headers[header_index + 1][0] if header_index + 1 < len(headers) else len(lines)
        # The supported default stack names its built-in sources "default" and
        # "community". User/project overrides are rejected before this parser.
        name = match.group(1).split()[0]
        install_allowed = match.group(2).lower() == "install allowed"
        url = _wrapped_catalog_url(lines[start + 1 : end], extension_label=False)
        if url:
            catalogs.append(Catalog(name, url, install_allowed))
    return catalogs


def _wrapped_catalog_url(lines: Sequence[str], *, extension_label: bool) -> str | None:
    """Reassemble URLs wrapped by Rich to the current console width."""
    for index, line in enumerate(lines):
        if extension_label:
            marker = re.match(r"^\s+URL:\s*(.*)$", line)
            if not marker:
                continue
            first_part = marker.group(1)
        else:
            marker = re.search(r"https?://", line)
            if not marker:
                continue
            first_part = line[marker.start() :]

        value = re.sub(r"\s+", "", first_part)
        if not value and index + 1 < len(lines):
            index += 1
            value = re.sub(r"\s+", "", lines[index])
        while value.startswith(("https://", "http://")) and not value.endswith(".json"):
            index += 1
            if index >= len(lines):
                break
            continuation = lines[index].strip()
            if (
                not continuation
                or continuation.lower().startswith("install:")
                or continuation.lower().startswith("description:")
            ):
                break
            value += re.sub(r"\s+", "", continuation)
        if value.startswith(("https://", "http://")) and value.endswith(".json"):
            return value
    return None


def official_catalog_override_reason(
    project_root: Path,
    *,
    kind: str,
    environment: dict[str, str] | None = None,
    user_home: Path | None = None,
) -> str | None:
    """Return why a non-default catalog configuration must be skipped."""
    env = os.environ if environment is None else environment
    if kind == "extension":
        env_name = "SPECKIT_CATALOG_URL"
        config_name = "extension-catalogs.yml"
        expected = OFFICIAL_EXTENSION_CATALOG
    elif kind == "workflow":
        env_name = "SPECKIT_WORKFLOW_CATALOG_URL"
        config_name = "workflow-catalogs.yml"
        expected = OFFICIAL_WORKFLOW_CATALOG
    else:
        raise ValueError(f"unsupported catalog kind: {kind}")

    override = env.get(env_name, "").strip()
    if override and override != expected:
        return f"{env_name} selects a non-default catalog"

    home = Path.home() if user_home is None else user_home
    for config in (project_root / ".specify" / config_name, home / ".specify" / config_name):
        if config.exists() or config.is_symlink():
            return f"custom catalog configuration exists: {config}"
    return None


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return None


class CacheStore:
    """Atomic cache for component checks and the pre-launch session gate."""

    def __init__(self, root: Path, now: datetime) -> None:
        self.root = root
        self.path = root / CACHE_RELATIVE_PATH
        self.now = now.astimezone(timezone.utc)
        self.data: dict[str, Any] = {"schema_version": CACHE_SCHEMA_VERSION, "components": {}}
        self.dirty = False
        self._validate_path()
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if (
                    isinstance(loaded, dict)
                    and loaded.get("schema_version") == CACHE_SCHEMA_VERSION
                    and isinstance(loaded.get("components"), dict)
                ):
                    self.data = loaded
                else:
                    print("缓存格式无法识别；本次按未缓存处理。")
            except (OSError, UnicodeError, json.JSONDecodeError):
                print("缓存文件损坏或不可读；本次按未缓存处理。")

    def _validate_path(self) -> None:
        state_dir = self.path.parent
        if state_dir.is_symlink() or self.path.is_symlink():
            raise UpdateError(f"缓存路径不能是符号链接：{self.path}")
        if state_dir.exists() and not state_dir.is_dir():
            raise UpdateError(f"缓存目录位置已被非目录文件占用：{state_dir}")
        if self.path.exists() and not self.path.is_file():
            raise UpdateError(f"缓存路径不是普通文件：{self.path}")
        try:
            state_dir.resolve(strict=False).relative_to(self.root.resolve())
        except (OSError, ValueError):
            raise UpdateError(f"缓存路径不在项目目录内：{self.path}") from None

    def get_fresh(self, key: str, identity: dict[str, Any]) -> dict[str, Any] | None:
        entry = self.data["components"].get(key)
        if not isinstance(entry, dict) or entry.get("identity") != identity:
            return None
        if entry.get("result") not in {
            "up-to-date",
            "updated",
            "local-ahead",
            "update-available",
            "blocked-by-cli",
        }:
            return None
        checked_at = entry.get("checked_at_utc")
        if not isinstance(checked_at, str):
            return None
        try:
            timestamp = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        if timestamp.tzinfo is None:
            return None
        age = self.now - timestamp.astimezone(timezone.utc)
        if age < timedelta(0) or age >= CACHE_TTL:
            return None
        return entry

    def set_full_check(self, status: str, *, checked_at: datetime | None = None) -> None:
        if status not in {"running", "success", "attention"}:
            raise ValueError(f"unsupported full-check status: {status}")
        timestamp = (checked_at or self.now).astimezone(timezone.utc)
        self.data["last_full_check"] = {
            "status": status,
            "checked_at_utc": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        self.dirty = True

    def full_check_is_fresh(self) -> bool:
        """Return whether AGENTS may skip launching this updater for seven days."""
        entry = self.data.get("last_full_check")
        if not isinstance(entry, dict) or entry.get("status") != "success":
            return False
        checked_at = entry.get("checked_at_utc")
        if not isinstance(checked_at, str):
            return False
        try:
            timestamp = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if timestamp.tzinfo is None:
            return False
        age = self.now - timestamp.astimezone(timezone.utc)
        return timedelta(0) <= age < CACHE_TTL

    def record(
        self,
        key: str,
        *,
        identity: dict[str, Any],
        result: str,
        detail: str,
        remote_check: bool,
    ) -> None:
        if result not in {
            "up-to-date",
            "updated",
            "local-ahead",
            "update-available",
            "blocked-by-cli",
        }:
            self.invalidate(key)
            return
        self.data["components"][key] = {
            "checked_at_utc": self.now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "identity": identity,
            "result": result,
            "detail": detail,
            "remote_check": remote_check,
        }
        self.dirty = True

    def invalidate(self, key: str) -> None:
        if key in self.data["components"]:
            del self.data["components"][key]
            self.dirty = True

    def invalidate_prefix(self, prefix: str) -> None:
        for key in tuple(self.data["components"]):
            if key.startswith(prefix):
                self.invalidate(key)

    def save(self) -> None:
        if not self.dirty:
            return
        self._validate_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".spec-kit-update-",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(self.data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temp_path, self.path)
            self.dirty = False
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


class CommandRunner:
    """Run read-only commands or stream an official CLI confirmation."""

    def __init__(
        self,
        binary: str,
        cwd: Path,
        *,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.binary = binary
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _environment() -> dict[str, str]:
        env = os.environ.copy()
        # Stable CLI output encoding keeps the parsers and Windows terminals
        # from depending on the active OEM code page.
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def capture(self, *args: str) -> CommandResult:
        try:
            result = subprocess.run(
                [self.binary, *args],
                cwd=self.cwd,
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            output = error.stdout or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            message = f"[更新助手] 官方 CLI 命令超过 {self.timeout_seconds:g} 秒，已终止。"
            print(message)
            output += f"\n{message}\n"
            return CommandResult(124, output)
        return CommandResult(result.returncode, result.stdout)

    def interactive(self, *args: str) -> CommandResult:
        process = subprocess.Popen(
            [self.binary, *args],
            cwd=self.cwd,
            env=self._environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        assert process.stdout is not None and process.stdin is not None
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        parts: list[str] = []
        prompt_buffer = ""
        answered_prompt = False
        timed_out = threading.Event()

        def terminate_after_timeout() -> None:
            timed_out.set()
            try:
                process.kill()
            except OSError:
                pass

        timer = threading.Timer(self.timeout_seconds, terminate_after_timeout)
        timer.daemon = True
        timer.start()
        try:
            while True:
                chunk = os.read(process.stdout.fileno(), 4096)
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if text:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    parts.append(text)
                    prompt_buffer = (prompt_buffer + text)[-512:]
                    response: bytes | None = None
                    if not answered_prompt and re.search(
                        r"update these extensions\?\s+\[[yYnN]/[yYnN]\]:\s*$",
                        prompt_buffer,
                        flags=re.IGNORECASE,
                    ):
                        print("\n[更新助手] 已按项目规则确认官方扩展更新。")
                        response = b"y\n"
                    elif not answered_prompt and re.search(
                        r"update these workflows\?\s+\[[yYnN]/[yYnN]\]:\s*$",
                        prompt_buffer,
                        flags=re.IGNORECASE,
                    ):
                        print("\n[更新助手] 已按项目规则确认官方工作流更新。")
                        response = b"y\n"
                    elif not answered_prompt and re.search(
                        r"\?\s+\[[yYnN]/[yYnN]\]:\s*$", prompt_buffer
                    ):
                        print("\n[更新助手] CLI 提出未识别的确认；助手按安全默认值拒绝。")
                        response = b"n\n"
                    if response is not None:
                        try:
                            process.stdin.write(response)
                            process.stdin.flush()
                        except OSError:
                            pass
                        answered_prompt = True
        finally:
            timer.cancel()
        tail = decoder.decode(b"", final=True)
        if tail:
            sys.stdout.write(tail)
            sys.stdout.flush()
            parts.append(tail)
        for stream in (process.stdin, process.stdout):
            try:
                stream.close()
            except OSError:
                pass
        returncode = process.wait()
        output = "".join(parts)
        if timed_out.is_set():
            message = f"[更新助手] 官方 CLI 命令超过 {self.timeout_seconds:g} 秒，已终止。"
            print(message)
            output += f"\n{message}\n"
            returncode = 124
        return CommandResult(returncode, output)


class ComponentUpdater:
    def __init__(
        self,
        root: Path,
        *,
        recheck: bool = False,
        runner: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.root = root
        self.recheck = recheck
        self._fixed_now = now
        self.now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.cache = CacheStore(root, self.now)
        self.runner = runner
        self.binary: str | None = None
        self.attention = False
        self.incomplete = False
        self.fatal = False
        self.lines: list[str] = []

    def report(self, component: str, status: str, detail: str = "") -> None:
        suffix = f" — {detail}" if detail else ""
        line = f"{component}: {status}{suffix}"
        self.lines.append(line)
        print(line)

    def capture(self, *args: str) -> CommandResult:
        assert self.runner is not None
        return self.runner.capture(*args)

    def interactive(self, *args: str) -> CommandResult:
        assert self.runner is not None
        return self.runner.interactive(*args)

    def remote_cache(self, key: str, identity: dict[str, Any]) -> dict[str, Any] | None:
        if self.recheck:
            return None
        return self.cache.get_fresh(key, identity)

    def record_remote(
        self, key: str, identity: dict[str, Any], result: str, detail: str
    ) -> None:
        self.cache.record(
            key,
            identity=identity,
            result=result,
            detail=detail,
            remote_check=True,
        )

    def setup_cli(self) -> str | None:
        self.binary = shutil.which("specify")
        if not self.binary:
            self.report("Spec Kit CLI", "失败", "PATH 中找不到 specify")
            self.fatal = True
            return None
        self.runner = CommandRunner(self.binary, self.root)
        result = self.capture("--version")
        version = parse_cli_version(result.output) if result.returncode == 0 else None
        if version is None:
            self.report("Spec Kit CLI", "状态未知", "无法读取或比较本地 CLI 版本")
            self.fatal = True
            return None
        self.report("Spec Kit CLI", "本地版本", version)
        return version

    def check_cli_release(self, cli_version: str) -> None:
        key = "cli-release"
        identity = {"cli_version": cli_version}
        cached = self.remote_cache(key, identity)
        if cached:
            detail = cached.get("detail", "")
            self.report("Spec Kit CLI 更新检查", "缓存命中", detail)
            if cached["result"] == "update-available":
                self.attention = True
            return

        result = self.capture("self", "check")
        parsed = parse_self_check(result.output) if result.returncode == 0 else None
        if parsed is None:
            self.cache.invalidate(key)
            self.report("Spec Kit CLI 更新检查", "未缓存", "检查失败或输出无法识别；下次会重试")
            self.attention = True
            self.incomplete = True
            return
        status, version = parsed
        if status == "up-to-date":
            self.record_remote(key, identity, status, f"当前为 {version}")
            self.report("Spec Kit CLI 更新检查", "已是最新", f"{version}；成功结果缓存 7 天")
        else:
            detail = f"可用版本 {version}；升级仍需用户明确批准"
            self.record_remote(key, identity, status, detail)
            self.report("Spec Kit CLI 更新检查", "发现更新", detail)
            self.attention = True

    def check_integrations(self, cli_version: str) -> None:
        result = self.capture("integration", "status", "--json")
        if result.returncode != 0:
            self.cache.invalidate_prefix("integration:")
            self.report("Agent 集成", "状态未知", "官方 status --json 失败")
            self.attention = True
            self.incomplete = True
            return
        try:
            keys = parse_installed_integrations(result.output)
        except (ValueError, json.JSONDecodeError) as error:
            self.cache.invalidate_prefix("integration:")
            self.report("Agent 集成", "状态未知", str(error))
            self.attention = True
            self.incomplete = True
            return
        if not keys:
            self.cache.invalidate_prefix("integration:")
            self.report("Agent 集成", "无已安装集成")
            return

        for key in keys:
            component = f"Agent 集成 {key}"
            if not SAFE_INTEGRATION_KEY.fullmatch(key) or key in {".", ".."}:
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", "清单键不安全，未读取或更新")
                self.attention = True
                self.incomplete = True
                continue
            manifest_path = self.root / ".specify" / "integrations" / f"{key}.manifest.json"
            if manifest_path.is_symlink() or not manifest_path.is_file():
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", "集成清单缺失或不是普通文件")
                self.attention = True
                self.incomplete = True
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_version = manifest.get("version") if isinstance(manifest, dict) else None
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", f"无法读取集成清单：{error}")
                self.attention = True
                self.incomplete = True
                continue
            if not isinstance(manifest_version, str):
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", "集成清单没有可比较的版本")
                self.attention = True
                self.incomplete = True
                continue

            classification = classify_integration_version(cli_version, manifest_version)
            identity = {"cli_version": cli_version, "manifest_version": manifest_version}
            if classification == "current":
                self.cache.record(
                    f"integration:{key}",
                    identity=identity,
                    result="up-to-date",
                    detail=f"CLI {cli_version} 与清单版本一致",
                    remote_check=False,
                )
                self.report(component, "已是当前 CLI 发布版本", manifest_version)
                continue
            if classification == "future-manifest":
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", f"清单版本 {manifest_version} 高于 CLI {cli_version}")
                self.attention = True
                self.incomplete = True
                continue
            if classification == "unknown":
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "状态未知", "版本格式无法安全比较")
                self.attention = True
                self.incomplete = True
                continue

            self.report(component, "发现较旧清单", f"{manifest_version} → {cli_version}；运行官方升级")
            upgraded = self.interactive("integration", "upgrade", key, "--force")
            if upgraded.returncode != 0 or "cancelled" in upgraded.output.lower():
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "升级失败", "未记录成功状态")
                self.attention = True
                self.incomplete = True
                continue
            try:
                after = json.loads(manifest_path.read_text(encoding="utf-8"))
                after_version = after.get("version") if isinstance(after, dict) else None
            except (OSError, UnicodeError, json.JSONDecodeError):
                after_version = None
            if after_version != cli_version:
                self.cache.invalidate(f"integration:{key}")
                self.report(component, "升级结果未核实", "升级后清单版本未匹配当前 CLI")
                self.attention = True
                self.incomplete = True
                continue
            self.cache.record(
                f"integration:{key}",
                identity={"cli_version": cli_version, "manifest_version": after_version},
                result="updated",
                detail=f"已核实版本 {after_version}",
                remote_check=False,
            )
            self.report(component, "已更新并核实", after_version)

    def extension_catalogs(self) -> tuple[dict[str, Catalog] | None, str | None]:
        reason = official_catalog_override_reason(self.root, kind="extension")
        if reason:
            return None, reason
        result = self.capture("extension", "catalog", "list")
        if result.returncode != 0:
            return None, "官方 CLI 无法列出活动扩展目录"
        catalogs = parse_extension_catalogs(result.output)
        if not catalogs or catalogs[0].url != OFFICIAL_EXTENSION_CATALOG:
            return None, "活动扩展目录首选项无法确认为 Spec Kit 官方目录"
        return {catalog.name: catalog for catalog in catalogs}, None

    def check_extensions(self, cli_version: str) -> None:
        inventory_result = self.capture("extension", "list", "--json")
        if inventory_result.returncode != 0:
            for extension_id in APPROVED_EXTENSIONS:
                self.cache.invalidate(f"extension:{extension_id}")
            self.report("官方扩展", "状态未知", "官方 CLI 无法读取已安装扩展清单")
            self.attention = True
            self.incomplete = True
            return
        try:
            records = parse_installed_extensions(inventory_result.output)
        except (ValueError, json.JSONDecodeError) as error:
            for extension_id in APPROVED_EXTENSIONS:
                self.cache.invalidate(f"extension:{extension_id}")
            self.report("官方扩展", "状态未知", f"扩展 JSON 无法解析：{error}")
            self.attention = True
            self.incomplete = True
            return
        installed = {record["id"]: record for record in records}
        targets = [extension_id for extension_id in APPROVED_EXTENSIONS if extension_id in installed]
        if not targets:
            for extension_id in APPROVED_EXTENSIONS:
                self.cache.invalidate(f"extension:{extension_id}")
            self.report("官方扩展", "未安装 assess 或 bug；跳过")
            return

        _, reason = self.extension_catalogs()
        if reason:
            for extension_id in targets:
                self.cache.invalidate(f"extension:{extension_id}")
            self.report("官方扩展", "状态未知", f"来源校验失败：{reason}")
            self.attention = True
            self.incomplete = True
            return
        for extension_id in targets:
            component = f"扩展 {extension_id}"
            record = installed[extension_id]
            local_version = record["version"]
            identity = {
                "cli_version": cli_version,
                "local_version": local_version,
                "catalog_url": OFFICIAL_EXTENSION_CATALOG,
            }
            key = f"extension:{extension_id}"
            cached = self.remote_cache(key, identity)
            if cached:
                self.report(component, "缓存命中", cached.get("detail", cached["result"]))
                if cached["result"] == "blocked-by-cli":
                    self.attention = True
                continue

            before = parse_version(local_version)
            if before is None:
                self.cache.invalidate(key)
                self.report(component, "状态未知", f"本地版本格式无法比较：{local_version}")
                self.attention = True
                self.incomplete = True
                continue
            result = self.interactive("extension", "update", extension_id)
            output = ANSI_PATTERN.sub("", result.output)
            lower_output = output.lower()
            if result.returncode != 0 or "cancelled" in lower_output or "canceled" in lower_output:
                self.cache.invalidate(key)
                self.report(component, "检查或更新失败", "未写入成功检查时间；下次会重试")
                self.attention = True
                self.incomplete = True
                continue
            if "upgrade spec-kit" in lower_output and "available" in lower_output:
                detail = "目录有更新，但当前 CLI 不能安装该版本"
                self.record_remote(key, identity, "blocked-by-cli", detail)
                self.report(component, "等待 CLI 升级", detail)
                self.attention = True
                continue
            if "all extensions are up to date" in lower_output or re.search(
                rf"\b{re.escape(extension_id)}\b.*\bup to date\b", lower_output
            ):
                detail = f"{local_version}；成功结果缓存 7 天"
                self.record_remote(key, identity, "up-to-date", detail)
                self.report(component, "已是最新", detail)
                continue
            if "successfully updated" in lower_output:
                after_result = self.capture("extension", "list", "--json")
                try:
                    after_records = parse_installed_extensions(after_result.output)
                    after_record = next(item for item in after_records if item["id"] == extension_id)
                    after_version = after_record["version"]
                except (ValueError, json.JSONDecodeError, StopIteration):
                    after_version = None
                after = parse_version(after_version)
                if after_result.returncode == 0 and after is not None and after > before:
                    identity = {
                        "cli_version": cli_version,
                        "local_version": after_version,
                        "catalog_url": OFFICIAL_EXTENSION_CATALOG,
                    }
                    detail = f"已核实更新到 {after_version}；成功结果缓存 7 天"
                    self.record_remote(key, identity, "updated", detail)
                    self.report(component, "已更新并核实", detail)
                    continue
            self.cache.invalidate(key)
            self.report(component, "结果无法核实", "CLI 输出或安装版本不符合已确认格式；下次会重试")
            self.attention = True
            self.incomplete = True

    def workflow_catalogs(self) -> tuple[list[Catalog] | None, str | None]:
        reason = official_catalog_override_reason(self.root, kind="workflow")
        if reason:
            return None, reason
        result = self.capture("workflow", "catalog", "list")
        if result.returncode != 0:
            return None, "官方 CLI 无法列出活动工作流目录"
        catalogs = parse_workflow_catalogs(result.output)
        if (
            not catalogs
            or catalogs[0].url != OFFICIAL_WORKFLOW_CATALOG
            or not catalogs[0].install_allowed
        ):
            return None, "活动工作流目录首选项无法确认为可安装的 Spec Kit 官方目录"
        return catalogs, None

    def check_workflows(self, cli_version: str) -> None:
        registry_path = self.root / ".specify" / "workflows" / "workflow-registry.json"
        if registry_path.is_symlink() or not registry_path.is_file():
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "状态未知", "工作流注册表缺失或不是普通文件")
            self.attention = True
            self.incomplete = True
            return
        try:
            workflows = parse_workflow_registry(registry_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "状态未知", f"注册表无法解析：{error}")
            self.attention = True
            self.incomplete = True
            return
        metadata = workflows.get("speckit")
        if metadata is None:
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "未安装；跳过")
            return
        source = metadata.get("source")
        local_version = metadata.get("version")
        if source not in {"bundled", "catalog"} or not isinstance(local_version, str):
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "来源或版本未知；跳过")
            self.attention = True
            self.incomplete = True
            return
        if parse_version(local_version) is None:
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "状态未知", f"本地版本格式无法比较：{local_version}")
            self.attention = True
            self.incomplete = True
            return

        catalogs, reason = self.workflow_catalogs()
        if catalogs is None:
            self.cache.invalidate("workflow:speckit")
            self.report("工作流 speckit", "状态未知", f"来源校验失败：{reason}")
            self.attention = True
            self.incomplete = True
            return

        identity = {
            "cli_version": cli_version,
            "local_version": local_version,
            "source": source,
            "catalog_url": OFFICIAL_WORKFLOW_CATALOG,
        }
        key = "workflow:speckit"
        cached = self.remote_cache(key, identity)
        if cached:
            self.report("工作流 speckit", "缓存命中", cached.get("detail", cached["result"]))
            continue_attention = cached["result"] == "blocked-by-cli"
            self.attention = self.attention or continue_attention
            return

        info_result = self.capture("workflow", "info", "speckit")
        search_result = self.capture("workflow", "search", "speckit")
        local_info_version = (
            parse_workflow_info_version(info_result.output)
            if info_result.returncode == 0
            else None
        )
        catalog_version = (
            parse_workflow_search_version(search_result.output, "speckit")
            if search_result.returncode == 0
            else None
        )
        if local_info_version != local_version or catalog_version is None:
            self.cache.invalidate(key)
            self.report("工作流 speckit", "版本无法核实", "CLI info/search 与注册表不一致或目录结果不唯一")
            self.attention = True
            self.incomplete = True
            return

        local_parsed = parse_version(local_version)
        catalog_parsed = parse_version(catalog_version)
        assert local_parsed is not None and catalog_parsed is not None
        if catalog_parsed < local_parsed:
            detail = f"本地 {local_version} 高于官方目录 {catalog_version}；不降级"
            self.record_remote(key, identity, "local-ahead", detail)
            self.report("工作流 speckit", "本地版本较新", detail)
            return
        if catalog_parsed == local_parsed:
            detail = f"{local_version}；成功结果缓存 7 天"
            self.record_remote(key, identity, "up-to-date", detail)
            self.report("工作流 speckit", "已是最新", detail)
            return

        self.report(
            "工作流 speckit",
            "发现更新",
            f"{local_version} → {catalog_version}；调用官方 CLI",
        )
        if source == "catalog":
            update_result = self.interactive("workflow", "update", "speckit")
        else:
            update_result = self.interactive("workflow", "add", "speckit")
        update_output = ANSI_PATTERN.sub("", update_result.output).lower()
        if (
            update_result.returncode != 0
            or "cancelled" in update_output
            or "canceled" in update_output
        ):
            self.cache.invalidate(key)
            self.report("工作流 speckit", "更新失败或取消", "未写入成功检查时间；下次会重试")
            self.attention = True
            self.incomplete = True
            return

        verify = self.capture("workflow", "info", "speckit")
        verified_version = (
            parse_workflow_info_version(verify.output) if verify.returncode == 0 else None
        )
        verified_parsed = parse_version(verified_version) if verified_version else None
        if verified_parsed is None or verified_parsed < catalog_parsed:
            self.cache.invalidate(key)
            self.report("工作流 speckit", "更新结果未核实", "本地版本仍低于目录候选版本；下次会重试")
            self.attention = True
            self.incomplete = True
            return
        identity = {
            "cli_version": cli_version,
            "local_version": verified_version,
            "source": "catalog",
            "catalog_url": OFFICIAL_WORKFLOW_CATALOG,
        }
        detail = f"已核实更新到 {verified_version}；成功结果缓存 7 天"
        self.record_remote(key, identity, "updated", detail)
        self.report("工作流 speckit", "已更新并核实", detail)

    def run(self) -> int:
        # Persist a non-success gate before doing work. If this process is
        # interrupted or any check needs attention, the next session retries.
        self.cache.set_full_check("running")
        try:
            self.cache.save()
        except (OSError, UpdateError) as error:
            self.report("缓存", "写入失败", str(error))
            self.attention = True
            return 2

        cli_version = self.setup_cli()
        if cli_version is None:
            self.incomplete = True
            self.cache.set_full_check("attention")
            try:
                self.cache.save()
            except (OSError, UpdateError) as error:
                self.report("缓存", "写入失败", str(error))
            return 1
        print(f"项目：{self.root}")
        if self.recheck:
            print("远端版本检查：忽略七天缓存")
        self.check_cli_release(cli_version)
        self.check_integrations(cli_version)
        self.check_extensions(cli_version)
        self.check_workflows(cli_version)
        finished_at = self._fixed_now or datetime.now(timezone.utc)
        self.cache.set_full_check(
            "attention" if self.incomplete else "success",
            checked_at=finished_at,
        )
        try:
            self.cache.save()
        except (OSError, UpdateError) as error:
            self.report("缓存", "写入失败", str(error))
            self.attention = True
        return 2 if self.attention else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按需检查并更新项目中已安装的官方 Spec Kit 组件。"
    )
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="忽略七天远端检查缓存；仍只在 CLI 发现更新时调用对应更新命令。",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    root = find_project_root(Path.cwd())
    if root is None:
        print("错误：当前目录及父目录中没有 .specify/；请从 Spec Kit 项目内运行。", file=sys.stderr)
        return 1
    if sys.version_info < (3, 10):
        print("错误：更新助手需要 Python 3.10 或更高版本。", file=sys.stderr)
        return 1
    try:
        updater = ComponentUpdater(root, recheck=args.recheck)
        return updater.run()
    except UpdateError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
