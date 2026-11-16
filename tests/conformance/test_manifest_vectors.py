"""Yellow Paper PMF-1 manifest vectors and grammar tests (YP §7, Table A.3)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aethel_codex.errors import AethelError
from aethel_codex.manifest import parse_manifest, serialize_manifest


@pytest.fixture
def yp_vectors() -> dict[str, Any]:
    v_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(v_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_manifest_genesis_roundtrip(yp_vectors: dict[str, Any]) -> None:
    gen_entry = yp_vectors["manifests"]["genesis"]
    raw = gen_entry["text"].encode("utf-8")
    assert len(raw) == gen_entry["length"]

    manifest = parse_manifest(raw)
    assert manifest.manifest_id() == gen_entry["manifest_id"]
    assert manifest.profile == "pip-1"
    assert manifest.markup == "pip-md-1"
    assert manifest.lang == "en"
    assert manifest.title == "Test Manuscript"
    assert manifest.license == "CC0-1.0"
    assert str(manifest.text_pid) == (
        "pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
    )
    assert manifest.text_length == 48
    assert len(manifest.authors) == 1
    assert len(manifest.assets) == 1
    assert len(manifest.cites) == 1

    # Round trip byte equality
    reserialized = serialize_manifest(manifest)
    assert reserialized == raw


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_manifest_revision_roundtrip(yp_vectors: dict[str, Any]) -> None:
    rev_entry = yp_vectors["manifests"]["revision"]
    raw = rev_entry["text"].encode("utf-8")
    assert len(raw) == rev_entry["length"]

    manifest = parse_manifest(raw)
    assert manifest.manifest_id() == rev_entry["manifest_id"]
    assert manifest.beacon is not None
    assert manifest.beacon.source == "example-beacon"
    assert manifest.beacon.sequence == 123456
    assert manifest.beacon.value == bytes.fromhex(
        "00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff"
    )
    assert manifest.work_pid is not None
    assert len(manifest.parents) == 1

    reserialized = serialize_manifest(manifest)
    assert reserialized == raw


@pytest.mark.conformance
@pytest.mark.req("UR-01")
def test_manifest_negative_mutations(yp_vectors: dict[str, Any]) -> None:
    mutations = yp_vectors["manifests"]["negative_mutations"]
    assert len(mutations) == 9

    for mut in mutations:
        name = mut["name"]
        raw = bytes.fromhex(mut["input_hex"])
        expected = mut["expect"]

        if expected == "ACCEPTED":
            # Mutation 8: text length 2^64 - 1
            manifest = parse_manifest(raw)
            assert manifest.text_length == 18446744073709551615
            assert serialize_manifest(manifest) == raw
        else:
            with pytest.raises(AethelError) as exc_info:
                parse_manifest(raw)
            assert exc_info.value.code == expected, (
                f"Mutation '{name}' expected {expected}, got {exc_info.value.code}"
            )


@pytest.mark.conformance
def test_abnf_grammar_cases(yp_vectors: dict[str, Any]) -> None:
    cases = yp_vectors["grammar_cases_derived_from_abnf"]

    # Base genesis manifest lines
    base_gen = yp_vectors["manifests"]["genesis"]["text"]

    # lang_accept and lang_reject
    for valid_lang in cases["lang_accept"]:
        mod = base_gen.replace("lang en\n", f"lang {valid_lang}\n").encode("utf-8")
        manifest = parse_manifest(mod)
        assert manifest.lang == valid_lang

    for bad_lang in cases["lang_reject"]:
        mod = base_gen.replace("lang en\n", f"lang {bad_lang}\n").encode("utf-8")
        with pytest.raises(AethelError) as exc_info:
            parse_manifest(mod)
        assert exc_info.value.code == "E_BAD_VALUE"

    # media_accept and media_reject in asset line
    for valid_media in cases["media_accept"]:
        mod = base_gen.replace("image/svg+xml\n", f"{valid_media}\n").encode("utf-8")
        manifest = parse_manifest(mod)
        assert manifest.assets[0].media_type == valid_media

    for bad_media in cases["media_reject"]:
        mod = base_gen.replace("image/svg+xml\n", f"{bad_media}\n").encode("utf-8")
        with pytest.raises(AethelError) as exc_info:
            parse_manifest(mod)
        assert exc_info.value.code == "E_BAD_VALUE"

    # beacon_value_reject
    base_rev = yp_vectors["manifests"]["revision"]["text"]
    for bad_val in cases["beacon_value_reject"]:
        mod = base_rev.replace(
            "00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff\n",
            f"{bad_val}\n",
        ).encode("utf-8")
        with pytest.raises(AethelError) as exc_info:
            parse_manifest(mod)
        assert exc_info.value.code == "E_BAD_VALUE"
