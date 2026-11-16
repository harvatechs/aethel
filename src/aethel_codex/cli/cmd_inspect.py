"""CLI handler for aethel inspect (cli-spec.md §3)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aethel_codex.cli.sanitize import sanitize_terminal
from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import LABEL_MANIFEST, TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION
from aethel_codex.errors import AethelError
from aethel_codex.hashing import H
from aethel_codex.manifest import Manifest, parse_manifest


def _format_manifest_dict(manifest: Manifest) -> dict[str, Any]:
    """Convert parsed manifest into dictionary matching aethel.inspect/1 schema."""
    return {
        "profile": manifest.profile,
        "markup": manifest.markup,
        "lang": manifest.lang,
        "title": manifest.title,
        "license": manifest.license,
        "text": {
            "pid": str(manifest.text_pid),
            "length": manifest.text_length,
        },
        "work": str(manifest.work_pid) if manifest.work_pid else None,
        "beacon": (
            {
                "source": manifest.beacon.source,
                "sequence": manifest.beacon.sequence,
                "value": manifest.beacon.value.hex(),
            }
            if manifest.beacon
            else None
        ),
        "parents": [str(p) for p in manifest.parents],
        "authors": [str(a) for a in manifest.authors],
        "derivatives": [{"kind": d.kind, "target": str(d.target)} for d in manifest.derivatives],
        "assets": [
            {
                "name": a.name,
                "pid": str(a.pid),
                "length": a.length,
                "media_type": a.media_type,
            }
            for a in manifest.assets
        ],
        "cites": [str(c) for c in manifest.cites],
    }


def _print_inspect_human(m_pid: str, manifest: Manifest) -> None:
    """Print human-readable manifest fields (cli-spec.md §3)."""
    sys.stdout.write("inspect parses a manifest. It does not verify anything.\n")
    sys.stdout.write(f"Manifest ID:  {m_pid}\n")
    sys.stdout.write(f"Profile:      {manifest.profile}\n")
    sys.stdout.write(f"Markup:       {manifest.markup}\n")
    sys.stdout.write(f"Language:     {manifest.lang}\n")
    sys.stdout.write(f"Title:        {sanitize_terminal(manifest.title)}\n")
    sys.stdout.write(f"License:      {sanitize_terminal(manifest.license)}\n")
    sys.stdout.write(f"Text:         {manifest.text_pid} ({manifest.text_length:,} bytes)\n")
    if manifest.work_pid:
        sys.stdout.write(f"Work:         {manifest.work_pid}\n")
    if manifest.beacon:
        sys.stdout.write(
            f"Beacon:       {manifest.beacon.source} #{manifest.beacon.sequence} "
            f"{manifest.beacon.value.hex()}\n"
        )
    for p in manifest.parents:
        sys.stdout.write(f"Parent:       {p}\n")
    for a in manifest.authors:
        sys.stdout.write(f"Author:       {a}\n")
    for d in manifest.derivatives:
        sys.stdout.write(f"Derivative:   {d.kind} {d.target}\n")
    for a_entry in manifest.assets:
        clean_name = sanitize_terminal(a_entry.name)
        line = (
            f"Asset:        {clean_name} -> {a_entry.pid} "
            f"({a_entry.length:,} bytes, {a_entry.media_type})\n"
        )
        sys.stdout.write(line)
    for c in manifest.cites:
        sys.stdout.write(f"Cite:         {c}\n")


def handle_inspect(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute inspect command."""
    target = Path(args.target).resolve()
    manifest_file = target / "manifest.pip" if target.is_dir() else target

    try:
        manifest_bytes = manifest_file.read_bytes()
    except OSError as e:
        msg = f"Cannot read manifest file {manifest_file}: {e}"
        raise AethelError("MANIFEST_MISSING", msg) from None

    manifest = parse_manifest(manifest_bytes)
    m_digest = H(LABEL_MANIFEST, manifest_bytes)
    m_pid = f"pip1:m:{m_digest.hex()}"

    if ui.json_mode:
        doc = {
            "schema": "aethel.inspect/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "manifest_id": m_pid,
            "manifest": _format_manifest_dict(manifest),
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        _print_inspect_human(m_pid, manifest)

    return 0
