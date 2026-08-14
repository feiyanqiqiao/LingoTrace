# Multilingual Listening Notes User Stories and Acceptance Tests

Status: `Reference Guidance`

Maturity path: `Reference Guidance -> Candidate Contract -> Enforced Contract`

Related guidance index: [Language Pack Capability Guidance](language-pack-capability-guidance.md)

## Purpose

This document defines the current user-facing behavior required from the `listening_notes` capability across language packs. Japanese and English implementations plus current public tests provide the reference evidence.

Listening-note behavior is not considered supported until it has a user story, acceptance criteria, and regression or manual-review evidence.

## Applicability

All language packs that implement `listening_notes` should index, reference, and satisfy this document before the capability is considered complete.

This document is shared guidance for:

- Turning one local audio file or media URL into a traceable listening note.
- Separating fixed listening-script generation from flexible source-note generation.
- Supporting extensive listening notes and intensive sentence or dialogue slice notes.
- Preserving transcript artifacts, source audio references, and manually curated sentence selections.
- Blocking incomplete intensive notes when reliable slice evidence is missing.
- Keeping review-card extraction and speaking-card promotion as downstream workflows.

Language packs may define their own transcript engines, pronunciation cues, fields, templates, and sentence-selection standards. Japanese pitch accent, `accent_display`, `Shadowing_*` conventions, and Chinese explanation labels are reference behavior, not generic core fields.

## Language Applicability Matrix

Labels:

- `Required`: every language pack implementing this capability should satisfy the behavior.
- `Optional`: the behavior is useful but only required when the pack declares the supporting feature.
- `Language-Specific`: the behavior depends on language-owned fields, templates, or pedagogy.
- `Covered`: current implementation or regression evidence exists.
- `Partial`: current support exists, but not all acceptance criteria are proven.
- `Planned`: expected for future implementation, but not currently covered.
- `Unsupported`: the pack does not currently support this behavior.
- `N/A`: not applicable to the pack.

| User story | Shared | Japanese | English | Notes |
| --- | --- | --- | --- | --- |
| `US-1` One audio or URL to a traceable note | `Required` | `Covered` | `Covered` | The official tool selects `en-US` from English Vault context and writes through the English guard. |
| `US-2` Separate listening from source notes and review cards | `Required` | `Covered` | `Covered` | Both packs keep extraction and later card promotion separate. |
| `US-3` Extensive listening without slices | `Optional` | `Covered` | `Covered` | English supports the shared extensive-listening route. |
| `US-4` Intensive notes from reliable slice evidence | `Optional` | `Covered` | `Covered` | English uses the same validated slice evidence and English-owned note fields. |
| `US-5` Reviewed manifest for unreliable timestamps | `Optional` | `Covered` | `Covered` | The official language-neutral tool enforces reviewed manifests for uncertain boundaries. |
| `US-6` Preserve manual sentence selection on rerun | `Required` | `Covered` | `Covered` | Existing curated sections are preserved independent of target language. |
| `US-7` Curate directly memorizable sentences | `Optional` | `Partial` | `Partial` | Naturalness and productive value remain model-reviewed in both languages. |
| `US-8` Preserve provenance and raw artifacts | `Required` | `Covered` | `Covered` | English uses the same guarded artifact bundle under its listening role. |
| `US-9` Clear runtime/resource failure | `Required` | `Covered` | `Covered` | English reports missing ASR/slice tooling and does not load Japanese dictionaries. |
| `US-10` Explicit unsupported declaration | `Required` | `N/A` | `N/A` | Both current packs implement listening notes. |
| `US-11` Language-specific pronunciation cues | `Language-Specific` | `Covered` | `Covered` | Japanese may annotate pitch accent; English keeps plain transcript and owns stress/phoneme cards separately. |
| `US-12` Multi-ASR cross-check | `Optional` | `Covered` | `Covered` | Both locales use provider-neutral dual-ASR comparison and validated LLM consensus. |
| `US-13` Short-choice exam structure | `Optional` | `Covered` | `N/A` | The current short-choice heuristics are Japanese exam-specific. |
| `US-14` Listening frontmatter and dashboard readiness | `Required` | `Covered` | `Covered` | English emits `en/listening` fields and has listening dashboard views. |
| `US-15` Conservative dialogue rendering | `Optional` | `Covered` | `Covered` | Language-neutral dialogue fallback is available to English listening notes. |
| `US-16` Dry-run, naming, and uncertain-output gate | `Required` | `Partial` | `Partial` | Naming quality still needs model or human review for real media. |
| `US-17` Single-item safety and no default batch writes | `Required` | `Covered` | `Covered` | The official tool rejects default batch writes for both packs. |

