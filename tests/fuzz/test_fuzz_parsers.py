"""Hypothesis-driven fuzz targets for strict protocol parsers (testing-and-conformance.md §11)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aethel_codex.citations import parse_citation
from aethel_codex.ctf1 import canonicalize
from aethel_codex.envelope import parse_attestation_envelope, parse_envelope
from aethel_codex.errors import (
    AethelError,
    CanonicalizationError,
    CitationError,
    EnvelopeError,
    ManifestError,
)
from aethel_codex.manifest import parse_manifest
from aethel_codex.proof import parse_chunk_proof
from aethel_codex.verify import verify_bundle


@pytest.mark.fuzz
@given(st.binary(max_size=65536))
def test_fuzz_canonicalize(data: bytes) -> None:
    """Fuzz CTF-1 canonicalizer: must return canonical bytes or raise typed error."""
    try:
        canonical_bytes, report = canonicalize(data)
        assert isinstance(canonical_bytes, bytes)
        assert report.output_bytes >= 0
    except CanonicalizationError:
        pass


@pytest.mark.fuzz
@given(st.binary(max_size=65536))
def test_fuzz_parse_manifest(data: bytes) -> None:
    """Fuzz PMF-1 manifest parser: must return Manifest or raise ManifestError."""
    try:
        manifest = parse_manifest(data)
        assert manifest.profile == "pip-1"
    except ManifestError:
        pass


@pytest.mark.fuzz
@given(st.binary(max_size=65536))
def test_fuzz_parse_envelope(data: bytes) -> None:
    """Fuzz SGE-1 envelope parser: must return SignatureEnvelope or raise error."""
    try:
        env = parse_envelope(data)
        assert env.role in range(1, 256)
    except EnvelopeError:
        pass


@pytest.mark.fuzz
@given(st.binary(max_size=65536))
def test_fuzz_parse_attestation_envelope(data: bytes) -> None:
    """Fuzz ATT-1 envelope parser: must return AttestationEnvelope or raise error."""
    try:
        att = parse_attestation_envelope(data)
        assert isinstance(att.kind, str)
    except EnvelopeError:
        pass


@pytest.mark.fuzz
@given(st.binary(max_size=65536))
def test_fuzz_parse_chunk_proof(data: bytes) -> None:
    """Fuzz TFP-1 chunk proof parser: must return ChunkProof or raise AethelError."""
    try:
        proof = parse_chunk_proof(data)
        assert proof.chunk_index >= 0
    except AethelError:
        pass


@pytest.mark.fuzz
@given(st.text(max_size=512))
def test_fuzz_parse_citation(text: str) -> None:
    """Fuzz citation URI parser: must return Citation or raise CitationError."""
    try:
        cite = parse_citation(text)
        assert str(cite.target).startswith("pip1:")
    except CitationError:
        pass


@pytest.mark.fuzz
@given(st.binary(max_size=4096), st.binary(max_size=4096))
def test_fuzz_verify_bundle(
    tmp_path_factory: pytest.TempPathFactory, manifest_bytes: bytes, text_bytes: bytes
) -> None:
    """Fuzz bundle verifier: must always return typed VerifyReport without crashing."""
    bundle_dir = tmp_path_factory.mktemp("fuzz_bundle")
    (bundle_dir / "manifest.pip").write_bytes(manifest_bytes)
    (bundle_dir / "text.md").write_bytes(text_bytes)

    report = verify_bundle(bundle_dir)
    assert report.integrity in ("PASS", "FAIL", "INCONCLUSIVE")
    assert isinstance(report.checks, list)
    assert report.exit_code in (0, 1, 6)
