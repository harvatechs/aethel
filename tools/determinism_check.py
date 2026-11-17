"""Determinism verification script across runs and platforms (YP §11, release-and-deployment.md §4)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from aethel_codex.ctf1 import canonicalize
from aethel_codex.merkle import text_id
from aethel_codex.publish import PublishRequest, publish_bundle

EXPECTED_T2_TEXT_ID = "pip1:t:9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413"
T2_INPUT_HEX = "efbbbf43616665cc810d0a6c696e652074776f0d6c696e65207468726565"


def check_t2_determinism() -> bool:
    """Check T2 manuscript input canonicalization determinism."""
    t2_input = bytes.fromhex(T2_INPUT_HEX)
    canonical_bytes, _ = canonicalize(t2_input)
    t2_id = text_id(canonical_bytes)

    if t2_id != EXPECTED_T2_TEXT_ID:
        print(
            f"FAIL: T2 text ID mismatch: got {t2_id}, expected {EXPECTED_T2_TEXT_ID}",
            file=sys.stderr,
        )
        return False

    # Second pass must be identical (fixed point)
    canonical_pass2, _ = canonicalize(canonical_bytes)
    if canonical_pass2 != canonical_bytes or text_id(canonical_pass2) != EXPECTED_T2_TEXT_ID:
        print("FAIL: T2 fixed-point idempotence violation", file=sys.stderr)
        return False

    print("PASS: T2 canonical text and identifier determinism verified")
    return True


def check_publish_determinism() -> bool:
    """Check that publishing identical inputs produces identical manifest bytes and ID."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_path = Path(tmp_str)
        ms_path = tmp_path / "genesis.md"
        ms_path.write_bytes(b"# The Aethel Codex\n\nWrite once. Verify forever.\n")

        req1 = PublishRequest(
            manuscript_path=ms_path,
            title="The Aethel Codex",
            license="Apache-2.0",
            unsigned=True,
            dry_run=True,
        )
        res1 = publish_bundle(req1)

        req2 = PublishRequest(
            manuscript_path=ms_path,
            title="The Aethel Codex",
            license="Apache-2.0",
            unsigned=True,
            dry_run=True,
        )
        res2 = publish_bundle(req2)

        if res1.manifest_pid != res2.manifest_pid:
            print("FAIL: Multiple publish runs produced differing manifest IDs", file=sys.stderr)
            return False

        if res1.text_pid != res2.text_pid:
            print("FAIL: Multiple publish runs produced differing text IDs", file=sys.stderr)
            return False

    print("PASS: Publish manifest and text identifier determinism verified")
    return True


def main() -> int:
    """Run all determinism checks."""
    print("Running PIP-1 cross-platform determinism checks...")
    ok = check_t2_determinism() and check_publish_determinism()
    if ok:
        print("ALL DETERMINISM CHECKS PASSED")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
