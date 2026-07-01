from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reports import CommandReport, Finding


CONTEXT_RELATIVE_PATH = ".lingotrace/vault-context.json"
SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_TARGET_LANGUAGES = ("ja", "en")
SUPPORTED_EXPLANATION_LANGUAGE = "zh"


@dataclass(frozen=True)
class VaultContext:
    vault_schema_version: int
    target_language: str
    explanation_language: str
    language_pack: str
    language_pack_version: str
    enabled_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ContextLoadResult:
    context: VaultContext | None
    findings: list[Finding]
    report: CommandReport


def load_vault_context(vault_root: str | Path) -> ContextLoadResult:
    root = Path(vault_root)
    context_path = root / CONTEXT_RELATIVE_PATH
    read_files = [CONTEXT_RELATIVE_PATH]
    findings: list[Finding] = []

    if not context_path.exists():
        findings.append(
            Finding(
                code="context_missing",
                message="Vault context is required before write-capable workflows.",
                path=CONTEXT_RELATIVE_PATH,
            )
        )
        return _result(None, findings, read_files)

    try:
        payload = json.loads(context_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                code="invalid_context_json",
                message=f"Vault context JSON is invalid: {exc.msg}.",
                path=CONTEXT_RELATIVE_PATH,
            )
        )
        return _result(None, findings, read_files)

    if not isinstance(payload, dict):
        findings.append(Finding(code="invalid_context_shape", message="Vault context must be a JSON object."))
        return _result(None, findings, read_files)

    context = _parse_context(payload, findings)
    if findings:
        return _result(None, findings, read_files)
    return _result(context, findings, read_files)


def _parse_context(payload: dict[str, Any], findings: list[Finding]) -> VaultContext | None:
    schema_version = payload.get("vault_schema_version")
    target_language = payload.get("target_language")
    explanation_language = payload.get("explanation_language")
    language_pack = payload.get("language_pack")
    language_pack_version = payload.get("language_pack_version")
    enabled_capabilities = payload.get("enabled_capabilities")

    if schema_version != SUPPORTED_SCHEMA_VERSION:
        findings.append(Finding(code="unsupported_vault_schema", message="Unsupported Vault schema version."))
    if target_language not in SUPPORTED_TARGET_LANGUAGES:
        findings.append(Finding(code="unsupported_target_language", message="Unsupported target language."))
    if explanation_language != SUPPORTED_EXPLANATION_LANGUAGE:
        findings.append(Finding(code="unsupported_explanation_language", message="Unsupported explanation language."))
    if not isinstance(language_pack, str) or not language_pack:
        findings.append(Finding(code="invalid_language_pack", message="Language pack must be a non-empty string."))
    if not isinstance(language_pack_version, str) or not language_pack_version:
        findings.append(
            Finding(code="invalid_language_pack_version", message="Language pack version must be a non-empty string.")
        )
    if not isinstance(enabled_capabilities, list) or not all(isinstance(item, str) for item in enabled_capabilities):
        findings.append(
            Finding(code="invalid_enabled_capabilities", message="Enabled capabilities must be a list of strings.")
        )
        return None

    seen: set[str] = set()
    for capability in enabled_capabilities:
        if capability in seen:
            findings.append(
                Finding(code="duplicate_enabled_capability", message=f"Duplicate enabled capability: {capability}.")
            )
            break
        seen.add(capability)

    if findings:
        return None

    return VaultContext(
        vault_schema_version=int(schema_version),
        target_language=str(target_language),
        explanation_language=str(explanation_language),
        language_pack=str(language_pack),
        language_pack_version=str(language_pack_version),
        enabled_capabilities=tuple(enabled_capabilities),
    )


def _result(context: VaultContext | None, findings: list[Finding], read_files: list[str]) -> ContextLoadResult:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return ContextLoadResult(
        context=context,
        findings=findings,
        report=CommandReport(
            command="validate-vault",
            mode="check",
            exit_code=1 if errors else 0,
            errors=errors,
            warnings=warnings,
            read_files=read_files,
        ),
    )
