"""Cryptographic backend registry and resolution (YP §8, specs.md §8)."""

from aethel_codex.backends.base import SignatureBackend
from aethel_codex.backends.mldsa import MLDSA65Backend, MLDSA87Backend
from aethel_codex.backends.slhdsa import SLHDSASHA2256sBackend, SLHDSASHAKE256sBackend
from aethel_codex.errors import AethelError

_BACKENDS_BY_ID: dict[int, SignatureBackend] = {
    0x01: MLDSA65Backend(),
    0x02: MLDSA87Backend(),
    0x10: SLHDSASHAKE256sBackend(),
    0x11: SLHDSASHA2256sBackend(),
}

_BACKENDS_BY_NAME: dict[str, SignatureBackend] = {b.name: b for b in _BACKENDS_BY_ID.values()}

__all__ = ["SignatureBackend", "get_backend"]


def get_backend(alg: int | str) -> SignatureBackend:
    """Retrieve cryptographic signature backend by algorithm ID (int) or name (str).

    Raises:
        AethelError: With code ALG_UNKNOWN if algorithm is not supported.
    """
    if isinstance(alg, int):
        if alg in _BACKENDS_BY_ID:
            return _BACKENDS_BY_ID[alg]
        raise AethelError("ALG_UNKNOWN", f"Unknown algorithm ID: 0x{alg:02X}")
    if isinstance(alg, str):
        if alg in _BACKENDS_BY_NAME:
            return _BACKENDS_BY_NAME[alg]
        raise AethelError("ALG_UNKNOWN", f"Unknown algorithm name: {alg!r}")
    raise AethelError("ALG_UNKNOWN", f"Invalid algorithm identifier type: {type(alg)}")
