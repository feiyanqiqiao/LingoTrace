#!/usr/bin/env python3
"""Portable, Agent-neutral Spec Kit governance manager.

The manager deliberately keeps the first implementation small and explicit:
read-only discovery is available without a Spec Kit project, while every
filesystem or external CLI mutation is represented by a canonical plan and
must pass through ``apply-plan``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
PLAN_TTL = timedelta(minutes=30)
RUNTIME_DIR = ".spec-kit-governance"
PROJECT_PACKAGE = "docs/spec-kit"
MANAGER_RELATIVE = "tools/spec-kit-governance/governance.py"
START_MARKER = "<!-- PROJECT-SPEC-KIT-GOVERNANCE:START -->"
END_MARKER = "<!-- PROJECT-SPEC-KIT-GOVERNANCE:END -->"
CLI_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(\.dev|a|b|rc)(\d+))?$")
SAFE_RELATIVE = re.compile(r"^[^/\\].*$")
STATUSES = {
    "CLI_MISSING", "CLI_INCOMPATIBLE", "CLI_VERSION_UNTESTED", "CLI_VERSION_UNPARSEABLE",
    "IDENTITY_UNKNOWN", "IDENTITY_CONFLICT", "KEY_REQUIRED", "PROJECT_NOT_INITIALIZED",
    "EXACT_NATIVE_INSTALLED", "NATIVE_CANDIDATE_NOT_INSTALLED", "NATIVE_CANDIDATE_INSTALLED_UNVERIFIED",
    "NATIVE_CANDIDATE_REJECTED", "NATIVE_INSTALL_BLOCKED", "AMBIGUOUS", "CATALOG_UNAVAILABLE",
    "CONTEXT_ANCHOR_UNKNOWN", "ANCHOR_FORMAT_UNSUPPORTED", "UNSUPPORTED_GENERIC_COMPATIBLE",
    "UNSUPPORTED_INCOMPATIBLE", "INTEGRATION_CONFLICT", "DEFAULT_CHANGE_FORBIDDEN",
    "CENTRAL_SOURCE_UNVERIFIED", "PROJECT_RULES_PROTECTED", "STATE_BROKEN", "RECOVERY_REQUIRED", "READY_WITH_LIMITATIONS", "READY",
}


class GovernanceError(RuntimeError):
    def __init__(self, message: str, status: str | None = None) -> None:
        super().__init__(message)
        self.status = status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def plan_hash(plan: dict[str, Any]) -> str:
    payload = dict(plan)
    payload.pop("plan_sha256", None)
    return sha256_bytes(canonical_json(payload))


def validate_plan_shape(plan: dict[str, Any]) -> None:
    required = {"schema_version", "plan_id", "operation_type", "created_at", "expires_at", "project_root_fingerprint", "git_status_porcelain_sha256", "manager_file_mutations", "external_cli_mutations", "capability_inventory_before", "plan_sha256"}
    missing = sorted(required - set(plan))
    if missing:
        raise GovernanceError(f"plan missing required fields: {', '.join(missing)}", "STATE_BROKEN")
    if plan.get("schema_version") != SCHEMA_VERSION or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(plan.get("plan_id"))):
        raise GovernanceError("unsupported or malformed plan identity", "STATE_BROKEN")
    if plan.get("operation_type") == "plan-init" and plan.get("claimed_integration_key") == "generic":
        raise GovernanceError("plan-init cannot use generic integration", "UNSUPPORTED_INCOMPATIBLE")
    if plan.get("operation_type") == "plan-init" and not isinstance(plan.get("rehearsal"), dict):
        raise GovernanceError("plan-init requires isolated init rehearsal evidence", "STATE_BROKEN")
    if plan.get("operation_type") == "plan-init" and not valid_language_tag(plan.get("documentation_language")):
        raise GovernanceError("plan-init requires an explicit documentation language", "DOCUMENTATION_LANGUAGE_REQUIRED")
    if plan.get("operation_type") == "plan-init" and not plan.get("current_agent", {}).get("runtime_id"):
        raise GovernanceError("plan-init requires an explicit runtime identity", "IDENTITY_UNKNOWN")
    if plan.get("operation_type") == "plan-init" and not plan.get("context_anchor"):
        raise GovernanceError("plan-init requires an explicit project context anchor", "CONTEXT_ANCHOR_UNKNOWN")
    if plan.get("operation_type") in {"plan-governance-bootstrap", "plan-onboard"} and not plan.get("context_anchor"):
        raise GovernanceError("an explicit project context anchor is required", "CONTEXT_ANCHOR_UNKNOWN")
    if plan.get("operation_type") == "plan-onboard" and plan.get("context_anchor") and not plan.get("anchor_compatibility_evidence"):
        raise GovernanceError("onboarding requires anchor compatibility evidence", "CONTEXT_ANCHOR_UNKNOWN")
    context_anchor = plan.get("context_anchor")
    for item in plan.get("manager_file_mutations", []):
        if item.get("path") == "" or item.get("old_sha256") is not None and not re.fullmatch(r"[0-9a-f]{64}", item["old_sha256"]):
            raise GovernanceError("malformed manager mutation", "STATE_BROKEN")
        if item.get("expected_new_sha256") and not re.fullmatch(r"[0-9a-f]{64}", item["expected_new_sha256"]):
            raise GovernanceError("malformed manager mutation checksum", "STATE_BROKEN")
        if item.get("protected_anchor") is True and item.get("path") != context_anchor:
            raise GovernanceError("protected anchor mutation does not match the declared context anchor", "STATE_BROKEN")
        if item.get("path") == context_anchor and (item.get("action") != "append-managed-loader" or item.get("protected_anchor") is not True):
            raise GovernanceError("the declared project rules anchor accepts only a managed Loader append", "PROJECT_RULES_PROTECTED")
    for item in plan.get("external_cli_mutations", []):
        argv = item.get("argv", [])
        if not argv or argv[0] != "specify":
            raise GovernanceError("external mutation executable is not allowlisted", "UNSUPPORTED_INCOMPATIBLE")
        if "--force" in argv and plan.get("operation_type") != "plan-init":
            raise GovernanceError("--force is forbidden outside plan-init", "UNSUPPORTED_INCOMPATIBLE")


def project_root_from(path: Path | None = None) -> Path:
    candidate = (path or Path.cwd()).resolve()
    for item in (candidate, *candidate.parents):
        if (item / ".git").exists():
            return item
    return candidate


def safe_relative(root: Path, value: str) -> Path:
    if not value or "\x00" in value or Path(value).is_absolute() or not SAFE_RELATIVE.match(value):
        raise GovernanceError(f"unsafe project-relative path: {value!r}")
    rel = Path(value)
    if ".." in rel.parts:
        raise GovernanceError(f"path traversal is forbidden: {value!r}")
    target = (root / rel).resolve(strict=False)
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise GovernanceError(f"path escapes project root: {value!r}") from exc
    return rel


def relative_existing(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"invalid JSON: {path}: {exc}", "STATE_BROKEN") from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"JSON object required: {path}", "STATE_BROKEN")
    return value


def git_value(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def git_fingerprint(root: Path) -> dict[str, str]:
    raw_status = git_value(root, "status", "--porcelain=v1", "--untracked-files=all")
    # The manager's own plan, backup, and journal files are ephemeral runtime
    # state.  They must not invalidate the exact plan between plan creation and
    # apply; all durable project mutations remain covered by the file hashes in
    # the plan itself.
    status_lines = []
    for line in raw_status.splitlines():
        path_text = line[3:] if len(line) >= 3 else ""
        if path_text == RUNTIME_DIR or path_text.startswith(RUNTIME_DIR + "/"):
            continue
        status_lines.append(line)
    status = "\n".join(status_lines)
    head = git_value(root, "rev-parse", "HEAD") or "UNBORN"
    return {
        "git_head": head,
        "git_status_porcelain_sha256": sha256_bytes(status.encode("utf-8")),
        "project_root_fingerprint": sha256_bytes(str(root).encode("utf-8")),
    }


def cli_version() -> str | None:
    executable = shutil.which("specify")
    if not executable:
        return None
    result = subprocess.run([executable, "version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = (result.stdout or result.stderr)
    # Current Specify renders a rich information panel rather than a plain
    # version line.  Accept the machine-readable --version form first, then
    # extract the labelled CLI Version field from the panel.
    simple = subprocess.run([executable, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    simple_text = (simple.stdout or simple.stderr).strip()
    match = re.search(r"\b(\d+\.\d+\.\d+(?:(?:\.dev|a|b|rc)\d+)?)\b", simple_text)
    if match:
        return match.group(1)
    match = re.search(r"CLI Version\s+([^\s│]+)", output)
    return match.group(1).strip() if result.returncode == 0 and match else None


def parse_cli_version(value: str) -> tuple[int, int, int, int, int]:
    match = CLI_VERSION_RE.fullmatch(value.strip())
    if not match:
        raise GovernanceError(f"unparseable specify version: {value}", "CLI_VERSION_UNPARSEABLE")
    major, minor, patch, stage, number = match.groups()
    ranks = {".dev": 0, "a": 1, "b": 2, "rc": 3, None: 4}
    return int(major), int(minor), int(patch), ranks[stage], int(number or 0)


def command_status(root: Path) -> dict[str, Any] | None:
    executable = shutil.which("specify")
    if not executable or not (root / ".specify").is_dir():
        return None
    result = subprocess.run([executable, "integration", "status", "--json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise GovernanceError(result.stderr.strip() or "integration status failed", "STATE_BROKEN")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GovernanceError("integration status did not return JSON", "STATE_BROKEN") from exc
    if not isinstance(data, dict):
        raise GovernanceError("integration status JSON must be an object", "STATE_BROKEN")
    return data


def project_config(root: Path) -> dict[str, Any] | None:
    path = root / PROJECT_PACKAGE / "PROJECT_CONFIG.json"
    return read_json(path) if path.is_file() else None


def adapters(root: Path) -> dict[str, Any]:
    path = root / PROJECT_PACKAGE / "ADAPTERS.json"
    return read_json(path) if path.is_file() else {"schema_version": 1, "anchors": [], "bindings": []}


def validate_project_package(root: Path) -> list[str]:
    errors: list[str] = []
    config_path = root / PROJECT_PACKAGE / "PROJECT_CONFIG.json"
    adapter_path = root / PROJECT_PACKAGE / "ADAPTERS.json"
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    if config_path.is_file():
        config = read_json(config_path)
        required = {"schema_version", "default_integration", "onboarding", "generic", "catalogs", "context", "documentation", "upgrade", "quality_gates"}
        errors.extend(f"PROJECT_CONFIG missing {name}" for name in sorted(required - set(config)))
        if config.get("schema_version") != 1:
            errors.append("PROJECT_CONFIG schema_version must be 1")
        if config.get("default_integration", {}).get("policy") != "pinned":
            errors.append("default integration policy must be pinned")
        if config.get("onboarding", {}).get("allow_unsafe_multi_install") is not False:
            errors.append("unsafe multi-install must remain disabled")
        language_tag = config.get("documentation", {}).get("language_tag")
        if language_tag is not None and not valid_language_tag(language_tag):
            errors.append("documentation language_tag must be null or a valid BCP 47 tag")
        if (root / ".specify").is_dir() and language_tag is None:
            errors.append("initialized Spec Kit projects require an explicit documentation language")
    if adapter_path.is_file():
        registry = read_json(adapter_path)
        if registry.get("schema_version") != 1 or not isinstance(registry.get("anchors"), list) or not isinstance(registry.get("bindings"), list):
            errors.append("ADAPTERS schema is invalid")
        for binding in registry.get("bindings", []):
            if binding.get("integration_mode") == "native" and binding.get("verification", {}).get("status") == "active":
                if binding.get("verification", {}).get("method") not in {"fresh-session-loader", "fresh-session-materialized"}:
                    errors.append("active native binding must be fresh-session verified")
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        required = {"schema_version", "governance_package_version", "policy_version", "reference_version", "source", "specify_compatibility", "paths", "content_sha256", "project_owned_files"}
        errors.extend(f"MANIFEST missing {name}" for name in sorted(required - set(manifest)))
        if manifest.get("schema_version") != 1:
            errors.append("MANIFEST schema_version must be 1")
    return errors


def cli_compatibility(root: Path) -> str:
    version = cli_version()
    if version is None:
        return "CLI_MISSING"
    try:
        current = parse_cli_version(version)
    except GovernanceError:
        return "CLI_VERSION_UNPARSEABLE"
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    if not manifest_path.is_file():
        return "READY"
    manifest = read_json(manifest_path)
    compatibility = manifest.get("specify_compatibility", {})
    minimum = compatibility.get("minimum_version")
    maximum = compatibility.get("maximum_version_exclusive")
    tested = compatibility.get("tested_version")
    if tested and current == parse_cli_version(tested):
        return "READY"
    if minimum and current < parse_cli_version(minimum):
        return "CLI_INCOMPATIBLE"
    if maximum and current >= parse_cli_version(maximum):
        return "CLI_INCOMPATIBLE"
    if tested and current > parse_cli_version(tested):
        return "CLI_VERSION_UNTESTED"
    return "READY"


def governance_files(root: Path) -> list[str]:
    return [
        f"{PROJECT_PACKAGE}/START_HERE.md", f"{PROJECT_PACKAGE}/POLICY.md", f"{PROJECT_PACKAGE}/REFERENCE.md",
        f"{PROJECT_PACKAGE}/OPERATING_PROTOCOL.md", f"{PROJECT_PACKAGE}/AGENT_ONBOARDING.md",
        f"{PROJECT_PACKAGE}/LOCAL_OVERRIDES.md", f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json",
        f"{PROJECT_PACKAGE}/MANIFEST.json", f"{PROJECT_PACKAGE}/ADAPTERS.json", MANAGER_RELATIVE,
    ]


def source_root(value: str | None) -> Path:
    root = Path(value).resolve() if value else Path(__file__).resolve().parents[2]
    required = [root / "governance/project", root / "governance/schemas"]
    if not all(item.is_dir() for item in required):
        raise GovernanceError(f"invalid governance source: {root}")
    return root


def valid_language_tag(value: Any) -> bool:
    """Accept a structurally valid BCP 47 language tag without a product-specific list."""
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", value) is not None


def marker_loader(documentation_language: str | None = None) -> str:
    language_rule = ""
    if documentation_language is not None:
        if not valid_language_tag(documentation_language):
            raise GovernanceError("documentation language must be a valid BCP 47 tag", "DOCUMENTATION_LANGUAGE_INVALID")
        language_rule = (
            f"\n\n## Documentation language\n\n"
            f"Project documentation language: `{documentation_language}`.\n\n"
            "Write new and substantively rewritten project documentation, including Spec Kit artifacts, "
            "in this language unless an explicit user or more specific project instruction overrides it. "
            "Do not translate existing documentation solely because this setting was selected."
        )
    return (
        f"{START_MARKER}\n\n"
        "# Spec Kit Governance\n\n"
        "This repository uses the committed project-local Spec Kit governance package.\n\n"
        "Read `docs/spec-kit/START_HERE.md` before substantive engineering work.\n\n"
        f"Do not replace the project baseline with personal global rules or a local Reference.{language_rule}\n\n"
        f"{END_MARKER}\n"
    )


def append_loader(existing: bytes, loader: bytes) -> bytes:
    """Upsert one managed Loader while preserving every byte outside its markers."""
    start = START_MARKER.encode("utf-8")
    end = END_MARKER.encode("utf-8")
    start_count = existing.count(start)
    end_count = existing.count(end)
    if start_count != end_count or start_count > 1:
        raise GovernanceError("project context anchor has malformed or duplicate governance markers", "STATE_BROKEN")
    if start_count == 1:
        start_at = existing.index(start)
        end_at = existing.index(end, start_at) + len(end)
        current_block = existing[start_at:end_at]
        if current_block == loader.rstrip(b"\n"):
            return existing
        if existing[end_at:end_at + 2] == b"\r\n":
            end_at += 2
        elif existing[end_at:end_at + 1] == b"\n":
            end_at += 1
        return existing[:start_at] + loader + existing[end_at:]
    if not existing.strip():
        return loader
    if existing.endswith(b"\n\n") or existing.endswith(b"\r\n\r\n"):
        separator = b""
    elif existing.endswith(b"\r\n"):
        separator = b"\r\n"
    elif existing.endswith(b"\n"):
        separator = b"\n"
    else:
        separator = b"\n\n"
    return existing + separator + loader


def preflight_writable(root: Path, rel: str) -> dict[str, Any]:
    safe_relative(root, rel)
    target = root / rel
    parent = target.parent
    if target.exists() and not target.is_file():
        raise GovernanceError(f"native anchor is not a regular file: {rel}", "NATIVE_INSTALL_BLOCKED")
    if parent.exists() and not os.access(parent, os.W_OK):
        raise GovernanceError(f"native anchor parent is not writable: {rel}", "NATIVE_INSTALL_BLOCKED")
    if target.exists() and not os.access(target, os.W_OK):
        raise GovernanceError(f"native anchor is not writable: {rel}", "NATIVE_INSTALL_BLOCKED")
    return {"path": rel, "writable": True, "evidence": "os.access(parent,target,W_OK)"}


def file_mutation(root: Path, rel: str, content: bytes, action: str = "create", *, protected_anchor: bool = False) -> dict[str, Any]:
    safe_relative(root, rel)
    if protected_anchor and action != "append-managed-loader":
        raise GovernanceError("the project-owned context anchor accepts only append-managed-loader", "PROJECT_RULES_PROTECTED")
    target = root / rel
    actual_action = action if action == "append-managed-loader" or target.exists() else "create"
    expected_content = content
    if actual_action == "append-managed-loader" and target.is_file():
        expected_content = append_loader(target.read_bytes(), content)
    mutation = {
        "action": actual_action,
        "path": rel,
        "old_sha256": sha256_file(target) if target.is_file() else None,
        "expected_new_sha256": sha256_bytes(expected_content),
        "mode": stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644,
        "content_b64": base64.b64encode(content).decode("ascii"),
    }
    if protected_anchor:
        mutation["protected_anchor"] = True
    return mutation


def onboarding_mutations(root: Path, runtime_id: str, display_name: str, key: str, anchor_path: str, evidence_rel: str, *, integration_mode: str = "native", attestation_hash: str | None = None, attestation_rel: str | None = None, commands_dir: str | None = None, delivery_mode: str = "loader") -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    preflight_writable(root, anchor_path)
    anchor_mutation = file_mutation(
        root, anchor_path, marker_loader().encode("utf-8"),
        "append-managed-loader", protected_anchor=True,
    )
    evidence = {
        "schema_version": 1,
        "runtime_id": runtime_id,
        "display_name": display_name,
        "integration_key": key,
        "integration_mode": integration_mode,
        "anchor_path": anchor_path,
        "result": "native-install-provisional",
        "verified": False,
        "created_at": iso(utc_now()),
    }
    evidence_bytes = canonical_json(evidence) + b"\n"
    evidence_mutation = file_mutation(root, evidence_rel, evidence_bytes)
    evidence_hash = evidence_mutation["expected_new_sha256"]
    anchor_id = "anchor-" + sha256_bytes(anchor_path.encode("utf-8"))[:16]
    adapters_path = root / PROJECT_PACKAGE / "ADAPTERS.json"
    registry = adapters(root)
    anchors = [item for item in registry.get("anchors", []) if item.get("id") != anchor_id]
    anchors.append({
        "id": anchor_id, "path": anchor_path, "format": "markdown", "delivery_mode": delivery_mode,
        "marker_start": START_MARKER, "marker_end": END_MARKER,
        "managed_content_sha256": anchor_mutation["expected_new_sha256"], "status": "rendered", "managed": True,
    })
    bindings = [item for item in registry.get("bindings", []) if item.get("runtime_id") != runtime_id]
    bindings.append({
        "runtime_id": runtime_id, "display_name": display_name or runtime_id, "integration_key": key,
        "integration_mode": integration_mode, "status_evidence_sha256": evidence_hash,
        "default_integration_changed": False, "anchor_ids": [anchor_id],
        "capabilities": {"core_workflow": "not-verified", "extensions": "not-verified", "presets": "not-verified", "events": "not-verified"},
        "verification": {"status": "provisional", "specify_version": cli_version() or "unknown", "product_version": runtime_id, "verified_at": iso(utc_now()), "method": "fresh-session-materialized" if delivery_mode == "materialized" else "fresh-session-loader", "evidence": evidence_rel},
    })
    if integration_mode == "explicit-generic-transition":
        bindings[-1]["generic_transition"] = {
            "native_absence_attestation_sha256": attestation_hash or "0" * 64,
            "native_absence_evidence": attestation_rel or evidence_rel,
            "attested_specify_version": cli_version() or "unknown",
            "native_integration_available_at_approval": False,
            "limitations_acknowledged": True,
            "commands_dir": commands_dir or "",
            "format": "markdown",
            "compatibility_verified": True,
        }
    registry = {"schema_version": 1, "anchors": anchors, "bindings": bindings}
    adapters_mutation = file_mutation(root, f"{PROJECT_PACKAGE}/ADAPTERS.json", canonical_json(registry) + b"\n", "replace")
    mutations = [anchor_mutation, evidence_mutation, adapters_mutation]
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        manifest.setdefault("content_sha256", {})[f"{PROJECT_PACKAGE}/ADAPTERS.json"] = adapters_mutation["expected_new_sha256"]
        mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", canonical_json(manifest) + b"\n", "replace"))
    return mutations, {"path": anchor_path, "writable": True, "evidence": "preflight_writable"}, anchor_id


def governance_update_mutations(root: Path, source: Path) -> list[dict[str, Any]]:
    mapping = {
        "START_HERE.md": source / "governance/project/START_HERE.md",
        "POLICY.md": source / "governance/project/POLICY.md",
        "REFERENCE.md": source / "governance/project/REFERENCE.md",
        "OPERATING_PROTOCOL.md": source / "governance/project/OPERATING_PROTOCOL.md",
        "AGENT_ONBOARDING.md": source / "governance/project/AGENT_ONBOARDING.md",
    }
    mutations = [file_mutation(root, f"{PROJECT_PACKAGE}/{name}", path.read_bytes(), "replace") for name, path in mapping.items()]
    manager_source = source / "governance/manager/speckit_governance.py"
    if not manager_source.is_file():
        raise GovernanceError("governance manager is missing from update source", "CENTRAL_SOURCE_UNVERIFIED")
    mutations.append(file_mutation(root, MANAGER_RELATIVE, manager_source.read_bytes(), "replace"))
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        for item in mutations:
            manifest.setdefault("content_sha256", {})[item["path"]] = item["expected_new_sha256"]
        manifest["source"] = manifest.get("source", {})
        source_revision = git_value(source, "rev-parse", "HEAD")
        if re.fullmatch(r"[0-9a-f]{40}", source_revision):
            manifest["source"]["revision"] = source_revision
        mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", canonical_json(manifest) + b"\n", "replace"))
    return mutations


def activate_binding_mutations(root: Path, runtime_id: str, key: str, evidence_rel: str, delivery_mode: str) -> list[dict[str, Any]]:
    evidence_path = root / safe_relative(root, evidence_rel)
    if not evidence_path.is_file():
        raise GovernanceError("fresh-session verification evidence is missing", "CONTEXT_ANCHOR_UNKNOWN")
    evidence = read_json(evidence_path)
    if evidence.get("runtime_id") != runtime_id or evidence.get("integration_key") != key or evidence.get("fresh_session") is not True or evidence.get("loader_loaded") is not True or evidence.get("managed_files_verified") is not True:
        raise GovernanceError("fresh-session evidence does not prove runtime-to-key loading", "STATE_BROKEN")
    if delivery_mode == "materialized" and evidence.get("loader_failure") is not True:
        raise GovernanceError("materialized delivery requires a recorded Loader failure", "CONTEXT_ANCHOR_UNKNOWN")
    if key != "generic":
        status = command_status(root) or {}
        installed = status.get("installed_integrations", [])
        installed_keys = {item.get("key") if isinstance(item, dict) else item for item in installed}
        if key not in installed_keys:
            raise GovernanceError("fresh-session evidence cannot activate an integration that is not installed", "NATIVE_CANDIDATE_NOT_INSTALLED")
    path = root / PROJECT_PACKAGE / "ADAPTERS.json"
    registry = adapters(root)
    binding = next((item for item in registry.get("bindings", []) if item.get("runtime_id") == runtime_id and item.get("integration_key") == key), None)
    if binding is None:
        raise GovernanceError("no provisional binding matches runtime and integration key", "STATE_BROKEN")
    binding["verification"]["status"] = "active"
    binding["verification"]["method"] = "fresh-session-materialized" if delivery_mode == "materialized" else "fresh-session-loader"
    binding["verification"]["evidence"] = evidence_rel
    binding["verification"]["verified_at"] = iso(utc_now())
    binding["capabilities"] = {"core_workflow": "verified", "extensions": "not-verified", "presets": "not-verified", "events": "not-verified"}
    registry_bytes = canonical_json(registry) + b"\n"
    mutation = file_mutation(root, f"{PROJECT_PACKAGE}/ADAPTERS.json", registry_bytes, "replace")
    mutations = [mutation]
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        manifest.setdefault("content_sha256", {})[f"{PROJECT_PACKAGE}/ADAPTERS.json"] = mutation["expected_new_sha256"]
        mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", canonical_json(manifest) + b"\n", "replace"))
    return mutations


def make_plan(root: Path, operation: str, mutations: list[dict[str, Any]], *, external: list[dict[str, Any]] | None = None, identity: dict[str, Any] | None = None, claimed_key: str | None = None, context_anchor: str | None = None, write_preflight: list[dict[str, Any]] | None = None, anchor_compatibility_evidence: list[dict[str, Any]] | None = None, rehearsal: dict[str, Any] | None = None, documentation_language: str | None = None) -> dict[str, Any]:
    now = utc_now()
    config_path = root / PROJECT_PACKAGE / "PROJECT_CONFIG.json"
    manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
    adapter_path = root / PROJECT_PACKAGE / "ADAPTERS.json"
    overrides_path = root / PROJECT_PACKAGE / "LOCAL_OVERRIDES.md"
    status = command_status(root)
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": uuid.uuid4().hex,
        "operation_type": operation,
        "created_at": iso(now),
        "expires_at": iso(now + PLAN_TTL),
        **git_fingerprint(root),
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "project_config_sha256": sha256_file(config_path) if config_path.is_file() else None,
        "adapters_sha256": sha256_file(adapter_path) if adapter_path.is_file() else None,
        "local_overrides_sha256": sha256_file(overrides_path) if overrides_path.is_file() else None,
        "integration_status_sha256": sha256_bytes(canonical_json(status)) if status is not None else None,
        "specify_version": cli_version(),
        "inputs": [{"path": m["path"], "sha256": m["old_sha256"]} for m in mutations if m["old_sha256"]],
        "input_files": [{"path": m["path"], "sha256": m["old_sha256"]} for m in mutations if m["old_sha256"]],
        "identity": identity or {},
        "current_agent": {"runtime_id": (identity or {}).get("runtime_id", "agent-neutral-bootstrap"), "declaration_source": "user-declared" if identity else "runtime-declared"},
        "claimed_integration_key": claimed_key,
        "required_native_key": claimed_key,
        "native_fallback_prohibited": bool(claimed_key and claimed_key != "generic"),
        "native_target_paths": [],
        "write_preflight": write_preflight or [],
        "on_native_write_failure": "NATIVE_INSTALL_BLOCKED",
        "anchor": context_anchor,
        "context_anchor": context_anchor,
        "anchor_compatibility_evidence": anchor_compatibility_evidence or [],
        "documentation_language": documentation_language,
        "rehearsal": rehearsal,
        "capability_inventory_before": runtime_capability_inventory(root),
        "manager_file_mutations": mutations,
        "external_cli_mutations": external or [],
        "changes_default_integration": False,
        "default_integration_change": False,
        "previous_default_integration": None,
        "requires_network": bool(external),
        "network_required": bool(external),
        "risk_assessment": {
            "ambiguity_open": False, "cross_cutting_component_count": 1, "public_contract_change": False,
            "data_migration": False, "security_impact": False, "compliance_impact": False,
            "irreversible_operation": False, "artifact_conflict": False, "unknown_bug_cause": False,
            "evidence": ["docs/spec-kit/START_HERE.md" if (root / PROJECT_PACKAGE / "START_HERE.md").is_file() else "GLOBAL_POLICY.md"],
        },
        "required_user_authorization": f"Approve exact plan {operation}",
        "risks_and_recovery": ["Revalidate all snapshots before apply", "Restore backups on failure"],
        "recovery_steps": ["Inspect the changed-file inventory", "Restore the plan backup", "Re-run status before retrying"],
        "plan_sha256": None,
    }
    plan["plan_sha256"] = plan_hash(plan)
    return plan


def save_plan(root: Path, plan: dict[str, Any]) -> Path:
    validate_plan_shape(plan)
    directory = root / RUNTIME_DIR / "plans"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{plan['plan_id']}.json"
    path.write_bytes(canonical_json(plan) + b"\n")
    return path


def bootstrap_mutations(root: Path, source: Path, context_anchor: str) -> list[dict[str, Any]]:
    preflight_writable(root, context_anchor)
    mapping = {
        "START_HERE.md": source / "governance/project/START_HERE.md",
        "POLICY.md": source / "governance/project/POLICY.md",
        "REFERENCE.md": source / "governance/project/REFERENCE.md",
        "OPERATING_PROTOCOL.md": source / "governance/project/OPERATING_PROTOCOL.md",
        "AGENT_ONBOARDING.md": source / "governance/project/AGENT_ONBOARDING.md",
        "LOCAL_OVERRIDES.md": source / "governance/project/LOCAL_OVERRIDES.template.md",
        "PROJECT_CONFIG.json": source / "governance/project/PROJECT_CONFIG.default.json",
        "ADAPTERS.json": source / "governance/project/ADAPTERS.template.json",
    }
    mutations = [file_mutation(root, f"{PROJECT_PACKAGE}/{name}", path.read_bytes()) for name, path in mapping.items()]
    manager_bytes = Path(__file__).read_bytes()
    mutations += [file_mutation(root, MANAGER_RELATIVE, manager_bytes)]
    # MANIFEST is generated from the exact bytes planned above.  This makes a
    # freshly bootstrapped project self-describing without requiring a second
    # mutable implementation or a post-apply hand edit.
    source_revision = git_value(source, "rev-parse", "HEAD") or "0" * 40
    reviewed_upstream = (source / "UPSTREAM_BASELINE").read_text(encoding="utf-8").strip() if (source / "UPSTREAM_BASELINE").is_file() else "0" * 40
    if not re.fullmatch(r"[0-9a-f]{40}", reviewed_upstream):
        reviewed_upstream = "0" * 40
    tested_cli = cli_version() or "0.0.0"
    manifest_content = {
        "schema_version": 1,
        "governance_package_version": "1.0.0",
        "policy_version": "1.0.0",
        "reference_version": "2026.08.21",
        "manager_version": "1.0.0",
        "source": {"repository": "https://github.com/jiezhengj/Spec-Kit-Reference", "revision": source_revision, "release": "v1.0.0", "reviewed_upstream_revision": reviewed_upstream},
        "specify_compatibility": {"minimum_version": "0.16.6", "tested_version": tested_cli, "maximum_version_exclusive": None, "approved_install_ref": reviewed_upstream},
        "paths": {
            "start_here": f"{PROJECT_PACKAGE}/START_HERE.md", "policy": f"{PROJECT_PACKAGE}/POLICY.md",
            "reference": f"{PROJECT_PACKAGE}/REFERENCE.md", "operating_protocol": f"{PROJECT_PACKAGE}/OPERATING_PROTOCOL.md",
            "onboarding": f"{PROJECT_PACKAGE}/AGENT_ONBOARDING.md", "local_overrides": f"{PROJECT_PACKAGE}/LOCAL_OVERRIDES.md",
            "project_config": f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json", "adapters": f"{PROJECT_PACKAGE}/ADAPTERS.json", "manager": MANAGER_RELATIVE,
        },
        "content_sha256": {},
        "project_owned_files": [f"{PROJECT_PACKAGE}/LOCAL_OVERRIDES.md", f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json", f"{PROJECT_PACKAGE}/ADAPTERS.json"],
        "portable_anchor": {"path": context_anchor, "marker_start": START_MARKER, "marker_end": END_MARKER},
    }
    for item in mutations:
        manifest_content["content_sha256"][item["path"]] = item["expected_new_sha256"]
    manifest_bytes = canonical_json(manifest_content) + b"\n"
    mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", manifest_bytes))
    mutations += [file_mutation(
        root, context_anchor, marker_loader().encode("utf-8"),
        "append-managed-loader", protected_anchor=True,
    )]
    return mutations


def cmd_doctor(root: Path) -> dict[str, Any]:
    version = cli_version()
    result: dict[str, Any] = {
        "schema_version": 1, "project_root": str(root), "git": git_fingerprint(root),
        "specify_version": version, "specify_present": version is not None, "specify_project": (root / ".specify").is_dir(),
        "governance_package": (root / PROJECT_PACKAGE).is_dir(), "runtime_directory": (root / RUNTIME_DIR).is_dir(),
        "status": "READY" if (root / PROJECT_PACKAGE).is_dir() else "PROJECT_NOT_INITIALIZED",
    }
    package_errors = validate_project_package(root) if (root / PROJECT_PACKAGE).is_dir() else []
    if package_errors:
        result["status"] = "STATE_BROKEN"
        result["package_errors"] = package_errors
    compatibility = cli_compatibility(root)
    result["cli_compatibility"] = compatibility
    if compatibility not in {"READY", "CLI_MISSING"}:
        result["status"] = compatibility
    if version is None:
        result["status"] = "CLI_MISSING"
        result["install_suggestion"] = "uv tool install specify-cli --from git+https://github.com/github/spec-kit.git"
    if (root / PROJECT_PACKAGE / "PROJECT_CONFIG.json").is_file():
        result["project_config"] = project_config(root)
    return result


def resolution(root: Path, runtime_id: str, display_name: str | None, key: str | None) -> dict[str, Any]:
    env_runtime = os.environ.get("SPEC_KIT_CURRENT_AGENT_ID")
    env_key = os.environ.get("SPEC_KIT_CURRENT_INTEGRATION_KEY")
    if runtime_id and env_runtime and runtime_id != env_runtime:
        raise GovernanceError("runtime identity declarations conflict", "IDENTITY_CONFLICT")
    if key and env_key and key != env_key:
        raise GovernanceError("integration key declarations conflict", "IDENTITY_CONFLICT")
    runtime_id = runtime_id or env_runtime or ""
    key = key or env_key
    generic_attestation: dict[str, Any] | None = None
    generic_attestation_rel: str | None = None
    if not runtime_id:
        raise GovernanceError("runtime ID is required", "IDENTITY_UNKNOWN")
    if cli_version() is None:
        status = "CLI_MISSING"
    elif not key:
        status = "KEY_REQUIRED"
    elif key == "generic" and not (root / ".specify").is_dir():
        status = "UNSUPPORTED_INCOMPATIBLE"
    elif not (root / ".specify").is_dir():
        status = "PROJECT_NOT_INITIALIZED"
    else:
        current = command_status(root)
        installed = current.get("installed_integrations", []) if current else []
        keys = {item.get("key") if isinstance(item, dict) else item for item in installed}
        registry = adapters(root)
        active = next((item for item in registry.get("bindings", []) if item.get("runtime_id") == runtime_id and item.get("verification", {}).get("status") == "active"), None)
        if active and active.get("integration_key") == key:
            status = "READY_WITH_LIMITATIONS" if key == "generic" else "EXACT_NATIVE_INSTALLED"
        elif active and active.get("integration_key") != key:
            status = "NATIVE_CANDIDATE_REJECTED"
        elif key == "generic":
            status = "UNSUPPORTED_INCOMPATIBLE"
        else:
            status = "NATIVE_CANDIDATE_INSTALLED_UNVERIFIED" if key in keys else "NATIVE_CANDIDATE_NOT_INSTALLED"
    current = command_status(root) if (root / ".specify").is_dir() and cli_version() is not None else None
    installed = current.get("installed_integrations", []) if current else []
    registry = adapters(root) if (root / PROJECT_PACKAGE / "ADAPTERS.json").is_file() else {"bindings": [], "anchors": []}
    active = next((item for item in registry.get("bindings", []) if item.get("runtime_id") == runtime_id and item.get("verification", {}).get("status") == "active"), None)
    active_anchor = None
    if active:
        anchor_ids = set(active.get("anchor_ids", []))
        anchor = next((item for item in registry.get("anchors", []) if item.get("id") in anchor_ids), None)
        active_anchor = anchor.get("path") if anchor else None
    default_key = current.get("default_integration") if isinstance(current, dict) else None
    if isinstance(default_key, dict):
        default_key = default_key.get("key")
    installed_keys = {item.get("key") if isinstance(item, dict) else item for item in installed}
    response = {
        "schema_version": 1, "status": status, "project_root": str(root),
        "identity": {"runtime_id": runtime_id, "display_name": display_name, "source": "environment" if env_runtime and not display_name else "explicit-input"},
        "integration": {"key": key, "mode": ("explicit-generic-transition" if key == "generic" and status == "READY_WITH_LIMITATIONS" else ("native" if key and key != "generic" and status == "EXACT_NATIVE_INSTALLED" else None)), "installed": key in installed_keys, "default": key == default_key, "multi_install_safe": None},
        "context": {"anchor": active_anchor, "anchor_source": "active-binding" if active_anchor else None},
        "required_action": "provide-exact-key" if status == "KEY_REQUIRED" else ("reuse-active-binding" if status in {"EXACT_NATIVE_INSTALLED", "READY_WITH_LIMITATIONS"} else "review-and-plan"),
        "warnings": [], "next_safe_step": "Run plan-onboard only after reviewing this result",
    }
    if status == "CLI_MISSING":
        response["required_action"] = "install-with-user-approval"
        response["install_suggestion"] = "uv tool install specify-cli --from git+https://github.com/github/spec-kit.git"
    return response


def load_plan(root: Path, path: Path) -> dict[str, Any]:
    path = path.resolve()
    expected_dir = (root / RUNTIME_DIR / "plans").resolve()
    try:
        path.relative_to(expected_dir)
    except ValueError as exc:
        raise GovernanceError("plan is outside the runtime plan directory") from exc
    plan = read_json(path)
    if plan.get("plan_sha256") != plan_hash(plan):
        raise GovernanceError("plan_sha256 mismatch")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise GovernanceError("unsupported plan schema")
    validate_plan_shape(plan)
    return plan


def validate_apply(root: Path, plan: dict[str, Any], approved_id: str, approved_hash: str) -> None:
    if plan.get("plan_id") != approved_id or plan.get("plan_sha256") != approved_hash:
        raise GovernanceError("approval does not match exact plan")
    expires = datetime.fromisoformat(str(plan["expires_at"]).replace("Z", "+00:00"))
    if utc_now() > expires:
        raise GovernanceError("plan expired")
    current = git_fingerprint(root)
    for key in ("project_root_fingerprint", "git_head", "git_status_porcelain_sha256"):
        if plan.get(key) != current.get(key):
            raise GovernanceError(f"plan input changed: {key}")
    snapshot_paths = {
        "manifest_sha256": root / f"{PROJECT_PACKAGE}/MANIFEST.json",
        "project_config_sha256": root / f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json",
        "adapters_sha256": root / f"{PROJECT_PACKAGE}/ADAPTERS.json",
        "local_overrides_sha256": root / f"{PROJECT_PACKAGE}/LOCAL_OVERRIDES.md",
    }
    for field, target in snapshot_paths.items():
        expected = plan.get(field)
        actual = sha256_file(target) if target.is_file() else None
        if expected != actual:
            raise GovernanceError(f"plan input changed: {field}")
    planned_status_hash = plan.get("integration_status_sha256")
    current_status = command_status(root)
    current_status_hash = sha256_bytes(canonical_json(current_status)) if current_status is not None else None
    if planned_status_hash != current_status_hash:
        raise GovernanceError("plan input changed: integration_status_sha256")
    planned_cli_version = plan.get("specify_version")
    if planned_cli_version != cli_version():
        raise GovernanceError("plan input changed: specify_version")
    for item in plan.get("inputs", []):
        target = root / safe_relative(root, item["path"])
        if not target.is_file() or sha256_file(target) != item["sha256"]:
            raise GovernanceError(f"plan input changed: {item['path']}")


def project_inventory(root: Path) -> dict[str, str]:
    """Hash durable files for external CLI scope verification."""
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or RUNTIME_DIR in path.relative_to(root).parts or ".git" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        result[rel] = sha256_file(path)
    return result


def tree_digest(root: Path, relative: str) -> str | None:
    target = root / relative
    if not target.exists():
        return None
    if target.is_file():
        return sha256_file(target)
    entries: list[bytes] = []
    for path in sorted((item for item in target.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        entries.append(rel.encode("utf-8") + b"\0" + sha256_file(path).encode("ascii") + b"\n")
    return sha256_bytes(b"".join(entries))


def runtime_reported_prefixes(status: dict[str, Any] | None) -> set[str]:
    """Extract only path-like values explicitly reported by the installed runtime."""
    prefixes: set[str] = set()
    path_key = re.compile(r"(?:path|file|directory|dir|skill|command|managed)", re.IGNORECASE)

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and path_key.search(key):
            candidate = Path(value)
            if not candidate.is_absolute() and ".." not in candidate.parts and value not in {".", ""}:
                prefixes.add(candidate.as_posix().rstrip("/") + "/")

    visit(status)
    return prefixes


def runtime_capability_inventory(root: Path) -> dict[str, Any]:
    """Return a deterministic, path-relative inventory for upgrade gates.

    The installed CLI remains authoritative for runtime facts.  This function
    records only stable hashes and JSON status, never absolute paths, tokens,
    or environment variables.
    """
    status = command_status(root)
    status_copy = status if isinstance(status, dict) else None
    registry = adapters(root)
    anchor_paths = {
        item.get("path") for item in registry.get("anchors", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    agent_artifacts = {
        rel: digest for rel, digest in project_inventory(root).items()
        if rel in anchor_paths or any(rel.startswith(prefix) for prefix in runtime_reported_prefixes(status_copy))
    }
    return {
        "schema_version": 1,
        "specify_project": (root / ".specify").is_dir(),
        "integration_status": status_copy,
        "integration_status_sha256": sha256_bytes(canonical_json(status_copy)) if status_copy is not None else None,
        "paths": {
            ".specify": tree_digest(root, ".specify"),
            "constitution": tree_digest(root, ".specify/memory/constitution.md"),
            "specs": tree_digest(root, "specs"),
            "agent_skills_or_commands": sha256_bytes(canonical_json(agent_artifacts)) if agent_artifacts else None,
            "project_governance": sha256_bytes(canonical_json({rel: digest for rel, digest in project_inventory(root).items() if rel.startswith("docs/spec-kit/") or rel == MANAGER_RELATIVE})) or None,
        },
        "default_integration": (status_copy or {}).get("default_integration") if status_copy else None,
        "installed_integrations": (status_copy or {}).get("installed_integrations", []) if status_copy else [],
    }


def init_rehearsal(root: Path, key: str, force: bool) -> dict[str, Any]:
    """Run the exact init argv in an isolated temporary directory.

    Rehearsal is plan-generation evidence only.  It never writes the real
    project and does not infer Agent identity from generated directories.
    """
    if key == "generic":
        raise GovernanceError("plan-init requires a concrete integration key", "UNSUPPORTED_INCOMPATIBLE")
    executable = shutil.which("specify")
    if not executable:
        raise GovernanceError("specify CLI is missing", "CLI_MISSING")
    argv = ["specify", "init", "--here"]
    if force:
        argv.append("--force")
    argv.extend(["--non-interactive", "--integration", key])
    with tempfile.TemporaryDirectory(prefix="spec-kit-rehearsal-") as directory:
        rehearsal_root = Path(directory)
        before = project_inventory(rehearsal_root)
        result = subprocess.run(argv, cwd=rehearsal_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        after = project_inventory(rehearsal_root)
        if result.returncode != 0:
            raise GovernanceError("Spec Kit init rehearsal failed; inspect CLI output before retrying", "NATIVE_INSTALL_BLOCKED")
        changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        if not changed:
            raise GovernanceError("Spec Kit init rehearsal produced no observable project artifacts", "STATE_BROKEN")
        return {
            "argv": argv,
            "cli_version": cli_version(),
            "force": force,
            "changed_files": changed,
            "changed_sha256": {path: after[path] for path in changed if path in after},
            "allowed_path_prefixes": sorted({path.split("/", 1)[0] + "/" for path in changed}),
            "stdout_sha256": sha256_bytes(result.stdout.encode("utf-8")),
            "stderr_sha256": sha256_bytes(result.stderr.encode("utf-8")),
        }


def has_durable_project_files(root: Path) -> bool:
    return bool(project_inventory(root))


def run_external_mutations(root: Path, plan: dict[str, Any]) -> list[str]:
    def rollback_external(item: dict[str, Any]) -> tuple[int | None, list[str]]:
        rollback_argv = item.get("rollback_argv")
        if not isinstance(rollback_argv, list) or not rollback_argv:
            return None, []
        if rollback_argv[0] != "specify" or any(not isinstance(value, str) or not value for value in rollback_argv):
            return None, []
        before_rollback = project_inventory(root)
        result = subprocess.run(rollback_argv, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        after_rollback = project_inventory(root)
        return result.returncode, sorted(path for path in set(before_rollback) | set(after_rollback) if before_rollback.get(path) != after_rollback.get(path))

    changed: list[str] = []
    for item in plan.get("external_cli_mutations", []):
        argv = item.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(value, str) or not value for value in argv):
            raise GovernanceError("external mutation argv must be a non-empty string list", "STATE_BROKEN")
        if argv[0] != "specify":
            raise GovernanceError("external mutation executable is not allowlisted", "UNSUPPORTED_INCOMPATIBLE")
        if "--force" in argv and plan.get("operation_type") != "plan-init":
            raise GovernanceError("--force is forbidden for this operation", "UNSUPPORTED_INCOMPATIBLE")
        before = project_inventory(root)
        for snapshot in item.get("pre_execution_snapshot", []):
            rel = snapshot.get("path")
            if not isinstance(rel, str) or not safe_relative(root, rel).as_posix() == rel:
                raise GovernanceError("external pre-execution snapshot contains an unsafe path", "STATE_BROKEN")
            target = root / rel
            if not target.is_file() or sha256_file(target) != snapshot.get("sha256"):
                raise GovernanceError(f"external mutation input changed: {rel}", "RECOVERY_REQUIRED")
        result = subprocess.run(argv, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        after = project_inventory(root)
        delta = sorted(set(before) | set(after))
        changed_now = [path for path in delta if before.get(path) != after.get(path)]
        changed.extend(changed_now)
        if result.returncode != 0:
            rollback_argv = item.get("rollback_argv")
            rollback_returncode, rollback_changed = rollback_external(item)
            report = root / RUNTIME_DIR / "plans" / f"{plan['plan_id']}.external-failure.json"
            report.parent.mkdir(parents=True, exist_ok=True)
            restored = project_inventory(root) == before
            report.write_bytes(canonical_json({"argv": argv, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "changed": changed_now, "rollback_argv": rollback_argv, "rollback_returncode": rollback_returncode, "rollback_changed": rollback_changed, "restored": restored}) + b"\n")
            status = "NATIVE_INSTALL_BLOCKED" if restored and plan.get("required_native_key") and plan.get("required_native_key") != "generic" else "RECOVERY_REQUIRED"
            raise GovernanceError(f"external CLI failed; recovery review required: {' '.join(argv)}", status)
        allowed = item.get("allowed_path_prefixes", [])
        def within_allowed(path: str, prefix: str) -> bool:
            normalized = prefix.rstrip("/")
            return path == normalized or path.startswith(normalized + "/")

        unexpected = [path for path in changed_now if allowed and not any(within_allowed(path, prefix) for prefix in allowed)]
        if unexpected:
            rollback_argv = item.get("rollback_argv")
            rollback_returncode, rollback_changed = rollback_external(item)
            restored = project_inventory(root) == before
            report = root / RUNTIME_DIR / "plans" / f"{plan['plan_id']}.external-scope-failure.json"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_bytes(canonical_json({"argv": argv, "unexpected": unexpected, "changed": changed_now, "rollback_argv": rollback_argv, "rollback_returncode": rollback_returncode, "rollback_changed": rollback_changed, "restored": restored}) + b"\n")
            raise GovernanceError(f"external CLI changed files outside approved scope: {unexpected}", "STATE_BROKEN" if restored else "RECOVERY_REQUIRED")
        inventory_path = root / RUNTIME_DIR / "plans" / f"{plan['plan_id']}.changed.json"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_bytes(canonical_json({"argv": argv, "changed": {path: after.get(path) for path in changed_now}}) + b"\n")
    return changed


def apply_manager_mutations(root: Path, plan: dict[str, Any]) -> list[str]:
    backup_dir = root / RUNTIME_DIR / "backups" / plan["plan_id"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    originals: dict[str, bytes | None] = {}
    try:
        for item in plan.get("manager_file_mutations", []):
            rel = item["path"]
            safe_relative(root, rel)
            target = root / rel
            context_anchor = plan.get("context_anchor")
            if item.get("protected_anchor") is True and rel != context_anchor:
                raise GovernanceError("protected anchor mutation does not match the declared context anchor", "STATE_BROKEN")
            if rel == context_anchor and (item.get("action") != "append-managed-loader" or item.get("protected_anchor") is not True):
                raise GovernanceError("the declared project rules anchor accepts only append-managed-loader", "PROJECT_RULES_PROTECTED")
            if target.is_symlink():
                raise GovernanceError(f"refusing to mutate symlink: {rel}", "STATE_BROKEN")
            old = target.read_bytes() if target.is_file() else None
            originals[rel] = old
            if old is not None:
                backup = backup_dir / (rel.replace("/", "__") + ".bak")
                backup.write_bytes(old)
            content = base64.b64decode(item["content_b64"])
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.get("action") == "append-managed-loader" and target.exists():
                content = append_loader(target.read_bytes(), content)
            temp = target.with_name(f".{target.name}.{plan['plan_id']}.tmp")
            temp.write_bytes(content)
            with temp.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temp, target)
            os.chmod(target, item.get("mode", 0o644))
            try:
                directory_fd = os.open(str(target.parent), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
            changed.append(rel)
    except GovernanceError:
        for rel, old in originals.items():
            target = root / rel
            try:
                if old is None:
                    if target.exists() and target.is_file():
                        target.unlink()
                else:
                    target.write_bytes(old)
            except OSError as recovery_error:
                raise GovernanceError(f"manager mutation failed and recovery failed: {rel}", "RECOVERY_REQUIRED") from recovery_error
        raise
    except Exception as exc:
        for rel, old in originals.items():
            target = root / rel
            try:
                if old is None:
                    if target.exists() and target.is_file():
                        target.unlink()
                else:
                    target.write_bytes(old)
            except OSError:
                raise GovernanceError(f"manager mutation failed and recovery failed: {rel}", "RECOVERY_REQUIRED") from exc
        raise GovernanceError(f"manager mutation failed and was restored: {exc}", "RECOVERY_REQUIRED") from exc
    return changed


def cmd_apply(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    plan = load_plan(root, Path(args.plan))
    validate_apply(root, plan, args.approve_plan_id, args.approve_plan_sha256)
    # External Spec Kit mutations run before the project-owned configuration
    # commit.  If the CLI fails, no governance config is advanced; if the
    # subsequent local commit fails, the result is explicitly recovery-needed.
    changed = run_external_mutations(root, plan)
    try:
        changed.extend(apply_manager_mutations(root, plan))
    except Exception as exc:
        raise GovernanceError(f"external mutation succeeded but governance commit failed: {exc}", "RECOVERY_REQUIRED") from exc
    after_path = root / RUNTIME_DIR / "plans" / f"{plan['plan_id']}.capability-after.json"
    after_path.parent.mkdir(parents=True, exist_ok=True)
    after_path.write_bytes(canonical_json(runtime_capability_inventory(root)) + b"\n")
    return {"status": "applied", "plan_id": plan["plan_id"], "changed": changed}


def create_plan_command(root: Path, operation: str, args: argparse.Namespace) -> dict[str, Any]:
    if operation != "plan-governance-bootstrap" and operation not in {"plan-upgrade", "plan-rollback", "plan-activate-binding"}:
        compatibility = cli_compatibility(root)
        if compatibility != "READY":
            raise GovernanceError(f"Spec Kit CLI is not eligible for mutation: {compatibility}", compatibility)
    env_runtime = os.environ.get("SPEC_KIT_CURRENT_AGENT_ID")
    if getattr(args, "runtime_id", None) and env_runtime and args.runtime_id != env_runtime:
        raise GovernanceError("runtime identity declarations conflict", "IDENTITY_CONFLICT")
    runtime_id = getattr(args, "runtime_id", None) or env_runtime
    identity = {"runtime_id": runtime_id, "display_name": getattr(args, "display_name", None), "source": "environment" if env_runtime and not getattr(args, "runtime_id", None) else "explicit-input"} if runtime_id else {}
    key = getattr(args, "integration_key", None)
    env_key = os.environ.get("SPEC_KIT_CURRENT_INTEGRATION_KEY")
    if key and env_key and key != env_key:
        raise GovernanceError("integration key declarations conflict", "IDENTITY_CONFLICT")
    key = key or env_key
    requested_anchor = getattr(args, "context_anchor", None)
    env_anchor = os.environ.get("SPEC_KIT_CONTEXT_ANCHOR")
    if requested_anchor and env_anchor and requested_anchor != env_anchor:
        raise GovernanceError("context anchor declarations conflict", "IDENTITY_CONFLICT")
    context_anchor = requested_anchor or env_anchor
    if context_anchor:
        context_anchor = safe_relative(root, context_anchor).as_posix()
    delivery_mode = getattr(args, "delivery_mode", "loader")
    anchor_evidence: list[dict[str, Any]] = []
    if operation == "plan-onboard":
        if not runtime_id:
            raise GovernanceError("runtime ID is required for onboarding", "IDENTITY_UNKNOWN")
        if not context_anchor:
            raise GovernanceError("context anchor is required for onboarding", "CONTEXT_ANCHOR_UNKNOWN")
        if not (root / ".specify").is_dir():
            raise GovernanceError("onboarding requires an existing .specify project; run plan-init first", "PROJECT_NOT_INITIALIZED")
        if not (root / PROJECT_PACKAGE / "PROJECT_CONFIG.json").is_file():
            raise GovernanceError("project governance package is missing; run plan-governance-bootstrap first", "PROJECT_NOT_INITIALIZED")
        if not getattr(args, "anchor_evidence", None):
            raise GovernanceError("onboarding requires anchor compatibility evidence", "CONTEXT_ANCHOR_UNKNOWN")
        anchor_evidence_path = root / safe_relative(root, args.anchor_evidence)
        if not anchor_evidence_path.is_file():
            raise GovernanceError("anchor compatibility evidence is missing", "CONTEXT_ANCHOR_UNKNOWN")
        anchor_record = read_json(anchor_evidence_path)
        evidence_hash = sha256_file(anchor_evidence_path)
        if anchor_record.get("anchor_path") not in {None, context_anchor}:
            raise GovernanceError("anchor compatibility evidence targets a different path", "CONTEXT_ANCHOR_UNKNOWN")
        if anchor_record.get("format") not in {None, "markdown", "text"}:
            raise GovernanceError("anchor format is unsupported", "ANCHOR_FORMAT_UNSUPPORTED")
        anchor_evidence = [{"source": args.anchor_evidence, "content_sha256": evidence_hash, "review_conclusion": str(anchor_record.get("review_conclusion", "reviewed"))}]
        if delivery_mode not in {"loader", "materialized"}:
            raise GovernanceError("unsupported delivery mode", "UNSUPPORTED_INCOMPATIBLE")
        if delivery_mode == "materialized":
            failure_rel = getattr(args, "loader_failure_evidence", None)
            if not failure_rel:
                raise GovernanceError("materialized delivery requires Loader failure evidence", "CONTEXT_ANCHOR_UNKNOWN")
            failure_path = root / safe_relative(root, failure_rel)
            if not failure_path.is_file():
                raise GovernanceError("Loader failure evidence is missing", "CONTEXT_ANCHOR_UNKNOWN")
            failure_record = read_json(failure_path)
            if failure_record.get("runtime_id") != runtime_id or failure_record.get("integration_key") != key or failure_record.get("fresh_session") is not True or failure_record.get("loader_failure") is not True:
                raise GovernanceError("Loader failure evidence does not match runtime and key", "CONTEXT_ANCHOR_UNKNOWN")
        elif getattr(args, "loader_failure_evidence", None):
            raise GovernanceError("Loader failure evidence is only valid for materialized delivery", "UNSUPPORTED_INCOMPATIBLE")
    if operation == "plan-activate-binding":
        if not runtime_id:
            raise GovernanceError("runtime ID is required to activate a binding", "IDENTITY_UNKNOWN")
        if not key:
            raise GovernanceError("integration key is required to activate a binding", "KEY_REQUIRED")
        if not getattr(args, "verification_evidence", None):
            raise GovernanceError("fresh-session verification evidence is required", "CONTEXT_ANCHOR_UNKNOWN")
    if key == "generic" and operation == "plan-onboard":
        # Generic is never a permission fallback.  It is an explicit,
        # separately attested transition and therefore cannot be planned from
        # the ordinary native onboarding path.
        config = project_config(root) or {}
        if config.get("generic", {}).get("policy") != "explicit-approval-required":
            raise GovernanceError("generic transition is disabled by project configuration", "UNSUPPORTED_INCOMPATIBLE")
        attestation = getattr(args, "attestation", None)
        if not attestation:
            raise GovernanceError("generic transition requires an explicit native-absence attestation", "UNSUPPORTED_INCOMPATIBLE")
        evidence = root / safe_relative(root, attestation)
        if not evidence.is_file():
            raise GovernanceError("native-absence attestation does not exist", "UNSUPPORTED_INCOMPATIBLE")
        record = read_json(evidence)
        if record.get("runtime_id") != runtime_id or record.get("conclusion") != "no-native-integration-found-for-runtime" or record.get("reviewed_by_current_operator") is not True:
            raise GovernanceError("native-absence attestation does not match runtime identity", "UNSUPPORTED_INCOMPATIBLE")
        observed_version = cli_version()
        if not observed_version or record.get("specify_version") != observed_version:
            raise GovernanceError("native-absence attestation does not match the installed CLI version", "UNSUPPORTED_INCOMPATIBLE")
        catalog_rel = record.get("catalog_evidence")
        catalog_hash = record.get("catalog_evidence_sha256")
        if not isinstance(catalog_rel, str) or not isinstance(catalog_hash, str):
            raise GovernanceError("generic transition requires immutable catalog evidence", "UNSUPPORTED_INCOMPATIBLE")
        catalog_path = root / safe_relative(root, catalog_rel)
        if not catalog_path.is_file() or sha256_file(catalog_path) != catalog_hash:
            raise GovernanceError("generic catalog evidence hash is invalid", "UNSUPPORTED_INCOMPATIBLE")
        current = command_status(root) or {}
        installed = current.get("installed_integrations", [])
        if installed:
            raise GovernanceError("generic transition requires an empty installed integration set", "INTEGRATION_CONFLICT")
        generic_attestation = record
        generic_attestation_rel = attestation
        if operation != "plan-onboard" or not getattr(args, "commands_dir", None):
            raise GovernanceError("generic transition requires plan-onboard and an explicit commands directory", "UNSUPPORTED_INCOMPATIBLE")
        safe_relative(root, args.commands_dir)
    if operation == "plan-governance-bootstrap":
        if not context_anchor:
            raise GovernanceError(
                "bootstrap requires the current Agent runtime or user to provide the project context anchor",
                "CONTEXT_ANCHOR_UNKNOWN",
            )
        mutations = bootstrap_mutations(root, source_root(getattr(args, "source", None)), context_anchor)
    else:
        mutations = []
    rehearsal = None
    if operation == "plan-init":
        if not key:
            raise GovernanceError("integration key is required", "KEY_REQUIRED")
        if not runtime_id:
            raise GovernanceError("ask the user for the current Agent runtime identity before initialization", "IDENTITY_UNKNOWN")
        if not context_anchor:
            raise GovernanceError("the current Agent runtime must provide its project context anchor", "CONTEXT_ANCHOR_UNKNOWN")
        documentation_language = getattr(args, "documentation_language", None)
        if not documentation_language:
            raise GovernanceError(
                "ask the user which language future project documentation should use, then pass --documentation-language",
                "DOCUMENTATION_LANGUAGE_REQUIRED",
            )
        if not valid_language_tag(documentation_language):
            raise GovernanceError("documentation language must be a valid BCP 47 tag", "DOCUMENTATION_LANGUAGE_INVALID")
        config_path = root / PROJECT_PACKAGE / "PROJECT_CONFIG.json"
        manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
        if not config_path.is_file() or not manifest_path.is_file():
            raise GovernanceError("plan-init requires the project governance bootstrap package", "PROJECT_NOT_INITIALIZED")
        manifest_anchor = read_json(manifest_path).get("portable_anchor", {}).get("path")
        if manifest_anchor != context_anchor:
            raise GovernanceError("plan-init context anchor does not match the bootstrapped runtime anchor", "CONTEXT_ANCHOR_UNKNOWN")
        preflight_writable(root, context_anchor)
        rehearsal = init_rehearsal(root, key, bool(args.force))
    if operation in {"plan-upgrade", "plan-rollback"} and not key:
        if not args.source:
            raise GovernanceError("an explicit staged governance source is required", "CENTRAL_SOURCE_UNVERIFIED")
        mutations.extend(governance_update_mutations(root, source_root(args.source)))
    if operation == "plan-activate-binding":
        mutations.extend(activate_binding_mutations(root, runtime_id, key, args.verification_evidence, args.delivery_mode))
    if operation == "plan-onboard" and key:
        evidence_rel = f"{PROJECT_PACKAGE}/evidence/onboard-{uuid.uuid4().hex}.json"
        onboarding, preflight, _anchor_id = onboarding_mutations(
            root, runtime_id, args.display_name or runtime_id, key, context_anchor, evidence_rel,
            integration_mode="explicit-generic-transition" if key == "generic" else "native",
            attestation_hash=sha256_file(root / safe_relative(root, args.attestation)) if key == "generic" and args.attestation else None,
            attestation_rel=generic_attestation_rel,
            commands_dir=args.commands_dir if key == "generic" else None,
            delivery_mode=delivery_mode,
        )
        mutations.extend(onboarding)
    if operation == "plan-init" and key and key != "generic":
        if has_durable_project_files(root) and not args.force:
            raise GovernanceError("non-empty brownfield init requires the dedicated --force rehearsal plan", "NATIVE_INSTALL_BLOCKED")
        if args.force and not has_durable_project_files(root):
            raise GovernanceError("--force is reserved for non-empty brownfield init", "UNSUPPORTED_INCOMPATIBLE")
        config_path = root / PROJECT_PACKAGE / "PROJECT_CONFIG.json"
        if config_path.is_file():
            config = project_config(root) or {}
            config.setdefault("default_integration", {})["key"] = key
            config["documentation"] = {
                "language_tag": documentation_language,
                "selection_source": "explicit-user-selection",
                "scope": "new-and-substantively-rewritten-project-documentation",
            }
            config_bytes = canonical_json(config) + b"\n"
            config_mutation = file_mutation(root, f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json", config_bytes, "replace")
            mutations.append(config_mutation)
            manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
            if manifest_path.is_file():
                manifest = read_json(manifest_path)
                manifest.setdefault("content_sha256", {})[f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json"] = config_mutation["expected_new_sha256"]
                mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", canonical_json(manifest) + b"\n", "replace"))
            mutations.append(file_mutation(
                root, context_anchor, marker_loader(documentation_language).encode("utf-8"),
                "append-managed-loader", protected_anchor=True,
            ))
    if operation in {"plan-onboard", "plan-init", "plan-extension-install", "plan-default-change", "plan-upgrade", "plan-rollback"} and operation != "plan-governance-bootstrap":
        if operation == "plan-onboard" and not key:
            raise GovernanceError("integration key is required", "KEY_REQUIRED")
        argv: list[str] = []
        if operation == "plan-init":
            if not key:
                raise GovernanceError("integration key is required", "KEY_REQUIRED")
            argv = ["specify", "init", "--here", "--non-interactive", "--integration", key]
            if args.force:
                argv.insert(3, "--force")
        elif operation == "plan-onboard":
            argv = ["specify", "integration", "install", key] if key else []
            if key == "generic":
                argv.append(f"--integration-options=--commands-dir {args.commands_dir}")
        elif operation == "plan-extension-install":
            argv = ["specify", "extension", "add", args.extension_directory]
        elif operation == "plan-default-change":
            if not (root / ".specify").is_dir():
                raise GovernanceError("default change requires an existing .specify project", "PROJECT_NOT_INITIALIZED")
            config = project_config(root) or {}
            if config.get("default_integration", {}).get("allow_change") is not True:
                raise GovernanceError("default change is not enabled", "DEFAULT_CHANGE_FORBIDDEN")
            argv = ["specify", "integration", "use", key]
            if not key:
                raise GovernanceError("default change requires an exact integration key", "KEY_REQUIRED")
            config["default_integration"]["key"] = key
            config["default_integration"]["allow_change"] = False
            config_mutation = file_mutation(root, f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json", canonical_json(config) + b"\n", "replace")
            mutations.append(config_mutation)
            manifest_path = root / PROJECT_PACKAGE / "MANIFEST.json"
            if manifest_path.is_file():
                manifest = read_json(manifest_path)
                manifest.setdefault("content_sha256", {})[f"{PROJECT_PACKAGE}/PROJECT_CONFIG.json"] = config_mutation["expected_new_sha256"]
                mutations.append(file_mutation(root, f"{PROJECT_PACKAGE}/MANIFEST.json", canonical_json(manifest) + b"\n", "replace"))
        elif operation == "plan-upgrade":
            argv = ["specify", "integration", "upgrade", key] if key else []
        elif operation == "plan-rollback":
            argv = []
        rollback_argv: list[str] = []
        if operation == "plan-default-change":
            current = command_status(root) or {}
            previous = current.get("default_integration") or current.get("default")
            if isinstance(previous, dict):
                previous = previous.get("key")
            if isinstance(previous, str) and previous:
                rollback_argv = ["specify", "integration", "use", previous]
        allowed_prefixes = [".specify/"]
        for prefix in getattr(args, "allowed_path_prefix", []) or []:
            allowed_prefixes.append(safe_relative(root, prefix).as_posix().rstrip("/") + "/")
        if operation == "plan-init" and rehearsal:
            allowed_prefixes = list(rehearsal.get("allowed_path_prefixes", allowed_prefixes))
        if operation == "plan-onboard" and key == "generic":
            allowed_prefixes.append(args.commands_dir.rstrip("/") + "/")
        external = [] if not argv else [{"argv": argv, "working_directory": ".", "allowed_path_prefixes": allowed_prefixes, "rollback_argv": rollback_argv, "pre_apply_snapshot": [], "postconditions": [], "changed_file_inventory": f"{RUNTIME_DIR}/plans/<plan-id>.changed.json"}]
    else:
        external = []
    if external:
        inventory = project_inventory(root)
        for item in external:
            prefixes = item.get("allowed_path_prefixes", [])
            snapshot = [
                {"path": rel, "sha256": digest}
                for rel, digest in sorted(inventory.items())
                if any(rel == prefix.rstrip("/") or rel.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)
            ]
            item["cli_version"] = cli_version()
            item["pre_execution_snapshot"] = snapshot
            item["expected_status_postconditions"] = ["integration status remains JSON-readable when .specify exists"]
            item["expected_managed_file_postconditions"] = []
            item["failure_recovery_protocol"] = "Preserve runtime evidence; run rollback_argv when supplied; return RECOVERY_REQUIRED if inventory is not restored."
            item["changed_file_inventory_path"] = f"{RUNTIME_DIR}/plans/<plan-id>.changed.json"
    plan = make_plan(
        root, operation, mutations, external=external, identity=identity, claimed_key=key,
        context_anchor=context_anchor,
        write_preflight=[{"path": context_anchor, "writable": True, "evidence": "preflight_writable"}] if context_anchor else [],
        anchor_compatibility_evidence=anchor_evidence,
        rehearsal=rehearsal,
        documentation_language=getattr(args, "documentation_language", None) if operation == "plan-init" else None,
    )
    path = save_plan(root, plan)
    return {"status": "plan-created", "plan_id": plan["plan_id"], "plan_sha256": plan["plan_sha256"], "path": str(path), "operation_type": operation}


def dispatch(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    command = args.command
    if command == "doctor":
        return cmd_doctor(root)
    if command == "resolve-agent":
        return resolution(root, args.runtime_id, args.display_name, args.integration_key)
    if command == "apply-plan":
        return cmd_apply(root, args)
    if command in {"plan-governance-bootstrap", "plan-init", "plan-onboard", "plan-extension-install", "plan-default-change", "plan-upgrade", "plan-rollback", "plan-activate-binding"}:
        return create_plan_command(root, command, args)
    if command in {"render", "verify"}:
        package = root / PROJECT_PACKAGE
        missing = [path for path in governance_files(root) if not (root / path).is_file()]
        mismatched: list[str] = []
        package_errors = validate_project_package(root) if not missing else []
        manifest_path = package / "MANIFEST.json"
        if not missing and manifest_path.is_file():
            manifest = read_json(manifest_path)
            for rel, expected in manifest.get("content_sha256", {}).items():
                target = root / safe_relative(root, rel)
                if not target.is_file() or sha256_file(target) != expected:
                    mismatched.append(rel)
        status = "READY" if not missing and not mismatched and not package_errors else "STATE_BROKEN"
        return {"status": status, "missing": missing, "mismatched": mismatched, "package_errors": package_errors, "project_root": str(root)}
    if command == "check-update":
        if not args.source or not Path(args.source).is_absolute():
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "explicit absolute --source is required"}
        source_root_path = Path(args.source).resolve()
        if not (source_root_path / ".git").exists():
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "source is not a Git checkout"}
        source_head = git_value(source_root_path, "rev-parse", "HEAD")
        index = source_root_path / "governance/release/latest.json"
        if not index.is_file():
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "release index missing"}
        release = read_json(index)
        provenance = release.get("source", {})
        if not re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("revision", ""))) or source_head != provenance.get("revision"):
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "source HEAD does not match release provenance"}
        source_status = git_value(source_root_path, "status", "--porcelain=v1", "--untracked-files=all")
        if source_status:
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "source worktree is not clean"}
        if sha256_bytes(source_status.encode("utf-8")) != provenance.get("worktree_status_sha256") or provenance.get("worktree_clean") is not True:
            return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": "source worktree provenance mismatch"}
        for field in ("portable_artifact", "extension_artifact"):
            artifact = release.get(field, {})
            path = index.parent / artifact.get("path", "")
            if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
                return {"status": "CENTRAL_SOURCE_UNVERIFIED", "reason": f"{field} checksum mismatch"}
        return {"status": "candidate-available", "index": str(index), "release": release}
    raise GovernanceError(f"unknown command: {command}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", default=None)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    resolve = sub.add_parser("resolve-agent"); resolve.add_argument("--runtime-id", required=True); resolve.add_argument("--display-name"); resolve.add_argument("--integration-key"); resolve.add_argument("--json", action="store_true")
    for name in ("plan-governance-bootstrap", "plan-init", "plan-onboard", "plan-extension-install", "plan-default-change", "plan-upgrade", "plan-rollback", "plan-activate-binding"):
        item = sub.add_parser(name)
        item.add_argument("--runtime-id")
        item.add_argument("--display-name")
        item.add_argument("--integration-key")
        item.add_argument("--source")
        item.add_argument("--force", action="store_true")
        item.add_argument("--extension-directory", default="__STAGED_EXTENSION_DIRECTORY__")
        item.add_argument("--version", default="VERSION_REQUIRED")
        item.add_argument("--attestation")
        item.add_argument("--commands-dir")
        item.add_argument("--allowed-path-prefix", action="append", default=[])
        item.add_argument("--context-anchor")
        item.add_argument("--documentation-language")
        item.add_argument("--anchor-evidence")
        item.add_argument("--loader-failure-evidence")
        item.add_argument("--verification-evidence")
        item.add_argument("--delivery-mode", choices=["loader", "materialized"], default="loader")
    apply = sub.add_parser("apply-plan"); apply.add_argument("--plan", required=True); apply.add_argument("--approve-plan-id", required=True); apply.add_argument("--approve-plan-sha256", required=True)
    sub.add_parser("render"); sub.add_parser("verify")
    update = sub.add_parser("check-update"); update.add_argument("--source")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = project_root_from(Path(args.project_root) if args.project_root else None)
    try:
        result = dispatch(root, args)
    except GovernanceError as exc:
        result = {"status": exc.status or "ERROR", "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