## Ownership Boundary

Core owns:

- Vault context loading.
- Language-pack manifest loading.
- Capability enablement and stability checks.
- Vault-relative write guards.
- `FileMutation` preview/apply execution.
- Atomic file-application semantics and blocked-write reporting.

External audio tooling owns:

- Media download or capture.
- Speech recognition.
- Raw transcript JSON or Markdown artifacts.
- Deterministic audio clipping when a slice manifest is provided.

Language packs own:

- Natural-language agent instructions for listening-note tasks.
- Path roles for listening material roots.
- Listening note templates and required fields.
- Extensive vs intensive routing policy.
- Pronunciation or accent rendering rules.
- Slice grouping rules for sentence, dialogue, or numbered-dialogue material.
- Second-phase productive-chunk curation.
- Pack-level regression tests and manual review cases.

## User Stories

### 1. Convert One Audio Or URL Into A Traceable Listening Note

As a learner, I want one audio file or media URL to become a readable listening note, so I can inspect the transcript without juggling external tools.

Acceptance criteria:

- The workflow accepts one local audio file or one URL plus a target listening directory.
- Local audio remains embedded or referenced from the listening material directory.
- URL input persists the finalized local audio and raw transcript artifacts before rendering the note.
- The note records transcript status and transcript reference.
- The workflow stops before writing when the audio, URL output, transcript tool, or target path is missing.

Japanese reference:

- The daily request is "请把这段音频做成精听稿 / 听力笔记 / 泛听笔记".
- Transcript acquisition is delegated to ListenKit.
- Rendered notes use `track: listening`, `transcript_status`, `transcript_ref`, and a source-audio embed.

Regression coverage:

- `test_japanese_pack_contains_skill_first_agent_entry`
- `test_public_user_docs_are_natural_language_first`

### 2. Keep Listening Notes Separate From Source Notes And Review Cards

As a learner, I want fixed listening-script work to stay separate from flexible study-note and card workflows, so each workflow has a clear purpose.

Acceptance criteria:

- Listening script generation creates or updates a listening note, not a source note.
- Flexible article, video-summary, or transcript-backed study notes are routed to `source_notes`.
- Vocabulary, grammar, pronunciation, and error cards are routed to `review_materials`.
- Useful sentence promotion to speaking cards is routed to `speaking_cards`.
- The listening workflow may report downstream candidates but must not silently create review cards or speaking cards.

Current capability boundary:

- `listening_notes` owns fixed listening-practice notes.
- `source_notes` owns flexible source notes.
- `review_materials` owns review cards.
- `speaking_cards` owns speaking-card promotion.

Regression coverage:

- `test_japanese_pack_contains_skill_first_agent_entry`
- `test_review_material_agent_skill_requires_confirmation_for_risky_writes`

### 3. Default To Extensive Listening Without Sentence Slices

As a learner, I want ordinary listening material to become a complete script without extra slice artifacts, so the note stays lightweight when I only need broad comprehension.

Acceptance criteria:

