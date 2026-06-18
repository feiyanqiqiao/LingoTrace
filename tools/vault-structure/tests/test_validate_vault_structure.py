import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_vault_structure.py"
SPEC = importlib.util.spec_from_file_location("validate_vault_structure", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ValidateVaultStructureTests(unittest.TestCase):
    def test_note_files_skips_icloud_dataless_placeholder(self) -> None:
        class FakeStat:
            st_size = 128
            st_blocks = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            valid = root / "学习系统/词库/有效.md"
            placeholder = root / "学习系统/词库/未下载.md"
            valid.parent.mkdir(parents=True)
            valid.write_text("# 有效\n", encoding="utf-8")
            placeholder.write_text("# 未下载\n", encoding="utf-8")
            original_stat = Path.stat

            def fake_stat(path: Path, *args: object, **kwargs: object):
                if path == placeholder:
                    return FakeStat()
                return original_stat(path, *args, **kwargs)

            with patch.object(Path, "stat", fake_stat):
                notes = MODULE.note_files(root)

        self.assertEqual(notes, [valid])

    def test_note_files_reports_non_placeholder_stat_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bad = root / "学习系统/词库/坏文件.md"
            bad.parent.mkdir(parents=True)
            bad.write_text("# 坏文件\n", encoding="utf-8")
            original_stat = Path.stat

            def fake_stat(path: Path, *args: object, **kwargs: object):
                if path == bad:
                    raise OSError("permission denied")
                return original_stat(path, *args, **kwargs)

            with patch.object(Path, "stat", fake_stat):
                with self.assertRaisesRegex(OSError, "unable to stat note file"):
                    MODULE.note_files(root)

    def test_relative_audio_embed_resolves_from_note_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "学习系统/听力/source/example.md"
            audio = root / "学习系统/听力/source/attach/example.m4a"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"audio")
            note.write_text("![[attach/example.m4a]]\n", encoding="utf-8")

            missing = MODULE.find_missing_explicit_links(root, [note])

            self.assertEqual(missing, [])

    def test_baseline_comparison_reports_only_new_missing_links(self) -> None:
        existing = {"笔记/old.md::学习系统/发音/练习/缺失"}
        current = existing | {"笔记/new.md::学习系统/听力/缺失"}

        new_missing = MODULE.new_missing_links(current, existing)

        self.assertEqual(new_missing, {"笔记/new.md::学习系统/听力/缺失"})

    def test_written_baseline_is_used_for_same_run_validation(self) -> None:
        missing = {"笔记/old.md::学习系统/发音/练习/缺失"}

        baseline = MODULE.validation_baseline(missing, set(), wrote_baseline=True, explicit_baseline=False)

        self.assertEqual(baseline, missing)

    def test_dotted_note_name_resolves_by_appending_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "学习系统/词库/例.md"
            daily = root / "笔记/2026.5/2026.5.2.md"
            note.parent.mkdir(parents=True)
            daily.parent.mkdir(parents=True)
            note.write_text("[[笔记/2026.5/2026.5.2]]\n", encoding="utf-8")
            daily.write_text("# 2026.5.2\n", encoding="utf-8")

            missing = MODULE.find_missing_explicit_links(root, [note])

            self.assertEqual(missing, [])

    def test_find_paths_config_prefers_root_system_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            root_config = root / "系统配置/paths.json"
            intermediate_config = root / "学习系统/系统/配置/paths.json"
            root_config.parent.mkdir(parents=True)
            intermediate_config.parent.mkdir(parents=True)
            root_config.write_text("{}\n", encoding="utf-8")
            intermediate_config.write_text("{}\n", encoding="utf-8")

            found = MODULE.find_paths_config(root)

            self.assertEqual(found, root_config)

    def test_validate_roles_accepts_split_review_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            roles = {
                "config_root": "系统配置",
                "template_root": "系统配置/模板",
                "main_dashboard": "学习系统/总训练.base",
                "focus_vocab_root": "学习系统/词库/重点词汇",
                "base_vocab_root": "学习系统/词库/基础词汇",
                "grammar_root": "学习系统/语法",
                "error_root": "学习系统/错题",
                "speaking_card_root": "学习系统/生活口语/句库",
                "speaking_guide_root": "学习系统/生活口语/场景指南",
                "listening_root": "学习系统/听力",
                "pronunciation_practice_root": "学习系统/发音/练习",
                "pronunciation_accent_root": "学习系统/发音/アクセント",
                "pronunciation_phoneme_root": "学习系统/发音/音素",
                "pronunciation_reading_distinction_root": "学习系统/发音/读音辨析",
                "pronunciation_asset_root": "学习系统/发音/素材",
                "lexicon_root": "学习系统/词库",
                "composition_root": "学习系统/作文",
                "daily_notes_root": "笔记",
            }
            config = {
                "managed_review_roots": [
                    roles["focus_vocab_root"],
                    roles["grammar_root"],
                    roles["error_root"],
                    roles["speaking_card_root"],
                    roles["listening_root"],
                    roles["pronunciation_accent_root"],
                    roles["pronunciation_phoneme_root"],
                ],
                "base_vocab_root": roles["base_vocab_root"],
                "daily_notes_root": roles["daily_notes_root"],
                "roles": roles,
            }
            for path in roles.values():
                target = root / path
                if target.suffix:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("", encoding="utf-8")
                else:
                    target.mkdir(parents=True, exist_ok=True)
            config_path = root / "系统配置/paths.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

            errors = MODULE.validate_roles(root)

            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
