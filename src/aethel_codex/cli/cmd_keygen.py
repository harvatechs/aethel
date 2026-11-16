"""CLI handler for aethel keygen and aethel key info (cli-spec.md §3)."""

import argparse
import getpass
import json
import sys
from pathlib import Path

from aethel_codex.backends import get_backend
from aethel_codex.cli.ui import UIContext, UsageError
from aethel_codex.constants import TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION
from aethel_codex.errors import AethelError, KeyFileError
from aethel_codex.keyfile import create_key
from aethel_codex.pid import key_id


def _resolve_passphrase(args: argparse.Namespace) -> str | None:
    """Resolve passphrase from flags or interactive TTY prompt."""
    if args.no_passphrase:
        return None

    if args.passphrase_file:
        p_path = Path(args.passphrase_file)
        try:
            return p_path.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as e:
            msg = f"Cannot read passphrase file {p_path}: {e}"
            raise AethelError("KEYFILE_INVALID", msg) from None

    if not sys.stdin.isatty():
        msg = (
            "Passphrase required: run from a terminal or provide "
            "--passphrase-file or --no-passphrase"
        )
        raise UsageError(msg)

    p1 = getpass.getpass("Passphrase: ")
    p2 = getpass.getpass("Repeat passphrase: ")
    if p1 != p2:
        raise AethelError("KEYFILE_PASSPHRASE", "Passphrases do not match")
    return p1


def _generate_single_key(
    alg: str, out_path: Path | None, out_dir: Path, passphrase: str | None
) -> dict[str, str]:
    """Generate a single key pair and write to file."""
    backend = get_backend(alg)
    sec_bytes, pub_bytes = backend.generate()
    k_id = key_id(backend.alg_id, pub_bytes)
    if out_path:
        target_path = out_path
    else:
        hex_digest = k_id.split(":")[-1]
        target_path = out_dir / f"{hex_digest[:16]}.aek"

    create_key(alg, target_path, passphrase=passphrase, secret_bytes=sec_bytes)
    protection = "scrypt-chacha20poly1305" if passphrase else "none"
    return {
        "alg": alg,
        "key_id": k_id,
        "path": str(target_path),
        "protection": protection,
    }


def handle_keygen(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute keygen command."""
    passphrase = _resolve_passphrase(args)
    algs = ["ml-dsa-87", "slh-dsa-sha2-256s"] if args.dual else [args.alg]

    results: list[dict[str, str]] = []
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for alg in algs:
        target_path = Path(args.out).resolve() if (len(algs) == 1 and args.out) else None
        record = _generate_single_key(alg, target_path, out_dir, passphrase)
        results.append(record)

    if ui.json_mode:
        doc = {
            "schema": "aethel.keygen/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "keys": results,
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        for r in results:
            sys.stdout.write(f"{r['key_id']}\n")
        if not ui.quiet:
            sys.stderr.write(
                "reminder: this file holds the only copy of the secret signing key. "
                "Back it up offline.\n"
            )

    return 0


def handle_key_info(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute key info command."""
    key_path = Path(args.keyfile).resolve()
    try:
        data = key_path.read_bytes()
        text = data.decode("utf-8")
    except OSError as e:
        raise AethelError("KEYFILE_INVALID", f"Cannot read key file {key_path}: {e}") from None
    except UnicodeDecodeError:
        raise KeyFileError("KEYFILE_INVALID", f"Key file is not valid UTF-8: {key_path}") from None

    lines = text.splitlines()
    if len(lines) < 5 or lines[0] != "aethel-key 1":
        raise KeyFileError("KEYFILE_INVALID", f"Invalid key file format: {key_path}")

    alg = lines[1][len("alg ") :] if lines[1].startswith("alg ") else "unknown"
    k_id = lines[2][len("key ") :] if lines[2].startswith("key ") else "unknown"
    pub_b64 = lines[3][len("public-key ") :] if lines[3].startswith("public-key ") else ""
    protection = lines[4][len("protection ") :] if lines[4].startswith("protection ") else "none"

    if ui.json_mode:
        doc = {
            "schema": "aethel.keygen/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "keys": [
                {
                    "alg": alg,
                    "key_id": k_id,
                    "path": str(key_path),
                    "protection": protection,
                }
            ],
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        sys.stdout.write(f"Algorithm:   {alg}\n")
        sys.stdout.write(f"Key ID:      {k_id}\n")
        sys.stdout.write(f"Protection:  {protection}\n")
        if args.public:
            sys.stdout.write(f"Public key:  {pub_b64}\n")

    return 0
