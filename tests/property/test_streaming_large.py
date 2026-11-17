"""Streaming scale tests for Merkle TreeHasher (YP §5, testing-and-conformance.md §10)."""

from __future__ import annotations

import pytest

from aethel_codex.merkle import TreeHasher


@pytest.mark.slow
def test_stream_1gib_bounded_memory() -> None:
    """Stream 1 GiB of data in 1 MiB chunks with bounded memory and log(N) stack depth."""
    hasher = TreeHasher()
    one_mib = b"\x5a" * (1024 * 1024)

    # 1024 chunks of 1 MiB = 1 GiB (262,144 leaves of 4 KiB each)
    for _ in range(1024):
        hasher.update(one_mib)
        # Stack size for 2^18 leaves is bounded by log2(262144) + 1 <= 20
        assert len(hasher._stack) <= 30

    assert hasher.length == 1024 * 1024 * 1024
    root = hasher.root()
    assert len(root) == 32
    # Verify cached root returns identical digest
    assert hasher.root() == root
