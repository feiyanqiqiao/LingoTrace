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
