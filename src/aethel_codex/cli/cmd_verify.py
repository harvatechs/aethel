"""CLI handler for aethel verify (cli-spec.md §3)."""

import argparse
import json
import sys
from pathlib import Path

from aethel_codex.cli.ui import UIContext
from aethel_codex.limits import DEFAULT_LIMITS, Limits
from aethel_codex.report import VerifyReport
from aethel_codex.verify import verify_bundle


def _render_human_report(report: VerifyReport, ui: UIContext) -> None:
    dot = ui.dot()
    m_id = report.manifest_id or "unknown"
    sys.stdout.write(f"{m_id}\n\n")

    # Integrity line
    sys.stdout.write(f"Integrity    {report.integrity:<12}\n")

    # Attribution line
    attr = report.attribution
    sys.stdout.write(f"Attribution  {attr.cls} ({attr.signed} of {attr.declared})\n")
    for k in attr.keys:
        k_id = ui.abbreviate_id(k["key"])
        alg_str = k.get("alg") or ""
        sys.stdout.write(f"               {k_id}   {k['status']:<8} {alg_str}\n")

    # History line
    hist_status = report.history.get("status", "SKIPPED")
    hist_reason = report.history.get("reason", "")
    hist_desc = "genesis manifest, no parents" if hist_reason == "NO_PARENTS" else hist_reason
    sys.stdout.write(f"History      {hist_status:<12} {hist_desc}\n")

    # Time line
    time_status = report.time.get("status", "SKIPPED")
    time_reason = report.time.get("reason", "")
    if time_reason == "NO_TIME_EVIDENCE":
        time_desc = "no beacon and no attestations"
    elif time_reason == "ATT_UNVERIFIED":
        time_desc = "attestation present, unverified"
    elif time_reason == "BEACON_UNVERIFIED":
        time_desc = "beacon present, unchecked"
    else:
        time_desc = time_reason
    sys.stdout.write(f"Time         {time_status:<12} {time_desc}\n\n")

    # Checks summary line
    checks_str = f" {dot} ".join(f"{c.id} {c.status}" for c in report.checks)
    sys.stdout.write(f"Checks  {checks_str}\n")
    for note in report.notes:
        sys.stdout.write(f"{note}\n")


def _build_limits(args: argparse.Namespace) -> Limits:
    """Build Limits configuration based on CLI arguments."""
    if not (args.max_text_bytes or args.max_asset_bytes):
        return DEFAULT_LIMITS
    return Limits(
        max_text_bytes=args.max_text_bytes or DEFAULT_LIMITS.max_text_bytes,
        max_manifest_bytes=DEFAULT_LIMITS.max_manifest_bytes,
        max_envelope_bytes=DEFAULT_LIMITS.max_envelope_bytes,
        max_signatures=DEFAULT_LIMITS.max_signatures,
        max_asset_bytes=args.max_asset_bytes or DEFAULT_LIMITS.max_asset_bytes,
        max_dir_entries=DEFAULT_LIMITS.max_dir_entries,
    )


def _render_verify_output(reports: list[VerifyReport], ui: UIContext) -> None:
    """Render verification reports to JSON or human-readable stdout."""
    if ui.json_mode:
        if len(reports) == 1:
            sys.stdout.write(json.dumps(reports[0].to_dict(), indent=2) + "\n")
        else:
            for rep in reports:
                sys.stdout.write(json.dumps(rep.to_dict(), separators=(",", ":")) + "\n")
    else:
        for i, rep in enumerate(reports):
            if i > 0:
                sys.stdout.write("\n" + "=" * 60 + "\n\n")
            _render_human_report(rep, ui)


def handle_verify(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute verify command across one or more bundles."""
    limits = _build_limits(args)
    parents_path = Path(args.parents).resolve() if args.parents else None
    reports: list[VerifyReport] = []
    exit_codes: list[int] = []

    for b_path in args.bundle:
        bundle_dir = Path(b_path).resolve()
        rep = verify_bundle(
            bundle_dir,
            parents=parents_path,
            require_attributed=args.require_attributed,
            require_dual_family=args.require_dual_family,
            require_parents=args.require_parents,
            warnings_as_errors=args.warnings_as_errors,
            limits=limits,
        )
        reports.append(rep)
        exit_codes.append(rep.exit_code)

    _render_verify_output(reports, ui)

    # Exit code precedence: 1 beats 6 beats 0
    if 1 in exit_codes:
        return 1
    if 6 in exit_codes:
        return 6
    for code in exit_codes:
        if code != 0:
            return code
    return 0
