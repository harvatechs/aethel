"""Unit tests for unicode18 and ctf1 module branch coverage (PT0 100%)."""

import pytest

from aethel_codex import ctf1, unicode18
from aethel_codex.errors import CanonicalizationError


def test_is_forbidden_branches() -> None:
    # cp <= 0x08
    assert unicode18.is_forbidden(0x00)
    assert unicode18.is_forbidden(0x08)
    # 0x09 (TAB), 0x0A (LF) are allowed
    assert not unicode18.is_forbidden(0x09)
    assert not unicode18.is_forbidden(0x0A)
    # 0x0B, 0x0C
    assert unicode18.is_forbidden(0x0B)
    assert unicode18.is_forbidden(0x0C)
    # 0x0D (CR) is allowed in raw manuscript (canonicalized to LF)
    assert not unicode18.is_forbidden(0x0D)
    # 0x0E <= cp <= 0x1F
    assert unicode18.is_forbidden(0x0E)
    assert unicode18.is_forbidden(0x1F)
    # ASCII printable is allowed
    assert not unicode18.is_forbidden(0x20)
    assert not unicode18.is_forbidden(0x7E)
    # 0x7F <= cp <= 0x9F
    assert unicode18.is_forbidden(0x7F)
    assert unicode18.is_forbidden(0x85)
    assert unicode18.is_forbidden(0x9F)
    # BOM
    assert unicode18.is_forbidden(0xFEFF)
    # Noncharacters 0xFDD0..0xFDEF
    assert unicode18.is_forbidden(0xFDD0)
    assert unicode18.is_forbidden(0xFDEF)
    assert not unicode18.is_forbidden(0xFDDF - 100)
    # Noncharacters ending in FFFE or FFFF
    assert unicode18.is_forbidden(0xFFFE)
    assert unicode18.is_forbidden(0xFFFF)
    assert unicode18.is_forbidden(0x1FFFE)
    assert unicode18.is_forbidden(0x1FFFF)
    assert unicode18.is_forbidden(0x10FFFE)
    assert unicode18.is_forbidden(0x10FFFF)
    # Normal Unicode
    assert not unicode18.is_forbidden(0x41)
    assert not unicode18.is_forbidden(0x4E00)


def test_compute_line_col_branches() -> None:
    # Test line and col across lone \r, \r\n, and \n
    text = "a\rb\r\nc\nd"
    # 'a' at idx 0: line 1, col 1
    assert unicode18.compute_line_col(text, 0) == (1, 1)
    # '\r' at idx 1: line 1, col 2
    assert unicode18.compute_line_col(text, 1) == (1, 2)
    # 'b' at idx 2: line 2, col 1
    assert unicode18.compute_line_col(text, 2) == (2, 1)
    # '\r' of \r\n at idx 3: line 2, col 2
    assert unicode18.compute_line_col(text, 3) == (2, 2)
    # 'c' after \r\n at idx 5: line 3, col 1
    assert unicode18.compute_line_col(text, 5) == (3, 1)
    # '\n' after 'c' at idx 6: line 3, col 2
    assert unicode18.compute_line_col(text, 6) == (3, 2)
    # 'd' after \n at idx 7: line 4, col 1
    assert unicode18.compute_line_col(text, 7) == (4, 1)


def test_canonicalize_empty_and_bom_empty() -> None:
    with pytest.raises(CanonicalizationError) as exc_info:
        ctf1.canonicalize(b"")
    assert exc_info.value.code == "E_EMPTY_TEXT"

    with pytest.raises(CanonicalizationError) as exc_info:
        ctf1.canonicalize(b"\xef\xbb\xbf")
    assert exc_info.value.code == "E_EMPTY_TEXT"


def test_canonicalize_invalid_utf8_offset_with_bom() -> None:
    # Invalid UTF-8 after BOM
    with pytest.raises(CanonicalizationError) as exc_info:
        ctf1.canonicalize(b"\xef\xbb\xbfhello\xffworld")
    assert exc_info.value.code == "E_INVALID_UTF8"
    assert exc_info.value.detail.get("offset") == 8  # 3 bytes BOM + 5 bytes "hello"


def test_canonicalize_lone_cr_and_crlf_reporting() -> None:
    data = b"Line 1\rLine 2\r\nLine 3\n"
    canonical_bytes, report = ctf1.canonicalize(data)
    assert canonical_bytes == b"Line 1\nLine 2\nLine 3\n"
    assert report.crlf_converted == 1
    assert report.lone_cr_converted == 1
    assert not report.final_lf_added
    assert not report.bom_removed
    assert not report.nfc_changed


def test_canonicalize_nfc_changed_and_final_lf_added() -> None:
    # 'e' + combining acute accent (\u0301) -> NFC gives \u00e9
    decomposed = "caf\u0065\u0301".encode("utf-8")
    canonical_bytes, report = ctf1.canonicalize(decomposed)
    assert canonical_bytes == "café\n".encode()
    assert report.nfc_changed
    assert report.final_lf_added
