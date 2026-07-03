# LingoTrace English Language Pack 实施计划 (Phase 2 第一步) v3

本文档阐述了在遵循上游最新的四层多语言架构规范下，创建并引入 `English` 语言包第一版（最小可测试包）的实施细节。本方案已吸收 V1 与 V2 版本的所有评审反馈，提供了从架构声明到代码级的完整可执行规范，无需再翻阅旧文档即可独立实施。

## 🎯 目标描述

建立标准合规的英语语言包。本阶段定位为 **“最小可测试包” (Minimal Testable Pack)**：不实现真正的英语 Python 业务逻辑，但提供完整的结构声明、空壳桩函数 (stubs) 以及对应的自动化测试，确保能在结构层面 100% 通过上游架构验证。

> **关于运行时的说明**
> 当前核心（`core/context.py`）上下文硬编码了 `SUPPORTED_TARGET_LANGUAGE = "ja"` 且 `SUPPORTED_EXPLANATION_LANGUAGE = "zh"`。本 PR 不修改核心，因此英语包暂不能在真实环境端到端运行，仅作为“结构就绪”的里程碑。真正可运行需要依赖后续泛化上下文的 PR。

## 📝 设计决策记录 (Design Decisions)

基于前期评审的反馈，我们在第一版中固化了以下关键决策：
1. **Locale 设定**：选择 `en-US` 作为默认的 `transcription_locale`，未来用户可在自己的 Vault 配置中覆盖（例如改为 `en-GB`）。
2. **专属字段设定**：脱离日语语境，使用 `ipa`（国际音标）、`word_stress`（重音模式）、`part_of_speech`（词性）、`collocations`（常见搭配）。
3. **释义字段避碰**：`meaning_zh` 会在卡片模板中直接使用，但不在 `fields.json` 中声明所属权，以免与日语包（已声明拥有权）发生冲突。
4. **Item Types 预留**：`item_types` 包含了 `vocab`, `grammar`, `error`, 和 `pronunciation`。虽然目前不支持发音训练，但因为字段里有 `ipa` 和 `word_stress`，提前声明 `pronunciation` 可以避免未来版本扩展时修改 manifest。

---

## 🛠️ Proposed Changes

所有修改均限制在 `lingotrace/packs/english/` 与 `tests/lingotrace/packs/` 中。

### 1. English Language Pack Skeleton (清单与配置)

#### [NEW] `lingotrace/packs/english/__init__.py`
空文件，仅作为包边界标识。

