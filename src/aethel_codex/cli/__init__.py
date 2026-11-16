"""Command line interface for aethel (cli-spec.md §1, §2)."""

import json
import sys
import traceback

from aethel_codex.cli.parser import build_parser
from aethel_codex.cli.ui import UIContext, UsageError
from aethel_codex.errors import AethelError, InternalError, KeyFileError

CRYPTO_ERROR_CODES = {
    "KEYFILE_INVALID",
    "KEYFILE_PERMISSIONS",
    "KEYFILE_PASSPHRASE",
    "BACKEND_ERROR",
}

IO_ERROR_CODES = {
    "TEXT_MISSING",
    "MANIFEST_MISSING",
    "ASSET_MISSING",
    "UNSAFE_PATH",
    "ID_MISMATCH",
}


def _map_exception_to_exit(exc: Exception) -> tuple[int, str, str, str | None]:
    """Map python exception to (exit_code, error_code, message, yp_section)."""
    if isinstance(exc, KeyboardInterrupt):
        return 130, "INTERRUPTED", "Operation interrupted by user", None

    if isinstance(exc, UsageError):
        return 2, "USAGE", exc.message, None

    if isinstance(exc, InternalError):
        return 70, exc.code, exc.message, exc.yp_section

    if isinstance(exc, KeyFileError):
        return 4, exc.code, exc.message, exc.yp_section

    if isinstance(exc, AethelError):
        code = exc.code
        msg = exc.message or str(exc)
        yp = exc.yp_section

        if code == "UNICODE_DATA_MISMATCH":
            return 70, code, msg, yp
        if code in CRYPTO_ERROR_CODES:
            return 4, code, msg, yp
        if code in IO_ERROR_CODES:
            return 5, code, msg, yp
        return 3, code, msg, yp

    if isinstance(exc, OSError):
        return 5, "IO_ERROR", str(exc), None

    return 70, "INTERNAL", str(exc), None


def _dispatch_command(args: object, ui: UIContext) -> int:
    """Dispatch parsed args to the appropriate command handler."""
    cmd = getattr(args, "command", None)
    if cmd == "canon":
        from aethel_codex.cli.cmd_canon import handle_canon

        return handle_canon(args, ui)  # type: ignore[arg-type]
    if cmd == "id":
        from aethel_codex.cli.cmd_id import handle_id

        return handle_id(args, ui)  # type: ignore[arg-type]
    if cmd == "keygen":
        from aethel_codex.cli.cmd_keygen import handle_keygen

        return handle_keygen(args, ui)  # type: ignore[arg-type]
    if cmd == "key":
        if getattr(args, "key_command", None) == "info":
            from aethel_codex.cli.cmd_keygen import handle_key_info

            return handle_key_info(args, ui)  # type: ignore[arg-type]
        return 2
    if cmd == "publish":
        from aethel_codex.cli.cmd_publish import handle_publish

        return handle_publish(args, ui)  # type: ignore[arg-type]
    if cmd == "sign":
        from aethel_codex.cli.cmd_sign import handle_sign

        return handle_sign(args, ui)  # type: ignore[arg-type]
    if cmd == "verify":
        from aethel_codex.cli.cmd_verify import handle_verify

        return handle_verify(args, ui)  # type: ignore[arg-type]
    if cmd == "inspect":
        from aethel_codex.cli.cmd_inspect import handle_inspect

        return handle_inspect(args, ui)  # type: ignore[arg-type]

    sys.stderr.write(f"Unknown command: {cmd}\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for aethel."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    if not argv:
        parser.print_usage(sys.stderr)
        return 2

    # Check for unrecognized command / argparse parse errors
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    if not args.command:
        parser.print_usage(sys.stderr)
        return 2

    ui = UIContext(
        json_mode=getattr(args, "json", False),
        quiet=getattr(args, "quiet", False),
        verbose=getattr(args, "verbose", False),
        no_color=getattr(args, "no_color", False),
        ascii_mode=getattr(args, "ascii_mode", False),
        debug=getattr(args, "debug", False),
    )

    try:
        return _dispatch_command(args, ui)
    except Exception as exc:  # noqa: BLE001
        exit_code, code, msg, yp = _map_exception_to_exit(exc)
        if ui.json_mode:
            err_doc = {
                "schema": "aethel.error/1",
                "code": code,
                "message": msg,
                "exit": exit_code,
                "yp": yp,
            }
            sys.stdout.write(json.dumps(err_doc, indent=2) + "\n")
        else:
            sys.stderr.write(f"error: {msg}\n")
            if code and code not in ("IO_ERROR", "INTERNAL"):
                dot = ui.dot()
                line = f"       code {code} {dot} run `aethel explain {code}` for more.\n"
                sys.stderr.write(line)
            if ui.debug:
                traceback.print_exc(file=sys.stderr)
        return exit_code


__all__ = ["main"]
