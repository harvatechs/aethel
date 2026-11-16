"""Canonical Text Form 1 (CTF-1) implementation (YP §4, specs.md §4)."""

from dataclasses import dataclass

from aethel_codex.errors import CanonicalizationError
from aethel_codex.unicode18 import find_forbidden, find_unassigned, nfc


@dataclass(frozen=True)
class CanonReport:
    """Report detailing normalization changes applied by CTF-1."""

    input_bytes: int
    output_bytes: int
    bom_removed: bool
    crlf_converted: int
    lone_cr_converted: int
    nfc_changed: bool
    final_lf_added: bool


def canonicalize(data: bytes) -> tuple[bytes, CanonReport]:
    """Apply CTF-1 canonicalization to manuscript bytes.

    Normative reference: Yellow Paper §4.2.

    Args:
        data: Raw manuscript input bytes.

    Returns:
        Tuple of (canonical_bytes, CanonReport).

    Raises:
        CanonicalizationError: If text is invalid UTF-8, contains forbidden or unassigned
            characters, or canonicalizes to empty text.
    """
    orig_len = len(data)
    bom_removed = data.startswith(b"\xef\xbb\xbf")
    if bom_removed:
        data = data[3:]

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        offset = e.start + (3 if bom_removed else 0)
        raise CanonicalizationError(
            "E_INVALID_UTF8",
            f"Invalid UTF-8 sequence at byte offset {offset}",
            offset=offset,
        ) from None

    # Precedence: check forbidden over whole text first, then unassigned (U-6, Q-01)
    forb = find_forbidden(text)
    if forb is not None:
        cp, line, col = forb
        raise CanonicalizationError(
            "E_FORBIDDEN_CODEPOINT",
            f"Forbidden scalar value U+{cp:04X} at line {line}, column {col}",
            codepoint=f"U+{cp:04X}",
            line=line,
            column=col,
        )

    unassigned = find_unassigned(text)
    if unassigned is not None:
        cp, line, col = unassigned
        raise CanonicalizationError(
            "E_UNASSIGNED_CODEPOINT",
            f"Unassigned scalar value U+{cp:04X} at line {line}, column {col}",
            codepoint=f"U+{cp:04X}",
            line=line,
            column=col,
        )

    # Line terminators
    crlf_count = text.count("\r\n")
    lone_cr_count = text.count("\r") - crlf_count
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # NFC Normalization
    normalized = nfc(text)
    nfc_changed = normalized != text

    # Empty text rejection
    if not normalized:
        raise CanonicalizationError(
            "E_EMPTY_TEXT", "Manuscript text is empty after canonicalization"
        )

    # Final line feed
    final_lf_added = not normalized.endswith("\n")
    if final_lf_added:
        normalized += "\n"

    out_bytes = normalized.encode("utf-8")
    report = CanonReport(
        input_bytes=orig_len,
        output_bytes=len(out_bytes),
        bom_removed=bom_removed,
        crlf_converted=crlf_count,
        lone_cr_converted=lone_cr_count,
        nfc_changed=nfc_changed,
        final_lf_added=final_lf_added,
    )
    return out_bytes, report
