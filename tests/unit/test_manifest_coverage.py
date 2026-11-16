"""Unit tests for PMF-1 manifest parser, serializer, and builder error paths (PT1 95%+)."""

import pytest

from aethel_codex.errors import ManifestError
from aethel_codex.manifest import (
    Manifest,
    ManifestBuilder,
    parse_manifest,
)
from aethel_codex.pid import Pid

VALID_GENESIS = (
    "pip-manifest 1\n"
    "profile pip-1\n"
    "markup pip-md-1\n"
    "lang en\n"
    "title Test Manuscript\n"
    "license CC0-1.0\n"
    "text pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba 48\n"
)


def test_invalid_utf8_rejection() -> None:
    bad = b"pip-manifest 1\nprofile pip-1\n\xff"
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_INVALID_UTF8"


def test_bad_lines_rejections() -> None:
    # Contains carriage return
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(VALID_GENESIS.replace("\n", "\r\n").encode())
    assert exc_info.value.code == "E_BAD_LINES"

    # Missing final LF
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(VALID_GENESIS.rstrip("\n").encode())
    assert exc_info.value.code == "E_BAD_LINES"

    # Blank line
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest((VALID_GENESIS + "\n").encode())
    assert exc_info.value.code == "E_BAD_LINES"

    # Line without space
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(VALID_GENESIS.replace("lang en\n", "lang_en\n").encode())
    assert exc_info.value.code == "E_BAD_LINES"


