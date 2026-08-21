# First-time Agent onboarding

1. The current Agent must provide a runtime ID and an exact integration key. A display name without a key returns `KEY_REQUIRED`.
2. Read `specify version` and `specify --help`; if the CLI is absent, request authorization and recommend `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<approved-40-character-commit-sha>`. Do not install it silently, use a floating branch, or treat installation as proof that Agent-specific project files exist.
3. Run read-only `doctor` and `resolve-agent`. Do not treat a default, a PATH tool, a directory name, or a similar product as an identity.
4. When `.specify/` exists, run `specify integration status --json`. Reuse a healthy existing active binding; otherwise generate an onboarding plan.
5. When `.specify/` does not exist, complete the Agent-neutral governance bootstrap first, then generate a `plan-init` with an explicit integration. Omitting `--integration` is prohibited.
6. When the native integration is not installed, the plan uses `specify integration install <claimed-key>` without `--force`; multi-install safety is decided by the CLI gate.
7. For an external native install, pass each project-relative target prefix explicitly from the current CLI/runtime's reported integration metadata as `--allowed-path-prefix <prefix>`. The manager never guesses a Skills, Commands, or context directory. A missing or incomplete scope must stop the plan rather than broaden the prefix.
8. Any unwritable native target, permission, sandbox, repair, or installation error returns `NATIVE_INSTALL_BLOCKED`; preserve the existing state and stop.
9. A context anchor may come only from an active binding or from a project-relative path explicitly supplied by the user, and it must carry compatibility evidence through `plan-onboard --anchor-evidence <project-relative-json>`. Stop for an unknown or unsupported format.
10. Materialized delivery is allowed only when Loader fresh-session validation fails and the user explicitly requests it; `--loader-failure-evidence <project-relative-json>` must be supplied at the same time.
11. Perform the sole apply only after the user authorizes it with `apply-plan --approve-plan-id <id> --approve-plan-sha256 <hash>`.
12. In a new session, verify the anchor, Loader, Policy version, probe token, runtime ID, integration key, native workflow, and existing inventory; save project-relative verification evidence, then generate `plan-activate-binding`. Until that plan is applied, the binding may only be `provisional` and must not be reported as `READY`.

13. If the project already has the runtime-selected context anchor, onboarding may only inject or update the managed loader region; every byte outside that region must be preserved byte-for-byte. Overwriting, deleting, reordering, normalizing, or whole-file formatting is prohibited. If the anchor is absent, create only the exact runtime- or user-supplied path after evidence validation; never guess a filename.
14. Before `plan-init`, ask the user for the BCP-47 language tag for new or substantially rewritten project documentation. Pass it as `--documentation-language <tag>`. The manager stores the explicit selection in `PROJECT_CONFIG.json` and the selected context-anchor loader; it must not infer a language or mass-translate existing documents.
