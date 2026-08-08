from __future__ import annotations

import argparse
import json
from pathlib import Path

from lingotrace.init.english_vault import initialize_english_vault, plan_english_vault_initialization
from lingotrace.init.japanese_vault import initialize_japanese_vault, plan_japanese_vault_initialization
from lingotrace.init.runtime_connections import register_runtime_connection, resolve_runtime_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a LingoTrace Vault or manage its runtime connection.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("vault", help="Preview or initialize a Japanese or English Vault.")
    initialize.add_argument("--language", choices=("english", "japanese"), required=True)
    initialize.add_argument("--vault", type=Path, required=True)
    initialize.add_argument("--runtime-root", type=Path)
    initialize.add_argument("--apply", action="store_true")

    connect = subparsers.add_parser("connect-runtime", help="Append a runtime path for the current platform.")
    connect.add_argument("--vault", type=Path, required=True)
    connect.add_argument("--runtime-root", type=Path, required=True)
    connect.add_argument("--apply", action="store_true")

    resolve = subparsers.add_parser("resolve-runtime", help="Resolve a usable runtime for the current platform.")
    resolve.add_argument("--vault", type=Path, required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "vault":
        if args.language == "english":
            function = initialize_english_vault if args.apply else plan_english_vault_initialization
        else:
            function = initialize_japanese_vault if args.apply else plan_japanese_vault_initialization
        report = function(args.vault, runtime_root=args.runtime_root)
    elif args.command == "connect-runtime":
        report = register_runtime_connection(
            args.vault,
            args.runtime_root,
            mode="apply" if args.apply else "preview",
        )
    else:
        report = resolve_runtime_connection(args.vault)

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
