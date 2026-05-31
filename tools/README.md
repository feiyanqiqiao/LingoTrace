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
- 在精聽模式下生成逐句切片引用。
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
```

依賴：

- Skill wrapper：`codex-skills/jp-listening-script-generator/scripts/run-listening-transcribe.sh`
- 通用轉寫能力：`../ListenKit/cli/generate-markdown.sh`
- 離線詞典快取：由 `setup_offline_dictionary.py` 維護。

#### 常用句邊界

`transcribe_listening.py` 只建立 `## 可直接背的常用句` 區塊骨架，不自動決定最終常用句。

新筆記生成後，仍需由人工或模型閱讀完整腳本，保守挑選 `0-5` 句真正值得背、可以遷移到其他生活場景的表達，再同步更新 frontmatter 的 `daily_use_sentences`。重跑既有筆記時，工具會保留已手工修訂的常用句，除非明確要求重置。

這個邊界用於避免把 ASR 不穩定句、教材操練句、不自然表達或過度泛用骨架直接收入常用句池。

### `setup_offline_dictionary.py`

用途：

- 檢查離線日語詞典快取是否可用。
- 安裝 `fugashi` 與 `unidic-lite` 到 Vault 外部快取目錄。
- 為聽力筆記與詞彙維護提供重音候選。

何時使用：

- 首次使用聽力轉寫工具前。
- 聽力工具提示離線詞典缺失時。
- 需要確認分詞與重音候選是否正常時。

何時不要使用：

- 不要用它生成聽力筆記。
- 不要把詞典快取寫入 Vault 或提交到 Git。
- 不要把本地候選直接當作人工確認結果。

常用命令：

```bash
python3 tools/listening-transcribe-official/setup_offline_dictionary.py --check
python3 tools/listening-transcribe-official/setup_offline_dictionary.py --install
```

依賴：

- Python
- Vault 外部快取目錄：預設為 `~/Library/Caches/jp-listening-dicts`
- 可用 `JP_LISTENING_DICT_DIR` 覆蓋預設位置。

### 測試

執行測試：

```bash
python3 -m unittest tools/listening-transcribe-official/tests/test_transcribe_listening.py
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
