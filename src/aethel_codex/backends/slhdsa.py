"""SLH-DSA signature backends using pqcrypto (YP §8.2, FIPS 205)."""

import pqcrypto
import pqcrypto.sign.slh_dsa_sha2_256s as pq_sha2
import pqcrypto.sign.slh_dsa_shake_256s as pq_shake

from aethel_codex.errors import CryptoError


class SLHDSASHAKE256sBackend:
    """SLH-DSA-SHAKE-256s signature backend."""

    alg_id: int = 0x10
    name: str = "slh-dsa-shake-256s"
    family: str = "slh-dsa"
    public_key_size: int = 64
    signature_size: int = 29792

    def generate(self) -> tuple[bytes, bytes]:
        """Generate fresh keypair returning (secret_key_128b, public_key_64b)."""
        pk, sk = pq_shake.keygen()
        return bytes(sk), bytes(pk)

    def public_from_secret(self, secret: bytes) -> bytes:
        """Derive 64-byte public key from 128-byte secret key."""
        if len(secret) != 128:
            raise CryptoError(
                "BACKEND_ERROR", f"SLH-DSA secret key must be 128 bytes, got {len(secret)}"
            )
        return secret[64:]

    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
        """Sign message under context using hedged signing."""
        if len(secret) != 128:
            raise CryptoError(
                "BACKEND_ERROR", f"SLH-DSA secret key must be 128 bytes, got {len(secret)}"
            )
        return bytes(pq_shake.sign(secret, message, context=context))

    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
        """Verify signature under context."""
        if len(public) != self.public_key_size or len(signature) != self.signature_size:
            return False
        try:
            pq_shake.verify(public, message, signature, context=context)
            return True
        except (pqcrypto.InvalidSignatureError, ValueError):
            return False


class SLHDSASHA2256sBackend:
    """SLH-DSA-SHA2-256s signature backend (recommended long-term anchor)."""

    alg_id: int = 0x11
    name: str = "slh-dsa-sha2-256s"
    family: str = "slh-dsa"
    public_key_size: int = 64
    signature_size: int = 29792

    def generate(self) -> tuple[bytes, bytes]:
        """Generate fresh keypair returning (secret_key_128b, public_key_64b)."""
        pk, sk = pq_sha2.keygen()
        return bytes(sk), bytes(pk)

    def public_from_secret(self, secret: bytes) -> bytes:
        """Derive 64-byte public key from 128-byte secret key."""
        if len(secret) != 128:
            raise CryptoError(
                "BACKEND_ERROR", f"SLH-DSA secret key must be 128 bytes, got {len(secret)}"
            )
        return secret[64:]

    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
        """Sign message under context using hedged signing."""
        if len(secret) != 128:
            raise CryptoError(
                "BACKEND_ERROR", f"SLH-DSA secret key must be 128 bytes, got {len(secret)}"
            )
        return bytes(pq_sha2.sign(secret, message, context=context))

    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
        """Verify signature under context."""
        if len(public) != self.public_key_size or len(signature) != self.signature_size:
            return False
        try:
            pq_sha2.verify(public, message, signature, context=context)
            return True
        except (pqcrypto.InvalidSignatureError, ValueError):
            return False