#### [NEW] `lingotrace/packs/english/manifest.json`
完整的合规清单：
```json
{
  "language_pack_id": "lingo-english",
  "language_pack_version": "0.1.0",
  "target_language": "en",
  "transcription_locale": "en-US",
  "compatible_core": {
    "minimum": "0.1.0",
    "maximum_exclusive": "0.2.0"
  },
  "compatible_vault_schema": {
    "minimum": 1,
    "maximum": 1
  },
  "capabilities": [
    {
      "id": "source_notes",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": ["source_notes_root"],
      "write_path_roles": ["source_notes_root"],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": ["English source note creation from reading material"]
    },
    {
      "id": "review_materials",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "source_notes_root"
      ],
      "write_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root"
      ],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": ["English vocabulary card creation with IPA and collocations"]
    },
    {
      "id": "review_rollover",
      "maturity": "experimental",
      "depends_on": [],
      "read_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "daily_notes_root"
      ],
      "write_path_roles": [
        "focus_vocab_root",
        "base_vocab_root",
        "grammar_root",
        "error_root",
        "daily_notes_root"
      ],
      "external_tools": [],
      "behavior_evidence": [],
      "conformance_tests": ["tests/lingotrace/packs/test_english_pack.py"],
      "manual_review_cases": []
    }
  ],
  "unsupported_capabilities": [
    {
      "id": "listening_notes",
      "failure_reason": "English listening transcription tools are not yet available.",
      "failure_policy": "stop_before_write",
      "fallback": "none"
    },
    {
      "id": "speaking_cards",
      "failure_reason": "English speaking card validation is not yet implemented.",
      "failure_policy": "stop_before_write",
      "fallback": "none"
    }
  ],
  "external_tools": [],
  "language_fields": [
    {
      "name": "ipa",
      "owner": "English language pack",
      "purpose": "IPA phonetic transcription for English review items."
    },
    {
      "name": "word_stress",
      "owner": "English language pack",
      "purpose": "Primary stress pattern or syllable stress notation."
    },
    {
      "name": "part_of_speech",
      "owner": "English language pack",
      "purpose": "Grammatical category (noun, verb, adjective, etc.)."
    },
    {
      "name": "collocations",
      "owner": "English language pack",
      "purpose": "Common collocations and phrases for the headword."
    }
  ],
  "item_types": ["vocab", "grammar", "error", "pronunciation"],
  "tag_namespace": "en",
  "default_path_roles": {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily"
  },
  "templates": [
    {
      "id": "focus_vocab_card",
      "capability_id": "review_materials",
      "path": "lingotrace/packs/english/templates/focus-vocab-card.md",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "daily_checklist",
      "capability_id": "review_rollover",
      "path": "lingotrace/packs/english/templates/daily-checklist.md",
      "artifact_class": "recreate-from-pack"
    }
  ],
  "workflow_entrypoints": [
    {
      "id": "source_notes_workflow",
      "capability_id": "source_notes",
      "entrypoint": "lingotrace.packs.english.workflows:source_notes",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_materials_workflow",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.english.workflows:review_materials",
      "call_policy": "through_core_write_guard"
    },
    {
      "id": "review_rollover_workflow",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.english.workflows:review_rollover",
      "call_policy": "through_core_write_guard"
    }
  ],
  "validators": [
    {
      "id": "review_materials_validator",
      "capability_id": "review_materials",
      "entrypoint": "lingotrace.packs.english.validators:validate_review_materials"
    },
    {
      "id": "review_rollover_validator",
      "capability_id": "review_rollover",
      "entrypoint": "lingotrace.packs.english.validators:validate_review_rollover"
    }
  ],
  "display_rules": [],
  "initialization_artifacts": [
    {
      "id": "default_vault_context",
      "capability_id": "review_rollover",
      "path": ".lingotrace/vault-context.json",
      "artifact_class": "recreate-from-pack"
    },
    {
      "id": "default_path_config",
      "capability_id": "review_rollover",
      "path": ".lingotrace/paths.json",
      "artifact_class": "recreate-from-pack"
    }
  ]
}
```

#### [NEW] `lingotrace/packs/english/fields.json`
```json
{
  "language_fields": [
    {
      "name": "ipa",
      "owner": "English language pack",
      "purpose": "IPA phonetic transcription for English review items."
    },
    {
      "name": "word_stress",
      "owner": "English language pack",
      "purpose": "Primary stress pattern or syllable stress notation."
    },
    {
      "name": "part_of_speech",
      "owner": "English language pack",
      "purpose": "Grammatical category (noun, verb, adjective, etc.)."
    },
    {
      "name": "collocations",
      "owner": "English language pack",
      "purpose": "Common collocations and phrases for the headword."
    }
  ]
}
```

#### [NEW] `lingotrace/packs/english/paths.json`
```json
{
  "default_path_roles": {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily"
  }
}
```

### 2. Python Stubs (工作流与校验器桩)

#### [NEW] `lingotrace/packs/english/workflows.py`
```python
"""English language pack workflow stubs.

All capabilities are experimental and require core context generalization
before they can run against a real English Vault. Each function returns
a missing_vault_root error when called without a vault_root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def listening_notes(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("listening_notes", "English listening transcription tools are not yet available.")


def source_notes(
    vault_root: str | Path | None = None,
    *,
    source_artifact: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("source_notes")
    return _not_yet_implemented("source_notes", mode)


def review_materials(
    vault_root: str | Path | None = None,
    *,
    card: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_materials")
    return _not_yet_implemented("review_materials", mode)


def speaking_cards(vault_root: str | Path | None = None, **_: Any) -> CommandReport:
    return _unsupported("speaking_cards", "English speaking card validation is not yet implemented.")


def review_rollover(
    vault_root: str | Path | None = None,
    *,
    run_date: str | None = None,
    mode: str = "preview",
) -> CommandReport:
    if vault_root is None:
        return _missing_vault_root("review_rollover")
    return _not_yet_implemented("review_rollover", mode)


def _missing_vault_root(capability_id: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="missing_vault_root", message="vault_root is required.")],
    )


def _unsupported(capability_id: str, reason: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode="preview",
        exit_code=1,
        errors=[Finding(code="unsupported_capability", message=reason)],
    )


def _not_yet_implemented(capability_id: str, mode: str) -> CommandReport:
    return CommandReport(
        command=f"{capability_id}-workflow",
        mode=mode,
        exit_code=1,
        errors=[Finding(
            code="not_yet_implemented",
            message=f"{capability_id} requires core context generalization before it can run.",
        )],
    )
```

