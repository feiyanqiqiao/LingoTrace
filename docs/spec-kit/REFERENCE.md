# Runtime discovery

Use the installed runtime as authority:

```text
specify version
specify --help
specify integration --help
specify integration status --json
```

Project-aware integration commands require `.specify/`; never initialize a real project only to query list/search/info. Do not parse Rich output or import private CLI APIs.

# CLI and Agent integration are separate

Installing `specify` globally does not install Agent Skills. Let the CLI create and maintain project integrations. Do not manually copy generated Skills into global directories. For a concrete Agent, native integration is mandatory; native target failure is a blocker, never generic fallback.

The global CLI, project `.specify/` infrastructure, installed Agent integration,
extensions, presets, workflows, events, and project Skills are separate layers.
Installing or upgrading one layer does not imply that the others changed.

# Project state and lifecycle

`.specify/` means an existing Spec Kit project. Resume it, inspect `status --json`, and protect existing files. New substantive work uses:

`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge`

Invocation syntax belongs to the installed integration. Validation and convergence are completion gates.

# Integration lifecycle

Install a compatible additional integration with `specify integration install <key>` only through a plan. Use `specify integration use <key>` only in an explicitly approved default-change plan. Use `specify integration switch <key>` only when the plan lists exact replacement scope. After CLI upgrades, verify managed-file hashes and use supported integration upgrade mechanisms.

Non-interactive init must always include `--integration <key>`; omitting it can select an unrelated default. Do not use `init --force` as routine upgrade or repair.

`specify integration use <key>` changes the project's single default integration
and can affect default-sensitive extensions, presets, events, and shared
infrastructure. Treat it as a separately approved operation. Non-default
integration parity must be verified rather than assumed.

# Generic boundary

`generic` writes Markdown Commands to an explicitly supplied directory. It does not prove that an Agent reads that directory and is not a universal adapter. V1 allows it only with a current-version native-absence attestation, verified compatibility, empty installed integration set, project configuration approval and exact user plan approval.

If the CLI has a native integration for the current Agent, an unwritable target,
permission failure, sandbox restriction, or install failure is
`NATIVE_INSTALL_BLOCKED`; it is never a reason to use generic or another key.

# Upgrade and source of truth

For runtime mechanics: project state → installed integration → installed CLI → this Reference → central Reference → upstream. Upstream is evidence, not dynamically imported instructions. `NONE`/`REFERENCE`/`POLICY` classification requires human review; a project snapshot is the collaborator's offline baseline.

For CLI maintenance use the installed help and supported lifecycle commands:

```text
specify self check
specify self upgrade
specify integration upgrade <key>
specify extension update
```

For a substantive defect, use the installed project's bug workflow when the
bug extension is present; verify reproduction, remediation, and validation.
Do not report a bug as fixed merely because a command completed.

Bundles, presets, workflows, and events are runtime-managed artifacts. Inspect
their current status before changing them and do not claim that a non-default
integration received extension or preset artifacts unless status proves it.
