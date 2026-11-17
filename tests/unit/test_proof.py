"""Unit tests for TFP-1 chunk proof serialization, parsing, and verification (YP §5, §13)."""

import pytest

from aethel_codex.errors import AethelError
from aethel_codex.merkle import text_id
from aethel_codex.pid import Pid
from aethel_codex.proof import (
    ChunkProof,
    create_chunk_proof,
    parse_chunk_proof,
    serialize_chunk_proof,
    verify_proof,
)


def test_chunk_proof_roundtrip() -> None:
    data = b"Hello, world! This is a test for chunk proof."
    blob_pid = Pid.parse(text_id(data))
    proof = create_chunk_proof(data, blob_pid, 0)

    serialized = serialize_chunk_proof(proof)
    parsed = parse_chunk_proof(serialized)

    assert parsed.blob_pid == proof.blob_pid
    assert parsed.blob_length == proof.blob_length
    assert parsed.chunk_index == proof.chunk_index
    assert parsed.chunk == proof.chunk
    assert parsed.path == proof.path

    assert verify_proof(parsed) is True


def test_chunk_proof_multi_chunk() -> None:
    # 10000 bytes will yield 3 chunks (4096 bytes each)
    data = b"x" * 10000
    blob_pid = Pid.parse(text_id(data))

    proof_last = create_chunk_proof(data, blob_pid, 2)
    serialized = serialize_chunk_proof(proof_last)
    parsed = parse_chunk_proof(serialized)
    assert verify_proof(parsed) is True

    # Bad index when creating proof (negative or out of range)
    with pytest.raises(AethelError) as exc:
        create_chunk_proof(data, blob_pid, -1)
    assert exc.value.code == "ENVELOPE_INVALID"

    with pytest.raises(AethelError) as exc:
        create_chunk_proof(data, blob_pid, 3)
    assert exc.value.code == "ENVELOPE_INVALID"


def test_chunk_proof_rejections() -> None:
    data = b"Test rejections"
    blob_pid = Pid.parse(text_id(data))
    proof = create_chunk_proof(data, blob_pid, 0)
    valid_bytes = serialize_chunk_proof(proof)

    # Size limit
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(b"x" * (256 * 1024 + 1))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Non UTF-8
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(b"\xff\xfe")
    assert exc.value.code == "ENVELOPE_INVALID"

    # Carriage return
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"\n", b"\r\n"))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Missing trailing newline
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.rstrip(b"\n"))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad line count (< 5)
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(b"pip-chunk-proof 1\nblob pip1:t:00\n")
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad magic
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"pip-chunk-proof 1", b"pip-chunk-proof 2"))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad blob line
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"blob pip1:t:", b"blob pip1:m:"))
    assert exc.value.code == "ENVELOPE_INVALID"

    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"blob ", b"tree "))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad length line
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"length ", b"size "))
    assert exc.value.code == "ENVELOPE_INVALID"

    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"length 15", b"length -1"))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad index line
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"index ", b"chunk_idx "))
    assert exc.value.code == "ENVELOPE_INVALID"

    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"index 0", b"index -1"))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad chunk line
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(valid_bytes.replace(b"chunk ", b"data "))
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad base64
    lines = valid_bytes.decode("utf-8").split("\n")
    lines[4] = "chunk ZE=="
    bad_b64_data = "\n".join(lines).encode("utf-8")
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(bad_b64_data)
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad path entry
    lines = valid_bytes.decode("utf-8").split("\n")
    lines.insert(5, "path invalid_entry")
    bad_path_data = "\n".join(lines).encode("utf-8")
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(bad_path_data)
    assert exc.value.code == "ENVELOPE_INVALID"

    # Bad hex length in path
    lines = valid_bytes.decode("utf-8").split("\n")
    lines.insert(5, "path 0011")
    bad_hex_data = "\n".join(lines).encode("utf-8")
    with pytest.raises(AethelError) as exc:
        parse_chunk_proof(bad_hex_data)
    assert exc.value.code == "ENVELOPE_INVALID"


def test_verify_proof_tampered() -> None:
    data = b"Testing tampered verify proof"
    blob_pid = Pid.parse(text_id(data))
    proof = create_chunk_proof(data, blob_pid, 0)

    # Corrupt chunk bytes
    bad_chunk_proof = ChunkProof(
        blob_pid=proof.blob_pid,
        blob_length=proof.blob_length,
        chunk_index=proof.chunk_index,
        chunk=b"tampered",
        path=proof.path,
    )
    assert verify_proof(bad_chunk_proof) is False

    # Corrupt blob pid
    other_pid = Pid.parse("pip1:t:0000000000000000000000000000000000000000000000000000000000000000")
    bad_pid_proof = ChunkProof(
        blob_pid=other_pid,
        blob_length=proof.blob_length,
        chunk_index=proof.chunk_index,
        chunk=proof.chunk,
        path=proof.path,
    )
    assert verify_proof(bad_pid_proof) is False
