"""Test protocol constants (R-PROTO-04, PT0)."""

import json
from pathlib import Path

from aethel_codex import constants


def test_constants_match_test_vectors() -> None:
    vectors_path = Path(__file__).resolve().parent.parent / "vectors" / "pip1-vectors.json"
    with open(vectors_path, encoding="utf-8") as f:
        vectors = json.load(f)

    labels_vec = vectors["constants"]["labels"]

    # Verify each label's length byte and lp
    for label_str, expected in labels_vec.items():
        label_bytes = label_str.encode("utf-8")
        assert len(label_bytes) == int(expected["length_byte_hex"], 16)
        lp_bytes = bytes([len(label_bytes)]) + label_bytes
        assert lp_bytes.hex() == expected["lp_hex"]

    assert constants.LABEL_LEAF == b"pip1.leaf"
    assert constants.LABEL_NODE == b"pip1.node"
    assert constants.LABEL_TEXT == b"pip1.text"
    assert constants.LABEL_ASSET == b"pip1.asset"
    assert constants.LABEL_MANIFEST == b"pip1.manifest"
    assert constants.LABEL_KEY == b"pip1.key"
    assert constants.SIG_CONTEXT == b"pip1.sig"
    assert constants.CHUNK_SIZE == 4096
    assert constants.UNICODE_VERSION == "18.0.0"


def test_algorithms_table() -> None:
    algs = constants.ALGORITHMS
    assert len(algs) == 4

    mldsa87 = algs[0x02]
    assert mldsa87.name == "ml-dsa-87"
    assert mldsa87.public_key_size == 2592
    assert mldsa87.signature_size == 4627
    assert mldsa87.secret_key_size == 32
    assert mldsa87.family == "ml"

    mldsa65 = algs[0x01]
    assert mldsa65.name == "ml-dsa-65"
    assert mldsa65.public_key_size == 1952
    assert mldsa65.signature_size == 3309
    assert mldsa65.secret_key_size == 32
    assert mldsa65.family == "ml"

    slh_shake = algs[0x10]
    assert slh_shake.name == "slh-dsa-shake-256s"
    assert slh_shake.public_key_size == 64
    assert slh_shake.signature_size == 29792
    assert slh_shake.secret_key_size == 128
    assert slh_shake.family == "slh"

    slh_sha2 = algs[0x11]
    assert slh_sha2.name == "slh-dsa-sha2-256s"
    assert slh_sha2.public_key_size == 64
    assert slh_sha2.signature_size == 29792
    assert slh_sha2.secret_key_size == 128
    assert slh_sha2.family == "slh"


def test_roles_table() -> None:
    assert constants.ROLE_AUTHOR == 0x01
    assert constants.ROLE_CONTRIBUTOR == 0x02
    assert constants.ROLE_TRANSLATOR == 0x03
    assert constants.ROLE_ENDORSER == 0x04
    assert constants.ROLES[0x01] == "author"
    assert constants.ROLES[0x02] == "contributor"
    assert constants.ROLES[0x03] == "translator"
    assert constants.ROLES[0x04] == "endorser"
