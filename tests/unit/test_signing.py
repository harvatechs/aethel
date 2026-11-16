"""Unit tests for signing, self-verification, and envelope verification (YP §9, PT1)."""

from typing import Any

import pytest

from aethel_codex.backends import get_backend
from aethel_codex.envelope import SignatureEnvelope
from aethel_codex.errors import InternalError
from aethel_codex.pid import Pid
from aethel_codex.signing import sign_manifest, verify_signature_envelope


def test_sign_manifest_and_self_verify() -> None:
    backend = get_backend(0x02)  # ML-DSA-87
    sk, pk = backend.generate()
    manifest_digest = b"\xaa" * 32

    env = sign_manifest(
        manifest_digest=manifest_digest,
        role=1,
        alg=0x02,
        secret_key=sk,
    )

    assert env.role == 1
    assert env.alg_name == "ml-dsa-87"
    assert env.manifest_pid.digest == manifest_digest
    assert env.public_key == pk

    # Verify signature envelope
    ok, reason = verify_signature_envelope(env, expected_manifest_pid=env.manifest_pid)
    assert ok is True
    assert reason is None


def test_faulty_backend_self_verify_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A backend producing bad signatures must cause sign_manifest to raise InternalError."""
    import aethel_codex.signing as sign_mod

    backend = get_backend(0x02)
    sk, _ = backend.generate()
    manifest_digest = b"\xbb" * 32

    class FaultyBackend:
        def __init__(self, real: Any) -> None:
            self._real = real
            self.alg_id = real.alg_id
            self.name = real.name
            self.public_key_size = real.public_key_size
            self.signature_size = real.signature_size

        def public_from_secret(self, secret: bytes) -> bytes:
            res: bytes = self._real.public_from_secret(secret)
            return res

        def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
            # Return corrupted signature of correct size
            return b"\x00" * int(self.signature_size)

        def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
            return False

    def faulty_get_backend(alg: Any) -> Any:
        real = get_backend(alg)
        return FaultyBackend(real)

    monkeypatch.setattr(sign_mod, "get_backend", faulty_get_backend)

    with pytest.raises(InternalError):
        sign_manifest(
            manifest_digest=manifest_digest,
            role=1,
            alg=0x02,
            secret_key=sk,
        )


def test_verify_signature_envelope_rejections() -> None:
    backend = get_backend(0x02)
    sk, _pk = backend.generate()
    manifest_digest = b"\xcc" * 32

    env = sign_manifest(
        manifest_digest=manifest_digest,
        role=1,
        alg=0x02,
        secret_key=sk,
    )

    # 1. Manifest mismatch
    other_pid = Pid.parse("pip1:m:" + "00" * 32)
    ok, reason = verify_signature_envelope(env, expected_manifest_pid=other_pid)
    assert ok is False
    assert reason == "manifest_mismatch"

    # 2. Key mismatch (key pid does not match H(LABEL_KEY, alg_id || public_key))
    corrupted_key_pid_env = SignatureEnvelope(
        manifest_pid=env.manifest_pid,
        role=env.role,
        alg_name=env.alg_name,
        key_pid=Pid.parse("pip1:k:" + "99" * 32),
        public_key=env.public_key,
        signature=env.signature,
    )
    ok, reason = verify_signature_envelope(corrupted_key_pid_env)
    assert ok is False
    assert reason == "key_mismatch"

    # 3. Public key length mismatch
    bad_pk_env = SignatureEnvelope(
        manifest_pid=env.manifest_pid,
        role=env.role,
        alg_name=env.alg_name,
        key_pid=env.key_pid,
        public_key=env.public_key[:-1],
        signature=env.signature,
    )
    ok, reason = verify_signature_envelope(bad_pk_env)
    assert ok is False
    assert reason == "public_key_length"

    # 4. Signature length mismatch
    bad_sig_len_env = SignatureEnvelope(
        manifest_pid=env.manifest_pid,
        role=env.role,
        alg_name=env.alg_name,
        key_pid=env.key_pid,
        public_key=env.public_key,
        signature=env.signature[:-1],
    )
    ok, reason = verify_signature_envelope(bad_sig_len_env)
    assert ok is False
    assert reason == "signature_length"

    # 5. Invalid signature bytes
    corrupted_sig = bytearray(env.signature)
    corrupted_sig[0] ^= 0x01
    bad_sig_bytes_env = SignatureEnvelope(
        manifest_pid=env.manifest_pid,
        role=env.role,
        alg_name=env.alg_name,
        key_pid=env.key_pid,
        public_key=env.public_key,
        signature=bytes(corrupted_sig),
    )
    ok, reason = verify_signature_envelope(bad_sig_bytes_env)
    assert ok is False
    assert reason == "signature_verification_failed"
