"""Unit tests for citation inline scanning and locator validation (YP §6.3, PT1)."""

import pytest

from aethel_codex.citations import (
    Citation,
    parse_citation,
    scan_inline_citations,
    validate_citation_range,
)
from aethel_codex.errors import CitationError
from aethel_codex.pid import Pid


def test_scan_inline_citations() -> None:
    t1_hex = "11" * 32
    t2_hex = "22" * 32
    m1_hex = "33" * 32
    k1_hex = "44" * 32

    text = (
        f"See cite:pip1:t:{t1_hex} and also (cite:pip1:m:{m1_hex}#b=10-20).\n"
        f"Do not match cite:pip1:k:{k1_hex} (type k is not citable).\n"
        f"Do not match wordcite:pip1:t:{t1_hex} due to negative lookbehind.\n"
        f"Do not match cite:pip1:t:{t1_hex}aa due to negative lookahead (66 hex chars).\n"
        f"Another valid: cite:pip1:a:{t2_hex}.\n"
    )

    pids = scan_inline_citations(text)
    assert len(pids) == 3
    assert pids[0] == Pid.parse(f"pip1:t:{t1_hex}")
    assert pids[1] == Pid.parse(f"pip1:m:{m1_hex}")
    assert pids[2] == Pid.parse(f"pip1:a:{t2_hex}")


def test_citation_roundtrip_str() -> None:
    pid = Pid.parse("pip1:t:" + "aa" * 32)
    c1 = Citation(target=pid, locator=None)
    assert str(c1) == f"cite:pip1:t:{'aa' * 32}"
    assert parse_citation(str(c1)) == c1

    c2 = Citation(target=pid, locator=(10, 50))
    assert str(c2) == f"cite:pip1:t:{'aa' * 32}#b=10-50"
    assert parse_citation(str(c2)) == c2


def test_asset_citation_range_validation() -> None:
    # Asset type allows arbitrary binary byte slices (no UTF-8 continuation check)
    a_pid = Pid.parse("pip1:a:" + "bb" * 32)
    citation = Citation(target=a_pid, locator=(2, 5))

    # Binary blob with continuation bytes
    blob = b"\x00\x01\x80\x81\x82\x05\x06"
    assert validate_citation_range(citation, blob) is True

    # End out of range
    citation_oob = Citation(target=a_pid, locator=(2, 10))
    with pytest.raises(CitationError) as exc_info:
        validate_citation_range(citation_oob, blob)
    assert exc_info.value.code == "CITE_RANGE"


def test_whole_blob_citation_no_locator() -> None:
    t_pid = Pid.parse("pip1:t:" + "cc" * 32)
    citation = Citation(target=t_pid, locator=None)
    assert validate_citation_range(citation, b"any content") is True
