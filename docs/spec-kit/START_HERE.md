# Entering a project

1. Confirm the actual project root.
2. Read `docs/spec-kit/PROJECT_CONFIG.json`, `LOCAL_OVERRIDES.md`, `POLICY.md`, and `MANIFEST.json`.
3. When work involves the CLI, an integration, an extension, init, upgrade, rollback, or recovery, also read `REFERENCE.md` and `OPERATING_PROTOCOL.md`.
4. Check `.specify/`. If it exists, recover its existing state and do not initialize again.
5. Do not treat the project's default integration as the current Agent identity; the current Agent must provide a runtime ID and exact integration key.
6. Do not claim that the current Agent has native Spec Kit integration until its onboarding is complete.
7. Generate an operation plan before every mutation; the current operator then authorizes it with the exact plan ID and hash, after which the sole `apply-plan` may run.
8. If a native-integration target is unwritable, permission is insufficient, a sandbox blocks the work, managed-file repair fails, or installation fails, stop and return `NATIVE_INSTALL_BLOCKED`; do not switch to generic or another key.

If the project already has the runtime-selected project context anchor, it is a project-owned rules file. The governance loader may only be appended or updated inside its managed region; all other bytes must remain byte-identical. A loader file may be created only at the exact anchor path supplied and evidence-validated in an approved plan.

Before `plan-init`, ask the user which BCP-47 language tag should govern new or substantially rewritten project documentation. Pass the explicit selection as `--documentation-language <tag>` so it is stored in project configuration and written into the selected context anchor. Do not infer or mass-translate.

The project governance package is a shared team baseline and does not depend on personal global rules or a central Reference directory. The central Reference may be used only for explicit update review.
