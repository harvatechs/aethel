#!/usr/bin/env python3
"""Minimal independent PIP-1 bundle verifier (stdlib only).

Normative reference: Yellow Paper PIP-YP-1 v1.0.0-rc.3, ADR-013.
Checks hash integrity V1-V3:
- V1: Manifest syntax, key ordering, directory name match, and manifest ID.
- V2: Text file existence, length, Merkle blob ID, and basic canonical checks.
      (Per ADR-013, the Unicode 18.0.0 repertoire check is marked not performed).
- V3: Asset files existence, lengths, and Merkle blob IDs.

This script uses ONLY the Python standard library. It does not import
aethel_codex, unicodedata2, cryptography, or pqcrypto.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any

LABEL_MANIFEST = b"pip1.manifest"
LABEL_TEXT = b"pip1.text"
LABEL_ASSET = b"pip1.asset"
LABEL_LEAF = b"pip1.leaf"
LABEL_NODE = b"pip1.node"
CHUNK_SIZE = 4096

_MARKUP_EXTENSIONS: dict[str, str] = {
    "pip-md-1": "text.md",
    "pip-tex-1": "text.tex",
    "pip-txt-1": "text.txt",
}

_MANIFEST_KEY_ORDER = [
    "profile",
    "markup",
    "lang",
    "title",
    "license",
    "beacon",
    "text",
    "work",
    "parent",
    "author",
    "derivative",
    "asset",
    "cite",
]

_SINGLETON_KEYS = {"profile", "markup", "lang", "title", "license", "beacon", "text", "work"}
_MANDATORY_KEYS = {"profile", "markup", "lang", "title", "license", "text"}

_PID_RE = re.compile(r"pip1:([mtak]):([0-9a-f]{64})")


def H(label: bytes, data: bytes) -> bytes:  # noqa: N802
    """Domain-separated SHA3-256 hash: H(label, x) = SHA3-256(u8(len) || label || x)."""
    if len(label) > 255:
        raise ValueError("Hash label exceeds 255 bytes")
    return hashlib.sha3_256(bytes([len(label)]) + label + data).digest()


def merkle_leaf(chunk: bytes) -> bytes:
    """Leaf hash: H(LABEL_LEAF, chunk)."""
    return H(LABEL_LEAF, chunk)


def merkle_node(left: bytes, right: bytes) -> bytes:
    """Interior node hash: H(LABEL_NODE, left || right)."""
    return H(LABEL_NODE, left + right)


def merkle_root(leaves: list[bytes]) -> bytes:
    """Recursive Merkle root calculation (YP §5.2)."""
    n = len(leaves)
    if n == 0:
        raise ValueError("Leaves cannot be empty")
    if n == 1:
        return leaves[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return merkle_node(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def compute_blob_id(label: bytes, data: bytes) -> str:
    """Compute 64-hex blob identifier digest: H(label, u64be(len) || MerkleRoot)."""
    if not data:
        chunks = [b""]
    else:
        chunks = [data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
    leaves = [merkle_leaf(c) for c in chunks]
    root = merkle_root(leaves)
    prefix = struct.pack(">Q", len(data))
    return H(label, prefix + root).hex()


def _is_safe_regular_file(path: Path) -> bool:
    """Check that a path exists, is a regular file, and is not a symlink."""
    try:
        st = os.lstat(path)
        return not os.path.islink(path) and (st.st_mode & 0o170000 == 0o100000)
    except OSError:
        return False


_PROFILE_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.-]*")
_LANG_RE = re.compile(r"[a-z]{2,3}(-([A-Z][a-z]{3}|[A-Z]{2}|[0-9]{3}|[a-z0-9]{2,8}))*")
_UINT_RE = re.compile(r"0|[1-9][0-9]*")
_BEACON_BSRC_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_BEACON_BVAL_RE = re.compile(r"([0-9a-f]{2}){1,64}")
_DERIVATIVE_KINDS = {"translation", "adaptation", "anthology", "commentary"}
_ASSET_ANAME_RE = re.compile(r"(?!\.{1,2}\Z)[A-Za-z0-9._-]{1,128}")
_ASSET_MEDIA_RE = re.compile(r"[a-z0-9][a-z0-9!#$&+\-.^_]{0,126}/[a-z0-9][a-z0-9!#$&+\-.^_]{0,126}")
_MAX_UINT64 = 18446744073709551615


def _validate_value_text(val: str, max_bytes: int) -> bool:
    """Validate value text field per YP §7.4."""
    b = val.encode("utf-8")
    if not (1 <= len(b) <= max_bytes):
        return False
    if val.startswith(" ") or val.endswith(" "):
        return False
    return not any(c in val for c in ("\t", "\r", "\n", "\0"))


def _parse_uint(val: str) -> int | None:
    if not _UINT_RE.fullmatch(val):
        return None
    n = int(val)
    if n > _MAX_UINT64:
        return None
    return n


def _parse_manifest_minimal(  # noqa: C901
    raw_bytes: bytes,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Strictly parse manifest bytes, returning (parsed_dict, error_code, error_detail)."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, "MANIFEST_INVALID", f"Invalid UTF-8: {e}"

    if "\r" in text:
        return None, "MANIFEST_INVALID", "Carriage return in manifest"
    if not text.endswith("\n"):
        return None, "MANIFEST_INVALID", "Manifest must end with newline"
    if text == "\n":
        return None, "MANIFEST_INVALID", "Empty manifest"

    lines = text.split("\n")[:-1]
    if not lines or lines[0] != "pip-manifest 1":
        return None, "MANIFEST_INVALID", "Invalid magic header"

    seen_keys: set[str] = set()
    last_rank = -1
    parsed: dict[str, Any] = {
        "profile": None,
        "markup": None,
        "lang": None,
        "title": None,
        "license": None,
        "beacon": None,
        "text_pid": None,
        "text_length": None,
        "work": None,
        "parents": [],
        "authors": [],
        "derivatives": [],
        "assets": [],
        "cites": [],
    }

    parent_lines: list[str] = []
    author_lines: list[str] = []
    derivative_lines: list[str] = []
    asset_names: list[str] = []
    cite_lines: list[str] = []

    for line_idx, line in enumerate(lines[1:], start=2):
        if not line:
            return None, "MANIFEST_INVALID", f"Empty line at {line_idx}"
        parts = line.split(" ", 1)
        if len(parts) != 2:
            return None, "MANIFEST_INVALID", f"Malformed line {line_idx}: no space"
        key, val = parts[0], parts[1]

        if key not in _MANIFEST_KEY_ORDER:
            return None, "MANIFEST_INVALID", f"Unknown key {key!r} at line {line_idx}"

        rank = _MANIFEST_KEY_ORDER.index(key)
        if key in _SINGLETON_KEYS:
            if key in seen_keys:
                return None, "MANIFEST_INVALID", f"Duplicate singleton key {key!r}"
            if rank < last_rank:
                return None, "MANIFEST_INVALID", f"Key out of order {key!r} at line {line_idx}"
        else:
            if rank < last_rank:
                return None, "MANIFEST_INVALID", f"Key out of order {key!r} at line {line_idx}"

        seen_keys.add(key)
        last_rank = rank

        # Specific field validation
        if key == "profile":
            if val != "pip-1":
                return None, "MANIFEST_INVALID", f"Unknown profile: {val!r}"
            parsed["profile"] = val
        elif key == "markup":
            if val not in ("pip-md-1", "pip-tex-1", "pip-txt-1"):
                return None, "MANIFEST_INVALID", f"Invalid markup: {val!r}"
            parsed["markup"] = val
        elif key == "lang":
            if len(val.encode("utf-8")) > 35 or not _LANG_RE.fullmatch(val):
                return None, "MANIFEST_INVALID", f"Invalid language tag: {val!r}"
            parsed["lang"] = val
        elif key == "title":
            if not _validate_value_text(val, 512):
                return None, "MANIFEST_INVALID", f"Invalid title: {val!r}"
            parsed["title"] = val
        elif key == "license":
            if not _validate_value_text(val, 256):
                return None, "MANIFEST_INVALID", f"Invalid license: {val!r}"
            parsed["license"] = val
        elif key == "beacon":
            bparts = val.split(" ")
            if len(bparts) != 3:
                return None, "MANIFEST_INVALID", "Invalid beacon format"
            bsrc, bseq_str, bval = bparts
            if not _BEACON_BSRC_RE.fullmatch(bsrc) or not _BEACON_BVAL_RE.fullmatch(bval):
                return None, "MANIFEST_INVALID", "Invalid beacon value"
            if _parse_uint(bseq_str) is None:
                return None, "MANIFEST_INVALID", "Invalid beacon sequence"
            parsed["beacon"] = val
        elif key == "text":
            m_parts = val.split(" ")
            if len(m_parts) != 2:
                return None, "MANIFEST_INVALID", "Invalid text line"
            t_pid_m = _PID_RE.fullmatch(m_parts[0])
            if not t_pid_m or t_pid_m.group(1) != "t":
                return None, "MANIFEST_INVALID", f"Invalid text PID: {m_parts[0]!r}"
            t_len = _parse_uint(m_parts[1])
            if t_len is None or t_len < 1:
                return None, "MANIFEST_INVALID", f"Invalid text length: {m_parts[1]!r}"
            parsed["text_pid"] = m_parts[0]
            parsed["text_length"] = t_len
        elif key == "work":
            w_pid_m = _PID_RE.fullmatch(val)
            if not w_pid_m or w_pid_m.group(1) != "m":
                return None, "MANIFEST_INVALID", f"Invalid work PID: {val!r}"
            parsed["work"] = val
        elif key == "parent":
            p_pid_m = _PID_RE.fullmatch(val)
            if not p_pid_m or p_pid_m.group(1) != "m":
                return None, "MANIFEST_INVALID", f"Invalid parent PID: {val!r}"
            parent_lines.append(val)
            parsed["parents"].append(val)
        elif key == "author":
            a_pid_m = _PID_RE.fullmatch(val)
            if not a_pid_m or a_pid_m.group(1) != "k":
                return None, "MANIFEST_INVALID", f"Invalid author PID: {val!r}"
            author_lines.append(val)
            parsed["authors"].append(val)
        elif key == "derivative":
            dparts = val.split(" ")
            if len(dparts) != 2:
                return None, "MANIFEST_INVALID", f"Invalid derivative line: {val!r}"
            dkind, dpid = dparts
            if dkind not in _DERIVATIVE_KINDS:
                return None, "MANIFEST_INVALID", f"Invalid derivative kind: {dkind!r}"
            d_pid_m = _PID_RE.fullmatch(dpid)
            if not d_pid_m or d_pid_m.group(1) != "m":
                return None, "MANIFEST_INVALID", f"Invalid derivative PID: {dpid!r}"
            derivative_lines.append(val)
            parsed["derivatives"].append(val)
        elif key == "asset":
            # format: aname SP pip1:a:<64hex> SP uint SP media
            a_parts = val.split(" ")
            if len(a_parts) != 4:
                return None, "MANIFEST_INVALID", f"Invalid asset line at {line_idx}"
            aname = a_parts[0]
            if not _ASSET_ANAME_RE.fullmatch(aname):
                return None, "MANIFEST_INVALID", f"Invalid asset name: {aname!r}"
            a_pid_m = _PID_RE.fullmatch(a_parts[1])
            if not a_pid_m or a_pid_m.group(1) != "a":
                return None, "MANIFEST_INVALID", f"Invalid asset PID: {a_parts[1]!r}"
            a_len = _parse_uint(a_parts[2])
            if a_len is None:
                return None, "MANIFEST_INVALID", f"Invalid asset length: {a_parts[2]!r}"
            media = a_parts[3]
            if not _ASSET_MEDIA_RE.fullmatch(media):
                return None, "MANIFEST_INVALID", f"Invalid asset media type: {media!r}"
            asset_names.append(aname)
            parsed["assets"].append({"name": aname, "pid": a_parts[1], "length": a_len})
        elif key == "cite":
            c_pid_m = _PID_RE.fullmatch(val)
            if not c_pid_m or c_pid_m.group(1) not in ("m", "t", "a"):
                return None, "MANIFEST_INVALID", f"Invalid cite PID: {val!r}"
            cite_lines.append(val)
            parsed["cites"].append(val)

    # Check mandatory keys
    for mk in _MANDATORY_KEYS:
        if mk not in seen_keys:
            return None, "MANIFEST_INVALID", f"Missing mandatory key: {mk!r}"

    # Work / Parent co-occurrence rule
    has_work = "work" in seen_keys
    has_parent = "parent" in seen_keys
    if has_work != has_parent:
        return None, "MANIFEST_INVALID", "Work requires parent and vice versa"

    # Sorted and unique checks on repeated fields
    for field_name, lines_list in (
        ("parent", parent_lines),
        ("author", author_lines),
        ("derivative", derivative_lines),
        ("cite", cite_lines),
    ):
        if lines_list:
            encoded_list = [line_item.encode("utf-8") for line_item in lines_list]
            if encoded_list != sorted(encoded_list) or len(set(encoded_list)) != len(encoded_list):
                return None, "MANIFEST_INVALID", f"{field_name} lines must be sorted and unique"

    if asset_names and (
        asset_names != sorted(asset_names) or len(set(asset_names)) != len(asset_names)
    ):
        return None, "MANIFEST_INVALID", "asset lines must be sorted and unique by name"

    return parsed, None, None


def verify_bundle_minimal(bundle_dir: str | Path) -> dict[str, Any]:  # noqa: C901
    """Execute independent V1-V3 verification on bundle_dir."""
    bpath = Path(bundle_dir)
    dir_name = bpath.name

    result: dict[str, Any] = {
        "bundle": str(bpath),
        "v1": {"status": "PASS", "code": None, "detail": None},
        "v2": {"status": "PASS", "code": None, "detail": None},
        "v3": {"status": "PASS", "code": None, "detail": None},
        "integrity": "PASS",
    }

    manifest_file = bpath / "manifest.pip"
    if not manifest_file.exists():
        result["v1"] = {
            "status": "FAIL",
            "code": "MANIFEST_MISSING",
            "detail": "manifest.pip not found",
        }
        result["v2"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["v3"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["integrity"] = "FAIL"
        return result

    if not _is_safe_regular_file(manifest_file):
        result["v1"] = {
            "status": "FAIL",
            "code": "UNSAFE_PATH",
            "detail": "manifest.pip is not a regular file",
        }
        result["v2"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["v3"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["integrity"] = "FAIL"
        return result

    try:
        manifest_bytes = manifest_file.read_bytes()
    except OSError as e:
        result["v1"] = {"status": "FAIL", "code": "MANIFEST_MISSING", "detail": str(e)}
        result["v2"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["v3"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["integrity"] = "FAIL"
        return result

    parsed_manifest, err_code, err_detail = _parse_manifest_minimal(manifest_bytes)
    if parsed_manifest is None:
        result["v1"] = {
            "status": "FAIL",
            "code": err_code or "MANIFEST_INVALID",
            "detail": err_detail,
        }
        result["v2"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["v3"] = {"status": "SKIPPED", "code": "DEPENDS_ON_V1", "detail": None}
        result["integrity"] = "FAIL"
        return result

    manifest_digest = H(LABEL_MANIFEST, manifest_bytes).hex()

    # If directory name is 64 hex characters, verify ID match
    is_hex_dir = bool(re.fullmatch(r"[0-9a-f]{64}", dir_name))
    if is_hex_dir and dir_name != manifest_digest:
        result["v1"] = {
            "status": "FAIL",
            "code": "ID_MISMATCH",
            "detail": f"Directory {dir_name} != {manifest_digest}",
        }
        result["integrity"] = "FAIL"

    # --------------------------------------------------------------------------
    # V2: Text Check
    # --------------------------------------------------------------------------
    expected_text_filename = _MARKUP_EXTENSIONS.get(parsed_manifest["markup"], "text.txt")
    text_file = bpath / expected_text_filename

    if not text_file.exists():
        result["v2"] = {
            "status": "FAIL",
            "code": "TEXT_MISSING",
            "detail": f"{expected_text_filename} not found",
        }
        result["integrity"] = "FAIL"
    elif not _is_safe_regular_file(text_file):
        result["v2"] = {
            "status": "FAIL",
            "code": "UNSAFE_PATH",
            "detail": f"{expected_text_filename} unsafe",
        }
        result["integrity"] = "FAIL"
    else:
        try:
            text_bytes = text_file.read_bytes()
        except OSError as e:
            result["v2"] = {"status": "FAIL", "code": "TEXT_MISSING", "detail": str(e)}
            result["integrity"] = "FAIL"
            text_bytes = None

        if text_bytes is not None:
            if len(text_bytes) != parsed_manifest["text_length"]:
                result["v2"] = {
                    "status": "FAIL",
                    "code": "TEXT_LENGTH",
                    "detail": f"Length {len(text_bytes)} != declared",
                }
                result["integrity"] = "FAIL"
            else:
                # Basic canonical checks without external unicodedata2
                if b"\r" in text_bytes:
                    result["v2"] = {
                        "status": "FAIL",
                        "code": "TEXT_NOT_CANONICAL",
                        "detail": "CR in text",
                    }
                    result["integrity"] = "FAIL"
                elif text_bytes and not text_bytes.endswith(b"\n"):
                    result["v2"] = {
                        "status": "FAIL",
                        "code": "TEXT_NOT_CANONICAL",
                        "detail": "No trailing newline",
                    }
                    result["integrity"] = "FAIL"
                else:
                    computed_tid = f"pip1:t:{compute_blob_id(LABEL_TEXT, text_bytes)}"
                    if computed_tid != parsed_manifest["text_pid"]:
                        result["v2"] = {
                            "status": "FAIL",
                            "code": "TEXT_MISMATCH",
                            "detail": f"{computed_tid} != {parsed_manifest['text_pid']}",
                        }
                        result["integrity"] = "FAIL"

    # Check for extra text.* files
    for ext_name in ("text.md", "text.tex", "text.txt"):
        if (
            ext_name != expected_text_filename
            and (bpath / ext_name).exists()
            and result["v2"]["status"] == "PASS"
        ):
            result["v2"] = {
                "status": "WARN",
                "code": "EXTRA_FILE",
                "detail": f"Extra text file {ext_name}",
            }

    # --------------------------------------------------------------------------
    # V3: Assets Check
    # --------------------------------------------------------------------------
    assets_dir = bpath / "assets"
    v3_fail = False
    v3_fail_code = None
    v3_fail_detail = None

    for asset_entry in parsed_manifest["assets"]:
        aname = asset_entry["name"]
        a_file = assets_dir / aname
        if not a_file.exists():
            v3_fail = True
            v3_fail_code = v3_fail_code or "ASSET_MISSING"
            v3_fail_detail = v3_fail_detail or f"Asset {aname} not found"
            continue

        if not _is_safe_regular_file(a_file):
            v3_fail = True
            v3_fail_code = v3_fail_code or "UNSAFE_PATH"
            v3_fail_detail = v3_fail_detail or f"Asset {aname} unsafe path"
            continue

        try:
            a_bytes = a_file.read_bytes()
        except OSError as e:
            v3_fail = True
            v3_fail_code = v3_fail_code or "ASSET_MISSING"
            v3_fail_detail = v3_fail_detail or str(e)
            continue

        if len(a_bytes) != asset_entry["length"]:
            v3_fail = True
            v3_fail_code = v3_fail_code or "ASSET_MISMATCH"
            v3_fail_detail = v3_fail_detail or f"Asset {aname} length mismatch"
            continue

        computed_aid = f"pip1:a:{compute_blob_id(LABEL_ASSET, a_bytes)}"
        if computed_aid != asset_entry["pid"]:
            v3_fail = True
            v3_fail_code = v3_fail_code or "ASSET_MISMATCH"
            v3_fail_detail = v3_fail_detail or f"Asset {aname} ID mismatch"
            continue

    if v3_fail:
        result["v3"] = {"status": "FAIL", "code": v3_fail_code, "detail": v3_fail_detail}
    else:
        # Check for unlisted extra files in assets/
        if assets_dir.is_dir():
            declared_names = {a["name"] for a in parsed_manifest["assets"]}
            for entry in assets_dir.iterdir():
                if entry.name not in declared_names and entry.is_file():
                    result["v3"] = {
                        "status": "WARN",
                        "code": "ASSET_EXTRA",
                        "detail": f"Unlisted asset {entry.name}",
                    }
                    break

    if any(result[k]["status"] == "FAIL" for k in ("v1", "v2", "v3")):
        result["integrity"] = "FAIL"
    else:
        result["integrity"] = "PASS"

    return result


def main() -> int:
    """CLI entrypoint for independent minimal verifier."""
    parser = argparse.ArgumentParser(
        description="Minimal independent PIP-1 bundle verifier (stdlib only)."
    )
    parser.add_argument("bundle", help="Path to PIP-1 bundle directory")
    parser.add_argument("--json", action="store_true", help="Output verification report in JSON")
    args = parser.parse_args()

    report = verify_bundle_minimal(args.bundle)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Bundle: {report['bundle']}")
        print(
            f"  V1 Manifest: {report['v1']['status']}"
            + (f" ({report['v1']['code']})" if report["v1"]["code"] else "")
        )
        print(
            f"  V2 Text:     {report['v2']['status']}"
            + (f" ({report['v2']['code']})" if report["v2"]["code"] else "")
        )
        print(
            f"  V3 Assets:   {report['v3']['status']}"
            + (f" ({report['v3']['code']})" if report["v3"]["code"] else "")
        )
        print(f"  Integrity:   {report['integrity']}")
        print("  Note: Unicode 18.0.0 repertoire check not performed (ADR-013)")

    return 0 if report["integrity"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
