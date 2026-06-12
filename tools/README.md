# Tools

此目錄只放可重複使用、適合納入版本控制的工具。一次性資料修復腳本、臨時轉寫產物與歷史腳本應放入 `tmp/legacy/`，不要留在 `tools/`。

## Listening Transcribe

目錄：`tools/listening-transcribe-official/`

這組工具用於將本地音訊或媒體 URL 轉為聽力筆記，並依需要生成逐句切片、泛聽或精聽內容。

### `transcribe_listening.py`

用途：

- 調用 ListenKit 取得轉寫結果。
- 生成或更新 Obsidian 聽力筆記。
- 管理素材目錄下的 `attach/` 與 `artifacts/`。
- 區分泛聽與精聽模式。
- 在精聽模式下生成學習語塊 manifest，並調用 ListenKit 導出真實切片。
- 加入可確認的重音資訊，並保留既有人工修訂內容。

何時使用：

- 需要把一個本地音訊或媒體 URL 轉為 Vault 內的固定聽力筆記格式時。
- 需要更新既有聽力筆記的腳本、音訊引用或精聽切片時。

何時不要使用：

- 不要直接把它當作日常入口。請優先透過 Skill wrapper 執行。
- 不要用它生成一般來源筆記、詞彙卡或生活口語卡。
- 不要讓它自動決選最終常用句。

常用命令：

```bash
zsh codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh --help
```

實際調用鏈路：

```text
jp-listening-script-generator
  -> run-listening-transcribe.sh
  -> tools/listening-transcribe-official/transcribe_listening.py
  -> ../ListenKit/cli/generate-markdown.sh
  -> ../ListenKit/cli/export-audio-slices.py
```

依賴：

- Skill wrapper：`codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh`
- 通用轉寫能力：`../ListenKit/cli/generate-markdown.sh`
- 通用時間範圍切片能力：`../ListenKit/cli/export-audio-slices.py`
- 離線詞典套件：由 `setup_offline_dictionary.py` 安裝及檢查於 LingoTrace 自己的本機 Cache runtime。
- Python runtime：LingoTrace 固定使用 `~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python`，ListenKit 固定使用 `~/Library/Caches/ListenKit/venvs/cpython-314/bin/python`。兩套環境都放在本機 Cache，避免從 iCloud 路徑載入原生擴展時卡住或讓 symlink 被改名；Homebrew `/opt/homebrew/bin/python3.14` 只負責初始化，兩者不得跨環境 import 套件。

#### 精聽學習語塊

精聽稿統一使用學習語塊，不直接把 ASR chunks 當作切片單位：

- 路由依據是腳本內容，不是資料夾或檔名；`Shadowing` 路徑不會強制套用對話規則。
- `dialogue/numbered` 按完整報號對話組切片，報號屬於該組，作為該 `SNN` 的第一段音頻與文本。
- `dialogue/exchange` 按完整問答交換切片；可靠且中間停頓不超過 `1.0` 秒的四輪問答保留為一組，否則使用兩輪 A/B。
- `sentence/sentence` 按自然句切片。
- 自動切分不可靠時，使用 `--slice-manifest PATH` 提供人工校正後的時間範圍。
- 使用 `--slice-profile auto|dialogue|sentence` 覆蓋自動分類；優先級為 CLI 覆蓋、reviewed manifest metadata、自動內容判斷。

生成器會先做錄音鏈前置檢查：來源音頻必須存在且非空，ListenKit 的轉寫與切片 CLI 必須可用，精聽切片還需要 `ffmpeg`/`ffprobe`。本地音頻與 URL 輸入都會把 ListenKit 原始 `.listenkit.md/.json` 保存到素材目錄的 `artifacts/`，避免只留下最終稿而無法回查。

生成器將 manifest 寫入素材目錄下的 `artifacts/<audio_stem>.slices.json`，並保存 `slice_profile` 的類型、分組、來源、編號策略和 padding。預設路徑中標記為 `source: manifest` 的檔案視為已人工 review，重跑時沿用其 profile 和時間範圍；`source: auto|cli` 則可重新分類。之後交給 ListenKit 導出 `attach/<audio_stem>_SNN.m4a`。精聽切片一律不得互相重疊；`dialogue/numbered` 使用 `0.0` 秒 padding，其他 profile 使用前後各 `0.5` 秒安全 padding，但不能跨入相鄰片段。導出報告與製作記錄也保存最終 profile。`segment_count`、學習包區塊、embed 和實際非空文件數量必須一致。

通用文本清洗只處理標點、空白與全半角數字，不按路徑套用教材專用詞語修正。`何回→何階`、`奥には→お国は` 等內容校正必須進入 reviewed transcript 或 manifest。

#### 常用句邊界

`transcribe_listening.py` 只建立 `## 可直接背的常用句` 區塊骨架，不自動決定最終常用句。

新筆記生成後，仍需由人工或模型閱讀完整腳本，保守挑選 `0-5` 句真正值得背、可以遷移到其他生活場景的表達，再同步更新 frontmatter 的 `daily_use_sentences`。重跑既有筆記時，工具會保留已手工修訂的常用句，除非明確要求重置。

這個邊界用於避免把 ASR 不穩定句、教材操練句、不自然表達或過度泛用骨架直接收入常用句池。

### `setup_offline_dictionary.py`

