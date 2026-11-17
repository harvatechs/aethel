"""Tamper matrix tests (YP §11, testing-and-conformance.md §6)."""

import os
import shutil
from pathlib import Path

import pytest

from aethel_codex.limits import Limits
from aethel_codex.verify import verify_bundle

FIXTURES_DIR = Path("tests/fixtures")


def _copy_bundle(scenario: str, tmp_path: Path) -> Path:
    scenario_dir = FIXTURES_DIR / scenario
    # Find 64-hex dir
    for item in scenario_dir.iterdir():
        if item.is_dir() and len(item.name) == 64:
            dest = tmp_path / item.name
            shutil.copytree(item, dest)
            return dest
    raise FileNotFoundError(f"No bundle directory found in {scenario_dir}")


def _flip_byte_at(file_path: Path, offset: int) -> None:
    data = bytearray(file_path.read_bytes())
    data[offset] ^= 0x01
    file_path.write_bytes(bytes(data))


@pytest.mark.req("UR-22")
def test_tamper_manifest_bit_flip(tmp_path: Path) -> None:
    """Bit flip in manifest.pip causes V1 FAIL and integrity FAIL."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    manifest_path = bundle / "manifest.pip"
    manifest_len = len(manifest_path.read_bytes())

    for offset in [0, manifest_len // 2, manifest_len - 1]:
        test_dir = tmp_path / f"manifest_flip_{offset}" / bundle.name
        shutil.copytree(bundle, test_dir)
        _flip_byte_at(test_dir / "manifest.pip", offset)

        report = verify_bundle(test_dir)
        assert report.integrity == "FAIL"
        checks = report.checks_dict()
        assert checks["V1"].startswith("FAIL:")
        assert report.exit_code == 1


def test_tamper_text_bit_flip(tmp_path: Path) -> None:
    """Bit flip in text.md causes V2 FAIL and integrity FAIL."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    text_path = bundle / "text.md"
    text_len = len(text_path.read_bytes())

    for offset in [0, text_len // 2, text_len - 1]:
        test_dir = tmp_path / f"text_flip_{offset}"
        shutil.copytree(bundle, test_dir)
        _flip_byte_at(test_dir / "text.md", offset)

        report = verify_bundle(test_dir)
        assert report.integrity == "FAIL"
        checks = report.checks_dict()
        assert checks["V2"].startswith("FAIL:")
        assert report.exit_code == 1


def test_tamper_asset_bit_flip(tmp_path: Path) -> None:
    """Bit flip in asset causes V3 FAIL and integrity FAIL."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    asset_path = bundle / "assets" / "figure1.svg"
    asset_len = len(asset_path.read_bytes())

    for offset in [0, asset_len // 2, asset_len - 1]:
        test_dir = tmp_path / f"asset_flip_{offset}"
        shutil.copytree(bundle, test_dir)
        _flip_byte_at(test_dir / "assets" / "figure1.svg", offset)

        report = verify_bundle(test_dir)
        assert report.integrity == "FAIL"
        checks = report.checks_dict()
        assert checks["V3"].startswith("FAIL:")
        assert report.exit_code == 1


def test_tamper_signature_bit_flip(tmp_path: Path) -> None:
    """Bit flip in signature envelope leaves integrity PASS, but V6 FAILS."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    sig_dir = bundle / "signatures"
    sig_file = next(sig_dir.glob("*.sig"))
    sig_len = len(sig_file.read_bytes())

    test_dir = tmp_path / "sig_flip"
    shutil.copytree(bundle, test_dir)
    target_sig = next((test_dir / "signatures").glob("*.sig"))
    _flip_byte_at(target_sig, sig_len // 2)

    report = verify_bundle(test_dir)
    assert report.integrity == "PASS"  # Signature corruption does NOT fail integrity!
    checks = report.checks_dict()
    assert checks["V6"].startswith("FAIL:")
    # Attribution falls to Unattributed
    assert report.attribution.cls == "Unattributed"
    assert report.attribution.signed == 0


def test_structural_missing_manifest(tmp_path: Path) -> None:
    """Deleted manifest.pip causes V1 FAIL MANIFEST_MISSING and dependent checks skipped."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    os.remove(bundle / "manifest.pip")

    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    checks = report.checks_dict()
    assert checks["V1"] == "FAIL:MANIFEST_MISSING"
    assert checks["V2"] == "SKIPPED:DEPENDS_ON_V1"
    assert checks["V3"] == "SKIPPED:DEPENDS_ON_V1"


def test_structural_missing_text(tmp_path: Path) -> None:
    """Deleted text causes V2 FAIL TEXT_MISSING."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    os.remove(bundle / "text.md")

    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    checks = report.checks_dict()
    assert checks["V2"] == "FAIL:TEXT_MISSING"


def test_structural_missing_asset(tmp_path: Path) -> None:
    """Deleted asset causes V3 FAIL ASSET_MISSING."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    os.remove(bundle / "assets" / "figure1.svg")

    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    checks = report.checks_dict()
    assert checks["V3"] == "FAIL:ASSET_MISSING"


def test_structural_extra_asset(tmp_path: Path) -> None:
    """Extra unlisted asset causes V3 WARN ASSET_EXTRA, but integrity PASS."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    extra_file = bundle / "assets" / "unlisted.png"
    extra_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    report = verify_bundle(bundle)
    assert report.integrity == "PASS"
    checks = report.checks_dict()
    assert checks["V3"] == "WARN:ASSET_EXTRA"


def test_structural_extra_signature_file(tmp_path: Path) -> None:
    """Extra non-.sig file in signatures causes V6 WARN EXTRA_FILE."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    (bundle / "signatures" / "notes.txt").write_text("random file", encoding="utf-8")

    report = verify_bundle(bundle)
    assert report.integrity == "PASS"
    checks = report.checks_dict()
    assert checks["V6"] == "WARN:EXTRA_FILE"


def test_structural_directory_rename_hex_and_non_hex(tmp_path: Path) -> None:
    """Renaming directory to other 64-hex causes ID_MISMATCH; renaming to non-hex does not."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)

    # Rename to another 64-hex
    other_hex_dir = tmp_path / ("ff" * 32)
    bundle.rename(other_hex_dir)
    report_hex = verify_bundle(other_hex_dir)
    assert report_hex.checks_dict()["V1"].startswith("FAIL:ID_MISMATCH")

    # Rename to non-hex name (e.g. "my-bundle")
    non_hex_dir = tmp_path / "my-bundle"
    other_hex_dir.rename(non_hex_dir)
    report_non_hex = verify_bundle(non_hex_dir)
    assert report_non_hex.checks_dict()["V1"] == "PASS"


def test_limits_exceeded(tmp_path: Path) -> None:
    """Exceeding text limits causes SKIPPED:LIMIT_EXCEEDED and integrity INCONCLUSIVE."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    tight_limits = Limits(max_text_bytes=10)  # text is 200 bytes

    report = verify_bundle(bundle, limits=tight_limits)
    assert report.integrity == "INCONCLUSIVE"
    assert report.checks_dict()["V2"] == "SKIPPED:LIMIT_EXCEEDED"
    assert report.exit_code == 6


def test_symlink_detection(tmp_path: Path) -> None:
    """Replacing manifest with symlink triggers UNSAFE_PATH."""
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    real_manifest = tmp_path / "real_manifest.pip"
    (bundle / "manifest.pip").rename(real_manifest)
    try:
        os.symlink(real_manifest, bundle / "manifest.pip")
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this host without elevation")

    report = verify_bundle(bundle)
    assert report.checks_dict()["V1"] == "FAIL:UNSAFE_PATH"
