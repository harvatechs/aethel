"""CLI handler for aethel revise (cli-spec.md §3)."""

import argparse
import json
import sys
from pathlib import Path

from aethel_codex.cli.cmd_publish import (
    _build_publish_json,
    _parse_asset_inputs,
    _parse_beacon,
    _parse_derivatives,
    _print_publish_human,
    _resolve_key_passphrases,
)
from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import CHUNK_SIZE
from aethel_codex.pid import Pid
from aethel_codex.publish import PublishRequest, revise_bundle


def handle_revise(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute revise command."""
    parent_bundle = Path(args.parent_bundle)
    manuscript = Path(args.manuscript)
    assets = _parse_asset_inputs(args)
    derivatives = _parse_derivatives(args.derivative)
    beacon = _parse_beacon(args.beacon)
    passphrases = _resolve_key_passphrases(args.key, args.passphrase_file)

    parents_dir = Path(args.parents) if getattr(args, "parents", None) else None

    req = PublishRequest(
        manuscript_path=manuscript,
        title=args.title,
        title_from_heading=args.title_from_heading,
        license=args.license,
        markup=args.markup,
        lang=args.lang if args.lang is not None else "und",
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
        parents_dir=parents_dir,
    )

    keep_assets = getattr(args, "keep_assets", False)
    keep_cites = getattr(args, "keep_cites", False)

    result = revise_bundle(
        parent_bundle_path=parent_bundle,
        req=req,
        keep_assets=keep_assets,
        keep_cites=keep_cites,
    )

    t_len = result.manifest.text_length
    chunks = (t_len + CHUNK_SIZE - 1) // CHUNK_SIZE if t_len > 0 else 1

    if ui.json_mode:
        doc = _build_publish_json(result, chunks)
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        _print_publish_human(result, chunks, ui)

    return 0
