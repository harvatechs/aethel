"""Tests for the seven attribution scenarios of Yellow Paper Table A.5 (specs.md §9)."""

from aethel_codex.envelope import SignatureEnvelope
from aethel_codex.manifest import Manifest
from aethel_codex.pid import Pid
from aethel_codex.verify import _check_v7_attribution


def _make_dummy_manifest(authors: list[str]) -> Manifest:
    return Manifest(
        profile="pip-1",
        markup="pip-md-1",
        lang="en",
        title="Test",
        license="CC0-1.0",
        text_pid=Pid.parse("pip1:t:" + "00" * 32),
        text_length=10,
        authors=tuple(Pid.parse(a) for a in authors),
    )


def _make_env(key_str: str, role: int, alg_name: str) -> SignatureEnvelope:
    return SignatureEnvelope(
        manifest_pid=Pid.parse("pip1:m:" + "11" * 32),
        role=role,
        alg_name=alg_name,
        key_pid=Pid.parse(key_str),
        public_key=b"\x00" * 32,
        signature=b"\x00" * 64,
    )


KEY1 = "pip1:k:" + "01" * 32
KEY2 = "pip1:k:" + "02" * 32
KEY3 = "pip1:k:" + "03" * 32


def test_attribution_table_row1_no_authors() -> None:
    # Row 1: 0 declared, 0 signed -> Unattributed
    m = _make_dummy_manifest([])
    check, att = _check_v7_attribution(m, [])
    assert check.status == "PASS"
    assert att.cls == "Unattributed"
    assert att.signed == 0
    assert att.declared == 0
    assert not att.keccak_independent


def test_attribution_table_row2_unattributed() -> None:
    # Row 2: 1 declared, 0 signed -> Unattributed
    m = _make_dummy_manifest([KEY1])
    check, att = _check_v7_attribution(m, [])
    assert check.status == "PASS"
    assert att.cls == "Unattributed"
    assert att.signed == 0
    assert att.declared == 1
    assert not att.keccak_independent
    assert att.keys[0]["status"] == "missing"


def test_attribution_table_row3_partially_attributed() -> None:
    # Row 3: 2 declared, 1 signed (ML-DSA-87) -> Partially attributed
    m = _make_dummy_manifest([KEY1, KEY2])
    envs = [_make_env(KEY1, 1, "ml-dsa-87")]
    check, att = _check_v7_attribution(m, envs)
    assert check.status == "PASS"
    assert att.cls == "Partially attributed"
    assert att.signed == 1
    assert att.declared == 2
    assert not att.keccak_independent
    assert att.keys[0]["status"] == "signed"
    assert att.keys[1]["status"] == "missing"


def test_attribution_table_row4_attributed_mldsa() -> None:
    # Row 4: 1 declared, 1 signed (ML-DSA-87) -> Attributed, keccak_independent=False
    m = _make_dummy_manifest([KEY1])
    envs = [_make_env(KEY1, 1, "ml-dsa-87")]
    check, att = _check_v7_attribution(m, envs)
    assert check.status == "PASS"
    assert att.cls == "Attributed"
    assert att.signed == 1
    assert att.declared == 1
    assert not att.keccak_independent
    assert att.keys[0]["status"] == "signed"


def test_attribution_table_row5_attributed_slhdsa_shake() -> None:
    # Row 5: 1 declared, 1 signed (SLH-DSA-SHAKE-256s) -> Attributed, keccak_independent=False
    m = _make_dummy_manifest([KEY1])
    envs = [_make_env(KEY1, 1, "slh-dsa-shake-256s")]
    check, att = _check_v7_attribution(m, envs)
    assert check.status == "PASS"
    assert att.cls == "Attributed"
    assert att.signed == 1
    assert att.declared == 1
    assert not att.keccak_independent


def test_attribution_table_row6_attributed_slhdsa_sha2() -> None:
    # Row 6: 1 declared, 1 signed (SLH-DSA-SHA2-256s) -> Attributed, keccak_independent=True
    m = _make_dummy_manifest([KEY1])
    envs = [_make_env(KEY1, 1, "slh-dsa-sha2-256s")]
    check, att = _check_v7_attribution(m, envs)
    assert check.status == "PASS"
    assert att.cls == "Attributed"
    assert att.signed == 1
    assert att.declared == 1
    assert att.keccak_independent


def test_attribution_table_row7_dual_family() -> None:
    # Row 7: 2 declared, 2 signed (ML-DSA-87 + SLH-DSA-SHA2-256s) -> Dual-family
    m = _make_dummy_manifest([KEY1, KEY2])
    envs = [_make_env(KEY1, 1, "ml-dsa-87"), _make_env(KEY2, 1, "slh-dsa-sha2-256s")]
    check, att = _check_v7_attribution(m, envs)
    assert check.status == "PASS"
    assert att.cls == "Dual-family"
    assert att.signed == 2
    assert att.declared == 2
    assert att.keccak_independent


def test_attribution_other_signatures_and_duplicate_keys() -> None:
    # Key signed twice with role 1, plus a contributor signature (role 2), plus undeclared key
    m = _make_dummy_manifest([KEY1])
    envs = [
        _make_env(KEY1, 1, "ml-dsa-87"),
        _make_env(KEY1, 1, "ml-dsa-87"),  # duplicate key, counted once
        _make_env(KEY1, 2, "ml-dsa-87"),  # contributor role
        _make_env(KEY3, 1, "ml-dsa-87"),  # undeclared key
    ]
    _check, att = _check_v7_attribution(m, envs)
    assert att.cls == "Attributed"
    assert att.signed == 1
    assert len(att.other_signatures) == 2
