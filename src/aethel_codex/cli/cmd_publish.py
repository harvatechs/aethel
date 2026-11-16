"""CLI handler for aethel publish (cli-spec.md §3)."""

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any

from aethel_codex.cli.sanitize import sanitize_terminal
from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import CHUNK_SIZE, TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION
from aethel_codex.errors import AethelError
from aethel_codex.pid import Pid
from aethel_codex.publish import AssetInput, PublishRequest, PublishResult, publish_bundle


def _parse_asset_inputs(args: argparse.Namespace) -> list[AssetInput]:
    name_overrides: dict[str, str] = {}
    for item in args.asset_name:
        if "=" in item:
            src, target_name = item.split("=", 1)
            name_overrides[src] = target_name

    media_overrides: dict[str, str] = {}
    for item in args.asset_media:
        if "=" in item:
            name, media_type = item.split("=", 1)
            media_overrides[name] = media_type

    inputs: list[AssetInput] = []
    for asset_str in args.asset:
        p = Path(asset_str)
        name = name_overrides.get(asset_str, p.name)
        media = media_overrides.get(name)
        inputs.append(AssetInput(path=p, name=name, media_type=media))
    return inputs


def _parse_derivatives(items: list[str]) -> list[tuple[str, Pid]]:
    derivatives: list[tuple[str, Pid]] = []
    for d in items:
        if ":" not in d:
            raise AethelError("E_BAD_VALUE", f"Malformed derivative specification: {d!r}")
        rel, pid_str = d.split(":", 1)
        derivatives.append((rel, Pid.parse(pid_str)))
    return derivatives


def _parse_beacon(beacon_str: str | None) -> tuple[str, int, bytes] | None:
    if not beacon_str:
        return None
    parts = beacon_str.split(":", 2)
    if len(parts) != 3:
        raise AethelError("E_BAD_VALUE", f"Malformed beacon specification: {beacon_str!r}")
    try:
        round_num = int(parts[1])
        val = bytes.fromhex(parts[2])
    except ValueError as e:
        raise AethelError("E_BAD_VALUE", f"Invalid beacon values: {e}") from None
    return parts[0], round_num, val


def _resolve_key_passphrases(
    keys: list[str], passphrase_file: str | None
) -> list[str | bytes | None]:
    if not keys:
        return []
    if passphrase_file:
        p_path = Path(passphrase_file)
        try:
            pwd = p_path.read_text(encoding="utf-8").rstrip("\r\n")
            return [pwd] * len(keys)
        except OSError as e:
            msg = f"Cannot read passphrase file {p_path}: {e}"
            raise AethelError("KEYFILE_INVALID", msg) from None

    if not sys.stdin.isatty():
        return [None] * len(keys)

    pwd = getpass.getpass("Passphrase: ")
    return [pwd] * len(keys)


def _build_publish_json(result: PublishResult, chunks: int) -> dict[str, Any]:
    """Build dictionary matching aethel.publish/1 schema."""
    sigs: list[dict[str, str]] = []
    for env in result.envelopes:
        sigs.append(
            {
                "role": env.role_name(),
                "alg": env.alg_name,
                "key_id": str(env.key_pid),
                "file": env.envelope_filename(),
            }
        )

    attr_info = None
    integrity_str = None
    if result.verify_report:
        integrity_str = result.verify_report.integrity
        attr = result.verify_report.attribution
        attr_info = {
            "class": attr.cls,
            "signed": attr.signed,
            "declared": attr.declared,
        }

    return {
        "schema": "aethel.publish/1",
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "profile": "pip-1",
            "yellow_paper": YELLOW_PAPER_VERSION,
        },
        "manifest_id": str(result.manifest_pid),
        "text_id": str(result.text_pid),
        "text_length": result.manifest.text_length,
        "text_chunks": chunks,
        "bundle_path": str(result.bundle_path) if result.bundle_path else None,
        "signatures": sigs,
        "dry_run": result.dry_run,
        "integrity": integrity_str,
        "attribution": attr_info,
    }


def _print_publish_human(result: PublishResult, chunks: int, ui: UIContext) -> None:
    """Print publish human readable output (cli-spec.md §3)."""
    dot = ui.dot()
    sys.stdout.write(f"Published   {result.manifest_pid}\n")
    chunk_word = "chunk" if chunks == 1 else "chunks"
    t_len = result.manifest.text_length
    sys.stdout.write(f"  text      {result.text_pid}   {t_len:,} bytes, {chunks} {chunk_word}\n")
    for env in result.envelopes:
        role = env.role_name()
        sys.stdout.write(f"  signed    {role} {dot} {env.alg_name} {dot} {env.key_pid}\n")
    if result.bundle_path:
        clean_path = sanitize_terminal(str(result.bundle_path))
        sys.stdout.write(f"  written   {clean_path}/\n")
    if result.verify_report:
        attr = result.verify_report.attribution
        line = (
            f"Integrity {result.verify_report.integrity} {dot} "
            f"Attribution {attr.cls} ({attr.signed} of {attr.declared})\n"
        )
        sys.stdout.write(line)


def handle_publish(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute publish command."""
    manuscript = Path(args.manuscript)
    assets = _parse_asset_inputs(args)
    derivatives = _parse_derivatives(args.derivative)
    beacon = _parse_beacon(args.beacon)
    passphrases = _resolve_key_passphrases(args.key, args.passphrase_file)

    req = PublishRequest(
        manuscript_path=manuscript,
        title=args.title,
        title_from_heading=args.title_from_heading,
        license=args.license,
        markup=args.markup,
        lang=args.lang,
        keys=[Path(k) for k in args.key],
        passphrases=passphrases,
        unsigned=args.unsigned,
        authors=[Pid.parse(a) for a in args.author],
        assets=assets,
        cites=[Pid.parse(c) for c in args.cite],
        derivatives=derivatives,
        beacon=beacon,
        out_dir=Path(args.out_dir),
        dry_run=args.dry_run,
    )

    result = publish_bundle(req)
    t_len = result.manifest.text_length
    chunks = (t_len + CHUNK_SIZE - 1) // CHUNK_SIZE if t_len > 0 else 1

    if ui.json_mode:
        doc = _build_publish_json(result, chunks)
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        _print_publish_human(result, chunks, ui)

    return 0
