#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlparse
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

COMMON_SECTION_PLACEHOLDER = (
    "二阶段待编辑：请基于完整脚本，用大模型或人工判断，挑选 0-5 句真正值得背、可迁移的表达；宁缺勿滥。\n\n"
    "- 原句：\n"
    "  可替换骨架：\n"
    "  使用场景：\n"
    "  选入理由：\n\n"
    "不要添加中文翻译字段。完成后同步更新 frontmatter 的 `daily_use_sentences`，只放日文原句或核心句。"
)
DEFAULT_MATERIAL_NOTE = "这条音频由 ListenKit 自动生成转写稿。建议人工复核题号、教材抬头、专有名词和少量长句切分，再决定是否继续精修。"
SHORT_CHOICE_MATERIAL_NOTE = "这条音频按短句应答题模式处理：脚本会优先保留题号与选项结构，必要时自动尝试慢速副本重转。仍建议人工顺耳确认题干与错误选项。"
FASTER_WHISPER_MATERIAL_NOTE = "这条音频由 ListenKit 的 faster-whisper 路线自动转写生成。仍需人工复核同音词、姓名、楼层等上下文词。"
DEFAULT_FASTER_WHISPER_MODEL = "small"
DEFAULT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
DIALOGUE_MATERIAL_NOTE_SUFFIX = "本稿按对话型精听内容整理；仅在文本呈现出明显问答或应答轮替时，保守标注 A：/B：。"
LISTENING_MODES = {"intensive", "extensive"}

QUESTION_CUES = (
    "ですか",
    "ますか",
    "何",
    "どこ",
    "どちら",
    "どのくらい",
    "どんな",
    "どう",
    "いかが",
    "いつ",
    "誰",
    "だれ",
    "何時",
    "何日",
    "何曜日",
    "何年",
    "何階",
)
REQUEST_OR_OFFER_CUES = ("ください", "どうぞ", "いかが", "大丈夫ですか", "ましょうか", "お願いします")
GREETING_CUES = ("はじめまして", "よろしく", "どうぞよろしく", "失礼します", "じゃ、また", "いただきます")
RESPONSE_CUES = (
    "はい",
    "いいえ",
    "ええ",
    "あ、",
    "ああ",
    "そうです",
    "そうですね",
    "そうですか",
    "どうも",
    "ありがとうございます",
    "すみません",
    "お願いします",
    "いただきます",
    "わかりました",
)


@dataclass
class Chunk:
    start: float | None
    end: float | None
    text: str


@dataclass
class TranscriptionCandidate:
    payload: dict
    segments: list[Chunk]
    sentences: list[str]
    full_text: str
    score: int
    route_label: str


@dataclass
class ScriptBlock:
    kind: str
    label: str | None = None
    utterances: list[str] | None = None
    text: str | None = None


class OfflineDictionaryError(RuntimeError):
    pass


CIRCLED_ACCENT_MARKS = "⓪①②③④⑤⑥⑦⑧⑨"
ACCENT_TYPE_TO_MARK = {str(index): mark for index, mark in enumerate(CIRCLED_ACCENT_MARKS)}
KANJI_CHAR_RE = re.compile(r"[\u3400-\u9fff々〆ヵヶ]")


def accent_marks_from_type(value: str) -> str | None:
    marks = [
        ACCENT_TYPE_TO_MARK[item]
        for item in re.findall(r"\d+", value or "")
        if item in ACCENT_TYPE_TO_MARK
    ]
    if not marks:
        return None
    return "/".join(dedupe_preserve_order(marks))


def term_replacement_pattern(term: str) -> str:
    prefix = r"(?<![\u3400-\u9fff々〆ヵヶ])" if KANJI_CHAR_RE.match(term[0]) else ""
    suffix = r"(?![\u3400-\u9fff々〆ヵヶ⓪①②③④⑤⑥⑦⑧⑨])" if KANJI_CHAR_RE.match(term[-1]) else rf"(?![{CIRCLED_ACCENT_MARKS}])"
    return prefix + re.escape(term) + suffix


def is_inflected_content_fragment(feature) -> bool:
    pos1 = str(getattr(feature, "pos1", "") or "")
    if pos1 not in {"動詞", "形容詞"}:
        return False
    form = str(getattr(feature, "cForm", "") or "")
    return form not in {"終止形-一般", "連体形-一般"}


class StaticAccentDictionary:
    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self.entries = entries or {}

    def lookup(self, term: str) -> str | None:
        return self.entries.get(term)

    def known_terms(self) -> list[str]:
        return sorted(self.entries, key=lambda item: (-len(item), item))

    def tokenize_terms(self, sentence: str) -> list[str]:
        return []


class OfflineAccentDictionary(StaticAccentDictionary):
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        entries = load_static_accent_entries(cache_dir)
        super().__init__(entries)
        self._tagger = None
        self._tagger_error: Exception | None = None
        self._lookup_cache: dict[str, str | None] = {}

    def lookup(self, term: str) -> str | None:
        static_entry = super().lookup(term)
        if static_entry:
            return static_entry
        if term in self._lookup_cache:
            return self._lookup_cache[term]
        value = self._lookup_unidic_accent(term)
        self._lookup_cache[term] = value
        return value

    def _load_tagger(self):
        if self._tagger is not None or self._tagger_error is not None:
            return self._tagger
        python_dir = self.cache_dir / "python"
        if python_dir.exists():
            sys.path.insert(0, str(python_dir))
        try:
            import fugashi  # type: ignore
            import unidic_lite  # type: ignore

            self._tagger = fugashi.Tagger(f"-d {unidic_lite.DICDIR}")
        except Exception as exc:  # pragma: no cover - depends on optional local packages
            self._tagger_error = exc
            self._tagger = None
        return self._tagger

    def tokenize_terms(self, sentence: str) -> list[str]:
        tagger = self._load_tagger()
        if tagger is None:
            return []
        terms: list[str] = []
        for word in tagger(sentence):
            surface = str(word.surface).strip()
            if is_focus_term(surface) and not is_inflected_content_fragment(word.feature):
                terms.append(surface)
        return dedupe_preserve_order(terms)

    def _lookup_unidic_accent(self, term: str) -> str | None:
        tagger = self._load_tagger()
        if tagger is None:
            return None
        words = list(tagger(term))
        if len(words) != 1:
            return None
        word = words[0]
        feature = word.feature
        known_forms = {
            str(getattr(word, "surface", "") or ""),
            str(getattr(feature, "lemma", "") or ""),
            str(getattr(feature, "orth", "") or ""),
            str(getattr(feature, "orthBase", "") or ""),
        }
        if term not in known_forms:
            return None
        if is_inflected_content_fragment(feature):
            return None
        marks = accent_marks_from_type(str(getattr(feature, "aType", "") or ""))
        if not marks:
            return None
        reading = (
            str(getattr(feature, "kana", "") or "")
            or str(getattr(feature, "kanaBase", "") or "")
            or str(getattr(feature, "pron", "") or "")
            or term
        )
        return f"{reading}{marks}"


