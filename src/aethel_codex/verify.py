"""Verification engine executing checks V1 through V8 (YP §11, specs.md §9)."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aethel_codex.bundle import BundleItem, BundleView, read_bundle
from aethel_codex.citations import scan_inline_citations
from aethel_codex.constants import (
    CHUNK_SIZE,
    LABEL_ASSET,
    LABEL_MANIFEST,
    STANDING_NOTE_SIGNATURE,
    STANDING_NOTE_TIME,
)
from aethel_codex.ctf1 import canonicalize
from aethel_codex.envelope import parse_envelope
from aethel_codex.errors import AethelError, EnvelopeError
from aethel_codex.hashing import H
from aethel_codex.limits import DEFAULT_LIMITS, Limits
from aethel_codex.manifest import AssetEntry, Manifest, parse_manifest
from aethel_codex.merkle import TreeHasher, text_id
from aethel_codex.pid import Pid
from aethel_codex.report import (
    AttributionReport,
    CheckResult,
    Status,
    VerifyReport,
)
from aethel_codex.signing import verify_signature_envelope

_MARKUP_EXTENSIONS: dict[str, str] = {
    "pip-md-1": "text.md",
    "pip-tex-1": "text.tex",
    "pip-txt-1": "text.txt",
}


def _check_v1_manifest(
    view: BundleView, limits: Limits
) -> tuple[CheckResult, bytes | None, Manifest | None, Pid | None]:
    """Execute check V1 (Manifest)."""
    if view.limit_exceeded:
        return (
            CheckResult("V1", Status.SKIPPED, "LIMIT_EXCEEDED", view.limit_reason),
            None,
            None,
            None,
        )

    if view.manifest_item is None:
        return (
            CheckResult("V1", Status.FAIL, "MANIFEST_MISSING", "manifest.pip not found"),
            None,
            None,
            None,
        )

    if not view.manifest_item.is_safe:
        return (
            CheckResult(
                "V1",
                Status.FAIL,
                view.manifest_item.error_code or "UNSAFE_PATH",
                view.manifest_item.error_detail,
            ),
            None,
            None,
            None,
        )

    try:
        manifest_bytes = view.manifest_item.read_bytes()
    except OSError as e:
        return CheckResult("V1", Status.FAIL, "MANIFEST_MISSING", str(e)), None, None, None

    if len(manifest_bytes) > limits.max_manifest_bytes:
        return (
            CheckResult(
                "V1",
                Status.SKIPPED,
                "LIMIT_EXCEEDED",
                f"Manifest size {len(manifest_bytes)} exceeds limit {limits.max_manifest_bytes}",
            ),
            None,
            None,
            None,
        )

    try:
        manifest = parse_manifest(manifest_bytes)
    except AethelError as e:
        return (
            CheckResult("V1", Status.FAIL, "MANIFEST_INVALID", e.code),
            manifest_bytes,
            None,
            None,
        )

    manifest_digest = H(LABEL_MANIFEST, manifest_bytes)
    manifest_pid = Pid("m", manifest_digest)

    if view.is_hex_dir_name and view.dir_name != manifest_digest.hex():
        detail = (
            f"Directory name {view.dir_name} does not match manifest ID {manifest_digest.hex()}"
        )
        return (
            CheckResult("V1", Status.FAIL, "ID_MISMATCH", detail),
            manifest_bytes,
            manifest,
            manifest_pid,
        )

    return (
        CheckResult("V1", Status.PASS, None, None),
        manifest_bytes,
        manifest,
        manifest_pid,
    )


def _resolve_text_item(view: BundleView, markup: str) -> tuple[BundleItem | None, bool]:
    expected_filename = _MARKUP_EXTENSIONS.get(markup, "text.txt")
    target_item = None
    extra_text = False

    for item in view.text_items:
        if item.name == expected_filename:
            target_item = item
        else:
            extra_text = True
    return target_item, extra_text


def _verify_text_bytes(raw_text: bytes, manifest: Manifest) -> tuple[bool, str | None, str | None]:
    if len(raw_text) != manifest.text_length:
        return (
            False,
            "TEXT_LENGTH",
            f"File length {len(raw_text)} != declared {manifest.text_length}",
        )

    try:
        canonical_bytes, _ = canonicalize(raw_text)
    except AethelError as e:
        return False, "TEXT_NOT_CANONICAL", e.code

    if canonical_bytes != raw_text:
        return False, "TEXT_NOT_CANONICAL", "differs"

    computed_tid = text_id(canonical_bytes)
    if str(computed_tid) != str(manifest.text_pid):
        return (
            False,
            "TEXT_MISMATCH",
            f"Computed {computed_tid} != declared {manifest.text_pid}",
        )

    return True, None, None


def _check_v2_text(
    view: BundleView, manifest: Manifest | None, limits: Limits
) -> tuple[CheckResult, bytes | None]:
    """Execute check V2 (Text)."""
    if manifest is None:
        return CheckResult("V2", Status.SKIPPED, "DEPENDS_ON_V1"), None

    target_item, extra_text = _resolve_text_item(view, manifest.markup)
    expected_filename = _MARKUP_EXTENSIONS.get(manifest.markup, "text.txt")

    if target_item is None:
        return CheckResult("V2", Status.FAIL, "TEXT_MISSING", f"{expected_filename} missing"), None

    if not target_item.is_safe:
        return (
            CheckResult(
                "V2",
                Status.FAIL,
                target_item.error_code or "UNSAFE_PATH",
                target_item.error_detail,
            ),
            None,
        )

    try:
        raw_text = target_item.read_bytes()
    except OSError as e:
        return CheckResult("V2", Status.FAIL, "TEXT_MISSING", str(e)), None

    if len(raw_text) > limits.max_text_bytes:
        return (
            CheckResult(
                "V2",
                Status.SKIPPED,
                "LIMIT_EXCEEDED",
                f"Text size {len(raw_text)} exceeds limit {limits.max_text_bytes}",
            ),
            None,
        )

    ok, code, detail = _verify_text_bytes(raw_text, manifest)
    if not ok:
        return CheckResult("V2", Status.FAIL, code, detail), raw_text

    if extra_text:
        return (
            CheckResult("V2", Status.WARN, "EXTRA_FILE", "Extra text.* file in bundle"),
            raw_text,
        )

    return CheckResult("V2", Status.PASS), raw_text


def _verify_single_asset(
    item: BundleItem, asset: AssetEntry, limits: Limits
) -> tuple[bool, str | None, str | None]:
    if not item.is_safe:
        return False, item.error_code or "UNSAFE_PATH", item.error_detail

    hasher = TreeHasher()
    try:
        with open(item.path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                if (
                    limits.max_asset_bytes is not None
                    and hasher.length + len(chunk) > limits.max_asset_bytes
                ):
                    return False, "LIMIT_EXCEEDED", None
                hasher.update(chunk)
    except OSError as e:
        return False, "ASSET_MISSING", str(e)

    if hasher.length != asset.length:
        return False, "ASSET_MISMATCH", f"Length {hasher.length} != {asset.length}"

    asset_digest = H(LABEL_ASSET, hasher.length.to_bytes(8, "big") + hasher.root())
    asset_pid_str = f"pip1:a:{asset_digest.hex()}"
    if asset_pid_str != str(asset.pid):
        return False, "ASSET_MISMATCH", f"ID {asset_pid_str} != {asset.pid}"

    return True, None, None


def _check_v3_assets(view: BundleView, manifest: Manifest | None, limits: Limits) -> CheckResult:
    """Execute check V3 (Assets)."""
    if manifest is None:
        return CheckResult("V3", Status.SKIPPED, "DEPENDS_ON_V1")

    items: list[dict[str, Any]] = []
    has_fail = False
    fail_code: str | None = None
    fail_detail: str | None = None

    for asset in manifest.assets:
        if asset.name not in view.asset_items:
            items.append(
                {"subject": asset.name, "status": "FAIL", "code": "ASSET_MISSING", "detail": None}
            )
            has_fail = True
            fail_code = fail_code or "ASSET_MISSING"
            continue

        item = view.asset_items[asset.name]
        ok, code, detail = _verify_single_asset(item, asset, limits)
        if not ok:
            if code == "LIMIT_EXCEEDED":
                return CheckResult("V3", Status.SKIPPED, "LIMIT_EXCEEDED")
            items.append({"subject": asset.name, "status": "FAIL", "code": code, "detail": detail})
            has_fail = True
            fail_code = fail_code or code
            fail_detail = fail_detail or detail
            continue

        items.append({"subject": asset.name, "status": "PASS", "code": None, "detail": None})

    declared_names = {a.name for a in manifest.assets}
    unlisted = (set(view.asset_items.keys()) - declared_names) | set(view.extra_asset_names)

    if has_fail:
        return CheckResult("V3", Status.FAIL, fail_code, fail_detail, items=items)
    if unlisted:
        return CheckResult(
            "V3",
            Status.WARN,
            "ASSET_EXTRA",
            f"Unlisted files in assets/: {sorted(unlisted)}",
            items=items,
        )
    return CheckResult("V3", Status.PASS, items=items)


def _check_v4_citations(manifest: Manifest | None, text_bytes: bytes | None) -> CheckResult:
    """Execute check V4 (Citations)."""
    if manifest is None:
        return CheckResult("V4", Status.SKIPPED, "DEPENDS_ON_V1")

    if text_bytes is None:
        return CheckResult("V4", Status.PASS)

    try:
        text_str = text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return CheckResult("V4", Status.PASS)

    scanned_pids = scan_inline_citations(text_str)
    declared_pids = {str(c) for c in manifest.cites} | {str(a.pid) for a in manifest.assets}
    declared_pids.add(str(manifest.text_pid))

    for pid in scanned_pids:
        if str(pid) not in declared_pids:
            return CheckResult(
                "V4",
                Status.WARN,
                "CITE_UNLISTED",
                f"Inline citation not declared in manifest: {pid}",
            )

    return CheckResult("V4", Status.PASS)


def _find_parent_bundle(parents: Path, parent_pid: Pid) -> BundleView | None:
    parent_hex = parent_pid.hex()
    if parents.name == parent_hex and parents.is_dir():
        return read_bundle(parents)
    direct = parents / parent_hex
    if direct.is_dir():
        return read_bundle(direct)
    return None


def _check_v5_history(
    manifest: Manifest | None, parents: Path | None
) -> tuple[CheckResult, list[str]]:
    """Execute check V5 (History)."""
    if manifest is None:
        return CheckResult("V5", Status.SKIPPED, "DEPENDS_ON_V1"), []

    if manifest.work_pid is None and not manifest.parents:
        return CheckResult("V5", Status.SKIPPED, "NO_PARENTS"), []

    if parents is None or not parents.exists():
        return CheckResult("V5", Status.SKIPPED, "PARENTS_UNAVAILABLE"), []

    parent_sources: list[str] = []
    for parent_pid in manifest.parents:
        parent_view = _find_parent_bundle(parents, parent_pid)
        if parent_view is None or parent_view.manifest_item is None:
            return CheckResult("V5", Status.SKIPPED, "PARENTS_UNAVAILABLE"), []

        try:
            p_bytes = parent_view.manifest_item.read_bytes()
            p_manifest = parse_manifest(p_bytes)
        except (OSError, AethelError):
            return CheckResult("V5", Status.SKIPPED, "PARENTS_UNAVAILABLE"), []

        p_work_id = (
            str(p_manifest.work_pid)
            if p_manifest.work_pid
            else f"pip1:m:{H(LABEL_MANIFEST, p_bytes).hex()}"
        )
        if p_work_id != str(manifest.work_pid):
            return (
                CheckResult(
                    "V5",
                    Status.FAIL,
                    "WORK_MISMATCH",
                    f"Parent work ID {p_work_id} does not match {manifest.work_pid}",
                ),
                parent_sources,
            )
        parent_sources.append(str(parent_view.root_path))

    return CheckResult("V5", Status.PASS), parent_sources


def _check_v6_signatures(
    view: BundleView, manifest: Manifest | None, manifest_pid: Pid | None, limits: Limits
) -> tuple[CheckResult, list[Any]]:
    """Execute check V6 (Signatures)."""
    if manifest is None or manifest_pid is None:
        return CheckResult("V6", Status.SKIPPED, "DEPENDS_ON_V1"), []

    if not view.signature_items:
        return CheckResult("V6", Status.SKIPPED, "NO_SIGNATURES"), []

    verified_envelopes: list[Any] = []
    for item in view.signature_items:
        if not item.is_safe:
            return (
                CheckResult("V6", Status.FAIL, item.error_code or "UNSAFE_PATH", item.error_detail),
                [],
            )

        try:
            env_bytes = item.read_bytes()
        except OSError as e:
            return CheckResult("V6", Status.FAIL, "ENVELOPE_INVALID", str(e)), []

        if len(env_bytes) > limits.max_envelope_bytes:
            return CheckResult("V6", Status.FAIL, "ENVELOPE_INVALID", "Envelope exceeds limit"), []

        try:
            envelope = parse_envelope(env_bytes)
        except EnvelopeError as e:
            return CheckResult("V6", Status.FAIL, e.code, str(e)), []

        ok, err_code = verify_signature_envelope(envelope, expected_manifest_pid=manifest_pid)
        if not ok:
            return CheckResult("V6", Status.FAIL, err_code or "SIG_INVALID"), []

        verified_envelopes.append(envelope)

    if view.extra_signature_names:
        return (
            CheckResult(
                "V6",
                Status.WARN,
                "EXTRA_FILE",
                f"Extra files in signatures/: {view.extra_signature_names}",
            ),
            verified_envelopes,
        )

    return CheckResult("V6", Status.PASS), verified_envelopes


def _determine_attribution_class(m: int, n: int, valid_author_keys: dict[str, str]) -> str:
    if m == 0:
        return "Unattributed"
    if 0 < m < n:
        return "Partially attributed"
    algs = set(valid_author_keys.values())
    has_ml = any("ml-dsa" in a for a in algs)
    has_slh = any("slh-dsa" in a for a in algs)
    return "Dual-family" if (has_ml and has_slh) else "Attributed"


def _check_v7_attribution(
    manifest: Manifest | None, verified_envelopes: Sequence[Any]
) -> tuple[CheckResult, AttributionReport]:
    """Execute check V7 (Attribution)."""
    if manifest is None:
        dummy_att = AttributionReport(
            cls="Unattributed", signed=0, declared=0, keccak_independent=False
        )
        return CheckResult("V7", Status.SKIPPED, "DEPENDS_ON_V1"), dummy_att

    declared_keys = [str(k) for k in manifest.authors]
    valid_author_keys: dict[str, str] = {}
    other_sigs: list[dict[str, Any]] = []

    for env in verified_envelopes:
        key_str = str(env.key_pid)
        if env.role == 1 and key_str in declared_keys:
            if key_str not in valid_author_keys:
                valid_author_keys[key_str] = env.alg_name
        else:
            other_sigs.append({"key": key_str, "role": env.role_name(), "alg": env.alg_name})

    m = len(valid_author_keys)
    n = len(declared_keys)
    cls = _determine_attribution_class(m, n, valid_author_keys)
    keccak_independent = any(a == "slh-dsa-sha2-256s" for a in valid_author_keys.values())

    keys_list: list[dict[str, Any]] = []
    for k in declared_keys:
        if k in valid_author_keys:
            keys_list.append({"key": k, "status": "signed", "alg": valid_author_keys[k]})
        else:
            keys_list.append({"key": k, "status": "missing", "alg": None})

    att_report = AttributionReport(
        cls=cls,
        signed=m,
        declared=n,
        keccak_independent=keccak_independent,
        keys=keys_list,
        other_signatures=other_sigs,
    )
    return CheckResult("V7", Status.PASS), att_report


def _check_v8_time(view: BundleView, manifest: Manifest | None) -> CheckResult:
    """Execute check V8 (Time)."""
    items: list[dict[str, Any]] = []

    if manifest and manifest.beacon:
        items.append(
            {
                "kind": "beacon",
                "status": "UNVERIFIED",
                "source": manifest.beacon.source,
                "value": manifest.beacon.value.hex(),
            }
        )

    for att in view.attestation_items:
        items.append({"kind": "attestation", "status": "UNVERIFIED", "file": att.name})

    if not items and not view.extra_attestation_names:
        return CheckResult("V8", Status.SKIPPED, "NO_TIME_EVIDENCE")

    if view.extra_attestation_names:
        return CheckResult(
            "V8",
            Status.WARN,
            "EXTRA_FILE",
            f"Extra files in attestations/: {view.extra_attestation_names}",
            items=items,
        )

    if manifest and manifest.beacon:
        return CheckResult(
            "V8",
            Status.WARN,
            "BEACON_UNVERIFIED",
            "Beacon present, unchecked",
            items=items,
        )

    return CheckResult(
        "V8",
        Status.WARN,
        "ATT_UNVERIFIED",
        "Attestation present, unverified",
        items=items,
    )


def _determine_exit_code(
    integrity: str,
    attribution: AttributionReport,
    checks: list[CheckResult],
    res_v5: CheckResult,
    require_attributed: bool,
    require_dual_family: bool,
    require_parents: bool,
    warnings_as_errors: bool,
) -> int:
    if integrity == "INCONCLUSIVE":
        return 6
    if integrity == "FAIL":
        return 1
    if require_attributed and attribution.cls in ("Unattributed", "Partially attributed"):
        return 1
    if require_dual_family and attribution.cls != "Dual-family":
        return 1
    if require_parents and res_v5.status == Status.SKIPPED:
        return 1
    if warnings_as_errors and any(c.status == Status.WARN for c in checks):
        return 2
    return 0


def verify_bundle(
    path: Path | str,
    *,
    parents: Path | str | None = None,
    limits: Limits | None = None,
    require_attributed: bool = False,
    require_dual_family: bool = False,
    require_parents: bool = False,
    warnings_as_errors: bool = False,
) -> VerifyReport:
    """Verify an on-disk bundle executing checks V1 through V8 (YP §11, specs.md §9)."""
    if limits is None:
        limits = DEFAULT_LIMITS

    view = read_bundle(path, limits=limits)
    parents_path = Path(parents).resolve() if parents else None

    # V1: Manifest
    res_v1, _manifest_bytes, manifest, manifest_pid = _check_v1_manifest(view, limits)

    # V2: Text
    res_v2, text_bytes = _check_v2_text(view, manifest, limits)

    # V3: Assets
    res_v3 = _check_v3_assets(view, manifest, limits)

    # V4: Citations
    res_v4 = _check_v4_citations(manifest, text_bytes)

    # V5: History
    res_v5, parent_sources = _check_v5_history(manifest, parents_path)

    # V6: Signatures
    res_v6, verified_envelopes = _check_v6_signatures(view, manifest, manifest_pid, limits)

    # V7: Attribution
    res_v7, attribution = _check_v7_attribution(manifest, verified_envelopes)

    # V8: Time
    res_v8 = _check_v8_time(view, manifest)

    checks = [res_v1, res_v2, res_v3, res_v4, res_v5, res_v6, res_v7, res_v8]

    # Integrity summary
    v1_v3_fails = any(c.status == Status.FAIL for c in (res_v1, res_v2, res_v3))
    v1_v3_limits = any(
        c.status == Status.SKIPPED and c.code == "LIMIT_EXCEEDED" for c in (res_v1, res_v2, res_v3)
    )

    if v1_v3_fails:
        integrity = "FAIL"
    elif v1_v3_limits or view.limit_exceeded:
        integrity = "INCONCLUSIVE"
    else:
        integrity = "PASS"

    # Warnings collection
    warnings: list[str] = []
    for c in checks:
        if c.status == Status.WARN:
            warnings.append(f"{c.id}: {c.code or ''} {c.detail or ''}".strip())

    notes = [
        STANDING_NOTE_SIGNATURE,
        STANDING_NOTE_TIME,
    ]

    history_dict: dict[str, Any] = {
        "status": res_v5.status_value(),
        "reason": res_v5.code,
        "parents": parent_sources,
    }

    time_dict: dict[str, Any] = {
        "status": res_v8.status_value(),
        "reason": res_v8.code,
        "items": res_v8.items,
    }

    exit_code = _determine_exit_code(
        integrity=integrity,
        attribution=attribution,
        checks=checks,
        res_v5=res_v5,
        require_attributed=require_attributed,
        require_dual_family=require_dual_family,
        require_parents=require_parents,
        warnings_as_errors=warnings_as_errors,
    )

    return VerifyReport(
        bundle_path=str(view.root_path),
        manifest_id=str(manifest_pid) if manifest_pid else None,
        work_id=(
            str(manifest.work_pid)
            if manifest and manifest.work_pid
            else (str(manifest_pid) if manifest_pid else None)
        ),
        integrity=integrity,
        attribution=attribution,
        history=history_dict,
        time=time_dict,
        checks=checks,
        warnings=warnings,
        notes=notes,
        exit_code=exit_code,
    )
