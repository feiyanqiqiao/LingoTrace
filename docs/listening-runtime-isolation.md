# Listening Runtime Isolation

> This document records the verified macOS and Windows Python/ASR isolation setup. Vault-to-LingoTrace runtime discovery itself is cross-platform and is documented in [Vault initialization and runtime connections](vault-initialization-and-runtime-connections.md); registering a runtime path does not by itself install or validate platform-specific listening dependencies.

The LingoTrace core runs on Python 3.11 or newer. Its Japanese listening extension and ListenKit use separate Python 3.14 virtual environments because their pinned native dependencies have been verified on that version. A system, framework, Homebrew, or other trusted Python 3.14 may bootstrap those environments; normal transcription never installs or upgrades packages.

On Windows, LingoTrace calls ListenKit through `cli/generate-markdown.ps1` with `pwsh` or Windows PowerShell. It never routes through `/bin/bash`, WSL, or Git Bash. Child Python processes have inherited `PYTHONHOME` and `PYTHONPATH` removed, but a host that corrupts those variables before Python starts must still select or repair its interpreter before LingoTrace code can run.

## Ownership

| Project | Default runtime | Direct dependencies | Responsibility |
| --- | --- | --- | --- |
| LingoTrace | macOS `~/Library/Caches/LingoTrace/venvs/cpython-314`; Windows `%LOCALAPPDATA%\LingoTrace\venvs\cpython-314`; Linux `${XDG_CACHE_HOME:-~/.cache}/lingotrace/venvs/cpython-314` | `fugashi==1.5.2`, `unidic-lite==1.0.8` | Japanese tokenization and accent candidates |
| ListenKit | Defined and initialized by the current ListenKit release | `faster-whisper==1.2.1` and platform ASR dependencies | Audio transcription and timestamped transcript artifacts |

The environments must not import each other's packages. LingoTrace must not import `faster_whisper`; ListenKit must not import `fugashi`.

## Boundary

The projects communicate only through:

- ListenKit CLI commands.
- Transcript JSON and Markdown artifacts.
- Slice manifests and export reports.

LingoTrace accepts transcript JSON with `schema_version: 1`. A payload without `schema_version` is treated as legacy v1. Explicit unknown versions are rejected before note generation.

## Initialization

Initialize each project explicitly from its own repository. Initialization is never triggered by a transcription command and requires user consent because it creates a venv and may download packages.

```bash
# LingoTrace repository
<python3.14> tools/listening-transcribe-official/init_listening_runtime.py \
  --bootstrap-python <python3.14> \
  --install

# ListenKit repository
# Follow the current platform-specific initializer documented by ListenKit.
```

`<python3.14>` must be an actually runnable Python 3.14 interpreter confirmed through `sys.executable` and `sys.version`; its command name alone is not evidence. The initializer refuses iCloud/OneDrive paths and unknown non-empty targets, creates the current platform's Cache venv, removes inherited `PYTHONHOME` and `PYTHONPATH` from child Python processes, installs the pinned requirements, and runs the dictionary health check. If a platform has no compatible wheel and pip needs to compile a native package, install that platform's supported build tools (for example Xcode Command Line Tools on macOS) only after the build error establishes the need and the user agrees.

On macOS, the LingoTrace Japanese listening execution layer normally uses `~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python`. Loading the `fugashi` native extension from an iCloud-resident project environment was previously observed to hang for more than 100 seconds, and iCloud renamed a project-root symlink to `.venv 2`; therefore no runtime or runtime symlink belongs inside the repository or Vault. `LINGOTRACE_LISTENING_PYTHON` is the preferred intentional override; `JP_LISTENING_PYTHON` remains a compatibility override. A missing or unhealthy runtime stops before transcription and prints the public initialization command.

ListenKit follows the same storage rule for its larger native ASR stack. Neither project keeps a virtual environment or runtime symlink inside iCloud/OneDrive. The projects remain independent and communicate only through ListenKit CLI and artifact contracts.

