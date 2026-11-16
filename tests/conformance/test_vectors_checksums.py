"""Verify immutable test vectors and fixtures checksums (R-PROTO-02)."""

import hashlib
from pathlib import Path

import pytest


def _check_sha256sums_file(sums_path: Path) -> None:
    assert sums_path.exists(), f"Checksum file missing: {sums_path}"
    lines = sums_path.read_text(encoding="utf-8").splitlines()
    repo_root = sums_path.parent.parent.parent

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected_hash, rel_path = line.split(None, 1)
        target_file = repo_root / rel_path
        assert target_file.exists(), f"Target file missing: {target_file}"
        actual_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"
        )


@pytest.mark.conformance
def test_vectors_sha256sums() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    _check_sha256sums_file(repo_root / "tests" / "vectors" / "SHA256SUMS")


@pytest.mark.conformance
def test_fixtures_sha256sums() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    _check_sha256sums_file(repo_root / "tests" / "fixtures" / "SHA256SUMS")
