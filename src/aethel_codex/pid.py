"""Permanent Ink Protocol Identifiers (PIDs) and key/manifest identity (YP §6, §7.6)."""

import re
from dataclasses import dataclass

from aethel_codex.constants import ALGORITHMS, LABEL_KEY, LABEL_MANIFEST
from aethel_codex.errors import AethelError
from aethel_codex.hashing import H

PID_PATTERN = re.compile(r"pip1:([mtak]):([0-9a-f]{64})")


@dataclass(frozen=True)
class Pid:
    """Permanent Ink Protocol Identifier (PID) value type.

    Normative reference: Yellow Paper §6.1.
    """

    pid_type: str  # "m" (manifest), "t" (text), "a" (asset), "k" (key)
    digest: bytes  # 32 raw bytes

    def __post_init__(self) -> None:
        """Validate PID fields on construction."""
        if self.pid_type not in ("m", "t", "a", "k"):
            raise AethelError("PID_SYNTAX", f"Invalid PID type: {self.pid_type!r}")
        if len(self.digest) != 32:
            raise AethelError("PID_SYNTAX", f"PID digest must be 32 bytes, got {len(self.digest)}")

    @classmethod
    def parse(cls, s: str) -> "Pid":
        """Parse canonical PID string using strict matching.

        Upper-case hex is rejected. Trailing whitespace is rejected.
        Normative reference: Yellow Paper §6.1, specs.md §5.
        """
        match = PID_PATTERN.fullmatch(s)
        if not match:
            raise AethelError("PID_SYNTAX", f"Invalid PID string: {s!r}")
        return cls(pid_type=match.group(1), digest=bytes.fromhex(match.group(2)))

    @classmethod
    def create(cls, pid_type: str, digest: bytes) -> "Pid":
        """Construct a validated PID instance."""
        return cls(pid_type=pid_type, digest=digest)

    def hex(self) -> str:
        """Return 64 lowercase hexadecimal characters of the digest."""
        return self.digest.hex()

    def __str__(self) -> str:
        """Format canonical PID string: pip1:<type>:<hex>."""
        return f"pip1:{self.pid_type}:{self.digest.hex()}"


def key_id(alg_id: int, public_key: bytes) -> str:
    """Compute key PID: pip1:k:<hex>.

    Normative reference: Yellow Paper §6.2.
    """
    if alg_id not in ALGORITHMS:
        raise AethelError("ALG_UNKNOWN", f"Algorithm 0x{alg_id:02X} unknown or unsupported")
    expected_len = ALGORITHMS[alg_id].public_key_size
    if len(public_key) != expected_len:
        raise AethelError(
            "KEY_MISMATCH",
            f"Public key length mismatch for 0x{alg_id:02X}: "
            f"got {len(public_key)}, expected {expected_len}",
        )
    digest = H(LABEL_KEY, bytes([alg_id]) + public_key)
    return f"pip1:k:{digest.hex()}"


def manifest_id(manifest_bytes: bytes) -> str:
    """Compute manifest PID: pip1:m:<hex>.

    Normative reference: Yellow Paper §7.6.
    """
    digest = H(LABEL_MANIFEST, manifest_bytes)
    return f"pip1:m:{digest.hex()}"
