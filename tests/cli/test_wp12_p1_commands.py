"""Tests for WP-12: P1 commands (revise, cite, proof, attest) (cli-spec.md §3)."""

import json
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest

from aethel_codex.cli import main


@pytest.fixture
def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "src" / "aethel_codex" / "schemas"


@pytest.fixture
def cite_schema(schemas_dir: Path) -> dict[str, Any]:
    with open(schemas_dir / "cite.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture
def proof_schema(schemas_dir: Path) -> dict[str, Any]:
    with open(schemas_dir / "proof.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture
def attest_schema(schemas_dir: Path) -> dict[str, Any]:
    with open(schemas_dir / "attest.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture
def sample_bundle(tmp_path: Path) -> Path:
    """Publish a minimal genesis bundle for test operations."""
    manuscript = tmp_path / "genesis.md"
    manuscript.write_bytes(b"# Genesis Edition\n\nFirst draft text for testing.\n")
    asset_file = tmp_path / "figure.svg"
    asset_file.write_bytes(b"<svg>circle</svg>\n")

    out_dir = tmp_path / "bundles"
    rc = main(
        [
            "publish",
            str(manuscript),
            "--title",
            "Genesis Document",
            "--license",
            "CC0-1.0",
            "--lang",
            "en",
            "--unsigned",
            "--asset",
            str(asset_file),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    bundle_dirs = list(out_dir.iterdir())
    assert len(bundle_dirs) == 1
    return bundle_dirs[0]


# ==============================================================================
# 1. Revise Command Tests
# ==============================================================================


def test_revise_bundle_and_verify(
    sample_bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rev_manuscript = tmp_path / "rev.md"
    rev_manuscript.write_bytes(b"# Second Edition\n\nRevised draft with improvements.\n")

    out_dir = tmp_path / "rev_bundles"
    rc = main(
        [
            "revise",
            str(sample_bundle),
            str(rev_manuscript),
            "--unsigned",
            "--keep-assets",
            "--out-dir",
            str(out_dir),
            "--parents",
            str(sample_bundle.parent),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "Published   pip1:m:" in captured.out
    assert "Integrity PASS" in captured.out

    # Locate revised bundle
    rev_dirs = list(out_dir.iterdir())
    assert len(rev_dirs) == 1
    rev_bundle = rev_dirs[0]

    # Verify manifest has work and parent
    manifest_text = (rev_bundle / "manifest.pip").read_text(encoding="utf-8")
    assert f"parent pip1:m:{sample_bundle.name}\n" in manifest_text
    assert f"work pip1:m:{sample_bundle.name}\n" in manifest_text
    # Asset was kept
    assert (rev_bundle / "assets" / "figure.svg").exists()

    # Verify command with --parents passes V5
    rc_v = main(["verify", str(rev_bundle), "--parents", str(sample_bundle.parent)])
    assert rc_v == 0
    cap_v = capsys.readouterr()
    assert "Integrity    PASS" in cap_v.out
    assert "V5 PASS" in cap_v.out


def test_revise_bundle_json(
    sample_bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rev_manuscript = tmp_path / "rev2.md"
    rev_manuscript.write_bytes(b"Quick update\n")

    rc = main(
        [
            "revise",
            str(sample_bundle),
            str(rev_manuscript),
            "--unsigned",
            "--dry-run",
            "--json",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["schema"] == "aethel.publish/1"
    assert data["dry_run"] is True


# ==============================================================================
# 2. Cite Command Tests
# ==============================================================================


def test_cite_make(capsys: pytest.CaptureFixture[str], cite_schema: dict[str, Any]) -> None:
    pid = "pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"

    # Bare cite make
    rc = main(["cite", "make", pid])
    assert rc == 0
    cap = capsys.readouterr()
    assert cap.out.strip() == f"cite:{pid}"

    # Range cite make
    rc_range = main(["cite", "make", pid, "--range", "0-48"])
    assert rc_range == 0
    cap_range = capsys.readouterr()
    assert cap_range.out.strip() == f"cite:{pid}#b=0-48"

    # JSON mode
    rc_json = main(["cite", "make", pid, "--range", "10-20", "--json"])
    assert rc_json == 0
    cap_json = capsys.readouterr()
    data = json.loads(cap_json.out)
    jsonschema.validate(instance=data, schema=cite_schema)
    assert data["schema"] == "aethel.cite.make/1"
    assert data["target"] == pid
    assert data["locator"] == [10, 20]

    # Type k rejected
    k_pid = "pip1:k:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
    rc_k = main(["cite", "make", k_pid])
    assert rc_k == 3

    # Invalid range start >= end
    rc_bad_r = main(["cite", "make", pid, "--range", "20-10"])
    assert rc_bad_r == 3


def test_cite_check_and_show(
    sample_bundle: Path, capsys: pytest.CaptureFixture[str], cite_schema: dict[str, Any]
) -> None:
    text_pid = "pip1:t:18ee875eb07e0ff83beaa7925e0a6d5952f44766bb4ec836585145b23d9b0ca4"
    # Find real text pid from manifest
    m_lines = (sample_bundle / "manifest.pip").read_text(encoding="utf-8").splitlines()
    for line in m_lines:
        if line.startswith("text "):
            text_pid = line.split()[1]
            break

    valid_uri = f"cite:{text_pid}#b=0-17"
    rc_check = main(["cite", "check", valid_uri, "--bundle", str(sample_bundle)])
    assert rc_check == 0
    cap_check = capsys.readouterr()
    assert "Citation locator valid" in cap_check.out

    # JSON mode
    rc_check_json = main(["cite", "check", valid_uri, "--bundle", str(sample_bundle), "--json"])
    assert rc_check_json == 0
    cap_check_json = capsys.readouterr()
    data = json.loads(cap_check_json.out)
    jsonschema.validate(instance=data, schema=cite_schema)
    assert data["schema"] == "aethel.cite.check/1"
    assert data["valid"] is True

    # Range out of bounds
    invalid_uri = f"cite:{text_pid}#b=0-9999"
    rc_bad = main(["cite", "check", invalid_uri, "--bundle", str(sample_bundle)])
    assert rc_bad == 3

    # Cite show
    rc_show = main(["cite", "show", valid_uri, "--bundle", str(sample_bundle)])
    assert rc_show == 0
    cap_show = capsys.readouterr()
    assert cap_show.out.strip() == "# Genesis Edition"


# ==============================================================================
# 3. Proof Command Tests (TFP-1)
# ==============================================================================


def test_proof_make_and_verify(
    sample_bundle: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    proof_schema: dict[str, Any],
) -> None:
    proof_file = tmp_path / "text_chunk0.tfp"

    # Make proof for text chunk 0
    rc_make = main(["proof", "make", str(sample_bundle), "--chunk", "0", "-o", str(proof_file)])
    assert rc_make == 0
    assert proof_file.exists()

    content = proof_file.read_text(encoding="utf-8")
    assert content.startswith("pip-chunk-proof 1\n")
    assert "blob pip1:t:" in content
    assert "index 0\n" in content
    assert "chunk " in content

    # Verify genuine proof
    rc_ver = main(["proof", "verify", str(proof_file)])
    assert rc_ver == 0
    cap_ver = capsys.readouterr()
    assert "Proof valid: chunk 0" in cap_ver.out

    # Verify JSON mode
    rc_ver_json = main(["proof", "verify", str(proof_file), "--json"])
    assert rc_ver_json == 0
    cap_ver_json = capsys.readouterr()
    data = json.loads(cap_ver_json.out)
    jsonschema.validate(instance=data, schema=proof_schema)
    assert data["schema"] == "aethel.proof.verify/1"
    assert data["valid"] is True

    # Forged proof fails: mutate chunk bytes while keeping valid base64
    from aethel_codex.envelope import strict_b64decode, strict_b64encode

    lines = content.splitlines()
    for idx, line_text in enumerate(lines):
        if line_text.startswith("chunk "):
            raw_c = bytearray(strict_b64decode(line_text[len("chunk ") :]))
            raw_c[0] ^= 0x01
            lines[idx] = f"chunk {strict_b64encode(bytes(raw_c))}"
            break
    tampered_file = tmp_path / "tampered.tfp"
    tampered_file.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    rc_forge = main(["proof", "verify", str(tampered_file)])
    assert rc_forge == 1
    cap_forge = capsys.readouterr()
    assert "Proof failed:" in cap_forge.out


def test_proof_asset_chunk(
    sample_bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    asset_proof = tmp_path / "asset.tfp"
    rc_make = main(
        [
            "proof",
            "make",
            str(sample_bundle),
            "--asset",
            "figure.svg",
            "--chunk",
            "0",
            "-o",
            str(asset_proof),
        ]
    )
    assert rc_make == 0

    rc_ver = main(["proof", "verify", str(asset_proof)])
    assert rc_ver == 0
    cap = capsys.readouterr()
    assert "Proof valid: chunk 0 of pip1:a:" in cap.out


# ==============================================================================
# 4. Attest Command Tests (ATT-1)
# ==============================================================================


def test_attest_add_and_verify(
    sample_bundle: Path, capsys: pytest.CaptureFixture[str], attest_schema: dict[str, Any]
) -> None:
    proof_b64 = "dGVzdC1hdHRlc3RhdGlvbi1wcm9vZg=="

    rc_add = main(
        [
            "attest",
            "add",
            str(sample_bundle),
            "--kind",
            "rfc3161",
            "--proof-b64",
            proof_b64,
            "--json",
        ]
    )
    assert rc_add == 0
    cap_add = capsys.readouterr()
    data = json.loads(cap_add.out)
    jsonschema.validate(instance=data, schema=attest_schema)
    assert data["schema"] == "aethel.attest.add/1"
    assert data["kind"] == "rfc3161"
    assert data["file"] == "attestations/rfc3161.att"

    # Attestation file exists in bundle
    att_file = sample_bundle / "attestations" / "rfc3161.att"
    assert att_file.is_file()
    att_text = att_file.read_text(encoding="utf-8")
    assert att_text.startswith("pip-attestation 1\n")
    assert f"manifest pip1:m:{sample_bundle.name}\n" in att_text
    assert "kind rfc3161\n" in att_text

    # Verify bundle: attestation is reported as present and unverified (V8 ATT_UNVERIFIED)
    rc_v = main(["verify", str(sample_bundle)])
    assert rc_v == 0
    cap_v = capsys.readouterr()
    assert "Integrity    PASS" in cap_v.out
    assert "attestation present, unverified" in cap_v.out
    assert "V8 WARN" in cap_v.out

    rc_v_json = main(["verify", str(sample_bundle), "--json"])
    assert rc_v_json == 0
    cap_v_json = capsys.readouterr()
    v_data = json.loads(cap_v_json.out)
    assert v_data["time"]["status"] == "WARN"
    assert v_data["time"]["reason"] == "ATT_UNVERIFIED"
    assert v_data["time"]["items"][0]["status"] == "UNVERIFIED"
    assert v_data["time"]["items"][0]["kind"] == "attestation"
