from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from lingotrace.core.json_output import emit_json
from lingotrace.core.reports import CommandReport, Finding


CAPABILITY_FIELDS = {
    "listening_notes": {"input_artifact"},
    "source_notes": {"source_artifact"},
    "review_materials": {
        "card",
        "item",
        "daily_checklist",
        "extraction_date",
        "existing_update_confirmed",
    },
    "speaking_cards": {"candidate"},
    "review_rollover": {"run_date"},
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one guarded LingoTrace language-pack capability.")
    parser.add_argument("capability", choices=tuple(CAPABILITY_FIELDS))
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--payload", help="UTF-8 JSON object file, or '-' to read stdin. Defaults to an empty object.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args(argv)


def run_capability(
    capability: str,
    *,
    vault_root: str | Path,
    payload: dict[str, Any] | None = None,
    mode: str = "preview",
) -> CommandReport:
    if capability not in CAPABILITY_FIELDS:
        return _error_report(capability, mode, "unsupported_capability", f"Unsupported capability: {capability}")
    if mode not in {"preview", "apply"}:
        raise ValueError(f"unsupported_mode: {mode}")

    vault = Path(vault_root)
    context_path = vault / ".lingotrace" / "vault-context.json"
    try:
        context = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _error_report(
            capability,
            mode,
            "invalid_vault_context",
            f"Cannot read the initialized Vault context: {exc}",
            str(context_path),
        )

    pack_id = context.get("language_pack")
    workflows = _workflows_for_pack(pack_id)
    if workflows is None:
        return _error_report(
            capability,
            mode,
            "unsupported_language_pack",
            f"Unsupported language_pack in Vault context: {pack_id!r}",
            str(context_path),
        )

    values = dict(payload or {})
    reserved = sorted(set(values) & {"vault_root", "mode"})
    unsupported = sorted(set(values) - CAPABILITY_FIELDS[capability])
    if reserved or unsupported:
        fields = reserved or unsupported
        code = "reserved_payload_field" if reserved else "unsupported_payload_field"
        return _error_report(
            capability,
            mode,
            code,
            f"Payload contains unsupported fields for {capability}: {', '.join(fields)}",
        )

    function: Callable[..., CommandReport] = getattr(workflows, capability)
    return function(vault_root=vault, mode=mode, **values)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = _load_payload(args.payload)
        report = run_capability(
            args.capability,
            vault_root=args.vault,
            payload=payload,
            mode="apply" if args.apply else "preview",
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = _error_report(
            args.capability,
            "apply" if args.apply else "preview",
            "invalid_payload_json",
            str(exc),
            args.payload,
        )
    try:
        emit_json(report.to_dict(), report_json=args.report_json)
    except OSError as exc:
        print(f"Unable to write JSON report: {exc}", file=sys.stderr)
        return 1
    return report.exit_code


def _load_payload(path: str | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Capability payload must be a JSON object.")
    return payload


def _workflows_for_pack(pack_id: object):
    if pack_id == "lingo-english":
        from lingotrace.packs.english import workflows

        return workflows
    if pack_id == "lingo-japanese":
        from lingotrace.packs.japanese import workflows

        return workflows
    return None


def _error_report(
    capability: str,
    mode: str,
    code: str,
    message: str,
    path: str | None = None,
) -> CommandReport:
    return CommandReport(
        command=f"{capability}-workflow",
        mode=mode,
        exit_code=1,
        errors=[Finding(code=code, message=message, path=path)],
    )


if __name__ == "__main__":
    raise SystemExit(main())
