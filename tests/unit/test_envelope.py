"""Unit tests for SGE-1 signature envelope parsing and strict Base64 (YP §9.4, PT1)."""

import pytest

from aethel_codex.envelope import (
    parse_envelope,
    serialize_envelope,
    strict_b64decode,
    strict_b64encode,
)
from aethel_codex.errors import EnvelopeError

VALID_ENVELOPE = (
    "pip-signature 1\n"
    "manifest pip1:m:e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d\n"
    "role author\n"
    "alg ml-dsa-87\n"
    "key pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b\n"
    "public-key AAAA\n"
    "signature BBBB\n"
)


def test_strict_base64() -> None:
    # Valid
    assert strict_b64encode(b"\x00\x01\x02") == "AAEC"
    assert strict_b64decode("AAEC") == b"\x00\x01\x02"

    # Non-canonical padding (stray bits)
    # "ZE==" has non-zero unused bits in the second byte
    with pytest.raises(EnvelopeError) as exc_info:
        strict_b64decode("ZE==")
    assert exc_info.value.code == "ENVELOPE_INVALID"

    # Invalid characters
    with pytest.raises(EnvelopeError) as exc_info:
        strict_b64decode("AAEC!")
    assert exc_info.value.code == "ENVELOPE_INVALID"


def test_envelope_parse_and_serialize_roundtrip() -> None:
    env = parse_envelope(VALID_ENVELOPE.encode())
    assert env.role == 1
    assert env.role_name() == "author"
    assert env.alg_name == "ml-dsa-87"
    assert str(env.manifest_pid) == (
        "pip1:m:e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
    )
    assert serialize_envelope(env) == VALID_ENVELOPE.encode()
    assert env.envelope_filename() == "signatures/author-ml-dsa-87-2b27c5d44b407af5.sig"


def test_envelope_hex_roles() -> None:
    # role 0x01 should parse as role 1 and re-serialize as "author"
    hex_role_env = VALID_ENVELOPE.replace("role author\n", "role 0x01\n")
    env = parse_envelope(hex_role_env.encode())
    assert env.role == 1
    assert env.role_name() == "author"
    # Serializes to name
    assert b"role author\n" in serialize_envelope(env)

    # role 0x05 (custom registry role)
    custom_role_env = VALID_ENVELOPE.replace("role author\n", "role 0x05\n")
    env5 = parse_envelope(custom_role_env.encode())
    assert env5.role == 5
    assert env5.role_name() == "0x05"
    assert b"role 0x05\n" in serialize_envelope(env5)


def test_envelope_parse_rejections() -> None:
    # Role 0x00 is forbidden
    bad_role_0 = VALID_ENVELOPE.replace("role author\n", "role 0x00\n").encode()
    with pytest.raises(EnvelopeError) as exc_info:
        parse_envelope(bad_role_0)
    assert exc_info.value.code == "ENVELOPE_INVALID"

    # Bad header
    bad_magic = VALID_ENVELOPE.replace("pip-signature 1\n", "pip-signature 2\n").encode()
    with pytest.raises(EnvelopeError) as exc_info:
        parse_envelope(bad_magic)
    assert exc_info.value.code == "ENVELOPE_INVALID"

    # Missing lines
    bad_short = b"pip-signature 1\nmanifest pip1:m:11\n"
    with pytest.raises(EnvelopeError) as exc_info:
        parse_envelope(bad_short)
    assert exc_info.value.code == "ENVELOPE_INVALID"

    # Carriage return
    with pytest.raises(EnvelopeError) as exc_info:
        parse_envelope(VALID_ENVELOPE.replace("\n", "\r\n").encode())
    assert exc_info.value.code == "ENVELOPE_INVALID"
