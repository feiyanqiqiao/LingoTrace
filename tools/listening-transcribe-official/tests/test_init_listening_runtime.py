import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "init_listening_runtime.py"
SPEC = importlib.util.spec_from_file_location("init_listening_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def runtime_info(executable: str, *, in_venv: bool) -> dict[str, object]:
    return {
        "executable": executable,
        "version": "3.14.4",
        "major": 3,
        "minor": 14,
        "prefix": str(Path(executable).parent),
        "base_prefix": "/opt/python",
        "in_venv": in_venv,
    }


class InitListeningRuntimeTests(unittest.TestCase):
    def test_default_runtime_paths_are_platform_native(self) -> None:
        macos = MODULE.default_runtime_dir(platform_name="macos", home="/Users/test", environ={})
        linux = MODULE.default_runtime_dir(
            platform_name="linux",
            home="/home/test",
            environ={"XDG_CACHE_HOME": "/cache"},
        )
        windows = MODULE.default_runtime_dir(
            platform_name="windows",
            home="C:/Users/test",
            environ={"LOCALAPPDATA": "C:/Users/test/AppData/Local"},
        )

        self.assertEqual(macos, Path("/Users/test/Library/Caches/LingoTrace/venvs/cpython-314"))
        self.assertEqual(linux, Path("/cache/lingotrace/venvs/cpython-314"))
        self.assertTrue(windows.as_posix().endswith("LingoTrace/venvs/cpython-314"))
        self.assertEqual(
            MODULE.runtime_python_path(Path("C:/runtime"), "windows").as_posix(),
            "C:/runtime/Scripts/python.exe",
        )
        self.assertEqual(MODULE.runtime_python_path(Path("/runtime"), "macos"), Path("/runtime/bin/python"))

    def test_child_environment_removes_host_python_pollution(self) -> None:
        environment = MODULE.clean_python_subprocess_environment(
            {"PYTHONHOME": "/broken", "PYTHONPATH": "/also-broken", "KEEP": "yes"}
        )

        self.assertNotIn("PYTHONHOME", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertEqual(environment["PYTHONUTF8"], "1")
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(environment["KEEP"], "yes")

    def test_dry_run_reports_create_install_and_check_commands_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = (Path(tmpdir) / "runtime").resolve()
            bootstrap = runtime_info("/opt/python3.14", in_venv=False)
            with mock.patch.object(MODULE, "python_runtime_info", return_value=bootstrap):
                with mock.patch.object(MODULE, "run_command") as run_mock:
                    exit_code = MODULE.initialize_or_check_runtime(
                        bootstrap_python="/opt/python3.14",
                        runtime_dir=runtime_dir,
                        platform_name="macos",
                        action="dry-run",
                    )

            self.assertEqual(exit_code, 0)
            self.assertFalse(runtime_dir.exists())
            run_mock.assert_not_called()

    def test_install_creates_new_venv_then_delegates_to_public_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = (Path(tmpdir) / "runtime").resolve()
            runtime_python = runtime_dir / "bin" / "python"
            bootstrap = runtime_info("/opt/python3.14", in_venv=False)
            installed = runtime_info(str(runtime_python), in_venv=True)
            commands: list[list[str]] = []

            def fake_run(command: list[str]) -> int:
                commands.append(command)
                if command[1:3] == ["-m", "venv"]:
                    runtime_python.parent.mkdir(parents=True)
                    runtime_python.write_text("python", encoding="utf-8")
                return 0

            with mock.patch.object(MODULE, "python_runtime_info", side_effect=[bootstrap, installed]):
                with mock.patch.object(MODULE, "run_command", side_effect=fake_run):
                    exit_code = MODULE.initialize_or_check_runtime(
                        bootstrap_python="/opt/python3.14",
                        runtime_dir=runtime_dir,
                        platform_name="macos",
                        action="install",
                    )

            self.assertEqual(exit_code, 0)
            self.assertEqual(commands[0], ["/opt/python3.14", "-m", "venv", str(runtime_dir)])
            self.assertEqual(commands[1], MODULE.setup_command(runtime_python, "--install"))

    def test_check_reuses_existing_runtime_without_creating_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = (Path(tmpdir) / "runtime").resolve()
            runtime_python = runtime_dir / "bin" / "python"
            runtime_python.parent.mkdir(parents=True)
            runtime_python.write_text("python", encoding="utf-8")
            bootstrap = runtime_info("/opt/python3.14", in_venv=False)
            installed = runtime_info(str(runtime_python), in_venv=True)
            with mock.patch.object(MODULE, "python_runtime_info", side_effect=[bootstrap, installed]):
                with mock.patch.object(MODULE, "run_command", return_value=0) as run_mock:
                    exit_code = MODULE.initialize_or_check_runtime(
                        bootstrap_python="/opt/python3.14",
                        runtime_dir=runtime_dir,
                        platform_name="macos",
                        action="check",
                    )

            self.assertEqual(exit_code, 0)
            run_mock.assert_called_once_with(MODULE.setup_command(runtime_python, "--check"))

    def test_rejects_wrong_bootstrap_version_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir) / "runtime"
            bootstrap = runtime_info("/usr/bin/python3", in_venv=False)
            bootstrap.update({"version": "3.9.6", "major": 3, "minor": 9})
            with mock.patch.object(MODULE, "python_runtime_info", return_value=bootstrap):
                with mock.patch.object(MODULE, "run_command") as run_mock:
                    with self.assertRaisesRegex(RuntimeError, "must be Python 3.14"):
                        MODULE.initialize_or_check_runtime(
                            bootstrap_python="/usr/bin/python3",
                            runtime_dir=runtime_dir,
                            platform_name="macos",
                            action="install",
                        )

            self.assertFalse(runtime_dir.exists())
            run_mock.assert_not_called()

    def test_rejects_synchronized_and_unknown_nonempty_targets(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outside iCloud/OneDrive"):
            MODULE.initialize_or_check_runtime(
                bootstrap_python="/opt/python3.14",
                runtime_dir=Path("/Users/test/Library/Mobile Documents/LingoTrace/runtime"),
                platform_name="macos",
                action="install",
            )
        self.assertTrue(
            MODULE.is_synchronized_runtime_path(
                Path("C:/Users/test/OneDrive/LingoTrace/runtime"),
                environ={"OneDrive": "C:/Users/test/OneDrive"},
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir) / "runtime"
            runtime_dir.mkdir()
            (runtime_dir / "unknown.txt").write_text("keep", encoding="utf-8")
            bootstrap = runtime_info("/opt/python3.14", in_venv=False)
            with mock.patch.object(MODULE, "python_runtime_info", return_value=bootstrap):
                with self.assertRaisesRegex(RuntimeError, "non-empty directory"):
                    MODULE.initialize_or_check_runtime(
                        bootstrap_python="/opt/python3.14",
                        runtime_dir=runtime_dir,
                        platform_name="macos",
                        action="install",
                    )


if __name__ == "__main__":
    unittest.main()
