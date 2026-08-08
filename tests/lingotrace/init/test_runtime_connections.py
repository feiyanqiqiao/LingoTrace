from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.english_vault import initialize_english_vault
from lingotrace.init.runtime_connections import (
    current_platform,
    register_runtime_connection,
    resolve_runtime_connection,
    runtime_connection_relative_path,
)


class RuntimeConnectionTests(unittest.TestCase):
    def test_platform_names_are_portable_and_stable(self) -> None:
        self.assertEqual("macos", current_platform("Darwin"))
        self.assertEqual("windows", current_platform("Windows"))
        self.assertEqual("linux", current_platform("Linux"))

    def test_registering_one_platform_never_overwrites_another_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            platform_paths = {
                "macos": "/Users/example/LingoTrace",
                "windows": r"C:\Projects\LingoTrace",
                "linux": "/home/example/LingoTrace",
            }
            non_current = [item for item in platform_paths if item != current_platform()]
            preserved_platform, added_platform = non_current
            preserved_path = vault / runtime_connection_relative_path(preserved_platform)
            preserved_path.parent.mkdir(parents=True)
            preserved_content = {
                "runtime_connection_schema_version": 1,
                "platform": preserved_platform,
                "connections": [
                    {"runtime_root": platform_paths[preserved_platform], "source": "user-confirmed"}
                ],
            }
            preserved_path.write_text(json.dumps(preserved_content), encoding="utf-8")

            report = register_runtime_connection(
                vault,
                platform_paths[added_platform],
                platform_name=added_platform,
                mode="apply",
            )

            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual(preserved_content, json.loads(preserved_path.read_text(encoding="utf-8")))
            added_content = json.loads(
                (vault / runtime_connection_relative_path(added_platform)).read_text(encoding="utf-8")
            )
            self.assertEqual(added_platform, added_content["platform"])
            self.assertEqual(platform_paths[added_platform], added_content["connections"][0]["runtime_root"])

    def test_same_platform_registration_appends_without_removing_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            first_runtime = root / "runtime-one"
            second_runtime = root / "runtime-two"
            _make_runtime(first_runtime, "english")
            _make_runtime(second_runtime, "english")

            first = register_runtime_connection(vault, first_runtime, mode="apply")
            second = register_runtime_connection(vault, second_runtime, mode="apply")

            self.assertTrue(first.accepted, first.to_dict())
            self.assertTrue(second.accepted, second.to_dict())
            content = json.loads((vault / runtime_connection_relative_path()).read_text(encoding="utf-8"))
            self.assertEqual(
                [str(first_runtime), str(second_runtime)],
                [item["runtime_root"] for item in content["connections"]],
            )

    def test_resolution_skips_stale_candidate_and_returns_usable_runtime_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            usable_runtime = root / "runtime"
            _make_runtime(usable_runtime, "english")
            initialize_english_vault(vault, runtime_root=usable_runtime)
            connection_path = vault / runtime_connection_relative_path()
            content = json.loads(connection_path.read_text(encoding="utf-8"))
            content["connections"].insert(0, {"runtime_root": str(root / "missing"), "source": "user-confirmed"})
            connection_path.write_text(json.dumps(content), encoding="utf-8")

            report = resolve_runtime_connection(vault)

            self.assertTrue(report.accepted, report.to_dict())
            self.assertEqual(str(usable_runtime), report.artifacts["runtime_root"])
            self.assertTrue(report.artifacts["agent_skill"].endswith("packs/english/agent_skills/SKILL.md"))

    def test_missing_current_platform_connection_tells_agent_to_ask_and_preserve_other_platforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            other_platform = "windows" if current_platform() != "windows" else "linux"
            path = vault / runtime_connection_relative_path(other_platform)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "runtime_connection_schema_version": 1,
                        "platform": other_platform,
                        "connections": [
                            {
                                "runtime_root": (
                                    r"C:\Projects\LingoTrace"
                                    if other_platform == "windows"
                                    else "/opt/LingoTrace"
                                ),
                                "source": "user-confirmed",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = resolve_runtime_connection(vault)

            self.assertFalse(report.accepted)
            self.assertEqual("runtime_connection_required", report.errors[0].code)
            self.assertIn("Do not modify connection files for other platforms", report.errors[0].message)


def _make_runtime(root: Path, pack: str) -> None:
    package = root / "lingotrace"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    skill = package / "packs" / pack / "agent_skills" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Skill\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