def test_bad_magic_rejection() -> None:
    bad = VALID_GENESIS.replace("pip-manifest 1\n", "pip-manifest 2\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_MAGIC"


def test_unknown_key_rejection() -> None:
    bad = VALID_GENESIS.replace("license CC0-1.0\n", "license CC0-1.0\ncustom-key val\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_UNKNOWN_KEY"


def test_field_order_and_duplicate_singletons() -> None:
    # Duplicate profile
    bad = VALID_GENESIS.replace("profile pip-1\n", "profile pip-1\nprofile pip-1\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_FIELD_ORDER"

    # Out of order fields
    bad = VALID_GENESIS.replace(
        "profile pip-1\nmarkup pip-md-1\n", "markup pip-md-1\nprofile pip-1\n"
    ).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_FIELD_ORDER"


def test_value_text_rejections() -> None:
    # Empty title
    bad = VALID_GENESIS.replace("title Test Manuscript\n", "title \n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Title starting with space (tested also in negative vector 5)
    bad = VALID_GENESIS.replace("title Test Manuscript\n", "title  Test\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Title ending with space
    bad = VALID_GENESIS.replace("title Test Manuscript\n", "title Test \n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Title containing forbidden scalar (TAB)
    bad = VALID_GENESIS.replace("title Test Manuscript\n", "title Test\tManuscript\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Title not NFC
    decomposed = "title caf\u0065\u0301\n"
    bad = VALID_GENESIS.replace("title Test Manuscript\n", decomposed).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Title length > 512 bytes
    long_title = "title " + ("a" * 513) + "\n"
    bad = VALID_GENESIS.replace("title Test Manuscript\n", long_title).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"


def test_missing_mandatory_fields() -> None:
    fields = [
        "profile pip-1\n",
        "markup pip-md-1\n",
        "lang en\n",
        "title Test Manuscript\n",
        "license CC0-1.0\n",
        "text pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba 48\n",
    ]
    for f in fields:
        bad = VALID_GENESIS.replace(f, "").encode()
        with pytest.raises(ManifestError) as exc_info:
            parse_manifest(bad)
        assert exc_info.value.code == "E_MISSING_FIELD"


def test_work_parent_rule() -> None:
    # Work without parent
    work_line = "work pip1:m:" + "11" * 32 + "\n"
    bad = (VALID_GENESIS + work_line).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_WORK_PARENT_RULE"

    # Parent without work
    parent_line = "parent pip1:m:" + "11" * 32 + "\n"
    bad = (VALID_GENESIS + parent_line).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_WORK_PARENT_RULE"


def test_not_sorted_or_unique() -> None:
    # Duplicate parents
    p1 = "parent pip1:m:" + "11" * 32 + "\n"
    w1 = "work pip1:m:" + "11" * 32 + "\n"
    bad = (VALID_GENESIS + w1 + p1 + p1).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_NOT_SORTED_OR_UNIQUE"

    # Duplicate authors
    a1 = "author pip1:k:" + "11" * 32 + "\n"
    bad = (VALID_GENESIS + a1 + a1).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_NOT_SORTED_OR_UNIQUE"

    # Unsorted authors
    a1 = "author pip1:k:" + "11" * 32 + "\n"
    a2 = "author pip1:k:" + "22" * 32 + "\n"
    bad = (VALID_GENESIS + a2 + a1).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_NOT_SORTED_OR_UNIQUE"

    # Duplicate asset names
    as1 = "asset fig.svg pip1:a:" + "11" * 32 + " 10 image/svg+xml\n"
    as2 = "asset fig.svg pip1:a:" + "22" * 32 + " 20 image/svg+xml\n"
    bad = (VALID_GENESIS + as1 + as2).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_NOT_SORTED_OR_UNIQUE"


def test_roundtrip_fault_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test E_ROUNDTRIP by modifying serialization behavior
    import aethel_codex.manifest as m_mod

    raw = VALID_GENESIS.encode()
    orig_serialize = m_mod.serialize_manifest

    def faulty_serialize(manifest: Manifest) -> bytes:
        return orig_serialize(manifest) + b"\n"

    monkeypatch.setattr(m_mod, "serialize_manifest", faulty_serialize)
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(raw)
    assert exc_info.value.code == "E_ROUNDTRIP"


def test_builder_deduplication_and_sorting() -> None:
    text_pid = Pid.parse("pip1:t:" + "11" * 32)
    k1 = Pid.parse("pip1:k:" + "22" * 32)
    k2 = Pid.parse("pip1:k:" + "11" * 32)
    p1 = Pid.parse("pip1:m:" + "33" * 32)
    p2 = Pid.parse("pip1:m:" + "44" * 32)
    a1 = Pid.parse("pip1:a:" + "55" * 32)

    builder = (
        ManifestBuilder()
        .set_profile("pip-1")
        .set_markup("pip-md-1")
        .set_lang("en")
        .set_title("Test")
        .set_license("CC0-1.0")
        .set_beacon("src", 1, bytes.fromhex("00ff"))
        .set_text(text_pid, 10)
        .set_work(p1)
        .add_parent(p1)
        .add_parent(p2)
        .add_author(k1)
        .add_author(k2)
        .add_author(k1)
        .add_derivative("translation", p1)
        .add_asset("fig1.png", a1, 100, "image/png")
        .add_asset("fig1.png", a1, 100, "image/png")  # duplicate identical
    )

    manifest = builder.build()
    assert len(manifest.authors) == 2
    assert manifest.authors[0] == k2
    assert manifest.authors[1] == k1
    # Test manifest_id on un-serialized manifest
    unserialized = Manifest(
        profile=manifest.profile,
        markup=manifest.markup,
        lang=manifest.lang,
        title=manifest.title,
        license=manifest.license,
        text_pid=manifest.text_pid,
        text_length=manifest.text_length,
    )
    assert unserialized.manifest_id().startswith("pip1:m:")


def test_builder_asset_conflict_and_missing_text() -> None:
    a1 = Pid.parse("pip1:a:" + "55" * 32)
    a2 = Pid.parse("pip1:a:" + "66" * 32)
    b = ManifestBuilder().add_asset("fig.png", a1, 100, "image/png")
    with pytest.raises(ManifestError) as exc_info:
        b.add_asset("fig.png", a2, 100, "image/png")
    assert exc_info.value.code == "E_NOT_SORTED_OR_UNIQUE"

    with pytest.raises(ManifestError) as exc_info:
        ManifestBuilder().build()
    assert exc_info.value.code == "E_MISSING_FIELD"


def test_field_value_type_rejections() -> None:
    # Text PID with wrong type
    bad = VALID_GENESIS.replace("text pip1:t:", "text pip1:m:").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Text length < 1
    bad = VALID_GENESIS.replace(" 48\n", " 0\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Work PID with wrong type
    bad = (
        VALID_GENESIS + "work pip1:t:" + "11" * 32 + "\nparent pip1:m:" + "22" * 32 + "\n"
    ).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Parent PID with wrong type
    bad = (
        VALID_GENESIS + "work pip1:m:" + "11" * 32 + "\nparent pip1:t:" + "22" * 32 + "\n"
    ).encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Author PID with wrong type
    bad = (VALID_GENESIS + "author pip1:m:" + "11" * 32 + "\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Derivative PID with wrong type
    bad = (VALID_GENESIS + "derivative translation pip1:t:" + "11" * 32 + "\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Derivative with bad kind
    bad = (VALID_GENESIS + "derivative bogus pip1:m:" + "11" * 32 + "\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Asset PID with wrong type
    bad = (VALID_GENESIS + "asset f.png pip1:t:" + "11" * 32 + " 10 image/png\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"

    # Cite PID with type 'k'
    bad = (VALID_GENESIS + "cite pip1:k:" + "11" * 32 + "\n").encode()
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(bad)
    assert exc_info.value.code == "E_BAD_VALUE"
