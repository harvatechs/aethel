"""Comprehensive edge corpus testing for Unicode 18.0.0 and CTF-1 (YP §4, A.1)."""

from __future__ import annotations

import pytest

from aethel_codex.ctf1 import canonicalize
from aethel_codex.errors import CanonicalizationError
from aethel_codex.unicode18 import is_unassigned


@pytest.mark.conformance
def test_banned_controls_and_separators() -> None:
    """Verify that all banned C0, C1 controls and noncharacters per YP §4.3 are rejected."""
    # NUL (0x00)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"hello\x00world\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # Bell (0x07)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"bell\x07sound\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # Form Feed (U+000C)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"page1\x0cpage2\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # ESC (U+001B)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"\x1b[31mRed\x1b[0m\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # DEL (U+007F)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"delete\x7fchar\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # NEL (Next Line, U+0085)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("line1\u0085line2\n".encode("utf-8"))
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # C1 boundary (U+009F)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("end\u009fctrl\n".encode("utf-8"))
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"


@pytest.mark.conformance
def test_noncharacters_and_surrogates() -> None:
    """Verify that noncharacters and surrogate halves are strictly rejected."""
    # Noncharacters: U+FDD0
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("text\ufdd0\n".encode("utf-8"))
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # Noncharacters: U+FFFE, U+FFFF
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("text\ufffe\n".encode("utf-8"))
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("text\uffff\n".encode("utf-8"))
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"

    # Invalid UTF-8 encoding of surrogate half (e.g. U+D800: ED A0 80)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"\xed\xa0\x80\n")
    assert exc.value.code == "E_INVALID_UTF8"


@pytest.mark.conformance
def test_unassigned_codepoints() -> None:
    """Verify that unassigned codepoints in Unicode 18.0.0 are rejected."""
    # U+0378 is unassigned in Unicode 18.0.0
    assert is_unassigned(0x0378)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("test\u0378\n".encode("utf-8"))
    assert exc.value.code == "E_UNASSIGNED_CODEPOINT"


@pytest.mark.conformance
def test_multiple_boms_and_empty_text() -> None:
    """Verify multiple BOMs and empty text handling."""
    # Empty input
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"")
    assert exc.value.code == "E_EMPTY_TEXT"

    # Single BOM only (canonicalizes to empty text)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"\xef\xbb\xbf")
    assert exc.value.code == "E_EMPTY_TEXT"

    # Double BOM: first is stripped, second remains (U+FEFF is forbidden if not initial BOM)
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(b"\xef\xbb\xbf\xef\xbb\xbfhello\n")
    assert exc.value.code == "E_FORBIDDEN_CODEPOINT"


@pytest.mark.conformance
def test_line_ending_permutations() -> None:
    """Verify canonicalization of all valid line ending permutations."""
    # CRLF converted to LF
    out1, rep1 = canonicalize(b"Line 1\r\nLine 2\r\n")
    assert out1 == b"Line 1\nLine 2\n"
    assert rep1.crlf_converted == 2

    # Lone CR converted to LF
    out2, rep2 = canonicalize(b"Line 1\rLine 2\r")
    assert out2 == b"Line 1\nLine 2\n"
    assert rep2.lone_cr_converted == 2

    # Missing trailing newline is appended
    out3, rep3 = canonicalize(b"No trailing newline")
    assert out3 == b"No trailing newline\n"
    assert rep3.final_lf_added is True


@pytest.mark.conformance
def test_nfc_normalization_and_idempotence() -> None:
    """Verify NFC composition of decomposed characters and idempotence."""
    # e + combining acute accent -> e with acute (C3 A9)
    decomposed = "e\u0301\n".encode("utf-8")
    composed, rep = canonicalize(decomposed)
    assert composed == "\u00e9\n".encode("utf-8")
    assert rep.nfc_changed is True

    # Idempotence (fixed-point property)
    composed2, rep2 = canonicalize(composed)
    assert composed2 == composed
    assert rep2.nfc_changed is False
