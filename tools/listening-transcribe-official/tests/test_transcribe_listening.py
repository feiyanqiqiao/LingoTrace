import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "transcribe_listening.py"
SPEC = importlib.util.spec_from_file_location("transcribe_listening", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SETUP_MODULE_PATH = Path(__file__).resolve().parents[1] / "setup_offline_dictionary.py"
SETUP_SPEC = importlib.util.spec_from_file_location("setup_offline_dictionary", SETUP_MODULE_PATH)
SETUP_MODULE = importlib.util.module_from_spec(SETUP_SPEC)
assert SETUP_SPEC.loader is not None
sys.modules[SETUP_SPEC.name] = SETUP_MODULE
SETUP_SPEC.loader.exec_module(SETUP_MODULE)
WRAPPER_PATH = Path(__file__).resolve().parents[3] / "codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh"
INIT_RUNTIME_PATH = WRAPPER_PATH.with_name("init-listening-runtime.sh")
CHECK_CHAIN_PATH = WRAPPER_PATH.with_name("check-listening-chain.sh")
REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements-listening.txt"


class TranscribeListeningTests(unittest.TestCase):
    def test_wrapper_defaults_to_local_cache_virtualenv(self) -> None:
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")

        self.assertIn('${HOME}/Library/Caches/LingoTrace/venvs/cpython-314/bin/python', wrapper)
        self.assertNotIn('${ROOT}/.venv', wrapper)
        self.assertNotIn('/opt/homebrew/bin/python3.14', wrapper)

    def test_wrapper_supports_explicit_runtime_override_without_fallback(self) -> None:
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")

        self.assertIn("LINGOTRACE_LISTENING_PYTHON", wrapper)
        self.assertIn("JP_LISTENING_PYTHON", wrapper)
        self.assertIn("init-listening-runtime.sh", wrapper)

    def test_runtime_requirements_only_pin_direct_dictionary_dependencies(self) -> None:
        requirements = [
            line.strip()
            for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(requirements, ["fugashi==1.5.2", "unidic-lite==1.0.8"])

    def test_runtime_init_and_chain_check_are_explicit(self) -> None:
        init_script = INIT_RUNTIME_PATH.read_text(encoding="utf-8")
        check_script = CHECK_CHAIN_PATH.read_text(encoding="utf-8")

        self.assertIn('python3.14', init_script)
        self.assertIn('requirements-listening.txt', init_script)
        self.assertIn('Library/Caches/LingoTrace/venvs/cpython-314', init_script)
        self.assertNotIn('ln -s', init_script)
        self.assertIn('${LISTENKIT_ROOT}/cli/check-runtime.sh', check_script)
        self.assertIn('Library/Caches/ListenKit/venvs/cpython-314/bin/python', check_script)
        self.assertNotIn('${LISTENKIT_ROOT}/.venv/bin/python', check_script)
        self.assertIn('ffmpeg', check_script)
        self.assertIn('ffprobe', check_script)

    def test_confirmed_accent_index_uses_configured_focus_vocab_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = root / "系统配置/paths.json"
            focus = root / "学习系统/词库/重点词汇"
            config.parent.mkdir(parents=True)
            focus.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "roles": {
                            "focus_vocab_root": "学习系统/词库/重点词汇",
                            "base_vocab_root": "学习系统/词库/基础词汇",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (focus / "相撲.md").write_text(
                "---\nheadword: 相撲\nreading: すもう\naccent_display: すもう⓪\n---\n",
                encoding="utf-8",
            )

            index = MODULE.load_confirmed_accent_index(root)

            self.assertEqual(index["相撲"], "すもう⓪")

    def test_process_one_preserves_existing_second_phase_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "manabo_cz20.mp3"
            audio_path.write_bytes(b"audio")
            note_path = root / "manabo_cz20_1日の摂取カロリー.md"
            note_path.write_text(
                "\n".join(
                    [
                        "---",
                        "track: listening",
                        "daily_use_sentences:",
                        "  - 既存の例文です。",
                        "transcript_status: full",
                        "transcript_ref: in-note",
                        "---",
                        "",
                        "# manabo_cz20 1日の摂取カロリー",
                        "",
                        "![[manabo_cz20.mp3]]",
                        "",
                        "## 脚本",
                        "",
                        "旧脚本です。",
                        "",
                        "## 可直接背的常用句",
                        "",
                        "原句：既存の例文です。",
                        "句式：既存の句式説明。",
                        "可替换骨架：AはBです。",
                        "",
                        "## 素材说明",
                        "",
                        "人工で補った説明です。",
                        "",
                        "## 我的备注",
                        "",
                        "ここは残したいメモです。",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            payload = {
                "full_text": "新しい文です。次の文です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "新しい文です。"},
                    {"start": 1.2, "end": 2.1, "text": "次の文です。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                result = MODULE.process_one(audio_path, None, "ja-JP", None, False)

            self.assertIn("Updated", result)
            rendered = note_path.read_text(encoding="utf-8")
            self.assertIn("新しい", rendered)
            self.assertIn("次の文です。", rendered)
            self.assertIn("原句：既存の例文です。", rendered)
            self.assertIn("人工で補った説明です。", rendered)
            self.assertIn("## 我的备注", rendered)
            self.assertIn("ここは残したいメモです。", rendered)
            self.assertIn("  - 既存の例文です。", rendered)

    def test_process_one_creates_placeholder_when_note_is_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "manabo_cz99.mp3"
            audio_path.write_bytes(b"audio")
            payload = {
                "full_text": "これは新しい素材です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "これは新しい素材です。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                result = MODULE.process_one(audio_path, None, "ja-JP", None, False)

            self.assertIn("Created", result)
            created_notes = list(root.glob("manabo_cz99_*.md"))
            self.assertEqual(len(created_notes), 1)
            rendered = created_notes[0].read_text(encoding="utf-8")
            self.assertIn("daily_use_sentences: []", rendered)
            self.assertIn(MODULE.COMMON_SECTION_PLACEHOLDER, rendered)

    def test_learning_package_marks_confirmed_and_local_candidate_accents(self) -> None:
        package = MODULE.build_learning_package(
            ["公園を散歩します。"],
            {"公園": "こうえん⓪"},
            MODULE.StaticAccentDictionary({"散歩": "さんぽ⓪"}),
            ["manabo_cz99_S01.m4a"],
        )

        self.assertIn("### S01", package)
        self.assertIn("公園⓪を散歩⓪します。", package)
        self.assertIn("![[manabo_cz99_S01.m4a]]", package)
        self.assertNotIn("句子：", package)
        self.assertNotIn("语音切片：", package)
        self.assertNotIn("备注：", package)
        self.assertNotIn("已确认", package)
        self.assertNotIn("本地候选", package)
        self.assertNotIn("跟读切分：", package)
        self.assertNotIn("重点词重音：", package)
        self.assertNotIn("发音焦点：", package)
        self.assertNotIn("打磨提示：", package)

    def test_offline_dictionary_lookup_uses_unidic_accent_type(self) -> None:
        class Feature:
            kana = "コウエン"
            kanaBase = "コウエン"
            pron = "コーエン"
            lemma = "公園"
            orth = "公園"
            orthBase = "公園"
            aType = "0"

        class Word:
            surface = "公園"
            feature = Feature()

        class FakeTagger:
            def __call__(self, text):
                return [Word()] if text == "公園" else []

        with tempfile.TemporaryDirectory() as tmpdir:
            dictionary = MODULE.OfflineAccentDictionary(Path(tmpdir))
            dictionary._tagger = FakeTagger()

            self.assertEqual(dictionary.lookup("公園"), "コウエン⓪")
            package = MODULE.build_learning_package(
                ["公園を散歩します。"],
                {},
                dictionary,
                ["manabo_cz99_S01.m4a"],
            )

        self.assertIn("公園⓪を散歩します。", package)

    def test_offline_dictionary_uses_active_virtualenv_not_abi_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dictionary = MODULE.OfflineAccentDictionary(Path(tmpdir))

            self.assertFalse(hasattr(dictionary, "python_target"))

    def test_learning_package_marks_unknown_focus_terms_as_pending_confirmation(self) -> None:
        package = MODULE.build_learning_package(
            ["三井公園を少し歩きます。"],
            {},
            MODULE.StaticAccentDictionary({}),
            [None],
        )

        self.assertIn("三井公園を少し歩きます。", package)
        self.assertIn("（语音切片待生成）", package)
        self.assertNotIn("句子：", package)
        self.assertNotIn("语音切片：", package)
        self.assertNotIn("备注：", package)
        self.assertNotIn("待确认", package)
        self.assertNotIn("三井公園⓪", package)

    def test_inline_accent_prefers_longer_terms_over_nested_terms(self) -> None:
        package = MODULE.build_learning_package(
            ["相撲取りの世界です。"],
            {"相撲取り": "すもうとり⓪", "相撲": "すもう⓪"},
            MODULE.StaticAccentDictionary({}),
            [None],
        )

        self.assertIn("相撲取り⓪の世界です。", package)
        self.assertNotIn("相撲⓪取り", package)

    def test_inline_accent_does_not_mark_kanji_substring_inside_compound(self) -> None:
        package = MODULE.build_learning_package(
            ["兄弟子たちの食事当番です。"],
            {},
            MODULE.StaticAccentDictionary({"兄弟": "きょうだい①", "食事": "しょくじ⓪", "当番": "とうばん①"}),
            ["manabo_cz99_S01.m4a"],
        )

        self.assertIn("兄弟子たちの食事当番です。", package)
        self.assertNotIn("兄弟①子", package)
        self.assertNotIn("食事⓪当番", package)
        self.assertNotIn("食事当番①", package)

    def test_offline_dictionary_does_not_mark_inflected_stems(self) -> None:
        class Feature:
            kana = "ツクラ"
            kanaBase = "ツクル"
            pron = "ツクラ"
            lemma = "作る"
            orth = "作ら"
            orthBase = "作る"
            pos1 = "動詞"
            cForm = "未然形-一般"
            aType = "2"

        class Word:
            surface = "作ら"
            feature = Feature()

        class FakeTagger:
            def __call__(self, text):
                return [Word()] if text == "作ら" else []

        with tempfile.TemporaryDirectory() as tmpdir:
            dictionary = MODULE.OfflineAccentDictionary(Path(tmpdir))
            dictionary._tagger = FakeTagger()

            self.assertIsNone(dictionary.lookup("作ら"))

    def test_build_body_places_learning_package_before_plain_script(self) -> None:
        body, _ = MODULE.build_body(
            "manabo_cz15 私の町",
            "manabo_cz15.mp3",
            ["公園を散歩します。"],
            [MODULE.Chunk(start=0.0, end=1.0, text="公園を散歩します。")],
            Path("manabo_cz15.mp3"),
            confirmed_accent_index={"公園": "こうえん⓪"},
            offline_dictionary=MODULE.StaticAccentDictionary({"散歩": "さんぽ⓪"}),
        )

        self.assertLess(body.index("## 精听学习包"), body.index("## 脚本"))
        self.assertIn("公園⓪を散歩⓪します。", body)
        self.assertNotIn("句子：", body)
        self.assertNotIn("语音切片：", body)
        self.assertNotIn("备注：", body)

    def test_resolve_listening_mode_defaults_to_extensive(self) -> None:
        self.assertEqual(MODULE.resolve_listening_mode(None, [], ""), "extensive")

    def test_resolve_listening_mode_uses_explicit_mode_first(self) -> None:
        frontmatter = ["track: listening", "listening_mode: extensive"]
        body = "## 精听学习包\n\n### S01\n\n公園を散歩します。"

        self.assertEqual(MODULE.resolve_listening_mode("intensive", frontmatter, body), "intensive")

    def test_resolve_listening_mode_infers_legacy_intensive_package(self) -> None:
        body = "## 精听学习包\n\n### S01\n\n公園を散歩します。"

        self.assertEqual(MODULE.resolve_listening_mode(None, [], body), "intensive")

    def test_build_body_extensive_skips_learning_package_and_accents_script(self) -> None:
        body, _ = MODULE.build_body(
            "N3 A-6 ケーキ",
            "N3 A-6.mp3",
            ["公園を散歩します。"],
            [MODULE.Chunk(start=0.0, end=1.0, text="公園を散歩します。")],
            Path("N3 A-6.mp3"),
            confirmed_accent_index={"公園": "こうえん⓪"},
            offline_dictionary=MODULE.StaticAccentDictionary({"散歩": "さんぽ⓪"}),
            audio_slice_refs=["N3 A-6_S01.m4a"],
            listening_mode="extensive",
        )

        self.assertNotIn("## 精听学习包", body)
        self.assertNotIn("### S01", body)
        self.assertNotIn("![[N3 A-6_S01.m4a]]", body)
        self.assertIn("## 脚本", body)
        self.assertIn("公園⓪を散歩⓪します。", body)

    def test_build_body_intensive_keeps_plain_script_and_learning_package(self) -> None:
        body, _ = MODULE.build_body(
            "manabo_cz15 私の町",
            "manabo_cz15.mp3",
            ["公園を散歩します。"],
            [MODULE.Chunk(start=0.0, end=1.0, text="公園を散歩します。")],
            Path("manabo_cz15.mp3"),
            confirmed_accent_index={"公園": "こうえん⓪"},
            offline_dictionary=MODULE.StaticAccentDictionary({"散歩": "さんぽ⓪"}),
            audio_slice_refs=["manabo_cz15_S01.m4a"],
            listening_mode="intensive",
        )

        self.assertIn("## 精听学习包", body)
        self.assertIn("公園⓪を散歩⓪します。", body)
        script_section = body.split("## 脚本", 1)[1]
        self.assertIn("公園を散歩します。", script_section)
        self.assertNotIn("公園⓪を散歩⓪します。", script_section)

    def test_export_sentence_audio_slices_uses_chunk_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "manabo_cz99.mp3"
            audio_path.write_bytes(b"fake audio")
            attach_dir = root / "attach"
            chunks = [MODULE.Chunk(start=1.2, end=2.8, text="公園を散歩します。")]

            def fake_run_ffmpeg(args):
                Path(args[-1]).write_bytes(b"slice")

            with mock.patch.object(MODULE, "run_ffmpeg", side_effect=fake_run_ffmpeg) as ffmpeg_mock:
                refs = MODULE.export_sentence_audio_slices(audio_path, chunks, attach_dir, "manabo_cz99")

            self.assertEqual(refs, ["attach/manabo_cz99_S01.m4a"])
            self.assertTrue((attach_dir / "manabo_cz99_S01.m4a").exists())
            command = ffmpeg_mock.call_args.args[0]
            self.assertIn("-ss", command)
            self.assertIn("1.2", command)
            self.assertIn("-to", command)
            self.assertIn("2.8", command)

    def test_sentence_learning_blocks_map_natural_sentences_across_chunks(self) -> None:
        blocks = MODULE.sentence_learning_blocks(
            ["今日は晴れです。", "散歩します。"],
            [
                MODULE.Chunk(start=0.0, end=1.0, text="今日は"),
                MODULE.Chunk(start=1.0, end=3.0, text="晴れです。散歩します。"),
            ],
        )

        self.assertIsNotNone(blocks)
        assert blocks is not None
        self.assertEqual([block.id for block in blocks], ["S01", "S02"])
        self.assertEqual([block.text for block in blocks], ["今日は晴れです。", "散歩します。"])
        self.assertEqual(blocks[0].start, 0.0)
        self.assertGreater(blocks[0].end, 1.0)
        self.assertEqual(blocks[0].end, blocks[1].start)
        self.assertEqual(blocks[1].end, 3.0)

    def test_numbered_dialogue_profile_is_detected_without_shadowing_path(self) -> None:
        payload = {
            "engine": "faster-whisper",
            "full_text": "",
            "segments": [
                {"start": 0.0, "end": 0.8, "text": "1"},
                {"start": 0.8, "end": 2.0, "text": "お名前は？"},
                {"start": 2.0, "end": 3.0, "text": "ペドロです。"},
                {"start": 3.5, "end": 4.2, "text": "2"},
                {"start": 4.2, "end": 5.5, "text": "お国は？"},
                {"start": 5.5, "end": 6.5, "text": "スペインです。"},
            ],
        }

        candidate = MODULE.candidate_from_payload(Path("neutral/lesson.mp3"), payload, "faster-whisper")

        self.assertEqual(candidate.slice_profile.kind, "dialogue")
        self.assertEqual(candidate.slice_profile.grouping, "numbered")
        self.assertEqual(candidate.slice_profile.number_markers, "included")
        self.assertEqual(candidate.slice_profile.padding_seconds, 0.0)

    def test_numbered_dialogue_accepts_observation_response_and_long_answer(self) -> None:
        chunks = [
            MODULE.Chunk(start=0.0, end=0.5, text="1"),
            MODULE.Chunk(start=0.5, end=2.0, text="あ、見て。昨日の台風で木が倒れてる。"),
            MODULE.Chunk(start=2.0, end=3.5, text="本当だ。すごい風だったんだね。"),
            MODULE.Chunk(start=4.0, end=4.5, text="2"),
            MODULE.Chunk(start=4.5, end=5.5, text="リンさん、宿題は？"),
            MODULE.Chunk(start=5.5, end=8.5, text="すいません。今、母が来ているので、来週出してもいいですか？"),
        ]

        profile = MODULE.detect_slice_profile(chunks)
        blocks = MODULE.numbered_dialogue_learning_blocks(chunks)

        self.assertEqual(profile.grouping, "numbered")
        self.assertIsNotNone(blocks)
        assert blocks is not None
        self.assertEqual(len(blocks), 2)
        self.assertIn("A：あ、見て。昨日の台風で木が倒れてる。", blocks[0].text)
        self.assertIn("B：すいません。今、母が来ているので、来週出してもいいですか？", blocks[1].text)

    def test_shadowing_path_monologue_uses_sentence_profile(self) -> None:
        payload = {
            "engine": "faster-whisper",
            "full_text": "今日は良い天気です。公園を散歩します。",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "今日は良い天気です。"},
                {"start": 2.0, "end": 4.0, "text": "公園を散歩します。"},
            ],
        }

        candidate = MODULE.candidate_from_payload(Path("Shadowing_初中級/lesson.mp3"), payload, "faster-whisper")

        self.assertEqual(candidate.slice_profile.kind, "sentence")
        self.assertEqual(candidate.slice_profile.grouping, "sentence")
        self.assertEqual(candidate.slice_profile.padding_seconds, 0.5)

    def test_unnumbered_dialogue_groups_continuous_four_turn_exchange(self) -> None:
        chunks = [
            MODULE.Chunk(start=0.0, end=1.0, text="お名前は？"),
            MODULE.Chunk(start=1.0, end=2.0, text="ペドロです。"),
            MODULE.Chunk(start=2.5, end=3.5, text="お国は？"),
            MODULE.Chunk(start=3.5, end=4.5, text="スペインです。"),
        ]

        profile = MODULE.detect_slice_profile(chunks)
        blocks = MODULE.dialogue_exchange_learning_blocks(chunks)

        self.assertEqual(profile.kind, "dialogue")
        self.assertEqual(profile.grouping, "exchange")
        self.assertIsNotNone(blocks)
        assert blocks is not None
        self.assertEqual(len(blocks), 1)
        self.assertEqual(
            blocks[0].text,
            "A：お名前は？\nB：ペドロです。\nA：お国は？\nB：スペインです。",
        )

    def test_unnumbered_dialogue_groups_two_turn_exchange(self) -> None:
        chunks = [
            MODULE.Chunk(start=0.0, end=1.0, text="駅までどのくらいですか？"),
            MODULE.Chunk(start=1.0, end=2.0, text="歩いて5分ぐらいです。"),
        ]

        profile = MODULE.detect_slice_profile(chunks)
        blocks = MODULE.dialogue_exchange_learning_blocks(chunks)

        self.assertEqual(profile.grouping, "exchange")
        self.assertIsNotNone(blocks)
        assert blocks is not None
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].start, 0.0)
        self.assertEqual(blocks[0].end, 2.0)

    def test_numbered_list_without_dialogue_falls_back_to_sentence(self) -> None:
        profile = MODULE.detect_slice_profile(
            [
                MODULE.Chunk(start=0.0, end=0.5, text="1"),
                MODULE.Chunk(start=0.5, end=1.5, text="東京"),
                MODULE.Chunk(start=1.5, end=2.0, text="2"),
                MODULE.Chunk(start=2.0, end=3.0, text="大阪"),
            ]
        )

        self.assertEqual(profile.kind, "sentence")
        self.assertEqual(profile.grouping, "sentence")

    def test_mixed_dialogue_and_monologue_falls_back_to_sentence(self) -> None:
        profile = MODULE.detect_slice_profile(
            [
                MODULE.Chunk(start=0.0, end=1.0, text="駅までどのくらいですか？"),
                MODULE.Chunk(start=1.0, end=2.0, text="歩いて5分ぐらいです。"),
                MODULE.Chunk(start=2.0, end=4.0, text="そのあと、公園をゆっくり散歩しました。"),
            ]
        )

        self.assertEqual(profile.grouping, "sentence")

    def test_numbered_dialogue_learning_blocks_include_own_number_announcement(self) -> None:
        blocks = MODULE.numbered_dialogue_learning_blocks(
            [
                MODULE.Chunk(start=0.0, end=1.0, text="セクション10"),
                MODULE.Chunk(start=1.0, end=2.0, text="1"),
                MODULE.Chunk(start=2.0, end=4.0, text="最近、冷えますか？"),
                MODULE.Chunk(start=4.0, end=6.0, text="はい、本当に寒くなりました。"),
                MODULE.Chunk(start=6.0, end=7.0, text="２"),
                MODULE.Chunk(start=7.0, end=9.0, text="新しい仕事には、もう慣れた？"),
                MODULE.Chunk(start=9.0, end=11.0, text="はい、もう慣れました。"),
            ]
        )

        self.assertIsNotNone(blocks)
        assert blocks is not None
        self.assertEqual([block.id for block in blocks], ["S01", "S02"])
        self.assertEqual(blocks[0].start, 1.0)
        self.assertEqual(blocks[0].end, 6.0)
        self.assertEqual(blocks[0].text, "1\nA：最近、冷えますか？\nB：はい、本当に寒くなりました。")
        self.assertEqual(blocks[0].kind, "numbered-dialogue")
        self.assertEqual(blocks[1].start, 6.0)

    def test_numbered_dialogue_learning_blocks_reject_missing_group_number(self) -> None:
        blocks = MODULE.numbered_dialogue_learning_blocks(
            [
                MODULE.Chunk(start=0.0, end=1.0, text="セクション10"),
                MODULE.Chunk(start=1.0, end=2.0, text="1"),
                MODULE.Chunk(start=2.0, end=4.0, text="最近、冷えますね。"),
                MODULE.Chunk(start=4.0, end=5.0, text="3"),
                MODULE.Chunk(start=5.0, end=7.0, text="今週末の予定、何かある？"),
            ]
        )

        self.assertIsNone(blocks)

    def test_manual_slice_manifest_can_override_ranges_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manual.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "slices": [
                            {
                                "id": "S01",
                                "start": 1.5,
                                "end": 4.5,
                                "text": "人工整理した一段落です。",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            blocks = MODULE.load_manual_learning_blocks(manifest_path, [])

        self.assertEqual(
            blocks,
            [
                MODULE.LearningBlock(
                    id="S01",
                    text="人工整理した一段落です。",
                    start=1.5,
                    end=4.5,
                    kind="manual",
                )
            ],
        )

    def test_slice_profile_cli_override_precedes_manifest_profile(self) -> None:
        detected = MODULE.SliceProfile("dialogue", "numbered", "auto", "included", 0.0)
        manifest = MODULE.SliceProfile("dialogue", "numbered", "manifest", "included", 0.0)

        resolved = MODULE.resolve_slice_profile("sentence", manifest, detected, [])

        self.assertEqual(resolved.kind, "sentence")
        self.assertEqual(resolved.grouping, "sentence")
        self.assertEqual(resolved.source, "cli")
        self.assertEqual(resolved.padding_seconds, 0.5)

    def test_slice_profile_manifest_precedes_auto_detection(self) -> None:
        detected = MODULE.SliceProfile("sentence", "sentence", "auto", "none", 0.5)
        manifest = MODULE.SliceProfile("dialogue", "numbered", "manifest", "included", 0.0)

        resolved = MODULE.resolve_slice_profile("auto", manifest, detected, [])

        self.assertEqual(resolved, manifest)

    def test_forced_dialogue_requires_reliable_blocks_or_manifest_profile(self) -> None:
        detected = MODULE.SliceProfile("sentence", "sentence", "auto", "none", 0.5)
        chunks = [MODULE.Chunk(start=0.0, end=2.0, text="今日は良い天気です。")]

        with self.assertRaisesRegex(RuntimeError, "reviewed --slice-manifest"):
            MODULE.resolve_slice_profile("dialogue", None, detected, chunks)

    def test_manifest_profile_is_optional_and_persisted_without_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.slices.json"
            profile = MODULE.SliceProfile("dialogue", "exchange", "auto", "none", 0.5)
            blocks = [
                MODULE.LearningBlock(
                    id="S01",
                    text="A：駅までどのくらいですか？\nB：歩いて5分ぐらいです。",
                    start=1.0,
                    end=4.0,
                    kind="dialogue-exchange",
                )
            ]

            MODULE.write_slice_manifest(path, blocks, profile)
            payload = json.loads(path.read_text(encoding="utf-8"))
            loaded = MODULE.load_manifest_slice_profile(path)

        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["slice_profile"]["grouping"], "exchange")
        self.assertEqual(loaded, MODULE.SliceProfile("dialogue", "exchange", "manifest", "none", 0.5))

    def test_legacy_manifest_without_profile_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy.slices.json"
            path.write_text(
                json.dumps({"version": 1, "slices": [{"id": "S01", "start": 1.0, "end": 2.0}]}),
                encoding="utf-8",
            )

            profile = MODULE.load_manifest_slice_profile(path)

        self.assertIsNone(profile)

    def test_default_manifest_is_reused_only_when_marked_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.slices.json"
            profile = MODULE.SliceProfile("dialogue", "numbered", "auto", "included", 0.0)
            blocks = [
                MODULE.LearningBlock(id="S01", text="1\nA：お名前は？\nB：ペドロです。", start=1.0, end=3.0, kind="manual")
            ]
            MODULE.write_slice_manifest(path, blocks, profile)

            automatic = MODULE.load_manifest_slice_profile(path, reviewed_only=True)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["slice_profile"]["source"] = "manifest"
            path.write_text(json.dumps(payload), encoding="utf-8")
            reviewed = MODULE.load_manifest_slice_profile(path, reviewed_only=True)

        self.assertIsNone(automatic)
        self.assertEqual(reviewed, MODULE.SliceProfile("dialogue", "numbered", "manifest", "included", 0.0))

    def test_parse_args_accepts_slice_profile_override(self) -> None:
        with mock.patch.object(sys, "argv", ["transcribe-listening", "audio.mp3", "--slice-profile", "dialogue"]):
            args = MODULE.parse_args()

        self.assertEqual(args.slice_profile, "dialogue")

    def test_review_sidecar_records_resolved_slice_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "attach" / "lesson.mp3"
            audio_path.parent.mkdir(parents=True)
            audio_path.write_bytes(b"audio")
            note_path = root / "lesson.md"
            manifest_path = root / "artifacts" / "lesson.slices.json"
            report_path = root / "artifacts" / "lesson.slice-export.json"
            profile = MODULE.SliceProfile("dialogue", "exchange", "cli", "none", 0.5)
            export_result = MODULE.SliceExportResult([], report_path, {"version": 1, "slices": []})
            blocks = [
                MODULE.LearningBlock(
                    id="S01",
                    text="A：駅までどのくらいですか？\nB：歩いて5分ぐらいです。",
                    start=1.0,
                    end=3.0,
                    kind="dialogue-exchange",
                )
            ]

            review_path = MODULE.write_intensive_review_sidecar(
                audio_path,
                note_path,
                "faster-whisper",
                manifest_path,
                export_result,
                blocks,
                profile,
            )
            review = review_path.read_text(encoding="utf-8")

        self.assertIn("- slice_profile_kind: dialogue", review)
        self.assertIn("- slice_profile_grouping: exchange", review)
        self.assertIn("- slice_profile_source: cli", review)
        self.assertIn("- slice_padding_seconds: 0.5", review)

    def test_export_learning_block_slices_invokes_listenkit_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "attach" / "20.mp3"
            audio_path.parent.mkdir()
            audio_path.write_bytes(b"audio")
            manifest_path = root / "artifacts" / "20.slices.json"
            blocks = [
                MODULE.LearningBlock(id="S01", text="最近、冷えますね。", start=2.0, end=4.0, kind="manual")
            ]
            report = {
                "version": 1,
                "source": str(audio_path),
                "slices": [
                    {
                        "id": "S01",
                        "start": 1.85,
                        "end": 4.15,
                        "path": str(audio_path.parent / "20_S01.m4a"),
                        "status": "exported",
                    }
                ],
            }

            with mock.patch.object(MODULE, "listenkit_export_audio_slices_script_path", return_value=Path("/tmp/export.py")):
                with mock.patch.object(MODULE, "preflight_intensive_slice_tooling"):
                    with mock.patch.object(
                        MODULE.subprocess,
                        "run",
                        return_value=mock.Mock(returncode=0, stdout=json.dumps(report), stderr=""),
                    ) as run_mock:
                        profile = MODULE.SliceProfile("sentence", "sentence", "auto", "none", 0.5)
                        export_result = MODULE.export_learning_block_slices(audio_path, blocks, manifest_path, profile)
                        report_exists = export_result.report_path.exists()

        self.assertEqual(export_result.refs, ["attach/20_S01.m4a"])
        self.assertEqual(export_result.report_path, root / "artifacts" / "20.slice-export.json")
        self.assertTrue(report_exists)
        self.assertEqual(export_result.report["slice_profile"]["grouping"], "sentence")
        command = run_mock.call_args.args[0]
        self.assertIn("/tmp/export.py", command)
        self.assertIn("--manifest", command)
        self.assertIn(str(manifest_path), command)
        self.assertIn("--padding-seconds", command)
        self.assertIn("0.5", command)
        self.assertNotIn("--allow-overlap", command)
        self.assertIn("--overwrite", command)

    def test_numbered_dialogue_export_uses_exact_boundaries_without_path_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "neutral" / "Unit3" / "attach" / "21.mp3"
            audio_path.parent.mkdir(parents=True)
            audio_path.write_bytes(b"audio")
            manifest_path = audio_path.parent.parent / "artifacts" / "21.slices.json"
            manifest_path.parent.mkdir()
            blocks = [
                MODULE.LearningBlock(id="S09", text="すいません、待ちましたか？", start=91.14, end=100.62, kind="manual")
            ]
            report = {
                "version": 1,
                "source": str(audio_path),
                "slices": [
                    {
                        "id": "S09",
                        "start": 91.14,
                        "end": 100.62,
                        "path": str(audio_path.parent / "21_S09.m4a"),
                        "status": "exported",
                    }
                ],
            }

            with mock.patch.object(MODULE, "listenkit_export_audio_slices_script_path", return_value=Path("/tmp/export.py")):
                with mock.patch.object(MODULE, "preflight_intensive_slice_tooling"):
                    with mock.patch.object(
                        MODULE.subprocess,
                        "run",
                        return_value=mock.Mock(returncode=0, stdout=json.dumps(report), stderr=""),
                    ) as run_mock:
                        profile = MODULE.SliceProfile("dialogue", "numbered", "auto", "included", 0.0)
                        result = MODULE.export_learning_block_slices(audio_path, blocks, manifest_path, profile)

        command = run_mock.call_args.args[0]
        self.assertIn("--padding-seconds", command)
        self.assertIn("0.0", command)
        self.assertNotIn("--allow-overlap", command)
        self.assertEqual(result.report["slice_profile"]["grouping"], "numbered")

    def test_validate_intensive_slice_output_requires_real_nonempty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "attach" / "20.mp3"
            audio_path.parent.mkdir()
            audio_path.write_bytes(b"audio")
            body = "\n".join(["## 精听学习包", "", "### S01", "", "最近、冷えますね。", "", "![[attach/20_S01.m4a]]"])
            blocks = [
                MODULE.LearningBlock(id="S01", text="最近、冷えますね。", start=2.0, end=4.0, kind="manual")
            ]

            with self.assertRaisesRegex(RuntimeError, "missing or empty file"):
                MODULE.validate_intensive_slice_output(audio_path, blocks, ["attach/20_S01.m4a"], body)

            (audio_path.parent / "20_S01.m4a").write_bytes(b"slice")
            MODULE.validate_intensive_slice_output(audio_path, blocks, ["attach/20_S01.m4a"], body)

    def test_validate_intensive_slice_output_rejects_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "attach" / "20.mp3"
            audio_path.parent.mkdir()
            audio_path.write_bytes(b"audio")
            blocks = [
                MODULE.LearningBlock(id="S01", text="最近、冷えますね。", start=2.0, end=4.0, kind="manual")
            ]

            with self.assertRaisesRegex(RuntimeError, "still contains audio-slice placeholders"):
                MODULE.validate_intensive_slice_output(
                    audio_path,
                    blocks,
                    ["attach/20_S01.m4a"],
                    "## 精听学习包\n\n### S01\n\n最近、冷えますね。\n\n（语音切片待生成）",
                )

    def test_build_body_intensive_uses_learning_block_text(self) -> None:
        blocks = [
            MODULE.LearningBlock(
                id="S01",
                text="A：最近、冷えますね。\nB：本当に寒くなりましたね。",
                start=2.0,
                end=6.0,
                kind="numbered-dialogue",
            )
        ]
        body, _ = MODULE.build_body(
            "20 はじめまして",
            "attach/20.mp3",
            ["元の脚本です。"],
            [MODULE.Chunk(start=0.0, end=1.0, text="元の脚本です。")],
            Path("20.mp3"),
            offline_dictionary=MODULE.StaticAccentDictionary({}),
            audio_slice_refs=["attach/20_S01.m4a"],
            listening_mode="intensive",
            learning_blocks=blocks,
        )

        package = body.split("## 脚本", 1)[0]
        self.assertIn("A：最近、冷えますね。\nB：本当に寒くなりましたね。", package)
        self.assertNotIn("元の脚本です。", package)

    def test_process_one_preserves_intentionally_empty_common_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "manabo_cz21.mp3"
            audio_path.write_bytes(b"audio")
            note_path = root / "manabo_cz21_恵方巻きとうなぎとお菓子.md"
            note_path.write_text(
                "\n".join(
                    [
                        "---",
                        "track: listening",
                        "daily_use_sentences: []",
                        "transcript_status: full",
                        "transcript_ref: in-note",
                        "---",
                        "",
                        "# manabo_cz21 恵方巻きとうなぎとお菓子",
                        "",
                        "![[manabo_cz21.mp3]]",
                        "",
                        "## 脚本",
                        "",
                        "旧脚本です。",
                        "",
                        "## 可直接背的常用句",
                        "",
                        "",
                        "## 素材说明",
                        "",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            payload = {
                "full_text": "新しい脚本です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "新しい脚本です。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                MODULE.process_one(audio_path, None, "ja-JP", None, False)

            rendered = note_path.read_text(encoding="utf-8")
            self.assertNotIn(MODULE.COMMON_SECTION_PLACEHOLDER, rendered)
            common_block = rendered.split("## 可直接背的常用句", 1)[1].split("## 素材说明", 1)[0]
            self.assertEqual(common_block.strip(), "")

    def test_dry_run_does_not_rename_generated_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "manabo_cz20.mp3"
            audio_path.write_bytes(b"audio")
            placeholder_path = root / "manabo_cz20_识别稿.md"
            target_path = root / "manabo_cz20_1日の摂取カロリー.md"
            placeholder_path.write_text(
                "\n".join(
                    [
                        "---",
                        "track: listening",
                        "daily_use_sentences: []",
                        "transcript_status: partial",
                        "transcript_ref: in-note",
                        "---",
                        "",
                        "# manabo_cz20 识别稿",
                        "",
                        "![[manabo_cz20.mp3]]",
                        "",
                        "## 脚本",
                        "",
                        "旧脚本です。",
                        "",
                        "## 我的备注",
                        "",
                        "ここは残したいメモです。",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            payload = {
                "full_text": "摂取カロリーについて話しています。摂取カロリーは大切です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "摂取カロリーについて話しています。"},
                    {"start": 1.2, "end": 2.1, "text": "摂取カロリーは大切です。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                result = MODULE.process_one(audio_path, None, "ja-JP", None, True)

            self.assertTrue(placeholder_path.exists())
            self.assertFalse(target_path.exists())
            self.assertIn(str(target_path), result)
            self.assertIn("## 我的备注", result)
            self.assertIn("ここは残したいメモです。", result)

    def test_new_notes_infer_source_tag_from_audio_path(self) -> None:
        cases = [
            ("中級を学ぼう/manabo_cz99.mp3", "source/manabo"),
            ("ドリル＆ドリル　日本語能力試験Ｎ3/N3 A-5.mp3", "source/drill_n3"),
            ("実力アップ/29番-32番.mp3", "source/jitsuryoku_up"),
        ]

        for relative_path, expected_tag in cases:
            with self.subTest(relative_path=relative_path):
                frontmatter = MODULE.build_default_frontmatter(Path(relative_path), 1, False)
                self.assertIn(f"  - {expected_tag}", frontmatter)

    def test_dialogue_frontmatter_uses_dialogue_defaults(self) -> None:
        frontmatter = MODULE.build_default_frontmatter(Path("Shadowing_初中級/Unit1/04.mp3"), 4, False, True)
        self.assertIn("  - 对话轮替时容易把发言人和应答关系听反", frontmatter)
        self.assertIn("practice_focus: 先确认每轮是谁在问、谁在答，再抓场景里的高频问句和应答模板。", frontmatter)

    def test_conservative_dialogue_detection_marks_clear_qa(self) -> None:
        rendered = MODULE.render_conservative_ab_dialogue(
            ["駅までどのくらいですか？", "歩いて5分ぐらいです。"]
        )
        self.assertEqual(rendered, ["A：駅までどのくらいですか？", "B：歩いて5分ぐらいです。"])

    def test_conservative_dialogue_detection_rejects_monologue(self) -> None:
        rendered = MODULE.render_conservative_ab_dialogue(
            ["今日は良い天気ですね。", "朝から公園を散歩して、とても静かなたたずまいを楽しみました。"]
        )
        self.assertIsNone(rendered)

    def test_non_dialogue_script_keeps_plain_paragraphs(self) -> None:
        chunks = [
            MODULE.Chunk(start=0.0, end=1.0, text="今日は良い天気ですね。"),
            MODULE.Chunk(start=1.0, end=2.0, text="朝から公園を散歩して、とても静かなたたずまいを楽しみました。"),
        ]
        rendered, dialogue_mode = MODULE.render_dialogue_script_section(
            ["今日は良い天気ですね。", "朝から公園を散歩して、とても静かなたたずまいを楽しみました。"],
            chunks,
            MODULE.SliceProfile("sentence", "sentence", "auto", "none", 0.5),
        )
        self.assertFalse(dialogue_mode)
        self.assertNotIn("A：", rendered)

    def test_main_rejects_scan_dir_for_single_item_workflow(self) -> None:
        stderr = StringIO()
        with mock.patch.object(sys, "argv", ["transcribe-listening", "--scan-dir", "学习系统/听力"]):
            with mock.patch("sys.stderr", stderr):
                exit_code = MODULE.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Batch scan mode is not supported", stderr.getvalue())

    def test_main_fails_when_offline_dictionary_runtime_is_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "audio.mp3"
            audio_path.write_bytes(b"audio")
            stderr = StringIO()
            with mock.patch.object(
                MODULE.OfflineAccentDictionary,
                "validate_runtime",
                side_effect=MODULE.OfflineDictionaryError("Offline dictionary runtime validation failed"),
            ):
                with mock.patch.dict(os.environ, {"JP_LISTENING_DICT_DIR": str(root / "dict")}, clear=False):
                    with mock.patch.object(sys, "argv", ["transcribe-listening", str(audio_path), "--dry-run"]):
                        with mock.patch("sys.stderr", stderr):
                            exit_code = MODULE.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Offline dictionary runtime validation failed", stderr.getvalue())

    def test_auto_engine_uses_listenkit_default_for_numbered_dialogue(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_dir = root / "Shadowing_初中級" / "Unit1"
            audio_dir.mkdir(parents=True)
            audio_path = audio_dir / "04.mp3"
            audio_path.write_bytes(b"audio")
            payload = {
                "engine": "faster-whisper",
                "full_text": "",
                "segments": [
                    {"start": 0.0, "end": 3.0, "text": "セクション4"},
                    {"start": 3.0, "end": 5.0, "text": "1"},
                    {"start": 5.0, "end": 8.0, "text": "はじめまして、渡辺です。"},
                    {"start": 8.0, "end": 14.0, "text": "田中です。どうぞよろしく。"},
                    {"start": 54.8, "end": 55.3, "text": "2"},
                    {"start": 55.4, "end": 59.4, "text": "山田さんの部屋は何階ですか?"},
                    {"start": 59.4, "end": 63.4, "text": "三階です。"},
                    {"start": 70.0, "end": 70.3, "text": "3"},
                    {"start": 70.4, "end": 72.4, "text": "お国は?"},
                    {"start": 72.4, "end": 74.4, "text": "スペインです。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload) as invoke_mock:
                result = MODULE.process_one(
                    audio_path,
                    None,
                    "ja-JP",
                    "田中です",
                    True,
                    offline_dictionary=MODULE.StaticAccentDictionary(
                        {"渡辺": "わたなべ⓪", "田中": "たなか⓪", "山田": "やまだ⓪", "部屋": "へや②"}
                    ),
                )

            invoke_mock.assert_called_once()
            self.assertEqual(invoke_mock.call_args.args[2], "auto")
            self.assertIn("セクション4", result)
            self.assertIn("1\nA：はじめまして、渡辺⓪です。\nB：田中⓪です。どうぞよろしく。", result)
            self.assertIn("2\nA：山田⓪さんの部屋②は何階ですか？\nB：三階です。", result)
            self.assertIn("3\nA：お国は？\nB：スペインです。", result)
            self.assertIn(MODULE.FASTER_WHISPER_MATERIAL_NOTE, result)
            self.assertIn(MODULE.DIALOGUE_MATERIAL_NOTE_SUFFIX, result)

    def test_structural_normalization_does_not_apply_material_specific_word_rewrites(self) -> None:
        self.assertEqual(MODULE.normalize_structured_text("山田さんの部屋は何回ですか?"), "山田さんの部屋は何回ですか？")
        self.assertEqual(MODULE.normalize_structured_text("３回です。"), "3回です。")
        self.assertEqual(MODULE.normalize_structured_text("奥には?"), "奥には？")

    def test_default_invocation_uses_listenkit_generate_markdown(self) -> None:
        expected_payload = {
            "engine": "faster-whisper",
            "locale": "ja-JP",
            "language": "Japanese",
            "full_text": "ok",
            "segments": [],
            "timing_complete": True,
        }

        def fake_run(command, **kwargs):
            output_path = Path(command[command.index("--output") + 1])
            output_path.write_text("# transcript\n", encoding="utf-8")
            output_path.with_suffix(".json").write_text(json.dumps(expected_payload), encoding="utf-8")
            return mock.Mock(returncode=0, stdout=str(output_path), stderr="")

        with mock.patch.object(MODULE, "preflight_listenkit_generate_tooling"):
            with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run) as run_mock:
                payload = MODULE.invoke_listenkit(Path("/tmp/audio.mp3"), "ja-JP", "auto", {"FASTER_WHISPER_PYTHON": "/tmp/fw/bin/python"})

        command = run_mock.call_args.args[0]
        env = run_mock.call_args.kwargs["env"]
        self.assertIn("ListenKit/cli/generate-markdown.sh", command[1])
        self.assertIn("--input", command)
        self.assertIn("/tmp/audio.mp3", command)
        self.assertIn("--language", command)
        self.assertIn("Japanese", command)
        self.assertNotIn("--engine", command)
        self.assertNotIn("--auto-init", command)
        self.assertEqual(env["FASTER_WHISPER_PYTHON"], "/tmp/fw/bin/python")
        self.assertEqual(payload["engine"], "faster-whisper")

    def test_local_invocation_can_persist_listenkit_artifacts(self) -> None:
        expected_payload = {
            "engine": "faster-whisper",
            "locale": "ja-JP",
            "language": "Japanese",
            "full_text": "ok",
            "segments": [],
            "timing_complete": True,
        }

        def fake_run(command, **kwargs):
            output_path = Path(command[command.index("--output") + 1])
            output_path.write_text("# transcript\n", encoding="utf-8")
            output_path.with_suffix(".json").write_text(json.dumps(expected_payload), encoding="utf-8")
            return mock.Mock(returncode=0, stdout=str(output_path), stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "artifacts"
            with mock.patch.object(MODULE, "preflight_listenkit_generate_tooling"):
                with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
                    MODULE.invoke_listenkit(
                        Path("/tmp/audio.mp3"),
                        "ja-JP",
                        "auto",
                        artifact_dir=artifact_dir,
                        artifact_stem="audio",
                    )

            self.assertTrue((artifact_dir / "audio.faster-whisper.listenkit.md").exists())
            self.assertTrue((artifact_dir / "audio.faster-whisper.listenkit.json").exists())

    def test_intensive_preflight_requires_audio_and_export_tooling(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "attach" / "20.mp3"
            audio.parent.mkdir()
            audio.write_bytes(b"audio")
            listenkit_root = Path(tmpdir) / "ListenKit"
            cli = listenkit_root / "cli"
            cli.mkdir(parents=True)
            generate = cli / "generate-markdown.sh"
            generate.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            generate.chmod(0o755)

            with mock.patch.dict(MODULE.os.environ, {"LISTENKIT_ROOT": str(listenkit_root)}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "audio-slice export CLI"):
                    MODULE.preflight_listening_audio_chain(audio, intensive=True)

    def test_default_invocation_forces_huggingface_offline_when_small_model_is_cached(self) -> None:
        expected_payload = {
            "engine": "faster-whisper",
            "locale": "ja-JP",
            "language": "Japanese",
            "full_text": "ok",
            "segments": [],
            "timing_complete": True,
        }

        def fake_run(command, **kwargs):
            output_path = Path(command[command.index("--output") + 1])
            output_path.write_text("# transcript\n", encoding="utf-8")
            output_path.with_suffix(".json").write_text(json.dumps(expected_payload), encoding="utf-8")
            return mock.Mock(returncode=0, stdout=str(output_path), stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            hf_home = Path(tmpdir) / "hf"
            snapshot = hf_home / "hub" / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
            snapshot.mkdir(parents=True)
            (snapshot / "model.bin").write_bytes(b"cached")
            with mock.patch.dict(MODULE.os.environ, {"HF_HOME": str(hf_home)}, clear=True):
                with mock.patch.object(MODULE, "preflight_listenkit_generate_tooling"):
                    with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run) as run_mock:
                        MODULE.invoke_listenkit(Path("/tmp/audio.mp3"), "ja-JP", "auto")

        env = run_mock.call_args.kwargs["env"]
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertEqual(env["TRANSFORMERS_OFFLINE"], "1")

    def test_explicit_apple_invocation_uses_generate_markdown_override(self) -> None:
        expected_payload = {
            "engine": "apple",
            "locale": "ja-JP",
            "language": "Japanese",
            "full_text": "ok",
            "segments": [],
            "timing_complete": True,
        }

        def fake_run(command, **kwargs):
            output_path = Path(command[command.index("--output") + 1])
            output_path.write_text("# transcript\n", encoding="utf-8")
            output_path.with_suffix(".json").write_text(json.dumps(expected_payload), encoding="utf-8")
            return mock.Mock(returncode=0, stdout=str(output_path), stderr="")

        with mock.patch.dict(MODULE.os.environ, {"LISTENKIT_ROOT": "/tmp/listenkit"}, clear=True):
            with mock.patch.object(MODULE, "preflight_listenkit_generate_tooling"):
                with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run) as run_mock:
                    payload = MODULE.invoke_listenkit(Path("/tmp/audio.mp3"), "ja-JP", "apple")

        command = run_mock.call_args.args[0]
        self.assertEqual(command[1], "/tmp/listenkit/cli/generate-markdown.sh")
        self.assertIn("--engine", command)
        self.assertIn("apple", command)
        self.assertNotIn("--auto-init", command)
        self.assertEqual(payload["engine"], "apple")

    def test_url_requires_output_dir(self) -> None:
        stderr = StringIO()
        with mock.patch.object(sys, "argv", ["transcribe-listening", "--url", "https://example.com/a.mp4"]):
            with mock.patch("sys.stderr", stderr):
                exit_code = MODULE.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("--output-dir is required", stderr.getvalue())

    def test_url_input_generates_note_from_finalized_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_dir = root / "听力"
            expected_payload = {
                "engine": "faster-whisper",
                "locale": "ja-JP",
                "language": "Japanese",
                "full_text": "電話番号の読み方です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "電話番号の読み方です。"},
                ],
                "timing_complete": True,
            }

            def fake_run(command, **kwargs):
                output_path = Path(command[command.index("--output") + 1])
                output_path.write_text("# transcript\n", encoding="utf-8")
                output_path.with_suffix(".json").write_text(json.dumps(expected_payload), encoding="utf-8")
                audio_dir = output_path.parent / "audio"
                audio_dir.mkdir()
                audio_format = command[command.index("--format") + 1]
                (audio_dir / f"{output_path.stem}.{audio_format}").write_bytes(b"audio")
                return mock.Mock(returncode=0, stdout=str(output_path), stderr="")

            with mock.patch.object(MODULE, "preflight_listenkit_generate_tooling"):
                with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run) as run_mock:
                    result = MODULE.process_url(
                        "https://www.youtube.com/watch?v=abc123",
                        output_dir,
                        None,
                        "ja-JP",
                        "数字の読み方",
                        False,
                    )

            command = run_mock.call_args_list[0].args[0]
            self.assertIn("--url", command)
            self.assertIn("https://www.youtube.com/watch?v=abc123", command)
            final_audio = output_dir / "attach" / "youtube_abc123_4b91d82f.m4a"
            self.assertTrue(final_audio.exists())
            created_notes = list(output_dir.glob("youtube_abc123_4b91d82f_*.md"))
            self.assertEqual(len(created_notes), 1)
            rendered = created_notes[0].read_text(encoding="utf-8")
            self.assertIn("audio_ref: attach/youtube_abc123_4b91d82f.m4a", rendered)
            self.assertIn("![[attach/youtube_abc123_4b91d82f.m4a]]", rendered)
            self.assertIn("電話番号の読み方です。", rendered)
            self.assertIn("来源 URL：<https://www.youtube.com/watch?v=abc123>", rendered)
            self.assertIn("Source URL: https://www.youtube.com/watch?v=abc123", result)
            self.assertTrue((output_dir / "artifacts/youtube_abc123_4b91d82f.faster-whisper.listenkit.md").exists())
            self.assertTrue((output_dir / "artifacts/youtube_abc123_4b91d82f.faster-whisper.listenkit.json").exists())

    def test_audio_in_attach_generates_note_in_material_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            material_dir = root / "中級を学ぼう"
            attach_dir = material_dir / "attach"
            attach_dir.mkdir(parents=True)
            audio_path = attach_dir / "manabo_cz99.mp3"
            audio_path.write_bytes(b"audio")
            payload = {
                "full_text": "これは新しい素材です。",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "これは新しい素材です。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                result = MODULE.process_one(audio_path, None, "ja-JP", None, False)

            self.assertIn("Created", result)
            created_notes = list(material_dir.glob("manabo_cz99_*.md"))
            self.assertEqual(len(created_notes), 1)
            self.assertEqual(list(attach_dir.glob("*.md")), [])
            rendered = created_notes[0].read_text(encoding="utf-8")
            self.assertIn("audio_ref: attach/manabo_cz99.mp3", rendered)
            self.assertIn("![[attach/manabo_cz99.mp3]]", rendered)

    def test_existing_note_title_is_preserved_for_shadowing_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_dir = root / "Shadowing_初中級" / "Unit1"
            audio_dir.mkdir(parents=True)
            audio_path = audio_dir / "04.mp3"
            audio_path.write_bytes(b"audio")
            note_path = audio_dir / "04_田中です.md"
            note_path.write_text(
                "\n".join(
                    [
                        "---",
                        "track: listening",
                        "daily_use_sentences: []",
                        "transcript_status: full",
                        "transcript_ref: in-note",
                        "---",
                        "",
                        "# 04 田中です",
                        "",
                        "![[04.mp3]]",
                        "",
                        "## 脚本",
                        "",
                        "旧脚本です。",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            payload = {
                "full_text": "",
                "segments": [
                    {"start": 0.0, "end": 3.0, "text": "セクション4"},
                    {"start": 3.0, "end": 5.0, "text": "1"},
                    {"start": 5.0, "end": 8.0, "text": "ホットコーヒーのMひとつください。"},
                ],
            }

            with mock.patch.object(MODULE, "invoke_listenkit", return_value=payload):
                result = MODULE.process_one(audio_path, None, "ja-JP", None, True)

            self.assertIn("# 04 田中です", result)
            self.assertNotIn("# 04 ホットコーヒー", result)

    def test_shadowing_four_turn_exchange_is_rendered_as_abab(self) -> None:
        chunks = [
            MODULE.Chunk(start=0.0, end=1.0, text="セクション7"),
            MODULE.Chunk(start=1.0, end=2.0, text="7"),
            MODULE.Chunk(start=2.0, end=3.0, text="お名前は？"),
            MODULE.Chunk(start=3.0, end=4.0, text="ペドロです。"),
            MODULE.Chunk(start=4.0, end=5.0, text="お国は？"),
            MODULE.Chunk(start=5.0, end=6.0, text="スペインです。"),
        ]
        rendered, dialogue_mode = MODULE.render_dialogue_script_section(
            [],
            chunks,
            MODULE.SliceProfile("dialogue", "numbered", "auto", "included", 0.0),
        )
        self.assertTrue(dialogue_mode)
        self.assertIn("7\nA：お名前は？\nB：ペドロです。\nA：お国は？\nB：スペインです。", rendered)

    def test_setup_install_command_targets_selected_virtualenv(self) -> None:
        args = mock.Mock(python="/tmp/LingoTrace/.venv/bin/python")
        command = SETUP_MODULE.install_command(args)

        self.assertEqual(command[:4], [args.python, "-m", "pip", "install"])
        self.assertIn(str(REQUIREMENTS_PATH), command)
        self.assertNotIn("--target", command)

    def test_setup_offline_dictionary_rejects_non_virtualenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            runtime = {
                "executable": sys.executable,
                "version": "3.14.3",
                "cache_tag": "cpython-314",
                "in_venv": False,
                "prefix": "/opt/homebrew",
                "base_prefix": "/opt/homebrew",
            }
            with mock.patch.object(SETUP_MODULE, "python_runtime_info", return_value=runtime):
                ok, messages = SETUP_MODULE.check_runtime(cache_dir, sys.executable)

            self.assertFalse(ok)
            self.assertIn("virtual environment", "\n".join(messages))

    def test_setup_offline_dictionary_rejects_icloud_native_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            runtime = {
                "executable": "/Users/test/Library/Mobile Documents/vault/.venv/bin/python",
                "version": "3.14.3",
                "cache_tag": "cpython-314",
                "in_venv": True,
                "prefix": "/Users/test/Library/Mobile Documents/vault/.venv",
                "base_prefix": "/opt/homebrew",
            }
            with mock.patch.object(SETUP_MODULE, "python_runtime_info", return_value=runtime):
                with mock.patch.object(SETUP_MODULE, "import_from_runtime") as import_mock:
                    ok, messages = SETUP_MODULE.check_runtime(cache_dir, sys.executable)

            self.assertFalse(ok)
            self.assertIn("iCloud", "\n".join(messages))
            import_mock.assert_not_called()

    def test_setup_install_refuses_icloud_native_runtime_before_pip(self) -> None:
        runtime = {
            "executable": "/Users/test/Library/Mobile Documents/vault/.venv/bin/python",
            "version": "3.14.3",
            "cache_tag": "cpython-314",
            "in_venv": True,
            "prefix": "/Users/test/Library/Mobile Documents/vault/.venv",
            "base_prefix": "/opt/homebrew",
        }
        stderr = StringIO()
        with mock.patch.object(SETUP_MODULE, "python_runtime_info", return_value=runtime):
            with mock.patch.object(SETUP_MODULE.subprocess, "run") as run_mock:
                with mock.patch.object(sys, "argv", ["setup-offline-dictionary", "--install"]):
                    with mock.patch("sys.stderr", stderr):
                        exit_code = SETUP_MODULE.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("iCloud", stderr.getvalue())
        run_mock.assert_not_called()

    def test_setup_offline_dictionary_rejects_missing_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            runtime = {
                "executable": sys.executable,
                "version": "3.14.3",
                "cache_tag": "cpython-314",
                "in_venv": True,
                "prefix": "/tmp/LingoTrace/.venv",
                "base_prefix": "/opt/homebrew",
            }
            with mock.patch.object(SETUP_MODULE, "python_runtime_info", return_value=runtime):
                with mock.patch.object(SETUP_MODULE, "import_from_runtime", return_value=(False, "packages are not ready")):
                    ok, messages = SETUP_MODULE.check_runtime(cache_dir, sys.executable)

            self.assertFalse(ok)
            self.assertIn("not ready", "\n".join(messages))

    def test_setup_offline_dictionary_rejects_broken_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            runtime = {
                "executable": sys.executable,
                "version": "3.14.3",
                "cache_tag": "cpython-314",
                "in_venv": True,
                "prefix": "/tmp/LingoTrace/.venv",
                "base_prefix": "/opt/homebrew",
            }
            with mock.patch.object(SETUP_MODULE, "python_runtime_info", return_value=runtime):
                with mock.patch.object(
                    SETUP_MODULE,
                    "import_from_runtime",
                    return_value=(False, "Python dictionary packages are not ready: dlopen failed"),
                ):
                    ok, messages = SETUP_MODULE.check_runtime(cache_dir, sys.executable)

            self.assertFalse(ok)
            rendered = "\n".join(messages)
            self.assertIn("not ready", rendered)
            self.assertIn("dlopen failed", rendered)

    def test_listenkit_json_accepts_schema_v1_and_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name, payload in (
                ("v1.json", {"schema_version": 1, "segments": []}),
                ("legacy.json", {"segments": []}),
            ):
                path = root / name
                path.write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual(MODULE.load_listenkit_json(path), payload)

    def test_listenkit_json_rejects_unknown_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "future.json"
            path.write_text(json.dumps({"schema_version": 2, "segments": []}), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "unsupported schema_version: 2"):
                MODULE.load_listenkit_json(path)


if __name__ == "__main__":
    unittest.main()