- Extensive mode is the default when the user does not explicitly ask for intensive listening.
- Extensive notes include the transcript script.
- Extensive notes do not render an intensive learning package.
- Extensive notes do not create sentence slice blocks or slice embeds.
- Pronunciation or accent cues may be rendered inline according to the language pack's policy.

Japanese reference:

- Extensive notes use `listening_mode: extensive`.
- They render `## 脚本` and omit `## 精听学习包`.
- Japanese may annotate known pitch accent candidates in the script.

Regression coverage:

- `test_extensive_note_has_no_intensive_blocks_or_slices`

### 4. Build Intensive Notes Only From Reliable Slice Evidence

As a learner, I want intensive listening notes to contain real sentence or dialogue clips, so I can repeat one short unit without dragging through a long recording.

Acceptance criteria:

- Intensive mode is used only when the user asks for intensive listening or the pack has an explicit equivalent policy.
- Intensive notes render a learning package before or alongside the transcript according to the pack template.
- Every learning block has a stable slice id, slice text, and a real non-empty audio reference.
- `segment_count`, headings, manifest entries, and audio embeds agree.
- A note with missing clips, placeholders, or mismatched slice counts is incomplete.

Japanese reference:

- Intensive notes use `listening_mode: intensive`.
- Each block uses `### SNN`.
- Audio clips are embedded as material-local slice files.

Regression coverage:

- `test_intensive_note_segments_match_manifest_and_nonempty_slice_files`

### 5. Require A Reviewed Manifest When Timestamps Are Unreliable

As a learner, I want the workflow to stop when automatic timestamps are unreliable, so the system does not fabricate precision.

Acceptance criteria:

- If automatic segmentation cannot produce reliable slice boundaries, the workflow blocks completion.
- The user-facing report names the missing resolution, such as a reviewed slice manifest.
- The workflow does not write a finished intensive note when the required manifest is missing.
- Generic normalization may clean punctuation or spacing, but material-specific transcript corrections belong in reviewed artifacts.
- The workflow must not use a low-quality `extensive` note as an intermediate artifact for intensive repair; it should use saved transcript artifacts and a reviewed manifest instead.

Japanese reference:

- A blocked intensive run asks for `--slice-manifest` with explicit ranges and text.
- Numbered dialogue, dialogue exchange, and sentence material are classified from transcript structure, not path names.

Regression coverage:

- `test_unreliable_timestamps_require_reviewed_manifest`

### 6. Preserve Manual Chunk Selection On Rerun

As a learner, I want rerunning transcription to preserve hand-curated sentence selections and notes, so regeneration does not erase my review work.

Acceptance criteria:

- Existing curated common chunks are preserved unless the user explicitly asks to reset them.
- Existing manual note sections are preserved unless the user explicitly asks to replace them.
- Existing listening mode is preserved when rerunning an existing note unless the user asks to change mode.
- Legacy notes that already contain `## 精听学习包` are treated as `intensive`; unmarked existing notes default to `extensive`.
- The workflow asks before overwriting or merging when the target note already exists and the write is risky.

Japanese reference:

- Preserve `## 常用语块` and the legacy `## 可直接背的常用句` heading without silently rewriting either one.
- Preserve frontmatter `daily_use_sentences`.
- Preserve extra manual sections such as personal notes.

Regression coverage:

- `test_rerun_preserves_manual_sentence_selection_and_sections`

### 7. Curate A Small Set Of Productive Chunks

As a learner, I want the note to highlight only a few productive chunks, so listening input can become active output without memorizing source-specific full sentences.

Acceptance criteria:

- After transcript rendering, the agent performs a second-phase chunk-selection pass.
- The selected set may contain 0 to 5 chunks and has no mechanical length threshold.
- Selection favors replaceable patterns with clear cross-scene communicative value.
- Empty selection is acceptable when no chunk is genuinely useful.
- `daily_use_sentences` stores only the productive Japanese chunk patterns and stays aligned with the section.

Japanese reference:

