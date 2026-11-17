"""TFP-1 chunk proof serialization, parsing, creation, and verification (specs.md §5, §13)."""

from dataclasses import dataclass

from aethel_codex.constants import (
    CHUNK_SIZE,
    LABEL_ASSET,
    LABEL_LEAF,
    LABEL_TEXT,
    MAX_ENVELOPE_BYTES,
)
from aethel_codex.envelope import strict_b64decode, strict_b64encode
from aethel_codex.errors import AethelError
from aethel_codex.hashing import H, u64be
from aethel_codex.merkle import audit_path, chunk_data, merkle_leaf, root_from_path
from aethel_codex.pid import Pid


@dataclass(frozen=True)
class ChunkProof:
    """TFP-1 Merkle chunk audit proof."""

    blob_pid: Pid
    blob_length: int
    chunk_index: int
    chunk: bytes
    path: tuple[bytes, ...]
    raw_bytes: bytes = b""


def create_chunk_proof(blob: bytes, blob_pid: Pid, chunk_index: int) -> ChunkProof:
    """Generate a TFP-1 chunk audit proof for the specified chunk of blob."""
    if chunk_index < 0:
        raise AethelError("ENVELOPE_INVALID", f"Negative chunk index: {chunk_index}")

    chunks = chunk_data(blob)
    if chunk_index >= len(chunks):
        raise AethelError(
            "ENVELOPE_INVALID",
            f"Chunk index {chunk_index} out of range (blob has {len(chunks)} chunks)",
        )

    leaves = [merkle_leaf(c) for c in chunks]
    path = tuple(audit_path(chunk_index, leaves))
    target_chunk = chunks[chunk_index]

    return ChunkProof(
        blob_pid=blob_pid,
        blob_length=len(blob),
        chunk_index=chunk_index,
        chunk=target_chunk,
        path=path,
    )


def serialize_chunk_proof(proof: ChunkProof) -> bytes:
    """Serialize ChunkProof into canonical TFP-1 UTF-8 bytes."""
    lines: list[str] = [
        "pip-chunk-proof 1",
        f"blob {proof.blob_pid}",
        f"length {proof.blob_length}",
        f"index {proof.chunk_index}",
        f"chunk {strict_b64encode(proof.chunk)}",
    ]
    for p in proof.path:
        lines.append(f"path {p.hex()}")
    return "\n".join(lines).encode("utf-8") + b"\n"


def _parse_path_lines(lines: list[str]) -> list[bytes]:
    path_hashes: list[bytes] = []
    for line_idx, line in enumerate(lines, start=6):
        if not line.startswith("path "):
            raise AethelError(
                "ENVELOPE_INVALID", f"Line {line_idx} must start with 'path ', got {line!r}"
            )
        hex_val = line[len("path ") :]
        if len(hex_val) != 64 or not all(c in "0123456789abcdef" for c in hex_val):
            raise AethelError(
                "ENVELOPE_INVALID", f"Invalid 64-hex path hash in line {line_idx}: {hex_val!r}"
            )
        path_hashes.append(bytes.fromhex(hex_val))
    return path_hashes


def _parse_proof_lines(
    lines: list[str],
) -> tuple[Pid, int, int, bytes, list[bytes]]:
    if len(lines) < 5:
        raise AethelError(
            "ENVELOPE_INVALID", f"Chunk proof must have at least 5 lines, got {len(lines)}"
        )

    if lines[0] != "pip-chunk-proof 1":
        raise AethelError("ENVELOPE_INVALID", f"Invalid chunk proof magic: {lines[0]!r}")

    if not lines[1].startswith("blob "):
        raise AethelError("ENVELOPE_INVALID", "Line 2 must start with 'blob '")
    blob_pid = Pid.parse(lines[1][len("blob ") :])
    if blob_pid.pid_type not in ("t", "a"):
        raise AethelError(
            "ENVELOPE_INVALID", f"Proof blob PID must be type 't' or 'a', got {blob_pid.pid_type!r}"
        )

    if not lines[2].startswith("length "):
        raise AethelError("ENVELOPE_INVALID", "Line 3 must start with 'length '")
    len_str = lines[2][len("length ") :]
    if not len_str.isdigit():
        raise AethelError("ENVELOPE_INVALID", f"Invalid length in chunk proof: {len_str!r}")
    blob_length = int(len_str)

    if not lines[3].startswith("index "):
        raise AethelError("ENVELOPE_INVALID", "Line 4 must start with 'index '")
    idx_str = lines[3][len("index ") :]
    if not idx_str.isdigit():
        raise AethelError("ENVELOPE_INVALID", f"Invalid index in chunk proof: {idx_str!r}")
    chunk_index = int(idx_str)

    if not lines[4].startswith("chunk "):
        raise AethelError("ENVELOPE_INVALID", "Line 5 must start with 'chunk '")
    chunk = strict_b64decode(lines[4][len("chunk ") :])
    path_hashes = _parse_path_lines(lines[5:])

    return blob_pid, blob_length, chunk_index, chunk, path_hashes


def parse_chunk_proof(data: bytes) -> ChunkProof:
    """Parse TFP-1 chunk proof bytes strictly."""
    if len(data) > MAX_ENVELOPE_BYTES:
        raise AethelError(
            "ENVELOPE_INVALID",
            f"Chunk proof exceeds maximum size {MAX_ENVELOPE_BYTES} bytes",
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise AethelError("ENVELOPE_INVALID", f"Invalid UTF-8 in chunk proof: {e}") from None

    if "\r" in text:
        raise AethelError("ENVELOPE_INVALID", "Carriage return is not permitted in chunk proof")
    if not text.endswith("\n"):
        raise AethelError("ENVELOPE_INVALID", "Chunk proof must end with a linefeed")

    lines = text.split("\n")[:-1]
    blob_pid, blob_length, chunk_index, chunk, path_hashes = _parse_proof_lines(lines)

    return ChunkProof(
        blob_pid=blob_pid,
        blob_length=blob_length,
        chunk_index=chunk_index,
        chunk=chunk,
        path=tuple(path_hashes),
        raw_bytes=data,
    )


def verify_proof(proof: ChunkProof) -> bool:
    """Verify a ChunkProof with the procedure in specs.md §5 and Yellow Paper §5.4."""
    blob_len = proof.blob_length
    m = proof.chunk_index
    n = (blob_len + CHUNK_SIZE - 1) // CHUNK_SIZE if blob_len > 0 else 1

    if m < 0 or m >= n:
        return False

    if blob_len == 0:
        expected_len = 0
    elif m < n - 1:
        expected_len = CHUNK_SIZE
    else:
        expected_len = blob_len - CHUNK_SIZE * (n - 1)

    if len(proof.chunk) != expected_len:
        return False

    h = H(LABEL_LEAF, proof.chunk)
    root = root_from_path(m, n, h, proof.path)
    if root is None:
        return False

    label = LABEL_TEXT if proof.blob_pid.pid_type == "t" else LABEL_ASSET
    expected_digest = H(label, u64be(blob_len) + root)

    return expected_digest == proof.blob_pid.digest