用途：

- 檢查 LingoTrace Python 3.14 環境與離線日語詞典是否可用。
- 安裝固定版本的 `fugashi` 與 `unidic-lite` 到 LingoTrace 本機 Cache runtime。
- 為聽力筆記與詞彙維護提供重音候選。

何時使用：

- 首次使用聽力轉寫工具前。
- 聽力工具提示 LingoTrace runtime 缺失或損壞時。
- 需要確認分詞與重音候選是否正常時。

何時不要使用：

- 不要用它生成聽力筆記。
- 不要把 runtime 或外部靜態詞典快取提交到 Git。
- 不要把本地候選直接當作人工確認結果。

常用命令：

```bash
codex-skills/jp-listening-script-generator/scripts/init-listening-runtime.sh
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python tools/listening-transcribe-official/setup_offline_dictionary.py --python ~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python --check
codex-skills/jp-listening-script-generator/scripts/check-listening-chain.sh
```

依賴：

- Homebrew Python 3.14 作為初始化器。
- LingoTrace 直接使用本機 Cache 中的 Python 套件；直接依賴只由 `requirements-listening.txt` 固定。
- Vault 外部快取目錄：預設為 `~/Library/Caches/jp-listening-dicts`，只保留跨版本靜態資料，例如根目錄 `accent_map.json`。
- 可用 `JP_LISTENING_DICT_DIR` 覆蓋預設位置。

完整環境邊界與升級規則見 `docs/listening-runtime-isolation.md`。

### 測試

執行測試：

```bash
~/Library/Caches/LingoTrace/venvs/cpython-314/bin/python -m unittest discover -s tools/listening-transcribe-official/tests -p 'test_*.py'
```

## Git Workflow Checks

目錄：`tools/git/`

這組工具用於降低公開倉庫提交時混入私有 Vault 內容的風險。

### `check-public-staged-files.sh`

用途：

- 檢查 staged 文件是否只包含公開 allowlist 路徑。
- 阻止筆記、Obsidian 狀態、音訊、圖片、PDF、暫存轉寫產物等私有內容進入提交。
- 可在 GitHub Actions 中檢查 PR diff 或 `main` push diff。

本地提交前執行：

```bash
bash tools/git/check-public-staged-files.sh
```

檢查某個 Git diff 範圍：

```bash
bash tools/git/check-public-staged-files.sh --range origin/main...HEAD
```

## Vault Structure

目錄：`tools/vault-structure/`

這組工具用於預覽或執行 Vault 目錄遷移，以及驗證角色路徑、顯式 wikilink、聽力附件、生活口語卡與 rollover 是否正常。

### `migrate_vault_layout.py`

用途：

- 按階段預覽 Vault 目錄搬移、引用改寫、新建與刪除清單。
- 僅在明確加上 `--apply` 時寫入。
- 寫入前在 `tmp/directory-refactor-backup/` 建立備份與 manifest。

何時使用：

- Vault 目錄結構需要調整時。
- 需要確認既有遷移是否已完成且可重跑時。

何時不要使用：

- 不要用它處理日常建卡或複習。
- 不要跳過預覽直接執行 `--apply`。
- 不要用盲目全文替換代替可核對的階段映射。

常用命令：

遷移工具預設只預覽。確認清單後，才加上 `--apply`：

```bash
python3 tools/vault-structure/migrate_vault_layout.py --phase content
python3 tools/vault-structure/migrate_vault_layout.py --phase content --apply
```

可用階段：

- `pronunciation`
- `system`
- `listening`
- `content`

依賴：

- Python
- Vault 根目錄內的既有學習內容與角色配置。

### `validate_vault_structure.py`

用途：

- 驗證角色路徑與兼容鏡像。
- 掃描顯式 wikilink 與媒體引用。
- 檢查聽力附件目錄結構。
- 串聯生活口語卡驗證器與 rollover 預覽。
- 產生或比較壞鏈基線。

何時使用：

- 目錄遷移前後。
- 修改路徑角色、聽力附件或生活口語卡結構後。
- 需要確認是否出現新增壞鏈時。

何時不要使用：

- 不要把新出現的壞鏈直接加入基線來略過問題。
- 不要用它改寫筆記；這是只讀驗證工具，只有 `--write-baseline` 會更新基線檔。

常用命令：

完整結構驗證：

```bash
python3 tools/vault-structure/validate_vault_structure.py \
  --baseline tmp/directory-refactor-baseline.json \
  --enforce-listening-layout \
  --run-integrations
```

更新壞鏈基線：

```bash
python3 tools/vault-structure/validate_vault_structure.py \
  --write-baseline tmp/directory-refactor-baseline.json
```

依賴：

- Python
- `系统配置/paths.json`
- 生活口語卡驗證器
- 次日 rollover wrapper

### 測試

執行測試：

```bash
python3 -m unittest discover -s tools/vault-structure/tests -p 'test_*.py'
```

## Maintenance Rules

- 新工具應有明確且可重複的用途。
- 支援預覽模式的工具，先執行預覽再寫入。
- 大量搬移或改鏈前，保留備份與可核對的清單。
- 不提交音訊、媒體、轉寫產物、快取、`.DS_Store` 或 `__pycache__/`。
- 一次性修復腳本完成任務後移到 `tmp/legacy/`。
