"""CLI handler for aethel explain (cli-spec.md §3, specs.md §14)."""

import argparse
import json
import sys
from typing import Any

from aethel_codex.cli.ui import UIContext
from aethel_codex.errors import ERROR_CODE_REGISTRY, ErrorCodeInfo

# Detailed diagnosis data for every registered error code (specs.md §14)
_EXPLAIN_DETAILS: dict[str, tuple[str, str, int]] = {
    # (usual_cause, what_to_do, typical_exit_code)
    "E_INVALID_UTF8": (
        "File is encoded in Latin-1, CP1252, UTF-16, or contains binary bytes.",
        "Convert the file to standard UTF-8 without byte-order mark before processing.",
        3,
    ),
    "E_FORBIDDEN_CODEPOINT": (
        (
            "Text contains C0/C1 control characters (except linefeed), "
            "lone surrogates, or noncharacters."
        ),
        "Remove control codes or replace them with standard spaces or Markdown formatting.",
        3,
    ),
    "E_UNASSIGNED_CODEPOINT": (
        "Code point has general category Cn (unassigned) in Unicode 18.0.0.",
        "Remove the unassigned code point or upgrade text to assigned characters.",
        3,
    ),
    "E_EMPTY_TEXT": (
        "Manuscript is zero bytes or consists entirely of ignored whitespace.",
        "Ensure the manuscript contains at least one non-empty line of content.",
        3,
    ),
    "E_FIELD_ORDER": (
        "Manifest fields do not appear in strict canonical order.",
        "Reorder manifest fields per PMF-1 specification (YP §7.2) or re-publish using aethel.",
        3,
    ),
    "E_BAD_LINES": (
        "Manifest contains invalid line endings (CRLF), trailing whitespace, or missing colons.",
        (
            "Ensure all manifest lines end with LF only, have no trailing whitespace, "
            "and follow key: value."
        ),
        3,
    ),
    "E_UNKNOWN_PROFILE": (
        "Profile field is not recognized by this version of aethel.",
        "Ensure the profile field is set to 'pip-1'.",
        3,
    ),
    "E_NOT_SORTED_OR_UNIQUE": (
        (
            "Repeated manifest fields (assets, parents, authors) are not strictly "
            "sorted or contain duplicates."
        ),
        "Sort repeated entries by UTF-8 bytes and remove duplicate lines.",
        3,
    ),
    "E_BAD_VALUE": (
        "Field value violates grammar, length, or character constraints.",
        "Check the field value syntax against the PMF-1 grammar specifications.",
        3,
    ),
    "E_INTEGER_RANGE": (
        "Integer value exceeds 2^64 - 1 or contains non-digit characters.",
        "Specify an integer value within the valid range 0 to 18446744073709551615.",
        3,
    ),
    "E_BAD_MAGIC": (
        "Manifest does not begin with the required magic header line.",
        "Ensure the first line of the manifest is 'pip-manifest 1'.",
        3,
    ),
    "E_UNKNOWN_KEY": (
        "Manifest contains an unrecognized field key.",
        "Remove unknown or experimental field keys from manifest.pip.",
        3,
    ),
    "E_MISSING_FIELD": (
        "A mandatory manifest field (profile, markup, lang, title, license, text) is missing.",
        "Supply all mandatory fields required by the PMF-1 specification.",
        3,
    ),
    "E_WORK_PARENT_RULE": (
        "Manifest specifies 'work' without 'parent', or 'parent' without 'work'.",
        "Include both 'work' and 'parent' for revisions, or omit both for genesis publications.",
        3,
    ),
    "E_ROUNDTRIP": (
        "Re-serialized manifest does not match input bytes byte-for-byte.",
        "Publish the bundle using aethel publish to ensure canonical serialization.",
        3,
    ),
    "MANIFEST_INVALID": (
        "manifest.pip failed strict PMF-1 grammar parsing during verification check V1.",
        "Inspect manifest.pip using `aethel inspect` and fix syntax errors.",
        1,
    ),
    "ID_MISMATCH": (
        "Computed manifest Merkle digest does not match the bundle directory name.",
        "Rename the directory to match the computed manifest ID or check for manifest tampering.",
        1,
    ),
    "TEXT_NOT_CANONICAL": (
        "Manuscript text file on disk is not identical to its CTF-1 canonical output.",
        "Re-canonicalize text using `aethel canon` or restore the original text file.",
        1,
    ),
    "TEXT_LENGTH": (
        "Text file byte length on disk does not match declared manifest length.",
        "Check if the text file was truncated, corrupted, or replaced after publishing.",
        1,
    ),
    "TEXT_MISMATCH": (
        "Computed text Merkle root PID does not match declared text PID in manifest.",
        "Restore original manuscript text or re-publish bundle with updated text.",
        1,
    ),
    "ASSET_MISSING": (
        "Declared asset file was not found on disk in the assets/ directory.",
        "Ensure all declared assets are placed in the assets/ directory with matching names.",
        1,
    ),
    "ASSET_MISMATCH": (
        "Asset file content or byte length does not match declared asset PID.",
        "Restore the original asset file or verify if file content was modified.",
        1,
    ),
    "ASSET_EXTRA": (
        "Unlisted file exists in the assets/ directory.",
        "Remove undeclared files from the assets/ directory.",
        0,
    ),
    "CITE_UNLISTED": (
        "Inline citation URI in manuscript text is not listed in manifest cites declarations.",
        "Add the cited PID to the manifest with `--cite` or remove the inline citation from text.",
        0,
    ),
    "CITE_LOCATOR_INVALID": (
        "Citation byte locator range is invalid for the cited target blob.",
        "Check that citation offsets fall on UTF-8 character boundaries and within blob length.",
        0,
    ),
    "WORK_MISMATCH": (
        "Child bundle and parent bundle do not share the same work identifier.",
        "Ensure the child bundle references a parent belonging to the same work lineage.",
        1,
    ),
    "SIG_INVALID": (
        "Cryptographic signature does not verify against manifest digest.",
        "Verify if manifest was tampered with after signing, or if signature file is corrupted.",
        1,
    ),
    "KEY_MISMATCH": (
        "Public key in signature envelope does not hash to declared key identifier.",
        "Check for envelope tampering or mismatch between key ID and public key bytes.",
        1,
    ),
    "ALG_UNKNOWN": (
        "Signature envelope specifies an algorithm not permitted by pip-1 profile.",
        (
            "Use one of the four supported algorithms: ml-dsa-87, ml-dsa-65, "
            "slh-dsa-sha2-256s, slh-dsa-shake-256s."
        ),
        1,
    ),
    "BEACON_FAILED": (
        "Randomness beacon verification failed against referenced randomness source.",
        "Verify beacon round number and output value against source.",
        1,
    ),
    "ATT_FAILED": (
        "Attestation proof verification failed.",
        "Verify attestation signature and proof structure.",
        1,
    ),
    "MANIFEST_MISSING": (
        "manifest.pip file was not found in the bundle root directory.",
        "Ensure manifest.pip exists in the specified bundle directory.",
        5,
    ),
    "TEXT_MISSING": (
        "Manuscript text file matching manifest markup was not found in bundle.",
        "Ensure text.md, text.tex, or text.txt exists in the bundle directory.",
        5,
    ),
    "ENVELOPE_INVALID": (
        "Signature or attestation envelope failed strict parsing.",
        "Re-create the signature envelope using `aethel sign`.",
        1,
    ),
    "UNSAFE_PATH": (
        "Bundle entry is a symlink, hard link, or points outside the bundle directory.",
        "Replace symlinks with regular files and ensure relative paths do not escape bundle root.",
        1,
    ),
    "EXTRA_FILE": (
        "Unrecognized file found in bundle root or signatures directory.",
        "Remove unrecognized files from the bundle directory.",
        0,
    ),
    "CITE_SYNTAX": (
        "Citation URI syntax is malformed or invalid.",
        "Format citation URI according to PIP-1 citation grammar.",
        3,
    ),
    "CITE_RANGE": (
        "Citation locator range falls outside target blob bounds.",
        "Ensure start offset is less than end offset and within target blob size.",
        3,
    ),
    "PID_SYNTAX": (
        "Permanent Ink Protocol identifier does not match pip1:<type>:<hex> grammar.",
        (
            "Check that PID prefix is pip1: followed by single lowercase letter "
            "and 64-character lowercase hex."
        ),
        3,
    ),
    "NO_PARENTS": (
        "Genesis manifest does not reference parent bundles.",
        "Expected status for genesis publications.",
        0,
    ),
    "PARENTS_UNAVAILABLE": (
        "Parent bundles were not provided to verify revision history.",
        "Provide parent bundle directory via `--parents DIR` flag.",
        0,
    ),
    "NO_SIGNATURES": (
        "Bundle does not contain any signature envelopes.",
        "Sign the bundle using `aethel sign` if author attribution is required.",
        0,
    ),
    "NO_TIME_EVIDENCE": (
        "Bundle carries neither randomness beacon nor time attestations.",
        "Normal status when no beacon was declared during publishing.",
        0,
    ),
    "BEACON_UNVERIFIED": (
        "Randomness beacon is present in manifest but unverified.",
        "Verify beacon externally against the randomness beacon provider.",
        0,
    ),
    "ATT_UNVERIFIED": (
        "Attestation proof is present but unverified.",
        "Verify attestation proof externally against the attestation authority.",
        0,
    ),
    "DEPENDS_ON_V1": (
        "Verification check was skipped because check V1 (Manifest) failed.",
        "Fix manifest errors to allow subsequent verification checks to run.",
        1,
    ),
    "LIMIT_EXCEEDED": (
        "Bundle exceeds configured size, entry, or signature resource limits.",
        "Increase verification resource caps using `--max-text-bytes` or `--max-asset-bytes`.",
        6,
    ),
    "KEYFILE_INVALID": (
        "Key file format is invalid, corrupted, or not valid UTF-8.",
        "Ensure key file is a valid AKF-1 format file.",
        4,
    ),
    "KEYFILE_PERMISSIONS": (
        "Key file permissions are wider than 0600 on a POSIX filesystem.",
        "Run `chmod 600 <keyfile>` to restrict permissions to the file owner.",
        4,
    ),
    "KEYFILE_PASSPHRASE": (
        "Passphrase entered does not decrypt the encrypted key file.",
        "Check that you entered the correct passphrase for this key file.",
        4,
    ),
    "BACKEND_ERROR": (
        "Underlying cryptographic backend library encountered an error.",
        "Verify that cryptography and pqcrypto packages are installed correctly.",
        4,
    ),
    "UNICODE_DATA_MISMATCH": (
        "Installed unicodedata2 tables do not match Unicode 18.0.0.",
        "Ensure unicodedata2 version 18.0.0 is installed in your Python environment.",
        70,
    ),
}


