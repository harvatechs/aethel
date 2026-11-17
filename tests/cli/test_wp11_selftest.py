"""Tests for WP-11: aethel version, explain, and selftest (cli-spec.md §3, §4)."""

import json
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest
import unicodedata2

from aethel_codex.cli import main
from aethel_codex.errors import ERROR_CODE_REGISTRY


@pytest.fixture
def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "src" / "aethel_codex" / "schemas"


@pytest.fixture
def version_schema(schemas_dir: Path) -> dict[str, Any]:
    with open(schemas_dir / "version.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture
def selftest_schema(schemas_dir: Path) -> dict[str, Any]:
    with open(schemas_dir / "selftest.json", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_version_subcommand_human(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["version"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "aethel 0.1.0" in captured.out
    assert "Unicode data: 18.0.0" in captured.out
    assert "ml-dsa-87" in captured.out
    assert "ml-dsa-65" in captured.out
    assert "slh-dsa-sha2-256s" in captured.out
    assert "slh-dsa-shake-256s" in captured.out
    assert "Python:" in captured.out
    assert "Platform:" in captured.out


def test_version_subcommand_json(
    capsys: pytest.CaptureFixture[str], version_schema: dict[str, Any]
) -> None:
    rc = main(["version", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    jsonschema.validate(instance=data, schema=version_schema)

    assert data["schema"] == "aethel.version/1"
    assert data["tool"]["name"] == "aethel"
    assert data["tool"]["version"] == "0.1.0"
    assert data["tool"]["profile"] == "pip-1"
    assert data["tool"]["yellow_paper"] == "1.0.0-rc.3"
    assert data["unicode"]["version"] == "18.0.0"
    assert len(data["backends"]) == 4
    algs = {b["alg"] for b in data["backends"]}
    assert algs == {"ml-dsa-87", "ml-dsa-65", "slh-dsa-sha2-256s", "slh-dsa-shake-256s"}


def test_global_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--version"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == "aethel 0.1.0 (PIP-1 profile pip-1, Yellow Paper 1.0.0-rc.3)\n"


def test_explain_all_registered_codes(capsys: pytest.CaptureFixture[str]) -> None:
    """Every single code in ERROR_CODE_REGISTRY must have a valid explanation."""
    assert len(ERROR_CODE_REGISTRY) >= 50

    for code in ERROR_CODE_REGISTRY:
        rc = main(["explain", code])
        assert rc == 0, f"explain {code} failed"
        captured = capsys.readouterr()
        assert f"Code:        {code}" in captured.out
        assert "Meaning:" in captured.out
        assert "Usual cause:" in captured.out
        assert "What to do:" in captured.out

        # JSON mode
        rc_json = main(["explain", code, "--json"])
        assert rc_json == 0, f"explain {code} --json failed"
        captured_json = capsys.readouterr()
        data = json.loads(captured_json.out)
        assert data["schema"] == "aethel.explain/1"
        assert data["code"] == code
        assert data["meaning"]
        assert data["cause"]
        assert data["what_to_do"]
        assert "exit_code" in data


def test_explain_list(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "--list"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Registered error codes" in captured.out
    for code in ERROR_CODE_REGISTRY:
        assert code in captured.out

    rc_json = main(["explain", "--list", "--json"])
    assert rc_json == 0
    captured_json = capsys.readouterr()
    data = json.loads(captured_json.out)
    assert data["schema"] == "aethel.explain_list/1"
    assert len(data["codes"]) == len(ERROR_CODE_REGISTRY)


def test_explain_unknown_code(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "NONEXISTENT_CODE_XYZ"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "unknown error code" in captured.err


def test_explain_missing_code(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "missing error code" in captured.err


def test_selftest_human(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["selftest"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Selftest: Permanent Ink Protocol (PIP-1)" in captured.out
    assert "All 13 selftest checks passed." in captured.out
    assert "[PASS]   unicode.guard" in captured.out
    assert "[PASS]   unicode.canary" in captured.out
    assert "[PASS]   ctf1.t1" in captured.out
    assert "[PASS]   ctf1.t2" in captured.out
    assert "[PASS]   ctf1.t3" in captured.out
    assert "[PASS]   ctf1.t4" in captured.out
    assert "[PASS]   ctf1.negatives" in captured.out
    assert "[PASS]   manifest.genesis" in captured.out
    assert "[PASS]   manifest.revision" in captured.out
    assert "[PASS]   crypto.ml_dsa_87" in captured.out
    assert "[PASS]   crypto.ml_dsa_65" in captured.out
    assert "[PASS]   crypto.slh_dsa_sha2_256s" in captured.out
    assert "[PASS]   crypto.slh_dsa_shake_256s" in captured.out


def test_selftest_json(capsys: pytest.CaptureFixture[str], selftest_schema: dict[str, Any]) -> None:
    rc = main(["selftest", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    jsonschema.validate(instance=data, schema=selftest_schema)

    assert data["schema"] == "aethel.selftest/1"
    assert data["passed"] is True
    assert data["tests_total"] == 13
    assert data["tests_passed"] == 13
    assert data["tests_failed"] == 0
    assert len(data["results"]) == 13


def test_selftest_failure_detection(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(unicodedata2, "unidata_version", "15.0.0")
    rc = main(["selftest"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "FAILED:" in captured.out
    assert "[FAIL]   unicode.guard" in captured.out
