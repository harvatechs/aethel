"""Smoke test for wheel installation and verification in a clean virtual environment (WP-15).

Verifies:
1. Wheel archive contains only permitted package files and data (no tests, fixtures, docs).
2. Clean virtual environment creation.
3. Installation of the built wheel via pip into the clean virtual environment.
4. Offline execution of `aethel selftest` in the clean environment.
5. Verification of a golden bundle fixture (`tests/fixtures/genesis-attributed`) using the installed CLI.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def verify_wheel_contents(wheel_path: Path) -> None:
    """Inspect wheel archive and assert strictly permitted files."""
    print(f"Inspecting wheel contents: {wheel_path.name}...")
    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()

    permitted_prefixes = ("aethel_codex/", "aethel_codex-")
    forbidden_substrings = ("tests/", "fixtures/", "docs/", "tools/", "scripts/")

    for name in names:
        if not any(name.startswith(p) for p in permitted_prefixes):
            msg = f"Forbidden file outside permitted root in wheel: {name}"
            raise ValueError(msg)
        if any(f in name for f in forbidden_substrings):
            msg = f"Forbidden artifact packaged in wheel: {name}"
            raise ValueError(msg)

    # Check that required package data is present
    required_entries = (
        "aethel_codex/py.typed",
        "aethel_codex/data/pip1-vectors.json",
        "aethel_codex/data/pip1-slh-dsa-vectors.json",
        "aethel_codex/schemas/verify.json",
        "aethel_codex/schemas/selftest.json",
    )
    for req in required_entries:
        if req not in names:
            msg = f"Required package data missing from wheel: {req}"
            raise ValueError(msg)

    print(f"PASS: Wheel archive structure valid ({len(names)} files)")


def run_cmd(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and check return code."""
    res = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"Command failed ({res.returncode}): {' '.join(args)}", file=sys.stderr)
        print("STDOUT:", res.stdout, file=sys.stderr)
        print("STDERR:", res.stderr, file=sys.stderr)
        sys.exit(res.returncode)
    return res


def smoke_test_wheel(wheel_path: Path, repo_root: Path) -> None:
    """Create a clean virtual environment and smoke test the installed wheel."""
    verify_wheel_contents(wheel_path)

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        venv_dir = tmp_dir / "smoke_venv"

        print(f"Creating clean virtual environment at {venv_dir}...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])

        if os.name == "nt":
            pip_exe = venv_dir / "Scripts" / "pip.exe"
            aethel_exe = venv_dir / "Scripts" / "aethel.exe"
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            pip_exe = venv_dir / "bin" / "pip"
            aethel_exe = venv_dir / "bin" / "aethel"
            python_exe = venv_dir / "bin" / "python"

        print(f"Installing {wheel_path.name} into clean environment...")
        # Use pip to install the wheel
        run_cmd([str(pip_exe), "install", str(wheel_path)])

        print("Testing `aethel selftest` in clean environment...")
        res_selftest = run_cmd([str(aethel_exe), "selftest"])
        if res_selftest.returncode != 0 or "selftest checks passed" not in res_selftest.stdout:
            print(
                "FAIL: `aethel selftest` did not report success:",
                res_selftest.stdout,
                file=sys.stderr,
            )
            sys.exit(1)
        print("PASS: `aethel selftest` clean run verified")

        print("Testing `aethel verify` on golden fixture in clean environment...")
        scenario_dir = repo_root / "tests" / "fixtures" / "genesis-attributed"
        fixture_bundles = [p for p in scenario_dir.iterdir() if p.is_dir() and len(p.name) == 64]
        if not fixture_bundles:
            print(f"FAIL: No 64-char bundle directory found in {scenario_dir}", file=sys.stderr)
            sys.exit(1)
        fixture_path = fixture_bundles[0]
        res_verify = run_cmd([str(aethel_exe), "verify", str(fixture_path)])
        if "Integrity    PASS" not in res_verify.stdout:
            print(
                "FAIL: `aethel verify` on genesis-attributed failed:",
                res_verify.stdout,
                file=sys.stderr,
            )
            sys.exit(1)
        print("PASS: `aethel verify` clean fixture verification verified")

        print("Checking python import from non-repo directory...")
        res_import = run_cmd(
            [str(python_exe), "-c", "import aethel_codex; print(aethel_codex.__name__)"],
            cwd=tmp_dir,
        )
        if "aethel_codex" not in res_import.stdout:
            print("FAIL: Package import failed:", res_import.stdout, file=sys.stderr)
            sys.exit(1)
        print("PASS: Clean import from outside repository verified")


def main() -> None:
    """Main entry point for wheel install smoke test."""
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root / "dist"
    wheels = list(dist_dir.glob("aethel_codex-*.whl"))

    if not wheels:
        print("No wheel found in dist/. Run `uv build` first.", file=sys.stderr)
        sys.exit(1)

    wheel_path = sorted(wheels)[-1]
    print(f"Starting wheel install smoke test on {wheel_path}...")
    smoke_test_wheel(wheel_path, repo_root)
    print("\nALL INSTALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