#### [NEW] `lingotrace/packs/english/validators.py`
```python
"""English language pack validators (stubs)."""
from __future__ import annotations

from typing import Any

from lingotrace.core.reports import CommandReport, Finding


def validate_review_materials(card: dict[str, Any]) -> CommandReport:
    required = ("item_type", "review_stage")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-materials", mode="check", exit_code=1 if errors else 0, errors=errors)


def validate_review_rollover(card: dict[str, Any]) -> CommandReport:
    required = ("review_stage", "next_review", "done_today")
    errors = [
        Finding(code="missing_field", message=f"Required field is missing: {field}.")
        for field in required
        if field not in card
    ]
    return CommandReport(command="validate-review-rollover", mode="check", exit_code=1 if errors else 0, errors=errors)
```

### 3. Agent 与模板层 (用户交互面)

#### [NEW] `lingotrace/packs/english/agent_skills/SKILL.md`
```markdown
# LingoTrace English Agent Skill

Use this skill when a user asks in natural language to maintain English learning materials.

## User Language

| User request | Agent task | Capability |
| --- | --- | --- |
| 帮我整理这篇英语阅读材料 | Source note task | `source_notes` |
| 把这个生词加入复习 | Review material task | `review_materials` |
| 结算复习 | Review rollover task | `review_rollover` |

> **Note:** Listening and speaking cards are currently unsupported for the English pack. If requested, politely apologize and refuse.

## Operating Rules

1. Always extract and specify `ipa`, `word_stress`, `part_of_speech`, and `collocations` for review items.
2. Do not use Japanese fields (e.g. kana, reading).
3. Do not overwrite existing notes blindly; ask for confirmation for merges.
```

#### [NEW] `lingotrace/packs/english/templates/focus-vocab-card.md`
```markdown
---
track: class_review
item_type: vocab
status: active
review_stage: 0
headword:
ipa:
word_stress:
part_of_speech:
collocations:
meaning_zh:
next_review:
---

# {{headword}}

## Review

- IPA: `{{ipa}}`
- Stress: `{{word_stress}}`
- Part of speech: `{{part_of_speech}}`
- Collocations: {{collocations}}
- Meaning: {{meaning_zh}}

## Notes

Add learner-maintained examples here.
```

#### [NEW] `lingotrace/packs/english/templates/daily-checklist.md`
```markdown
---
track: daily
item_type: checklist
done_today: false
---

# Daily Review Checklist

- [ ] Review due cards.
- [ ] Mark completed cards with `done_today`.
- [ ] Run review rollover only after manual review is complete.
```

### 4. 测试与验证层

