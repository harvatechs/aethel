"""Unit tests for merkle.py branch coverage (PT0 100%)."""

import pytest

from aethel_codex import merkle


def test_merkle_root_empty_raises() -> None:
    with pytest.raises(ValueError, match="leaves cannot be empty"):
        merkle.merkle_root([])


def test_tree_hasher_finalized_branches() -> None:
    hasher = merkle.TreeHasher()
    hasher.update(b"hello")
    r1 = hasher.root()
    # Call root() again returns cached root
    r2 = hasher.root()
    assert r1 == r2

    # Calling update() after finalize raises ValueError
    with pytest.raises(ValueError, match="TreeHasher already finalized"):
        hasher.update(b"more")


def test_audit_path_single_leaf() -> None:
    # n <= 1 returns empty list
    assert merkle.audit_path(0, [b"x" * 32]) == []


def test_root_from_path_structural_failures() -> None:
    h = b"x" * 32
    # n == 1 but non-empty path -> returns None
    assert merkle.root_from_path(0, 1, h, [b"dummy" * 6]) is None

    # n > 1 but empty path -> returns None
    assert merkle.root_from_path(0, 2, h, []) is None

    # Recursive call returns None on m < k
    # n = 4, k = 2. m = 0. path has 1 element (needs 2)
    assert merkle.root_from_path(0, 4, h, [b"dummy" * 6]) is None

    # Recursive call returns None on m >= k
    # n = 4, k = 2. m = 2. path has 1 element (needs 2)
    assert merkle.root_from_path(2, 4, h, [b"dummy" * 6]) is None


def test_verify_chunk_proof_empty_blob() -> None:
    # Empty blob (blob_length = 0, n = 1, chunk = b"")
    empty_root = merkle.blob_root(b"")
    assert merkle.verify_chunk_proof(
        blob_length=0,
        m=0,
        chunk=b"",
        path=[],
        expected_root=empty_root,
    )

    # Empty blob with non-empty chunk fails length check
    assert not merkle.verify_chunk_proof(
        blob_length=0,
        m=0,
        chunk=b"a",
        path=[],
        expected_root=empty_root,
    )


def test_verify_chunk_proof_structural_none() -> None:
    # n = 2, path is empty so root_from_path returns None
    assert not merkle.verify_chunk_proof(
        blob_length=8000,
        m=0,
        chunk=b"a" * 4096,
        path=[],
        expected_root=b"x" * 32,
    )
