"""CLI handler for aethel id (cli-spec.md §3)."""

import argparse
import json
import sys
from pathlib import Path

from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import CHUNK_SIZE, TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION
from aethel_codex.ctf1 import canonicalize
from aethel_codex.errors import AethelError
from aethel_codex.merkle import asset_id, text_id

TEXT_EXTENSIONS = {".md", ".markdown", ".tex", ".txt"}


def handle_id(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute id command."""
    is_stdin = args.file == "-"
    if is_stdin:
        if not args.kind:
            raise AethelError(
                "E_BAD_VALUE", "--kind text|asset is required when reading from standard input"
            )
        raw_bytes = sys.stdin.buffer.read()
        file_name = None
        kind = args.kind
    else:
        path = Path(args.file)
        try:
            raw_bytes = path.read_bytes()
        except OSError as e:
            raise AethelError("TEXT_MISSING", f"Cannot read input file {path}: {e}") from None
        file_name = str(path)
        is_text_ext = path.suffix.lower() in TEXT_EXTENSIONS
        kind = args.kind or ("text" if is_text_ext else "asset")

    if kind == "text":
        canon_bytes, _ = canonicalize(raw_bytes)
        identifier = text_id(canon_bytes)
        length = len(canon_bytes)
    else:
        identifier = asset_id(raw_bytes)
        length = len(raw_bytes)

    chunks = (length + CHUNK_SIZE - 1) // CHUNK_SIZE if length > 0 else 1

    if ui.json_mode:
        doc = {
            "schema": "aethel.id/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "file": file_name,
            "kind": kind,
            "id": identifier,
            "length": length,
            "chunks": chunks,
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        if ui.verbose:
            chunk_suffix = "chunk" if chunks == 1 else "chunks"
            sys.stdout.write(f"{identifier}   {length:,} bytes, {chunks} {chunk_suffix}\n")
        else:
            sys.stdout.write(f"{identifier}\n")

    return 0