The external dictionary-data cache contains only static cross-version data such as `~/Library/Caches/jp-listening-dicts/accent_map.json`. Python packages belong in the dedicated LingoTrace runtime, not under the dictionary-data cache.

The Windows dictionary-data cache defaults to `%LOCALAPPDATA%\LingoTrace\Caches\jp-listening-dicts`; Linux follows `XDG_CACHE_HOME`. `JP_LISTENING_DICT_DIR` remains the explicit override on every platform.

## Health Check

Run the read-only dictionary check from the LingoTrace repository. The same command works on every platform and discovers the platform-native default runtime:

```bash
<python3.14> tools/listening-transcribe-official/init_listening_runtime.py \
  --bootstrap-python <python3.14> \
  --check
```

It verifies:

- The LingoTrace runtime uses Python 3.14.
- LingoTrace loads the pinned dictionary packages and returns `公園⓪`, `散歩⓪`, and `し⓪` for the sample sentence.

The lower-level `setup_offline_dictionary.py` remains available for diagnosis inside an already-created runtime. It is not the new-machine bootstrap entry.

ListenKit runtime checks remain owned by the ListenKit repository. Listening-note tasks triggered through the Japanese Agent Skill still perform source-audio, transcript, and slice-tool preflight before changing files.

## Upgrades And Diagnosis

Change only direct dependency pins in each project's requirements file. Re-run that project's initializer, tests, and health checks before changing the other project. Do not copy `site-packages`, set cross-project `PYTHONPATH`, or install packages into the shared dictionary cache.

Package snapshots under `docs/` are diagnostic records of a verified environment. They are not installation inputs; requirements files remain the installation source of truth.

## Verification Record

On June 12, 2026:

- ListenKit's Python 3.14 runtime, `faster-whisper==1.2.1`, bounded import check, schema v1 producer/consumer behavior, and 71-test suite passed in PR #3.
- LingoTrace's 74-test suite passed after introducing the isolated-runtime contract.
- LingoTrace's local Cache runtime loaded the pinned dictionary packages and returned the required sample accents.
- ListenKit transcribed `Unit3/attach/23.mp3` to schema v1 with 28 non-empty, fully timestamped segments.
- LingoTrace completed an intensive dry-run for `Unit3/attach/23.mp3`, generated 19 learning blocks, and produced non-empty local accent candidates without modifying the material directory.

On June 13, 2026:

- ListenKit moved its Python 3.14 runtime out of iCloud to `~/Library/Caches/ListenKit/venvs/cpython-314` in PR #4.
- The new runtime passed the bounded import check and remained isolated from LingoTrace's `fugashi` dependency.
- `Unit3/attach/23.mp3` again produced schema v1 with 28 non-empty, fully timestamped segments.

On August 10, 2026, on Windows 11:

- LingoTrace ran under CPython 3.14.4 with GBK/CP936 as the inherited console encoding and emitted valid UTF-8 JSON through both stdout and `--report-json`.
- ListenKit's native PowerShell doctor found `faster-whisper==1.2.1`, ffmpeg/ffprobe, an NVIDIA GTX 1660 SUPER CUDA route, and a ready `small` model.
- A synthesized English WAV in a temporary initialized Vault whose path contained spaces completed a native `generate-markdown.ps1` transcription and LingoTrace guarded dry-run.
- Inputs outside the Vault and outside configured `listening_root` were independently rejected before transcription.

On August 10, 2026, on macOS arm64:

- The core, listening, Vault-structure, and architecture unittest groups passed 426 tests; pytest passed 425 tests with one expected skip and 25 subtests.
- Real `resolve-runtime`, `resolve-listenkit`, and `doctor` calls accepted an initialized Vault and returned the macOS `.sh` ListenKit entry; UTF-8 JSON reports remained valid under paths containing spaces and CJK characters.
- A sandbox-external ListenKit doctor reported MLX and Metal ready. A synthesized WAV completed guarded dry-runs in both MLX-primary/Apple-secondary and Apple-primary/MLX-secondary directions with independent ASR agreement and no Vault writes.
- A Vault-external audio input was rejected before transcription and produced a structured UTF-8 error report.
