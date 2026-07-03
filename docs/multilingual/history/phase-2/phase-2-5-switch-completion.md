# Phase 2.5 Switch Completion Gate

Phase 2.5 completes the post-cutover switch. It does not repeat private data migration. It ensures daily Japanese learning runs through the LingoTrace core, the Japanese language pack, and explicit target Vault configuration.

## Completion Criteria

Phase 2.5 is complete only when all of these conditions hold:

- all five Japanese workflows run through `lingotrace.packs.japanese.workflows:*`;
- every write-capable workflow passes through the core write guard before changing a target Vault file;
- preview mode reports planned writes and never edits files;
- apply mode writes only target Vault relative paths and reports changed files;
- missing Vault context, disabled capability, missing input, invalid path, or unavailable external input stops before write;
- public docs no longer present old local entry paths as the target runtime;
- legacy root retirement is visible in Git tracking and public allowlist checks;
- the canonical total-training view lives in the Japanese pack and preserves the today or next-day review filter;
- the old Vault remains in read-only observation or historical reference until separate user confirmation.

## Workflow Surface

The five Japanese workflows are:

- `lingotrace.packs.japanese.workflows:listening_notes`
- `lingotrace.packs.japanese.workflows:source_notes`
- `lingotrace.packs.japanese.workflows:review_materials`
- `lingotrace.packs.japanese.workflows:speaking_cards`
- `lingotrace.packs.japanese.workflows:review_rollover`

These entrypoints must not rely on old local runtime paths, folder-name language guessing, or source Vault layout assumptions. The target language, explanation language, language pack, schema version, and enabled capabilities come from `.lingotrace/vault-context.json`.

## Legacy Root Retirement

The public repository no longer keeps old operational roots as supported runtime surfaces. The following roots are local historical material only:

- old local workflow skill roots;
- old public Vault scaffold roots;
- old reusable dashboard path under the source Vault tree.

Historical behavior may remain documented in Phase 0 and Phase 1 evidence. That evidence does not authorize restoring the old runtime as a supported target mode.

## Total Training View Parity

The canonical dashboard template is `lingotrace/packs/japanese/views/total-training.base`.

It must preserve the mature today or next-day review entry behavior:

- root filters restrict entries to known training tracks;
- `next_day_flag` or an equivalent due and next-day formula is present;
- the primary daily view filters on that flag instead of showing every active note;
- active notes without a valid `track` do not appear in the total-training entry queue.

The active target Vault should use this canonical template. Updating the target Vault copy is a local synchronization step, not a private data migration.

## Boundary

Phase 2.5 does not ship English support, delete the old Vault, archive the old Vault, or commit private migration artifacts. Final removal of the old Vault requires separate user confirmation after read-only observation.
