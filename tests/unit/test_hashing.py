"""Test domain-separated hashing and byte encodings (R-PROTO-04, R-PROTO-09, PT0)."""

import hashlib

import pytest

from aethel_codex.hashing import H, lp, u64be


def test_lp_valid() -> None:
    label = b"pip1.text"
    assert lp(label) == b"\x09pip1.text"


def test_lp_bounds() -> None:
    with pytest.raises(ValueError, match="label length"):
        lp(b"")

    with pytest.raises(ValueError, match="label length"):
        lp(b"x" * 256)

    # 1 byte and 255 bytes must be valid
    assert lp(b"a") == b"\x01a"
    long_label = b"x" * 255
    assert lp(long_label) == b"\xff" + long_label


def test_h_matches_sha3_256() -> None:
    label = b"pip1.leaf"
    data = b"hello world"
    expected = hashlib.sha3_256(b"\x09pip1.leaf" + data).digest()
    assert H(label, data) == expected


def test_u64be() -> None:
    assert u64be(0) == b"\x00\x00\x00\x00\x00\x00\x00\x00"
    assert u64be(1) == b"\x00\x00\x00\x00\x00\x00\x00\x01"
    assert u64be(4096) == b"\x00\x00\x00\x00\x00\x00\x10\x00"
    assert u64be(0xFFFFFFFFFFFFFFFF) == b"\xff\xff\xff\xff\xff\xff\xff\xff"

    with pytest.raises(OverflowError):
        u64be(-1)

    with pytest.raises(OverflowError):
        u64be(0x10000000000000000)
