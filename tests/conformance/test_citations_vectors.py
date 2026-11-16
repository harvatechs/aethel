"""Yellow Paper citation URI and locator conformance tests (YP §6.3, Table A.5)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.citations import parse_citation, validate_citation_range
from aethel_codex.errors import CitationError


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_citation_locators_t2_table_a5(yp_vectors: dict[str, Any]) -> None:
    loc_entry = yp_vectors["locators"]
    t2_canonical = bytes.fromhex(loc_entry["canonical_text_hex"])
    assert len(t2_canonical) == loc_entry["canonical_text_length"]

    t2_pid = "pip1:t:9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413"

    for r in loc_entry["range_results"]:
        locator = r["locator"]
        expected_valid = r["valid"]
        cite_str = f"cite:{t2_pid}{locator}"

        # If start >= end (e.g. 5-5), parse_citation rejects at syntax parse
        if locator == "#b=5-5":
            with pytest.raises(CitationError) as exc_info:
                parse_citation(cite_str)
            assert exc_info.value.code == "CITE_SYNTAX"
            continue

        citation = parse_citation(cite_str)
        if expected_valid:
            assert validate_citation_range(citation, t2_canonical) is True
        else:
            with pytest.raises(CitationError) as exc_info:
                validate_citation_range(citation, t2_canonical)
            assert exc_info.value.code == "CITE_RANGE"


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_citation_syntax_errors(yp_vectors: dict[str, Any]) -> None:
    loc_entry = yp_vectors["locators"]
    t2_pid = "pip1:t:9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413"

    for bad_loc in loc_entry["syntax_errors_for_pid_t_T2"]:
        cite_str = f"cite:{t2_pid}{bad_loc}"
        with pytest.raises(CitationError) as exc_info:
            parse_citation(cite_str)
        assert exc_info.value.code == "CITE_SYNTAX"

    # Type k is refused
    k_pid = "pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b"
    with pytest.raises(CitationError) as exc_info:
        parse_citation(f"cite:{k_pid}")
    assert exc_info.value.code == "CITE_SYNTAX"

    # Uppercase hex in PID is refused
    upper_pid = "pip1:t:9E13E0CCE8ECB379C0705C7D97E13C8E1F588C194BD0E6982DFDE98ED6E8F413"
    with pytest.raises(CitationError) as exc_info:
        parse_citation(f"cite:{upper_pid}")
    assert exc_info.value.code == "CITE_SYNTAX"


@pytest.mark.conformance
def test_citation_range_integers() -> None:
    t_pid = "pip1:t:" + "11" * 32
    # uint > 2^64 - 1
    bad_large = f"cite:{t_pid}#b=0-18446744073709551616"
    with pytest.raises(CitationError) as exc_info:
        parse_citation(bad_large)
    assert exc_info.value.code == "CITE_SYNTAX"

    # Trailing newline rejected (due to fullmatch)
    bad_nl = f"cite:{t_pid}#b=0-10\n"
    with pytest.raises(CitationError) as exc_info:
        parse_citation(bad_nl)
    assert exc_info.value.code == "CITE_SYNTAX"
