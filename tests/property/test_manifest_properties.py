"""Property tests for PMF-1 manifest builder, parser, and serializer (YP §7, R-PROTO-06)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.errors import AethelError
from aethel_codex.manifest import ManifestBuilder, parse_manifest, serialize_manifest
from aethel_codex.pid import Pid


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.fuzz
def test_manifest_builder_roundtrip() -> None:
    """Test builder creates valid manifest that roundtrips through serialize and parse."""
    text_pid = Pid.parse("pip1:t:" + "11" * 32)
    author_pid = Pid.parse("pip1:k:" + "22" * 32)
    asset_pid = Pid.parse("pip1:a:" + "33" * 32)
    cite_pid = Pid.parse("pip1:m:" + "44" * 32)

    builder = (
        ManifestBuilder()
        .set_profile("pip-1")
        .set_markup("pip-md-1")
        .set_lang("en-US")
        .set_title("Valid Title 123")
        .set_license("Apache-2.0")
        .set_text(text_pid, 100)
        .add_author(author_pid)
        .add_asset("image.png", asset_pid, 500, "image/png")
        .add_cite(cite_pid)
    )

    manifest = builder.build()
    raw = serialize_manifest(manifest)

    parsed = parse_manifest(raw)
    assert parsed.title == "Valid Title 123"
    assert parsed.license == "Apache-2.0"
    assert parsed.text_length == 100
    assert serialize_manifest(parsed) == raw


@pytest.mark.fuzz
def test_one_byte_mutation_property(yp_vectors: dict[str, Any]) -> None:
    """Every 1-byte mutation of a valid manifest either rejects or roundtrips identically."""
    for key in ("genesis", "revision"):
        raw = yp_vectors["manifests"][key]["text"].encode("utf-8")

        for pos in range(len(raw)):
            # Flip bit 0 of byte at pos
            mutated = bytearray(raw)
            mutated[pos] ^= 0x01
            mutated_bytes = bytes(mutated)

            try:
                parsed = parse_manifest(mutated_bytes)
                # If accepted, re-serialization must match mutated bytes identically
                assert serialize_manifest(parsed) == mutated_bytes
            except AethelError:
                # Expected rejection
                pass
