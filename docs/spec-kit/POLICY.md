# Scope

GitHub Spec Kit is used for substantive software engineering work. Read-only investigation, explanation, extremely small typo fixes, and very low-risk minor changes do not require the full lifecycle.

# Projects and brownfields

Before making a change, confirm the actual project root; read every applicable project-local rule, README, architecture document, test, dependency, and CI configuration; understand the actual brownfield system; and protect existing user work. When `.specify/` exists, restore the existing project state and do not routinely reinitialize it.

If the project already has the runtime-selected project context anchor, it is collaboratively maintained project rule content. The Spec Kit loader may be appended to or updated inside that file only through a reviewed manager plan; every byte outside the managed region must be preserved byte-for-byte. The manager may create only the exact anchor path supplied and evidence-validated by the current Agent runtime or user. It must never guess, replace, delete, reorder, normalize, or overwrite an anchor.

Before first-time Spec Kit initialization, ask the user for the BCP-47 language tag for new and substantially rewritten project documentation. Pass the explicit value to `plan-init`, store it in `PROJECT_CONFIG.json`, and render the corresponding rule in the selected context anchor. Never infer it from locale, Agent identity, existing documents, or a default; do not mass-translate existing documents.

# Agent-neutral operation and native integrations

The governance package does not enumerate Agent products in advance. The current Agent must have its runtime ID and exact integration key explicitly declared by the user, host, or Agent runtime; a display name cannot produce a mutation plan. Do not infer identity from PATH, directory names, a default integration, similar product names, or Rich catalog output.

When the current CLI provides a native integration for the current Agent, that native integration is mandatory. An unwritable Skills/Commands target or parent directory, insufficient permission, a sandbox block, managed-file repair failure, or CLI installation failure is `NATIVE_INSTALL_BLOCKED`. Do not downgrade to generic, use another key, or report completion because of convenience, permissions, paths, or conflicts. A binding may be `active` only after fresh-session verification confirms the runtime ID/key match, the context anchor is loaded, and managed files are healthy.

Generic is allowed only when the current CLI has no native integration, project configuration permits it, the current version has a human-reviewed native-absence attestation, the target Agent is compatible with the generic Markdown Commands contract, the project's installed integration set is empty, and the user approves the exact plan. Generic must be marked as non-native and limited support.

# Spec Kit state and lifecycle

New projects must use explicit `specify init --here --non-interactive --integration <approved-key>`. If a non-interactive init omits the key, the CLI may select a default product, so the manager must reject that command. In a non-empty brownfield, `--force` may appear only in a dedicated `plan-init`, with rehearsal, a scope snapshot, backup, exact authorization, and failure recovery; no other command may use `--force`.

Substantive work conceptually follows:

`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge`

Whether to run clarify, checklist, and analyze is determined by the fixed risk-assessment formula in the operation plan; validate and converge are completion gates. Implementation must remain synchronized with the accepted specification, plan, tasks, project constraints, and tests.

# Default and integration coexistence

The project default integration uses a pinned strategy. Routine onboarding must not change the default. A default change may update configuration only after project configuration opens a one-time change window, an independent plan is generated, `specify integration use <key>` is run, and status verification succeeds; failure must restore the prior default. Extensions, presets, events, and shared infrastructure of non-default integrations must be verified separately; do not claim parity.

# Authority order

The policy authority order is: current user instructions, higher-priority runtime rules, safety rules, every applicable project-local rule, project `LOCAL_OVERRIDES.md`, project `POLICY.md`, personal global Bootstrap, project `REFERENCE.md`, personal central Reference, and upstream documentation.

The runtime-fact order is: current-project `.specify/`, installed integrations and manifests, the installed CLI, project `REFERENCE.md`, personal central Reference, and upstream documentation. When runtime facts conflict with the project snapshot, the runtime prevails and the discrepancy must be recorded.

# Validation, upgrades, and completion

Relevant tests, builds, linting, schemas, reproductions, validation, and convergence must be run; failures must not be concealed. The CLI, integrations, extensions, governance package, and Skills are separate layers, and upgrading one layer must not assume that the others upgrade automatically. Central upstream changes must be classified as `NONE`, `REFERENCE`, or `POLICY`; the checker is read-only, the baseline advances last after review, and upstream history must not be merged or Policy automatically deployed.

Completion requires agreement among user intent, accepted artifacts, implementation, project constraints, validation, convergence, the native integration, adapter verification, and capability-inventory conservation. Do not report completion when a blocker, unmapped legacy capability, unplanned deletion, downgrade, invalid state, or default change exists.
