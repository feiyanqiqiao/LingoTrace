from __future__ import annotations

import unittest

from lingotrace.core.reports import CommandReport, Finding


class CommandReportTests(unittest.TestCase):
    def test_report_envelope_is_deterministic_and_machine_checkable(self) -> None:
        report = CommandReport(
            command="validate-vault",
            mode="dry-run",
            exit_code=1,
            errors=[
                Finding(
                    code="context_missing",
                    message="Vault context is required before write-capable workflows.",
                    path=".lingotrace/vault-context.json",
                )
            ],
            warnings=[
                Finding(
                    code="path_config_missing",
                    message="Pack defaults will be used.",
                    severity="warning",
                )
            ],
            read_files=[".lingotrace/vault-context.json"],
            planned_writes=[{"path": "review/example.md", "action": "create"}],
            artifacts={"manifest": "artifacts/manifest.json"},
        )

        envelope = report.to_dict()

        self.assertEqual(
            [
                "command",
                "mode",
                "accepted",
                "exit_code",
                "errors",
                "warnings",
                "read_files",
                "planned_writes",
                "changed_files",
                "skipped_files",
                "blocked_files",
                "artifacts",
            ],
            list(envelope.keys()),
        )
        self.assertFalse(envelope["accepted"])
        self.assertEqual("context_missing", envelope["errors"][0]["code"])
        self.assertEqual(".lingotrace/vault-context.json", envelope["errors"][0]["path"])
        self.assertEqual([], envelope["changed_files"])
        self.assertEqual({"manifest": "artifacts/manifest.json"}, envelope["artifacts"])

    def test_report_is_accepted_only_with_zero_exit_and_no_errors(self) -> None:
        self.assertTrue(CommandReport(command="validate-pack", mode="check").accepted)
        self.assertFalse(
            CommandReport(
                command="validate-pack",
                mode="check",
                errors=[Finding(code="invalid_maturity", message="Invalid maturity.")],
            ).accepted
        )
        self.assertFalse(CommandReport(command="validate-pack", mode="check", exit_code=1).accepted)


if __name__ == "__main__":
    unittest.main()
