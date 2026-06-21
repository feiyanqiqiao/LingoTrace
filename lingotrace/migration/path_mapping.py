from __future__ import annotations

from pathlib import Path
from typing import Any


JAPANESE_OPERATIONAL_PATH_MAPPINGS = [
    {"source_prefix": "学习系统/词库/重点词汇", "target_prefix": "review/focus/vocab"},
    {"source_prefix": "学习系统/词库/基础词汇", "target_prefix": "review/base/vocab"},
    {"source_prefix": "学习系统/语法", "target_prefix": "review/grammar"},
    {"source_prefix": "学习系统/错题", "target_prefix": "review/errors"},
    {"source_prefix": "学习系统/生活口语/句库", "target_prefix": "speaking/cards"},
    {"source_prefix": "学习系统/生活口语/场景指南", "target_prefix": "speaking/guides"},
    {"source_prefix": "学习系统/听力", "target_prefix": "listening"},
    {"source_prefix": "学习系统/发音/アクセント", "target_prefix": "review/pronunciation/accent"},
    {"source_prefix": "学习系统/发音/音素", "target_prefix": "review/pronunciation/phoneme"},
    {"source_prefix": "学习系统/发音/练习", "target_prefix": "review/pronunciation/practice"},
    {"source_prefix": "学习系统/发音/读音辨析", "target_prefix": "review/pronunciation/reading-distinctions"},
    {"source_prefix": "学习系统/发音/素材", "target_prefix": "sources/pronunciation-assets"},
    {"source_prefix": "学习系统/作文", "target_prefix": "sources/composition"},
    {"source_prefix": "笔记", "target_prefix": "daily"},
]


def map_target_path(relative_path: str, path_mappings: list[dict[str, Any]]) -> str:
    if _is_unsafe_relative_path(relative_path):
        raise ValueError("unsafe_relative_path")

    sorted_mappings = sorted(
        path_mappings,
        key=lambda mapping: len(str(mapping.get("source_prefix", ""))),
        reverse=True,
    )
    for mapping in sorted_mappings:
        source_prefix = str(mapping.get("source_prefix", "")).rstrip("/")
        target_prefix = str(mapping.get("target_prefix", "")).strip("/")
        if source_prefix == "":
            continue
        if relative_path == source_prefix:
            target_path = target_prefix
            break
        if relative_path.startswith(source_prefix + "/"):
            suffix = relative_path[len(source_prefix) + 1 :]
            target_path = f"{target_prefix}/{suffix}" if target_prefix else suffix
            break
    else:
        target_path = f"legacy-preserved/{relative_path}"

    if _is_unsafe_relative_path(target_path):
        raise ValueError("unsafe_target_path")
    return target_path


def _is_unsafe_relative_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return relative_path == "" or path.is_absolute() or ".." in path.parts
