"""ML-DSA signature backends using standard cryptography library (YP §8.1)."""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import mldsa

from aethel_codex.errors import CryptoError


class MLDSA65Backend:
    """ML-DSA-65 signature backend (FIPS 204)."""

    alg_id: int = 0x01
    name: str = "ml-dsa-65"
    family: str = "ml-dsa"
    public_key_size: int = 1952
    signature_size: int = 3309

    def generate(self) -> tuple[bytes, bytes]:
        """Generate fresh keypair returning (seed_bytes, public_bytes)."""
        priv = mldsa.MLDSA65PrivateKey.generate()
        return priv.private_bytes_raw(), priv.public_key().public_bytes_raw()

    def public_from_secret(self, secret: bytes) -> bytes:
        """Derive public key from 32-byte seed."""
        if len(secret) != 32:
            raise CryptoError(
                "BACKEND_ERROR", f"ML-DSA-65 seed must be 32 bytes, got {len(secret)}"
            )
        priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(secret)
        return priv.public_key().public_bytes_raw()

    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
        """Sign message under context using hedged randomness."""
        if len(secret) != 32:
            raise CryptoError(
                "BACKEND_ERROR", f"ML-DSA-65 seed must be 32 bytes, got {len(secret)}"
            )
        priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(secret)
        return priv.sign(message, context)

    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
        """Verify signature under context."""
        if len(public) != self.public_key_size or len(signature) != self.signature_size:
            return False
        try:
            pub = mldsa.MLDSA65PublicKey.from_public_bytes(public)
            pub.verify(signature, message, context)
            return True
        except (InvalidSignature, ValueError):
            return False


class MLDSA87Backend:
    """ML-DSA-87 signature backend (FIPS 204)."""

    alg_id: int = 0x02
    name: str = "ml-dsa-87"
    family: str = "ml-dsa"
    public_key_size: int = 2592
    signature_size: int = 4627

    def generate(self) -> tuple[bytes, bytes]:
        """Generate fresh keypair returning (seed_bytes, public_bytes)."""
        priv = mldsa.MLDSA87PrivateKey.generate()
        return priv.private_bytes_raw(), priv.public_key().public_bytes_raw()

    def public_from_secret(self, secret: bytes) -> bytes:
        """Derive public key from 32-byte seed."""
        if len(secret) != 32:
            raise CryptoError(
                "BACKEND_ERROR", f"ML-DSA-87 seed must be 32 bytes, got {len(secret)}"
            )
        priv = mldsa.MLDSA87PrivateKey.from_seed_bytes(secret)
        return priv.public_key().public_bytes_raw()

    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
        """Sign message under context using hedged randomness."""
        if len(secret) != 32:
            raise CryptoError(
                "BACKEND_ERROR", f"ML-DSA-87 seed must be 32 bytes, got {len(secret)}"
            )
        priv = mldsa.MLDSA87PrivateKey.from_seed_bytes(secret)
        return priv.sign(message, context)

    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
        """Verify signature under context."""
        if len(public) != self.public_key_size or len(signature) != self.signature_size:
            return False
        try:
            pub = mldsa.MLDSA87PublicKey.from_public_bytes(public)
            pub.verify(signature, message, context)
            return True
        except (InvalidSignature, ValueError):
            return False
