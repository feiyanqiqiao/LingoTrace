from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lingotrace.core.json_output import emit_json
from lingotrace.init.doctor import inspect_onboarding
from lingotrace.init.english_vault import initialize_english_vault, plan_english_vault_initialization
from lingotrace.init.japanese_vault import initialize_japanese_vault, plan_japanese_vault_initialization
from lingotrace.init.listenkit_connections import register_listenkit_connection, resolve_listenkit_connection
from lingotrace.init.runtime_connections import register_runtime_connection, resolve_runtime_connection
from lingotrace.init.runtime_updates import apply_runtime_update, check_runtime_update
from lingotrace.init.vault_upgrade import upgrade_vault


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a LingoTrace Vault or manage its runtime connection.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("vault", help="Preview or initialize a Japanese or English Vault.")
    initialize.add_argument("--language", choices=("english", "japanese"), required=True)
    initialize.add_argument("--vault", type=Path, required=True)
    initialize.add_argument("--runtime-root", type=Path)
    initialize.add_argument("--apply", action="store_true")

    upgrade = subparsers.add_parser("upgrade-vault", help="Preview or apply safe pack artifact upgrades to an existing Vault.")
    upgrade.add_argument("--vault", type=Path, required=True)
    upgrade.add_argument("--apply", action="store_true")

    connect = subparsers.add_parser("connect-runtime", help="Append a runtime path for the current platform.")
    connect.add_argument("--vault", type=Path, required=True)
    connect.add_argument("--runtime-root", type=Path, required=True)
    connect.add_argument("--apply", action="store_true")

    resolve = subparsers.add_parser("resolve-runtime", help="Resolve a usable runtime for the current platform.")
    resolve.add_argument("--vault", type=Path, required=True)

    connect_listenkit = subparsers.add_parser(
        "connect-listenkit", help="Save a shared device ListenKit path or an explicit Vault override."
    )
    connect_listenkit.add_argument("--vault", type=Path, help="Required only for --scope vault.")
    connect_listenkit.add_argument("--listenkit-root", type=Path, required=True)
    connect_listenkit.add_argument(
        "--scope",
        choices=("device", "vault"),
        default="device",
        help="Save the cross-language device default unless a Vault-specific override is required.",
    )
    connect_listenkit.add_argument("--apply", action="store_true")

    resolve_listenkit = subparsers.add_parser(
        "resolve-listenkit", help="Resolve a usable ListenKit installation for the current platform."
    )
    resolve_listenkit.add_argument("--vault", type=Path, required=True)
    resolve_listenkit.add_argument(
        "--listenkit-root",
        type=Path,
        help="Validate and use this path for the current resolution only; do not save it.",
    )

    doctor = subparsers.add_parser("doctor", help="Inspect learner onboarding prerequisites without changing them.")
    doctor.add_argument("--language", choices=("english", "japanese"), required=True)
    doctor.add_argument("--vault", type=Path, required=True)
    doctor.add_argument("--runtime-root", type=Path, required=True)
    doctor.add_argument("--listenkit-root", type=Path)

    check_update = subparsers.add_parser("check-update", help="Check official upstream once per local day.")
    check_update.add_argument("--vault", type=Path, required=True)
    check_update.add_argument("--runtime-root", type=Path, required=True)
    check_update.add_argument("--force", action="store_true")

    apply_update = subparsers.add_parser("apply-update", help="Preview or apply a safe official runtime update.")
    apply_update.add_argument("--vault", type=Path, required=True)
    apply_update.add_argument("--runtime-root", type=Path, required=True)
    apply_update.add_argument("--apply", action="store_true")

    for command_parser in (
        initialize,
        upgrade,
        connect,
        resolve,
        connect_listenkit,
        resolve_listenkit,
        doctor,
        check_update,
        apply_update,
    ):
        command_parser.add_argument(
            "--report-json",
            type=Path,
            help="Also atomically write the UTF-8 JSON report to this path.",
        )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "vault":
        if args.language == "english":
            function = initialize_english_vault if args.apply else plan_english_vault_initialization
        else:
            function = initialize_japanese_vault if args.apply else plan_japanese_vault_initialization
        report = function(
            args.vault,
            runtime_root=args.runtime_root,
        )
    elif args.command == "upgrade-vault":
        report = upgrade_vault(args.vault, mode="apply" if args.apply else "preview")
    elif args.command == "connect-runtime":
        report = register_runtime_connection(
            args.vault,
            args.runtime_root,
            mode="apply" if args.apply else "preview",
        )
    elif args.command == "resolve-runtime":
        report = resolve_runtime_connection(args.vault)
    elif args.command == "connect-listenkit":
        report = register_listenkit_connection(
            args.vault,
            args.listenkit_root,
            scope=args.scope,
            mode="apply" if args.apply else "preview",
        )
    elif args.command == "resolve-listenkit":
        report = resolve_listenkit_connection(args.vault, listenkit_root=args.listenkit_root)
    elif args.command == "doctor":
        report = inspect_onboarding(
            language=args.language,
            vault_root=args.vault,
            runtime_root=args.runtime_root,
            listenkit_root=args.listenkit_root,
        )
    elif args.command == "check-update":
        report = check_runtime_update(
            args.vault,
            args.runtime_root,
            force=args.force,
        )
    else:
        report = apply_runtime_update(
            args.vault,
            args.runtime_root,
            mode="apply" if args.apply else "preview",
        )

    try:
        emit_json(report.to_dict(), report_json=args.report_json)
    except OSError as exc:
        print(f"Unable to write JSON report: {exc}", file=sys.stderr)
        return 1
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