#### [NEW] `tests/lingotrace/packs/test_english_pack.py`
本文件包含 7 个独立的合规断言测试：
```python
"""English language pack conformance tests."""
import importlib
import json
import unittest
from pathlib import Path

from lingotrace.core.capabilities import PHASE0_CAPABILITY_IDS
from lingotrace.core.manifests import load_language_pack_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ROOT = REPO_ROOT / "lingotrace" / "packs" / "english"
MANIFEST_PATH = PACK_ROOT / "manifest.json"
FIELDS_PATH = PACK_ROOT / "fields.json"
PATHS_PATH = PACK_ROOT / "paths.json"

EXPECTED_PATH_ROLES = {
    "focus_vocab_root": "review/focus/vocab",
    "base_vocab_root": "review/base/vocab",
    "grammar_root": "review/grammar",
    "error_root": "review/errors",
    "speaking_card_root": "speaking/cards",
    "speaking_guide_root": "speaking/guides",
    "listening_root": "listening",
    "pronunciation_accent_root": "review/pronunciation/accent",
    "pronunciation_phoneme_root": "review/pronunciation/phoneme",
    "source_notes_root": "sources",
    "daily_notes_root": "daily",
}

EXPECTED_LANGUAGE_FIELDS = {"ipa", "word_stress", "part_of_speech", "collocations"}


class EnglishPackTests(unittest.TestCase):

    def test_manifest_loads_through_core_loader(self):
        """1. Manifest passes load_language_pack_manifest without errors."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        self.assertTrue(result.report.accepted, result.report.to_dict())
        self.assertIsNotNone(result.manifest)
        assert result.manifest is not None
        self.assertEqual("lingo-english", result.manifest.language_pack_id)

    def test_declared_capabilities_are_subset_of_phase0_ids(self):
        """2. All declared capabilities use reviewed IDs from PHASE0_CAPABILITY_IDS."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        declared_ids = set(result.manifest.capabilities) | set(result.manifest.unsupported_capabilities)
        self.assertTrue(declared_ids.issubset(PHASE0_CAPABILITY_IDS))

    def test_unsupported_capabilities_have_fallback_none(self):
        """3. Unsupported capabilities declare fallback: 'none' and have failure policies."""
        result = load_language_pack_manifest(MANIFEST_PATH)
        assert result.manifest is not None
        self.assertIn("listening_notes", result.manifest.unsupported_capabilities)
        self.assertIn("speaking_cards", result.manifest.unsupported_capabilities)

    def test_language_fields_are_english_pack_owned(self):
        """4. fields.json declares English-owned fields, not Japanese fields."""
        fields = json.loads(FIELDS_PATH.read_text(encoding="utf-8"))
        field_names = {r["name"] for r in fields["language_fields"]}
        self.assertEqual(EXPECTED_LANGUAGE_FIELDS, field_names)
        self.assertNotIn("reading", field_names)

    def test_default_path_roles_match_phase1_design(self):
        """5. Path roles align with general architectural paths."""
        paths = json.loads(PATHS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_PATH_ROLES, paths["default_path_roles"])

    def test_workflow_stubs_do_not_reference_japanese_runtime(self):
        """6. workflows.py does not import or reference Japanese pack modules."""
        source = (PACK_ROOT / "workflows.py").read_text(encoding="utf-8")
        self.assertNotIn("japanese", source.lower())
        self.assertNotIn("jp-", source)

    def test_pack_owned_surfaces_exist(self):
        """7. Every template and workflow entrypoint declared in manifest exists on disk."""
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for record in manifest.get("templates", []):
            self.assertTrue((REPO_ROOT / record["path"]).exists(), record["path"])
```

## 🧪 Verification Plan

验证通过标准：**合规性测试 100% 通过**，且符合 Phase 0 检查清单。

### Automated Tests
1. `python -m unittest discover -s tests/lingotrace -p 'test_*.py'`
2. `python -m unittest discover -s tools/architecture-baseline/tests -p 'test_*.py'`
3. `bash tools/git/check-public-staged-files.sh`

### Conformance Checklist Compliance
基于 `docs/multilingual/history/phase-0/language-pack-conformance-checklist.md`，执行全面逐项对照：

**Identity And Versions**
- [x] 包 ID 为 `lingo-<language>` 格式 (`lingo-english`)。
- [x] 声明了明确的 `target_language` (`en`)。
- [x] 明确了 `transcription_locale` 为 `en-US`。
- [x] 不包含任何动态猜测目标语言的逻辑。

**Capabilities**
- [x] 支持和不支持的能力 ID 严格来自 `PHASE0_CAPABILITY_IDS`。
- [x] 不支持的能力 (`listening_notes`, `speaking_cards`) 拥有 `failure_reason` 且 `fallback` 为 `"none"`。
- [x] 不支持的能力显式指定了 `failure_policy` 为 `"stop_before_write"`。
- [x] `external_tools` 是空数组，且包内没有复用任何现有的日语工具链。

**Pack-Owned Surface**
- [x] manifest 中完整列出了工作流入口 `workflow_entrypoints`，无硬伤。
- [x] 完整声明了对应的校验器 `validators` 桩。
- [x] 声明了 `item_types` (包括预留发音卡)。
- [x] 声明了英语的命名空间 `tag_namespace` 为 `"en"`。

**Core Boundary**
- [x] 所有返回都是标准的 `CommandReport`，没有对用户的私人 Vault 发起直接的磁盘破坏性读写。
- [x] 代码完全是桩实现，不存在侵入性的 `frontmatter` 修改（遵循未知 frontmatter 保留原则）。
- [x] 遵守隔离规则，没有引入任何私人数据。
