"""CLI handler for aethel cite make|check|show (cli-spec.md §3, specs.md §6)."""

import argparse
import json
import re
import sys
from pathlib import Path

from aethel_codex.citations import Citation, parse_citation, validate_citation_range
from aethel_codex.cli.sanitize import sanitize_terminal
from aethel_codex.cli.ui import UIContext, UsageError
from aethel_codex.constants import LABEL_ASSET, LABEL_MANIFEST, LABEL_TEXT
from aethel_codex.errors import AethelError, CitationError
from aethel_codex.hashing import H
from aethel_codex.merkle import blob_id
from aethel_codex.pid import Pid

RANGE_RE = re.compile(r"^(0|[1-9][0-9]*)-(0|[1-9][0-9]*)$")


def _find_manifest_blob(bundle_dir: Path, target_pid: Pid) -> bytes:
    m_file = bundle_dir / "manifest.pip"
    if not m_file.exists():
        raise AethelError("MANIFEST_MISSING", f"manifest.pip not found in {bundle_dir}")
    data = m_file.read_bytes()
    actual_digest = H(LABEL_MANIFEST, data)
    if actual_digest != target_pid.digest:
        raise AethelError(
            "ID_MISMATCH",
            f"Manifest in {bundle_dir} does not match cited PID {target_pid}",
        )
    return data


def _find_text_blob(bundle_dir: Path, target_pid: Pid) -> bytes:
    text_files = list(bundle_dir.glob("text.*"))
    if not text_files:
        raise AethelError("TEXT_MISSING", f"Manuscript text file not found in {bundle_dir}")
    for t_file in text_files:
        if t_file.is_file():
            data = t_file.read_bytes()
            actual_digest = blob_id(LABEL_TEXT, data)
            if actual_digest == target_pid.digest:
                return data
    raise AethelError(
        "TEXT_MISMATCH",
        f"No manuscript text in {bundle_dir} matches cited PID {target_pid}",
    )


def _find_asset_blob(bundle_dir: Path, target_pid: Pid) -> bytes:
    assets_dir = bundle_dir / "assets"
    if assets_dir.is_dir():
        for a_file in assets_dir.iterdir():
            if a_file.is_file():
                data = a_file.read_bytes()
                actual_digest = blob_id(LABEL_ASSET, data)
                if actual_digest == target_pid.digest:
                    return data
    raise AethelError(
        "ASSET_MISSING",
        f"No asset in {bundle_dir}/assets matches cited PID {target_pid}",
    )


def _find_target_blob_in_bundle(bundle_dir: Path, target_pid: Pid) -> bytes:
    """Locate and return the target blob bytes matching target_pid in bundle."""
    if not bundle_dir.is_dir():
        raise AethelError("IO", f"Bundle directory not found: {bundle_dir}")

    if target_pid.pid_type == "m":
        return _find_manifest_blob(bundle_dir, target_pid)
    if target_pid.pid_type == "t":
        return _find_text_blob(bundle_dir, target_pid)
    if target_pid.pid_type == "a":
        return _find_asset_blob(bundle_dir, target_pid)

    raise AethelError("PID_SYNTAX", f"Cannot locate cited PID of type {target_pid.pid_type}")


def _handle_cite_make(args: argparse.Namespace, ui: UIContext) -> int:
    pid_str = getattr(args, "target_pid", None)
    if not pid_str:
        raise UsageError("Provide a target PID to cite")

    pid = Pid.parse(pid_str)
    if pid.pid_type == "k":
        raise CitationError("CITE_SYNTAX", "Key identifiers (type 'k') are not citable")

    range_str = getattr(args, "range", None)
    locator: tuple[int, int] | None = None
    if range_str:
        match = RANGE_RE.fullmatch(range_str)
        if not match:
            raise CitationError("CITE_SYNTAX", f"Malformed range specification: {range_str!r}")
        start, end = int(match.group(1)), int(match.group(2))
        if start >= end:
            raise CitationError("CITE_SYNTAX", f"Range start {start} >= end {end}")
        locator = (start, end)

    citation = Citation(target=pid, locator=locator)
    uri = str(citation)

    if ui.json_mode:
        doc = {
            "schema": "aethel.cite.make/1",
            "uri": uri,
            "target": str(pid),
            "locator": list(locator) if locator else None,
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        sys.stdout.write(f"{uri}\n")

    return 0


def _handle_cite_check(args: argparse.Namespace, ui: UIContext) -> int:
    uri_str = getattr(args, "uri", None)
    if not uri_str:
        raise UsageError("Provide a citation URI to check")

    citation = parse_citation(uri_str)

    bundle_arg = getattr(args, "bundle", None)
    file_arg = getattr(args, "file", None)
    if not bundle_arg and not file_arg:
        raise UsageError("Either --bundle or --file is required for `aethel cite check`")

    if file_arg:
        f_path = Path(str(file_arg))
        if not f_path.exists():
            raise AethelError("IO", f"File not found: {f_path}")
        blob = f_path.read_bytes()
    else:
        blob = _find_target_blob_in_bundle(Path(str(bundle_arg)), citation.target)

    validate_citation_range(citation, blob)

    if ui.json_mode:
        doc = {
            "schema": "aethel.cite.check/1",
            "valid": True,
            "uri": str(citation),
            "target": str(citation.target),
            "blob_length": len(blob),
            "locator": list(citation.locator) if citation.locator else None,
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        loc_str = f" range {citation.locator[0]}-{citation.locator[1]}" if citation.locator else ""
        sys.stdout.write(
            f"Citation locator valid for {citation.target}{loc_str} ({len(blob):,} bytes)\n"
        )

    return 0


def _handle_cite_show(args: argparse.Namespace, ui: UIContext) -> int:
    uri_str = getattr(args, "uri", None)
    if not uri_str:
        raise UsageError("Provide a citation URI to show")

    citation = parse_citation(uri_str)
    bundle_arg = getattr(args, "bundle", None)
    if not bundle_arg:
        raise UsageError("--bundle DIR is required for `aethel cite show`")

    blob = _find_target_blob_in_bundle(Path(str(bundle_arg)), citation.target)
    validate_citation_range(citation, blob)

    sliced = blob[citation.locator[0] : citation.locator[1]] if citation.locator else blob

    if sys.stdout.isatty():
        try:
            text = sliced.decode("utf-8")
            clean_text = sanitize_terminal(text)
            sys.stdout.write(clean_text)
            if not clean_text.endswith("\n"):
                sys.stdout.write("\n")
        except UnicodeDecodeError:
            sys.stdout.buffer.write(sliced)
    else:
        sys.stdout.buffer.write(sliced)

    return 0


def handle_cite(args: argparse.Namespace, ui: UIContext) -> int:
    """Dispatch cite subcommands."""
    cite_cmd = getattr(args, "cite_command", None)
    if cite_cmd == "make":
        return _handle_cite_make(args, ui)
    if cite_cmd == "check":
        return _handle_cite_check(args, ui)
    if cite_cmd == "show":
        return _handle_cite_show(args, ui)

    raise UsageError("Expected cite subcommand: make, check, or show")
