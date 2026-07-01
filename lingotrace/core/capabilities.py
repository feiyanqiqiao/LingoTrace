from __future__ import annotations

from dataclasses import dataclass

from .context import VaultContext
from .manifests import LanguagePackManifest
from .reports import Finding


PHASE0_CAPABILITY_IDS = {
    "listening_notes",
    "source_notes",
    "review_materials",
    "speaking_cards",
    "review_rollover",
    "total_training_dashboard",
}


@dataclass(frozen=True)
class CapabilityDecision:
    capability_id: str
    accepted: bool
    findings: list[Finding] | tuple[Finding, ...]


class CapabilityRegistry:
    def __init__(self, manifest: LanguagePackManifest):
        self._manifest = manifest

    def require(self, capability_id: str, context: VaultContext) -> CapabilityDecision:
        if capability_id not in PHASE0_CAPABILITY_IDS:
            return _rejected(capability_id, "unknown_capability", f"Unknown capability: {capability_id}.")

        if capability_id not in context.enabled_capabilities:
            return _rejected(
                capability_id,
                "capability_not_enabled",
                f"Capability is not enabled in the Vault context: {capability_id}.",
            )

        if capability_id in self._manifest.unsupported_capabilities:
            unsupported = self._manifest.unsupported_capabilities[capability_id]
            return _rejected(capability_id, "unsupported_capability", unsupported.failure_reason)

        capability = self._manifest.capabilities.get(capability_id)
        if capability is None:
            return _rejected(
                capability_id,
                "capability_undeclared",
                f"Capability is neither declared nor explicitly unsupported: {capability_id}.",
            )

        if capability.maturity != "stable":
            return _rejected(
                capability_id,
                "capability_not_stable",
                f"Capability is not stable and is unavailable by default: {capability_id}.",
            )

        for dependency in capability.depends_on:
            if dependency not in context.enabled_capabilities:
                return _rejected(
                    capability_id,
                    "missing_capability_dependency",
                    f"Capability dependency is not enabled: {dependency}.",
                )

        return CapabilityDecision(capability_id=capability_id, accepted=True, findings=[])


def _rejected(capability_id: str, code: str, message: str) -> CapabilityDecision:
    return CapabilityDecision(
        capability_id=capability_id,
        accepted=False,
        findings=[Finding(code=code, message=message)],
    )
