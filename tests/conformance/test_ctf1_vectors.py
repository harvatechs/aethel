"""Test CTF-1 against Yellow Paper vectors T1, T2, and 12 negative vectors (YP §4, A.1)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.ctf1 import canonicalize
from aethel_codex.errors import CanonicalizationError


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_vector_t1(yp_vectors: dict[str, Any]) -> None:
    t1 = yp_vectors["ctf1"]["T1"]
    raw = bytes.fromhex(t1["input_hex"])
    expected = bytes.fromhex(t1["output_hex"])

    out, report = canonicalize(raw)
    assert out == expected
    # Fixed point property
    out2, _ = canonicalize(out)
    assert out2 == out
    assert report.output_bytes == len(expected)


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_vector_t2(yp_vectors: dict[str, Any]) -> None:
    t2 = yp_vectors["ctf1"]["T2"]
    raw = bytes.fromhex(t2["input_hex"])
    expected = bytes.fromhex(t2["output_hex"])

    out, report = canonicalize(raw)
    assert out == expected
    assert out.hex() == t2["output_hex"]
    # Fixed point property
    out2, _ = canonicalize(out)
    assert out2 == out
    assert report.bom_removed is True
    assert report.crlf_converted == 1
    assert report.lone_cr_converted == 1
    assert report.nfc_changed is True
    assert report.final_lf_added is True


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_vector_t3(yp_vectors: dict[str, Any]) -> None:
    # T3 input is 10,000 ASCII bytes: (('0123456789'*1000)[:9999] + LF)
    raw = (b"0123456789" * 1000)[:9999] + b"\n"
    assert len(raw) == 10000

    out, report = canonicalize(raw)
    assert out == raw
    assert len(out) == 10000
    assert report.input_bytes == 10000
    assert report.output_bytes == 10000

    out2, _ = canonicalize(out)
    assert out2 == out


@pytest.mark.conformance
@pytest.mark.req("UR-03")
def test_ctf1_negative_vectors(yp_vectors: dict[str, Any]) -> None:
    negatives = yp_vectors["ctf1"]["negative"]
    assert len(negatives) == 12

    for neg in negatives:
        raw = bytes.fromhex(neg["input_hex"])
        expected_code = neg["expect"]
        with pytest.raises(CanonicalizationError) as exc_info:
            canonicalize(raw)
        assert exc_info.value.code == expected_code, (
            f"Failed on {neg['input_hex']}: expected {expected_code}, got {exc_info.value.code}"
        )
        assert exc_info.value.yp_section.startswith("§4")
