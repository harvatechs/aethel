"""CLI handler for aethel attest add (cli-spec.md §3, specs.md §8)."""

import argparse
import json
import sys
from pathlib import Path

from aethel_codex.cli.ui import UIContext, UsageError
from aethel_codex.constants import LABEL_MANIFEST
from aethel_codex.envelope import (
    KIND_RE,
    AttestationEnvelope,
    serialize_attestation_envelope,
    strict_b64decode,
)
from aethel_codex.errors import AethelError
from aethel_codex.hashing import H
from aethel_codex.pid import Pid


def _read_proof_bytes(args: argparse.Namespace) -> bytes:
    proof_b64 = getattr(args, "proof_b64", None)
    proof_file = getattr(args, "proof_file", None)
    if not proof_b64 and not proof_file:
        raise UsageError("Either --proof-b64 or --proof-file is required")

    if proof_file:
        p_path = Path(str(proof_file))
        if not p_path.is_file():
            raise AethelError("IO", f"Proof file not found: {p_path}")
        return p_path.read_bytes()
    return strict_b64decode(str(proof_b64))


def _write_attestation_file(b_dir: Path, kind: str, serialized: bytes) -> Path:
    att_dir = b_dir / "attestations"
    att_dir.mkdir(parents=True, exist_ok=True)
    out_file = att_dir / f"{kind}.att"
    if out_file.exists():
        if out_file.read_bytes() != serialized:
            raise AethelError("IO", f"Attestation file already exists: {out_file}")
    else:
        out_file.write_bytes(serialized)
    return out_file


def _handle_attest_add(args: argparse.Namespace, ui: UIContext) -> int:
    bundle_path = getattr(args, "bundle", None)
    if not bundle_path:
        raise UsageError("Provide bundle directory path")

    b_dir = Path(bundle_path)
    if not b_dir.is_dir():
        raise AethelError("IO", f"Bundle directory not found: {b_dir}")

    manifest_file = b_dir / "manifest.pip"
    if not manifest_file.is_file():
        raise AethelError("MANIFEST_MISSING", f"manifest.pip not found in {b_dir}")

    m_data = manifest_file.read_bytes()
    m_digest = H(LABEL_MANIFEST, m_data)
    manifest_pid = Pid.create("m", m_digest)

    kind = getattr(args, "kind", None)
    if not kind:
        raise UsageError("--kind KIND is required for `aethel attest add`")
    if not KIND_RE.fullmatch(kind):
        raise AethelError("ENVELOPE_INVALID", f"Invalid attestation kind: {kind!r}")

    proof_bytes = _read_proof_bytes(args)

    env = AttestationEnvelope(
        manifest_pid=manifest_pid,
        kind=kind,
        proof=proof_bytes,
    )
    serialized = serialize_attestation_envelope(env)
    _write_attestation_file(b_dir, kind, serialized)

    if ui.json_mode:
        doc = {
            "schema": "aethel.attest.add/1",
            "manifest_id": str(manifest_pid),
            "kind": kind,
            "file": f"attestations/{kind}.att",
            "proof_bytes": len(proof_bytes),
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        sys.stdout.write(f"Added attestation {kind} to {b_dir}\n")

    return 0


def handle_attest(args: argparse.Namespace, ui: UIContext) -> int:
    """Dispatch attest subcommands."""
    attest_cmd = getattr(args, "attest_command", None)
    if attest_cmd == "add":
        return _handle_attest_add(args, ui)

    raise UsageError("Expected attest subcommand: add")
