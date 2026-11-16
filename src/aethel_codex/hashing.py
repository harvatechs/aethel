"""FIPS 202 SHA3-256 with domain-separation labels (YP §0, §3.4, R-PROTO-09)."""

import hashlib


def lp(label: bytes) -> bytes:
    """Length-prefix a domain label: LP(L) = u8(len(L)) || L.

    Args:
        label: Label bytes, must be between 1 and 255 bytes inclusive.

    Returns:
        Length-prefixed label bytes.

    Raises:
        ValueError: If label length is not between 1 and 255 bytes.
    """
    if not (1 <= len(label) <= 255):
        raise ValueError(f"label length must be 1..255, got {len(label)}")
    return bytes([len(label)]) + label


def H(label: bytes, x: bytes) -> bytes:  # noqa: N802
    """Compute domain-separated hash using SHA3-256.

    Normative reference: Yellow Paper §0.

    Args:
        label: Domain label bytes.
        x: Payload bytes to hash.

    Returns:
        32-byte SHA3-256 digest.

    Raises:
        ValueError: If label is invalid.
    """
    return hashlib.sha3_256(lp(label) + x).digest()


def u64be(n: int) -> bytes:
    """Encode an integer as an 8-byte big-endian unsigned integer.

    Normative reference: Yellow Paper §0.

    Args:
        n: Non-negative integer < 2^64.

    Returns:
        8-byte big-endian representation.

    Raises:
        OverflowError: If n is negative or >= 2^64.
    """
    if n < 0 or n >= (1 << 64):
        raise OverflowError(f"Integer out of u64 range: {n}")
    return n.to_bytes(8, "big")
