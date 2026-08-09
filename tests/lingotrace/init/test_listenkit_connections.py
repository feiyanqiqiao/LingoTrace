from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.listenkit_connections import (
    listenkit_connection_relative_path,
    recommended_listenkit_root,
    register_listenkit_connection,
    resolve_listenkit_connection,
)
from lingotrace.init.runtime_connections import current_platform


class ListenKitConnectionTests(unittest.TestCase):
    def test_recommended_locations_are_platform_specific_and_overridable(self) -> None:
        self.assertEqual(
            "/Users/example/Documents/Project/ListenKit",
            recommended_listenkit_root(
                runtime_root="/Users/example/Documents/Project/LingoTrace",
                platform_name="macos",
            ),
        )
        self.assertEqual(
            r"C:\Users\Example\AppData\Local\LingoTrace\ListenKit",
            recommended_listenkit_root(
                runtime_root=r"C:\Users\Example\AppData\Local\LingoTrace\runtime",
                platform_name="windows",
            ),
        )
        self.assertEqual(
            "/srv/user-data/lingotrace/ListenKit",
            recommended_listenkit_root(
                runtime_root="/srv/user-data/lingotrace/runtime",
                platform_name="linux",
            ),
        )

    def test_registration_appends_same_platform_candidate_without_removing_old_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            first = root / "listenkit-one"
            second = root / "listenkit-two"
            _make_listenkit(first)
            _make_listenkit(second)

            first_report = register_listenkit_connection(vault, first, mode="apply")
            second_report = register_listenkit_connection(vault, second, mode="apply")

            self.assertTrue(first_report.accepted, first_report.to_dict())
            self.assertTrue(second_report.accepted, second_report.to_dict())
            content = json.loads((vault / listenkit_connection_relative_path()).read_text(encoding="utf-8"))
            self.assertEqual(
                [str(first), str(second)],
                [entry["listenkit_root"] for entry in content["connections"]],
            )

    def test_resolution_skips_stale_candidate_and_returns_usable_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            usable = root / "ListenKit"
            _make_listenkit(usable)
            register_listenkit_connection(vault, usable, mode="apply")
            path = vault / listenkit_connection_relative_path()
            content = json.loads(path.read_text(encoding="utf-8"))
            content["connections"].insert(0, {"listenkit_root": str(root / "missing"), "source": "old-device"})
            path.write_text(json.dumps(content), encoding="utf-8")

            report = resolve_listenkit_connection(vault)

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual(str(usable), report.artifacts["listenkit_root"])
        self.assertTrue(report.artifacts["generate_markdown"].endswith("cli/generate-markdown.sh"))

    def test_missing_connection_offers_reinstall_or_select_existing_without_touching_other_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            other_platform = "windows" if current_platform() != "windows" else "linux"
            other_path = vault / listenkit_connection_relative_path(other_platform)
            other_path.parent.mkdir(parents=True)
            other_path.write_text(
                json.dumps(
                    {
                        "listenkit_connection_schema_version": 1,
                        "platform": other_platform,
                        "connections": [{"listenkit_root": "C:\\ListenKit", "source": "user-confirmed"}],
                    }
                ),
                encoding="utf-8",
            )

            report = resolve_listenkit_connection(vault)

        self.assertFalse(report.accepted)
        self.assertEqual("listenkit_connection_required", report.errors[0].code)
        options = {entry["id"] for entry in json.loads(report.artifacts["recovery_options"])}
        self.assertEqual({"reinstall", "select_existing"}, options)
        self.assertIn("do not modify other platforms", report.errors[0].message)

    def test_all_stale_paths_offer_the_same_two_recovery_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            path = vault / listenkit_connection_relative_path()
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "listenkit_connection_schema_version": 1,
                        "platform": current_platform(),
                        "connections": [{"listenkit_root": str(vault / "missing"), "source": "old-device"}],
                    }
                ),
                encoding="utf-8",
            )

            report = resolve_listenkit_connection(vault)

        self.assertFalse(report.accepted)
        self.assertEqual("listenkit_connection_unavailable", report.errors[0].code)
        self.assertIn("reinstall ListenKit", report.errors[0].message)
        self.assertIn("provide an existing ListenKit directory", report.errors[0].message)

    def test_invalid_checkout_is_rejected_before_connection_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            invalid = root / "not-listenkit"
            invalid.mkdir()

            report = register_listenkit_connection(vault, invalid, mode="apply")

        self.assertFalse(report.accepted)
        self.assertEqual("listenkit_root_invalid", report.errors[0].code)

    def test_listenkit_checkout_must_stay_outside_private_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            listenkit = vault / "tools" / "ListenKit"
            _make_listenkit(listenkit)

            report = register_listenkit_connection(vault, listenkit, mode="apply")

        self.assertFalse(report.accepted)
        self.assertIn("vault_listenkit_overlap", {finding.code for finding in report.errors})


def _make_listenkit(root: Path) -> None:
    (root / "cli").mkdir(parents=True)
    (root / "README.md").write_text("# ListenKit\n", encoding="utf-8")
    (root / "cli" / "generate-markdown.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
