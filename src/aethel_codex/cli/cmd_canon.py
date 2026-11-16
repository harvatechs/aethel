"""CLI handler for aethel canon (cli-spec.md §3)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION
from aethel_codex.ctf1 import CanonReport, canonicalize
from aethel_codex.errors import AethelError


def _print_canon_report(report: CanonReport, in_len: int, out_len: int) -> None:
    """Print human-readable explanation of CTF-1 modifications."""
    sys.stderr.write(f"Canonical form: {out_len:,} bytes (input {in_len:,}).\n")
    if report.bom_removed:
        sys.stderr.write("  removed the byte-order mark\n")
    if report.crlf_converted > 0:
        sys.stderr.write(f"  converted {report.crlf_converted} CR LF line endings to LF\n")
    if report.lone_cr_converted > 0:
        sys.stderr.write(f"  converted {report.lone_cr_converted} lone CR line endings to LF\n")
    if report.nfc_changed:
        sys.stderr.write("  normalized to Unicode 18.0.0 NFC\n")
    if report.final_lf_added:
        sys.stderr.write("  added a final line feed\n")


def _build_canon_json(
    is_canonical: bool, in_len: int, out_len: int, report: CanonReport
) -> dict[str, Any]:
    """Build JSON document matching aethel.canon/1 schema."""
    return {
        "schema": "aethel.canon/1",
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "profile": "pip-1",
            "yellow_paper": YELLOW_PAPER_VERSION,
        },
        "canonical": is_canonical,
        "input_bytes": in_len,
        "output_bytes": out_len,
        "changes": {
            "bom_removed": report.bom_removed,
            "crlf_converted": report.crlf_converted,
            "lone_cr_converted": report.lone_cr_converted,
            "nfc_changed": report.nfc_changed,
            "final_lf_added": report.final_lf_added,
        },
    }


def handle_canon(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute canon command."""
    if args.file == "-":
        raw_bytes = sys.stdin.buffer.read()
    else:
        path = Path(args.file)
        try:
            raw_bytes = path.read_bytes()
        except OSError as e:
            raise AethelError("TEXT_MISSING", f"Cannot read input file {path}: {e}") from None

    canon_bytes, report = canonicalize(raw_bytes)
    is_canonical = (
        len(raw_bytes) == len(canon_bytes)
        and not report.bom_removed
        and report.crlf_converted == 0
        and report.lone_cr_converted == 0
        and not report.nfc_changed
        and not report.final_lf_added
    )

    if args.check:
        return 0 if is_canonical else 1

    if args.report and not ui.quiet:
        _print_canon_report(report, len(raw_bytes), len(canon_bytes))

    if args.out:
        out_path = Path(args.out)
        try:
            out_path.write_bytes(canon_bytes)
        except OSError as e:
            msg = f"Cannot write to output file {out_path}: {e}"
            raise AethelError("TEXT_MISSING", msg) from None

    if ui.json_mode:
        doc = _build_canon_json(is_canonical, len(raw_bytes), len(canon_bytes), report)
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    elif not args.out:
        sys.stdout.buffer.write(canon_bytes)

    return 0
