"""Security controls and threat model tests (YP §12, security.md, testing-and-conformance.md §7)."""

from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

from aethel_codex.citations import scan_inline_citations
from aethel_codex.cli import main
from aethel_codex.cli.ui import sanitize_terminal_text
from aethel_codex.errors import AethelError
from aethel_codex.publish import AssetInput, PublishRequest, publish_bundle
from aethel_codex.verify import verify_bundle

REPO_SRC = Path(__file__).resolve().parent.parent.parent / "src" / "aethel_codex"
BANNED_MODULES = {"socket", "urllib", "http", "ssl", "requests", "subprocess"}


def test_no_network_or_subprocess_imports_ast() -> None:
    """Verify that no file in src/aethel_codex/ imports banned network or subprocess modules."""
    assert REPO_SRC.is_dir(), f"Source directory not found: {REPO_SRC}"

    for py_file in REPO_SRC.rglob("*.py"):
        tree = ast.parse(py_file.read_bytes(), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    assert root_mod not in BANNED_MODULES, (
                        f"Banned import {alias.name!r} in {py_file.relative_to(REPO_SRC)}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_mod = node.module.split(".")[0]
                assert root_mod not in BANNED_MODULES, (
                    f"Banned import from {node.module!r} in {py_file.relative_to(REPO_SRC)}"
                )


def test_secrets_hygiene_in_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that private keys, seeds, and passphrases never leak to stdout, stderr, or JSON."""
    pass_file = tmp_path / "passphrase.txt"
    test_passphrase = "UltraSecretPassphrase123!@#"  # noqa: S105
    pass_file.write_bytes(test_passphrase.encode("utf-8") + b"\n")

    key_file = tmp_path / "author.aek"
    rc_keygen = main(
        [
            "keygen",
            "--out",
            str(key_file),
            "--alg",
            "ml-dsa-87",
            "--passphrase-file",
            str(pass_file),
        ]
    )
    assert rc_keygen == 0
    cap_keygen = capsys.readouterr()

    # Passphrase must not be present in output
    assert test_passphrase not in cap_keygen.out
    assert test_passphrase not in cap_keygen.err

    # Key file content: raw secret should be encrypted
    key_bytes = key_file.read_bytes()
    assert test_passphrase.encode("utf-8") not in key_bytes

    # Manuscript publish & sign
    ms = tmp_path / "secret_paper.md"
    ms.write_bytes(b"# Research Findings\nConfidential experiment.\n")
    out_dir = tmp_path / "published"

    rc_pub = main(
        [
            "publish",
            str(ms),
            "--out-dir",
            str(out_dir),
            "--title",
            "Research Paper",
            "--license",
            "CC0-1.0",
            "--key",
            str(key_file),
            "--passphrase-file",
            str(pass_file),
        ]
    )
    assert rc_pub == 0
    cap_pub = capsys.readouterr()

    assert test_passphrase not in cap_pub.out
    assert test_passphrase not in cap_pub.err


def test_redos_guard_inline_scanner() -> None:
    """Verify that scanner does not backtrack exponentially on crafted input (ReDoS guard)."""
    # 10 MB payload of repeated partial citation patterns
    repeated_prefix = "cite:pip1:t:" * 100_000
    noise = "This is not a cite: nor is it cite:pip1:x:12345678 " * 20_000
    huge_text = f"{repeated_prefix}\n{noise}\ncite:pip1:t:{'a' * 64}\n"

    start = time.perf_counter()
    matches = scan_inline_citations(huge_text)
    elapsed = time.perf_counter() - start

    assert len(matches) == 1
    assert str(matches[0]) == f"pip1:t:{'a' * 64}"
    assert elapsed < 2.0, f"Inline citation scan exceeded 2.0s: took {elapsed:.3f}s"


def test_terminal_injection_sanitization() -> None:
    """Verify that terminal control codes, bidi overrides, and tag characters are escaped."""
    malicious_inputs = [
        "Normal Title \x1b[31;1mRED_ALERT\x1b[0m",  # ANSI CSI sequence
        "Link \x1b]8;;http://malicious.example.com\x1b\\Click\x1b]8;;\x1b\\",  # OSC 8
        "Bidi \u202eReversedText\u202c",  # Right-to-Left Override
        "Tag \U000e0001HiddenTag",  # Unicode Tag character
        "Control \x07\x08\x0b\x0c",  # Bell, Backspace, Vertical Tab, Form Feed
    ]

    for raw in malicious_inputs:
        sanitized = sanitize_terminal_text(raw)
        # Raw ESC must never survive in sanitized string
        assert "\x1b" not in sanitized
        # Bidi overrides must be escaped
        assert "\u202e" not in sanitized
        # Tags must be escaped
        assert "\U000e0001" not in sanitized


def test_asset_case_collision_refused(tmp_path: Path) -> None:
    """Refuse publishing assets that differ only in case on case-insensitive filesystems."""
    ms = tmp_path / "manuscript.md"
    ms.write_bytes(b"# Case Test\nTesting case collision.\n")

    asset1 = tmp_path / "diagram.png"
    asset2 = tmp_path / "DIAGRAM.PNG"
    asset1.write_bytes(b"content1")
    asset2.write_bytes(b"content2")

    out_bundle = tmp_path / "case_bundle"
    req = PublishRequest(
        manuscript_path=ms,
        title="Case Test",
        license="CC0-1.0",
        unsigned=True,
        assets=[AssetInput(asset1), AssetInput(asset2)],
        out_dir=out_bundle,
    )
    with pytest.raises(AethelError) as exc_info:
        publish_bundle(req)
    assert exc_info.value.code in ("ASSET_NAME_COLLISION", "E_NOT_SORTED_OR_UNIQUE")


def test_traversal_in_asset_names_rejected(tmp_path: Path) -> None:
    """Refuse assets with path traversal elements or backslashes."""
    ms = tmp_path / "manuscript.md"
    ms.write_bytes(b"# Traversal Test\n")

    # Creating a bundle with invalid asset name in manifest
    bundle_dir = tmp_path / "bad_bundle"
    bundle_dir.mkdir()
    bad_asset_pid = "pip1:a:0000000000000000000000000000000000000000000000000000000000000000"
    manifest_lines = (
        "pip-manifest 1\n"
        "profile pip-1\n"
        "markup pip-md-1\n"
        "lang en\n"
        "title Traversal Test\n"
        "license CC0-1.0\n"
        "text pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba 48\n"
        f"asset ../secret.txt {bad_asset_pid} 10 text/plain\n"
    )
    (bundle_dir / "manifest.pip").write_bytes(manifest_lines.encode("utf-8"))

    report = verify_bundle(bundle_dir)
    assert report.checks[0].status_value() == "FAIL"
    assert report.checks[0].code == "MANIFEST_INVALID"
