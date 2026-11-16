"""Citation URI parsing, inline scanning, and byte locator range verification (YP §6.3)."""

import re
from dataclasses import dataclass

from aethel_codex.errors import CitationError
from aethel_codex.pid import Pid

MAX_UINT64 = 18446744073709551615

# Normative regexes from specs.md §6
CITE_RE = re.compile(r"cite:(pip1:[mta]:[0-9a-f]{64})(?:#b=(0|[1-9][0-9]*)-(0|[1-9][0-9]*))?")
INLINE_RE = re.compile(r"(?<![A-Za-z0-9+.\-])cite:pip1:([mta]):([0-9a-f]{64})(?![0-9A-Fa-f])")


@dataclass(frozen=True)
class Citation:
    """Citation URI pointing to a manifest, text, or asset, with optional byte locator."""

    target: Pid
    locator: tuple[int, int] | None = None  # (start, end) byte range [start, end)

    def __str__(self) -> str:
        """Format canonical citation URI string."""
        base = f"cite:{self.target}"
        if self.locator is not None:
            return f"{base}#b={self.locator[0]}-{self.locator[1]}"
        return base


def parse_citation(s: str) -> Citation:
    """Parse citation URI using strict grammar matching.

    Type k is rejected. Upper-case hex is rejected.
    Offsets with leading zeros, start >= end, or > 2^64-1 are rejected with CITE_SYNTAX.
    Normative reference: Yellow Paper §6.3, specs.md §6.
    """
    match = CITE_RE.fullmatch(s)
    if not match:
        raise CitationError("CITE_SYNTAX", f"Malformed citation URI: {s!r}")

    target_pid = Pid.parse(match.group(1))

    start_str = match.group(2)
    end_str = match.group(3)

    if start_str is not None and end_str is not None:
        start = int(start_str)
        end = int(end_str)
        if start > MAX_UINT64 or end > MAX_UINT64:
            raise CitationError("CITE_SYNTAX", f"Citation byte offset exceeds 2^64 - 1: {s!r}")
        if start >= end:
            raise CitationError(
                "CITE_SYNTAX", f"Citation start offset {start} >= end offset {end}: {s!r}"
            )
        locator: tuple[int, int] | None = (start, end)
    else:
        locator = None

    return Citation(target=target_pid, locator=locator)


def validate_citation_range(citation: Citation, blob: bytes) -> bool:
    """Verify that a citation byte locator is valid for the target blob.

    For text (t) and manifest (m) blobs, start and end must fall on UTF-8 scalar boundaries.
    Normative reference: Yellow Paper §6.3.

    Raises:
        CitationError: With code CITE_RANGE if bounds or UTF-8 boundaries are violated.
    """
    if citation.locator is None:
        return True

    start, end = citation.locator
    blob_len = len(blob)

    if end > blob_len:
        raise CitationError(
            "CITE_RANGE",
            f"Citation end offset {end} exceeds blob length {blob_len}",
        )

    # For text and manifest blobs, ensure start and end do not split UTF-8 multi-byte sequences
    if citation.target.pid_type in ("m", "t"):
        if 0x80 <= blob[start] <= 0xBF:
            raise CitationError(
                "CITE_RANGE",
                f"Citation start offset {start} falls on "
                f"a UTF-8 continuation byte (0x{blob[start]:02X})",
            )
        if end < blob_len and (0x80 <= blob[end] <= 0xBF):
            raise CitationError(
                "CITE_RANGE",
                f"Citation end offset {end} falls on a UTF-8 continuation byte (0x{blob[end]:02X})",
            )

    return True


def scan_inline_citations(text: str) -> list[Pid]:
    """Scan text for inline citation references (lexical search, ignoring locators).

    Normative reference: Yellow Paper §6.3, specs.md §6.
    """
    results: list[Pid] = []
    for match in INLINE_RE.finditer(text):
        pid_type = match.group(1)
        digest = bytes.fromhex(match.group(2))
        results.append(Pid.create(pid_type, digest))
    return results
