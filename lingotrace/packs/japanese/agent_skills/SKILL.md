# LingoTrace Japanese Agent Skill

Use this skill when a user asks in natural language to maintain Japanese learning materials in a LingoTrace-backed Obsidian learning library.

This skill is the daily operating entry for agents. Users should not need to mention internal workflow names, Python functions, CLI flags, Vault schema, or write modes.

## User Language

Map intuitive study requests to the Japanese pack capabilities:

| User request | Agent task | Capability |
| --- | --- | --- |
| 请把这段音频做成精听稿 / 听力笔记 / 泛听笔记 | Listening note task | `listening_notes` |
| 帮我把这篇材料整理成日语学习笔记 / 生成学习笔记 | Source note task | `source_notes` |
| 把这个词加入复习 / 建词卡 / 建语法卡 | Review material task | `review_materials` |
| 这句话很实用，帮我做成口语卡 / 这句以后要会说 | Speaking card task | `speaking_cards` |
| 今天复习结束了，帮我结算 / 结算复习 | Review rollover task | `review_rollover` |

Prefer user-facing language such as:

- 保存到你的日语学习库
- 先让我确认将要新增或修改的内容
- 不会覆盖你已经手工整理过的笔记
- 复习结算前会先列出将被更新的卡片
- 缺少音频、来源或日期时，先向用户确认

Avoid asking users to say implementation phrases such as internal workflow names, data envelopes, or write-mode terms.

## Operating Rules

Agent Skill must not write files directly. It must route actual changes through the LingoTrace core write guard and the Japanese pack capability that matches the task.

Before a write-capable task, the agent must confirm the learning library context exists and that the matching capability is enabled. If context or capability checks fail, stop before writing and explain the missing setup in user-facing language.

Default behavior is risk-based:

- Listening notes, source notes, and speaking cards usually create new files. When the user clearly asks to create them, the agent may save the result after checking that the destination does not already exist.
- If a target note already exists, stop and ask before overwriting or merging. Preserve manually curated listening selections, review notes, and daily summaries.
- Review material maintenance starts with search and duplicate checks. New low-risk cards may be saved; merges, moves, overwrites, or review-state changes need confirmation.
- Review rollover first summarizes the cards that would change. Only update review state after the user confirms the settlement.

## Listening Notes

For requests such as "请把 23.mp3 做成精听稿", the agent should provide the full daily experience:

1. Check that the audio or URL is available.
2. Check the listening chain and slice tooling before intensive listening work.
3. Generate or reuse the transcript and slice evidence.
4. Build a listening note body with real audio slice references for intensive notes.
5. Save the note to the user's Japanese learning library through `listening_notes`.
6. Report the created note, slice count, and any follow-up review needed.

Do not ask the user to prepare an internal artifact manually. If the transcript, slice manifest, or audio tool is missing, explain the concrete missing input or tool and stop before changing files.

## Source Notes

For requests such as "帮我把这篇材料整理成日语学习笔记", preserve source traceability. The resulting note should make the material, transcript, audio reference, or text source easy to audit later.

The source-note task itself should not create vocabulary, grammar, pronunciation, error, or speaking cards. If the user asks for downstream review material, complete or confirm the source note first, then hand off to the appropriate card task.

## Review Materials

For requests such as "把这个词加入复习", search before creating. Check the focused review layer before the base lexicon to avoid duplicates.

Cards should remain concise enough for review. Long explanations belong in source notes or reference notes, not in the review prompt.

## Speaking Cards

For requests such as "这句话很实用，帮我做成口语卡", only create a speaking card when the phrase has been manually reviewed or supplied by the user as a known usable expression.

Do not promote unstable ASR text, raw transcript fragments, or unnatural textbook drills into speaking cards without review.

## Review Rollover

For requests such as "今天复习结束了，帮我结算", summarize the pending review-state changes first. Include the count of cards that would advance, cards that would become mastered, and any blocked cards.

Do not silently batch-update review state. Wait for explicit user confirmation before settlement changes are saved.
