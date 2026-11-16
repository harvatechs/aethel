"""Merkle tree calculation, streaming tree hasher, and chunk audit proofs (YP §5)."""

from collections.abc import Sequence

from aethel_codex.constants import CHUNK_SIZE, LABEL_ASSET, LABEL_LEAF, LABEL_NODE, LABEL_TEXT
from aethel_codex.hashing import H, u64be


def chunk_data(data: bytes) -> list[bytes]:
    """Split data into 4096-byte chunks.

    Empty data produces exactly one empty chunk [b""].
    Normative reference: Yellow Paper §5.1.
    """
    if not data:
        return [b""]
    return [data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]


def merkle_leaf(chunk: bytes) -> bytes:
    """Compute leaf hash for a chunk: H(LABEL_LEAF, chunk)."""
    return H(LABEL_LEAF, chunk)


def merkle_node(left: bytes, right: bytes) -> bytes:
    """Compute interior node hash: H(LABEL_NODE, left || right)."""
    return H(LABEL_NODE, left + right)


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    """Compute Merkle tree root recursively over leaves.

    Normative reference: Yellow Paper §5.2.
    """
    n = len(leaves)
    if n == 0:
        raise ValueError("leaves cannot be empty")
    if n == 1:
        return leaves[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return H(LABEL_NODE, merkle_root(leaves[:k]) + merkle_root(leaves[k:]))


class TreeHasher:
    """Streaming O(log n) memory Merkle tree hasher.

    Normative reference: Yellow Paper §5.2, specs.md §5.
    """

    def __init__(self) -> None:
        """Initialize empty tree hasher."""
        self._stack: list[tuple[int, bytes]] = []  # (height, hash); heights strictly decrease
        self._buf = bytearray()
        self.length = 0
        self._leaves = 0
        self._finished = False
        self._cached_root: bytes | None = None

    def _push(self, chunk: bytes) -> None:
        h, height = H(LABEL_LEAF, chunk), 0
        self._leaves += 1
        while self._stack and self._stack[-1][0] == height:
            _, left = self._stack.pop()
            h, height = H(LABEL_NODE, left + h), height + 1
        self._stack.append((height, h))

    def update(self, data: bytes) -> None:
        """Feed data bytes into tree hasher."""
        if self._finished:
            raise ValueError("TreeHasher already finalized")
        self.length += len(data)
        self._buf += data
        while len(self._buf) >= CHUNK_SIZE:
            self._push(bytes(self._buf[:CHUNK_SIZE]))
            del self._buf[:CHUNK_SIZE]

    def root(self) -> bytes:
        """Finalize and return Merkle root."""
        if self._finished and self._cached_root is not None:
            return self._cached_root
        if self._buf or self._leaves == 0:
            self._push(bytes(self._buf))
            self._buf.clear()
        acc = self._stack[-1][1]
        for _, h in reversed(self._stack[:-1]):
            acc = H(LABEL_NODE, h + acc)
        self._finished = True
        self._cached_root = acc
        return acc


def blob_root(data: bytes) -> bytes:
    """Compute Merkle tree root for data bytes."""
    hasher = TreeHasher()
    hasher.update(data)
    return hasher.root()


def blob_id(label: bytes, data: bytes) -> bytes:
    """Compute 32-byte blob identifier digest: H(label, u64be(len) || root).

    Normative reference: Yellow Paper §5.3.
    """
    return H(label, u64be(len(data)) + blob_root(data))


def text_id(data: bytes) -> str:
    """Compute canonical text PID: pip1:t:<hex>."""
    return f"pip1:t:{blob_id(LABEL_TEXT, data).hex()}"


def asset_id(data: bytes) -> str:
    """Compute asset PID: pip1:a:<hex>."""
    return f"pip1:a:{blob_id(LABEL_ASSET, data).hex()}"


def audit_path(m: int, leaves: Sequence[bytes]) -> list[bytes]:
    """Compute audit path for leaf index m (leaf level first).

    Normative reference: Yellow Paper §5.4.
    """
    n = len(leaves)
    if n <= 1:
        return []
    k = 1 << ((n - 1).bit_length() - 1)
    if m < k:
        return [*audit_path(m, leaves[:k]), merkle_root(leaves[k:])]
    return [*audit_path(m - k, leaves[k:]), merkle_root(leaves[:k])]


def root_from_path(m: int, n: int, h: bytes, path: Sequence[bytes]) -> bytes | None:
    """Reconstruct Merkle root from leaf hash and audit path.

    Returns None on structural path invalidity.
    Normative reference: Yellow Paper §5.4.
    """
    if n == 1:
        return h if not path else None
    if not path:
        return None
    k = 1 << ((n - 1).bit_length() - 1)
    s, rest = path[-1], path[:-1]
    if m < k:
        r = root_from_path(m, k, h, rest)
        return None if r is None else H(LABEL_NODE, r + s)
    r = root_from_path(m - k, n - k, h, rest)
    return None if r is None else H(LABEL_NODE, s + r)


def verify_chunk_proof(
    blob_length: int,
    m: int,
    chunk: bytes,
    path: Sequence[bytes],
    expected_root: bytes,
) -> bool:
    """Verify a chunk audit proof against expected Merkle root.

    Normative reference: Yellow Paper §5.4.
    """
    n = (blob_length + CHUNK_SIZE - 1) // CHUNK_SIZE if blob_length > 0 else 1
    if m < 0 or m >= n:
        return False

    if blob_length == 0:
        expected_len = 0
    elif m < n - 1:
        expected_len = CHUNK_SIZE
    else:
        expected_len = blob_length - CHUNK_SIZE * (n - 1)

    if len(chunk) != expected_len:
        return False

    h = H(LABEL_LEAF, chunk)
    computed_root = root_from_path(m, n, h, path)
    if computed_root is None:
        return False
    return computed_root == expected_root
