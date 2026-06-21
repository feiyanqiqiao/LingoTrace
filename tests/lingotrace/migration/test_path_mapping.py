from __future__ import annotations

import unittest

from lingotrace.migration.path_mapping import (
    JAPANESE_OPERATIONAL_PATH_MAPPINGS,
    map_target_path,
)


class PathMappingTests(unittest.TestCase):
    def test_maps_old_japanese_roles_to_new_target_roles(self) -> None:
        self.assertEqual(
            "review/focus/vocab/合成語.md",
            map_target_path(
                "学习系统/词库/重点词汇/合成語.md",
                JAPANESE_OPERATIONAL_PATH_MAPPINGS,
            ),
        )
        self.assertEqual(
            "listening/Shadowing_初中級/Unit1/01.md",
            map_target_path(
                "学习系统/听力/Shadowing_初中級/Unit1/01.md",
                JAPANESE_OPERATIONAL_PATH_MAPPINGS,
            ),
        )
        self.assertEqual(
            "daily/2026.6/2026.6.20.md",
            map_target_path("笔记/2026.6/2026.6.20.md", JAPANESE_OPERATIONAL_PATH_MAPPINGS),
        )

    def test_longest_prefix_wins_before_broad_fallback(self) -> None:
        self.assertEqual(
            "review/pronunciation/accent/card.md",
            map_target_path(
                "学习系统/发音/アクセント/card.md",
                JAPANESE_OPERATIONAL_PATH_MAPPINGS,
            ),
        )
        self.assertEqual(
            "legacy-preserved/学习系统/発音/unknown.md",
            map_target_path(
                "学习系统/発音/unknown.md",
                JAPANESE_OPERATIONAL_PATH_MAPPINGS,
            ),
        )

    def test_rejects_unsafe_source_and_target_paths(self) -> None:
        with self.assertRaises(ValueError):
            map_target_path("../outside.md", JAPANESE_OPERATIONAL_PATH_MAPPINGS)

        with self.assertRaises(ValueError):
            map_target_path(
                "学习系统/听力/card.md",
                [{"source_prefix": "学习系统/听力", "target_prefix": "../outside"}],
            )


if __name__ == "__main__":
    unittest.main()
