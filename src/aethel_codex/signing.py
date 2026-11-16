"""Manifest signing, self-verification, and envelope verification (YP §9, specs.md §8)."""

from aethel_codex.backends import get_backend
from aethel_codex.constants import SIG_CONTEXT
from aethel_codex.envelope import SignatureEnvelope
from aethel_codex.errors import AethelError, InternalError
from aethel_codex.pid import Pid, key_id


def sign_manifest(
    manifest_digest: bytes,
    role: int,
    alg: int | str,
    secret_key: bytes,
) -> SignatureEnvelope:
    """Sign manifest digest and return self-verified signature envelope.

    Normative reference: Yellow Paper §9.1, §9.2, R-SEC-02.

    Raises:
        InternalError: If signature fails self-verification prior to release.
    """
    if len(manifest_digest) != 32:
        raise ValueError(f"manifest_digest must be 32 bytes, got {len(manifest_digest)}")
    if not (1 <= role <= 255):
        raise ValueError(f"role must be 1..255, got {role}")

    backend = get_backend(alg)
    message_m = bytes([role]) + manifest_digest

    # Hedged signing under context "pip1.sig"
    sig = backend.sign(secret_key, message_m, context=SIG_CONTEXT)
    pk = backend.public_from_secret(secret_key)
    k_id = key_id(backend.alg_id, pk)

    # Mandatory self-verification before releasing (R-SEC-02, Non-negotiable 11)
    if not backend.verify(pk, message_m, sig, context=SIG_CONTEXT):
        raise InternalError(
            "BACKEND_ERROR",
            "Signature failed self-verification before release (fail-closed)",
        )

    return SignatureEnvelope(
        manifest_pid=Pid.create("m", manifest_digest),
        role=role,
        alg_name=backend.name,
        key_pid=Pid.parse(k_id),
        public_key=pk,
        signature=sig,
    )


def verify_signature_envelope(
    envelope: SignatureEnvelope,
    expected_manifest_pid: Pid | None = None,
) -> tuple[bool, str | None]:
    """Verify SGE-1 signature envelope following the 7 normative checks.

    Normative reference: Yellow Paper §9.3.

    Returns:
        (True, None) if verified successfully, or (False, reason) if verification fails.
    """
    # 1. Parse checks already succeeded if we have an envelope instance
    # 2. Check algorithm in table
    try:
        backend = get_backend(envelope.alg_name)
    except AethelError:
        return False, "alg_unknown"

    # 3. Check public key length
    if len(envelope.public_key) != backend.public_key_size:
        return False, "public_key_length"

    # 4. Check key ID against public key hash
    expected_k_id = key_id(backend.alg_id, envelope.public_key)
    if str(envelope.key_pid) != expected_k_id:
        return False, "key_mismatch"

    # 5. Check signature length
    if len(envelope.signature) != backend.signature_size:
        return False, "signature_length"

    # 6. Check manifest PID matches expected bundle manifest ID
    if expected_manifest_pid is not None and envelope.manifest_pid != expected_manifest_pid:
        return False, "manifest_mismatch"

    # 7. Backend cryptographic verification with M = u8(role) || manifest_digest
    message_m = bytes([envelope.role]) + envelope.manifest_pid.digest
    if not backend.verify(envelope.public_key, message_m, envelope.signature, context=SIG_CONTEXT):
        return False, "signature_verification_failed"

    return True, None
