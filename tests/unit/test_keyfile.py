"""Unit tests for AKF-1 key file creation, encryption, loading, and permissions."""

import os
import stat
from pathlib import Path

import pytest

from aethel_codex.errors import KeyFileError
from aethel_codex.keyfile import SecretKey, create_key, load_key


@pytest.mark.req("UR-05")
@pytest.mark.req("UR-39")
def test_keyfile_roundtrip_unencrypted(tmp_path: Path) -> None:
    key_path = tmp_path / "plain.aek"
    created = create_key("ml-dsa-87", key_path)
    assert created == key_path
    assert key_path.exists()

    # Load unencrypted key
    sk = load_key(key_path)
    assert sk.alg.name == "ml-dsa-87"
    assert len(sk.public_key) == 2592
    assert len(sk.secret_bytes) == 32
    assert sk.key_pid.pid_type == "k"


@pytest.mark.req("UR-06")
def test_keyfile_roundtrip_encrypted(tmp_path: Path) -> None:
    key_path = tmp_path / "encrypted.aek"
    passphrase = "correct horse battery staple"  # noqa: S105

    create_key("ml-dsa-87", key_path, passphrase=passphrase)
    assert key_path.exists()

    # Load with correct passphrase
    sk = load_key(key_path, passphrase=passphrase)
    assert sk.alg.name == "ml-dsa-87"
    assert len(sk.public_key) == 2592
    assert len(sk.secret_bytes) == 32

    # Load with wrong passphrase fails
    with pytest.raises(KeyFileError) as exc_info:
        load_key(key_path, passphrase="wrong passphrase")  # noqa: S106
    assert exc_info.value.code == "KEYFILE_PASSPHRASE"

    # Load without passphrase fails
    with pytest.raises(KeyFileError) as exc_info2:
        load_key(key_path, passphrase=None)
    assert exc_info2.value.code == "KEYFILE_PASSPHRASE"


def test_keyfile_aad_tamper_fails(tmp_path: Path) -> None:
    key_path = tmp_path / "tampered.aek"
    passphrase = "secure passphrase"  # noqa: S105
    create_key("ml-dsa-87", key_path, passphrase=passphrase)

    # Tamper with the alg header line
    lines = key_path.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "alg ml-dsa-87"
    # Replace with another valid alg name to check AAD detection rather than parse error
    lines[1] = "alg ml-dsa-65"
    key_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(KeyFileError) as exc_info:
        load_key(key_path, passphrase=passphrase)
    assert exc_info.value.code in ("KEYFILE_PASSPHRASE", "KEYFILE_INVALID")


def test_keyfile_o_excl_refuses_overwrite(tmp_path: Path) -> None:
    key_path = tmp_path / "existing.aek"
    create_key("ml-dsa-87", key_path)

    # Attempt to create again at same path must raise KeyFileError
    with pytest.raises(KeyFileError) as exc_info:
        create_key("ml-dsa-87", key_path)
    assert exc_info.value.code == "KEYFILE_INVALID"


def test_keyfile_permissions_check_posix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_path = tmp_path / "perms.aek"
    create_key("ml-dsa-87", key_path)

    # Mock _IS_POSIX to simulate POSIX
    monkeypatch.setattr("aethel_codex.keyfile._IS_POSIX", True)

    class MockStat:
        st_mode = stat.S_IFREG | 0o644  # Group and other readable!
        st_size = 500

    monkeypatch.setattr(os, "lstat", lambda _: MockStat())

    with pytest.raises(KeyFileError) as exc_info:
        load_key(key_path)
    assert exc_info.value.code == "KEYFILE_PERMISSIONS"


def test_keyfile_public_secret_consistency_check(tmp_path: Path) -> None:
    key_path = tmp_path / "inconsistent.aek"
    create_key("ml-dsa-87", key_path)

    # Tamper with public key line to another valid base64 string
    from aethel_codex.envelope import strict_b64encode

    lines = key_path.read_text(encoding="utf-8").splitlines()
    lines[3] = f"public-key {strict_b64encode(b'A' * 2592)}"
    key_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(KeyFileError) as exc_info:
        load_key(key_path)
    assert exc_info.value.code == "KEYFILE_INVALID"


