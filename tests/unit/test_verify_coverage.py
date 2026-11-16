"""Comprehensive unit tests covering edge branches and error states in verify and bundle."""

import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from aethel_codex.bundle import read_bundle
from aethel_codex.limits import Limits
from aethel_codex.report import CheckResult, Status
from aethel_codex.verify import verify_bundle

FIXTURES_DIR = Path("tests/fixtures")


def _copy_bundle(scenario: str, tmp_path: Path) -> Path:
    scenario_dir = FIXTURES_DIR / scenario
    for item in scenario_dir.iterdir():
        if item.is_dir() and len(item.name) == 64:
            dest = tmp_path / item.name
            shutil.copytree(item, dest)
            return dest
    raise FileNotFoundError("Bundle not found")


def test_bundle_not_a_dir(tmp_path: Path) -> None:
    not_dir = tmp_path / "not_a_dir"
    not_dir.write_text("file", encoding="utf-8")
    view = read_bundle(not_dir)
    assert not view.limit_exceeded


def test_bundle_max_dir_entries_limit(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    view = read_bundle(bundle, limits=Limits(max_dir_entries=2))
    assert view.limit_exceeded
    assert view.limit_reason == "LIMIT_EXCEEDED"

    report = verify_bundle(bundle, limits=Limits(max_dir_entries=2))
    assert report.integrity == "INCONCLUSIVE"
    assert report.checks_dict()["V1"] == "SKIPPED:LIMIT_EXCEEDED"


def test_v1_manifest_size_limit(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    report = verify_bundle(bundle, limits=Limits(max_manifest_bytes=10))
    assert report.integrity == "INCONCLUSIVE"
    assert report.checks_dict()["V1"] == "SKIPPED:LIMIT_EXCEEDED"


def test_v1_manifest_invalid_syntax(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    (bundle / "manifest.pip").write_bytes(b"invalid manifest content\n")
    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    assert report.checks_dict()["V1"] == "FAIL:MANIFEST_INVALID"


def test_v2_extra_text_file(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    (bundle / "text.txt").write_text("extra text file", encoding="utf-8")
    report = verify_bundle(bundle)
    assert report.integrity == "PASS"
    assert report.checks_dict()["V2"] == "WARN:EXTRA_FILE"


def test_v2_text_length_mismatch(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    (bundle / "text.md").write_bytes(b"# Short\n")
    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    assert report.checks_dict()["V2"] == "FAIL:TEXT_LENGTH"


def test_v2_text_non_canonical(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    orig_len = len((bundle / "text.md").read_bytes())
    # Create non-canonical text of identical length (contains carriage return)
    bad_text = b"# Non-canon\r\n" + b" " * (orig_len - 14) + b"\n"
    (bundle / "text.md").write_bytes(bad_text)
    report = verify_bundle(bundle)
    assert report.integrity == "FAIL"
    assert report.checks_dict()["V2"].startswith("FAIL:TEXT_NOT_CANONICAL")


def test_v3_asset_size_limit_exceeded(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    report = verify_bundle(bundle, limits=Limits(max_asset_bytes=10))
    assert report.integrity == "INCONCLUSIVE"
    assert report.checks_dict()["V3"] == "SKIPPED:LIMIT_EXCEEDED"


def test_v4_unlisted_inline_citation(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    # Add an unlisted citation into text
    original_text = (bundle / "text.md").read_bytes()
    new_text = original_text + b"\ncite:pip1:t:" + b"99" * 32 + b"\n"
    # Update manifest to match text length and text PID
    from aethel_codex.manifest import parse_manifest, serialize_manifest
    from aethel_codex.merkle import text_id
    from aethel_codex.pid import Pid

    m = parse_manifest((bundle / "manifest.pip").read_bytes())
    new_tid = Pid.parse(text_id(new_text))
    new_m = serialize_manifest(
        m.__class__(
            profile=m.profile,
            markup=m.markup,
            lang=m.lang,
            title=m.title,
            license=m.license,
            text_pid=new_tid,
            text_length=len(new_text),
            authors=m.authors,
            assets=m.assets,
            cites=m.cites,
        )
    )
    (bundle / "text.md").write_bytes(new_text)
    (bundle / "manifest.pip").write_bytes(new_m)

    # Rename directory to match new manifest ID
    from aethel_codex.constants import LABEL_MANIFEST
    from aethel_codex.hashing import H

    new_mid_hex = H(LABEL_MANIFEST, new_m).hex()
    new_dir = bundle.parent / new_mid_hex
    bundle.rename(new_dir)

    report = verify_bundle(new_dir)
    assert report.checks_dict()["V4"] == "WARN:CITE_UNLISTED"


def test_v5_parent_work_mismatch(tmp_path: Path) -> None:
    # Use revision fixture
    rev_src = FIXTURES_DIR / "revision"
    rev_bundle_dir = next(d for d in rev_src.iterdir() if d.is_dir() and len(d.name) == 64)
    rev_dest = tmp_path / "rev" / rev_bundle_dir.name
    shutil.copytree(rev_bundle_dir, rev_dest)

    # Copy genesis as parent, but modify parent's work_id
    gen_src = FIXTURES_DIR / "genesis-attributed"
    gen_bundle_dir = next(d for d in gen_src.iterdir() if d.is_dir() and len(d.name) == 64)
    gen_dest = tmp_path / "parents" / gen_bundle_dir.name
    shutil.copytree(gen_bundle_dir, gen_dest)

    from aethel_codex.manifest import parse_manifest, serialize_manifest
    from aethel_codex.pid import Pid

    p_m = parse_manifest((gen_dest / "manifest.pip").read_bytes())
    # Add a conflicting work PID
    tampered_p_m = serialize_manifest(
        p_m.__class__(
            profile=p_m.profile,
            markup=p_m.markup,
            lang=p_m.lang,
            title=p_m.title,
            license=p_m.license,
            text_pid=p_m.text_pid,
            text_length=p_m.text_length,
            work_pid=Pid.parse("pip1:m:" + "22" * 32),
            authors=p_m.authors,
            assets=p_m.assets,
            cites=p_m.cites,
            parents=(Pid.parse("pip1:m:" + "33" * 32),),
        )
    )
    (gen_dest / "manifest.pip").write_bytes(tampered_p_m)

    report = verify_bundle(rev_dest, parents=tmp_path / "parents")
    assert report.checks_dict()["V5"].startswith("FAIL:WORK_MISMATCH")


def test_v6_envelope_size_limit(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    report = verify_bundle(bundle, limits=Limits(max_envelope_bytes=10))
    assert report.checks_dict()["V6"].startswith("FAIL:ENVELOPE_INVALID")


def test_v6_envelope_syntax_error(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    sig_file = next((bundle / "signatures").glob("*.sig"))
    sig_file.write_text("invalid envelope format\n", encoding="utf-8")
    report = verify_bundle(bundle)
    assert report.checks_dict()["V6"].startswith("FAIL:ENVELOPE_INVALID")


def test_v8_attestation_present_and_extra_file(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    att_dir = bundle / "attestations"
    att_dir.mkdir()
    (att_dir / "timestamp.att").write_text(
        "pip-attestation 1\nmanifest pip1:m:00\nkind rfc3161\nproof AA==\n", encoding="utf-8"
    )
    report = verify_bundle(bundle)
    assert report.checks_dict()["V8"] == "WARN:ATT_UNVERIFIED"

    # Extra non-.att file in attestations
    (att_dir / "unrelated.txt").write_text("note", encoding="utf-8")
    report2 = verify_bundle(bundle)
    assert report2.checks_dict()["V8"] == "WARN:EXTRA_FILE"


def test_gates_exit_codes(tmp_path: Path) -> None:
    bundle = _copy_bundle("genesis-attributed", tmp_path)

    # Require dual-family on a single-family bundle (genesis-attributed is only ML-DSA-87)
    r1 = verify_bundle(bundle, require_dual_family=True)
    assert r1.exit_code == 1

    # Require parents on genesis (which has no parents)
    r2 = verify_bundle(bundle, require_parents=True)
    assert r2.exit_code == 1

    # Warnings as errors when a warning exists
    (bundle / "assets" / "extra.dat").write_bytes(b"data")
    r3 = verify_bundle(bundle, warnings_as_errors=True)
    assert r3.exit_code == 2


def test_report_methods(tmp_path: Path) -> None:
    cr = CheckResult(id="V1", status=Status.PASS)
    assert cr.status_summary() == "PASS"

    cr_fail = CheckResult(id="V1", status=Status.FAIL, code="MANIFEST_MISSING")
    assert cr_fail.status_summary() == "FAIL:MANIFEST_MISSING"

    # Test to_json on verify report
    bundle = _copy_bundle("genesis-attributed", tmp_path)
    rep = verify_bundle(bundle)
    json_str = rep.to_json()
    assert '"schema": "aethel.verify/1"' in json_str


def test_bundle_safe_entry_branches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from aethel_codex.bundle import _check_safe_entry, _scan_dir

    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")

    # Mock islink to simulate symlink
    monkeypatch.setattr(os.path, "islink", lambda _: True)
    safe, code, _ = _check_safe_entry(p)
    assert not safe
    assert code == "UNSAFE_PATH"

    # Mock lstat returning non-regular file mode
    import stat

    class FakeStat:
        st_mode = stat.S_IFDIR

    monkeypatch.setattr(os.path, "islink", lambda _: False)
    monkeypatch.setattr(os, "lstat", lambda _: FakeStat())
    safe, code, _ = _check_safe_entry(p)
    assert not safe
    assert code == "UNSAFE_PATH"

    # Mock lstat OSError
    def raise_oserror(_: Any) -> Any:
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "lstat", raise_oserror)
    safe, code, _ = _check_safe_entry(p)
    assert not safe
    assert code == "UNSAFE_PATH"

    # Mock scandir OSError
    monkeypatch.setattr(os, "scandir", raise_oserror)
    assert _scan_dir(tmp_path) == []


def test_verify_unsafe_items_and_io_errors(tmp_path: Path) -> None:
    from aethel_codex.bundle import BundleItem, BundleView
    from aethel_codex.verify import (
        _check_v1_manifest,
        _check_v2_text,
        _check_v3_assets,
        _check_v4_citations,
        _check_v5_history,
        _check_v6_signatures,
    )

    # 1. Unsafe manifest item
    unsafe_item = BundleItem(name="manifest.pip", path=tmp_path / "manifest.pip", is_safe=False)
    view = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, manifest_item=unsafe_item
    )
    res, _, _, _ = _check_v1_manifest(view, Limits())
    assert res.status == "FAIL"
    assert res.code == "UNSAFE_PATH"

    # 2. Manifest read OSError
    non_existent_item = BundleItem(
        name="manifest.pip", path=tmp_path / "non_existent.pip", is_safe=True
    )
    view2 = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, manifest_item=non_existent_item
    )
    res2, _, _, _ = _check_v1_manifest(view2, Limits())
    assert res2.status == "FAIL"
    assert res2.code == "MANIFEST_MISSING"

    # 3. None manifest checks
    assert _check_v3_assets(view, None, Limits()).status == "SKIPPED"
    assert _check_v4_citations(None, None).status == "SKIPPED"
    res_h, _ = _check_v5_history(None, None)
    assert res_h.status == "SKIPPED"
    res_s, _ = _check_v6_signatures(view, None, None, Limits())
    assert res_s.status == "SKIPPED"

    # 4. Citations on invalid UTF-8 bytes
    from aethel_codex.manifest import Manifest
    from aethel_codex.pid import Pid

    m = Manifest(
        profile="pip-1",
        markup="pip-md-1",
        lang="en",
        title="Test",
        license="CC0-1.0",
        text_pid=Pid.parse("pip1:t:" + "00" * 32),
        text_length=10,
    )
    assert _check_v4_citations(m, b"\xff\xfe").status == "PASS"

    # 5. Unsafe text item & Text read OSError
    unsafe_text = BundleItem(name="text.md", path=tmp_path / "text.md", is_safe=False)
    view_text = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, text_items=[unsafe_text]
    )
    res_t, _ = _check_v2_text(view_text, m, Limits())
    assert res_t.status == "FAIL"
    assert res_t.code == "UNSAFE_PATH"

    bad_read_text = BundleItem(name="text.md", path=tmp_path / "non_existent.md", is_safe=True)
    view_text2 = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, text_items=[bad_read_text]
    )
    res_t2, _ = _check_v2_text(view_text2, m, Limits())
    assert res_t2.status == "FAIL"
    assert res_t2.code == "TEXT_MISSING"

    # 6. Unsafe signature item & Signature read OSError
    unsafe_sig = BundleItem(name="1.sig", path=tmp_path / "1.sig", is_safe=False)
    view_sig = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, signature_items=[unsafe_sig]
    )
    res_sig, _ = _check_v6_signatures(view_sig, m, Pid.parse("pip1:m:" + "00" * 32), Limits())
    assert res_sig.status == "FAIL"
    assert res_sig.code == "UNSAFE_PATH"

    bad_sig = BundleItem(name="1.sig", path=tmp_path / "non_existent.sig", is_safe=True)
    view_sig2 = BundleView(
        root_path=tmp_path, dir_name="foo", is_hex_dir_name=False, signature_items=[bad_sig]
    )
    res_sig2, _ = _check_v6_signatures(view_sig2, m, Pid.parse("pip1:m:" + "00" * 32), Limits())
    assert res_sig2.status == "FAIL"
    assert res_sig2.code == "ENVELOPE_INVALID"
