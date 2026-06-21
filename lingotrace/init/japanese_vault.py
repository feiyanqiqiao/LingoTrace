from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


PACK_ROOT = Path(__file__).resolve().parents[1] / "packs" / "japanese"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
PATHS_PATH = PACK_ROOT / "paths.json"


def plan_japanese_vault_initialization(target_root: str | Path) -> CommandReport:
    root = Path(target_root)
    manifest = _read_json(MANIFEST_PATH)
    path_config = _read_json(PATHS_PATH)

    planned_writes = _planned_writes(manifest, path_config)
    blocked_files = [
        entry["path"]
        for entry in planned_writes
        if entry["action"] != "create_directory" and (root / entry["path"]).exists()
    ]
    blocked_files.extend(
        entry["path"]
        for entry in planned_writes
        if entry["action"] == "create_directory" and (root / entry["path"]).is_file()
    )

    errors = [
        Finding(
            code="target_conflict",
            message=f"Target path already exists and will not be overwritten: {path}.",
            path=path,
        )
        for path in blocked_files
    ]

    warnings: list[Finding] = []
    if any(root.iterdir()) and not errors:
        warnings.append(
            Finding(
                code="target_not_empty",
                message="Target directory is not empty; dry-run validation completed without planned overwrite.",
                severity="warning",
            )
        )

    return CommandReport(
        command="init-japanese-vault",
        mode="dry-run",
        exit_code=1 if errors else 0,
        errors=errors,
        warnings=warnings,
        read_files=[
            "lingotrace/packs/japanese/manifest.json",
            "lingotrace/packs/japanese/paths.json",
        ],
        planned_writes=planned_writes,
        blocked_files=blocked_files,
    )


def _planned_writes(manifest: dict[str, Any], path_config: dict[str, Any]) -> list[dict[str, Any]]:
    default_path_roles = path_config["default_path_roles"]
    planned: list[dict[str, Any]] = [
        {
            "path": ".lingotrace/vault-context.json",
            "action": "write_json",
            "artifact_class": "recreate-from-pack",
            "reason": "default Japanese Vault context",
            "content": _default_context(manifest),
        },
        {
            "path": ".lingotrace/paths.json",
            "action": "write_json",
            "artifact_class": "recreate-from-pack",
            "reason": "default Japanese path roles",
            "content": _default_paths(default_path_roles),
        },
    ]

    for role, relative_path in default_path_roles.items():
        planned.append(
            {
                "path": relative_path,
                "action": "create_directory",
                "artifact_class": "recreate-from-pack",
                "reason": f"default path role: {role}",
            }
        )

    for template in manifest["templates"]:
        source_path = template["path"]
        planned.append(
            {
                "path": f"templates/{Path(source_path).name}",
                "action": "copy_pack_artifact",
                "artifact_class": template["artifact_class"],
                "reason": f"template: {template['id']}",
                "source_path": source_path,
            }
        )

    for view in manifest["default_views"]:
        source_path = view["path"]
        planned.append(
            {
                "path": f"views/{Path(source_path).name}",
                "action": "copy_pack_artifact",
                "artifact_class": view["artifact_class"],
                "reason": f"default view: {view['id']}",
                "source_path": source_path,
            }
        )

    return planned


def _default_context(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "vault_schema_version": 1,
        "target_language": manifest["target_language"],
        "explanation_language": "zh",
        "language_pack": manifest["language_pack_id"],
        "language_pack_version": manifest["language_pack_version"],
        "enabled_capabilities": [capability["id"] for capability in manifest["capabilities"]],
    }


def _default_paths(default_path_roles: dict[str, str]) -> dict[str, Any]:
    return {
        "path_roles": [
            {
                "role": role,
                "relative_path": relative_path,
                "source": "vault_config",
            }
            for role, relative_path in default_path_roles.items()
        ]
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
