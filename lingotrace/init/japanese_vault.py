from __future__ import annotations

from pathlib import Path

from lingotrace.core.reports import CommandReport
from lingotrace.init.vault import apply_vault_initialization, plan_vault_initialization


PACK_ROOT = Path(__file__).resolve().parents[1] / "packs" / "japanese"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
PATHS_PATH = PACK_ROOT / "paths.json"


def plan_japanese_vault_initialization(
    target_root: str | Path,
    *,
    runtime_root: str | Path | None = None,
    platform_name: str | None = None,
) -> CommandReport:
    return plan_vault_initialization(
        target_root,
        manifest_path=MANIFEST_PATH,
        paths_path=PATHS_PATH,
        command="init-japanese-vault",
        runtime_root=runtime_root,
        platform_name=platform_name,
    )


def initialize_japanese_vault(
    target_root: str | Path,
    *,
    runtime_root: str | Path | None = None,
    platform_name: str | None = None,
) -> CommandReport:
    plan = plan_japanese_vault_initialization(
        target_root,
        runtime_root=runtime_root,
        platform_name=platform_name,
    )
    return apply_vault_initialization(target_root, plan)
