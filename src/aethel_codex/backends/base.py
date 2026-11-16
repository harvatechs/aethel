"""Cryptographic signature backend interface and protocol (YP §8, specs.md §8)."""

from typing import Protocol


class SignatureBackend(Protocol):
    """Protocol for post-quantum signature backends (ML-DSA, SLH-DSA)."""

    alg_id: int
    name: str
    family: str  # "ml-dsa" or "slh-dsa"
    public_key_size: int
    signature_size: int

    def generate(self) -> tuple[bytes, bytes]:
        """Generate a fresh keypair returning (secret_key, public_key)."""
        ...

    def public_from_secret(self, secret: bytes) -> bytes:
        """Derive public key bytes from secret key bytes."""
        ...

    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes:
        """Sign message under context string using hedged signing."""
        ...

    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool:
        """Verify signature under context string. Returns True iff valid."""
        ...
