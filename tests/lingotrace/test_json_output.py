from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class JsonOutputTests(unittest.TestCase):
    def test_explicit_stderr_stream_is_reconfigured_to_utf8(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp936"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "from lingotrace.core.json_output import emit_json; "
                    "emit_json({'message': '中文错误'}, stream=sys.stderr)"
                ),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
            env=environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"message": "中文错误"}, json.loads(result.stderr.decode("utf-8")))
        self.assertIn("中文错误".encode("utf-8"), result.stderr)


if __name__ == "__main__":
    unittest.main()
