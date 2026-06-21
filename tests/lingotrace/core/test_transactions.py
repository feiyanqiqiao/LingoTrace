from __future__ import annotations

import unittest

from lingotrace.core.capabilities import CapabilityDecision
from lingotrace.core.reports import Finding
from lingotrace.core.transactions import WritePlanEntry, WriteTransactionGuard


class WriteTransactionGuardTests(unittest.TestCase):
    def test_preview_records_planned_writes_without_changing_files(self) -> None:
        decision = CapabilityDecision(capability_id="review_materials", accepted=True, findings=())
        guard = WriteTransactionGuard(decision)

        report = guard.preview(
            [
                WritePlanEntry(
                    path="review/focus/vocab/example.md",
                    action="create",
                    reason="new review card",
                )
            ]
        )

        self.assertTrue(report.accepted)
        self.assertEqual(
            [{"path": "review/focus/vocab/example.md", "action": "create", "reason": "new review card"}],
            report.to_dict()["planned_writes"],
        )
        self.assertEqual([], report.to_dict()["changed_files"])

    def test_apply_blocks_when_capability_decision_is_rejected(self) -> None:
        decision = CapabilityDecision(
            capability_id="review_materials",
            accepted=False,
            findings=(Finding(code="capability_not_enabled", message="Capability is not enabled."),),
        )
        guard = WriteTransactionGuard(decision)

        report = guard.apply(
            [
                WritePlanEntry(
                    path="review/focus/vocab/example.md",
                    action="create",
                    reason="new review card",
                )
            ]
        )

        self.assertFalse(report.accepted)
        self.assertEqual("capability_not_enabled", report.to_dict()["errors"][0]["code"])
        self.assertEqual(["review/focus/vocab/example.md"], report.to_dict()["blocked_files"])
        self.assertEqual([], report.to_dict()["changed_files"])


if __name__ == "__main__":
    unittest.main()
