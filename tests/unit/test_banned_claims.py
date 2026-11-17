"""Banned claims audit test (WP-16, UR-40, R-HON-01, what-not-to-do.md §4)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aethel_codex.errors import ERROR_CODE_REGISTRY

BANNED_PHRASES = [
    r"\bproves you wrote it\b",
    r"\bproof of authorship\b",
    r"\bproves when you had the idea\b",
    r"\btimestamped authorship\b",
    r"\btamper-proof\b",
    r"\bunalterable\b",
    r"\bquantum-proof\b",
    r"\bquantum-safe\b",
    r"\bunbreakable\b",
    r"\bverified author\b",
    r"\bverified identity\b",
    r"\bblockchain\b",
    r"\bdecentralized storage\b",
    r"\bimmutable ledger\b",
    r"\bweb3\b",
    r"\bmilitary-grade\b",
    r"\bunhackable\b",
]

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.req("UR-40")
def test_banned_claims_in_user_facing_documentation() -> None:
    """Verify that user-facing docs contain zero banned claims."""
    doc_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "tutorial.md",
        REPO_ROOT / "docs" / "verify-by-hand.md",
        REPO_ROOT / "docs" / "man-page.md",
    ]

    for doc_path in doc_files:
        assert doc_path.is_file(), f"Document missing: {doc_path}"
        text = doc_path.read_text(encoding="utf-8").lower()

        for pattern in BANNED_PHRASES:
            matches = re.findall(pattern, text)
            assert not matches, (
                f"Banned claim matching {pattern!r} found in {doc_path.name}: {matches}"
            )


@pytest.mark.req("UR-40")
def test_banned_claims_in_error_registry() -> None:
    """Verify that error messages and explanations contain zero banned claims."""
    from aethel_codex.cli.cmd_explain import _EXPLAIN_DETAILS

    for code, info in ERROR_CODE_REGISTRY.items():
        text = f"{info.code} {info.meaning} {info.yp_section}".lower()
        for pattern in BANNED_PHRASES:
            matches = re.findall(pattern, text)
            assert not matches, (
                f"Banned claim matching {pattern!r} found in error code {code}: {matches}"
            )

    for code, (cause, what_to_do, _) in _EXPLAIN_DETAILS.items():
        text = f"{cause} {what_to_do}".lower()
        for pattern in BANNED_PHRASES:
            matches = re.findall(pattern, text)
            assert not matches, (
                f"Banned claim matching {pattern!r} found in explain text for {code}: {matches}"
            )
