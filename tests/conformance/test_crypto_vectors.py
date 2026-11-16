"""Yellow Paper cryptographic signature conformance tests (YP §8, §9, §10, Appendix A.2)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.backends import get_backend
from aethel_codex.constants import SIG_CONTEXT
from aethel_codex.envelope import parse_envelope
from aethel_codex.pid import Pid
from aethel_codex.signing import verify_signature_envelope


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.fixture
def slh_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-slh-dsa-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_ml_dsa_87_vector_and_negatives(yp_vectors: dict[str, Any]) -> None:
    vec = yp_vectors["signature_ml_dsa_87"]
    backend = get_backend(0x02)
    assert backend.name == "ml-dsa-87"

    pk_bytes = bytes.fromhex(vec["public_key_hex"])
    sig_bytes = bytes.fromhex(vec["signature_hex"])
    msg_m = bytes.fromhex(vec["message_M_hex"])  # role (0x01) || raw manifest digest (32 bytes)
    assert len(msg_m) == 33

    # 1. Full signature verifies under cryptography backend
    assert backend.verify(pk_bytes, msg_m, sig_bytes, context=SIG_CONTEXT) is True

    # 2. Negatives from must_fail_when
    # "context is pip1.other"
    assert backend.verify(pk_bytes, msg_m, sig_bytes, context=b"pip1.other") is False

    # "role byte is 02"
    role_02_msg = b"\x02" + msg_m[1:]
    assert backend.verify(pk_bytes, role_02_msg, sig_bytes, context=SIG_CONTEXT) is False

    # "message uses the revision manifest id"
    rev_id_hex = yp_vectors["manifests"]["revision"]["manifest_id"][len("pip1:m:") :]
    rev_msg = msg_m[:1] + bytes.fromhex(rev_id_hex)
    assert backend.verify(pk_bytes, rev_msg, sig_bytes, context=SIG_CONTEXT) is False

    # 3. Flipped bit in signature fails
    corrupted_sig = bytearray(sig_bytes)
    corrupted_sig[0] ^= 0x01
    assert backend.verify(pk_bytes, msg_m, bytes(corrupted_sig), context=SIG_CONTEXT) is False


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_ml_dsa_65_vector(yp_vectors: dict[str, Any]) -> None:
    vec = yp_vectors["pack_generated"]["ml_dsa_65"]
    backend = get_backend(0x01)
    assert backend.name == "ml-dsa-65"

    pk_bytes = bytes.fromhex(vec["public_key_hex"])
    sig_bytes = bytes.fromhex(vec["signature_hex"])
    msg_m = bytes.fromhex(vec["message_M_hex"])

    assert backend.verify(pk_bytes, msg_m, sig_bytes, context=SIG_CONTEXT) is True

    # Flipped bit fails
    corrupted_sig = bytearray(sig_bytes)
    corrupted_sig[0] ^= 0x01
    assert backend.verify(pk_bytes, msg_m, bytes(corrupted_sig), context=SIG_CONTEXT) is False


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_slh_dsa_vectors(slh_vectors: dict[str, Any]) -> None:
    ctx = bytes.fromhex(slh_vectors["context_hex"])
    assert ctx == SIG_CONTEXT
    msg_m = bytes.fromhex(slh_vectors["message_M_hex"])

    for vec in slh_vectors["vectors"]:
        alg_id = vec["alg_id"]
        backend = get_backend(alg_id)
        assert backend.name == vec["alg"]

        import base64

        pk_bytes = base64.b64decode(vec["public_key_b64"])
        sig_bytes = base64.b64decode(vec["signature_b64"])

        # Must verify
        assert backend.verify(pk_bytes, msg_m, sig_bytes, context=ctx) is True

        # Flipped signature must fail
        flipped_sig = base64.b64decode(vec["flipped_signature_b64"])
        assert backend.verify(pk_bytes, msg_m, flipped_sig, context=ctx) is False

        # Negatives from must_fail_when: "context is pip1.other"
        assert backend.verify(pk_bytes, msg_m, sig_bytes, context=b"pip1.other") is False

        # "role byte is 02"
        role_02_msg = b"\x02" + msg_m[1:]
        assert backend.verify(pk_bytes, role_02_msg, sig_bytes, context=ctx) is False


@pytest.mark.conformance
def test_dual_family_fixture_signatures() -> None:
    sig_dir = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "dual-family"
        / "8a58594cb834f8454ae9d52929ff8e5c81916112b730df34e3186374871e9849"
        / "signatures"
    )

    manifest_pid = Pid.parse(
        "pip1:m:8a58594cb834f8454ae9d52929ff8e5c81916112b730df34e3186374871e9849"
    )

    sig_files = list(sig_dir.glob("*.sig"))
    assert len(sig_files) == 2

    for sig_path in sig_files:
        raw = sig_path.read_bytes()
        envelope = parse_envelope(raw)
        assert envelope.manifest_pid == manifest_pid
        ok, reason = verify_signature_envelope(envelope, expected_manifest_pid=manifest_pid)
        assert ok is True
        assert reason is None