def default_dictionary_cache_dir() -> Path:
    override = os.environ.get("JP_LISTENING_DICT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Caches" / "jp-listening-dicts"


def load_static_accent_entries(cache_dir: Path) -> dict[str, str]:
    path = cache_dir / "accent_map.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise OfflineDictionaryError(f"Offline dictionary accent map must be a JSON object: {path}")
    return {str(key): str(value) for key, value in payload.items() if str(key).strip() and str(value).strip()}


def offline_dictionary_ready(cache_dir: Path) -> bool:
    return (cache_dir / "accent_map.json").exists() or (cache_dir / "python").exists()


def load_offline_dictionary(required: bool = True) -> StaticAccentDictionary:
    cache_dir = default_dictionary_cache_dir()
    if not offline_dictionary_ready(cache_dir):
        if required:
            raise OfflineDictionaryError(
                "Offline dictionary is not ready. Run "
                "`python3 tools/listening-transcribe-official/setup_offline_dictionary.py --install` "
                f"or set JP_LISTENING_DICT_DIR to a prepared cache. Checked: {cache_dir}"
            )
        return StaticAccentDictionary({})
    return OfflineAccentDictionary(cache_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="transcribe-listening",
        description="Generate a Japanese listening Markdown note from ListenKit transcript artifacts.",
    )
    parser.add_argument("audio_path", nargs="?")
    parser.add_argument("--url")
    parser.add_argument("--output-dir")
    parser.add_argument("--note-path")
    parser.add_argument("--locale", default="ja-JP")
    parser.add_argument("--title")
    parser.add_argument("--engine", choices=["auto", "apple", "faster-whisper"], default="auto")
    parser.add_argument("--format", choices=["mp3", "m4a", "wav", "flac"], default="m4a")
    parser.add_argument("--faster-whisper-python")
    parser.add_argument("--faster-whisper-model", default=DEFAULT_FASTER_WHISPER_MODEL)
    parser.add_argument("--faster-whisper-compute-type", default=DEFAULT_FASTER_WHISPER_COMPUTE_TYPE)
    parser.add_argument("--listening-mode", choices=sorted(LISTENING_MODES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scan-dir")
    return parser.parse_args()


def listenkit_root() -> Path:
    override = os.environ.get("LISTENKIT_ROOT")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[3] / "ListenKit"


def listenkit_generate_markdown_script_path() -> Path:
    return listenkit_root() / "cli" / "generate-markdown.sh"


def slugify_stem(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("._") or "listenkit_source"


def infer_stem_from_url(url: str, forced_title: str | None = None) -> str:
    if forced_title:
        return slugify_stem(forced_title)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if parsed.netloc.endswith("youtu.be") and parsed.path.strip("/"):
        base = parsed.path.strip("/").split("/")[0]
    elif "youtube" in parsed.netloc and query.get("v"):
        base = f"youtube_{query['v'][0]}"
    else:
        path_name = Path(parsed.path).stem if parsed.path else ""
        base = path_name or parsed.netloc or "listenkit_source"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return slugify_stem(f"{base}_{digest}")


def language_label_for_locale(locale: str) -> str:
    normalized = locale.lower()
    if normalized.startswith("ja"):
        return "Japanese"
    if normalized.startswith("en"):
        return "English"
    if normalized.startswith("zh"):
        return "Chinese"
    if normalized.startswith("ko"):
        return "Korean"
    return locale


def huggingface_hub_cache_dir() -> Path:
    explicit_cache = os.environ.get("HF_HUB_CACHE")
    if explicit_cache:
        return Path(explicit_cache).expanduser()
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        return Path(hf_home).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def faster_whisper_model_is_cached(model: str) -> bool:
    cache_name = f"models--Systran--faster-whisper-{model}"
    model_root = huggingface_hub_cache_dir() / cache_name / "snapshots"
    if not model_root.exists():
        return False
    return any(path.is_file() for path in model_root.glob("*/model.bin"))


def apply_cached_faster_whisper_offline_env(env: dict[str, str], engine: str) -> None:
    if engine == "apple":
        return
    if not faster_whisper_model_is_cached(DEFAULT_FASTER_WHISPER_MODEL):
        return
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")


def load_listenkit_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ListenKit transcript JSON is invalid: {path}: {exc}") from exc
    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            raise RuntimeError(f'{error.get("type", "error")}: {error.get("message", "ListenKit transcription failed.")}')
        raise RuntimeError(str(error))
    return payload


def invoke_listenkit(
    source: Path | str,
    locale: str,
    engine: str = "auto",
    env_overrides: dict[str, str] | None = None,
    source_kind: str = "input",
    output_stem: str | None = None,
    output_dir: Path | None = None,
    audio_format: str = "m4a",
) -> dict:
    script_path = listenkit_generate_markdown_script_path()
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    apply_cached_faster_whisper_offline_env(env, engine)
    with tempfile.TemporaryDirectory(prefix="listenkit-transcript-") as tmpdir:
        if output_stem is None:
            output_stem = source.stem if isinstance(source, Path) else infer_stem_from_url(source)
        output_path = Path(tmpdir) / f"{output_stem}.md"
        command = [
            "/bin/bash",
            str(script_path),
            f"--{source_kind}",
            str(source),
            "--language",
            language_label_for_locale(locale),
            "--locale",
            locale,
            "--output",
            str(output_path),
            "--format",
            audio_format,
        ]
        if engine != "auto":
            command.extend(["--engine", engine])
        if engine != "apple":
            command.append("--auto-init")
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "ListenKit transcript generation failed."
            raise RuntimeError(stderr)
        transcript_json = output_path.with_suffix(".json")
        if not transcript_json.exists():
            raise RuntimeError(f"ListenKit did not create expected transcript JSON: {transcript_json}")
        payload = load_listenkit_json(transcript_json)
        if output_dir is not None:
            imported_audio = output_path.parent / "audio" / f"{output_path.stem}.{audio_format}"
            if not imported_audio.exists():
                raise RuntimeError(f"ListenKit did not create expected audio file: {imported_audio}")
            attach_dir = output_dir / "attach"
            artifact_dir = output_dir / "artifacts"
            attach_dir.mkdir(parents=True, exist_ok=True)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            final_audio = attach_dir / imported_audio.name
            if imported_audio.resolve() != final_audio.resolve():
                shutil.move(str(imported_audio), final_audio)
            shutil.move(str(output_path), artifact_dir / f"{output_path.stem}.listenkit.md")
            shutil.move(str(transcript_json), artifact_dir / f"{output_path.stem}.listenkit.json")
            payload["_listenkit_final_audio_path"] = str(final_audio)
        return payload


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "ffmpeg failed."
        raise RuntimeError(stderr)


def material_dir_for_audio(audio_path: Path) -> Path:
    if audio_path.parent.name == "attach":
        return audio_path.parent.parent
    return audio_path.parent


def audio_ref_for_note(audio_path: Path) -> str:
    if audio_path.parent.name == "attach":
        return f"attach/{audio_path.name}"
    return audio_path.name


def resolve_note_path(audio_path: Path, note_override: str | None) -> Path | None:
    if note_override:
        return Path(note_override)

    candidates = sorted(material_dir_for_audio(audio_path).glob(f"{audio_path.stem}_*.md"))
    for candidate in candidates:
        if "_无文本待补.md" in candidate.name:
            return candidate
    if len(candidates) == 1:
        return candidates[0]
    return None


def parse_frontmatter(note_text: str) -> tuple[list[str], str]:
    lines = note_text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Missing frontmatter start delimiter.")
    try:
        end_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("Missing frontmatter end delimiter.") from exc
    return lines[1:end_index], "\n".join(lines[end_index + 1 :]).strip()


def set_scalar(lines: list[str], key: str, value: str) -> None:
    target = f"{key}:"
    for idx, line in enumerate(lines):
        if line.startswith(target):
            lines[idx] = f"{key}: {value}"
            return
    lines.append(f"{key}: {value}")


def set_list(lines: list[str], key: str, values: list[str]) -> None:
    target = f"{key}:"
    block = [target] + [f"  - {quote_if_needed(value)}" for value in values]
    for idx, line in enumerate(lines):
        if line.startswith(target):
            end = idx + 1
            while end < len(lines):
                current = lines[end]
                if current.startswith("  - ") or current.strip() == "" or current[:1] in {" ", "\t"}:
                    end += 1
                    continue
                break
            lines[idx:end] = block
            return
    lines.extend(block)


def has_key(lines: list[str], key: str) -> bool:
    target = f"{key}:"
    return any(line.startswith(target) for line in lines)


def quote_if_needed(value: str) -> str:
    if not value:
        return '""'
    if any(token in value for token in [":", "[", "]", '"']):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def clean_transcript_text(text: str) -> str:
    cleaned = text.replace("。 ", "。").replace("？ ", "？").replace("！ ", "！")
    cleaned = cleaned.replace("  ", " ")
    cleaned = re.sub(r"^第\s*[0-9一二三四五六七八九十]+\s*課本文[^。！？?]*[。！？?]\s*", "", cleaned)
    cleaned = re.sub(r"^(紹介|聴解)タスクシート質問\s*", "", cleaned)
    cleaned = re.sub(r"^\d+-\d+聞こう[。]?\s*", "", cleaned)
    cleaned = re.sub(r"^\d+番", "", cleaned)
    cleaned = cleaned.replace("懲戒タスクシート", "聴解タスクシート")
    cleaned = cleaned.replace("入り口", "入口")
    cleaned = cleaned.replace("侵入止め", "進入止め")
    cleaned = cleaned.replace("作られています", "造られています")
    cleaned = cleaned.replace("小さい方", "小さいほう")
    cleaned = cleaned.replace("大きい池より", "大きい池より")
    cleaned = cleaned.replace("静かな佇まい", "静かなたたずまい")
    cleaned = cleaned.replace("なんだか", "何だか")
    cleaned = cleaned.replace("朝よく行きます", "朝、よく行きます")
    cleaned = cleaned.replace("すご。ごしやすく", "過ごしやすく")
    cleaned = cleaned.replace("土曜の丑の日", "土用の丑の日")
    cleaned = cleaned.replace("土曜の牛の日", "土用の丑の日")
    cleaned = cleaned.replace("\n", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned.strip()


def is_short_choice_mode(audio_path: Path) -> bool:
    stem = audio_path.stem
    return (
        "実力アップ" in audio_path.as_posix()
        or bool(re.search(r"\d+番-\d+番", stem))
        or bool(re.fullmatch(r"\d+番", stem))
    )


def is_shadowing_path(audio_path: Path) -> bool:
    return "Shadowing" in audio_path.as_posix() or "シャドーイング" in audio_path.as_posix()


def normalize_shadowing_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("?", "？").replace("!", "！")
    cleaned = cleaned.replace("．", ".")
    cleaned = re.sub(r"\s+", "", cleaned)
    replacements = {
        "セクション４": "セクション4",
        "セクション 4": "セクション4",
        "何回ですか": "何階ですか",
        "3回です": "三階です",
        "３回です": "三階です",
        "奥には": "お国は",
        "わたなべ": "渡辺",
        "たなか": "田中",
        "なかた": "中田",
    }
    for before, after in replacements.items():
        cleaned = cleaned.replace(before, after)
    return cleaned


def normalize_payload_for_shadowing(payload: dict) -> dict:
    normalized = dict(payload)
    raw_segments = payload.get("segments", [])
    normalized_segments = []
    for segment in raw_segments:
        item = dict(segment)
        item["text"] = normalize_shadowing_text(str(segment.get("text", "")))
        normalized_segments.append(item)
    normalized["segments"] = normalized_segments
    normalized["full_text"] = "\n".join(
        str(segment.get("text", "")).strip() for segment in normalized_segments if str(segment.get("text", "")).strip()
    )
    return normalized


def raw_segments_to_chunks(raw_segments: Iterable[dict]) -> list[Chunk]:
    return [
        Chunk(
            start=segment.get("start"),
            end=segment.get("end"),
            text=str(segment.get("text", "")).strip(),
        )
        for segment in raw_segments
        if str(segment.get("text", "")).strip()
    ]


def merge_chunks(raw_segments: Iterable[dict]) -> list[Chunk]:
    chunks = [
        Chunk(
            start=segment.get("start"),
            end=segment.get("end"),
            text=str(segment.get("text", "")).strip(),
        )
        for segment in raw_segments
        if str(segment.get("text", "")).strip()
    ]
    merged: list[Chunk] = []
    buffer_text: list[str] = []
    buffer_start: float | None = None
    buffer_end: float | None = None

    def flush() -> None:
        nonlocal buffer_text, buffer_start, buffer_end
        if not buffer_text:
            return
        text = "".join(buffer_text).strip()
        if text:
            merged.append(Chunk(start=buffer_start, end=buffer_end, text=text))
        buffer_text = []
        buffer_start = None
        buffer_end = None

    for chunk in chunks:
        if buffer_start is None:
            buffer_start = chunk.start
        if buffer_end is not None and chunk.start is not None and chunk.start - buffer_end > 1.0:
            flush()
            buffer_start = chunk.start

        buffer_text.append(chunk.text)
        buffer_end = chunk.end

        if chunk.text in {"。", "！", "？"}:
            flush()

    flush()
    return merged


def chunks_to_sentences(chunks: Iterable[Chunk]) -> list[str]:
    text = "".join(chunk.text for chunk in chunks).strip()
    text = clean_transcript_text(text)
    raw = re.split(r"(?<=[。！？?])", text)
    sentences = [item.strip() for item in raw if item.strip()]
    deduped: list[str] = []
    for sentence in sentences:
        if not deduped or deduped[-1] != sentence:
            deduped.append(sentence)
    merged: list[str] = []
    for sentence in deduped:
        if (
            merged
            and len(sentence.replace("。", "").replace("？", "").replace("！", "").strip()) <= 4
            and re.search(r"[がをにではともへ]。$", merged[-1])
        ):
            merged[-1] = merged[-1][:-1] + sentence
            continue
        merged.append(sentence)
    return merged


def chunks_to_shadowing_lines(chunks: Iterable[Chunk]) -> list[str]:
    lines: list[str] = []
    pending_number: str | None = None

    def append_text(text: str) -> None:
        nonlocal pending_number
        if pending_number is not None:
            lines.append(f"{pending_number} {text}")
            pending_number = None
            return
        if lines and re.match(r"^\d+\s", lines[-1]):
            lines[-1] += text
            return
        lines.append(text)

    for chunk in chunks:
        text = normalize_shadowing_text(chunk.text)
        if not text:
            continue
        if re.fullmatch(r"\d+", text):
            pending_number = text
            continue
        numbered = re.match(r"^(\d+)[.。]\s*(.+)$", text)
        if numbered:
            pending_number = numbered.group(1)
            append_text(numbered.group(2))
            continue
        if text.startswith("セクション"):
            lines.append(text)
            continue
        append_text(text)

    if pending_number is not None:
        lines.append(pending_number)
    return lines


def is_brief_utterance(text: str) -> bool:
    content = re.sub(r"[。！？?、，,\s]", "", text)
    return 1 <= len(content) <= 28


def is_question_like(text: str) -> bool:
    return text.endswith("？") or any(cue in text for cue in QUESTION_CUES)


def is_request_or_offer_like(text: str) -> bool:
    return any(cue in text for cue in REQUEST_OR_OFFER_CUES)


def is_greeting_like(text: str) -> bool:
    return any(cue in text for cue in GREETING_CUES)


def is_response_like(text: str) -> bool:
    return any(cue in text for cue in RESPONSE_CUES)


def is_conservative_dialogue_pair(left: str, right: str) -> bool:
    if not (is_brief_utterance(left) and is_brief_utterance(right)):
        return False

    score = 0
    if is_question_like(left) and not is_question_like(right):
        score += 2
    if is_request_or_offer_like(left) and is_response_like(right):
        score += 2
    if is_greeting_like(left) and (is_greeting_like(right) or is_response_like(right)):
        score += 2
    if is_response_like(right):
        score += 1

    if score >= 2:
        return True

    if left.endswith("。") and right.endswith("。") and "です" in left and "です" in right:
        if is_greeting_like(left) or is_greeting_like(right):
            return True
    return False


def render_conservative_ab_dialogue(utterances: list[str]) -> list[str] | None:
    cleaned = [item.strip() for item in utterances if item and item.strip()]
    if len(cleaned) not in {2, 4}:
        return None
    if any(not is_brief_utterance(item) for item in cleaned):
        return None

    for idx in range(0, len(cleaned), 2):
        if not is_conservative_dialogue_pair(cleaned[idx], cleaned[idx + 1]):
            return None

    rendered: list[str] = []
    for idx, utterance in enumerate(cleaned):
        speaker = "A" if idx % 2 == 0 else "B"
        rendered.append(f"{speaker}：{utterance}")
    return rendered


def chunks_to_structured_blocks(chunks: Iterable[Chunk]) -> list[ScriptBlock]:
    blocks: list[ScriptBlock] = []
    pending_number: str | None = None
    pending_utterances: list[str] = []

    def flush_numbered() -> None:
        nonlocal pending_number, pending_utterances
        if pending_number is not None:
            blocks.append(ScriptBlock(kind="numbered", label=pending_number, utterances=pending_utterances.copy()))
        elif pending_utterances:
            blocks.append(ScriptBlock(kind="plain", utterances=pending_utterances.copy()))
        pending_number = None
        pending_utterances = []

    for chunk in chunks:
        text = normalize_shadowing_text(chunk.text)
        if not text:
            continue
        if text.startswith("セクション"):
            flush_numbered()
            blocks.append(ScriptBlock(kind="section", text=text))
            continue
        numbered = re.match(r"^(\d+)[.。]\s*(.+)$", text)
        if re.fullmatch(r"\d+", text):
            flush_numbered()
            pending_number = text
            continue
        if numbered:
            flush_numbered()
            pending_number = numbered.group(1)
            pending_utterances = [numbered.group(2)]
            continue
        if pending_number is not None:
            pending_utterances.append(text)
        else:
            blocks.append(ScriptBlock(kind="plain", utterances=[text]))

    flush_numbered()
    return blocks


def render_dialogue_script_section(sentences: list[str], chunks: list[Chunk], structured_mode: bool) -> tuple[str, bool]:
    if structured_mode:
        rendered_blocks: list[str] = []
        dialogue_detected = False
        for block in chunks_to_structured_blocks(chunks):
            if block.kind == "section":
                rendered_blocks.append(block.text or "")
                continue
            if block.kind == "numbered":
                lines = [block.label or ""]
                rendered_dialogue = render_conservative_ab_dialogue(block.utterances or [])
                if rendered_dialogue is not None:
                    lines.extend(rendered_dialogue)
                    dialogue_detected = True
                else:
                    lines.extend(block.utterances or [])
                rendered_blocks.append("\n".join(line for line in lines if line))
                continue
            rendered_dialogue = render_conservative_ab_dialogue(block.utterances or [])
            if rendered_dialogue is not None:
                rendered_blocks.append("\n".join(rendered_dialogue))
                dialogue_detected = True
            else:
                rendered_blocks.append("\n".join(block.utterances or []))

        return "\n\n".join(block for block in rendered_blocks if block).strip(), dialogue_detected

    rendered_dialogue = render_conservative_ab_dialogue(sentences)
    if rendered_dialogue is not None:
        return "\n".join(rendered_dialogue), True

    paragraphs = group_paragraphs(sentences)
    script_section = "\n\n".join(paragraphs) if paragraphs else "当前未能生成稳定脚本，请检查音频或模型环境。"
    return script_section, False


def count_question_numbers(text: str) -> int:
    return len(set(re.findall(r"(\d+)番", text)))


def count_option_markers(text: str) -> int:
    return len(re.findall(r"(?<!\d)([123])(?=[^\d])", text))


def score_short_choice_candidate(full_text: str, sentences: list[str], audio_path: Path) -> int:
    score = 0
    score += count_question_numbers(full_text) * 8
    score += count_option_markers(full_text) * 3
    score += sum(1 for sentence in sentences if re.search(r"\d+番", sentence)) * 5
    score += sum(1 for sentence in sentences if re.search(r"(?<!\d)[123](?=[^\d])", sentence)) * 2
    if "何と言いますか" in full_text:
        score += 6
    if "お邪魔しています" in full_text:
        score += 2
    if "行ってまいります" in full_text:
        score += 2
    if audio_path.stem in full_text:
        score -= 2
    return score


def split_sentences_from_text(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[。！？?])", text) if segment.strip()]


def choose_short_choice_script(generated_script: str, existing_script: str | None, audio_path: Path) -> str:
    if not existing_script:
        return generated_script

    generated_clean = clean_transcript_text(generated_script)
    existing_clean = clean_transcript_text(existing_script)
    generated_score = score_short_choice_candidate(
        generated_clean,
        split_sentences_from_text(generated_clean),
        audio_path,
    )
    existing_score = score_short_choice_candidate(
        existing_clean,
        split_sentences_from_text(existing_clean),
        audio_path,
    )
    if existing_score >= generated_score:
        return existing_script
    return generated_script


def build_candidate(
    audio_path: Path,
    locale: str,
    route_label: str,
    engine: str = "auto",
    faster_whisper_python: str | None = None,
    faster_whisper_model: str = DEFAULT_FASTER_WHISPER_MODEL,
    faster_whisper_compute_type: str = DEFAULT_FASTER_WHISPER_COMPUTE_TYPE,
) -> TranscriptionCandidate:
    env_overrides = {}
    if faster_whisper_python:
        env_overrides["FASTER_WHISPER_PYTHON"] = str(Path(faster_whisper_python).expanduser())
    payload = invoke_listenkit(audio_path, locale, engine, env_overrides or None)
    return candidate_from_payload(audio_path, payload, route_label)


def candidate_from_payload(audio_path: Path, payload: dict, route_label: str) -> TranscriptionCandidate:
    if is_shadowing_path(audio_path):
        payload = normalize_payload_for_shadowing(payload)

    if str(payload.get("engine", "")) == "apple" and not is_shadowing_path(audio_path):
        segments = merge_chunks(payload.get("segments", []))
    else:
        segments = raw_segments_to_chunks(payload.get("segments", []))

    if is_shadowing_path(audio_path):
        sentences = chunks_to_shadowing_lines(segments)
        full_text = "\n".join(sentences)
    else:
        full_text = clean_transcript_text(str(payload.get("full_text", "")))
        sentences = chunks_to_sentences(segments)
    if not sentences and full_text:
        sentences = [segment.strip() for segment in re.split(r"(?<=[。！？?])", full_text) if segment.strip()]
    return TranscriptionCandidate(
        payload=payload,
        segments=segments,
        sentences=sentences,
        full_text=full_text,
        score=score_short_choice_candidate(full_text, sentences, audio_path),
        route_label=route_label,
    )


def build_slow_copy(audio_path: Path) -> Path:
    suffix = audio_path.suffix or ".mp3"
    handle, temp_path = tempfile.mkstemp(prefix=f"{audio_path.stem}_slow_", suffix=suffix)
    os.close(handle)
    slow_path = Path(temp_path)
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-filter:a",
            "atempo=0.85",
            str(slow_path),
        ]
    )
    return slow_path


def transcribe_with_heuristics(
    audio_path: Path,
    locale: str,
    engine: str = "auto",
    faster_whisper_python: str | None = None,
    faster_whisper_model: str = DEFAULT_FASTER_WHISPER_MODEL,
    faster_whisper_compute_type: str = DEFAULT_FASTER_WHISPER_COMPUTE_TYPE,
) -> tuple[TranscriptionCandidate, str]:
    try:
        base_candidate = build_candidate(
            audio_path,
            locale,
            "base",
            engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
        )
    except RuntimeError as exc:
        raise RuntimeError(f"ListenKit transcript generation failed. Original error: {exc}") from exc

    if not is_short_choice_mode(audio_path):
        return base_candidate, str(base_candidate.payload.get("engine", "base"))

    slow_path = build_slow_copy(audio_path)
    try:
        slow_candidate = build_candidate(
            slow_path,
            locale,
            "slow",
            engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
        )
    finally:
        try:
            slow_path.unlink(missing_ok=True)
        except OSError:
            pass

    if slow_candidate.score > base_candidate.score:
        return slow_candidate, "slow"
    return base_candidate, str(base_candidate.payload.get("engine", "base"))


def infer_title(audio_stem: str, forced_title: str | None, sentences: list[str]) -> str:
    prefix = "_".join(audio_stem.split("_")[:2])
    if forced_title:
        return f"{prefix} {forced_title}"
    topic = infer_topic_title(sentences)
    if topic:
        return f"{prefix} {topic}"
    for sentence in sentences:
        stripped = sentence.replace("。", "").strip()
        if stripped.startswith("第") or stripped in {"質問", "買える"}:
            continue
        if re.match(r"^\d+-\d+聞こう", stripped) or re.match(r"^\d+番", stripped):
            continue
        if 3 <= len(stripped) <= 14 and re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", stripped):
            return f"{prefix} {stripped}"
    return f"{prefix} 识别稿"


def infer_title_from_existing_note(audio_path: Path, note_path: Path | None) -> str | None:
    if note_path is None or not note_path.exists() or should_rename_generated_note(note_path):
        return None
    prefix = f"{audio_path.stem}_"
    if not note_path.stem.startswith(prefix):
        return None
    suffix = note_path.stem.removeprefix(prefix).replace("_", " ").strip()
    if not suffix:
        return None
    return f"{audio_path.stem} {suffix}"


def infer_topic_title(sentences: list[str]) -> str | None:
    text = "".join(sentences)
    phrase_pairs = [
        (("土用の丑の日", "節分"), "土用の丑の日と節分の質問"),
        (("摂取カロリー",), "1日の摂取カロリー"),
        (("恵方巻き", "うなぎ", "お菓子"), "恵方巻きとうなぎとお菓子"),
        (("土用の丑の日", "うなぎ"), "土用の丑の日とうなぎ"),
        (("節分", "恵方巻き"), "節分と恵方巻き"),
        (("ユニセックス", "ファッション"), "ユニセックスファッション"),
        (("三井公園",), "私の町"),
    ]
    for keywords, title in phrase_pairs:
        if all(keyword in text for keyword in keywords):
            return title

    repeated = [
        candidate
        for candidate in re.findall(r"[一-龥ぁ-んァ-ヶー]{4,12}", text)
        if candidate not in {"日本では", "ということ", "という習慣", "本当だとしたら", "商業主義から", "新しい食生活"}
    ]
    counts: dict[str, int] = {}
    for candidate in repeated:
        counts[candidate] = counts.get(candidate, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    if ranked and ranked[0][1] >= 2:
        return ranked[0][0]
    return None


def slugify_note_title(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "识别稿"


def desired_note_path(audio_path: Path, title: str) -> Path:
    return material_dir_for_audio(audio_path) / f"{audio_path.stem}_{slugify_note_title(title.split(' ', 1)[1])}.md"


def should_rename_generated_note(note_path: Path) -> bool:
    suffix = note_path.stem.removeprefix(f"{note_path.stem.split('_')[0]}_{note_path.stem.split('_')[1]}_")
    return (
        note_path.name.endswith("_识别稿.md")
        or bool(re.match(r"^\d+-\d+聞こう$", suffix))
        or bool(re.match(r"^\d+番", suffix))
    )


def infer_source_tag(audio_path: Path) -> str | None:
    path_text = audio_path.as_posix()
    if "中級を学ぼう" in path_text or audio_path.stem.startswith("manabo_"):
        return "source/manabo"
    if "ドリル＆ドリル" in path_text or "日本語能力試験" in path_text:
        return "source/drill_n3"
    if "実力アップ" in path_text:
        return "source/jitsuryoku_up"
    return None


def build_default_frontmatter(
    audio_path: Path,
    sentence_count: int,
    short_choice_mode: bool,
    dialogue_content_mode: bool = False,
    listening_mode: str = "extensive",
) -> list[str]:
    today = date.today().isoformat()
    difficulty = "3" if sentence_count >= 8 else "2"
    if short_choice_mode:
        weak_points = [
            "这条材料是短句应答题，题干和选项切分容易粘连",
            "若个别选项仍不自然，优先回听题干和错误选项",
        ]
        practice_focus = "重点抓题干与三选项结构，并对比自然说法和不自然选项。"
    elif dialogue_content_mode:
        weak_points = [
            "对话轮替时容易把发言人和应答关系听反",
            "场景词、数字、人名、地点等短信息在对话里更容易混淆",
        ]
        practice_focus = "先确认每轮是谁在问、谁在答，再抓场景里的高频问句和应答模板。"
    else:
        weak_points = [
            "新生成的精听稿，建议先听一遍确认题号和开头提示语",
            "长句和专有名词可能仍有少量自动转写误差",
        ]
        practice_focus = "先通读脚本抓主题，再对照带时间字幕精修 1-3 个长句。"
    lines = [
        "track: listening",
        "status: active",
        "priority: high",
        "done_today: false",
        f"audio_ref: {audio_ref_for_note(audio_path)}",
        "transcript_status: full",
        "transcript_ref: in-note",
        f"listening_mode: {listening_mode}",
        f"difficulty: {difficulty}",
        f"segment_count: {sentence_count}",
    ]
    lines.extend(["weak_points:"] + [f"  - {item}" for item in weak_points])
    lines.append(f"practice_focus: {practice_focus}")
    lines.append("daily_use_sentences: []")
    lines.append("source_notes: []")
    lines.append(f"first_seen: {today}")
    lines.append(f"last_seen: {today}")
    lines.append("seen_count: 1")
    lines.append("error_count: 0")
    lines.append("review_stage: day0")
    lines.append(f"next_review: {today}")
    lines.append('last_reviewed: ""')
    lines.extend(["tags:", "  - jp/listening", "  - jp/p0_plus"])
    source_tag = infer_source_tag(audio_path)
    if source_tag:
        lines.append(f"  - {source_tag}")
    return lines


def group_paragraphs(sentences: list[str], limit: int = 70) -> list[str]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    count = 0
    for sentence in sentences:
        if current and count + len(sentence) > limit:
            paragraphs.append(current)
            current = []
            count = 0
        current.append(sentence)
        count += len(sentence)
    if current:
        paragraphs.append(current)
    return ["".join(items) for items in paragraphs]


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def is_focus_term(term: str) -> bool:
    cleaned = term.strip("。、！？?「」『』（）()")
    if len(cleaned) < 2:
        return False
    if re.fullmatch(r"[ぁ-ん]+", cleaned) and cleaned not in {"少し", "かなり", "ちょうど", "いっぱい"}:
        return False
    if cleaned in {"です", "ます", "でした", "ました", "ください", "あります", "います", "する", "した"}:
        return False
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", cleaned))


def strip_term_inflection(term: str) -> str:
    cleaned = term.strip("。、！？?「」『』（）()")
    for suffix in ["します", "しました", "している", "しています", "する", "した", "しますね"]:
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix) + 1:
            cleaned = cleaned[: -len(suffix)]
            break
    if cleaned.startswith("少し") and len(cleaned) > 2:
        return "少し"
    return cleaned


def rough_extract_focus_terms(sentence: str) -> list[str]:
    parts = re.split(r"(?:を|が|は|に|で|へ|と|も|から|まで|より|や|、|。|！|？|\?)", sentence)
    terms: list[str] = []
    for part in parts:
        cleaned = strip_term_inflection(part)
        if is_focus_term(cleaned):
            terms.append(cleaned)
    return dedupe_preserve_order(terms)


def select_focus_terms(
    sentence: str,
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
    limit: int = 5,
) -> list[str]:
    candidates: list[str] = []
    for term in sorted(confirmed_accent_index, key=lambda item: (-len(item), item)):
        if term and term in sentence:
            candidates.append(term)
    for term in offline_dictionary.known_terms():
        if term in sentence:
            candidates.append(term)
    candidates.extend(offline_dictionary.tokenize_terms(sentence))
    candidates.extend(rough_extract_focus_terms(sentence))
    return [term for term in dedupe_preserve_order(candidates) if is_focus_term(term)][:limit]


def render_follow_along_split(sentence: str) -> str:
    normalized = sentence.strip()
    match = re.match(r"^(.+?[をがはにでへと])(.+)$", normalized)
    if match and len(match.group(2)) >= 2:
        return f"{match.group(1)} / {match.group(2)}"
    if "、" in normalized:
        return normalized.replace("、", "、 / ", 1)
    return normalized


def render_accent_lines(
    terms: list[str],
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
) -> list[str]:
    if not terms:
        return ["- 重点词なし"]
    lines: list[str] = []
    for term in terms:
        confirmed = confirmed_accent_index.get(term)
        if confirmed:
            lines.append(f"- {term}：{confirmed}（已确认）")
            continue
        candidate = offline_dictionary.lookup(term)
        if candidate:
            lines.append(f"- {term}：{candidate}（本地候选）")
            continue
        lines.append(f"- {term}：待确认")
    return lines


ACCENT_MARK_RE = re.compile(rf"[{CIRCLED_ACCENT_MARKS}]")


def accent_mark_from_display(value: str) -> str | None:
    match = ACCENT_MARK_RE.search(value)
    if match:
        return match.group(0)
    return None


def resolve_accent_note(
    term: str,
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
) -> tuple[str | None, str]:
    confirmed = confirmed_accent_index.get(term)
    if confirmed:
        mark = accent_mark_from_display(confirmed)
        if mark:
            return mark, f"{term}{mark}（已确认）"
        return None, f"{term}：{confirmed}（已确认）"

    candidate = offline_dictionary.lookup(term)
    if candidate:
        mark = accent_mark_from_display(candidate)
        if mark:
            return mark, f"{term}{mark}（本地候选）"
        return None, f"{term}：{candidate}（本地候选）"

    return None, f"{term}：待确认"


def inline_accent_marks(
    sentence: str,
    terms: list[str],
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
) -> tuple[str, list[str]]:
    rendered = sentence
    notes: list[str] = []
    replacements: list[tuple[str, str]] = []
    for term in terms:
        mark, note = resolve_accent_note(term, confirmed_accent_index, offline_dictionary)
        notes.append(note)
        if mark:
            replacements.append((term, f"{term}{mark}"))

    replacement_terms = [term for term, _ in replacements]
    replacements = [
        (term, replacement)
        for term, replacement in replacements
        if not any(term != other and term in other for other in replacement_terms)
    ]
    for term, replacement in sorted(replacements, key=lambda item: (-len(item[0]), item[0])):
        rendered = re.sub(term_replacement_pattern(term), replacement, rendered)
    return rendered, notes


def render_audio_slice_line(audio_slice_ref: str | None) -> str:
    if audio_slice_ref:
        return f"![[{audio_slice_ref}]]"
    return "（语音切片待生成）"


def build_learning_package(
    sentences: list[str],
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
    audio_slice_refs: list[str | None] | None = None,
) -> str:
    blocks: list[str] = []
    for idx, sentence in enumerate(sentences, start=1):
        terms = select_focus_terms(sentence, confirmed_accent_index, offline_dictionary)
        accented_sentence, _accent_notes = inline_accent_marks(
            sentence,
            terms,
            confirmed_accent_index,
            offline_dictionary,
        )
        audio_slice_ref = audio_slice_refs[idx - 1] if audio_slice_refs and idx - 1 < len(audio_slice_refs) else None
        blocks.append(
            "\n".join(
                [
                    f"### S{idx:02d}",
                    "",
                    accented_sentence,
                    "",
                    render_audio_slice_line(audio_slice_ref),
                ]
            )
        )
    return "\n\n".join(blocks) if blocks else "当前未能生成逐句学习包，请先确认脚本内容。"


def accent_script_section(
    script_section: str,
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
) -> str:
    rendered_lines: list[str] = []
    for line in script_section.splitlines():
        if not line.strip():
            rendered_lines.append(line)
            continue
        if re.fullmatch(r"(セクション|第)?\s*\d+", line.strip()):
            rendered_lines.append(line)
            continue
        terms = select_focus_terms(line, confirmed_accent_index, offline_dictionary)
        accented_line, _accent_notes = inline_accent_marks(
            line,
            terms,
            confirmed_accent_index,
            offline_dictionary,
        )
        rendered_lines.append(accented_line)
    return "\n".join(rendered_lines)


def reliable_sentence_chunks(sentences: list[str], chunks: list[Chunk]) -> list[Chunk] | None:
    if len(sentences) != len(chunks):
        return None
    for sentence, chunk in zip(sentences, chunks):
        if chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
            return None
        if clean_transcript_text(sentence) != clean_transcript_text(chunk.text):
            return None
    return chunks


def slice_attach_dir(audio_path: Path) -> Path:
    return material_dir_for_audio(audio_path) / "attach"


def export_sentence_audio_slices(
    audio_path: Path,
    sentence_chunks: list[Chunk],
    attach_dir: Path,
    audio_stem: str,
) -> list[str | None]:
    if not audio_path.exists() or audio_path.stat().st_size <= 0:
        return [None for _ in sentence_chunks]
    attach_dir.mkdir(parents=True, exist_ok=True)
    refs: list[str | None] = []
    for idx, chunk in enumerate(sentence_chunks, start=1):
        if chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
            refs.append(None)
            continue
        filename = f"{audio_stem}_S{idx:02d}.m4a"
        output_path = attach_dir / filename
        try:
            run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(chunk.start),
                    "-to",
                    str(chunk.end),
                    "-i",
                    str(audio_path),
                    "-vn",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    str(output_path),
                ]
            )
        except Exception:
            output_path.unlink(missing_ok=True)
            refs.append(None)
            continue
        refs.append(f"attach/{filename}")
    return refs


def format_timestamp(value: float | None) -> str:
    if value is None:
        return "??:??.??"
    minutes = int(value // 60)
    seconds = value - (minutes * 60)
    return f"{minutes:02d}:{seconds:05.2f}"


def parse_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


def find_vault_root_from_path(path: Path) -> Path:
    current = path.resolve().parent
    while current != current.parent:
        if (current / "学习系统").exists() and (current / "codex-skills").exists():
            return current
        current = current.parent
    return path.resolve().parent


def frontmatter_value(lines: list[str], key: str) -> str:
    prefix = f"{key}:"
    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip().strip('"')
    return ""


def resolve_listening_mode(forced_mode: str | None, frontmatter_lines: list[str], existing_body: str) -> str:
    if forced_mode:
        return forced_mode
    frontmatter_mode = frontmatter_value(frontmatter_lines, "listening_mode")
    if frontmatter_mode in LISTENING_MODES:
        return frontmatter_mode
    if "## 精听学习包" in existing_body:
        return "intensive"
    return "extensive"


def load_vault_path_roles(vault_root: Path) -> dict[str, str]:
    for relative in (
        "系统配置/paths.json",
        "学习系统/系统/配置/paths.json",  # legacy fallback
        "学习系统/系统配置/paths.json",  # legacy fallback
    ):
        path = vault_root / relative
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("roles", {})
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def load_confirmed_accent_index(vault_root: Path) -> dict[str, str]:
    roles = load_vault_path_roles(vault_root)
    roots = [
        vault_root / roles.get("focus_vocab_root", "学习系统/词库/重点词汇"),
        vault_root / roles.get("base_vocab_root", "学习系统/词库/基础词汇"),
        vault_root / "学习系统" / "发音",
    ]
    index: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            accent = frontmatter_value(frontmatter, "accent_display")
            if not accent:
                continue
            for key in [
                frontmatter_value(frontmatter, "headword"),
                frontmatter_value(frontmatter, "reading"),
                path.stem,
            ]:
                if key and key not in index:
                    index[key] = accent
    return index


def choose_material_section(preserved_sections: dict[str, str], material_note: str) -> str:
    existing = preserved_sections.get("素材说明")
    if not existing:
        return material_note
    if "faster-whisper" in material_note and "faster-whisper" not in existing:
        return f"{material_note}\n\n既存说明：{existing}"
    return existing


def decorate_material_note(material_note: str, dialogue_content_mode: bool) -> str:
    if not dialogue_content_mode:
        return material_note
    if DIALOGUE_MATERIAL_NOTE_SUFFIX in material_note:
        return material_note
    return f"{material_note}\n\n{DIALOGUE_MATERIAL_NOTE_SUFFIX}"


def build_body(
    title: str,
    audio_name: str,
    sentences: list[str],
    chunks: list[Chunk],
    audio_path: Path,
    existing_body: str | None = None,
    material_note: str = DEFAULT_MATERIAL_NOTE,
    short_choice_mode: bool = False,
    structured_dialogue_mode: bool = False,
    confirmed_accent_index: dict[str, str] | None = None,
    offline_dictionary: StaticAccentDictionary | None = None,
    audio_slice_refs: list[str | None] | None = None,
    listening_mode: str = "intensive",
) -> tuple[str, bool]:
    script_section, dialogue_content_mode = render_dialogue_script_section(sentences, chunks, structured_dialogue_mode)
    existing_sections = parse_sections(existing_body or "")
    known_headings = {"精听学习包", "脚本", "可直接背的常用句", "素材说明"}
    preserved_sections = {heading: content for heading, content in existing_sections}
    if short_choice_mode:
        script_section = choose_short_choice_script(
            script_section,
            preserved_sections.get("脚本"),
            audio_path,
        )
    common_section = (
        preserved_sections["可直接背的常用句"]
        if "可直接背的常用句" in preserved_sections
        else COMMON_SECTION_PLACEHOLDER
    )
    material_section = (
        choose_material_section(preserved_sections, decorate_material_note(material_note, dialogue_content_mode))
    )
    accent_index = confirmed_accent_index or {}
    dictionary = offline_dictionary or StaticAccentDictionary({})
    if listening_mode == "extensive":
        script_section = accent_script_section(script_section, accent_index, dictionary)
        learning_package = None
    else:
        learning_package = build_learning_package(
            sentences,
            accent_index,
            dictionary,
            audio_slice_refs,
        )

    lines = [
        f"# {title}",
        "",
        f"![[{audio_name}]]",
        "",
        "## 脚本",
        "",
        script_section,
        "",
        "## 可直接背的常用句",
        "",
        common_section,
        "",
        "## 素材说明",
        "",
        material_section,
    ]
    if learning_package is not None:
        lines[3:3] = [
            "",
            "## 精听学习包",
            "",
            learning_package,
        ]

    for heading, content in existing_sections:
        if heading in known_headings:
            continue
        lines.extend(["", f"## {heading}", ""])
        if content:
            lines.append(content)

    return "\n".join(lines), dialogue_content_mode


def render_note(frontmatter_lines: list[str], body: str) -> str:
    return "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n"


def process_one(
    audio_path: Path,
    note_override: str | None,
    locale: str,
    forced_title: str | None,
    dry_run: bool,
    engine: str = "auto",
    faster_whisper_python: str | None = None,
    faster_whisper_model: str = DEFAULT_FASTER_WHISPER_MODEL,
    faster_whisper_compute_type: str = DEFAULT_FASTER_WHISPER_COMPUTE_TYPE,
    candidate_route: tuple[TranscriptionCandidate, str] | None = None,
    source_url: str | None = None,
    offline_dictionary: StaticAccentDictionary | None = None,
    listening_mode: str | None = None,
) -> str:
    if candidate_route is None:
        candidate, route_label = transcribe_with_heuristics(
            audio_path,
            locale,
            engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
        )
    else:
        candidate, route_label = candidate_route
    sentences = candidate.sentences
    short_choice_mode = is_short_choice_mode(audio_path)
    structured_dialogue_mode = is_shadowing_path(audio_path)
    note_path = resolve_note_path(audio_path, note_override)
    if forced_title:
        title = infer_title(audio_path.stem, forced_title, sentences)
    else:
        title = infer_title_from_existing_note(audio_path, note_path) or infer_title(audio_path.stem, None, sentences)
    target_note_path = desired_note_path(audio_path, title)
    existed = note_path.exists() if note_path is not None else False
    should_rename_note = (
        note_path is not None
        and note_override is None
        and note_path.exists()
        and should_rename_generated_note(note_path)
        and note_path != target_note_path
        and not target_note_path.exists()
    )
    read_note_path = note_path
    if note_path is None:
        write_note_path = target_note_path
    elif should_rename_note and not dry_run:
        note_path.rename(target_note_path)
        read_note_path = target_note_path
        write_note_path = target_note_path
    elif should_rename_note:
        write_note_path = target_note_path
    else:
        write_note_path = note_path
    if route_label == "faster-whisper":
        material_note = FASTER_WHISPER_MATERIAL_NOTE
    else:
        material_note = SHORT_CHOICE_MATERIAL_NOTE if short_choice_mode else DEFAULT_MATERIAL_NOTE
    if short_choice_mode and route_label == "slow":
        material_note += " 本次已自动采用慢速副本作为较优转写结果。"
    if source_url:
        material_note += f"\n\n来源 URL：<{source_url}>"

    existing_body: str | None
    if read_note_path is not None and read_note_path.exists():
        frontmatter_lines, old_body = parse_frontmatter(read_note_path.read_text(encoding="utf-8"))
        set_scalar(frontmatter_lines, "transcript_status", "full")
        set_scalar(frontmatter_lines, "transcript_ref", "in-note")
        set_scalar(frontmatter_lines, "last_seen", date.today().isoformat())
        if not has_key(frontmatter_lines, "daily_use_sentences"):
            set_list(frontmatter_lines, "daily_use_sentences", [])
        existing_body = old_body
    else:
        write_note_path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter_lines = []
        existing_body = None
    resolved_listening_mode = resolve_listening_mode(listening_mode, frontmatter_lines, existing_body or "")
    if frontmatter_lines:
        set_scalar(frontmatter_lines, "listening_mode", resolved_listening_mode)
    sentence_chunks = reliable_sentence_chunks(sentences, candidate.segments)
    audio_slice_refs = None
    if resolved_listening_mode == "intensive" and sentence_chunks is not None and not dry_run:
        audio_slice_refs = export_sentence_audio_slices(
            audio_path,
            sentence_chunks,
            slice_attach_dir(audio_path),
            audio_path.stem,
        )
    body, dialogue_content_mode = build_body(
        title,
        audio_ref_for_note(audio_path),
        sentences,
        candidate.segments,
        audio_path,
        existing_body,
        material_note,
        short_choice_mode,
        structured_dialogue_mode,
        load_confirmed_accent_index(find_vault_root_from_path(audio_path)),
        offline_dictionary or load_offline_dictionary(required=False),
        audio_slice_refs,
        resolved_listening_mode,
    )
    if not frontmatter_lines:
        frontmatter_lines = build_default_frontmatter(
            audio_path,
            len(sentences),
            short_choice_mode,
            dialogue_content_mode,
            resolved_listening_mode,
        )
    rendered = render_note(frontmatter_lines, body)
    if dry_run:
        return f"=== {write_note_path} ===\n{rendered}"
    write_note_path.write_text(rendered, encoding="utf-8")
    verb = "Updated" if existed else "Created"
    return f"{verb} {write_note_path}"


def process_url(
    url: str,
    output_dir: Path,
    note_override: str | None,
    locale: str,
    forced_title: str | None,
    dry_run: bool,
    engine: str = "auto",
    faster_whisper_python: str | None = None,
    audio_format: str = "m4a",
    offline_dictionary: StaticAccentDictionary | None = None,
    listening_mode: str | None = None,
) -> str:
    output_stem = infer_stem_from_url(url)
    env_overrides = {}
    if faster_whisper_python:
        env_overrides["FASTER_WHISPER_PYTHON"] = str(Path(faster_whisper_python).expanduser())
    payload = invoke_listenkit(
        url,
        locale,
        engine,
        env_overrides or None,
        source_kind="url",
        output_stem=output_stem,
        output_dir=output_dir,
        audio_format=audio_format,
    )
    final_audio_value = payload.get("_listenkit_final_audio_path")
    if not final_audio_value:
        raise RuntimeError("ListenKit URL workflow did not return a finalized audio path.")
    final_audio_path = Path(str(final_audio_value))
    route_label = str(payload.get("engine", "base"))
    candidate = candidate_from_payload(final_audio_path, payload, route_label)
    result = process_one(
        final_audio_path,
        note_override,
        locale,
        forced_title,
        dry_run,
        engine,
        faster_whisper_python,
        candidate_route=(candidate, route_label),
        source_url=url,
        offline_dictionary=offline_dictionary,
        listening_mode=listening_mode,
    )
    if dry_run:
        return f"Source URL: {url}\nFinal audio: {final_audio_path}\n{result}"
    return f"Source URL: {url}\nFinal audio: {final_audio_path}\n{result}"


def scan_audio_files(directory: Path) -> list[Path]:
    files = []
    for path in directory.rglob("*"):
        if path.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac"}:
            files.append(path)
    return sorted(files)


def main() -> int:
    args = parse_args()
    source_count = sum(1 for value in [args.audio_path, args.url, args.scan_dir] if value)
    if source_count == 0:
        print("Provide one of <audio_path>, --url, or --scan-dir.", file=sys.stderr)
        return 1
    if source_count > 1:
        print("Use only one of <audio_path>, --url, or --scan-dir.", file=sys.stderr)
        return 1

    if args.scan_dir:
        print("Batch scan mode is not supported in the current single-item workflow.", file=sys.stderr)
        return 1

    if args.url and not args.output_dir:
        print("--output-dir is required when using --url.", file=sys.stderr)
        return 1

    try:
        offline_dictionary = load_offline_dictionary(required=True)
    except OfflineDictionaryError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.url:
        result = process_url(
            args.url,
            Path(args.output_dir),
            args.note_path,
            args.locale,
            args.title,
            args.dry_run,
            args.engine,
            args.faster_whisper_python,
            args.format,
            offline_dictionary,
            args.listening_mode,
        )
        print(result)
        return 0

    if args.audio_path:
        result = process_one(
            Path(args.audio_path),
            args.note_path,
            args.locale,
            args.title,
            args.dry_run,
            args.engine,
            args.faster_whisper_python,
            args.faster_whisper_model,
            args.faster_whisper_compute_type,
            offline_dictionary=offline_dictionary,
            listening_mode=args.listening_mode,
        )
        print(result)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