- New notes use `## 常用语块`; legacy `## 可直接背的常用句` sections remain readable and preserved.
- Each item records `语块`, `类型`, `素材原句`, `替换练习`, and `交际作用`.
- The source sentence is a listening anchor, not the memorization target.
- Dialogue material prefers reusable questions, responses, greetings, requests, confirmations, refusals, and social formulas.

Regression coverage:

- `test_rerun_preserves_manual_sentence_selection_and_sections`
- Manual review remains required for sentence quality and naturalness.

### 8. Preserve Provenance And Raw Artifacts

As a learner, I want the note and its artifacts to make the transcript auditable later, so I can trace the note back to the original source.

Acceptance criteria:

- Raw transcript artifacts are stored in a material-local artifact location or another pack-approved location.
- URL-derived audio keeps the original URL or tool artifact when available.
- Local audio notes retain a stable source-audio reference.
- Intensive runs keep the resolved slice manifest or export report needed to audit slice boundaries.
- `## 素材说明` records the source, generation route, known limits, and review needs.
- Generated notes must not depend on private cache paths as the only provenance.

Japanese reference:

- ListenKit `.listenkit.md` and `.listenkit.json` artifacts are kept under `artifacts/`.
- Intensive runs keep slice export and review artifacts.

Regression coverage:

- `test_intensive_note_segments_match_manifest_and_nonempty_slice_files`
- Manual review of artifact paths is still needed for real media runs.

### 9. Fail Clearly When Runtime Or Language Resources Are Missing

As a learner, I want the workflow to fail with a clear reason when the audio or language runtime is unavailable, so I know what must be fixed before trying again.

Acceptance criteria:

- Missing ASR, media, clipping, dictionary, or pronunciation resources cause a clear blocking error.
- The workflow does not install or upgrade packages during ordinary generation.
- Language-specific pronunciation data is treated as a candidate source unless the pack has confirmed data.
- The workflow must not invent plausible-looking pronunciation or accent information.

Japanese reference:

- LingoTrace listening rendering uses a dedicated cache-backed Python runtime.
- ListenKit uses its own dedicated runtime.
- Japanese pitch accent candidates come from confirmed vault data or offline dictionary candidates; unknown values remain confirmable instead of fabricated.

Regression coverage:

- `tools/listening-transcribe-official/tests/test_transcribe_listening.py`
- `test_unreliable_timestamps_require_reviewed_manifest`

### 10. Declare Unsupported Listening Capability Explicitly

As a learner, I want a language pack without listening tooling to say so plainly, so the agent does not silently fall back to another language's workflow.

Acceptance criteria:

- A language pack that cannot transcribe listening material declares `listening_notes` unsupported.
- The user-facing failure reason is clear and language-pack specific.
- Unsupported packs must not call Japanese runtime, Japanese dictionaries, Japanese path names, or Japanese templates.
- A future implementation must cite this guidance and document language-specific exceptions.

Current reference:

- Japanese and English both implement listening through their own pack workflow and the shared official tool.
- A future unsupported pack must still declare the capability unsupported rather than reusing either implementation.

Regression coverage:

- `test_contributor_guide_records_current_infrastructure_limits`

### 11. Render Language-Specific Pronunciation Cues Without Making Them Core Fields

As a learner, I want the listening note to show the pronunciation cues that matter for the target language, so I can shadow the recording with the right sound pattern.

Acceptance criteria:

- Pronunciation, stress, tone, pitch accent, or prosody annotation is language-pack-owned behavior.
- A language pack may render pronunciation cues in intensive learning blocks when they directly support listening and shadowing.
- A language pack should keep the plain transcript readable; when two views are useful, the practice block can be annotated while the full script remains plain.
- Annotation must use confirmed pack data first, then clearly handled local candidates according to pack policy.
- The workflow must not fabricate plausible-looking pronunciation, tone, stress, or accent values.
- Unknown or disputed pronunciation cues should remain unmarked or be routed to a review process rather than shown as confirmed.

