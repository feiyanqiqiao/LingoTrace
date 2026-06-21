# Listening Runtime Isolation

LingoTrace and ListenKit use separate Python 3.14 virtual environments. Homebrew Python 3.14 is only the bootstrap interpreter; normal transcription runs never install or upgrade packages.

## Ownership

| Project | Runtime | Direct dependencies | Responsibility |
| --- | --- | --- | --- |
| LingoTrace | `~/Library/Caches/LingoTrace/venvs/cpython-314` | `fugashi==1.5.2`, `unidic-lite==1.0.8` | Note rendering, tokenization, accent candidates |
| ListenKit | `~/Library/Caches/ListenKit/venvs/cpython-314` | `faster-whisper==1.2.1` | Audio transcription and timestamped transcript artifacts |

The environments must not import each other's packages. LingoTrace must not import `faster_whisper`; ListenKit must not import `fugashi`.

## Boundary

The projects communicate only through:

- ListenKit CLI commands.
- Transcript JSON and Markdown artifacts.
- Slice manifests and export reports.

LingoTrace accepts transcript JSON with `schema_version: 1`. A payload without `schema_version` is treated as legacy v1. Explicit unknown versions are rejected before note generation.

## Initialization

Initialize each project explicitly from its own repository. Initialization is never triggered by a transcription command.

```bash
# LingoTrace repository
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python tools/listening-transcribe-official/setup_offline_dictionary.py --python ~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python --install

# ListenKit repository
cli/init-faster-whisper.sh
```

The LingoTrace listening execution layer uses `~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python`. The repository is stored under iCloud, where loading the `fugashi` native extension directly was observed to hang for more than 100 seconds. A project-root symlink was also renamed to `.venv 2` by iCloud, so the runtime has no entry inside the Vault. The same extension loaded from the local Cache path in about 0.4 seconds. `LINGOTRACE_LISTENING_PYTHON` is the preferred intentional override; `JP_LISTENING_PYTHON` remains a compatibility override. A missing or unhealthy runtime stops before transcription and prints the initialization command.

ListenKit follows the same storage rule for its larger native ASR stack. Its runtime lives at `~/Library/Caches/ListenKit/venvs/cpython-314`; neither project keeps a virtual environment or runtime symlink inside iCloud. The projects remain independent and communicate only through ListenKit CLI and artifact contracts.

The external dictionary-data cache contains only static cross-version data such as `~/Library/Caches/jp-listening-dicts/accent_map.json`. Python packages belong in the dedicated LingoTrace runtime, not under the dictionary-data cache.

## Health Check

Run the read-only dictionary check from the LingoTrace repository:

```bash
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python tools/listening-transcribe-official/setup_offline_dictionary.py --python ~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python --check
```

It verifies:

- The LingoTrace runtime uses Python 3.14.
- LingoTrace loads the pinned dictionary packages and returns `公園⓪`, `散歩⓪`, and `し⓪` for the sample sentence.

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
