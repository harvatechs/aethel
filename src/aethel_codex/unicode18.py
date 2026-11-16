"""Unicode 18.0.0 validation, repertoire, and normalization (YP §4.3, §4.4, R-PROTO-08)."""

from typing import cast

import unicodedata2

from aethel_codex.errors import AethelError

UNICODE_VERSION: str = "18.0.0"


def check_unicode_version() -> None:
    """Verify that unicodedata2 provides Unicode 18.0.0 tables.

    Normative reference: Yellow Paper §4.4.

    Raises:
        AethelError: With code UNICODE_DATA_MISMATCH if the version does not match.
    """
    version = getattr(unicodedata2, "unidata_version", None)
    if version != UNICODE_VERSION:
        raise AethelError(
            "UNICODE_DATA_MISMATCH",
            f"Unicode data version mismatch: expected {UNICODE_VERSION}, got {version}",
        )


# Run version guard at import
check_unicode_version()


def is_forbidden(cp: int) -> bool:
    """Check if codepoint belongs to the forbidden set.

    Normative reference: Yellow Paper §4.3.
    """
    if cp <= 0x08:
        return True
    if cp in (0x0B, 0x0C):
        return True
    if 0x0E <= cp <= 0x1F:
        return True
    if 0x7F <= cp <= 0x9F:
        return True
    if cp == 0xFEFF:
        return True
    if 0xFDD0 <= cp <= 0xFDEF:
        return True
    return (cp & 0xFFFE) == 0xFFFE


def is_unassigned(cp: int) -> bool:
    """Check if codepoint is unassigned (General_Category == Cn).

    Normative reference: Yellow Paper §4.2 step 3, §4.3.
    """
    cat: str = unicodedata2.category(chr(cp))
    return cat == "Cn"


def compute_line_col(text: str, target_idx: int) -> tuple[int, int]:
    """Compute 1-based (line, column) in code points for index target_idx.

    Lines are split on LF, CR LF, or CR.
    """
    line = 1
    col = 1
    i = 0
    text_len = len(text)
    while i < target_idx:
        ch = text[i]
        if ch == "\r":
            line += 1
            col = 1
            if i + 1 < text_len and text[i + 1] == "\n":
                i += 1
        elif ch == "\n":
            line += 1
            col = 1
        else:
            col += 1
        i += 1
    return line, col


def find_forbidden(text: str) -> tuple[int, int, int] | None:
    """Find the first forbidden codepoint in text.

    Returns:
        (codepoint, line, column) or None if none found.
    """
    for idx, ch in enumerate(text):
        cp = ord(ch)
        if is_forbidden(cp):
            line, col = compute_line_col(text, idx)
            return cp, line, col
    return None


def find_unassigned(text: str) -> tuple[int, int, int] | None:
    """Find the first unassigned codepoint in text.

    Returns:
        (codepoint, line, column) or None if none found.
    """
    for idx, ch in enumerate(text):
        cp = ord(ch)
        if is_unassigned(cp):
            line, col = compute_line_col(text, idx)
            return cp, line, col
    return None


def nfc(text: str) -> str:
    """Normalize text to Unicode 18.0.0 NFC form.

    Normative reference: Yellow Paper §4.2 step 5.
    """
    return cast(str, unicodedata2.normalize("NFC", text))