Japanese reference:

- Japanese intensive notes should use inline pitch-accent markers such as `公園⓪` or `京都①` in `## 精听学习包`.
- Japanese intensive notes should keep `## 脚本` plain by default, so the full transcript remains easy to read.
- Japanese vocabulary cards may store canonical `accent_display` as kana plus accent marker, while listening notes may render compact inline cues on the sentence surface.
- New Japanese intensive listening blocks should prefer explicit downstep notation, such as `こいし＼い`, because it shows the pitch drop directly during shadowing and reduces the mental conversion from accent number to sound movement.
- Compact kana plus accent number, such as `こいしい③`, remains the stable storage and dashboard/review-card display style for `accent_display`.
- Existing listening notes should not be bulk-rewritten only to change accent notation style; apply the downstep style to newly generated or explicitly regenerated listening-practice blocks.
- Recent monologue notes and earlier Shadowing notes both support the same broad rule: annotated practice blocks, plain script, and no source labels inside the note body.
- The better default is selective high-value annotation for listening practice rather than marking every possible token. Dense annotation can be useful for focused repair, but it should not make the sentence hard to read.

Regression coverage:

- `test_japanese_listening_guidance_records_accent_annotation_policy`
- `test_learning_package_renders_kana_accent_as_downstep_marker`
- Manual review remains required for disputed Japanese pitch accent.

### 12. Cross-Check Every Transcript With More Than One ASR Route

As a learner, I want every generated listening script to be checked by more than one transcription route by default, so ordinary-looking material does not silently bypass transcript validation.

Acceptance criteria:

- Multi-engine ASR comparison is enabled by default for every generated Japanese listening script, including ordinary extensive notes, intensive notes, local audio, and URL input.
- Single-ASR generation is an explicit user opt-out through `--single-asr`, not an automatic shortcut for ordinary or apparently low-risk material.
- The primary ASR output and secondary ASR output should be persisted as separate artifacts when both are used.
- The workflow should align the two transcripts by timestamp, sentence, or segment id and produce a disagreement report or reviewed transcript artifact.
- The final note should use reviewed consensus text, not a blind merge of two transcripts.
- Disagreements around names, numbers, homophones, particles, endings, or slice boundaries should be surfaced for review.
- When the caller is an LLM-capable agent, disagreement handling should continue automatically in the same task: the agent reads a structured merge request, judges each segment with context, produces a temporary consensus, and reruns the guarded workflow.
- Preview-only runs must materialize the merge request at a stable read-only temporary path that remains available after staging cleanup; the rerun supplies both that request and the reviewed transcript.
- The deterministic runtime must validate audio hash, merge-request identity, segment ids, timestamps, confidence, and completion status before accepting an LLM consensus.
- An LLM-reviewed transcript without its exact pending merge request must be rejected. Decisions selecting the primary, secondary, or agreed text must match the corresponding ASR candidate.
- The agent must tell the learner how many differences were merged, which model performed the merge, and whether any uncertainty remains; low-confidence decisions still block the final note.
- If the secondary ASR route requires GUI permission, network access, paid services, or unavailable language support, the workflow may proceed with a single engine and report the limitation.

Japanese reference:

- The current Japanese chain already supports `faster-whisper` and Apple Speech routes through ListenKit.
- The Japanese Agent Skill must preserve the default dual-ASR route and use `--single-asr` only when the user explicitly asks for it.
- Some existing Shadowing artifacts keep both Apple and faster-whisper transcript files for comparison.
- Japanese disagreement runs emit `artifacts/<audio_stem>.llm-merge-request.json` with a reviewed-transcript template that Codex, Gemini, or another compatible agent can complete without a provider-specific API inside the script.
- The merge request and reviewed transcript use a lightweight artifact schema so the calling agent and deterministic runtime can exchange evidence without sharing provider-specific internals.
- Cross-checking should reduce manual transcript correction, but it does not replace reviewed manifests for intensive slice boundaries.

