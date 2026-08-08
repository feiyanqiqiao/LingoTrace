from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.doctor import inspect_onboarding, recommended_locations


class OnboardingDoctorTests(unittest.TestCase):
    def test_ready_runtime_accepts_missing_optional_desktop_and_listening_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            vault = root / "vault"
            (runtime / "lingotrace").mkdir(parents=True)
            (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")

            report = inspect_onboarding(
                language="english",
                vault_root=vault,
                runtime_root=runtime,
                platform_name="linux",
                home=root / "home",
                environ={},
                which=lambda name: "/usr/bin/python3" if name == "python3" else None,
            )

        self.assertTrue(report.accepted, report.to_dict())
        warning_codes = {finding.code for finding in report.warnings}
        self.assertEqual({"git_not_found", "listenkit_not_found", "obsidian_desktop_not_found"}, warning_codes)
        dependencies = json.loads(report.artifacts["dependencies"])
        self.assertEqual("found", dependencies["python"]["status"])
        self.assertEqual("missing_optional", dependencies["obsidian_desktop"]["status"])

    def test_missing_python_and_invalid_runtime_are_required_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = inspect_onboarding(
                language="japanese",
                vault_root=root / "vault",
                runtime_root=root / "missing-runtime",
                platform_name="linux",
                home=root / "home",
                environ={},
                which=lambda _name: None,
            )

        self.assertFalse(report.accepted)
        self.assertEqual(
            {"python_required", "runtime_root_invalid"},
            {finding.code for finding in report.errors},
        )

    def test_vault_and_runtime_must_not_contain_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            (runtime / "lingotrace").mkdir(parents=True)
            (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")
            report = inspect_onboarding(
                language="english",
                vault_root=runtime / "private-vault",
                runtime_root=runtime,
                platform_name="linux",
                home=Path(tmp) / "home",
                environ={},
                which=lambda name: "/usr/bin/python3" if name == "python3" else None,
            )

        self.assertFalse(report.accepted)
        self.assertIn("vault_runtime_overlap", {finding.code for finding in report.errors})

    def test_listenkit_directory_requires_public_cli_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            listenkit = root / "ListenKit"
            (runtime / "lingotrace").mkdir(parents=True)
            (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")
            (listenkit / "cli").mkdir(parents=True)
            (listenkit / "README.md").write_text("# ListenKit\n", encoding="utf-8")
            (listenkit / "cli" / "generate-markdown.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            report = inspect_onboarding(
                language="english",
                vault_root=root / "vault",
                runtime_root=runtime,
                listenkit_root=listenkit,
                platform_name="linux",
                home=root / "home",
                environ={},
                which=lambda name: "/usr/bin/python3" if name == "python3" else None,
            )

        dependencies = json.loads(report.artifacts["dependencies"])
        self.assertEqual("found", dependencies["listenkit"]["status"])
        self.assertNotIn("listenkit_not_found", {finding.code for finding in report.warnings})

    def test_recommended_locations_are_platform_specific(self) -> None:
        macos = recommended_locations("english", platform_name="macos", home="/Users/example", environ={})
        windows = recommended_locations(
            "japanese",
            platform_name="windows",
            home=r"C:\Users\Example",
            environ={"USERPROFILE": r"C:\Users\Example", "LOCALAPPDATA": r"C:\Users\Example\AppData\Local"},
        )
        linux = recommended_locations("english", platform_name="linux", home="/home/example", environ={})

        self.assertEqual(
            "/Users/example/Library/Application Support/LingoTrace/runtime",
            macos["runtime_root"],
        )
        self.assertEqual(r"C:\Users\Example\AppData\Local\LingoTrace\runtime", windows["runtime_root"])
        self.assertEqual(r"C:\Users\Example\Documents\Obsidian\LingoTrace-Japanese", windows["vault_root"])
        self.assertEqual("/home/example/.local/share/lingotrace/runtime", linux["runtime_root"])


if __name__ == "__main__":
    unittest.main()
