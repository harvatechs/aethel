"""CLI handler for aethel proof make|verify (cli-spec.md §3, specs.md §5, §13)."""

import argparse
import json
import sys
from pathlib import Path

from aethel_codex.cli.ui import UIContext, UsageError
from aethel_codex.constants import LABEL_ASSET, LABEL_TEXT
from aethel_codex.errors import AethelError
from aethel_codex.merkle import blob_id
from aethel_codex.pid import Pid
from aethel_codex.proof import (
    create_chunk_proof,
    parse_chunk_proof,
    serialize_chunk_proof,
    verify_proof,
)


def _handle_proof_make(args: argparse.Namespace, ui: UIContext) -> int:
    bundle_path = getattr(args, "bundle", None)
    if not bundle_path:
        raise UsageError("Provide bundle directory path")

    b_dir = Path(bundle_path)
    if not b_dir.is_dir():
        raise AethelError("IO", f"Bundle directory not found: {b_dir}")

    chunk_idx = getattr(args, "chunk", None)
    if chunk_idx is None:
        raise UsageError("--chunk N is required for `aethel proof make`")

    asset_name = getattr(args, "asset", None)
    if asset_name:
        target_file = b_dir / "assets" / asset_name
        if not target_file.is_file():
            raise AethelError("ASSET_MISSING", f"Asset {asset_name} not found in {b_dir}")
        blob = target_file.read_bytes()
        digest = blob_id(LABEL_ASSET, blob)
        blob_pid = Pid.create("a", digest)
    else:
        text_files = list(b_dir.glob("text.*"))
        if not text_files:
            raise AethelError("TEXT_MISSING", f"Manuscript text not found in {b_dir}")
        target_file = text_files[0]
        blob = target_file.read_bytes()
        digest = blob_id(LABEL_TEXT, blob)
        blob_pid = Pid.create("t", digest)

    proof = create_chunk_proof(blob, blob_pid, chunk_idx)
    serialized = serialize_chunk_proof(proof)

    out_file = getattr(args, "output", None)
    if out_file:
        out_p = Path(out_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_bytes(serialized)
        if not ui.quiet:
            sys.stderr.write(f"Wrote chunk proof to {out_p}\n")
    else:
        sys.stdout.buffer.write(serialized)

    return 0


def _handle_proof_verify(args: argparse.Namespace, ui: UIContext) -> int:
    proof_file = getattr(args, "proof_file", None)
    if not proof_file:
        raise UsageError("Provide chunk proof file path to verify")

    p_path = Path(proof_file)
    if not p_path.is_file():
        raise AethelError("IO", f"Proof file not found: {p_path}")

    data = p_path.read_bytes()
    proof = parse_chunk_proof(data)
    valid = verify_proof(proof)

    if ui.json_mode:
        doc = {
            "schema": "aethel.proof.verify/1",
            "valid": valid,
            "blob": str(proof.blob_pid),
            "blob_length": proof.blob_length,
            "chunk_index": proof.chunk_index,
            "path_length": len(proof.path),
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        if valid:
            sys.stdout.write(
                f"Proof valid: chunk {proof.chunk_index} of {proof.blob_pid} "
                f"({proof.blob_length:,} bytes, {len(proof.path)} path nodes)\n"
            )
        else:
            sys.stdout.write(f"Proof failed: invalid chunk or audit path for {proof.blob_pid}\n")

    return 0 if valid else 1


def handle_proof(args: argparse.Namespace, ui: UIContext) -> int:
    """Dispatch proof subcommands."""
    proof_cmd = getattr(args, "proof_command", None)
    if proof_cmd == "make":
        return _handle_proof_make(args, ui)
    if proof_cmd == "verify":
        return _handle_proof_verify(args, ui)

    raise UsageError("Expected proof subcommand: make or verify")