Regression coverage:

- `test_compare_engine_persists_asr_disagreement_report_without_replacing_primary`
- `test_all_listening_material_defaults_to_dual_asr_unless_opted_out`
- `test_llm_merge_request_contains_provider_neutral_review_template`
- `test_japanese_agent_skill_auto_merges_asr_disagreements`
- `test_llm_reviewed_consensus_skips_retranscription_and_finishes_note`
- `test_provider_neutral_two_pass_merge_survives_preview_cleanup`

### 13. Preserve Short-Choice And Exam Listening Structure

As a learner, I want exam-style short-choice listening to keep its question and option structure, so the note remains useful for review and not just as a paragraph transcript.

Acceptance criteria:

- Short-choice or exam listening material should preserve question numbers and `1/2/3` option structure when the transcript supports it.
- The workflow may use a slow-copy retry or equivalent second pass when the first transcript loses option structure.
- When an existing note already has a clearly better short-choice script, the workflow should preserve it instead of overwriting it with a weaker retranscription.
- The note should keep the prompt, choices, and answer-relevant phrasing easy to compare.
- If the option structure is unstable, the workflow should report uncertainty rather than forcing a misleading layout.

Japanese reference:

- Japanese `実力アップ` / JLPT-style listening files may trigger short-choice mode.
- The current Japanese tool uses a short-choice score and slow-copy retry to protect question numbers and option structure.

Regression coverage:

- `test_listening_guidance_records_remaining_migrated_skill_rules`
- Existing renderer tests cover short-choice scoring and preservation; capability guidance now records the user-facing rule.

### 14. Initialize Listening Frontmatter And Dashboard Readiness

As a learner, I want generated listening notes to appear correctly in the training dashboard, so listening practice can be reviewed and settled alongside other learning work.

Acceptance criteria:

- Generated listening notes include the pack-owned listening track marker.
- Listening notes include status and scheduling fields when the language pack's dashboard or review flow expects them.
- `segment_count` reflects the number of intensive learning blocks, or zero for non-sliced extensive notes.
- `weak_points` records the listening difficulty or likely failure points.
- `practice_focus` states the next concrete listening action.
- `daily_use_sentences` stays aligned with the final common-chunk section and contains only the pack-approved productive chunk patterns.
- Dashboard-facing fields should be stable and concise; long explanations belong in the note body.

Japanese reference:

- Japanese listening notes use `track: listening`, `review_status: backlog`, `priority`, `done_today: false`, blank scheduling fields, `segment_count`, `weak_points`, `practice_focus`, and `daily_use_sentences` unless the user explicitly activates review.
- The total-training dashboard includes listening notes through `track == "listening"`.

Regression coverage:

- `test_listening_guidance_records_remaining_migrated_skill_rules`
- Renderer tests cover frontmatter defaults for ordinary, short-choice, and dialogue material.

### 15. Apply A Conservative Dialogue And Numbered-Dialogue Rendering Contract

As a learner, I want dialogue listening notes to keep speaker turns and numbered groups only when they are reliable, so shadowing practice follows the real recording instead of an invented structure.

Acceptance criteria:

- Dialogue rendering is based on transcript structure, not folder name, lesson title, or material series.
- Use `A：/B：` only when question/answer or response alternation is clearly visible.
- The workflow must not invent `C：` or additional speakers unless the transcript artifact provides reliable speaker metadata.
- Numbered dialogue uses one complete numbered group per learning block when the group boundaries are reliable.
- The spoken group number belongs to its own `SNN` text/audio block and must not be merged into the previous or next block.
- Dialogue/exchange blocks should keep coherent two-turn or four-turn exchanges where the timing supports them.
- Unstable numbering, missing group numbers, mixed monologue/dialogue, or unreliable order should fall back to sentence mode or require a reviewed manifest.

Japanese reference:

