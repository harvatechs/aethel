"""Comprehensive unit tests covering all error and edge branches in crypto modules."""

import pytest

from aethel_codex.backends import get_backend
from aethel_codex.constants import MAX_ENVELOPE_BYTES
from aethel_codex.envelope import (
    SignatureEnvelope,
    parse_envelope,
)
from aethel_codex.errors import AethelError, CryptoError, EnvelopeError
from aethel_codex.pid import Pid
from aethel_codex.signing import sign_manifest, verify_signature_envelope

VALID_ENV = (
    "pip-signature 1\n"
    "manifest pip1:m:e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d\n"
    "role author\n"
    "alg ml-dsa-87\n"
    "key pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b\n"
    "public-key AAAA\n"
    "signature BBBB\n"
)


def test_backends_get_backend_variants() -> None:
    # Int and str lookups
    for aid, name in [
        (0x01, "ml-dsa-65"),
        (0x02, "ml-dsa-87"),
        (0x10, "slh-dsa-shake-256s"),
        (0x11, "slh-dsa-sha2-256s"),
    ]:
        b1 = get_backend(aid)
        b2 = get_backend(name)
        assert b1.name == name
        assert b2.alg_id == aid

    # Unknown ID
    with pytest.raises(AethelError) as exc_info:
        get_backend(0x99)
    assert exc_info.value.code == "ALG_UNKNOWN"

    # Unknown name
    with pytest.raises(AethelError) as exc_info:
        get_backend("unknown-alg")
    assert exc_info.value.code == "ALG_UNKNOWN"

    # Invalid type
    with pytest.raises(AethelError) as exc_info:
        get_backend(None)  # type: ignore[arg-type]
    assert exc_info.value.code == "ALG_UNKNOWN"


def test_backends_key_generation_and_length_checks() -> None:
    for aid in (0x01, 0x02, 0x10, 0x11):
        backend = get_backend(aid)
        sk, pk = backend.generate()
        assert len(pk) == backend.public_key_size
        derived_pk = backend.public_from_secret(sk)
        assert derived_pk == pk

        # Invalid secret length
        with pytest.raises(CryptoError):
            backend.public_from_secret(sk[:-1])
        with pytest.raises(CryptoError):
            backend.sign(sk[:-1], b"msg", b"pip1.sig")

        # Sign and verify
        sig = backend.sign(sk, b"message", b"pip1.sig")
        assert len(sig) == backend.signature_size
        assert backend.verify(pk, b"message", sig, b"pip1.sig") is True

        # Verify length rejections
        assert backend.verify(pk[:-1], b"message", sig, b"pip1.sig") is False
        assert backend.verify(pk, b"message", sig[:-1], b"pip1.sig") is False


def test_envelope_syntax_error_branches() -> None:
    # Exceeding MAX_ENVELOPE_BYTES
    huge_data = b"x" * (MAX_ENVELOPE_BYTES + 1)
    with pytest.raises(EnvelopeError):
        parse_envelope(huge_data)

    # Invalid UTF-8
    with pytest.raises(EnvelopeError):
        parse_envelope(b"pip-signature 1\n\xff")

    # Missing lines
    with pytest.raises(EnvelopeError):
        parse_envelope(b"pip-signature 1\nmanifest pip1:m:11\n")

    # Line 1 not starting with 'manifest '
    bad_l1 = VALID_ENV.replace("manifest ", "badmanifest ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l1)

    # Line 1 wrong PID type
    bad_l1_pid = VALID_ENV.replace("manifest pip1:m:", "manifest pip1:t:").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l1_pid)

    # Line 2 not starting with 'role '
    bad_l2 = VALID_ENV.replace("role ", "badrole ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l2)

    # Line 2 invalid role format
    bad_l2_fmt = VALID_ENV.replace("role author", "role badrole").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l2_fmt)

    # Line 3 not starting with 'alg '
    bad_l3 = VALID_ENV.replace("alg ", "badalg ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l3)

    # Line 3 unknown algorithm
    bad_l3_alg = VALID_ENV.replace("alg ml-dsa-87", "alg bad-alg").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l3_alg)

    # Line 4 not starting with 'key '
    bad_l4 = VALID_ENV.replace("key ", "badkey ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l4)

    # Line 4 wrong key PID type
    bad_l4_pid = VALID_ENV.replace("key pip1:k:", "key pip1:m:").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l4_pid)

    # Line 5 not starting with 'public-key '
    bad_l5 = VALID_ENV.replace("public-key ", "badpk ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l5)

    # Line 6 not starting with 'signature '
    bad_l6 = VALID_ENV.replace("signature ", "badsig ").encode()
    with pytest.raises(EnvelopeError):
        parse_envelope(bad_l6)


def test_signing_input_validation() -> None:
    # Wrong manifest digest length
    with pytest.raises(ValueError, match="manifest_digest must be 32 bytes"):
        sign_manifest(b"\x00" * 31, 1, 0x02, b"\x00" * 32)

    # Wrong role integer range
    with pytest.raises(ValueError, match=r"role must be 1\.\.255"):
        sign_manifest(b"\x00" * 32, 0, 0x02, b"\x00" * 32)
    with pytest.raises(ValueError, match=r"role must be 1\.\.255"):
        sign_manifest(b"\x00" * 32, 256, 0x02, b"\x00" * 32)


def test_verify_signature_envelope_unknown_alg() -> None:
    env = SignatureEnvelope(
        manifest_pid=Pid.parse("pip1:m:" + "11" * 32),
        role=1,
        alg_name="non-existent-alg",
        key_pid=Pid.parse("pip1:k:" + "22" * 32),
        public_key=b"\x00" * 32,
        signature=b"\x00" * 32,
    )
    ok, reason = verify_signature_envelope(env)
    assert ok is False
    assert reason == "alg_unknown"
