"""Conformance tests for the five golden fixtures (specs.md §9, testing-and-conformance.md §3)."""

import json
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest

from aethel_codex.verify import verify_bundle

FIXTURES_DIR = Path("tests/fixtures")
SCHEMA_PATH = Path("src/aethel_codex/schemas/verify.json")


@pytest.fixture(scope="module")
def verify_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _load_fixture_data(scenario: str) -> tuple[Path, dict[str, Any]]:
    scenario_dir = FIXTURES_DIR / scenario
    with open(scenario_dir / "expected.json", encoding="utf-8") as f:
        expected: dict[str, Any] = json.load(f)
    manifest_hex = expected["manifest_id"].split(":")[-1]
    bundle_path = scenario_dir / manifest_hex
    return bundle_path, expected


@pytest.mark.conformance
@pytest.mark.req("UR-17")
@pytest.mark.req("UR-18")
@pytest.mark.req("UR-19")
@pytest.mark.req("UR-20")
@pytest.mark.req("UR-21")
def test_fixture_genesis_attributed(verify_schema: dict[str, Any]) -> None:
    bundle_path, expected = _load_fixture_data("genesis-attributed")
    report = verify_bundle(bundle_path)

    assert report.manifest_id == expected["manifest_id"]
    assert report.integrity == expected["integrity"]
    assert report.attribution.cls == expected["attribution"]["cls"]
    assert report.attribution.signed == expected["attribution"]["signed"]
    assert report.attribution.declared == expected["attribution"]["declared"]
    assert report.attribution.keccak_independent == expected["attribution"]["keccak_independent"]
    assert report.checks_dict() == expected["checks"]
    assert report.exit_code == expected["exit_code_verify"]

    jsonschema.validate(instance=report.to_dict(), schema=verify_schema)


@pytest.mark.conformance
def test_fixture_genesis_unsigned(verify_schema: dict[str, Any]) -> None:
    bundle_path, expected = _load_fixture_data("genesis-unsigned")
    report = verify_bundle(bundle_path)

    assert report.manifest_id == expected["manifest_id"]
    assert report.integrity == expected["integrity"]
    assert report.attribution.cls == expected["attribution"]["cls"]
    assert report.attribution.signed == expected["attribution"]["signed"]
    assert report.attribution.declared == expected["attribution"]["declared"]
    assert report.attribution.keccak_independent == expected["attribution"]["keccak_independent"]
    assert report.checks_dict() == expected["checks"]
    assert report.exit_code == expected["exit_code_verify"]

    # Test gate require_attributed
    report_req = verify_bundle(bundle_path, require_attributed=True)
    assert report_req.exit_code == expected["exit_code_verify_require_attributed"]

    jsonschema.validate(instance=report.to_dict(), schema=verify_schema)


@pytest.mark.conformance
def test_fixture_dual_family(verify_schema: dict[str, Any]) -> None:
    bundle_path, expected = _load_fixture_data("dual-family")
    report = verify_bundle(bundle_path)

    assert report.manifest_id == expected["manifest_id"]
    assert report.integrity == expected["integrity"]
    assert report.attribution.cls == expected["attribution"]["cls"]
    assert report.attribution.signed == expected["attribution"]["signed"]
    assert report.attribution.declared == expected["attribution"]["declared"]
    assert report.attribution.keccak_independent == expected["attribution"]["keccak_independent"]
    assert report.checks_dict() == expected["checks"]
    assert report.exit_code == expected["exit_code_verify"]

    jsonschema.validate(instance=report.to_dict(), schema=verify_schema)


@pytest.mark.conformance
def test_fixture_partial_attribution(verify_schema: dict[str, Any]) -> None:
    bundle_path, expected = _load_fixture_data("partial-attribution")
    report = verify_bundle(bundle_path)

    assert report.manifest_id == expected["manifest_id"]
    assert report.integrity == expected["integrity"]
    assert report.attribution.cls == expected["attribution"]["cls"]
    assert report.attribution.signed == expected["attribution"]["signed"]
    assert report.attribution.declared == expected["attribution"]["declared"]
    assert report.attribution.keccak_independent == expected["attribution"]["keccak_independent"]
    assert report.checks_dict() == expected["checks"]
    assert report.exit_code == expected["exit_code_verify"]

    report_req = verify_bundle(bundle_path, require_attributed=True)
    assert report_req.exit_code == expected["exit_code_verify_require_attributed"]

    jsonschema.validate(instance=report.to_dict(), schema=verify_schema)


@pytest.mark.conformance
def test_fixture_revision_with_and_without_parents(verify_schema: dict[str, Any]) -> None:
    bundle_path, expected = _load_fixture_data("revision")

    # Without parents
    report_no_parents = verify_bundle(bundle_path)
    assert report_no_parents.manifest_id == expected["manifest_id"]
    assert report_no_parents.integrity == expected["integrity"]
    assert report_no_parents.attribution.cls == expected["attribution"]["cls"]
    assert report_no_parents.checks_dict() == expected["checks_without_parents"]
    assert report_no_parents.exit_code == expected["exit_code_verify"]
    jsonschema.validate(instance=report_no_parents.to_dict(), schema=verify_schema)

    # With parents supplied
    parents_dir = bundle_path.parent / expected["parents_fixture"]
    report_with_parents = verify_bundle(bundle_path, parents=parents_dir)
    assert report_with_parents.checks_dict() == expected["checks_with_parents"]
    assert report_with_parents.exit_code == expected["exit_code_verify"]
    jsonschema.validate(instance=report_with_parents.to_dict(), schema=verify_schema)
