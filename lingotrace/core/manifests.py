from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reports import CommandReport, Finding


VALID_MATURITY_VALUES = {"stable", "experimental", "deprecated"}


@dataclass(frozen=True)
class CapabilityDeclaration:
    id: str
    maturity: str
    depends_on: tuple[str, ...]
    read_path_roles: tuple[str, ...]
    write_path_roles: tuple[str, ...]
    external_tools: tuple[str, ...]
    behavior_evidence: tuple[str, ...]
    conformance_tests: tuple[str, ...]
    manual_review_cases: tuple[str, ...]


@dataclass(frozen=True)
class UnsupportedCapability:
    id: str
    failure_reason: str
    failure_policy: str
    fallback: str


@dataclass(frozen=True)
class LanguagePackManifest:
    language_pack_id: str
    language_pack_version: str
    target_language: str
    capabilities: dict[str, CapabilityDeclaration]
    unsupported_capabilities: dict[str, UnsupportedCapability]
    default_path_roles: dict[str, str]


@dataclass(frozen=True)
class ManifestLoadResult:
    manifest: LanguagePackManifest | None
    findings: list[Finding]
    report: CommandReport


def load_language_pack_manifest(path: str | Path) -> ManifestLoadResult:
    manifest_path = Path(path)
    read_files = [manifest_path.as_posix()]
    findings: list[Finding] = []

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append(Finding(code="manifest_missing", message="Language pack manifest is missing."))
        return _result(None, findings, read_files)
    except json.JSONDecodeError as exc:
        findings.append(Finding(code="invalid_manifest_json", message=f"Manifest JSON is invalid: {exc.msg}."))
        return _result(None, findings, read_files)

    if not isinstance(payload, dict):
        findings.append(Finding(code="invalid_manifest_shape", message="Language pack manifest must be a JSON object."))
        return _result(None, findings, read_files)

    manifest = _parse_manifest(payload, findings)
    if findings:
        return _result(None, findings, read_files)
    return _result(manifest, findings, read_files)


def _parse_manifest(payload: dict[str, Any], findings: list[Finding]) -> LanguagePackManifest | None:
    capability_payloads = payload.get("capabilities", [])
    unsupported_payloads = payload.get("unsupported_capabilities", [])
    default_path_roles = payload.get("default_path_roles", {})

    if not isinstance(capability_payloads, list):
        findings.append(Finding(code="invalid_capabilities_shape", message="Capabilities must be a list."))
        return None
    if not isinstance(unsupported_payloads, list):
        findings.append(
            Finding(code="invalid_unsupported_capabilities_shape", message="Unsupported capabilities must be a list.")
        )
        return None
    if not isinstance(default_path_roles, dict):
        findings.append(Finding(code="invalid_default_path_roles", message="Default path roles must be an object."))
        return None

    capabilities: dict[str, CapabilityDeclaration] = {}
    for raw in capability_payloads:
        if not isinstance(raw, dict):
            findings.append(Finding(code="invalid_capability_shape", message="Capability must be an object."))
            continue
        capability = _parse_capability(raw, findings)
        if capability is None:
            continue
        if capability.id in capabilities:
            findings.append(Finding(code="duplicate_capability", message=f"Duplicate capability: {capability.id}."))
            continue
        capabilities[capability.id] = capability

    unsupported_capabilities: dict[str, UnsupportedCapability] = {}
    for raw in unsupported_payloads:
        if not isinstance(raw, dict):
            findings.append(
                Finding(code="invalid_unsupported_capability_shape", message="Unsupported capability must be an object.")
            )
            continue
        unsupported = _parse_unsupported_capability(raw, findings)
        if unsupported is not None:
            unsupported_capabilities[unsupported.id] = unsupported

    if findings:
        return None

    return LanguagePackManifest(
        language_pack_id=str(payload.get("language_pack_id", "")),
        language_pack_version=str(payload.get("language_pack_version", "")),
        target_language=str(payload.get("target_language", "")),
        capabilities=capabilities,
        unsupported_capabilities=unsupported_capabilities,
        default_path_roles={str(key): str(value) for key, value in default_path_roles.items()},
    )


def _parse_capability(raw: dict[str, Any], findings: list[Finding]) -> CapabilityDeclaration | None:
    capability_id = str(raw.get("id", ""))
    maturity = str(raw.get("maturity", ""))
    if maturity not in VALID_MATURITY_VALUES:
        findings.append(Finding(code="invalid_maturity", message=f"Invalid capability maturity: {maturity}."))

    behavior_evidence = _tuple_of_strings(raw.get("behavior_evidence", []))
    conformance_tests = _tuple_of_strings(raw.get("conformance_tests", []))
    manual_review_cases = _tuple_of_strings(raw.get("manual_review_cases", []))

    if maturity == "stable" and (not behavior_evidence or not (conformance_tests or manual_review_cases)):
        findings.append(
            Finding(
                code="stable_capability_missing_evidence",
                message=f"Stable capability lacks required evidence: {capability_id}.",
            )
        )

    if findings:
        return None

    return CapabilityDeclaration(
        id=capability_id,
        maturity=maturity,
        depends_on=_tuple_of_strings(raw.get("depends_on", [])),
        read_path_roles=_tuple_of_strings(raw.get("read_path_roles", [])),
        write_path_roles=_tuple_of_strings(raw.get("write_path_roles", [])),
        external_tools=_tuple_of_strings(raw.get("external_tools", [])),
        behavior_evidence=behavior_evidence,
        conformance_tests=conformance_tests,
        manual_review_cases=manual_review_cases,
    )


def _parse_unsupported_capability(raw: dict[str, Any], findings: list[Finding]) -> UnsupportedCapability | None:
    fallback = str(raw.get("fallback", ""))
    if fallback != "none":
        findings.append(
            Finding(
                code="unsupported_capability_fallback_not_none",
                message="Unsupported capabilities must declare fallback as none.",
            )
        )
        return None

    return UnsupportedCapability(
        id=str(raw.get("id", "")),
        failure_reason=str(raw.get("failure_reason", "")),
        failure_policy=str(raw.get("failure_policy", "")),
        fallback=fallback,
    )


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


def _result(manifest: LanguagePackManifest | None, findings: list[Finding], read_files: list[str]) -> ManifestLoadResult:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return ManifestLoadResult(
        manifest=manifest,
        findings=findings,
        report=CommandReport(
            command="validate-pack",
            mode="check",
            exit_code=1 if errors else 0,
            errors=errors,
            warnings=warnings,
            read_files=read_files,
        ),
    )
