from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


DEFAULT_PERSONAL_PATH_MARKERS = (
    "/" + "Users" + "/",
    "Mobile" + " Documents",
    "iCloud" + "~md~obsidian",
)


def validate_public_report_paths(
    payload: Any,
    *,
    private_roots: Sequence[str] = (),
    private_name_markers: Sequence[str] = (),
    personal_path_markers: Sequence[str] = DEFAULT_PERSONAL_PATH_MARKERS,
) -> CommandReport:
    errors: list[Finding] = []
    private_markers = tuple(marker for marker in (*private_roots, *private_name_markers) if marker)
    personal_markers = tuple(marker for marker in personal_path_markers if marker)

    for path, value in _walk_strings(payload):
        if any(marker in value for marker in personal_markers):
            errors.append(
                Finding(
                    code="personal_absolute_path_rejected",
                    message="Public migration reports must not contain personal absolute-path markers.",
                    path=path,
                )
            )
            continue

        if any(marker in value for marker in private_markers):
            errors.append(
                Finding(
                    code="private_path_in_public_report",
                    message="Public migration reports must not contain private Vault roots, artifact roots, or user markers.",
                    path=path,
                )
            )

    return CommandReport(
        command="validate-public-migration-report-paths",
        mode="check",
        exit_code=1 if errors else 0,
        errors=sorted(errors, key=lambda finding: (finding.path or "", finding.code)),
    )


def _walk_strings(payload: Any, path: str = "") -> list[tuple[str, str]]:
    if isinstance(payload, str):
        return [(path, payload)]

    if isinstance(payload, Mapping):
        result: list[tuple[str, str]] = []
        for key in sorted(payload):
            child_path = str(key) if path == "" else f"{path}.{key}"
            result.extend(_walk_strings(payload[key], child_path))
        return result

    if isinstance(payload, Sequence) and not isinstance(payload, (bytes, bytearray)):
        result: list[tuple[str, str]] = []
        for index, value in enumerate(payload):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            result.extend(_walk_strings(value, child_path))
        return result

    return []
