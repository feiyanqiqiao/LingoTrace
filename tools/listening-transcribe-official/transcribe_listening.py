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
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

COMMON_SECTION_PLACEHOLDER = (
    "二阶段待编辑：请基于完整脚本，用大模型或人工判断，挑选 0-5 个真正可替换、可迁移的常用语块；宁缺勿滥。\n\n"
    "> 素材原句只作为听辨锚点，不要求整句原样背诵。\n\n"
    "- 语块：\n"
    "  类型：\n"
    "  素材原句：\n"
    "  替换练习：\n"
    "  交际作用：\n\n"
    "完成后同步更新 frontmatter 的 `daily_use_sentences`，只放日文语块骨架，不放素材完整句。"
)
DEFAULT_MATERIAL_NOTE = "这条音频由 ListenKit 自动生成转写稿。建议人工复核题号、教材抬头、专有名词和少量长句切分，再决定是否继续精修。"
SHORT_CHOICE_MATERIAL_NOTE = "这条音频按短句应答题模式处理：脚本会优先保留题号与选项结构，必要时自动尝试慢速副本重转。仍建议人工顺耳确认题干与错误选项。"
FASTER_WHISPER_MATERIAL_NOTE = "这条音频由 ListenKit 的 faster-whisper 路线自动转写生成。仍需人工复核同音词、姓名、楼层等上下文词。"
DEFAULT_FASTER_WHISPER_MODEL = "small"
DEFAULT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
INTENSIVE_SLICE_PADDING_SECONDS = 0.5
NUMBERED_DIALOGUE_SLICE_PADDING_SECONDS = 0.0
DIALOGUE_MATERIAL_NOTE_SUFFIX = "本稿按对话型精听内容整理；仅在文本呈现出明显问答或应答轮替时，保守标注 A：/B：。"
LISTENING_MODES = {"intensive", "extensive"}
SLICE_PROFILE_CHOICES = {"auto", "dialogue", "sentence"}

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
    "うん",
    "本当",
    "すいません",
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
    slice_profile: "SliceProfile"


@dataclass
class ScriptBlock:
    kind: str
    label: str | None = None
    utterances: list[str] | None = None
    text: str | None = None


@dataclass
class LearningBlock:
    id: str
    text: str
    start: float
    end: float
    kind: str


@dataclass(frozen=True)
class SliceProfile:
    kind: str
    grouping: str
    source: str
    number_markers: str
    padding_seconds: float

    def to_manifest_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "grouping": self.grouping,
            "source": self.source,
            "number_markers": self.number_markers,
            "padding_seconds": self.padding_seconds,
        }


@dataclass
class SliceExportResult:
    refs: list[str]
    report_path: Path
    report: dict


@dataclass
class ASRComparisonResult:
    candidate: TranscriptionCandidate
    report: dict
    report_path: Path | None
    consensus_path: Path | None
    merge_request_path: Path | None = None

    @property
    def unresolved_count(self) -> int:
        return int(self.report.get("unresolved_count", 0))


@dataclass
class PreparedListeningBundle:
    vault_root: Path
    note_path: str
    files: list[dict[str, object]]
    summary: str
    overwrite_required: bool
    staging_root: Path
    review_required: bool = False
    llm_merge_request_path: str | None = None
    disagreement_count: int = 0
    merge_model: str | None = None
    asr_validation_status: str = "single"

    def workflow_payload(self, *, overwrite_confirmed: bool = False) -> dict:
        files = self.files
        note_path = self.note_path
        if self.review_required:
            files = [item for item in files if is_review_artifact_path(str(item.get("path", "")))]
            note_path = ""
        return {
            "note_path": note_path,
            "files": files,
            "overwrite_confirmed": overwrite_confirmed,
        }

    def cleanup(self) -> None:
        shutil.rmtree(self.staging_root, ignore_errors=True)


class OfflineDictionaryError(RuntimeError):
    pass


CIRCLED_ACCENT_MARKS = "⓪①②③④⑤⑥⑦⑧⑨"
ACCENT_TYPE_TO_MARK = {str(index): mark for index, mark in enumerate(CIRCLED_ACCENT_MARKS)}
ACCENT_MARK_TO_TYPE = {mark: index for index, mark in enumerate(CIRCLED_ACCENT_MARKS)}
KANJI_CHAR_RE = re.compile(r"[\u3400-\u9fff々〆ヵヶ]")
KANA_ONLY_RE = re.compile(r"^[ぁ-んァ-ヶー]+$")
SMALL_KANA = set("ゃゅょャュョぁぃぅぇぉァィゥェォゎヮ")


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
        try:
            import fugashi  # type: ignore
            import unidic_lite  # type: ignore

            self._tagger = fugashi.Tagger(f"-d {unidic_lite.DICDIR}")
        except Exception as exc:  # pragma: no cover - depends on optional local packages
            self._tagger_error = exc
            self._tagger = None
        return self._tagger

    def runtime_details(self) -> str:
        vault_root = Path(__file__).resolve().parents[2]
        init_script = vault_root / "codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh"
        return (
            f"Python: {sys.executable}\n"
            f"Version: {sys.version.split()[0]}\n"
            f"ABI tag: {sys.implementation.cache_tag}\n"
            f"Virtual environment: {sys.prefix}\n"
            f"Repair: `{init_script}`"
        )

    def validate_runtime(self) -> list[str]:
        tagger = self._load_tagger()
        if tagger is None:
            detail = str(self._tagger_error) if self._tagger_error else "unknown import error"
            raise OfflineDictionaryError(
                f"Offline dictionary runtime validation failed: {detail}\n{self.runtime_details()}"
            )
        try:
            words = list(tagger("公園を散歩します。"))
        except Exception as exc:
            raise OfflineDictionaryError(
                f"Offline dictionary sample parse failed: {exc}\n{self.runtime_details()}"
            ) from exc
        if not words:
            raise OfflineDictionaryError(
                f"Offline dictionary parsed no tokens for the health-check sentence.\n{self.runtime_details()}"
            )
        accents: list[str] = []
        for word in words:
            marks = accent_marks_from_type(str(getattr(word.feature, "aType", "") or ""))
            if marks:
                accents.append(f"{word.surface}{marks}")
        if not accents:
            raise OfflineDictionaryError(
                f"Offline dictionary returned no accent candidates for the health-check sentence.\n{self.runtime_details()}"
            )
        return accents

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


