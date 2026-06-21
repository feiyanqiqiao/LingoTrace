from __future__ import annotations

import unittest

from lingotrace.core.capabilities import CapabilityRegistry, PHASE0_CAPABILITY_IDS
from lingotrace.core.context import VaultContext
from lingotrace.core.manifests import CapabilityDeclaration, LanguagePackManifest, UnsupportedCapability


def context(*enabled: str) -> VaultContext:
    return VaultContext(
        vault_schema_version=1,
        target_language="ja",
        explanation_language="zh",
        language_pack="lingo-japanese",
        language_pack_version="0.1.0",
        enabled_capabilities=tuple(enabled),
    )


def capability(
    capability_id: str,
    *,
    maturity: str = "stable",
    depends_on: tuple[str, ...] = (),
) -> CapabilityDeclaration:
    return CapabilityDeclaration(
        id=capability_id,
        maturity=maturity,
        depends_on=depends_on,
        read_path_roles=("focus_vocab_root",),
        write_path_roles=("focus_vocab_root",),
        external_tools=(),
        behavior_evidence=("JP-REVIEW-001",),
        conformance_tests=("tests/lingotrace/core/test_capabilities.py",),
        manual_review_cases=(),
    )


def manifest(
    *capabilities: CapabilityDeclaration,
    unsupported: tuple[UnsupportedCapability, ...] = (),
) -> LanguagePackManifest:
    return LanguagePackManifest(
        language_pack_id="lingo-japanese",
        language_pack_version="0.1.0",
        target_language="ja",
        capabilities={item.id: item for item in capabilities},
        unsupported_capabilities={item.id: item for item in unsupported},
        default_path_roles={"focus_vocab_root": "review/focus/vocab"},
    )


class CapabilityRegistryTests(unittest.TestCase):
    def test_phase0_capability_ids_are_fixed(self) -> None:
        self.assertEqual(
            {
                "listening_notes",
                "source_notes",
                "review_materials",
                "speaking_cards",
                "review_rollover",
            },
            PHASE0_CAPABILITY_IDS,
        )

    def test_rejects_unknown_capability(self) -> None:
        decision = CapabilityRegistry(manifest(capability("review_materials"))).require(
            "grammar_cards",
            context("grammar_cards"),
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(["unknown_capability"], [finding.code for finding in decision.findings])

    def test_rejects_disabled_capability(self) -> None:
        decision = CapabilityRegistry(manifest(capability("review_materials"))).require(
            "review_materials",
            context("review_rollover"),
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(["capability_not_enabled"], [finding.code for finding in decision.findings])

    def test_rejects_unsupported_capability(self) -> None:
        unsupported = UnsupportedCapability(
            id="listening_notes",
            failure_reason="this language pack has no accepted media workflow yet",
            failure_policy="stop_before_write",
            fallback="none",
        )
        decision = CapabilityRegistry(manifest(unsupported=(unsupported,))).require(
            "listening_notes",
            context("listening_notes"),
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(["unsupported_capability"], [finding.code for finding in decision.findings])

    def test_rejects_experimental_capability_by_default(self) -> None:
        decision = CapabilityRegistry(manifest(capability("review_materials", maturity="experimental"))).require(
            "review_materials",
            context("review_materials"),
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(["capability_not_stable"], [finding.code for finding in decision.findings])

    def test_rejects_missing_enabled_dependency(self) -> None:
        decision = CapabilityRegistry(
            manifest(
                capability("review_materials"),
                capability("speaking_cards", depends_on=("review_materials",)),
            )
        ).require("speaking_cards", context("speaking_cards"))

        self.assertFalse(decision.accepted)
        self.assertEqual(["missing_capability_dependency"], [finding.code for finding in decision.findings])

    def test_accepts_enabled_stable_capability(self) -> None:
        decision = CapabilityRegistry(manifest(capability("review_materials"))).require(
            "review_materials",
            context("review_materials"),
        )

        self.assertTrue(decision.accepted)
        self.assertEqual([], decision.findings)


if __name__ == "__main__":
    unittest.main()
