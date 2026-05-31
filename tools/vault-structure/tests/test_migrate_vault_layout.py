import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "migrate_vault_layout.py"
SPEC = importlib.util.spec_from_file_location("migrate_vault_layout", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MigrateVaultLayoutTests(unittest.TestCase):
    def test_listening_phase_moves_root_audio_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            material = root / "学习系统/听力/vlog"
            (material / "audio").mkdir(parents=True)
            (material / "audio/source.m4a").write_bytes(b"audio")
            (material / "source.listenkit.md").write_text("# raw\n", encoding="utf-8")
            (material / "source.listenkit.json").write_text("{}\n", encoding="utf-8")

            plan = MODULE.build_phase_plan(root, "listening")

            self.assertIn(
                MODULE.Move("学习系统/听力/vlog/audio/source.m4a", "学习系统/听力/vlog/attach/source.m4a"),
                plan.moves,
            )
            self.assertIn(
                MODULE.Move("学习系统/听力/vlog/source.listenkit.md", "学习系统/听力/vlog/artifacts/source.listenkit.md"),
                plan.moves,
            )
            self.assertIn(
                MODULE.Move("学习系统/听力/vlog/source.listenkit.json", "学习系统/听力/vlog/artifacts/source.listenkit.json"),
                plan.moves,
            )

    def test_listening_phase_does_not_move_existing_attach_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            attach = root / "学习系统/听力/Shadowing/Unit1/attach"
            attach.mkdir(parents=True)
            (attach / "01.mp3").write_bytes(b"audio")

            plan = MODULE.build_phase_plan(root, "listening")

            self.assertEqual(plan.moves, [])

    def test_rewrite_listening_embed_uses_attach_relative_path(self) -> None:
        moves = [
            MODULE.Move("学习系统/听力/Shadowing/Unit2/11.mp3", "学习系统/听力/Shadowing/Unit2/attach/11.mp3"),
        ]
        source = Path("学习系统/听力/Shadowing/Unit2/11_セクション1.md")

        rewritten = MODULE.rewrite_text(source, "![[11.mp3]]\n", moves, {})

        self.assertEqual(rewritten, "![[attach/11.mp3]]\n")

    def test_rewrite_pronunciation_embed_uses_vault_relative_path(self) -> None:
        moves = [
            MODULE.Move("学习系统/发音/其他/audio/source.m4a", "学习系统/发音/素材/audio/source.m4a"),
        ]
        source = Path("学习系统/发音/音素/技巧.md")

        rewritten = MODULE.rewrite_text(source, "![[source.m4a]]\n", moves, {})

        self.assertEqual(rewritten, "![[学习系统/发音/素材/audio/source.m4a]]\n")

    def test_system_phase_does_not_recreate_matching_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = root / "学习系统/系统/配置/paths.json"
            flow = root / "学习系统/系统/复习流程.md"
            config.parent.mkdir(parents=True)
            config.write_text(MODULE.intermediate_paths_config_text(), encoding="utf-8")
            flow.write_text(MODULE.intermediate_review_flow_text(), encoding="utf-8")

            plan = MODULE.build_phase_plan(root, "system")

            self.assertEqual(plan.creates, [])

    def test_content_phase_moves_review_layers_and_system_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = {
                "学习系统/课堂复习/词汇/重点.md": "# 重点\n",
                "学习系统/课堂复习/语法/语法.md": "# 语法\n",
                "学习系统/课堂复习/错题/错题.md": "# 错题\n",
                "学习系统/系统/配置/paths.json": "{}\n",
                "学习系统/系统/模板/录入模板索引.md": "# 模板\n",
                "学习系统/系统/面板/总训练.base": "views: []\n",
                "学习系统/系统/复习流程.md": "# 复习\n",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            plan = MODULE.build_phase_plan(root, "content")

            self.assertIn(MODULE.Move("学习系统/课堂复习/词汇/重点.md", "学习系统/词库/重点词汇/重点.md"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/课堂复习/语法/语法.md", "学习系统/语法/语法.md"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/课堂复习/错题/错题.md", "学习系统/错题/错题.md"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/系统/配置/paths.json", "系统配置/paths.json"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/系统/模板/录入模板索引.md", "系统配置/模板/录入模板索引.md"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/系统/面板/总训练.base", "学习系统/总训练.base"), plan.moves)
            self.assertIn(MODULE.Move("学习系统/系统/复习流程.md", "系统配置/复习流程.md"), plan.moves)

    def test_content_phase_writes_split_review_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            plan = MODULE.build_phase_plan(root, "content")
            config_create = next(create for create in plan.creates if create.path == "系统配置/paths.json")
            config = json.loads(config_create.content)

            self.assertEqual(
                config["managed_review_roots"][:3],
                ["学习系统/词库/重点词汇", "学习系统/语法", "学习系统/错题"],
            )
            self.assertEqual(config["roles"]["config_root"], "系统配置")
            self.assertEqual(config["roles"]["main_dashboard"], "学习系统/总训练.base")
            self.assertNotIn("class_review_root", config["roles"])

    def test_calculated_rewrites_ignore_dynamic_workspace_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / ".obsidian/workspace.json"
            workspace.parent.mkdir(parents=True)
            workspace.write_text('"学习系统/系统/面板/总训练.base"\n', encoding="utf-8")
            plan = MODULE.PhasePlan(
                "content",
                replacements={"学习系统/系统/面板/总训练.base": "学习系统/总训练.base"},
            )

            rewrites = MODULE.calculate_rewrites(root, plan)

            self.assertEqual(rewrites, {})

    def test_workspace_backup_history_is_not_rewritten(self) -> None:
        source = Path(".obsidian/workspace.json")
        text = '"tmp/directory-refactor-backup/files/学习系统/模板/录入模板索引.md"\n'

        rewritten = MODULE.rewrite_text(source, text, [], {"学习系统/模板": "学习系统/系统/模板"})

        self.assertEqual(rewritten, text)

    def test_legacy_fallback_comment_prevents_path_rewrite(self) -> None:
        source = Path("codex-skills/example.sh")
        text = 'config = "学习系统/系统配置/paths.json"  # legacy fallback\n'

        rewritten = MODULE.rewrite_text(source, text, [], {"学习系统/系统配置/paths.json": "学习系统/系统/配置/paths.json"})

        self.assertEqual(rewritten, text)


if __name__ == "__main__":
    unittest.main()
