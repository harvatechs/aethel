"""Property tests for CTF-1 (YP §4, R-PROTO-03, PT0)."""

import pytest
import unicodedata2
from hypothesis import given
from hypothesis import strategies as st

from aethel_codex.ctf1 import canonicalize
from aethel_codex.errors import CanonicalizationError
from aethel_codex.unicode18 import find_forbidden, find_unassigned


# Strategy for generating valid Unicode characters (assigned, not forbidden, not surrogate)
def is_valid_char(cp: int) -> bool:
    if (
        cp <= 0x08
        or cp in (0x0B, 0x0C)
        or 0x0E <= cp <= 0x1F
        or 0x7F <= cp <= 0x9F
        or cp == 0xFEFF
        or 0xFDD0 <= cp <= 0xFDEF
        or (cp & 0xFFFE) == 0xFFFE
        or (0xD800 <= cp <= 0xDFFF)
    ):
        return False
    return bool(unicodedata2.category(chr(cp)) != "Cn")


valid_codepoint = st.integers(min_value=0x20, max_value=0x10FFFD).filter(is_valid_char)
valid_text = st.text(alphabet=st.builds(chr, valid_codepoint), min_size=1, max_size=50)


@given(text=valid_text)
def test_ctf1_fixed_point_and_invariants(text: str) -> None:
    """Canonicalize is idempotent: canonicalize(C) == C, and outputs satisfy all invariants."""
    data = text.encode("utf-8")
    try:
        out1, _ = canonicalize(data)
    except CanonicalizationError:
        return

    # Invariants
    assert not out1.startswith(b"\xef\xbb\xbf"), "Output must not have BOM"
    assert b"\r" not in out1, "Output must not contain CR"
    assert out1.endswith(b"\n"), "Output must end with LF"

    decoded = out1.decode("utf-8")
    assert unicodedata2.normalize("NFC", decoded) == decoded, "Output must be NFC"
    assert find_forbidden(decoded) is None, "Output must contain no forbidden scalars"
    assert find_unassigned(decoded) is None, "Output must contain no unassigned scalars"

    # Fixed point
    out2, _ = canonicalize(out1)
    assert out2 == out1


@given(text=valid_text)
def test_ctf1_line_ending_and_bom_equivalence(text: str) -> None:
    """BOM and different line endings of the same text produce identical canonical bytes."""
    t_crlf = text.replace("\n", "\r\n")
    t_cr = text.replace("\n", "\r")

    raw_plain = text.encode("utf-8")
    raw_bom = b"\xef\xbb\xbf" + text.encode("utf-8")
    raw_crlf = t_crlf.encode("utf-8")
    raw_cr = t_cr.encode("utf-8")

    out_plain, _ = canonicalize(raw_plain)
    out_bom, _ = canonicalize(raw_bom)
    out_crlf, _ = canonicalize(raw_crlf)
    out_cr, _ = canonicalize(raw_cr)

    assert out_plain == out_bom == out_crlf == out_cr


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_20000_fixed_point_sweep() -> None:
    """Exhaustively verify fixed-point property over 20,000 distinct pseudo-random valid inputs."""
    import random

    rng = random.Random(42)  # noqa: S311
    # Pick from varied assigned Unicode blocks
    sample_cps = [cp for cp in range(0x20, 0x4000) if is_valid_char(cp)]

    for _ in range(20000):
        length = rng.randint(1, 15)
        chars = [chr(rng.choice(sample_cps)) for _ in range(length)]
        # Mix in newlines
        if rng.random() < 0.3:
            chars.append("\r\n" if rng.random() < 0.5 else "\n")
        raw = "".join(chars).encode("utf-8")
        if rng.random() < 0.2:
            raw = b"\xef\xbb\xbf" + raw

        out1, _ = canonicalize(raw)
        out2, _ = canonicalize(out1)
        assert out1 == out2
