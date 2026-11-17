"""Tests for packaging, distribution assets and determinism (WP-15, UR-30)."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_tool_module(name: str, rel_path: str) -> Any:
    file_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_det_mod = _load_tool_module("determinism_check", "tools/determinism_check.py")
_smoke_mod = _load_tool_module("install_smoke", "tools/install_smoke.py")

check_t2_determinism = _det_mod.check_t2_determinism
check_publish_determinism = _det_mod.check_publish_determinism
verify_wheel_contents = _smoke_mod.verify_wheel_contents


@pytest.mark.req("UR-30")
def test_package_metadata_contracts() -> None:
    """Verify package name, entry point and version contracts."""
    meta = importlib.metadata.metadata("aethel-codex")
    assert meta["Name"] == "aethel-codex"
    assert meta.get("License-Expression") == "Apache-2.0" or meta.get("License") == "Apache-2.0"

    # Check console script entry point
    entry_points = importlib.metadata.entry_points(group="console_scripts")
    aethel_ep = [ep for ep in entry_points if ep.name == "aethel"]
    assert len(aethel_ep) == 1
    assert aethel_ep[0].value == "aethel_codex.cli:main"


@pytest.mark.req("UR-30")
def test_package_data_available() -> None:
    """Verify required package data files are included and readable offline."""
    pkg_files = importlib.resources.files("aethel_codex")

    # py.typed
    py_typed = pkg_files.joinpath("py.typed")
    assert py_typed.is_file()

    # Schemas
    schema_dir = pkg_files.joinpath("schemas")
    assert schema_dir.is_dir()
    for schema_name in ("verify.json", "selftest.json", "publish.json", "id.json"):
        s_file = schema_dir.joinpath(schema_name)
        assert s_file.is_file()
        schema_json = json.loads(s_file.read_text(encoding="utf-8"))
        assert "$schema" in schema_json or "properties" in schema_json or "type" in schema_json

    # Vectors
    data_dir = pkg_files.joinpath("data")
    assert data_dir.is_dir()
    vec_file = data_dir.joinpath("pip1-vectors.json")
    assert vec_file.is_file()
    vec_json = json.loads(vec_file.read_text(encoding="utf-8"))
    assert "ctf1" in vec_json


@pytest.mark.req("UR-30")
def test_determinism_checks_pass() -> None:
    """Verify cross-platform determinism checks pass."""
    assert check_t2_determinism() is True
    assert check_publish_determinism() is True

    # Subprocess execution test
    res = subprocess.run(  # noqa: S603
        [sys.executable, str(REPO_ROOT / "tools" / "determinism_check.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ALL DETERMINISM CHECKS PASSED" in res.stdout


@pytest.mark.req("UR-30")
def test_wheel_contents_verification(tmp_path: Path) -> None:
    """Verify wheel contents validator accepts valid wheel and rejects forbidden files."""
    valid_wheel = tmp_path / "aethel_codex-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(valid_wheel, "w") as z:
        z.writestr("aethel_codex/__init__.py", b"")
        z.writestr("aethel_codex/py.typed", b"")
        z.writestr("aethel_codex/data/pip1-vectors.json", b"{}")
        z.writestr("aethel_codex/data/pip1-slh-dsa-vectors.json", b"{}")
        z.writestr("aethel_codex/schemas/verify.json", b"{}")
        z.writestr("aethel_codex/schemas/selftest.json", b"{}")
        z.writestr("aethel_codex-0.1.0.dist-info/METADATA", b"")

    verify_wheel_contents(valid_wheel)

    # Corrupt wheel with tests/
    bad_wheel = tmp_path / "bad.whl"
    with zipfile.ZipFile(bad_wheel, "w") as z:
        z.writestr("aethel_codex/__init__.py", b"")
        z.writestr("aethel_codex/py.typed", b"")
        z.writestr("aethel_codex/data/pip1-vectors.json", b"{}")
        z.writestr("aethel_codex/data/pip1-slh-dsa-vectors.json", b"{}")
        z.writestr("aethel_codex/schemas/verify.json", b"{}")
        z.writestr("aethel_codex/schemas/selftest.json", b"{}")
        z.writestr("tests/test_something.py", b"")

    with pytest.raises(ValueError, match="Forbidden"):
        verify_wheel_contents(bad_wheel)
