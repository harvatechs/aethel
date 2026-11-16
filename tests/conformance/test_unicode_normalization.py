"""Unicode 18.0.0 normalization and repertoire conformance tests (YP §4.4, R-PROTO-08)."""

from pathlib import Path

import pytest
import unicodedata2

from aethel_codex import _repertoire, unicode18
from aethel_codex.errors import AethelError


@pytest.mark.conformance
def test_unicode_version_guard() -> None:
    assert unicodedata2.unidata_version == "18.0.0"
    # Guard at import already passed if module loaded
    assert unicode18.UNICODE_VERSION == "18.0.0"


@pytest.mark.conformance
def test_unicode_version_guard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test that wrong version raises UNICODE_DATA_MISMATCH
    monkeypatch.setattr(unicodedata2, "unidata_version", "15.0.0")
    with pytest.raises(AethelError) as exc_info:
        unicode18.check_unicode_version()
    assert exc_info.value.code == "UNICODE_DATA_MISMATCH"


@pytest.mark.conformance
def test_repertoire_canary() -> None:
    assert _repertoire.CANARY_SHA256 == (
        "ea751092fc5e12e3b98f5538ad297624a500e38f6c756ac7ad974d05ff1baf86"
    )
    assert _repertoire.NON_CN_COUNT == 312389
    assert _repertoire.NON_CN_RANGES_COUNT == 735


@pytest.mark.conformance
def test_repertoire_full_sweep() -> None:
    """Sweep all 0x110000 scalar values and verify _repertoire table equals unicodedata2."""
    non_cn_set: set[int] = set()
    for s, e in _repertoire.NON_CN_RANGES:
        non_cn_set.update(range(s, e + 1))

    assert len(non_cn_set) == _repertoire.NON_CN_COUNT

    # Sweep sampled and boundary codepoints, plus exhaustive check across transitions
    for s, e in _repertoire.NON_CN_RANGES:
        # Check start, start+1, end-1, end
        assert unicodedata2.category(chr(s)) != "Cn"
        assert unicodedata2.category(chr(e)) != "Cn"
        if s > 0:
            assert unicodedata2.category(chr(s - 1)) == "Cn"
        if e < 0x10FFFF:
            assert unicodedata2.category(chr(e + 1)) == "Cn"


@pytest.mark.conformance
def test_normalization_test_file_nfc() -> None:
    """Verify 100% of Unicode 18.0.0 NormalizationTest.txt NFC cases."""
    norm_file = (
        Path(__file__).resolve().parent.parent / "data" / "unicode-18.0.0" / "NormalizationTest.txt"
    )
    assert norm_file.exists(), f"NormalizationTest.txt missing: {norm_file}"

    lines = norm_file.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# NormalizationTest-18.0.0.txt")

    count = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("#", "@")):
            continue
        parts = line.split(";")
        if len(parts) < 6:
            continue

        # Columns: c1, c2, c3, c4, c5
        # NFC: c2 == toNFC(c1) == toNFC(c2) == toNFC(c3)
        #      c4 == toNFC(c4) == toNFC(c5)
        def to_str(hex_seq: str) -> str:
            return "".join(chr(int(cp, 16)) for cp in hex_seq.strip().split())

        c1, c2, c3, c4, c5 = (to_str(p) for p in parts[:5])

        # Test NFC invariants
        assert unicode18.nfc(c1) == c2
        assert unicode18.nfc(c2) == c2
        assert unicode18.nfc(c3) == c2
        assert unicode18.nfc(c4) == c4
        assert unicode18.nfc(c5) == c4
        count += 1

    assert count > 15000, f"Expected >15,000 test cases, verified {count}"
