# LingoTrace Japanese Agent Skill

Use this skill when a user asks in natural language to maintain Japanese learning materials in a LingoTrace-backed Obsidian learning library.

This skill is the daily operating entry for agents. Users should not need to mention internal workflow names, Python functions, CLI flags, Vault schema, or write modes.

## Intent Recognition

Before choosing a workflow, infer the user's real learning intent from ordinary language. Do not match only the example phrases below.

Use these intent families:

- Audio or video to listening material: create or update a listening note, intensive listening script, extensive listening note, transcript-backed note, or audio slices.
- Source material to study note: turn an article, transcript, URL, screenshot text, video content, or pasted text into a traceable Japanese study note.
- Word, grammar, pronunciation, or error to review: add, update, deduplicate, or organize review material.
- Useful sentence to active output: create or update a speaking card for a reviewed phrase the user wants to be able to say.
- End-of-day review settlement: advance completed review items, update next review dates, or close today's review.
- Dashboard or view maintenance: update how a table, Base, filter, formula, column, sort order, or view displays learning items.

The local phrases "更新总训练表" and "请更新总训练表" are clear end-of-day review settlement requests. Route them to review rollover without asking a second confirmation question.

If another phrase could mean more than one intent, ask one short clarification question before writing:

- If the user means today's completed review should be settled, handle it as review rollover.
- If the user means the table display, filters, columns, formulas, or sort order should change, handle it as dashboard/view maintenance and confirm the intended display change.

Examples:

- "更新总训练表" / "请更新总训练表" -> clear review rollover.
- "处理一下总训练表" / "总训练表有点问题" -> ambiguous; ask whether the user means review settlement or dashboard/view maintenance.
- "词汇卡要显示重音和常见搭配" -> dashboard/view maintenance.

Prefer recognizing meaning over wording. Similar requests, abbreviations, typos, mixed Chinese/Japanese/English phrasing, or local habit phrases should be mapped by intent when the intended learning action is clear.

## User Language

Map intuitive study requests to the Japanese pack capabilities:

| User request | Agent task | Capability |
| --- | --- | --- |
| 请把这段音频做成精听稿 / 听力笔记 / 泛听笔记 | Listening note task | `listening_notes` |
| 帮我把这篇材料整理成日语学习笔记 / 生成学习笔记 | Source note task | `source_notes` |
| 把这个词加入复习 / 建词卡 / 建语法卡 | Review material task | `review_materials` |
| 这句话很实用，帮我做成口语卡 / 这句以后要会说 | Speaking card task | `speaking_cards` |
| 今天复习结束了，帮我结算 / 结算复习 / 更新总训练表 / 请更新总训练表 | Review rollover task | `review_rollover` |

Prefer user-facing language such as:

- 保存到你的日语学习库
- 先让我确认将要新增或修改的内容
- 不会覆盖你已经手工整理过的笔记
- 复习结算后会报告更新了哪些卡片
- 缺少音频、来源或日期时，先向用户确认

Avoid asking users to say implementation phrases such as internal workflow names, data envelopes, or write-mode terms.

## Operating Rules

Agent Skill must not write Vault files directly. Vault file changes must route through the LingoTrace core write guard and the Japanese pack capability that matches the task.

Review rollover is card-frontmatter backed: settlement reads and updates the configured review cards directly. The Obsidian total-training Base reads ordinary card frontmatter. Do not create or rely on a parallel review-state JSON store or generated review-state snapshot notes.

Before a write-capable task, the agent must confirm the learning library context exists and that the matching capability is enabled. If context or capability checks fail, stop before writing and explain the missing setup in user-facing language.

Default behavior is risk-based:

- Listening notes, source notes, and speaking cards usually create new files. When the user clearly asks to create them, the agent may save the result after checking that the destination does not already exist.
- If a target note already exists, stop and ask before overwriting or merging. Preserve manually curated listening selections, review notes, and daily summaries.
- Review material maintenance starts with search and duplicate checks. New low-risk cards may be saved; merges, moves, overwrites, or review-card frontmatter changes need confirmation.
- Clear review-settlement requests do not need a second user confirmation. Run `preview -> apply -> second preview`, then report the saved card frontmatter changes.
- Ambiguous requests still require clarification. If preview reports errors, stop before apply.

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

When the learning point is clear, convert the user request, source note, classroom note, or reviewed pasted material into a structured review item before calling `review_materials`. The workflow owns deterministic routing, initialization, duplicate handling, source-note appending, focus/base restoration, and core write guarding for structured items.

Use the review item route for:

- vocabulary with `headword`, optional `reading`, `accent_display`, `meaning_zh`, and `collocations`;
- grammar with `pattern`, `meaning_zh`, and `formation`;
- concrete errors with `correct_form`, `wrong_form`, and `reason`;
- pronunciation issues with `target_text`, `pronunciation_kind`, and `issue_tags`.

Cards should remain concise enough for review. Long explanations belong in source notes or reference notes, not in the review prompt.

If an image-backed item is not clearly readable, or if the card type, headword, grammar pattern, correct answer, or target root is uncertain, stop and ask before writing. Merges, moves, overwrites, and broad rewrites still require user confirmation.

## Speaking Cards

For requests such as "这句话很实用，帮我做成口语卡", only create a speaking card when the phrase has been manually reviewed or supplied by the user as a known usable expression.

Do not promote unstable ASR text, raw transcript fragments, or unnatural textbook drills into speaking cards without review.

## Review Rollover

For requests such as "今天复习结束了，帮我结算", run an internal preview first. If the preview is accepted and has no errors, apply the rollover immediately and run a second preview to verify no planned review writes remain.

After settlement, report the count of cards advanced, cards that became mastered, day180 focus vocabulary cards promoted into base vocabulary, delayed reschedules, blocked cards, and the second-preview result. Settlement may write base vocabulary only for the controlled day180 vocabulary mastery sink; broad base vocabulary merges, moves, deletions, rewrites, and daily-note summaries require a separate explicit content-maintenance task.
