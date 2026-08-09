from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lingotrace.init.english_vault import initialize_english_vault
from lingotrace.init.listenkit_connections import (
    device_listenkit_connection_path,
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

    def test_device_registration_is_shared_by_multiple_vaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_home = root / "device-data"
            listenkit = root / "ListenKit"
            _make_listenkit(listenkit)

            preview = register_listenkit_connection(None, listenkit, data_home=data_home)
            applied = register_listenkit_connection(None, listenkit, data_home=data_home, mode="apply")
            english = resolve_listenkit_connection(root / "English Vault", data_home=data_home)
            japanese = resolve_listenkit_connection(root / "Japanese Vault", data_home=data_home)

            self.assertTrue(preview.accepted, preview.to_dict())
            self.assertTrue(applied.accepted, applied.to_dict())
            self.assertEqual("device", applied.artifacts["connection_scope"])
            self.assertEqual("device", english.artifacts["connection_scope"])
            self.assertEqual("device", japanese.artifacts["connection_scope"])
            self.assertEqual(str(listenkit), english.artifacts["listenkit_root"])
            self.assertTrue(device_listenkit_connection_path(data_home=data_home).is_file())

    def test_registration_appends_same_device_candidate_without_removing_old_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_home = root / "device-data"
            first = root / "listenkit-one"
            second = root / "listenkit-two"
            _make_listenkit(first)
            _make_listenkit(second)

            register_listenkit_connection(None, first, data_home=data_home, mode="apply")
            register_listenkit_connection(None, second, data_home=data_home, mode="apply")

            content = json.loads(
                device_listenkit_connection_path(data_home=data_home).read_text(encoding="utf-8")
            )
            self.assertEqual(
                [str(first), str(second)],
                [entry["listenkit_root"] for entry in content["connections"]],
            )

    def test_explicit_path_precedes_vault_override_and_device_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            data_home = root / "device-data"
            explicit = root / "explicit"
            override = root / "override"
            default = root / "default"
            for candidate in (explicit, override, default):
                _make_listenkit(candidate)
            register_listenkit_connection(None, default, data_home=data_home, mode="apply")
            register_listenkit_connection(vault, override, scope="vault", mode="apply")

            report = resolve_listenkit_connection(
                vault,
                listenkit_root=explicit,
                data_home=data_home,
            )

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("explicit", report.artifacts["connection_scope"])
        self.assertEqual(str(explicit), report.artifacts["listenkit_root"])

    def test_vault_override_precedes_device_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            data_home = root / "device-data"
            override = root / "override"
            default = root / "default"
            _make_listenkit(override)
            _make_listenkit(default)
            register_listenkit_connection(None, default, data_home=data_home, mode="apply")
            register_listenkit_connection(vault, override, scope="vault", mode="apply")

            report = resolve_listenkit_connection(vault, data_home=data_home)

        self.assertEqual("vault", report.artifacts["connection_scope"])
        self.assertEqual(str(override), report.artifacts["listenkit_root"])

    def test_resolution_skips_stale_vault_override_and_uses_device_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            data_home = root / "device-data"
            usable = root / "ListenKit"
            _make_listenkit(usable)
            register_listenkit_connection(None, usable, data_home=data_home, mode="apply")
            override_path = vault / listenkit_connection_relative_path()
            override_path.parent.mkdir(parents=True)
            override_path.write_text(
                json.dumps(
                    {
                        "listenkit_connection_schema_version": 1,
                        "platform": current_platform(),
                        "connections": [{"listenkit_root": str(root / "missing"), "source": "vault-override"}],
                    }
                ),
                encoding="utf-8",
            )

            report = resolve_listenkit_connection(vault, data_home=data_home)

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("device", report.artifacts["connection_scope"])
        self.assertEqual(str(usable), report.artifacts["listenkit_root"])

    def test_usable_runtime_sibling_is_the_final_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            runtime = root / "runtime"
            listenkit = root / "ListenKit"
            (runtime / "lingotrace" / "packs" / "english" / "agent_skills").mkdir(parents=True)
            (runtime / "lingotrace" / "__init__.py").write_text("", encoding="utf-8")
            (runtime / "lingotrace" / "packs" / "english" / "agent_skills" / "SKILL.md").write_text(
                "# English", encoding="utf-8"
            )
            initialize_english_vault(vault, runtime_root=runtime)
            _make_listenkit(listenkit)

            report = resolve_listenkit_connection(vault, data_home=root / "empty-device-data")

        self.assertTrue(report.accepted, report.to_dict())
        self.assertEqual("recommended", report.artifacts["connection_scope"])
        self.assertEqual(str(listenkit), report.artifacts["listenkit_root"])

    def test_missing_connection_offers_reinstall_or_select_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = resolve_listenkit_connection(root / "vault", data_home=root / "device-data")

        self.assertFalse(report.accepted)
        self.assertEqual("listenkit_connection_required", report.errors[0].code)
        options = {entry["id"] for entry in json.loads(report.artifacts["recovery_options"])}
        self.assertEqual({"reinstall", "select_existing"}, options)
        self.assertEqual(
            str(device_listenkit_connection_path(data_home=root / "device-data")),
            report.artifacts["device_connection_path"],
        )

    def test_invalid_checkout_is_rejected_before_device_connection_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / "not-listenkit"
            invalid.mkdir()

            report = register_listenkit_connection(
                None,
                invalid,
                data_home=root / "device-data",
                mode="apply",
            )

        self.assertFalse(report.accepted)
        self.assertEqual("listenkit_root_invalid", report.errors[0].code)

    def test_vault_override_requires_a_vault_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            listenkit = Path(tmp) / "ListenKit"
            _make_listenkit(listenkit)
            report = register_listenkit_connection(None, listenkit, scope="vault")

        self.assertFalse(report.accepted)
        self.assertEqual("vault_root_required_for_listenkit_override", report.errors[0].code)

    def test_listenkit_checkout_must_stay_outside_private_vault_when_vault_is_known(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            listenkit = vault / "tools" / "ListenKit"
            _make_listenkit(listenkit)

            report = register_listenkit_connection(vault, listenkit, data_home=Path(tmp) / "device-data")

        self.assertFalse(report.accepted)
        self.assertIn("vault_listenkit_overlap", {finding.code for finding in report.errors})


def _make_listenkit(root: Path) -> None:
    (root / "cli").mkdir(parents=True)
    (root / "README.md").write_text("# ListenKit\n", encoding="utf-8")
    (root / "cli" / "generate-markdown.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
