# Read-only preflight

Confirm the project root, read every governance file in this directory, and inspect the Git state, `.specify/`, manifest, configuration, adapter, CLI version, and integration status. Read-only commands must not create `.specify/`, a plan, a backup, or a binding.

If the target project already has the runtime-selected project context anchor, first treat it as project-owned user rules. Bootstrap or onboarding may inject or update the governance loader only through `append-managed-loader`; every byte outside the managed region and its byte order must be preserved. Overwriting, deleting, reordering, normalizing, or whole-file formatting is prohibited. A missing anchor may be created only at the exact path supplied and evidence-validated in an approved plan.

Before `plan-init`, the current Agent must ask the user for the BCP-47 language tag for new or substantially rewritten project documentation. Supply it as `--documentation-language <tag>`; the manager must reject a missing or invalid value. Persist the explicit selection in project configuration and the selected context-anchor loader. Do not infer a language or translate existing documents automatically.

# Governance package bootstrap

Extract the portable artifact to `.spec-kit-governance/staging/<plan-id>/`, validate the manifest and SHA-256, and generate `plan-governance-bootstrap` from the staging manager. Bootstrap writes only the committed governance package, manager, manifest, and configuration, plus the Loader at the exact runtime-selected context-anchor path. It does not install the current Agent integration. Apply only after the user authorizes the exact plan ID/hash, then verify with the project manager.

# New projects

When `.specify/` does not exist, first obtain a clear approved key, rehearse with the same CLI/key in a temporary directory, and generate an external mutation scope. A non-empty brownfield may use `specify init --here --force --non-interactive --integration <key>` only through a dedicated `plan-init`; an empty project uses the command without force. After the actual change, compare the scope inventory, status, and managed files; an escape or incomplete recovery returns `RECOVERY_REQUIRED`.

# Existing projects

Run `specify integration status --json`. A missing, modified, invalid, or blocking finding returns `STATE_BROKEN`; an unwritable native repair for the current runtime returns `NATIVE_INSTALL_BLOCKED`. Do not rerun init to create duplicate specifications.

# Native onboarding

Installation health for a candidate key yields only `NATIVE_CANDIDATE_INSTALLED_UNVERIFIED`. Write the user-provided anchor and supply `--anchor-evidence <project-relative-json>` in `plan-onboard`; then perform fresh-session Loader validation and confirm that the runtime ID and key match. Before validation, it must not be active, `READY`, or represented as complete.

Fresh-session evidence must be project-relative JSON that proves at least the runtime ID, integration key, fresh session, Loader loading, and managed-file verification. The binding may become `active` only after `plan-activate-binding` is applied with the exact approval hash.

Materialized delivery is allowed only when Loader fresh-session validation explicitly fails and the user actively chooses it; `plan-onboard` must also provide `--delivery-mode materialized --loader-failure-evidence <project-relative-json>`. Do not use Materialized as a fallback when native writes fail.

# Generic

`generic` must not enter the native branch. V1 permits it only when project configuration allows it, the current-version native-absence attestation is valid, the installed integration set is empty, Markdown Commands compatibility has been verified, and the user approves it. Return `INTEGRATION_CONFLICT` when the project already has any integration; V1 does not implement migration to generic.

# Native blocker

When the native init target, integration target, managed-file repair, anchor, or parent directory is unwritable; permission is denied; a sandbox blocks the work; or an installation partially fails: preserve and inventory the existing state, return `NATIVE_INSTALL_BLOCKED`, request a writable checkout or permission, and regenerate the plan with the same claimed key after remediation. Do not fall back to generic, switch to another key, or delete existing artifacts.

# Upgrade and rollback

Read the fixed release index from the central source in read-only mode. First generate `plan-upgrade`, review Policy, Reference, manager, adapter, manifest, and capability inventory, then apply it. The inventory before and after the upgrade must be equivalent unless every change has an approved `REPLACE`. Rollback must not uninstall integrations or delete user work; incomplete failure recovery returns `RECOVERY_REQUIRED`.
