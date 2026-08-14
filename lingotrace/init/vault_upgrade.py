from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding
from lingotrace.init.vault import PROJECT_ROOT


LEGACY_TOTAL_TRAINING_HASHES = {
    "lingo-japanese": {"fc3ba75d1a0f2694b2736cef46ca4ab34e4a01f74b3fab7c02a065bb82307d1f"},
    "lingo-english": {"73c1be27bbbc014fef4d703f5cdba43b81c661ef078ad364da9f89b529e29560"},
}
PACK_DIRECTORIES = {"lingo-japanese": "japanese", "lingo-english": "english"}


def upgrade_vault(vault_root: str | Path, *, mode: str = "preview") -> CommandReport:
    root = Path(vault_root)
    context_path = root / ".lingotrace/vault-context.json"
    if not context_path.is_file():
        return _error(mode, "missing_vault_context", "The target Vault has no LingoTrace context.", ".lingotrace/vault-context.json")
    try:
        context = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _error(mode, "invalid_vault_context", "The target Vault context is not readable JSON.", ".lingotrace/vault-context.json")

    pack_id = str(context.get("language_pack") or "")
    pack_directory = PACK_DIRECTORIES.get(pack_id)
    if pack_directory is None:
        return _error(mode, "unsupported_language_pack", "Vault upgrade supports the public English and Japanese packs.", ".lingotrace/vault-context.json")
    pack_root = PROJECT_ROOT / "lingotrace" / "packs" / pack_directory
    manifest = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))
    planned_writes: list[dict[str, Any]] = []
    errors: list[Finding] = []

    enabled = list(context.get("enabled_capabilities") or [])
    if "review_queue" not in enabled:
        upgraded_context = dict(context)
        upgraded_context["enabled_capabilities"] = [*enabled, "review_queue"]
        upgraded_context["language_pack_version"] = manifest["language_pack_version"]
        planned_writes.append(
            {
                "path": ".lingotrace/vault-context.json",
                "action": "write_json",
                "reason": "enable the stable review queue capability",
                "content": upgraded_context,
            }
        )

    for name in ("total-training.base", "material-library.base"):
        source = pack_root / "views" / name
        destination = root / "views" / name
        relative = f"views/{name}"
        source_hash = _sha256(source.read_bytes())
        if not destination.exists():
            planned_writes.append(
                {
                    "path": relative,
                    "action": "copy_pack_artifact",
                    "reason": f"deploy {name}",
                    "source_path": source.relative_to(PROJECT_ROOT).as_posix(),
                    "expected_hash": None,
                }
            )
            continue
        current_hash = _sha256(destination.read_bytes())
        if current_hash == source_hash:
            continue
        if name == "total-training.base" and current_hash in LEGACY_TOTAL_TRAINING_HASHES[pack_id]:
            planned_writes.append(
                {
                    "path": relative,
                    "action": "copy_pack_artifact",
                    "reason": "upgrade the unmodified pack dashboard",
                    "source_path": source.relative_to(PROJECT_ROOT).as_posix(),
                    "expected_hash": current_hash,
                }
            )
            continue
        errors.append(
            Finding(
                code="modified_pack_view",
                message=f"Pack view differs from the known public template and will not be overwritten (current {current_hash[:12]}, pack {source_hash[:12]}).",
                path=relative,
            )
        )

    report = CommandReport(
        command="upgrade-vault",
        mode=mode,
        exit_code=1 if errors else 0,
        errors=errors,
        read_files=[".lingotrace/vault-context.json", f"lingotrace/packs/{pack_directory}/manifest.json"],
        planned_writes=planned_writes,
        blocked_files=[finding.path for finding in errors if finding.path],
        artifacts={"language_pack": pack_id},
    )
    if mode != "apply" or not report.accepted:
        return report

    for entry in planned_writes:
        destination = root / entry["path"]
        expected_hash = entry.get("expected_hash")
        if expected_hash is not None and (not destination.exists() or _sha256(destination.read_bytes()) != expected_hash):
            return _error(mode, "upgrade_race_conflict", "A target view changed after preview and was not overwritten.", entry["path"])
        if expected_hash is None and entry["action"] == "copy_pack_artifact" and destination.exists():
            return _error(mode, "upgrade_race_conflict", "A target view appeared after preview and was not overwritten.", entry["path"])
    changed: list[str] = []
    for entry in planned_writes:
        destination = root / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry["action"] == "write_json":
            destination.write_text(json.dumps(entry["content"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            destination.write_bytes((PROJECT_ROOT / entry["source_path"]).read_bytes())
        changed.append(entry["path"])
    report.changed_files = changed
    return report


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _error(mode: str, code: str, message: str, path: str) -> CommandReport:
    return CommandReport(
        command="upgrade-vault",
        mode=mode,
        exit_code=1,
        errors=[Finding(code=code, message=message, path=path)],
        blocked_files=[path],
    )
