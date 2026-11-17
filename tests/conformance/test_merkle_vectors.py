"""Yellow Paper Merkle tree and blob identifier conformance tests (YP §5, §6)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex import constants, merkle


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.conformance
@pytest.mark.req("UR-02")
def test_blob_id_t1() -> None:
    t1_bytes = b"# The Aethel Codex\n\nWrite once. Verify forever.\n"
    assert len(t1_bytes) == 48

    root = merkle.blob_root(t1_bytes)
    assert root.hex() == "bbcc5e9494dabc60e9465e93ab70c0f7436a29d5308a5b80b35f9478521165c4"

    t1_id = merkle.text_id(t1_bytes)
    assert t1_id == "pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_blob_id_t2(yp_vectors: dict[str, Any]) -> None:
    t2_canonical = bytes.fromhex(yp_vectors["ctf1"]["T2"]["output_hex"])
    assert len(t2_canonical) == 26

    t2_id = merkle.text_id(t2_canonical)
    assert t2_id == "pip1:t:9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413"


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_merkle_t3(yp_vectors: dict[str, Any]) -> None:
    t3_vec = yp_vectors["ctf1"]["T3"]
    t3_bytes = (b"0123456789" * 1000)[:9999] + b"\n"
    assert len(t3_bytes) == 10000

    chunks = merkle.chunk_data(t3_bytes)
    assert [len(c) for c in chunks] == t3_vec["chunk_lengths"]

    leaves = [merkle.merkle_leaf(c) for c in chunks]
    assert leaves[0].hex() == t3_vec["leaf0"]
    assert leaves[1].hex() == t3_vec["leaf1"]
    assert leaves[2].hex() == t3_vec["leaf2"]

    node01 = merkle.merkle_node(leaves[0], leaves[1])
    assert node01.hex() == t3_vec["node01"]

    root = merkle.merkle_root(leaves)
    assert root.hex() == t3_vec["root"]

    t3_id = merkle.text_id(t3_bytes)
    assert t3_id == t3_vec["text_id"]

    # Audit paths for leaves 0, 1, 2
    for m_str, expected_path_hex in t3_vec["audit_paths_leaf_level_first"].items():
        m = int(m_str)
        path = merkle.audit_path(m, leaves)
        assert [p.hex() for p in path] == expected_path_hex

        # Verify chunk proof
        assert merkle.verify_chunk_proof(
            blob_length=len(t3_bytes),
            m=m,
            chunk=chunks[m],
            path=path,
            expected_root=root,
        )


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_blob_id_t4(yp_vectors: dict[str, Any]) -> None:
    # Empty asset
    empty_bytes = b""
    empty_id = merkle.asset_id(empty_bytes)
    assert empty_id == yp_vectors["assets"]["empty"]
    assert empty_id == "pip1:a:e2a25df839aeba38c694f01b361c2e607f44f1e08c72353e806e0561139837f7"

    # SVG asset
    svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg"/>\n'
    assert len(svg_bytes) == 42
    svg_id = merkle.asset_id(svg_bytes)
    assert svg_id == yp_vectors["assets"]["figure1_svg"]["asset_id"]
    assert svg_id == "pip1:a:e7df5b50afd41b1621ceddbe590fe6ebaac58d393ff5da9b1f84a8f447da7462"


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_pack_generated_blob_sizes(yp_vectors: dict[str, Any]) -> None:
    """Test all 10 blob size vectors from pack_generated.blob_sizes."""
    entries = yp_vectors["pack_generated"]["blob_sizes"]["entries"]

    for entry in entries:
        length = entry["length"]
        # Generate data according to recipe: byte i = (i*31+7) & 0xFF
        data = bytes((i * 31 + 7) & 0xFF for i in range(length))
        assert len(data) == length

        # Check chunk count
        chunks = merkle.chunk_data(data)
        assert len(chunks) == entry["chunks"]

        # Check asset ID
        computed_asset_id = merkle.asset_id(data)
        assert computed_asset_id == entry["asset_id"]

        # Check text label ID if it were text
        computed_text_id = f"pip1:t:{merkle.blob_id(constants.LABEL_TEXT, data).hex()}"
        assert computed_text_id == entry["text_label_id_if_it_were_text"]

        # Verify streaming tree hasher gives identical root
        hasher = merkle.TreeHasher()
        hasher.update(data)
        assert hasher.root() == merkle.blob_root(data)