def _format_explain_dict(info: ErrorCodeInfo) -> dict[str, Any]:
    code = info.code
    details = _EXPLAIN_DETAILS.get(
        code,
        ("Error condition detected during execution.", "Consult protocol specification.", 3),
    )
    origin = "Yellow Paper normative" if info.source == "Y" else "Pack defined"
    return {
        "code": code,
        "meaning": info.meaning,
        "cause": details[0],
        "what_to_do": details[1],
        "yp_section": info.yp_section,
        "origin": origin,
        "exit_code": details[2],
    }


def handle_explain(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute explain command."""
    if getattr(args, "list_codes", False):
        if ui.json_mode:
            all_codes = [_format_explain_dict(info) for info in ERROR_CODE_REGISTRY.values()]
            doc = {"schema": "aethel.explain_list/1", "codes": all_codes}
            sys.stdout.write(json.dumps(doc, indent=2) + "\n")
        else:
            sys.stdout.write("Registered error codes (specs.md §14):\n\n")
            for code, info in sorted(ERROR_CODE_REGISTRY.items()):
                sys.stdout.write(f"  {code:<24} [{info.source}] {info.meaning}\n")
        return 0

    target_code = getattr(args, "code", None)
    if not target_code:
        sys.stderr.write("error: missing error code. Run `aethel explain --list` to view codes.\n")
        return 2

    clean_code = target_code.strip()
    if clean_code not in ERROR_CODE_REGISTRY:
        sys.stderr.write(
            f"error: unknown error code: {clean_code!r}. "
            "Run `aethel explain --list` or see specs.md §14.\n"
        )
        return 2

    info = ERROR_CODE_REGISTRY[clean_code]
    data = _format_explain_dict(info)

    if ui.json_mode:
        doc = {"schema": "aethel.explain/1", **data}
        sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    else:
        dot = ui.dot()
        sys.stdout.write(
            f"Code:        {data['code']} {dot} {data['origin']} ({data['yp_section']})\n"
        )
        sys.stdout.write(f"Meaning:     {data['meaning']}\n")
        sys.stdout.write(f"Usual cause: {data['cause']}\n")
        sys.stdout.write(f"What to do:  {data['what_to_do']}\n")

    return 0
