from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lingotrace.init.executables import find_executable


class ExecutableDiscoveryTests(unittest.TestCase):
    def test_windows_finds_stable_powershell_7_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            program_files = Path(tmp) / "Program Files"
            executable = program_files / "PowerShell" / "7" / "pwsh.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"launcher")

            resolved = find_executable(
                "pwsh",
                platform_name="windows",
                environ={"ProgramFiles": str(program_files)},
                which=lambda _: None,
            )

        self.assertEqual(str(executable), resolved)

    def test_windows_finds_winget_ffmpeg_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_app_data = Path(tmp) / "Local App Data"
            executable = local_app_data / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"launcher")

            resolved = find_executable(
                "ffmpeg",
                platform_name="windows",
                environ={"LOCALAPPDATA": str(local_app_data)},
                which=lambda _: None,
            )

        self.assertEqual(str(executable), resolved)


if __name__ == "__main__":
    unittest.main()
