"""CLI handler for aethel selftest (cli-spec.md §3, specs.md §14)."""

import argparse
import base64
import importlib.resources
import json
import sys
from dataclasses import dataclass
from typing import Any

import unicodedata2

from aethel_codex import _repertoire
from aethel_codex.backends import get_backend
from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import (
    SIG_CONTEXT,
    TOOL_NAME,
    TOOL_VERSION,
    YELLOW_PAPER_VERSION,
)
from aethel_codex.ctf1 import canonicalize
from aethel_codex.errors import AethelError, CanonicalizationError
from aethel_codex.manifest import parse_manifest
from aethel_codex.merkle import asset_id, text_id


def _check_canary() -> bool:
    """Verify repertoire canary digest matches expected SHA-256 (Yellow Paper §4.4, ADR-005)."""
    expected_sha256 = "ea751092fc5e12e3b98f5538ad297624a500e38f6c756ac7ad974d05ff1baf86"
    return (
        expected_sha256 == _repertoire.CANARY_SHA256
        and _repertoire.NON_CN_COUNT == 312389
        and _repertoire.NON_CN_RANGES_COUNT == 735
    )


@dataclass
class SelftestItemResult:
    """Individual selftest item execution result."""

    name: str
    category: str
    status: str  # "PASS" or "FAIL"
    detail: str | None = None


