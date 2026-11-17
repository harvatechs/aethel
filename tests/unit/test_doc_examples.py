"""Tests verifying that examples and tutorial commands execute correctly (WP-16, UR-32, UR-35)."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from aethel_codex.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    old_stdout, old_stderr = sys.stdout, sys.stderr
    out_buf, err_buf = io.StringIO(), io.StringIO()
    try:
        sys.stdout, sys.stderr = out_buf, err_buf
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    return rc, out_buf.getvalue(), err_buf.getvalue()


@pytest.mark.req("UR-32")
def test_example_script_runs() -> None:
    """Verify that examples/publish_and_verify.py runs and passes all assertions."""
    script_path = REPO_ROOT / "examples" / "publish_and_verify.py"
    res = subprocess.run(  # noqa: S603
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Verification successful!" in res.stdout


@pytest.mark.req("UR-35")
def test_readme_tutorial_workflow(tmp_path: Path) -> None:
    """Verify the 4-step tutorial workflow in README.md from start to finish."""
    # Step 1: Generate author key
    key_path = tmp_path / "author.aek"
    rc, _, _ = _run_cli(["keygen", "--out", str(key_path), "--no-passphrase"])
    assert rc == 0
    assert key_path.is_file()

    # Step 2: Publish manuscript
    essay_path = tmp_path / "essay.md"
    essay_path.write_bytes(b"# On Writing\n\nWords written with care.\n")
    bundles_dir = tmp_path / "bundles"

    rc, out, _ = _run_cli(
        [
            "publish",
            str(essay_path),
            "--title",
            "On Writing",
            "--license",
            "CC-BY-4.0",
            "--key",
            str(key_path),
            "--out-dir",
            str(bundles_dir),
            "--json",
        ]
    )
    assert rc == 0
    pub_data = json.loads(out)
    manifest_id = pub_data["manifest_id"]
    manifest_hex = manifest_id.split(":")[-1]
    bundle_path = bundles_dir / manifest_hex
    assert bundle_path.is_dir()

    # Step 3: Verify the bundle
    rc, out_ver, _ = _run_cli(["verify", str(bundle_path)])
    assert rc == 0
    assert "Integrity    PASS" in out_ver
    assert "Attributed (1 of 1)" in out_ver

    # Step 4: Detect tampering
    text_path = bundle_path / "text.md"
    content = text_path.read_bytes()
    text_path.write_bytes(content + b"tampered\n")

    rc, out_tamper, _ = _run_cli(["verify", str(bundle_path)])
    assert rc == 1
    assert "Integrity    FAIL" in out_tamper
    assert "V2 FAIL" in out_tamper


@pytest.mark.req("UR-35")
def test_tutorial_dual_family_and_revision(tmp_path: Path) -> None:
    """Verify dual-family signing and revision workflows described in tutorial.md."""
    # 1. Dual-family keys
    k1 = tmp_path / "lattice.aek"
    k2 = tmp_path / "stateless.aek"
    rc1, _, _ = _run_cli(["keygen", "--alg", "ml-dsa-87", "--out", str(k1), "--no-passphrase"])
    rc2, _, _ = _run_cli(
        ["keygen", "--alg", "slh-dsa-shake-256s", "--out", str(k2), "--no-passphrase"]
    )
    assert rc1 == 0
    assert rc2 == 0

    paper = tmp_path / "paper.md"
    paper.write_bytes(b"# Dual-Signed Paper\n\nVerified text.\n")
    bundles_dir = tmp_path / "bundles"

    rc, out, _ = _run_cli(
        [
            "publish",
            str(paper),
            "--title",
            "Dual-Signed Paper",
            "--license",
            "Apache-2.0",
            "--key",
            str(k1),
            "--key",
            str(k2),
            "--out-dir",
            str(bundles_dir),
            "--json",
        ]
    )
    assert rc == 0
    gen_data = json.loads(out)
    gen_hex = gen_data["manifest_id"].split(":")[-1]
    gen_bundle = bundles_dir / gen_hex

    rc_ver, out_ver, _ = _run_cli(["verify", str(gen_bundle)])
    assert rc_ver == 0
    assert "Dual-family (2 of 2)" in out_ver

    # 2. Revision
    rev_paper = tmp_path / "revised_paper.md"
    rev_paper.write_bytes(b"# Dual-Signed Paper (Second Edition)\n\nUpdated text.\n")

    rc_rev, out_rev, _ = _run_cli(
        [
            "revise",
            str(gen_bundle),
            str(rev_paper),
            "--title",
            "Dual-Signed Paper (Second Edition)",
            "--key",
            str(k1),
            "--out-dir",
            str(bundles_dir),
            "--json",
        ]
    )
    assert rc_rev == 0
    rev_data = json.loads(out_rev)
    rev_hex = rev_data["manifest_id"].split(":")[-1]
    rev_bundle = bundles_dir / rev_hex

    # Verify revision with parents
    rc_rev_ver, out_rev_ver, _ = _run_cli(
        ["verify", str(rev_bundle), "--parents", str(bundles_dir)]
    )
    assert rc_rev_ver == 0
    assert "V5 PASS" in out_rev_ver


@pytest.mark.req("UR-36")
def test_verify_by_hand_calculations() -> None:
    """Verify that the first-principles calculations in verify-by-hand.md work on golden fixture."""
    fixture_dir = FIXTURES_DIR / "genesis-attributed"
    manifest_hex = "e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
    bundle_dir = fixture_dir / manifest_hex

    # Step 1: Manifest ID calculation
    manifest_bytes = (bundle_dir / "manifest.pip").read_bytes()
    manifest_prefix = b"\x0dpip1.manifest"
    computed_manifest_id = hashlib.sha3_256(manifest_prefix + manifest_bytes).hexdigest()
    assert computed_manifest_id == manifest_hex

    # Step 2: Text ID calculation
    text_bytes = (bundle_dir / "text.md").read_bytes()
    leaf_prefix = b"\x09pip1.leaf"
    leaf_hash = hashlib.sha3_256(leaf_prefix + text_bytes).digest()
    text_prefix = b"\x09pip1.text"
    u64_len = len(text_bytes).to_bytes(8, "big")
    computed_text_id = hashlib.sha3_256(text_prefix + u64_len + leaf_hash).hexdigest()
    expected_text_id = "8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
    assert computed_text_id == expected_text_id
