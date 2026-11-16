"""Property tests for Merkle tree and audit paths (YP §5, R-PROTO-04, PT0)."""

import random

import pytest

from aethel_codex import merkle


@pytest.mark.fuzz
@pytest.mark.req("UR-01")
def test_streaming_equals_recursive_all_sizes_up_to_300() -> None:
    """Verify streaming TreeHasher equals recursive merkle_root for n = 1..300 leaves."""
    for n in range(1, 301):
        # Create deterministic chunks of 4096 bytes each
        # Use pseudo-random bytes
        rng = random.Random(n)  # noqa: S311
        chunks = [rng.randbytes(4096) for _ in range(n)]
        full_data = b"".join(chunks)

        # Recursive calculation
        leaves = [merkle.merkle_leaf(c) for c in chunks]
        expected_root = merkle.merkle_root(leaves)

        # Streaming calculation whole
        hasher_whole = merkle.TreeHasher()
        hasher_whole.update(full_data)
        assert hasher_whole.root() == expected_root

        # Streaming with irregular feed slices
        hasher_irregular = merkle.TreeHasher()
        offset = 0
        while offset < len(full_data):
            slice_size = rng.randint(1, 8192)
            hasher_irregular.update(full_data[offset : offset + slice_size])
            offset += slice_size
        assert hasher_irregular.root() == expected_root


@pytest.mark.fuzz
@pytest.mark.req("UR-01")
def test_audit_paths_and_forged_proofs_rejection() -> None:
    """Verify all valid audit paths pass and forged/mutated proofs fail."""
    rng = random.Random(1337)  # noqa: S311
    for n in [1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 64]:
        chunks = [rng.randbytes(4096) for _ in range(n)]
        # For the last chunk, make it random 1..4096 bytes
        last_len = rng.randint(1, 4096)
        chunks[-1] = chunks[-1][:last_len]
        blob_len = 4096 * (n - 1) + last_len

        leaves = [merkle.merkle_leaf(c) for c in chunks]
        root = merkle.merkle_root(leaves)

        for m in range(n):
            path = merkle.audit_path(m, leaves)

            # Valid proof must pass
            assert merkle.verify_chunk_proof(
                blob_length=blob_len,
                m=m,
                chunk=chunks[m],
                path=path,
                expected_root=root,
            )

            # Forgery 1: Flipped bit in chunk
            corrupted_chunk = bytearray(chunks[m])
            corrupted_chunk[0] ^= 0x01
            assert not merkle.verify_chunk_proof(
                blob_length=blob_len,
                m=m,
                chunk=bytes(corrupted_chunk),
                path=path,
                expected_root=root,
            )

            # Forgery 2: Wrong chunk length
            if len(chunks[m]) > 1:
                assert not merkle.verify_chunk_proof(
                    blob_length=blob_len,
                    m=m,
                    chunk=chunks[m][:-1],
                    path=path,
                    expected_root=root,
                )

            # Forgery 3: Mutated audit path element
            if path:
                corrupted_path = list(path)
                mut_elem = bytearray(corrupted_path[0])
                mut_elem[0] ^= 0x01
                corrupted_path[0] = bytes(mut_elem)
                assert not merkle.verify_chunk_proof(
                    blob_length=blob_len,
                    m=m,
                    chunk=chunks[m],
                    path=corrupted_path,
                    expected_root=root,
                )

            # Forgery 4: Out of bounds m
            assert not merkle.verify_chunk_proof(
                blob_length=blob_len,
                m=n,
                chunk=chunks[m],
                path=path,
                expected_root=root,
            )
            assert not merkle.verify_chunk_proof(
                blob_length=blob_len,
                m=-1,
                chunk=chunks[m],
                path=path,
                expected_root=root,
            )