def load_offline_dictionary(required: bool = True) -> StaticAccentDictionary:
    cache_dir = default_dictionary_cache_dir()
    dictionary = OfflineAccentDictionary(cache_dir)
    try:
        dictionary.validate_runtime()
    except OfflineDictionaryError:
        if required:
            raise
        return StaticAccentDictionary(load_static_accent_entries(cache_dir))
    return dictionary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="transcribe-listening",
        description="Generate a Japanese listening Markdown note from ListenKit transcript artifacts.",
    )
    parser.add_argument("audio_path", nargs="?")
    parser.add_argument("--url")
    parser.add_argument("--output-dir")
    parser.add_argument("--note-path")
    parser.add_argument("--vault-root")
    parser.add_argument("--lingotrace-root")
    parser.add_argument("--listenkit-root")
    parser.add_argument("--locale", default="ja-JP")
    parser.add_argument("--title")
    parser.add_argument("--engine", choices=["auto", "apple", "faster-whisper"], default="auto")
    parser.add_argument(
        "--compare-engine",
        choices=["auto", "apple", "faster-whisper"],
        default="auto",
        help="Secondary ASR route; auto enables dual-ASR validation by default.",
    )
    parser.add_argument(
        "--single-asr",
        action="store_true",
        help="Explicitly opt out of the default dual-ASR validation.",
    )
    parser.add_argument("--reviewed-transcript")
    parser.add_argument(
        "--merge-request",
        help="Stable merge-request artifact paired with an LLM-reviewed transcript.",
    )
    parser.add_argument("--format", choices=["mp3", "m4a", "wav", "flac"], default="m4a")
    parser.add_argument("--faster-whisper-python")
    parser.add_argument("--faster-whisper-model", default=DEFAULT_FASTER_WHISPER_MODEL)
    parser.add_argument("--faster-whisper-compute-type", default=DEFAULT_FASTER_WHISPER_COMPUTE_TYPE)
    parser.add_argument("--listening-mode", choices=sorted(LISTENING_MODES))
    parser.add_argument("--slice-manifest")
    parser.add_argument("--slice-profile", choices=sorted(SLICE_PROFILE_CHOICES), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-overwrite", action="store_true")
    parser.add_argument("--scan-dir")
    return parser.parse_args()


def lingotrace_root() -> Path:
    override = os.environ.get("LINGOTRACE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def listenkit_root() -> Path:
    override = os.environ.get("LISTENKIT_ROOT")
    if override:
        return Path(override).expanduser()
    return lingotrace_root().parent / "ListenKit"


def configure_project_roots(*, lingotrace: str | None = None, listenkit: str | None = None) -> None:
    if lingotrace:
        root = Path(lingotrace).expanduser().resolve()
        expected = root / "tools" / "listening-transcribe-official" / "transcribe_listening.py"
        if not expected.is_file():
            raise RuntimeError(f"LingoTrace root does not contain the listening generator: {root}")
        os.environ["LINGOTRACE_ROOT"] = str(root)
    if listenkit:
        root = Path(listenkit).expanduser().resolve()
        if not (root / "cli" / "generate-markdown.sh").is_file():
            raise RuntimeError(f"ListenKit root does not contain cli/generate-markdown.sh: {root}")
        os.environ["LISTENKIT_ROOT"] = str(root)


def listenkit_generate_markdown_script_path() -> Path:
    return listenkit_root() / "cli" / "generate-markdown.sh"


def listenkit_export_audio_slices_script_path() -> Path:
    return listenkit_root() / "cli" / "export-audio-slices.py"


def require_executable_file(path: Path, description: str) -> None:
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"{description} is missing or not executable: {path}")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required command for listening audio workflow: {name}")


def preflight_source_audio(audio_path: Path) -> None:
    if not audio_path.is_file() or audio_path.stat().st_size <= 0:
        raise RuntimeError(f"Source audio file is missing or empty: {audio_path}")


def preflight_listenkit_generate_tooling() -> None:
    require_executable_file(listenkit_generate_markdown_script_path(), "ListenKit generate-markdown CLI")


def preflight_intensive_slice_tooling() -> None:
    require_executable_file(listenkit_export_audio_slices_script_path(), "ListenKit audio-slice export CLI")
    require_command("ffmpeg")
    require_command("ffprobe")


def preflight_listening_audio_chain(audio_path: Path, intensive: bool = False) -> None:
    preflight_source_audio(audio_path)
    preflight_listenkit_generate_tooling()
    if intensive:
        preflight_intensive_slice_tooling()


def listenkit_artifact_label(payload: dict, fallback: str) -> str:
    label = str(payload.get("engine") or fallback or "listenkit")
    return slugify_stem(label)


def persist_listenkit_artifacts(
    output_path: Path,
    transcript_json: Path,
    artifact_dir: Path,
    artifact_stem: str,
    artifact_label: str,
    move: bool = False,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    target_stem = f"{artifact_stem}.{artifact_label}.listenkit"
    for source, suffix in [(output_path, ".md"), (transcript_json, ".json")]:
        target = artifact_dir / f"{target_stem}{suffix}"
        if move:
            shutil.move(str(source), target)
        else:
            shutil.copy2(source, target)


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
    schema_version = payload.get("schema_version")
    if schema_version not in (None, 1):
        raise RuntimeError(f"ListenKit transcript uses unsupported schema_version: {schema_version}")
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
    artifact_dir: Path | None = None,
    artifact_stem: str | None = None,
    artifact_label: str | None = None,
    audio_format: str = "m4a",
) -> dict:
    script_path = listenkit_generate_markdown_script_path()
    preflight_listenkit_generate_tooling()
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
        label = artifact_label or listenkit_artifact_label(payload, engine)
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
            persist_listenkit_artifacts(
                output_path,
                transcript_json,
                artifact_dir,
                artifact_stem or output_path.stem,
                label,
                move=True,
            )
            payload["_listenkit_final_audio_path"] = str(final_audio)
        elif artifact_dir is not None:
            persist_listenkit_artifacts(
                output_path,
                transcript_json,
                artifact_dir,
                artifact_stem or output_path.stem,
                label,
            )
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


def configured_path_roles(vault_root: Path) -> dict[str, str]:
    path = vault_root / ".lingotrace" / "paths.json"
    if not path.is_file():
        raise RuntimeError(f"LingoTrace Vault path configuration is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LingoTrace Vault path configuration is invalid JSON: {path}: {exc}") from exc
    roles: dict[str, str] = {}
    for item in payload.get("path_roles", []):
        if isinstance(item, dict) and item.get("role") and item.get("relative_path"):
            roles[str(item["role"])] = str(item["relative_path"]).strip("/")
    if "listening_root" not in roles:
        raise RuntimeError(f"LingoTrace Vault path configuration does not define listening_root: {path}")
    return roles


def discover_vault_root(start: Path) -> Path | None:
    candidate = start.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for current in (candidate, *candidate.parents):
        if (current / ".lingotrace" / "vault-context.json").is_file() and (
            current / ".lingotrace" / "paths.json"
        ).is_file():
            return current
    return None


def resolve_vault_root(explicit: str | None, *hints: str | Path | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        configured_path_roles(root)
        return root
    for hint in hints:
        if hint is None:
            continue
        found = discover_vault_root(Path(hint))
        if found is not None:
            configured_path_roles(found)
            return found
    found = discover_vault_root(Path.cwd())
    if found is not None:
        configured_path_roles(found)
        return found
    raise RuntimeError(
        "Unable to locate a LingoTrace Vault. Run from the Vault or pass --vault-root explicitly."
    )


def resolve_vault_relative_path(vault_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    resolved = path.resolve() if path.is_absolute() else (vault_root / path).resolve()
    try:
        resolved.relative_to(vault_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Listening path must stay inside the target Vault: {raw_path}") from exc
    return resolved


def resolve_readonly_input_path(vault_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        resolved = path.resolve()
    else:
        vault_candidate = (vault_root / path).resolve()
        resolved = vault_candidate if vault_candidate.exists() else path.resolve()
    if not resolved.is_file():
        raise RuntimeError(f"Read-only input artifact is missing: {resolved}")
    return resolved


def validate_listening_target(vault_root: Path, target: Path) -> None:
    listening_root = configured_path_roles(vault_root)["listening_root"]
    configured_root = (vault_root / listening_root).resolve()
    try:
        target.resolve().relative_to(configured_root)
    except ValueError as exc:
        raise RuntimeError(
            f"Listening input/output must stay under configured listening_root ({listening_root}): {target}"
        ) from exc


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


def normalize_structured_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("?", "？").replace("!", "！")
    cleaned = cleaned.replace("．", ".")
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.translate(FULLWIDTH_DIGIT_TRANSLATION)
    return cleaned


def normalize_payload_structure(payload: dict) -> dict:
    normalized = dict(payload)
    raw_segments = payload.get("segments", [])
    normalized_segments = []
    for segment in raw_segments:
        item = dict(segment)
        item["text"] = normalize_structured_text(str(segment.get("text", "")))
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


def chunks_to_structured_lines(chunks: Iterable[Chunk]) -> list[str]:
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
        text = normalize_structured_text(chunk.text)
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


def render_numbered_ab_dialogue(utterances: list[str]) -> list[str] | None:
    cleaned = [item.strip() for item in utterances if item and item.strip()]
    if len(cleaned) not in {2, 4}:
        return None
    if any(len(re.sub(r"[。！？?、，,\s]", "", item)) > 80 for item in cleaned):
        return None

    observation_cues = ("見て", "聞いた", "あれ", "これ", "ねえ")
    for index in range(0, len(cleaned), 2):
        left, right = cleaned[index], cleaned[index + 1]
        reliable = (
            is_conservative_dialogue_pair(left, right)
            or is_question_like(left)
            or is_response_like(right)
            or (any(cue in left for cue in observation_cues) and is_response_like(right))
        )
        if not reliable:
            return None

    return [f"{'A' if index % 2 == 0 else 'B'}：{utterance}" for index, utterance in enumerate(cleaned)]


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
        text = normalize_structured_text(chunk.text)
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


def render_dialogue_script_section(
    sentences: list[str],
    chunks: list[Chunk],
    slice_profile: SliceProfile | None = None,
) -> tuple[str, bool]:
    profile = slice_profile or detect_slice_profile(chunks)
    if profile.grouping == "numbered":
        rendered_blocks: list[str] = []
        dialogue_detected = False
        for block in chunks_to_structured_blocks(chunks):
            if block.kind == "section":
                rendered_blocks.append(block.text or "")
                continue
            if block.kind == "numbered":
                lines = [block.label or ""]
                rendered_dialogue = render_numbered_ab_dialogue(block.utterances or [])
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

    if profile.grouping == "exchange":
        blocks = dialogue_exchange_learning_blocks(chunks)
        if blocks is not None:
            return "\n\n".join(block.text for block in blocks), True

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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_asr_artifact(candidate: TranscriptionCandidate, audio_path: Path) -> dict:
    return {
        "schema_version": 1,
        "kind": "lingotrace_asr_artifact",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio": {
            "name": audio_path.name,
            "sha256": sha256_file(audio_path),
            "size_bytes": audio_path.stat().st_size,
        },
        "engine": str(candidate.payload.get("engine", candidate.route_label)),
        "route": candidate.route_label,
        "locale": str(candidate.payload.get("locale", "ja-JP")),
        "full_text": candidate.full_text,
        "segments": [
            {
                "id": f"T{index:03d}",
                "start": chunk.start,
                "end": chunk.end,
                "text": chunk.text,
            }
            for index, chunk in enumerate(candidate.segments, start=1)
        ],
    }


def write_normalized_asr_artifact(audio_path: Path, candidate: TranscriptionCandidate) -> Path:
    artifact_dir = material_dir_for_audio(audio_path) / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    engine = slugify_stem(str(candidate.payload.get("engine", candidate.route_label)))
    path = artifact_dir / f"{audio_path.stem}.{engine}.asr.json"
    path.write_text(
        json.dumps(normalized_asr_artifact(candidate, audio_path), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


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
    artifact_dir: Path | None = None,
    artifact_stem: str | None = None,
) -> TranscriptionCandidate:
    env_overrides = {}
    if faster_whisper_python:
        env_overrides["FASTER_WHISPER_PYTHON"] = str(Path(faster_whisper_python).expanduser())
    label = route_label if route_label != "base" else None
    payload = invoke_listenkit(
        audio_path,
        locale,
        engine,
        env_overrides or None,
        artifact_dir=artifact_dir,
        artifact_stem=artifact_stem,
        artifact_label=label,
    )
    return candidate_from_payload(audio_path, payload, route_label)


def candidate_from_payload(audio_path: Path, payload: dict, route_label: str) -> TranscriptionCandidate:
    payload = normalize_payload_structure(payload)
    raw_segments = raw_segments_to_chunks(payload.get("segments", []))
    slice_profile = detect_slice_profile(raw_segments)
    if str(payload.get("engine", "")) == "apple" and slice_profile.kind == "sentence":
        segments = merge_chunks(payload.get("segments", []))
    else:
        segments = raw_segments

    sentences, full_text = transcript_view_for_profile(payload, segments, slice_profile)
    return TranscriptionCandidate(
        payload=payload,
        segments=segments,
        sentences=sentences,
        full_text=full_text,
        score=score_short_choice_candidate(full_text, sentences, audio_path),
        route_label=route_label,
        slice_profile=slice_profile,
    )


def build_asr_comparison_report(
    primary: TranscriptionCandidate,
    secondary: TranscriptionCandidate,
) -> dict:
    rows = align_asr_candidates(primary, secondary)
    disagreements: list[dict] = []
    consensus_segments: list[dict] = []
    for index, row in enumerate(rows, start=1):
        primary_text = row["primary_text"]
        secondary_text = row["secondary_text"]
        status = comparison_status(primary_text, secondary_text)
        needs_review = status != "equal"
        consensus_segments.append(
            {
                "segment_id": f"T{index:03d}",
                "start": row.get("start"),
                "end": row.get("end"),
                "primary_text": primary_text,
                "secondary_text": secondary_text,
                "selected_text": primary_text or secondary_text,
                "decision": "agreement" if not needs_review else "pending_review",
                "needs_review": needs_review,
            }
        )
        if clean_transcript_text(primary_text) == clean_transcript_text(secondary_text):
            continue
        disagreements.append(
            {
                "index": index,
                "segment_id": f"T{index:03d}",
                "status": status,
                "primary_text": primary_text,
                "secondary_text": secondary_text,
                "start": row.get("start"),
                "end": row.get("end"),
                "categories": disagreement_categories(primary_text, secondary_text),
            }
        )
    return {
        "schema_version": 2,
        "kind": "asr_comparison",
        "status": "complete",
        "alignment": "timestamp_overlap_then_text_similarity",
        "primary": {
            "route": primary.route_label,
            "engine": str(primary.payload.get("engine", primary.route_label)),
            "segment_count": len(primary.segments),
        },
        "secondary": {
            "route": secondary.route_label,
            "engine": str(secondary.payload.get("engine", secondary.route_label)),
            "segment_count": len(secondary.segments),
        },
        "disagreement_count": len(disagreements),
        "unresolved_count": len(disagreements),
        "disagreements": disagreements,
        "consensus_segments": consensus_segments,
    }


def comparison_status(primary_text: str, secondary_text: str) -> str:
    if not primary_text:
        return "missing_primary"
    if not secondary_text:
        return "missing_secondary"
    if clean_transcript_text(primary_text) == clean_transcript_text(secondary_text):
        return "equal"
    return "different"


def _chunk_overlap(left: Chunk, right: Chunk) -> float:
    if left.start is None or left.end is None or right.start is None or right.end is None:
        return 0.0
    return max(0.0, min(left.end, right.end) - max(left.start, right.start))


def _text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, clean_transcript_text(left), clean_transcript_text(right)).ratio()


def align_asr_candidates(primary: TranscriptionCandidate, secondary: TranscriptionCandidate) -> list[dict]:
    primary_chunks = primary.segments or [Chunk(None, None, text) for text in primary.sentences]
    secondary_chunks = secondary.segments or [Chunk(None, None, text) for text in secondary.sentences]
    primary_edges: dict[int, set[int]] = {index: set() for index in range(len(primary_chunks))}
    secondary_edges: dict[int, set[int]] = {index: set() for index in range(len(secondary_chunks))}
    for primary_index, primary_chunk in enumerate(primary_chunks):
        for secondary_index, secondary_chunk in enumerate(secondary_chunks):
            if _chunk_overlap(primary_chunk, secondary_chunk) > 0:
                primary_edges[primary_index].add(secondary_index)
                secondary_edges[secondary_index].add(primary_index)

    used_primary: set[int] = set()
    used_secondary: set[int] = set()
    rows: list[dict] = []
    for seed in range(len(primary_chunks)):
        if seed in used_primary or not primary_edges[seed]:
            continue
        component_primary: set[int] = set()
        component_secondary: set[int] = set()
        pending_primary = [seed]
        pending_secondary: list[int] = []
        while pending_primary or pending_secondary:
            while pending_primary:
                index = pending_primary.pop()
                if index in component_primary:
                    continue
                component_primary.add(index)
                pending_secondary.extend(primary_edges[index] - component_secondary)
            while pending_secondary:
                index = pending_secondary.pop()
                if index in component_secondary:
                    continue
                component_secondary.add(index)
                pending_primary.extend(secondary_edges[index] - component_primary)
        used_primary.update(component_primary)
        used_secondary.update(component_secondary)
        members = [primary_chunks[index] for index in component_primary] + [
            secondary_chunks[index] for index in component_secondary
        ]
        starts = [chunk.start for chunk in members if chunk.start is not None]
        ends = [chunk.end for chunk in members if chunk.end is not None]
        rows.append(
            {
                "start": min(starts) if starts else None,
                "end": max(ends) if ends else None,
                "primary_text": "".join(primary_chunks[index].text for index in sorted(component_primary)),
                "secondary_text": "".join(secondary_chunks[index].text for index in sorted(component_secondary)),
            }
        )

    unused_primary = set(range(len(primary_chunks))) - used_primary
    unused_secondary = set(range(len(secondary_chunks))) - used_secondary
    for primary_index in sorted(unused_primary):
        primary_chunk = primary_chunks[primary_index]
        best_index: int | None = None
        best_score = -1.0
        for index in unused_secondary:
            secondary_chunk = secondary_chunks[index]
            similarity = _text_similarity(primary_chunk.text, secondary_chunk.text)
            if similarity > best_score:
                best_score = similarity
                best_index = index
        if best_index is not None and best_score >= 0.35:
            secondary_chunk = secondary_chunks[best_index]
            unused_secondary.remove(best_index)
        else:
            secondary_chunk = Chunk(None, None, "")
        starts = [value for value in (primary_chunk.start, secondary_chunk.start) if value is not None]
        ends = [value for value in (primary_chunk.end, secondary_chunk.end) if value is not None]
        rows.append(
            {
                "start": min(starts) if starts else None,
                "end": max(ends) if ends else None,
                "primary_text": primary_chunk.text,
                "secondary_text": secondary_chunk.text,
            }
        )
    for index in sorted(unused_secondary):
        chunk = secondary_chunks[index]
        rows.append(
            {
                "start": chunk.start,
                "end": chunk.end,
                "primary_text": "",
                "secondary_text": chunk.text,
            }
        )
    rows.sort(key=lambda row: (row["start"] is None, row["start"] or 0.0))
    return rows


def disagreement_categories(primary_text: str, secondary_text: str) -> list[str]:
    categories: list[str] = []
    combined = f"{primary_text}{secondary_text}"
    if re.search(r"\d|[一二三四五六七八九十百千万]+", combined):
        categories.append("number")
    if re.search(r"(さん|氏|様|駅|市|県|国|町|社)", combined):
        categories.append("proper_name_or_named_entity")
    if re.search(r"(は|が|を|に|で|と|も|へ|の|ね|よ|か)", combined):
        categories.append("particle_or_ending")
    if not primary_text or not secondary_text:
        categories.append("missing_text")
    if not categories:
        categories.append("word_or_homophone")
    return categories


def consensus_artifact(audio_path: Path, report: dict) -> dict:
    payload = {
        "schema_version": 1,
        "kind": "reviewed_transcript",
        "audio_sha256": sha256_file(audio_path),
        "primary_engine": report.get("primary", {}).get("engine"),
        "secondary_engine": report.get("secondary", {}).get("engine"),
        "review_status": "accepted" if not report.get("unresolved_count") else "needs_review",
        "segments": report.get("consensus_segments", []),
    }
    if report.get("merge_request_id"):
        payload["merge_request_id"] = report["merge_request_id"]
    return payload


def asr_merge_request_id(audio_path: Path, report: dict) -> str:
    identity = {
        "audio_sha256": sha256_file(audio_path),
        "primary": report.get("primary"),
        "secondary": report.get("secondary"),
        "segments": report.get("consensus_segments"),
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def llm_merge_request_artifact(audio_path: Path, report: dict) -> dict:
    merge_request_id = asr_merge_request_id(audio_path, report)
    report["merge_request_id"] = merge_request_id
    disagreement_by_id = {
        str(item.get("segment_id")): item for item in report.get("disagreements", []) if isinstance(item, dict)
    }
    template = consensus_artifact(audio_path, report)
    template["reviewer"] = {
        "kind": "llm",
        "provider": "agent-runtime",
        "model": "",
        "completed_at": "",
    }
    template_segments: list[dict] = []
    request_segments: list[dict] = []
    for segment in report.get("consensus_segments", []):
        segment_id = str(segment.get("segment_id", ""))
        disagreement = disagreement_by_id.get(segment_id, {})
        needs_merge = bool(segment.get("needs_review"))
        template_segment = dict(segment)
        template_segment["confidence"] = "" if needs_merge else "high"
        template_segment["rationale_zh"] = "" if needs_merge else "两路 ASR 一致。"
        template_segments.append(template_segment)
        request_segments.append(
            {
                **segment,
                "categories": list(disagreement.get("categories", [])),
                "task": "resolve_disagreement" if needs_merge else "confirm_agreement",
            }
        )
    template["segments"] = template_segments
    return {
        "schema_version": 1,
        "kind": "asr_llm_merge_request",
        "status": "merge_required",
        "merge_request_id": merge_request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio": {"name": audio_path.name, "sha256": sha256_file(audio_path)},
        "primary": report.get("primary", {}),
        "secondary": report.get("secondary", {}),
        "disagreement_count": int(report.get("disagreement_count", 0)),
        "instructions_zh": [
            "结合前后片段和日语语义判断每处差异，不要机械拼接两路文本。",
            "不得修改 segment_id、start、end、audio_sha256 或 merge_request_id。",
            "decision 只能使用 agreement、primary、secondary 或 merged。",
            "每个差异片段必须填写 confidence 和简短 rationale_zh。",
            "数字、姓名、地名、同音词或助词无法可靠判断时，保留 needs_review=true 并知会用户。",
        ],
        "allowed_decisions": ["agreement", "primary", "secondary", "merged"],
        "allowed_confidence": ["high", "medium", "low"],
        "segments": request_segments,
        "reviewed_transcript_template": template,
    }


def write_asr_comparison_report(
    audio_path: Path,
    primary: TranscriptionCandidate,
    secondary: TranscriptionCandidate,
) -> Path:
    artifact_dir = material_dir_for_audio(audio_path) / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifact_dir / f"{audio_path.stem}.asr-comparison.json"
    report = build_asr_comparison_report(primary, secondary)
    merge_request = llm_merge_request_artifact(audio_path, report) if report.get("unresolved_count") else None
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    consensus_path = artifact_dir / f"{audio_path.stem}.reviewed-transcript.json"
    consensus_path.write_text(
        json.dumps(consensus_artifact(audio_path, report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if merge_request is not None:
        merge_request_path = artifact_dir / f"{audio_path.stem}.llm-merge-request.json"
        merge_request_path.write_text(
            json.dumps(merge_request, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report_path


def load_reviewed_transcript(
    path: Path,
    audio_path: Path,
    merge_request_path: Path | None = None,
) -> TranscriptionCandidate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Reviewed transcript is invalid JSON: {path}: {exc}") from exc
    if payload.get("schema_version") != 1 or payload.get("kind") != "reviewed_transcript":
        raise RuntimeError("Reviewed transcript must use schema_version 1 and kind reviewed_transcript.")
    if payload.get("review_status") != "accepted":
        raise RuntimeError("Reviewed transcript must set review_status to accepted.")
    if payload.get("audio_sha256") != sha256_file(audio_path):
        raise RuntimeError("Reviewed transcript does not match the source audio hash.")
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise RuntimeError("Reviewed transcript must contain at least one segment.")
    reviewer = payload.get("reviewer")
    llm_review = isinstance(reviewer, dict) and reviewer.get("kind") == "llm"
    expected_segments: list[dict] | None = None
    if llm_review:
        if not str(reviewer.get("model", "")).strip() or not str(reviewer.get("completed_at", "")).strip():
            raise RuntimeError("LLM-reviewed transcript must record reviewer model and completed_at.")
        merge_request_id = str(payload.get("merge_request_id", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", merge_request_id):
            raise RuntimeError("LLM-reviewed transcript must preserve a valid merge_request_id.")
        if merge_request_path is None or not merge_request_path.is_file():
            raise RuntimeError("LLM-reviewed transcript requires its pending merge-request artifact.")
        request = json.loads(merge_request_path.read_text(encoding="utf-8"))
        if request.get("kind") != "asr_llm_merge_request":
            raise RuntimeError("LLM merge request has an unsupported artifact kind.")
        request_audio = request.get("audio", {})
        if request_audio.get("sha256") != sha256_file(audio_path):
            raise RuntimeError("LLM merge request does not match the source audio hash.")
        if request.get("merge_request_id") != merge_request_id:
            raise RuntimeError("LLM-reviewed transcript does not match the pending merge-request identity.")
        request_segments = request.get("segments")
        if not isinstance(request_segments, list) or len(request_segments) != len(raw_segments):
            raise RuntimeError("LLM-reviewed transcript must preserve every merge-request segment.")
        expected_segments = request_segments
    segments: list[dict] = []
    previous_end: float | None = None
    llm_segment_ids: set[str] = set()
    for index, item in enumerate(raw_segments):
        if not isinstance(item, dict) or not str(item.get("selected_text", "")).strip():
            raise RuntimeError("Every reviewed transcript segment needs selected_text.")
        if item.get("needs_review") is True or item.get("decision") == "pending_review":
            raise RuntimeError("Reviewed transcript still contains unresolved ASR disagreements.")
        if llm_review:
            segment_id = str(item.get("segment_id", ""))
            if not re.fullmatch(r"T\d{3,}", segment_id) or segment_id in llm_segment_ids:
                raise RuntimeError("Every LLM-reviewed segment must preserve a unique segment_id.")
            llm_segment_ids.add(segment_id)
            if expected_segments is not None:
                expected = expected_segments[index]
                if (
                    not isinstance(expected, dict)
                    or segment_id != str(expected.get("segment_id", ""))
                    or item.get("start") != expected.get("start")
                    or item.get("end") != expected.get("end")
                ):
                    raise RuntimeError("LLM-reviewed transcript changed merge-request segment identity or timestamps.")
            decision = str(item.get("decision", ""))
            confidence = str(item.get("confidence", ""))
            rationale = str(item.get("rationale_zh", "")).strip()
            if decision not in {"agreement", "primary", "secondary", "merged"}:
                raise RuntimeError("Every LLM-reviewed segment needs a supported decision.")
            if confidence not in {"high", "medium"}:
                raise RuntimeError("Accepted LLM-reviewed segments require high or medium confidence.")
            if not rationale:
                raise RuntimeError("Every LLM-reviewed segment needs rationale_zh.")
            selected_text = clean_transcript_text(str(item.get("selected_text", "")))
            primary_text = clean_transcript_text(str(expected.get("primary_text", "")))
            secondary_text = clean_transcript_text(str(expected.get("secondary_text", "")))
            if decision == "primary" and selected_text != primary_text:
                raise RuntimeError("LLM decision primary must preserve primary_text.")
            if decision == "secondary" and selected_text != secondary_text:
                raise RuntimeError("LLM decision secondary must preserve secondary_text.")
            if decision == "agreement" and not (
                primary_text == secondary_text == selected_text
            ):
                raise RuntimeError("LLM decision agreement requires equal ASR text and selected_text.")
        start = item.get("start")
        end = item.get("end")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or float(start) < 0
            or float(end) <= float(start)
        ):
            raise RuntimeError("Every reviewed transcript segment needs a valid non-empty timestamp range.")
        if previous_end is not None and float(start) < previous_end:
            raise RuntimeError("Reviewed transcript segments must be ordered and non-overlapping.")
        previous_end = float(end)
        segments.append(
            {
                "start": float(start),
                "end": float(end),
                "text": str(item["selected_text"]).strip(),
            }
        )
    candidate_payload = {
        "schema_version": 1,
        "engine": "reviewed-consensus",
        "locale": "ja-JP",
        "full_text": "".join(item["text"] for item in segments),
        "segments": segments,
        "timing_complete": all(item.get("start") is not None and item.get("end") is not None for item in segments),
    }
    return candidate_from_payload(audio_path, candidate_payload, "reviewed-consensus")


def transcript_view_for_profile(
    payload: dict,
    chunks: list[Chunk],
    profile: SliceProfile,
) -> tuple[list[str], str]:
    if profile.grouping == "numbered":
        sentences = chunks_to_structured_lines(chunks)
        full_text = "\n".join(sentences)
    elif profile.grouping == "exchange":
        sentences = [normalize_structured_text(chunk.text) for chunk in chunks if normalize_structured_text(chunk.text)]
        full_text = "\n".join(sentences)
    else:
        full_text = clean_transcript_text(str(payload.get("full_text", "")))
        sentences = chunks_to_sentences(chunks)
    if not sentences and full_text:
        sentences = [segment.strip() for segment in re.split(r"(?<=[。！？?])", full_text) if segment.strip()]
    return sentences, full_text


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
    persist_artifacts: bool = True,
    compare_engine: str | None = None,
) -> tuple[TranscriptionCandidate, str]:
    artifact_dir = material_dir_for_audio(audio_path) / "artifacts" if persist_artifacts else None
    artifact_stem = audio_path.stem
    try:
        base_candidate = build_candidate(
            audio_path,
            locale,
            "base",
            engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
            artifact_dir,
            artifact_stem,
        )
    except (RuntimeError, OSError) as exc:
        raise RuntimeError(f"ListenKit transcript generation failed. Original error: {exc}") from exc
    selected_candidate = base_candidate
    selected_route = str(base_candidate.payload.get("engine", "base"))

    if is_short_choice_mode(audio_path):
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
                artifact_dir,
                artifact_stem,
            )
        finally:
            try:
                slow_path.unlink(missing_ok=True)
            except OSError:
                pass
        if slow_candidate.score > base_candidate.score:
            selected_candidate = slow_candidate
            selected_route = "slow"

    if persist_artifacts:
        write_normalized_asr_artifact(audio_path, selected_candidate)
    compare_candidate_if_requested(
        audio_path,
        locale,
        selected_candidate,
        compare_engine,
        faster_whisper_python,
        faster_whisper_model,
        faster_whisper_compute_type,
        artifact_dir,
        artifact_stem,
        persist_artifacts,
    )
    return selected_candidate, selected_route


def compare_candidate_if_requested(
    audio_path: Path,
    locale: str,
    primary: TranscriptionCandidate,
    compare_engine: str | None,
    faster_whisper_python: str | None,
    faster_whisper_model: str,
    faster_whisper_compute_type: str,
    artifact_dir: Path | None,
    artifact_stem: str,
    persist_artifacts: bool,
) -> ASRComparisonResult | None:
    primary_engine = str(primary.payload.get("engine", ""))
    if compare_engine == "auto":
        compare_engine = "faster-whisper" if primary_engine == "apple" else "apple"
    if not compare_engine or compare_engine == primary_engine:
        return None
    try:
        secondary = build_candidate(
            audio_path,
            locale,
            f"compare-{compare_engine}",
            compare_engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
            artifact_dir,
            artifact_stem,
        )
    except (RuntimeError, OSError) as exc:
        report = {
            "schema_version": 2,
            "kind": "asr_comparison",
            "status": "secondary_unavailable",
            "primary": {
                "route": primary.route_label,
                "engine": str(primary.payload.get("engine", primary.route_label)),
                "segment_count": len(primary.segments),
            },
            "secondary": {"engine": compare_engine, "error": str(exc)},
            "disagreement_count": 0,
            "unresolved_count": 0,
            "disagreements": [],
            "consensus_segments": [],
        }
        report_path = None
        if persist_artifacts:
            report_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.asr-comparison.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ASRComparisonResult(primary, report, report_path, None)

    report = build_asr_comparison_report(primary, secondary)
    report_path: Path | None = None
    consensus_path: Path | None = None
    if persist_artifacts:
        write_normalized_asr_artifact(audio_path, secondary)
        report_path = write_asr_comparison_report(audio_path, primary, secondary)
        consensus_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.reviewed-transcript.json"
        merge_candidate = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.llm-merge-request.json"
        merge_request_path = merge_candidate if merge_candidate.is_file() else None
    else:
        merge_request_path = None
    return ASRComparisonResult(primary, report, report_path, consensus_path, merge_request_path)


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
    parts = note_path.stem.split("_", 2)
    suffix = parts[2] if len(parts) == 3 else note_path.stem
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
    trusted_candidates: list[str] = []
    rough_candidates: list[str] = []
    for term in sorted(confirmed_accent_index, key=lambda item: (-len(item), item)):
        if term and term in sentence:
            trusted_candidates.append(term)
    for term in offline_dictionary.known_terms():
        if term in sentence:
            trusted_candidates.append(term)
    rough_candidates.extend(offline_dictionary.tokenize_terms(sentence))
    rough_candidates.extend(rough_extract_focus_terms(sentence))
    candidates = dedupe_preserve_order(
        [
            *[term for term in trusted_candidates if len(term.strip()) >= 2],
            *[term for term in rough_candidates if is_focus_term(term)],
        ]
    )
    return candidates[:limit]


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


def accent_number_from_display(value: str) -> int | None:
    mark = accent_mark_from_display(value)
    if mark is None:
        return None
    return ACCENT_MARK_TO_TYPE.get(mark)


def kana_mora_boundary_index(text: str, mora_count: int) -> int | None:
    if mora_count <= 0:
        return None
    count = 0
    last_boundary = 0
    for index, char in enumerate(text):
        if char in SMALL_KANA and index > 0:
            last_boundary = index + 1
            continue
        count += 1
        last_boundary = index + 1
        if count == mora_count:
            return last_boundary
    return None


def downstep_accent_display(term: str, accent_display: str) -> str | None:
    if not KANA_ONLY_RE.fullmatch(term):
        return None
    accent_number = accent_number_from_display(accent_display)
    if accent_number is None or accent_number <= 0:
        return None
    boundary = kana_mora_boundary_index(term, accent_number)
    if boundary is None or boundary >= len(term):
        return None
    return f"{term[:boundary]}＼{term[boundary:]}"


def resolve_accent_note(
    term: str,
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
    accent_style: str = "circled",
) -> tuple[str | None, str]:
    confirmed = confirmed_accent_index.get(term)
    if confirmed:
        if accent_style == "downstep":
            downstep = downstep_accent_display(term, confirmed)
            if downstep:
                return downstep, f"{downstep}（已确认）"
        mark = accent_mark_from_display(confirmed)
        if mark:
            return f"{term}{mark}", f"{term}{mark}（已确认）"
        return None, f"{term}：{confirmed}（已确认）"

    candidate = offline_dictionary.lookup(term)
    if candidate:
        if accent_style == "downstep":
            downstep = downstep_accent_display(term, candidate)
            if downstep:
                return downstep, f"{downstep}（本地候选）"
        mark = accent_mark_from_display(candidate)
        if mark:
            return f"{term}{mark}", f"{term}{mark}（本地候选）"
        return None, f"{term}：{candidate}（本地候选）"

    return None, f"{term}：待确认"


def inline_accent_marks(
    sentence: str,
    terms: list[str],
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
    accent_style: str = "circled",
) -> tuple[str, list[str]]:
    rendered = sentence
    notes: list[str] = []
    replacements: list[tuple[str, str]] = []
    for term in terms:
        replacement, note = resolve_accent_note(term, confirmed_accent_index, offline_dictionary, accent_style)
        notes.append(note)
        if replacement:
            replacements.append((term, replacement))

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
    sentences: list[str] | list[LearningBlock],
    confirmed_accent_index: dict[str, str],
    offline_dictionary: StaticAccentDictionary,
    audio_slice_refs: list[str | None] | None = None,
) -> str:
    blocks: list[str] = []
    for idx, item in enumerate(sentences, start=1):
        sentence = item.text if isinstance(item, LearningBlock) else item
        terms = select_focus_terms(sentence, confirmed_accent_index, offline_dictionary)
        accented_sentence, _accent_notes = inline_accent_marks(
            sentence,
            terms,
            confirmed_accent_index,
            offline_dictionary,
            "downstep",
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


def learning_block_id(index: int) -> str:
    return f"S{index:02d}"


def chunk_text_for_alignment(chunk: Chunk) -> str:
    return clean_transcript_text(chunk.text)


def timestamp_for_text_offset(chunks: list[Chunk], offset: int, *, end_boundary: bool) -> float | None:
    cursor = 0
    for chunk in chunks:
        text = chunk_text_for_alignment(chunk)
        next_cursor = cursor + len(text)
        if not text:
            continue
        if offset < next_cursor or (end_boundary and offset == next_cursor):
            if chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
                return None
            ratio = (offset - cursor) / len(text)
            return round(chunk.start + (chunk.end - chunk.start) * ratio, 6)
        cursor = next_cursor
    if offset == cursor and chunks:
        return chunks[-1].end
    return None


def sentence_learning_blocks(sentences: list[str], chunks: list[Chunk]) -> list[LearningBlock] | None:
    sentence_texts = [clean_transcript_text(sentence) for sentence in sentences]
    chunk_texts = [chunk_text_for_alignment(chunk) for chunk in chunks]
    if not sentence_texts or "".join(sentence_texts) != "".join(chunk_texts):
        return None

    blocks: list[LearningBlock] = []
    cursor = 0
    for index, (sentence, aligned_text) in enumerate(zip(sentences, sentence_texts), start=1):
        next_cursor = cursor + len(aligned_text)
        start = timestamp_for_text_offset(chunks, cursor, end_boundary=False)
        end = timestamp_for_text_offset(chunks, next_cursor, end_boundary=True)
        if start is None or end is None or end <= start:
            return None
        blocks.append(LearningBlock(id=learning_block_id(index), text=sentence, start=start, end=end, kind="sentence"))
        cursor = next_cursor
    return blocks


FULLWIDTH_DIGIT_TRANSLATION = str.maketrans("０１２３４５６７８９", "0123456789")
KANJI_NUMBER_LABELS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def parse_group_number(text: str) -> int | None:
    normalized = normalize_structured_text(text).translate(FULLWIDTH_DIGIT_TRANSLATION)
    if normalized in KANJI_NUMBER_LABELS:
        return KANJI_NUMBER_LABELS[normalized]
    if re.fullmatch(r"\d+", normalized):
        return int(normalized)
    return None


def numbered_dialogue_learning_blocks(chunks: list[Chunk]) -> list[LearningBlock] | None:
    blocks: list[LearningBlock] = []
    current_number: int | None = None
    utterances: list[str] = []
    start: float | None = None
    end: float | None = None

    def flush() -> bool:
        nonlocal current_number, utterances, start, end
        if current_number is None:
            return True
        rendered_dialogue = render_numbered_ab_dialogue(utterances)
        if rendered_dialogue is None or start is None or end is None or end <= start:
            return False
        blocks.append(
            LearningBlock(
                id=learning_block_id(len(blocks) + 1),
                text="\n".join([str(current_number), *rendered_dialogue]),
                start=start,
                end=end,
                kind="numbered-dialogue",
            )
        )
        current_number = None
        utterances = []
        start = None
        end = None
        return True

    expected_number: int | None = None
    for chunk in chunks:
        text = normalize_structured_text(chunk.text)
        if not text or text.startswith("セクション"):
            continue
        number = parse_group_number(text)
        if number is not None:
            if not flush() or (expected_number is not None and number != expected_number):
                return None
            current_number = number
            if chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
                return None
            start = chunk.start
            end = chunk.end
            expected_number = number + 1
            continue
        numbered = re.match(r"^([0-9０-９]+)[.。]\s*(.+)$", text)
        if numbered:
            number = int(numbered.group(1).translate(FULLWIDTH_DIGIT_TRANSLATION))
            if not flush() or (expected_number is not None and number != expected_number):
                return None
            current_number = number
            expected_number = number + 1
            text = numbered.group(2)
        if current_number is None or chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
            return None
        utterances.append(text)
        start = chunk.start if start is None else start
        end = chunk.end

    if not flush() or len(blocks) < 2:
        return None
    return blocks


def dialogue_exchange_learning_blocks(chunks: list[Chunk]) -> list[LearningBlock] | None:
    normalized: list[Chunk] = []
    for chunk in chunks:
        text = normalize_structured_text(chunk.text)
        if not text or text.startswith("セクション") or parse_group_number(text) is not None:
            return None
        if chunk.start is None or chunk.end is None or chunk.end <= chunk.start:
            return None
        normalized.append(Chunk(start=chunk.start, end=chunk.end, text=text))
    if not normalized or len(normalized) % 2 != 0:
        return None

    pairs: list[list[Chunk]] = []
    for index in range(0, len(normalized), 2):
        pair = normalized[index : index + 2]
        if render_conservative_ab_dialogue([item.text for item in pair]) is None:
            return None
        pairs.append(pair)

    groups: list[list[Chunk]] = []
    index = 0
    while index < len(pairs):
        current = pairs[index]
        if index + 1 < len(pairs):
            following = pairs[index + 1]
            gap = float(following[0].start) - float(current[-1].end)
            combined = current + following
            if gap <= 1.0 and render_conservative_ab_dialogue([item.text for item in combined]) is not None:
                groups.append(combined)
                index += 2
                continue
        groups.append(current)
        index += 1

    blocks: list[LearningBlock] = []
    for index, group in enumerate(groups, start=1):
        rendered = render_conservative_ab_dialogue([item.text for item in group])
        if rendered is None:
            return None
        blocks.append(
            LearningBlock(
                id=learning_block_id(index),
                text="\n".join(rendered),
                start=float(group[0].start),
                end=float(group[-1].end),
                kind="dialogue-exchange",
            )
        )
    return blocks


def detect_slice_profile(chunks: list[Chunk]) -> SliceProfile:
    if numbered_dialogue_learning_blocks(chunks) is not None:
        return SliceProfile("dialogue", "numbered", "auto", "included", NUMBERED_DIALOGUE_SLICE_PADDING_SECONDS)
    if dialogue_exchange_learning_blocks(chunks) is not None:
        return SliceProfile("dialogue", "exchange", "auto", "none", INTENSIVE_SLICE_PADDING_SECONDS)
    return SliceProfile("sentence", "sentence", "auto", "none", INTENSIVE_SLICE_PADDING_SECONDS)


def slice_profile_from_mapping(raw: object, source: str) -> SliceProfile | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise RuntimeError("Slice manifest field 'slice_profile' must be an object.")
    kind = str(raw.get("kind", ""))
    grouping = str(raw.get("grouping", ""))
    declared_source = str(raw.get("source", ""))
    number_markers = str(raw.get("number_markers", ""))
    padding = raw.get("padding_seconds")
    valid = {
        ("dialogue", "numbered", "included", NUMBERED_DIALOGUE_SLICE_PADDING_SECONDS),
        ("dialogue", "exchange", "none", INTENSIVE_SLICE_PADDING_SECONDS),
        ("sentence", "sentence", "none", INTENSIVE_SLICE_PADDING_SECONDS),
    }
    if isinstance(padding, bool) or not isinstance(padding, (int, float)):
        raise RuntimeError("Slice profile padding_seconds must be a number.")
    if declared_source not in {"auto", "cli", "manifest"}:
        raise RuntimeError("Slice profile source must be auto, cli, or manifest.")
    normalized = (kind, grouping, number_markers, float(padding))
    if normalized not in valid:
        raise RuntimeError("Slice profile fields contain an unsupported combination.")
    return SliceProfile(kind, grouping, source, number_markers, float(padding))


def load_manifest_slice_profile(path: Path, reviewed_only: bool = False) -> SliceProfile | None:
    payload = load_listenkit_json(path)
    if payload.get("version") != 1:
        raise RuntimeError("Slice manifest field 'version' must be 1.")
    raw_profile = payload.get("slice_profile")
    if reviewed_only and (not isinstance(raw_profile, dict) or raw_profile.get("source") != "manifest"):
        return None
    return slice_profile_from_mapping(raw_profile, "manifest")


def resolve_slice_profile(
    requested: str,
    manifest_profile: SliceProfile | None,
    detected: SliceProfile,
    chunks: list[Chunk],
) -> SliceProfile:
    if requested not in SLICE_PROFILE_CHOICES:
        raise RuntimeError(f"Unsupported slice profile: {requested}")
    if requested == "sentence":
        return SliceProfile("sentence", "sentence", "cli", "none", INTENSIVE_SLICE_PADDING_SECONDS)
    if requested == "dialogue":
        numbered = numbered_dialogue_learning_blocks(chunks)
        if numbered is not None:
            return SliceProfile("dialogue", "numbered", "cli", "included", NUMBERED_DIALOGUE_SLICE_PADDING_SECONDS)
        exchange = dialogue_exchange_learning_blocks(chunks)
        if exchange is not None:
            return SliceProfile("dialogue", "exchange", "cli", "none", INTENSIVE_SLICE_PADDING_SECONDS)
        if manifest_profile is not None and manifest_profile.kind == "dialogue":
            return SliceProfile(
                manifest_profile.kind,
                manifest_profile.grouping,
                "cli",
                manifest_profile.number_markers,
                manifest_profile.padding_seconds,
            )
        raise RuntimeError(
            "Forced dialogue slice profile could not derive reliable dialogue blocks. "
            "Provide a reviewed --slice-manifest with dialogue slice_profile metadata and explicit ranges."
        )
    if manifest_profile is not None:
        return manifest_profile
    return detected


def automatic_learning_blocks(
    sentences: list[str],
    chunks: list[Chunk],
    profile: SliceProfile,
) -> list[LearningBlock] | None:
    if profile.grouping == "numbered":
        return numbered_dialogue_learning_blocks(chunks)
    if profile.grouping == "exchange":
        return dialogue_exchange_learning_blocks(chunks)
    return sentence_learning_blocks(sentences, chunks)


def load_manual_learning_blocks(path: Path, automatic_blocks: list[LearningBlock]) -> list[LearningBlock]:
    payload = load_listenkit_json(path)
    if payload.get("version") != 1:
        raise RuntimeError("Slice manifest field 'version' must be 1.")
    raw_slices = payload.get("slices")
    if not isinstance(raw_slices, list) or not raw_slices:
        raise RuntimeError("Slice manifest field 'slices' must be a non-empty list.")
    automatic_by_id = {block.id: block for block in automatic_blocks}
    blocks: list[LearningBlock] = []
    seen_ids: set[str] = set()
    previous_end: float | None = None
    for raw in raw_slices:
        if not isinstance(raw, dict):
            raise RuntimeError("Each slice manifest entry must be an object.")
        block_id = str(raw.get("id", ""))
        if not re.fullmatch(r"S\d{2,}", block_id):
            raise RuntimeError(f"Slice id must match SNN: {block_id!r}")
        if block_id in seen_ids:
            raise RuntimeError(f"Duplicate slice id: {block_id}")
        start = raw.get("start")
        end = raw.get("end")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise RuntimeError(f"Slice {block_id} start/end must be numbers.")
        start_value = float(start)
        end_value = float(end)
        if start_value < 0 or end_value <= start_value:
            raise RuntimeError(f"Slice {block_id} must satisfy 0 <= start < end.")
        if previous_end is not None and start_value < previous_end:
            raise RuntimeError(f"Slice {block_id} overlaps the previous slice.")
        fallback = automatic_by_id.get(block_id)
        text = str(raw.get("text", "")).strip() or (fallback.text if fallback else "")
        if not text:
            raise RuntimeError(f"Slice {block_id} needs text when automatic grouping cannot supply it.")
        seen_ids.add(block_id)
        blocks.append(LearningBlock(id=block_id, text=text, start=start_value, end=end_value, kind="manual"))
        previous_end = end_value
    return blocks


def slice_manifest_path(audio_path: Path) -> Path:
    return material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.slices.json"


def write_slice_manifest(path: Path, blocks: list[LearningBlock], profile: SliceProfile) -> None:
    payload = {
        "version": 1,
        "slice_profile": profile.to_manifest_dict(),
        "slices": [
            {"id": block.id, "start": block.start, "end": block.end, "text": block.text}
            for block in blocks
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slice_export_report_path(audio_path: Path) -> Path:
    return material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.slice-export.json"


def export_learning_block_slices(
    audio_path: Path,
    blocks: list[LearningBlock],
    manifest_path: Path,
    profile: SliceProfile,
) -> SliceExportResult:
    preflight_intensive_slice_tooling()
    command = [
        sys.executable,
        str(listenkit_export_audio_slices_script_path()),
        "--input",
        str(audio_path),
        "--manifest",
        str(manifest_path),
        "--output-dir",
        str(slice_attach_dir(audio_path)),
        "--padding-seconds",
        str(profile.padding_seconds),
        "--overwrite",
    ]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ListenKit slice export failed.")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ListenKit slice export returned invalid JSON: {exc}") from exc
    slices = report.get("slices")
    if not isinstance(slices, list) or len(slices) != len(blocks):
        raise RuntimeError("ListenKit slice export report count does not match learning blocks.")
    report["source"] = f"attach/{audio_path.name}"
    report["slice_profile"] = profile.to_manifest_dict()
    refs: list[str] = []
    for block, item in zip(blocks, slices):
        if item.get("id") != block.id or item.get("status") != "exported":
            raise RuntimeError(f"ListenKit slice export report is invalid for {block.id}.")
        relative_path = f"attach/{Path(str(item.get('path', ''))).name}"
        item["path"] = relative_path
        refs.append(relative_path)
    report_path = slice_export_report_path(audio_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return SliceExportResult(refs=refs, report_path=report_path, report=report)


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
    discovered = discover_vault_root(path)
    if discovered is not None:
        return discovered
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
    current_path = vault_root / ".lingotrace" / "paths.json"
    if current_path.is_file():
        try:
            payload = json.loads(current_path.read_text(encoding="utf-8"))
            return {
                str(item["role"]): str(item["relative_path"])
                for item in payload.get("path_roles", [])
                if isinstance(item, dict) and item.get("role") and item.get("relative_path")
            }
        except (OSError, json.JSONDecodeError):
            return {}
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
        vault_root / roles.get("pronunciation_accent_root", "学习系统/发音/アクセント"),
        vault_root / roles.get("pronunciation_phoneme_root", "学习系统/发音/音素"),
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
    slice_profile: SliceProfile | None = None,
    confirmed_accent_index: dict[str, str] | None = None,
    offline_dictionary: StaticAccentDictionary | None = None,
    audio_slice_refs: list[str | None] | None = None,
    listening_mode: str = "intensive",
    learning_blocks: list[LearningBlock] | None = None,
) -> tuple[str, bool]:
    script_section, dialogue_content_mode = render_dialogue_script_section(sentences, chunks, slice_profile)
    existing_sections = parse_sections(existing_body or "")
    known_headings = {"精听学习包", "脚本", "常用语块", "可直接背的常用句", "素材说明"}
    preserved_sections = {heading: content for heading, content in existing_sections}
    if short_choice_mode:
        script_section = choose_short_choice_script(
            script_section,
            preserved_sections.get("脚本"),
            audio_path,
        )
    if "常用语块" in preserved_sections:
        common_heading = "常用语块"
        common_section = preserved_sections[common_heading]
    elif "可直接背的常用句" in preserved_sections:
        # Preserve legacy user-curated sections verbatim, including their heading.
        common_heading = "可直接背的常用句"
        common_section = preserved_sections[common_heading]
    else:
        common_heading = "常用语块"
        common_section = COMMON_SECTION_PLACEHOLDER
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
            learning_blocks or sentences,
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
        f"## {common_heading}",
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


def validate_intensive_slice_output(
    audio_path: Path,
    blocks: list[LearningBlock],
    audio_slice_refs: list[str],
    body: str,
) -> None:
    expected = len(blocks)
    heading_count = len(re.findall(r"^### S\d{2,}$", body, flags=re.MULTILINE))
    embed_count = len(re.findall(r"!\[\[attach/[^]]+_S\d{2,}\.m4a\]\]", body))
    if "（语音切片待生成）" in body:
        raise RuntimeError("Intensive note still contains audio-slice placeholders.")
    if len(audio_slice_refs) != expected or heading_count != expected or embed_count != expected:
        raise RuntimeError(
            "Intensive slice verification failed: "
            f"learning_blocks={expected}, refs={len(audio_slice_refs)}, headings={heading_count}, embeds={embed_count}."
        )
    material_dir = material_dir_for_audio(audio_path)
    for ref in audio_slice_refs:
        output_path = material_dir / ref
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise RuntimeError(f"Intensive slice verification failed: missing or empty file: {output_path}")


def write_intensive_review_sidecar(
    audio_path: Path,
    note_path: Path,
    route_label: str,
    manifest_path: Path,
    slice_export_result: SliceExportResult,
    learning_blocks: list[LearningBlock],
    profile: SliceProfile,
    source_url: str | None = None,
) -> Path:
    artifact_dir = material_dir_for_audio(audio_path) / "artifacts"
    review_path = artifact_dir / f"{audio_path.stem}.review.md"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {audio_path.stem} 精听制作记录",
        "",
        f"- source_audio: `{audio_path}`",
        f"- note: `{note_path}`",
        f"- route: `{route_label}`",
        f"- manifest: `{manifest_path}`",
        f"- slice_export_report: `{slice_export_result.report_path}`",
        f"- slice_profile_kind: {profile.kind}",
        f"- slice_profile_grouping: {profile.grouping}",
        f"- slice_profile_source: {profile.source}",
        f"- number_markers: {profile.number_markers}",
        f"- slice_padding_seconds: {profile.padding_seconds}",
        "- allow_overlap: false",
        f"- learning_block_count: {len(learning_blocks)}",
    ]
    if source_url:
        lines.append(f"- source_url: <{source_url}>")
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Review the saved `.listenkit.json` / `.listenkit.md` artifacts when ASR text is disputed.",
            "- If slice boundaries sound wrong, edit the reviewed manifest and rerun the intensive export.",
            "- Padding is bounded by the non-overlap export policy and does not replace corrected timestamps.",
            "",
            "## Blocks",
            "",
        ]
    )
    for block in learning_blocks:
        lines.extend(
            [
                f"### {block.id}",
                "",
                f"- range: {block.start:.2f}-{block.end:.2f}",
                f"- text: {block.text}",
                "",
            ]
        )
    review_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return review_path


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
    slice_manifest_override: str | None = None,
    slice_profile_request: str = "auto",
    compare_engine: str | None = None,
    reviewed_transcript_override: str | None = None,
    merge_request_override: str | None = None,
    accent_vault_root: Path | None = None,
    rename_generated_note: bool = True,
) -> str:
    if discover_vault_root(audio_path) is not None:
        raise RuntimeError(
            "Direct listening generator writes to a LingoTrace Vault are disabled. "
            "Use the CLI preparation workflow so writes pass through the core guard."
        )
    preflight_source_audio(audio_path)
    if listening_mode == "intensive":
        preflight_intensive_slice_tooling()
    reviewed_path = Path(reviewed_transcript_override).expanduser() if reviewed_transcript_override else None
    merge_request_path = Path(merge_request_override).expanduser() if merge_request_override else None
    comparison_runtime_issue: str | None = None
    comparison_review_issue: str | None = None
    if reviewed_path is not None:
        canonical_merge_request = (
            material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.llm-merge-request.json"
        )
        pending_merge_request = merge_request_path or (
            canonical_merge_request if canonical_merge_request.is_file() else None
        )
        candidate = load_reviewed_transcript(
            reviewed_path,
            audio_path,
            pending_merge_request,
        )
        route_label = "reviewed-consensus"
        if not dry_run:
            canonical_reviewed_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.reviewed-transcript.json"
            canonical_reviewed_path.parent.mkdir(parents=True, exist_ok=True)
            if reviewed_path.resolve() != canonical_reviewed_path.resolve():
                shutil.copy2(reviewed_path, canonical_reviewed_path)
            if pending_merge_request is not None and pending_merge_request.resolve() != canonical_merge_request.resolve():
                shutil.copy2(pending_merge_request, canonical_merge_request)
            write_normalized_asr_artifact(audio_path, candidate)
    else:
        if candidate_route is None:
            candidate, route_label = transcribe_with_heuristics(
                audio_path,
                locale,
                engine,
                faster_whisper_python,
                faster_whisper_model,
                faster_whisper_compute_type,
                persist_artifacts=not dry_run,
                compare_engine=compare_engine,
            )
        else:
            candidate, route_label = candidate_route
            if not dry_run:
                write_normalized_asr_artifact(audio_path, candidate)
            if compare_engine:
                compare_candidate_if_requested(
                    audio_path,
                    locale,
                    candidate,
                    compare_engine,
                    faster_whisper_python,
                    faster_whisper_model,
                    faster_whisper_compute_type,
                    material_dir_for_audio(audio_path) / "artifacts" if not dry_run else None,
                    audio_path.stem,
                    not dry_run,
                )
        if compare_engine and not dry_run:
            comparison_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.asr-comparison.json"
            if comparison_path.is_file():
                comparison_payload = json.loads(comparison_path.read_text(encoding="utf-8"))
                if comparison_payload.get("status") == "secondary_unavailable":
                    secondary = comparison_payload.get("secondary", {})
                    comparison_runtime_issue = (
                        f"第二 ASR（{secondary.get('engine', 'unknown')}）不可用，本次降级为单 ASR；"
                        f"限制与错误已记录在 artifacts/{comparison_path.name}。"
                    )
            consensus_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.reviewed-transcript.json"
            if consensus_path.is_file():
                try:
                    candidate = load_reviewed_transcript(consensus_path, audio_path)
                    route_label = "reviewed-consensus"
                    write_normalized_asr_artifact(audio_path, candidate)
                except RuntimeError as exc:
                    merge_request_path = material_dir_for_audio(audio_path) / "artifacts" / f"{audio_path.stem}.llm-merge-request.json"
                    comparison_review_issue = (
                        f"ASR comparison requires LLM merge before final note generation: {exc} "
                        f"Use {merge_request_path} to create a temporary reviewed transcript and rerun with "
                        "--reviewed-transcript."
                    )
    raw_chunks = raw_segments_to_chunks(candidate.payload.get("segments", []))
    manifest_profile = None
    active_manifest_path: Path | None = None
    if slice_manifest_override:
        active_manifest_path = Path(slice_manifest_override).expanduser()
        manifest_profile = load_manifest_slice_profile(active_manifest_path)
    else:
        default_manifest_path = slice_manifest_path(audio_path)
        if default_manifest_path.is_file():
            reviewed_profile = load_manifest_slice_profile(default_manifest_path, reviewed_only=True)
            if reviewed_profile is not None:
                active_manifest_path = default_manifest_path
                manifest_profile = reviewed_profile
    slice_profile = resolve_slice_profile(
        slice_profile_request,
        manifest_profile,
        candidate.slice_profile,
        raw_chunks,
    )
    profile_chunks = raw_chunks if slice_profile.kind == "dialogue" else candidate.segments
    sentences, _full_text = transcript_view_for_profile(candidate.payload, profile_chunks, slice_profile)
    short_choice_mode = is_short_choice_mode(audio_path)
    note_path = resolve_note_path(audio_path, note_override)
    if forced_title:
        title = infer_title(audio_path.stem, forced_title, sentences)
    else:
        title = infer_title_from_existing_note(audio_path, note_path) or infer_title(audio_path.stem, None, sentences)
    target_note_path = desired_note_path(audio_path, title)
    existed = note_path.exists() if note_path is not None else False
    should_rename_note = (
        rename_generated_note
        and note_override is None
        and note_path is not None
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
    if comparison_review_issue:
        material_note += f"\n\n转写交叉比对尚未完成审核：{comparison_review_issue}"
    if comparison_runtime_issue:
        material_note += f"\n\n转写交叉比对限制：{comparison_runtime_issue}"

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
    learning_blocks: list[LearningBlock] | None = None
    audio_slice_refs: list[str] | None = None
    slice_export_result: SliceExportResult | None = None
    if resolved_listening_mode == "intensive":
        preflight_intensive_slice_tooling()
        automatic_blocks = automatic_learning_blocks(sentences, profile_chunks, slice_profile)
        if active_manifest_path is not None:
            manifest_path = active_manifest_path
            learning_blocks = load_manual_learning_blocks(manifest_path, automatic_blocks or [])
        else:
            manifest_path = slice_manifest_path(audio_path)
            learning_blocks = automatic_blocks
        if not learning_blocks:
            raise RuntimeError(
                "Unable to derive reliable intensive learning blocks from transcript timestamps. "
                "Provide a reviewed --slice-manifest with explicit ranges and text."
            )
        if frontmatter_lines:
            set_scalar(frontmatter_lines, "segment_count", str(len(learning_blocks)))
        if not dry_run:
            if active_manifest_path is None:
                write_slice_manifest(manifest_path, learning_blocks, slice_profile)
            slice_export_result = export_learning_block_slices(audio_path, learning_blocks, manifest_path, slice_profile)
            audio_slice_refs = slice_export_result.refs
    body, dialogue_content_mode = build_body(
        title,
        audio_ref_for_note(audio_path),
        sentences,
        profile_chunks,
        audio_path,
        existing_body,
        material_note,
        short_choice_mode,
        slice_profile,
        load_confirmed_accent_index(accent_vault_root or find_vault_root_from_path(audio_path)),
        offline_dictionary or load_offline_dictionary(required=False),
        audio_slice_refs,
        resolved_listening_mode,
        learning_blocks,
    )
    if resolved_listening_mode == "intensive" and not dry_run:
        validate_intensive_slice_output(audio_path, learning_blocks or [], audio_slice_refs or [], body)
    if not frontmatter_lines:
        frontmatter_lines = build_default_frontmatter(
            audio_path,
            len(learning_blocks) if learning_blocks is not None else len(sentences),
            short_choice_mode,
            dialogue_content_mode,
            resolved_listening_mode,
        )
    rendered = render_note(frontmatter_lines, body)
    if dry_run:
        return f"=== {write_note_path} ===\n{rendered}"
    write_note_path.write_text(rendered, encoding="utf-8")
    if resolved_listening_mode == "intensive" and learning_blocks and slice_export_result:
        write_intensive_review_sidecar(
            audio_path,
            write_note_path,
            route_label,
            manifest_path,
            slice_export_result,
            learning_blocks,
            slice_profile,
            source_url,
        )
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
    slice_manifest_override: str | None = None,
    slice_profile_request: str = "auto",
    compare_engine: str | None = None,
    reviewed_transcript_override: str | None = None,
    merge_request_override: str | None = None,
    accent_vault_root: Path | None = None,
) -> str:
    if discover_vault_root(output_dir) is not None:
        raise RuntimeError(
            "Direct URL listening writes to a LingoTrace Vault are disabled. "
            "Use the CLI preparation workflow so writes pass through the core guard."
        )
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
        slice_manifest_override=slice_manifest_override,
        slice_profile_request=slice_profile_request,
        compare_engine=compare_engine,
        reviewed_transcript_override=reviewed_transcript_override,
        merge_request_override=merge_request_override,
        accent_vault_root=accent_vault_root,
    )
    if dry_run:
        return f"Source URL: {url}\nFinal audio: {final_audio_path}\n{result}"
    return f"Source URL: {url}\nFinal audio: {final_audio_path}\n{result}"


def _tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not root.exists():
        return snapshot
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        snapshot[path.relative_to(root).as_posix()] = sha256_file(path)
    return snapshot


def _copy_preparation_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _mapped_stage_path(stage_vault: Path, vault_root: Path, source: Path) -> Path:
    return stage_vault / source.resolve().relative_to(vault_root.resolve())


def effective_compare_engine(
    requested: str | None,
    *,
    single_asr: bool,
    listening_mode: str | None,
    audio_path: Path,
    existing_note: Path | None,
) -> str | None:
    """Keep legacy routing inputs while making dual ASR the stable default."""
    if single_asr:
        return None
    if requested and requested != "auto":
        return requested
    return "auto"


def is_review_artifact_path(path: str) -> bool:
    return "/artifacts/" in f"/{path}" and (
        path.endswith(".listenkit.json")
        or path.endswith(".listenkit.md")
        or path.endswith(".asr.json")
        or path.endswith(".asr-comparison.json")
        or path.endswith(".llm-merge-request.json")
        or path.endswith(".reviewed-transcript.json")
        or path.endswith(".source.json")
    )


def llm_handoff_artifact_sources(merge_request_path: Path) -> list[Path]:
    suffix = ".llm-merge-request.json"
    if not merge_request_path.name.endswith(suffix):
        return [merge_request_path] if merge_request_path.is_file() else []
    stem = merge_request_path.name[: -len(suffix)]
    return sorted(
        path
        for path in merge_request_path.parent.glob(f"{stem}.*")
        if path.is_file() and is_review_artifact_path(f"artifacts/{path.name}")
    )


def restore_llm_handoff_artifacts(merge_request_path: Path, artifact_dir: Path) -> None:
    for source in llm_handoff_artifact_sources(merge_request_path):
        destination = artifact_dir / source.name
        _copy_preparation_file(source, destination)
        destination.chmod(0o600)


def _bundle_from_stage(
    *,
    vault_root: Path,
    stage_vault: Path,
    initial: dict[str, str],
    summary: str,
) -> PreparedListeningBundle:
    final = _tree_snapshot(stage_vault)
    changed = [path for path, digest in final.items() if initial.get(path) != digest]
    if not changed:
        raise RuntimeError("Listening preparation produced no changed artifacts.")
    note_candidates = [
        path
        for path in changed
        if path.endswith(".md") and "/artifacts/" not in f"/{path}" and "/attach/" not in f"/{path}"
    ]
    if len(note_candidates) != 1:
        raise RuntimeError(f"Listening preparation must produce exactly one note; found {note_candidates}.")
    note_path = note_candidates[0]
    files: list[dict[str, object]] = []
    for relative_path in changed:
        target = vault_root / relative_path
        files.append(
            {
                "path": relative_path,
                "source_path": str(stage_vault / relative_path),
                "action": "update_listening_note" if relative_path == note_path and target.exists() else (
                    "create_listening_note" if relative_path == note_path else "write_listening_artifact"
                ),
                "reason": "prepared listening note" if relative_path == note_path else "prepared listening provenance or media artifact",
            }
        )
    review_required = False
    merge_model: str | None = None
    consensus_files = [stage_vault / path for path in changed if path.endswith(".reviewed-transcript.json")]
    for consensus_path in consensus_files:
        payload = json.loads(consensus_path.read_text(encoding="utf-8"))
        if payload.get("review_status") != "accepted":
            review_required = True
            break
        reviewer = payload.get("reviewer")
        if isinstance(reviewer, dict) and reviewer.get("kind") == "llm":
            merge_model = str(reviewer.get("model") or "agent-runtime")
    merge_request_paths = [path for path in changed if path.endswith(".llm-merge-request.json")]
    llm_merge_request_path = merge_request_paths[0] if merge_request_paths else None
    disagreement_count = 0
    asr_validation_status = "single"
    if merge_model is not None:
        asr_validation_status = "merged"
        llm_merge_request_path = None
        for consensus_path in consensus_files:
            payload = json.loads(consensus_path.read_text(encoding="utf-8"))
            disagreement_count += sum(
                1
                for segment in payload.get("segments", [])
                if isinstance(segment, dict) and segment.get("decision") != "agreement"
            )
    elif llm_merge_request_path is not None:
        merge_request = json.loads((stage_vault / llm_merge_request_path).read_text(encoding="utf-8"))
        disagreement_count = int(merge_request.get("disagreement_count", 0))
        asr_validation_status = "disagreement"
    else:
        comparison_files = [stage_vault / path for path in changed if path.endswith(".asr-comparison.json")]
        for comparison_path in comparison_files:
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
            if comparison.get("status") == "secondary_unavailable":
                asr_validation_status = "secondary_unavailable"
                break
            if comparison.get("status") == "complete" and int(comparison.get("disagreement_count", 0)) == 0:
                asr_validation_status = "agreed"
    return PreparedListeningBundle(
        vault_root=vault_root,
        note_path=note_path,
        files=files,
        summary=summary,
        overwrite_required=(vault_root / note_path).exists(),
        staging_root=stage_vault.parent,
        review_required=review_required,
        llm_merge_request_path=llm_merge_request_path,
        disagreement_count=disagreement_count,
        merge_model=merge_model,
        asr_validation_status=asr_validation_status,
    )


def materialize_llm_merge_request_handoff(bundle: PreparedListeningBundle) -> Path | None:
    if not bundle.review_required or not bundle.llm_merge_request_path:
        return None
    current = Path(bundle.llm_merge_request_path)
    if current.is_absolute():
        if not current.is_file():
            raise RuntimeError(f"LLM merge request is missing: {current}")
        return current
    source = bundle.staging_root / "vault" / current
    if not source.is_file():
        raise RuntimeError(f"Prepared LLM merge request is missing: {source}")
    handoff_root = Path(tempfile.mkdtemp(prefix="lingotrace-llm-merge-"))
    for artifact_source in llm_handoff_artifact_sources(source):
        destination = handoff_root / artifact_source.name
        shutil.copy2(artifact_source, destination)
        destination.chmod(0o400)
    destination = handoff_root / source.name
    bundle.llm_merge_request_path = str(destination)
    return destination


def prepare_local_listening_bundle(
    *,
    vault_root: Path,
    audio_path: Path,
    note_override: Path | None,
    locale: str,
    title: str | None,
    engine: str,
    compare_engine: str | None,
    faster_whisper_python: str | None,
    faster_whisper_model: str,
    faster_whisper_compute_type: str,
    offline_dictionary: StaticAccentDictionary,
    listening_mode: str | None,
    slice_manifest_override: Path | None,
    slice_profile: str,
    reviewed_transcript: Path | None,
    merge_request: Path | None = None,
) -> PreparedListeningBundle:
    validate_listening_target(vault_root, audio_path)
    material_dir = material_dir_for_audio(audio_path)
    staging_root = Path(tempfile.mkdtemp(prefix="lingotrace-listening-prepare-"))
    stage_vault = staging_root / "vault"
    stage_audio = _mapped_stage_path(stage_vault, vault_root, audio_path)
    _copy_preparation_file(audio_path, stage_audio)

    existing_note = note_override or resolve_note_path(audio_path, None)
    stage_note: Path | None = None
    if existing_note is not None and existing_note.is_file():
        validate_listening_target(vault_root, existing_note)
        stage_note = _mapped_stage_path(stage_vault, vault_root, existing_note)
        _copy_preparation_file(existing_note, stage_note)

    default_manifest = slice_manifest_path(audio_path)
    if default_manifest.is_file():
        _copy_preparation_file(default_manifest, _mapped_stage_path(stage_vault, vault_root, default_manifest))

    stage_manifest: Path | None = None
    if slice_manifest_override is not None:
        validate_listening_target(vault_root, slice_manifest_override)
        stage_manifest = _mapped_stage_path(stage_vault, vault_root, slice_manifest_override)
        _copy_preparation_file(slice_manifest_override, stage_manifest)

    stage_reviewed: Path | None = None
    stage_merge_request: Path | None = None
    source_merge_request: Path | None = None
    if reviewed_transcript is not None:
        stage_reviewed = material_dir_for_audio(stage_audio) / "artifacts" / f"{audio_path.stem}.accepted-reviewed-transcript.json"
        _copy_preparation_file(reviewed_transcript, stage_reviewed)
        source_merge_request = merge_request or (
            material_dir / "artifacts" / f"{audio_path.stem}.llm-merge-request.json"
        )
        if source_merge_request.is_file():
            stage_merge_request = material_dir_for_audio(stage_audio) / "artifacts" / f"{audio_path.stem}.accepted-merge-request.json"
            _copy_preparation_file(
                source_merge_request,
                stage_merge_request,
            )

    initial = _tree_snapshot(stage_vault)
    if source_merge_request is not None and source_merge_request.is_file():
        restore_llm_handoff_artifacts(
            source_merge_request,
            material_dir_for_audio(stage_audio) / "artifacts",
        )
    try:
        summary = process_one(
            stage_audio,
            str(stage_note) if stage_note is not None else None,
            locale,
            title,
            False,
            engine,
            faster_whisper_python,
            faster_whisper_model,
            faster_whisper_compute_type,
            offline_dictionary=offline_dictionary,
            listening_mode=listening_mode,
            slice_manifest_override=str(stage_manifest) if stage_manifest is not None else None,
            slice_profile_request=slice_profile,
            compare_engine=compare_engine,
            reviewed_transcript_override=str(stage_reviewed) if stage_reviewed is not None else None,
            merge_request_override=str(stage_merge_request) if stage_merge_request is not None else None,
            accent_vault_root=vault_root,
            rename_generated_note=False,
        )
        return _bundle_from_stage(
            vault_root=vault_root,
            stage_vault=stage_vault,
            initial=initial,
            summary=summary.replace(str(stage_vault), str(vault_root)),
        )
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise


def prepare_url_listening_bundle(
    *,
    vault_root: Path,
    url: str,
    output_dir: Path,
    note_override: Path | None,
    locale: str,
    title: str | None,
    engine: str,
    compare_engine: str | None,
    faster_whisper_python: str | None,
    audio_format: str,
    offline_dictionary: StaticAccentDictionary,
    listening_mode: str | None,
    slice_manifest_override: Path | None,
    slice_profile: str,
    reviewed_transcript: Path | None,
    merge_request: Path | None = None,
) -> PreparedListeningBundle:
    validate_listening_target(vault_root, output_dir)
    staging_root = Path(tempfile.mkdtemp(prefix="lingotrace-listening-url-prepare-"))
    stage_vault = staging_root / "vault"
    stage_output = _mapped_stage_path(stage_vault, vault_root, output_dir)
    stage_output.mkdir(parents=True, exist_ok=True)
    stage_note: Path | None = None
    if note_override is not None and note_override.is_file():
        stage_note = _mapped_stage_path(stage_vault, vault_root, note_override)
        _copy_preparation_file(note_override, stage_note)
    stage_manifest: Path | None = None
    if slice_manifest_override is not None:
        stage_manifest = _mapped_stage_path(stage_vault, vault_root, slice_manifest_override)
        _copy_preparation_file(slice_manifest_override, stage_manifest)
    stage_reviewed: Path | None = None
    stage_merge_request: Path | None = None
    source_merge_request: Path | None = None
    if reviewed_transcript is not None:
        stage_reviewed = stage_output / "artifacts" / "accepted-reviewed-transcript.json"
        _copy_preparation_file(reviewed_transcript, stage_reviewed)
        source_merge_request = merge_request
        if source_merge_request is None:
            existing_artifact_dir = output_dir / "artifacts"
            existing_requests = sorted(existing_artifact_dir.glob("*.llm-merge-request.json")) if existing_artifact_dir.is_dir() else []
            source_merge_request = existing_requests[0] if len(existing_requests) == 1 else None
        if source_merge_request is not None and source_merge_request.is_file():
            stage_merge_request = stage_output / "artifacts" / "accepted-merge-request.json"
            _copy_preparation_file(source_merge_request, stage_merge_request)
    initial = _tree_snapshot(stage_vault)
    if source_merge_request is not None and source_merge_request.is_file():
        restore_llm_handoff_artifacts(source_merge_request, stage_output / "artifacts")
    try:
        summary = process_url(
            url,
            stage_output,
            str(stage_note) if stage_note is not None else None,
            locale,
            title,
            False,
            engine,
            faster_whisper_python,
            audio_format,
            offline_dictionary,
            listening_mode,
            str(stage_manifest) if stage_manifest is not None else None,
            slice_profile,
            compare_engine,
            str(stage_reviewed) if stage_reviewed is not None else None,
            str(stage_merge_request) if stage_merge_request is not None else None,
            vault_root,
        )
        return _bundle_from_stage(
            vault_root=vault_root,
            stage_vault=stage_vault,
            initial=initial,
            summary=summary.replace(str(stage_vault), str(vault_root)),
        )
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise


def apply_prepared_bundle(
    bundle: PreparedListeningBundle,
    *,
    apply: bool,
    overwrite_confirmed: bool,
) -> tuple[dict, dict | None]:
    root = lingotrace_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from lingotrace.packs.japanese import workflows

    payload = bundle.workflow_payload(overwrite_confirmed=overwrite_confirmed)
    preview = workflows.listening_notes(vault_root=bundle.vault_root, input_artifact=payload, mode="preview").to_dict()
    applied: dict | None = None
    if apply:
        applied = workflows.listening_notes(vault_root=bundle.vault_root, input_artifact=payload, mode="apply").to_dict()
    return preview, applied


def scan_audio_files(directory: Path) -> list[Path]:
    files = []
    for path in directory.rglob("*"):
        if path.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac"}:
            files.append(path)
    return sorted(files)


def listening_status_and_notification(bundle: PreparedListeningBundle) -> tuple[str, str]:
    if bundle.review_required:
        return (
            "llm_merge_required",
            f"双 ASR 检出 {bundle.disagreement_count} 处差异。调用方大模型应读取合并请求、"
            "自动生成临时共识文件并以 --reviewed-transcript 和 --merge-request 重跑；最终笔记尚未写入。",
        )
    if bundle.merge_model:
        return (
            "complete",
            f"双 ASR 差异已由 {bundle.merge_model} 自动判断并合并，最终笔记使用已校验共识。",
        )
    if bundle.asr_validation_status == "agreed":
        return "complete", "双 ASR 转写一致，无需模型合并；听力笔记已通过写入校验。"
    if bundle.asr_validation_status == "secondary_unavailable":
        return "complete", "第二 ASR 不可用，本次已受控降级为单 ASR；限制已记录在比较工件中。"
    return "complete", "听力笔记已通过转写与写入校验。"


def main() -> int:
    args = parse_args()
    if args.apply and args.dry_run:
        print("Use either --apply or --dry-run, not both.", file=sys.stderr)
        return 1
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
    if args.merge_request and not args.reviewed_transcript:
        print("--merge-request requires --reviewed-transcript.", file=sys.stderr)
        return 1

    try:
        configure_project_roots(lingotrace=args.lingotrace_root, listenkit=args.listenkit_root)
        vault_root = resolve_vault_root(args.vault_root, args.audio_path, args.output_dir, args.note_path)
        offline_dictionary = load_offline_dictionary(required=True)
    except (OfflineDictionaryError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    bundle: PreparedListeningBundle | None = None
    try:
        note_path = resolve_vault_relative_path(vault_root, args.note_path) if args.note_path else None
        manifest_path = resolve_vault_relative_path(vault_root, args.slice_manifest) if args.slice_manifest else None
        reviewed_path = resolve_readonly_input_path(vault_root, args.reviewed_transcript) if args.reviewed_transcript else None
        merge_request_path = resolve_readonly_input_path(vault_root, args.merge_request) if args.merge_request else None
        if args.url:
            output_dir = resolve_vault_relative_path(vault_root, args.output_dir)
            url_compare = None if args.single_asr else args.compare_engine
            bundle = prepare_url_listening_bundle(
                vault_root=vault_root,
                url=args.url,
                output_dir=output_dir,
                note_override=note_path,
                locale=args.locale,
                title=args.title,
                engine=args.engine,
                compare_engine=url_compare,
                faster_whisper_python=args.faster_whisper_python,
                audio_format=args.format,
                offline_dictionary=offline_dictionary,
                listening_mode=args.listening_mode,
                slice_manifest_override=manifest_path,
                slice_profile=args.slice_profile,
                reviewed_transcript=reviewed_path,
                merge_request=merge_request_path,
            )
        else:
            audio_path = resolve_vault_relative_path(vault_root, args.audio_path)
            validate_listening_target(vault_root, audio_path)
            existing_note = note_path or resolve_note_path(audio_path, None)
            compare_engine = effective_compare_engine(
                args.compare_engine,
                single_asr=args.single_asr,
                listening_mode=args.listening_mode,
                audio_path=audio_path,
                existing_note=existing_note,
            )
            bundle = prepare_local_listening_bundle(
                vault_root=vault_root,
                audio_path=audio_path,
                note_override=note_path,
                locale=args.locale,
                title=args.title,
                engine=args.engine,
                compare_engine=compare_engine,
                faster_whisper_python=args.faster_whisper_python,
                faster_whisper_model=args.faster_whisper_model,
                faster_whisper_compute_type=args.faster_whisper_compute_type,
                offline_dictionary=offline_dictionary,
                listening_mode=args.listening_mode,
                slice_manifest_override=manifest_path,
                slice_profile=args.slice_profile,
                reviewed_transcript=reviewed_path,
                merge_request=merge_request_path,
            )
        materialize_llm_merge_request_handoff(bundle)
        preview, applied = apply_prepared_bundle(
            bundle,
            apply=args.apply,
            overwrite_confirmed=args.confirm_overwrite,
        )
        status, notification = listening_status_and_notification(bundle)
        output = {
            "status": status,
            "summary": bundle.summary,
            "note_path": bundle.note_path,
            "review_required": bundle.review_required,
            "llm_merge_request_path": bundle.llm_merge_request_path,
            "disagreement_count": bundle.disagreement_count,
            "merge_model": bundle.merge_model,
            "asr_validation_status": bundle.asr_validation_status,
            "notification": notification,
            "preview": preview,
            "apply": applied,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if not preview.get("accepted", False):
            return 1
        if applied is not None and not applied.get("accepted", False):
            return 1
        if bundle.review_required:
            return 2
        return 0
    except (OfflineDictionaryError, RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if bundle is not None:
            bundle.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
