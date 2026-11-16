"""Unit tests for PID parsing, formatting, and identifier calculation (YP §6, §7.6)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.errors import AethelError
from aethel_codex.pid import Pid, key_id, manifest_id


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def test_pid_parse_and_str_valid() -> None:
    for t in ("m", "t", "a", "k"):
        hex_digest = "0123456789abcdef" * 4
        pid_str = f"pip1:{t}:{hex_digest}"
        pid = Pid.parse(pid_str)
        assert pid.pid_type == t
        assert pid.digest == bytes.fromhex(hex_digest)
        assert str(pid) == pid_str
        assert pid.hex() == hex_digest


def test_pid_equality_and_hashing() -> None:
    p1 = Pid.parse("pip1:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    p2 = Pid.parse("pip1:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    p3 = Pid.parse("pip1:t:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    assert p1 == p2
    assert p1 != p3
    assert hash(p1) == hash(p2)
    assert hash(p1) != hash(p3)


def test_pid_parse_rejections() -> None:
    bad_pids = [
        # Upper case hex is NOT allowed
        "pip1:m:0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF",
        # Short hex
        "pip1:m:0123456789abcdef",
        # Long hex
        "pip1:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef00",
        # Unknown type
        "pip1:x:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "pip1:z:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        # Bad scheme/prefix
        "pip2:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "pip1-m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        # Whitespace / trailing newlines (re.fullmatch)
        "pip1:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n",
        " pip1:m:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "",
        "pip1:m:",
    ]
    for bad in bad_pids:
        with pytest.raises(AethelError) as exc_info:
            Pid.parse(bad)
        assert exc_info.value.code == "PID_SYNTAX"


def test_pid_create_validation() -> None:
    # Invalid type
    with pytest.raises(AethelError) as exc_info:
        Pid.create("x", b"\x00" * 32)
    assert exc_info.value.code == "PID_SYNTAX"

    # Invalid digest length
    with pytest.raises(AethelError) as exc_info:
        Pid.create("m", b"\x00" * 31)
    assert exc_info.value.code == "PID_SYNTAX"


def test_manifest_id_vectors(yp_vectors: dict[str, Any]) -> None:
    # Genesis manifest
    gen_raw = yp_vectors["manifests"]["genesis"]["text"].encode("utf-8")
    expected_gen_id = yp_vectors["manifests"]["genesis"]["manifest_id"]
    computed_gen_id = manifest_id(gen_raw)
    assert computed_gen_id == expected_gen_id
    assert computed_gen_id == (
        "pip1:m:e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
    )

    # Revision manifest
    rev_raw = yp_vectors["manifests"]["revision"]["text"].encode("utf-8")
    expected_rev_id = yp_vectors["manifests"]["revision"]["manifest_id"]
    computed_rev_id = manifest_id(rev_raw)
    assert computed_rev_id == expected_rev_id
    assert computed_rev_id == (
        "pip1:m:ee09cf8b094f606ae03d1fe7d6db94e83956a9b9bdd019d2853e4d6c181c050d"
    )


def test_key_id_calculation(yp_vectors: dict[str, Any]) -> None:
    # ML-DSA-87 test vector key
    sig_vec = yp_vectors["signature_ml_dsa_87"]
    pk_bytes = bytes.fromhex(sig_vec["public_key_hex"])
    expected_key_id = sig_vec["key_id"]

    computed = key_id(0x02, pk_bytes)
    assert computed == expected_key_id
    assert computed == ("pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b")


def test_key_id_rejections() -> None:
    # Unknown algorithm ID
    with pytest.raises(AethelError) as exc_info:
        key_id(0x99, b"\x00" * 32)
    assert exc_info.value.code == "ALG_UNKNOWN"

    # Wrong public key length for ML-DSA-87 (expected 2592)
    with pytest.raises(AethelError) as exc_info:
        key_id(0x02, b"\x00" * 100)
    assert exc_info.value.code == "KEY_MISMATCH"