- Shadowing numbered dialogues use `dialogue/numbered`.
- Unnumbered question/answer exchanges use `dialogue/exchange`.
- Ordinary monologues remain `sentence/sentence` even under a `Shadowing_*` path.

Regression coverage:

- `test_listening_guidance_records_remaining_migrated_skill_rules`
- Renderer tests cover numbered dialogue detection, conservative A/B rendering, forced-dialogue blocking, and path-independent routing.

### 16. Use Dry-Run, Better Naming, And Uncertain-Output Gate

As a learner, I want uncertain listening generation to pause before writing and use meaningful note names, so the library stays readable and bad transcripts do not overwrite useful notes.

Acceptance criteria:

- When title quality, transcript stability, option structure, dialogue structure, or slice boundaries are uncertain, the workflow should run as preview/dry-run before writing.
- A generated note should prefer a topic-bearing filename, not a generic transcription name.
- If a target note exists, the workflow preserves manual sections and asks before risky overwrite, merge, or mode conversion.
- Existing scripts that are clearly better than a retranscription should be preserved.
- Generic punctuation, whitespace, and digit normalization is acceptable; material-specific corrections belong in reviewed transcript or manifest artifacts.

Japanese reference:

- Prefer names like `manabo_cz18_土用の丑の日とうなぎ.md` rather than a generic `识别稿`.
- Use `--dry-run` when title quality or recognition stability is uncertain.

Regression coverage:

- `test_listening_guidance_records_remaining_migrated_skill_rules`
- Existing renderer tests cover rerun preservation and CLI dry-run routes; naming remains partly manual-reviewed.

### 17. Prefer Single-Item Safety And No Default Batch Writes

As a learner, I want the agent to process one listening item at a time by default, so a broad scan cannot accidentally rewrite many notes or media artifacts.

Acceptance criteria:

- One audio file or one URL is the normal listening-note workflow.
- Batch mode is not a default user workflow.
- Directory scanning or batch processing, if implemented by a tool, must be explicit, previewable, and bounded.
- Broad batch writes should not run just because the user asked for one listening note.
- Internal source labels such as `本地候选` or `待确认` should not appear in the final note body; they may be used internally or in separate review workflows.
- Reviewed listening chunks remain candidates for speaking cards and must not be automatically promoted.

Japanese reference:

- The installed Japanese listening skill says batch mode is intentionally disabled in the current single-item workflow.
- Japanese accent source labels are internal selection labels, not final listening-note body text.
- Listening chunks require a later, separate speaking-card conversion request after offline review. That later request is the confirmation; the extraction task itself must never promote them.

Regression coverage:

- `test_listening_guidance_records_remaining_migrated_skill_rules`
- Renderer tests cover absence of source labels in the practice package; speaking-card promotion remains a separate workflow boundary.

## Agent Use Cases

### Clear Listening Note Request

User says: "请把这段音频做成听力笔记。"

Expected agent behavior:

- Confirm the audio or URL and target listening directory.
- Run the listening chain preflight.
- Generate or reuse transcript artifacts.
- Save a listening note if the target is new or the write is low risk.
- Report the note path, mode, transcript status, and any follow-up review needed.

### Clear Intensive Listening Request

User says: "请把 23.mp3 做成精听稿。"

Expected agent behavior:

- Treat the request as `listening_notes`.
- Check slice tooling before writing.
- Generate real learning-block audio clips.
- Block completion if a reviewed manifest is required.
- Report slice count and unresolved timestamp issues.

### Existing Note Rerun

User says: "这个听力笔记重新转写一下。"

Expected agent behavior:

- Detect the existing note.
- Preserve curated common chunks, legacy common-sentence sections, and manual sections by default.
- Ask before risky overwrite or mode conversion.
- Regenerate transcript-backed sections only within the declared scope.

### Downstream Speaking Card Request

User says in a later task: "把我已经 review 的这些语块转入口语库。"

Expected agent behavior:

