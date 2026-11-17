"""DoS mitigation and resource limits tests (YP §12, security.md §5, specs.md §12)."""

from __future__ import annotations

from pathlib import Path

from aethel_codex.limits import Limits
from aethel_codex.verify import verify_bundle

VALID_MANIFEST_TEMPLATE = (
    "pip-manifest 1\n"
    "profile pip-1\n"
    "markup pip-md-1\n"
    "lang en\n"
    "title Limit Test\n"
    "license CC0-1.0\n"
    "text pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba 48\n"
)


T1_TEXT = b"# The Aethel Codex\n\nWrite once. Verify forever.\n"


def test_manifest_size_limit_exceeded(tmp_path: Path) -> None:
    """Manifest exceeding max_manifest_bytes reports SKIPPED:LIMIT_EXCEEDED and INCONCLUSIVE."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.pip").write_bytes(VALID_MANIFEST_TEMPLATE.encode("utf-8"))
    (bundle_dir / "text.md").write_bytes(T1_TEXT)

    # Restrict manifest limit to below template size
    strict_limits = Limits(max_manifest_bytes=50)
    report = verify_bundle(bundle_dir, limits=strict_limits)

    v1 = report.checks[0]
    assert v1.status_value() == "SKIPPED"
    assert v1.code == "LIMIT_EXCEEDED"
    assert report.integrity == "INCONCLUSIVE"
    assert report.exit_code == 6


def test_text_size_limit_exceeded(tmp_path: Path) -> None:
    """Text file exceeding max_text_bytes reports SKIPPED:LIMIT_EXCEEDED and INCONCLUSIVE."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.pip").write_bytes(VALID_MANIFEST_TEMPLATE.encode("utf-8"))
    (bundle_dir / "text.md").write_bytes(T1_TEXT)

    # Restrict text limit to below text size
    strict_limits = Limits(max_text_bytes=10)
    report = verify_bundle(bundle_dir, limits=strict_limits)

    v1 = report.checks[0]
    v2 = report.checks[1]
    assert v1.status_value() == "PASS"
    assert v2.status_value() == "SKIPPED"
    assert v2.code == "LIMIT_EXCEEDED"
    assert report.integrity == "INCONCLUSIVE"
    assert report.exit_code == 6


def test_asset_size_limit_exceeded(tmp_path: Path) -> None:
    """Asset file exceeding max_asset_bytes reports SKIPPED:LIMIT_EXCEEDED and INCONCLUSIVE."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    zero_aid = "pip1:a:0000000000000000000000000000000000000000000000000000000000000000"
    manifest_lines = (
        VALID_MANIFEST_TEMPLATE + f"asset large.bin {zero_aid} 1000 application/octet-stream\n"
    )
    (bundle_dir / "manifest.pip").write_bytes(manifest_lines.encode("utf-8"))
    (bundle_dir / "text.md").write_bytes(T1_TEXT)
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "large.bin").write_bytes(b"x" * 1000)

    # Restrict asset limit to 500 bytes
    strict_limits = Limits(max_asset_bytes=500)
    report = verify_bundle(bundle_dir, limits=strict_limits)

    v3 = report.checks[2]
    assert v3.status_value() == "SKIPPED"
    assert v3.code == "LIMIT_EXCEEDED"
    assert report.integrity == "INCONCLUSIVE"
    assert report.exit_code == 6


def test_dir_entry_limit_exceeded(tmp_path: Path) -> None:
    """Directory exceeding max_dir_entries triggers LIMIT_EXCEEDED."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.pip").write_bytes(VALID_MANIFEST_TEMPLATE.encode("utf-8"))
    (bundle_dir / "text.md").write_bytes(T1_TEXT)

    # Add extra files
    for i in range(10):
        (bundle_dir / f"extra_{i}.txt").write_bytes(b"hello")

    strict_limits = Limits(max_dir_entries=5)
    report = verify_bundle(bundle_dir, limits=strict_limits)

    assert report.checks[0].status_value() == "SKIPPED"
    assert report.checks[0].code == "LIMIT_EXCEEDED"
    assert report.integrity == "INCONCLUSIVE"
    assert report.exit_code == 6


def test_huge_claimed_length_overflow_guard(tmp_path: Path) -> None:
    """Huge declared length (e.g. 2^64 - 1 or integer > 2^64 - 1) is rejected safely."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()

    # Case 1: uint > 2^64 - 1
    tpid = "pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
    overflow_manifest = (
        "pip-manifest 1\n"
        "profile pip-1\n"
        "markup pip-md-1\n"
        "lang en\n"
        "title Overflow Test\n"
        "license CC0-1.0\n"
        f"text {tpid} 18446744073709551616\n"
    )
    (bundle_dir / "manifest.pip").write_bytes(overflow_manifest.encode("utf-8"))
    report1 = verify_bundle(bundle_dir)
    assert report1.checks[0].status_value() == "FAIL"
    assert report1.checks[0].code == "MANIFEST_INVALID"

    # Case 2: exactly 2^64 - 1 (valid grammar, but file size mismatch)
    tpid = "pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
    max_uint_manifest = (
        "pip-manifest 1\n"
        "profile pip-1\n"
        "markup pip-md-1\n"
        "lang en\n"
        "title Max Uint Test\n"
        "license CC0-1.0\n"
        f"text {tpid} 18446744073709551615\n"
    )
    (bundle_dir / "manifest.pip").write_bytes(max_uint_manifest.encode("utf-8"))
    (bundle_dir / "text.md").write_bytes(b"# Real Text\nSmall file\n")
    report2 = verify_bundle(bundle_dir)
    assert report2.checks[0].status_value() == "PASS"
    assert report2.checks[1].status_value() == "FAIL"
    assert report2.checks[1].code == "TEXT_LENGTH"
