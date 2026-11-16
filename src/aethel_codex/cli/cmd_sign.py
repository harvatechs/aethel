"""CLI handler for aethel sign (cli-spec.md §3)."""

import argparse
import getpass
import json
import sys
from pathlib import Path

from aethel_codex.bundle import read_bundle
from aethel_codex.cli.sanitize import sanitize_terminal
from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import (
    LABEL_MANIFEST,
    ROLE_BY_NAME,
    TOOL_NAME,
    TOOL_VERSION,
    YELLOW_PAPER_VERSION,
)
from aethel_codex.envelope import serialize_envelope
from aethel_codex.errors import AethelError, KeyFileError
from aethel_codex.hashing import H
from aethel_codex.keyfile import load_key
from aethel_codex.manifest import parse_manifest
from aethel_codex.report import Status
from aethel_codex.signing import sign_manifest
from aethel_codex.verify import verify_bundle


def _parse_role(role_str: str) -> int:
    """Parse role string into integer (1..255)."""
    norm = role_str.lower()
    if norm in ROLE_BY_NAME:
        return ROLE_BY_NAME[norm]
    if norm.startswith("0x") and len(norm) == 4:
        try:
            val = int(norm[2:], 16)
            if 1 <= val <= 255:
                return val
        except ValueError:
            pass
    raise AethelError("E_BAD_VALUE", f"Invalid role identifier: {role_str!r}")


def _resolve_passphrase(passphrase_file: str | None) -> str | None:
    if passphrase_file:
        p_path = Path(passphrase_file)
        try:
            return p_path.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as e:
            msg = f"Cannot read passphrase file {p_path}: {e}"
            raise AethelError("KEYFILE_INVALID", msg) from None

    if not sys.stdin.isatty():
        return None

    return getpass.getpass("Passphrase: ")


def handle_sign(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute sign command."""
    bundle_path = Path(args.bundle).resolve()

    # 1. Integrity check V1-V3 via verify_bundle
    rep = verify_bundle(bundle_path)
    if rep.integrity != "PASS":
        fail_code = next(
            (c.code for c in rep.checks[:3] if c.status == Status.FAIL), "INTEGRITY_FAIL"
        )
        sys.stderr.write(
            f"error: refusing to sign: the bundle's integrity check failed ({fail_code}).\n"
            "       Signing a bundle that does not match its own manifest would "
            "approve nothing real.\n"
        )
        return 1

    view = read_bundle(bundle_path)
    if view.manifest_item is None:
        raise AethelError("MANIFEST_MISSING", "Manifest item is missing in bundle")
    manifest_bytes = view.manifest_item.read_bytes()
    manifest = parse_manifest(manifest_bytes)

    # 2. Key loading
    passphrase = _resolve_passphrase(args.passphrase_file)
    key_path = Path(args.key).resolve()
    try:
        secret_key = load_key(key_path, passphrase=passphrase)
    except KeyFileError as e:
        raise AethelError(e.code, str(e)) from None

    # 3. Role and author warning
    role = _parse_role(args.role)
    if role == 1 and secret_key.key_pid not in manifest.authors and not ui.quiet:
        sys.stderr.write(
            "warning: key is not a declared author in manifest.pip; "
            "signature will be reported separately and will not count toward attribution.\n"
        )

    # 4. Sign and write envelope
    manifest_digest = H(LABEL_MANIFEST, manifest_bytes)
    m_pid = f"pip1:m:{manifest_digest.hex()}"

    env = sign_manifest(manifest_digest, role, secret_key.alg.alg_id, secret_key.secret_bytes)
    sig_rel_path = env.envelope_filename()
    dest_path = bundle_path / sig_rel_path

    if dest_path.exists():
        sys.stderr.write(f"error: signature file already exists: {dest_path}\n")
        return 5

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(serialize_envelope(env))

    if ui.json_mode:
        doc = {
            "schema": "aethel.sign/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "bundle_path": str(bundle_path),
            "manifest_id": m_pid,
            "role": env.role_name(),
            "alg": env.alg_name,
            "key_id": str(env.key_pid),
            "signature_file": sig_rel_path,
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        clean_bundle = sanitize_terminal(str(bundle_path))
        line = (
            f"Signed {clean_bundle} as {env.role_name()} ({env.alg_name}) with key {env.key_pid}\n"
        )
        sys.stdout.write(line)

    return 0