- Do not handle it as listening transcription.
- Route to `speaking_cards`.
- Treat the later transfer request as confirmation that the named chunks were reviewed offline; do not ask again per card.
- Reject extraction and promotion inside the same user task.

### Short-Choice Exam Listening Request

User says: "把这道 N2 听力题做成笔记。"

Expected agent behavior:

- Preserve question numbers and answer choices when the transcript supports them.
- Use a second transcription or slow-copy pass when structure is weak and the tool supports it.
- Preserve an existing better script instead of overwriting it.
- Report unresolved question/choice uncertainty.

### Uncertain Transcript Request

User says: "这个录音识别不太准，帮我重新做。"

Expected agent behavior:

- Prefer dry-run or preview first.
- Compare available ASR artifacts when practical.
- When a structured LLM merge request is returned, resolve it automatically in the same task and rerun with the validated temporary consensus.
- Tell the user what the model merged; ask only when important evidence remains low-confidence.
- Preserve manual sections and ask before risky replacement.

## Coverage Matrix

| User story | Current evidence |
| --- | --- |
| One audio or URL to listening note | Japanese Agent Skill and user docs |
| Workflow separation | Japanese Agent Skill routing tests |
| Extensive mode has no slices | `test_extensive_note_has_no_intensive_blocks_or_slices` |
| Intensive slices are real and counted | `test_intensive_note_segments_match_manifest_and_nonempty_slice_files` |
| Unreliable timestamps block completion | `test_unreliable_timestamps_require_reviewed_manifest` |
| Rerun preserves manual curation | `test_rerun_preserves_manual_sentence_selection_and_sections` |
| Common sentence curation | Manual review plus rerun preservation test |
| Provenance and artifacts | Listening fixtures and real-run manual review |
| Runtime/resource failure clarity | Listening renderer tests and manual chain check |
| Unsupported packs fail explicitly | Contributor guide and English pack behavior |
| Language-specific pronunciation cues | `test_japanese_listening_guidance_records_accent_annotation_policy`, `test_learning_package_renders_kana_accent_as_downstep_marker`, plus manual pitch-accent review |
| Multi-engine ASR cross-check | `test_all_listening_material_defaults_to_dual_asr_unless_opted_out`, `test_compare_engine_persists_asr_disagreement_report_without_replacing_primary`, `test_llm_merge_request_contains_provider_neutral_review_template`, `test_llm_reviewed_consensus_skips_retranscription_and_finishes_note`, and `test_japanese_agent_skill_auto_merges_asr_disagreements` |
| Short-choice exam structure | `test_listening_guidance_records_remaining_migrated_skill_rules` plus renderer short-choice tests |
| Listening frontmatter and dashboard readiness | `test_listening_guidance_records_remaining_migrated_skill_rules` plus renderer frontmatter tests |
| Dialogue and numbered-dialogue rendering | `test_listening_guidance_records_remaining_migrated_skill_rules` plus renderer dialogue tests |
| Dry-run, naming, and uncertain-output gate | `test_listening_guidance_records_remaining_migrated_skill_rules`; naming remains manual-reviewed |
| Single-item safety and no default batch writes | `test_listening_guidance_records_remaining_migrated_skill_rules` |

## Open Gaps

- The public contract tests use fixture files and do not prove real ASR quality.
- Common-sentence naturalness still requires manual or model-assisted review.
- Japanese pitch-accent annotation needs better automated checks for density, confidence, and script-vs-practice placement.
- LLM merge quality still needs a broader fixture set for names, numbers, homophones, particles, endings, and ambiguous low-confidence audio before multi-ASR can become required across language packs.
- Topic-bearing filename quality and short-choice answer correctness still need human review for real learning material.
- Batch scanning exists as a tool-level affordance but should not be treated as a default agent workflow until preview and write bounds are stricter.
- Non-Japanese listening implementations need their own transcript engine, pronunciation policy, and slice validation before this guidance can become a candidate contract.
