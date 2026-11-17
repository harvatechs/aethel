"""Differential tests between aethel_codex.verify and scripts/verify_minimal.py.

Normative reference: Yellow Paper PIP-YP-1 v1.0.0-rc.3, ADR-013,
docs/testing-and-conformance.md §5 (Differential and oracle tests).
Gate requirement: Minimal verifier and the package agree on all fixtures
and on 200 randomly tampered bundles (V1-V3 verdicts must agree).
"""

from __future__ import annotations

import importlib.util
import random
import shutil
import sys
from pathlib import Path

import pytest

from aethel_codex.verify import verify_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIFY_MINIMAL_PATH = REPO_ROOT / "scripts" / "verify_minimal.py"

_spec = importlib.util.spec_from_file_location("verify_minimal", VERIFY_MINIMAL_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load {VERIFY_MINIMAL_PATH}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["verify_minimal"] = _mod
_spec.loader.exec_module(_mod)
verify_bundle_minimal = _mod.verify_bundle_minimal

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _get_fixture_bundles() -> list[Path]:
    """Discover all bundle directories within tests/fixtures/."""
    bundles: list[Path] = []
    for fixture_dir in sorted(FIXTURES_DIR.iterdir()):
        if fixture_dir.is_dir():
            for child in sorted(fixture_dir.iterdir()):
                if child.is_dir() and (child / "manifest.pip").exists():
                    bundles.append(child)
    return bundles


@pytest.mark.req("UR-36")
def test_minimal_verifier_agrees_on_all_fixtures() -> None:
    """The minimal verifier and the package verifier agree on all 5 golden fixtures."""
    bundles = _get_fixture_bundles()
    assert len(bundles) == 5, f"Expected 5 fixture bundles, found {len(bundles)}"

    for bundle_path in bundles:
        pkg_report = verify_bundle(bundle_path)
        min_report = verify_bundle_minimal(bundle_path)

        assert min_report["v1"]["status"] == "PASS", f"V1 failed on {bundle_path.name}"
        assert min_report["v2"]["status"] == "PASS", f"V2 failed on {bundle_path.name}"
        assert min_report["v3"]["status"] == "PASS", f"V3 failed on {bundle_path.name}"
        assert min_report["integrity"] == "PASS", f"Integrity failed on {bundle_path.name}"

        pkg_checks = {c.id: c.status_value() for c in pkg_report.checks}
        assert pkg_checks["V1"] == min_report["v1"]["status"]
        assert pkg_checks["V2"] == min_report["v2"]["status"]
        assert pkg_checks["V3"] == min_report["v3"]["status"]
        assert pkg_report.integrity == min_report["integrity"]


def _apply_mutation(  # noqa: C901
    bundle_dir: Path, mutation_type: int, rng: random.Random
) -> None:
    """Apply one deterministic mutation to a cloned bundle directory."""
    manifest_path = bundle_dir / "manifest.pip"
    text_files = list(bundle_dir.glob("text.*"))
    text_path = text_files[0] if text_files else None
    assets_dir = bundle_dir / "assets"
    asset_files = list(assets_dir.glob("*")) if assets_dir.is_dir() else []

    if mutation_type == 0 and manifest_path.exists():
        # Flip 1 bit in manifest
        ba_manifest = bytearray(manifest_path.read_bytes())
        if ba_manifest:
            pos = rng.randint(0, len(ba_manifest) - 1)
            bit = rng.randint(0, 7)
            ba_manifest[pos] ^= 1 << bit
            manifest_path.write_bytes(bytes(ba_manifest))

    elif mutation_type == 1 and manifest_path.exists():
        # Truncate manifest
        b_manifest = manifest_path.read_bytes()
        if len(b_manifest) > 5:
            manifest_path.write_bytes(b_manifest[:-3])

    elif mutation_type == 2 and manifest_path.exists():
        # Delete manifest
        manifest_path.unlink()

    elif mutation_type == 3 and manifest_path.exists():
        # Append carriage return or malformed line to manifest
        manifest_path.write_bytes(manifest_path.read_bytes() + b"\r\n")

    elif mutation_type == 4 and text_path and text_path.exists():
        # Flip 1 bit in text
        ba_text = bytearray(text_path.read_bytes())
        if ba_text:
            pos = rng.randint(0, len(ba_text) - 1)
            bit = rng.randint(0, 7)
            ba_text[pos] ^= 1 << bit
            text_path.write_bytes(bytes(ba_text))

    elif mutation_type == 5 and text_path and text_path.exists():
        # Truncate text
        b_text = text_path.read_bytes()
        if len(b_text) > 2:
            text_path.write_bytes(b_text[:-2])

    elif mutation_type == 6 and text_path and text_path.exists():
        # Append bytes to text
        text_path.write_bytes(text_path.read_bytes() + b"extra\n")

    elif mutation_type == 7 and text_path and text_path.exists():
        # Delete text file
        text_path.unlink()

    elif mutation_type == 8 and text_path and text_path.exists():
        # Add CR to text
        b_cr = text_path.read_bytes()
        text_path.write_bytes(b_cr.replace(b"\n", b"\r\n"))

    elif mutation_type == 9 and asset_files:
        # Flip bit in asset file
        a_file = rng.choice(asset_files)
        ba_asset = bytearray(a_file.read_bytes())
        if ba_asset:
            pos = rng.randint(0, len(ba_asset) - 1)
            bit = rng.randint(0, 7)
            ba_asset[pos] ^= 1 << bit
            a_file.write_bytes(bytes(ba_asset))

    elif mutation_type == 10 and asset_files:
        # Truncate asset file
        a_file = rng.choice(asset_files)
        b_asset = a_file.read_bytes()
        if len(b_asset) > 2:
            a_file.write_bytes(b_asset[:-2])

    elif mutation_type == 11 and asset_files:
        # Delete asset file
        a_file = rng.choice(asset_files)
        a_file.unlink()

    elif mutation_type == 12:
        # Add unlisted extra file in assets
        assets_dir.mkdir(exist_ok=True)
        (assets_dir / "unlisted_extra.bin").write_bytes(b"extra asset content")

    elif mutation_type == 13:
        # Add extra text.* file
        (bundle_dir / "text.txt").write_bytes(b"extra alternative text\n")

    elif mutation_type == 14 and manifest_path.exists():
        # Mutate magic in manifest
        content = manifest_path.read_text(encoding="utf-8")
        manifest_path.write_bytes(
            content.replace("pip-manifest 1", "pip-manifest 2").encode("utf-8")
        )

    else:
        # Fallback: mutate directory name to another 64-hex string (ID_MISMATCH)
        pass


def test_minimal_verifier_agrees_on_200_tampered_bundles(tmp_path: Path) -> None:
    """The minimal verifier and package verifier agree on 200 randomly tampered bundles."""
    bundles = _get_fixture_bundles()
    rng = random.Random(1337)  # noqa: S311

    for i in range(200):
        # Choose a fixture base bundle
        base_bundle = bundles[i % len(bundles)]
        target_dir = tmp_path / f"tampered_{i}_{base_bundle.name}"
        shutil.copytree(base_bundle, target_dir)

        # Decide whether to rename the directory to simulate ID_MISMATCH
        if i % 15 == 0:
            fake_hex = f"{rng.getrandbits(256):064x}"
            new_target_dir = tmp_path / f"bundle_{i}_{fake_hex}"
            target_dir.rename(new_target_dir)
            target_dir = new_target_dir

        mutation_type = rng.randint(0, 14)
        _apply_mutation(target_dir, mutation_type, rng)

        pkg_report = verify_bundle(target_dir)
        min_report = verify_bundle_minimal(target_dir)

        pkg_checks = {c.id: c.status_value() for c in pkg_report.checks}

        # Compare V1, V2, V3, and Integrity
        v1_p = pkg_checks["V1"]
        v1_m = min_report["v1"]["status"]
        assert v1_p == v1_m, f"Iter {i} (mut {mutation_type}): V1 ({v1_p} vs {v1_m})"

        v2_p = pkg_checks["V2"]
        v2_m = min_report["v2"]["status"]
        assert v2_p == v2_m, f"Iter {i} (mut {mutation_type}): V2 ({v2_p} vs {v2_m})"

        v3_p = pkg_checks["V3"]
        v3_m = min_report["v3"]["status"]
        assert v3_p == v3_m, f"Iter {i} (mut {mutation_type}): V3 ({v3_p} vs {v3_m})"

        int_p = pkg_report.integrity
        int_m = min_report["integrity"]
        assert int_p == int_m, f"Iter {i} (mut {mutation_type}): Integrity ({int_p} vs {int_m})"