def test_secret_key_memory_and_repr_safety() -> None:
    from aethel_codex.constants import ALG_ML_DSA_87
    from aethel_codex.pid import Pid

    secret_raw = b"\x42" * 32
    pub_raw = b"\x99" * 2592
    key_pid = Pid.parse("pip1:k:" + "01" * 32)

    sk = SecretKey(ALG_ML_DSA_87, key_pid, pub_raw, secret_raw)

    # Ensure secret bytes are not present in repr or str
    repr_str = repr(sk)
    str_str = str(sk)
    assert "42" not in repr_str
    assert "42" not in str_str
    assert "***" in repr_str

    # Test wipe
    assert sk.secret_bytes == secret_raw
    sk.wipe()
    assert sk.secret_bytes == b"\x00" * 32


def test_keyfile_slhdsa_suites(tmp_path: Path) -> None:
    for alg in ["slh-dsa-shake-256s", "slh-dsa-sha2-256s", "ml-dsa-65"]:
        kp = tmp_path / f"{alg}.aek"
        create_key(alg, kp, passphrase="pwd")  # noqa: S106
        sk = load_key(kp, passphrase="pwd")  # noqa: S106
        assert sk.alg.name == alg


def test_keyfile_syntax_and_validation_errors(tmp_path: Path) -> None:
    from aethel_codex.keyfile import _normalize_passphrase

    # Invalid UTF-8 bytes passphrase
    with pytest.raises(KeyFileError) as exc:
        _normalize_passphrase(b"\xff\xfe")
    assert exc.value.code == "KEYFILE_PASSPHRASE"

    # Base valid key
    base_kp = tmp_path / "base.aek"
    create_key("ml-dsa-87", base_kp)
    base_text = base_kp.read_text(encoding="utf-8")

    # 1. Non-existent file
    with pytest.raises(KeyFileError) as exc:
        load_key(tmp_path / "does_not_exist.aek")
    assert exc.value.code == "KEYFILE_INVALID"

    # 2. Oversized keyfile
    large_kp = tmp_path / "large.aek"
    large_kp.write_bytes(b"a" * 70000)
    with pytest.raises(KeyFileError) as exc:
        load_key(large_kp)
    assert exc.value.code == "KEYFILE_INVALID"

    # 3. Invalid UTF-8 in keyfile
    bad_utf8 = tmp_path / "bad_utf8.aek"
    bad_utf8.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_utf8)
    assert exc.value.code == "KEYFILE_INVALID"

    # 4. Carriage return in keyfile
    cr_kp = tmp_path / "cr.aek"
    cr_kp.write_bytes(base_text.replace("\n", "\r\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(cr_kp)
    assert exc.value.code == "KEYFILE_INVALID"

    # 5. Missing trailing linefeed
    no_lf = tmp_path / "no_lf.aek"
    no_lf.write_bytes(base_text.rstrip("\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(no_lf)
    assert exc.value.code == "KEYFILE_INVALID"

    # 6. Bad magic line
    bad_magic = tmp_path / "bad_magic.aek"
    lines = base_text.splitlines()
    lines[0] = "pip-key 1"
    bad_magic.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_magic)
    assert exc.value.code == "KEYFILE_INVALID"

    # 7. Bad alg line
    bad_alg = tmp_path / "bad_alg.aek"
    lines = base_text.splitlines()
    lines[1] = "alg unknown-alg"
    bad_alg.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_alg)
    assert exc.value.code == "KEYFILE_INVALID"

    # 8. Bad key line
    bad_key = tmp_path / "bad_key.aek"
    lines = base_text.splitlines()
    lines[2] = "key pip1:m:" + "00" * 32  # wrong type 'm'
    bad_key.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_key)
    assert exc.value.code == "KEYFILE_INVALID"

    # 9. Bad protection line
    bad_prot = tmp_path / "bad_prot.aek"
    lines = base_text.splitlines()
    lines[4] = "protection unknown-prot"
    bad_prot.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_prot)
    assert exc.value.code == "KEYFILE_INVALID"

    # 10. Malformed kdf-params in encrypted keyfile
    enc_kp = tmp_path / "enc.aek"
    create_key("ml-dsa-87", enc_kp, passphrase="pwd")  # noqa: S106
    enc_text = enc_kp.read_text(encoding="utf-8")
    lines_enc = enc_text.splitlines()
    lines_enc[5] = "kdf-params malformed"
    bad_kdf = tmp_path / "bad_kdf.aek"
    bad_kdf.write_bytes(("\n".join(lines_enc) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(bad_kdf, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"


def test_keyfile_comprehensive_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aethel_codex.backends import get_backend

    backend = get_backend("ml-dsa-87")
    sec, _ = backend.generate()

    # 1. create_key with explicit secret_bytes
    explicit_path = tmp_path / "explicit.aek"
    create_key("ml-dsa-87", explicit_path, secret_bytes=sec)
    sk = load_key(explicit_path)
    assert sk.secret_bytes == sec

    # 2. create_key OSError on open
    def mock_open(*args: object, **kwargs: object) -> int:
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "open", mock_open)
    with pytest.raises(KeyFileError) as exc:
        create_key("ml-dsa-87", tmp_path / "err.aek")
    assert exc.value.code == "KEYFILE_INVALID"
    monkeypatch.undo()

    # 3. create_key OSError on write
    def mock_fdopen(fd: int, mode: str) -> object:
        os.close(fd)
        raise OSError("Disk full")

    monkeypatch.setattr(os, "fdopen", mock_fdopen)
    with pytest.raises(KeyFileError) as exc:
        create_key("ml-dsa-87", tmp_path / "err_write.aek")
    assert exc.value.code == "KEYFILE_INVALID"
    monkeypatch.undo()

    # 4. load_key OSError on read
    def mock_read_bytes(self: Path) -> bytes:
        raise OSError("I/O error")

    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)
    with pytest.raises(KeyFileError) as exc:
        load_key(explicit_path)
    assert exc.value.code == "KEYFILE_INVALID"
    monkeypatch.undo()

    # 5. Encrypted keyfile corrupted lines
    enc_kp = tmp_path / "enc2.aek"
    create_key("ml-dsa-87", enc_kp, passphrase="pwd")  # noqa: S106
    enc_lines = enc_kp.read_text(encoding="utf-8").splitlines()

    # Wrong line count (7 lines)
    p7 = tmp_path / "enc_7lines.aek"
    p7.write_bytes(("\n".join(enc_lines[:7]) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p7, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # Bad salt base64
    bad_salt_lines = list(enc_lines)
    bad_salt_lines[5] = "kdf-params n=131072,r=8,p=1,salt=not_valid_b64!!!"
    p_salt = tmp_path / "bad_salt.aek"
    p_salt.write_bytes(("\n".join(bad_salt_lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_salt, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # Missing nonce prefix
    bad_nonce_lines = list(enc_lines)
    bad_nonce_lines[6] = "noncenonprefix xxxx"
    p_nonce = tmp_path / "bad_nonce.aek"
    p_nonce.write_bytes(("\n".join(bad_nonce_lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_nonce, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # Bad nonce base64
    bad_nonce_b64 = list(enc_lines)
    bad_nonce_b64[6] = "nonce invalid_b64!!!"
    p_nonce_b64 = tmp_path / "bad_nonce_b64.aek"
    p_nonce_b64.write_bytes(("\n".join(bad_nonce_b64) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_nonce_b64, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # Missing secret prefix in encrypted
    bad_sec_lines = list(enc_lines)
    bad_sec_lines[7] = "secretprefix xxxx"
    p_sec = tmp_path / "bad_sec.aek"
    p_sec.write_bytes(("\n".join(bad_sec_lines) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_sec, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # Bad secret base64 in encrypted
    bad_sec_b64 = list(enc_lines)
    bad_sec_b64[7] = "secret invalid_b64!!!"
    p_sec_b64 = tmp_path / "bad_sec_b64.aek"
    p_sec_b64.write_bytes(("\n".join(bad_sec_b64) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_sec_b64, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"

    # 6. Unencrypted header and body edge cases
    plain_kp = tmp_path / "plain2.aek"
    create_key("ml-dsa-87", plain_kp)
    plain_lines = plain_kp.read_text(encoding="utf-8").splitlines()

    # Missing alg prefix
    bad_hdr = list(plain_lines)
    bad_hdr[1] = "algorithm ml-dsa-87"
    p_hdr = tmp_path / "bad_hdr1.aek"
    p_hdr.write_bytes(("\n".join(bad_hdr) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_hdr)
    assert exc.value.code == "KEYFILE_INVALID"

    # Missing key prefix
    bad_hdr = list(plain_lines)
    bad_hdr[2] = "keyid pip1:k:xxxx"
    p_hdr = tmp_path / "bad_hdr2.aek"
    p_hdr.write_bytes(("\n".join(bad_hdr) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_hdr)
    assert exc.value.code == "KEYFILE_INVALID"

    # Missing public-key prefix
    bad_hdr = list(plain_lines)
    bad_hdr[3] = "pubkey xxxx"
    p_hdr = tmp_path / "bad_hdr3.aek"
    p_hdr.write_bytes(("\n".join(bad_hdr) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_hdr)
    assert exc.value.code == "KEYFILE_INVALID"

    # Bad public-key base64
    bad_hdr = list(plain_lines)
    bad_hdr[3] = "public-key invalid_b64!!!"
    p_hdr = tmp_path / "bad_hdr4.aek"
    p_hdr.write_bytes(("\n".join(bad_hdr) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_hdr)
    assert exc.value.code == "KEYFILE_INVALID"

    # Missing protection prefix
    bad_hdr = list(plain_lines)
    bad_hdr[4] = "protect none"
    p_hdr = tmp_path / "bad_hdr5.aek"
    p_hdr.write_bytes(("\n".join(bad_hdr) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_hdr)
    assert exc.value.code == "KEYFILE_INVALID"

    # Unencrypted wrong lines count (7 lines)
    bad_plain = [*list(plain_lines), "extra line"]
    p_plain = tmp_path / "bad_plain_count.aek"
    p_plain.write_bytes(("\n".join(bad_plain) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_plain)
    assert exc.value.code == "KEYFILE_INVALID"

    # Unencrypted missing secret prefix
    bad_plain = list(plain_lines)
    bad_plain[5] = "sec xxxx"
    p_plain = tmp_path / "bad_plain_sec.aek"
    p_plain.write_bytes(("\n".join(bad_plain) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_plain)
    assert exc.value.code == "KEYFILE_INVALID"

    # Unencrypted bad secret base64
    bad_plain = list(plain_lines)
    bad_plain[5] = "secret invalid_b64!!!"
    p_plain = tmp_path / "bad_plain_b64.aek"
    p_plain.write_bytes(("\n".join(bad_plain) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_plain)
    assert exc.value.code == "KEYFILE_INVALID"

    # 7. Semantic mismatch checks
    # Public key does not hash to declared key ID
    tamper_kpid = list(plain_lines)
    tamper_kpid[2] = "key pip1:k:" + "00" * 32
    p_kpid = tmp_path / "tamper_kpid.aek"
    p_kpid.write_bytes(("\n".join(tamper_kpid) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_kpid)
    assert exc.value.code == "KEYFILE_INVALID"

    # Secret key length mismatch
    from aethel_codex.envelope import strict_b64encode

    tamper_seclen = list(plain_lines)
    tamper_seclen[5] = f"secret {strict_b64encode(b'short')}"
    p_seclen = tmp_path / "tamper_seclen.aek"
    p_seclen.write_bytes(("\n".join(tamper_seclen) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_seclen)
    assert exc.value.code == "KEYFILE_INVALID"

    # Derived public key mismatch (32-byte secret for ml-dsa-87 replaced with different 32 bytes)
    tamper_pubmatch = list(plain_lines)
    tamper_pubmatch[5] = f"secret {strict_b64encode(b'x' * 32)}"
    p_pubmatch = tmp_path / "tamper_pubmatch.aek"
    p_pubmatch.write_bytes(("\n".join(tamper_pubmatch) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_pubmatch)
    assert exc.value.code == "KEYFILE_INVALID"

    # Fewer than 6 lines
    p_short = tmp_path / "short_lines.aek"
    p_short.write_bytes(b"aethel-key 1\nalg ml-dsa-87\n")
    with pytest.raises(KeyFileError) as exc:
        load_key(p_short)
    assert exc.value.code == "KEYFILE_INVALID"

    # Bad salt length in kdf-params (valid b64 chars but invalid b64 padding/length)
    bad_salt_len = list(enc_lines)
    bad_salt_len[5] = "kdf-params n=131072,r=8,p=1,salt=ABC"
    p_salt_len = tmp_path / "bad_salt_len.aek"
    p_salt_len.write_bytes(("\n".join(bad_salt_len) + "\n").encode("utf-8"))
    with pytest.raises(KeyFileError) as exc:
        load_key(p_salt_len, passphrase="pwd")  # noqa: S106
    assert exc.value.code == "KEYFILE_INVALID"
