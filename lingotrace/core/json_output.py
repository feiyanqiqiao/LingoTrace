from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO


def configure_utf8_stdio() -> None:
    """Use one predictable encoding for machine-readable CLI output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def render_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def emit_json(
    payload: Any,
    *,
    report_json: str | Path | None = None,
    stream: TextIO | None = None,
) -> None:
    configure_utf8_stdio()
    text = render_json(payload)
    if report_json is not None:
        _write_text_atomic(Path(report_json), text)
    if stream is None:
        stream = sys.stdout
    stream.write(text)
    stream.flush()


def _write_text_atomic(path: Path, text: str) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