def _load_package_vectors() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load bundled test vectors from package data."""
    data_dir = importlib.resources.files("aethel_codex").joinpath("data")
    pip1_text = data_dir.joinpath("pip1-vectors.json").read_text(encoding="utf-8")
    slh_text = data_dir.joinpath("pip1-slh-dsa-vectors.json").read_text(encoding="utf-8")
    return json.loads(pip1_text), json.loads(slh_text)


def _check_unicode() -> list[SelftestItemResult]:
    """Execute Unicode guard and canary checks."""
    results: list[SelftestItemResult] = []

    # 1. Unicode guard
    try:
        ver = unicodedata2.unidata_version
        if ver == "18.0.0":
            results.append(SelftestItemResult("unicode.guard", "unicode", "PASS", "Unicode 18.0.0"))
        else:
            msg = f"Expected Unicode 18.0.0, got {ver}"
            results.append(SelftestItemResult("unicode.guard", "unicode", "FAIL", msg))
    except (AttributeError, ValueError) as e:
        results.append(SelftestItemResult("unicode.guard", "unicode", "FAIL", str(e)))

    # 2. Unicode canary
    try:
        if _check_canary():
            results.append(
                SelftestItemResult(
                    "unicode.canary", "unicode", "PASS", "Repertoire canary verified"
                )
            )
        else:
            results.append(
                SelftestItemResult("unicode.canary", "unicode", "FAIL", "Canary digest mismatch")
            )
    except (ImportError, AttributeError, ValueError) as e:
        results.append(SelftestItemResult("unicode.canary", "unicode", "FAIL", str(e)))

    return results


def _check_ctf1_positives(yp_vecs: dict[str, Any]) -> list[SelftestItemResult]:
    """Execute CTF-1 T1-T4 positive and asset checks."""
    results: list[SelftestItemResult] = []

    # 3. CTF-1 T1 vector
    try:
        t1_vec = yp_vecs["ctf1"]["T1"]
        raw_t1 = bytes.fromhex(t1_vec["input_hex"])
        exp_t1 = bytes.fromhex(t1_vec["output_hex"])
        out_t1, _ = canonicalize(raw_t1)
        fixed_t1, _ = canonicalize(out_t1)
        t_id1 = str(text_id(out_t1))
        if out_t1 == exp_t1 and fixed_t1 == out_t1 and t_id1 == t1_vec["text_id"]:
            results.append(SelftestItemResult("ctf1.t1", "canonicalization", "PASS"))
        else:
            results.append(SelftestItemResult("ctf1.t1", "canonicalization", "FAIL", "T1 mismatch"))
    except (CanonicalizationError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("ctf1.t1", "canonicalization", "FAIL", str(e)))

    # 4. CTF-1 T2 vector
    try:
        t2_vec = yp_vecs["ctf1"]["T2"]
        raw_t2 = bytes.fromhex(t2_vec["input_hex"])
        exp_t2 = bytes.fromhex(t2_vec["output_hex"])
        out_t2, _ = canonicalize(raw_t2)
        fixed_t2, _ = canonicalize(out_t2)
        t_id2 = str(text_id(out_t2))
        if out_t2 == exp_t2 and fixed_t2 == out_t2 and t_id2 == t2_vec["text_id"]:
            results.append(SelftestItemResult("ctf1.t2", "canonicalization", "PASS"))
        else:
            results.append(SelftestItemResult("ctf1.t2", "canonicalization", "FAIL", "T2 mismatch"))
    except (CanonicalizationError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("ctf1.t2", "canonicalization", "FAIL", str(e)))

    # 5. CTF-1 T3 vector (multi-chunk)
    try:
        t3_vec = yp_vecs["ctf1"]["T3"]
        raw_t3 = (b"0123456789" * 1000)[:9999] + b"\n"
        out_t3, _ = canonicalize(raw_t3)
        t_id3 = str(text_id(out_t3))
        if out_t3 == raw_t3 and t_id3 == t3_vec["text_id"]:
            results.append(SelftestItemResult("ctf1.t3", "canonicalization", "PASS"))
        else:
            results.append(SelftestItemResult("ctf1.t3", "canonicalization", "FAIL", "T3 mismatch"))
    except (CanonicalizationError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("ctf1.t3", "canonicalization", "FAIL", str(e)))

    # 6. CTF-1 T4 vector (assets)
    try:
        assets_vec = yp_vecs["assets"]
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg"/>\n'
        empty_id_val = str(asset_id(b""))
        svg_id_val = str(asset_id(svg_bytes))
        if (
            empty_id_val == assets_vec["empty"]
            and svg_id_val == assets_vec["figure1_svg"]["asset_id"]
        ):
            results.append(SelftestItemResult("ctf1.t4", "assets", "PASS"))
        else:
            results.append(SelftestItemResult("ctf1.t4", "assets", "FAIL", "T4 asset ID mismatch"))
    except (KeyError, ValueError) as e:
        results.append(SelftestItemResult("ctf1.t4", "assets", "FAIL", str(e)))

    return results


def _check_ctf1_negatives(yp_vecs: dict[str, Any]) -> list[SelftestItemResult]:
    """Execute CTF-1 12 negative vectors checks."""
    results: list[SelftestItemResult] = []

    # 7. CTF-1 Negatives
    try:
        neg_cases = yp_vecs["ctf1"]["negative"]
        all_neg_rejected = True
        for neg in neg_cases:
            neg_raw = bytes.fromhex(neg["input_hex"])
            try:
                canonicalize(neg_raw)
                all_neg_rejected = False
                break
            except CanonicalizationError as ce:
                if ce.code != neg["expect"]:
                    all_neg_rejected = False
                    break
        if all_neg_rejected and len(neg_cases) == 12:
            results.append(
                SelftestItemResult(
                    "ctf1.negatives",
                    "canonicalization",
                    "PASS",
                    f"{len(neg_cases)} vectors rejected",
                )
            )
        else:
            results.append(
                SelftestItemResult(
                    "ctf1.negatives", "canonicalization", "FAIL", "A negative passed or wrong code"
                )
            )
    except (KeyError, ValueError) as e:
        results.append(SelftestItemResult("ctf1.negatives", "canonicalization", "FAIL", str(e)))

    return results


def _check_ctf1(yp_vecs: dict[str, Any]) -> list[SelftestItemResult]:
    """Execute CTF-1 and blob ID checks."""
    results: list[SelftestItemResult] = []
    results.extend(_check_ctf1_positives(yp_vecs))
    results.extend(_check_ctf1_negatives(yp_vecs))
    return results


def _check_manifests(yp_vecs: dict[str, Any]) -> list[SelftestItemResult]:
    """Execute manifest genesis and revision checks."""
    results: list[SelftestItemResult] = []

    # 8. Manifest genesis
    try:
        gen_vec = yp_vecs["manifests"]["genesis"]
        gen_bytes = gen_vec["text"].encode("utf-8")
        gen_m = parse_manifest(gen_bytes)
        gen_id = gen_m.manifest_id()
        if gen_id == gen_vec["manifest_id"]:
            results.append(SelftestItemResult("manifest.genesis", "manifest", "PASS"))
        else:
            results.append(
                SelftestItemResult("manifest.genesis", "manifest", "FAIL", "Genesis ID mismatch")
            )
    except (AethelError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("manifest.genesis", "manifest", "FAIL", str(e)))

    # 9. Manifest revision
    try:
        rev_vec = yp_vecs["manifests"]["revision"]
        rev_bytes = rev_vec["text"].encode("utf-8")
        rev_m = parse_manifest(rev_bytes)
        rev_id = rev_m.manifest_id()
        if rev_id == rev_vec["manifest_id"]:
            results.append(SelftestItemResult("manifest.revision", "manifest", "PASS"))
        else:
            results.append(
                SelftestItemResult("manifest.revision", "manifest", "FAIL", "Revision ID mismatch")
            )
    except (AethelError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("manifest.revision", "manifest", "FAIL", str(e)))

    return results


def _check_crypto(yp_vecs: dict[str, Any], slh_vecs: dict[str, Any]) -> list[SelftestItemResult]:
    """Execute cryptographic verification checks across backends."""
    results: list[SelftestItemResult] = []

    # 10. Crypto ML-DSA-87 (A.2)
    try:
        a2_vec = yp_vecs["signature_ml_dsa_87"]
        be87 = get_backend("ml-dsa-87")
        pk87 = bytes.fromhex(a2_vec["public_key_hex"])
        sig87 = bytes.fromhex(a2_vec["signature_hex"])
        msg87 = bytes.fromhex(a2_vec["message_M_hex"])
        v_ok = be87.verify(pk87, msg87, sig87, context=SIG_CONTEXT)
        v_bad_ctx = not be87.verify(pk87, msg87, sig87, context=b"pip1.other")
        v_bad_role = not be87.verify(pk87, b"\x02" + msg87[1:], sig87, context=SIG_CONTEXT)
        if v_ok and v_bad_ctx and v_bad_role:
            results.append(SelftestItemResult("crypto.ml_dsa_87", "crypto", "PASS"))
        else:
            results.append(
                SelftestItemResult("crypto.ml_dsa_87", "crypto", "FAIL", "A.2 verification failed")
            )
    except (AethelError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("crypto.ml_dsa_87", "crypto", "FAIL", str(e)))

    # 11. Crypto ML-DSA-65
    try:
        m65_vec = yp_vecs["pack_generated"]["ml_dsa_65"]
        be65 = get_backend("ml-dsa-65")
        pk65 = bytes.fromhex(m65_vec["public_key_hex"])
        sig65 = bytes.fromhex(m65_vec["signature_hex"])
        msg65 = bytes.fromhex(m65_vec["message_M_hex"])
        v65_ok = be65.verify(pk65, msg65, sig65, context=SIG_CONTEXT)
        bad_sig65 = bytearray(sig65)
        bad_sig65[0] ^= 0x01
        v65_bad = not be65.verify(pk65, msg65, bytes(bad_sig65), context=SIG_CONTEXT)
        if v65_ok and v65_bad:
            results.append(SelftestItemResult("crypto.ml_dsa_65", "crypto", "PASS"))
        else:
            results.append(
                SelftestItemResult("crypto.ml_dsa_65", "crypto", "FAIL", "ML-DSA-65 failed")
            )
    except (AethelError, KeyError, ValueError) as e:
        results.append(SelftestItemResult("crypto.ml_dsa_65", "crypto", "FAIL", str(e)))

    # 12 & 13. SLH-DSA vectors (SHA2-256s and SHAKE-256s)
    slh_msg = bytes.fromhex(slh_vecs["message_M_hex"])
    for s_vec in slh_vecs["vectors"]:
        alg_name = s_vec["alg"]
        res_name = f"crypto.{alg_name.replace('-', '_')}"
        try:
            be_slh = get_backend(alg_name)
            pk_slh = base64.b64decode(s_vec["public_key_b64"])
            sig_slh = base64.b64decode(s_vec["signature_b64"])
            flip_slh = base64.b64decode(s_vec["flipped_signature_b64"])

            ok_ver = be_slh.verify(pk_slh, slh_msg, sig_slh, context=SIG_CONTEXT)
            ok_flip = not be_slh.verify(pk_slh, slh_msg, flip_slh, context=SIG_CONTEXT)
            ok_ctx = not be_slh.verify(pk_slh, slh_msg, sig_slh, context=b"pip1.other")
            ok_role = not be_slh.verify(pk_slh, b"\x02" + slh_msg[1:], sig_slh, context=SIG_CONTEXT)

            if ok_ver and ok_flip and ok_ctx and ok_role:
                results.append(SelftestItemResult(res_name, "crypto", "PASS"))
            else:
                results.append(
                    SelftestItemResult(res_name, "crypto", "FAIL", "Verification failed")
                )
        except (AethelError, KeyError, ValueError) as e:
            results.append(SelftestItemResult(res_name, "crypto", "FAIL", str(e)))

    return results


def _run_all_checks() -> list[SelftestItemResult]:
    """Execute all packaged selftest verification items."""
    yp_vecs, slh_vecs = _load_package_vectors()
    results: list[SelftestItemResult] = []
    results.extend(_check_unicode())
    results.extend(_check_ctf1(yp_vecs))
    results.extend(_check_manifests(yp_vecs))
    results.extend(_check_crypto(yp_vecs, slh_vecs))
    return results


def handle_selftest(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute selftest command."""
    results = _run_all_checks()
    passed_count = sum(1 for r in results if r.status == "PASS")
    failed_count = sum(1 for r in results if r.status == "FAIL")
    all_passed = failed_count == 0

    if ui.json_mode:
        doc = {
            "schema": "aethel.selftest/1",
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "profile": "pip-1",
                "yellow_paper": YELLOW_PAPER_VERSION,
            },
            "passed": all_passed,
            "tests_total": len(results),
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        sys.stdout.write("Selftest: Permanent Ink Protocol (PIP-1)\n")
        sys.stdout.write("-" * 70 + "\n")
        for r in results:
            detail_str = f" ({r.detail})" if r.detail else ""
            status_tag = f"[{r.status}]"
            sys.stdout.write(f"{status_tag:<8} {r.name:<26} {r.category:<16}{detail_str}\n")
        sys.stdout.write("-" * 70 + "\n")
        if all_passed:
            sys.stdout.write(f"All {len(results)} selftest checks passed.\n")
        else:
            sys.stdout.write(f"FAILED: {failed_count} of {len(results)} checks failed.\n")

    return 0 if all_passed else 1
