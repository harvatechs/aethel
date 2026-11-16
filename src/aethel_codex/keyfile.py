"""AKF-1 key file creation, encryption, and secure loading (specs.md §13, security.md §4)."""

import os
import re
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from aethel_codex.backends import SignatureBackend, get_backend
from aethel_codex.constants import (
    ALGORITHMS,
    MAGIC_KEY,
    Algorithm,
)
from aethel_codex.envelope import strict_b64decode, strict_b64encode
from aethel_codex.errors import AethelError, KeyFileError
from aethel_codex.pid import Pid, key_id
from aethel_codex.unicode18 import nfc

MAX_KEYFILE_BYTES = 65536  # 64 KiB
SCRYPT_N = 131072  # 2^17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32
_IS_POSIX = os.name != "nt"

KDF_PARAMS_RE = re.compile(r"kdf-params n=([0-9]+),r=([0-9]+),p=([0-9]+),salt=([A-Za-z0-9+/=]+)")


class SecretKey:
    """Safe wrapper holding secret signing key material in a mutable bytearray."""

    def __init__(
        self,
        alg: Algorithm,
        key_pid: Pid,
        public_key: bytes,
        secret: bytearray | bytes,
    ) -> None:
        """Initialize SecretKey with algorithm, PID, public key, and secret bytes."""
        self.alg = alg
        self.key_pid = key_pid
        self.public_key = public_key
        self._secret = bytearray(secret)

    @property
    def secret_bytes(self) -> bytes:
        """Return secret key bytes."""
        return bytes(self._secret)

    def wipe(self) -> None:
        """Best-effort zeroization of secret key material in memory."""
        for i in range(len(self._secret)):
            self._secret[i] = 0

    def __repr__(self) -> str:
        """Never expose secret key material in representation."""
        return f"SecretKey(alg={self.alg.name!r}, key_pid={self.key_pid!r}, secret=***)"

    def __str__(self) -> str:
        """Format safe identifier representation."""
        return f"SecretKey({self.key_pid})"


def _normalize_passphrase(passphrase: str | bytes) -> bytes:
    if isinstance(passphrase, bytes):
        try:
            text = passphrase.decode("utf-8")
        except UnicodeDecodeError as e:
            raise KeyFileError(
                "KEYFILE_PASSPHRASE", f"Passphrase is not valid UTF-8: {e}"
            ) from None
    else:
        text = passphrase
    return nfc(text).encode("utf-8")


def _format_encrypted_content(
    backend_name: str,
    key_pid: Pid,
    public_key: bytes,
    secret_bytes: bytes,
    passphrase_bytes: bytes,
) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(12)

    kdf = Scrypt(
        salt=salt,
        length=SCRYPT_LEN,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    derived_key = kdf.derive(passphrase_bytes)

    header_lines = [
        MAGIC_KEY,
        f"alg {backend_name}",
        f"key {key_pid}",
        f"public-key {strict_b64encode(public_key)}",
        "protection scrypt-chacha20poly1305",
        f"kdf-params n={SCRYPT_N},r={SCRYPT_R},p={SCRYPT_P},salt={strict_b64encode(salt)}",
        f"nonce {strict_b64encode(nonce)}",
    ]
    header_text = "\n".join(header_lines) + "\n"
    aad = header_text.encode("utf-8")

    chacha = ChaCha20Poly1305(derived_key)
    ciphertext = chacha.encrypt(nonce, secret_bytes, aad)

    content = header_text + f"secret {strict_b64encode(ciphertext)}\n"
    return content.encode("utf-8")


def _format_unencrypted_content(
    backend_name: str, key_pid: Pid, public_key: bytes, secret_bytes: bytes
) -> bytes:
    lines = [
        MAGIC_KEY,
        f"alg {backend_name}",
        f"key {key_pid}",
        f"public-key {strict_b64encode(public_key)}",
        "protection none",
        f"secret {strict_b64encode(secret_bytes)}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def create_key(
    alg: int | str,
    path: Path | str,
    passphrase: str | bytes | None = None,
    secret_bytes: bytes | None = None,
) -> Path:
    """Generate or write an AKF-1 key file with strict O_EXCL and 0600 mode.

    Normative reference: specs.md §13, security.md §4.
    """
    backend = get_backend(alg)
    if secret_bytes is not None:
        public_key = backend.public_from_secret(secret_bytes)
    else:
        secret_bytes, public_key = backend.generate()

    k_id_str = key_id(backend.alg_id, public_key)
    key_pid = Pid.parse(k_id_str)

    if passphrase is not None and passphrase != "" and passphrase != b"":
        passphrase_bytes = _normalize_passphrase(passphrase)
        content_bytes = _format_encrypted_content(
            backend.name, key_pid, public_key, secret_bytes, passphrase_bytes
        )
    else:
        content_bytes = _format_unencrypted_content(backend.name, key_pid, public_key, secret_bytes)

    target_path = Path(path).resolve()
    try:
        fd = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise KeyFileError(
            "KEYFILE_INVALID", f"Refusing to overwrite existing key file: {target_path}"
        ) from None
    except OSError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Failed to create key file: {e}") from None

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content_bytes)
    except OSError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Failed to write key file: {e}") from None

    return target_path


def _parse_and_decrypt_encrypted_body(lines: list[str], passphrase: str | bytes | None) -> bytes:
    if len(lines) != 8:
        raise KeyFileError(
            "KEYFILE_INVALID", f"Encrypted keyfile must have 8 lines, got {len(lines)}"
        )

    if passphrase is None or passphrase == "" or passphrase == b"":
        raise KeyFileError("KEYFILE_PASSPHRASE", "Passphrase required for encrypted key")

    match = KDF_PARAMS_RE.fullmatch(lines[5])
    if not match:
        raise KeyFileError("KEYFILE_INVALID", f"Malformed kdf-params line: {lines[5]!r}")

    n = int(match.group(1))
    r = int(match.group(2))
    p = int(match.group(3))
    try:
        salt = strict_b64decode(match.group(4))
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid salt base64: {e}") from None

    if not lines[6].startswith("nonce "):
        raise KeyFileError("KEYFILE_INVALID", "Missing nonce line")
    try:
        nonce = strict_b64decode(lines[6][len("nonce ") :])
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid nonce base64: {e}") from None

    if not lines[7].startswith("secret "):
        raise KeyFileError("KEYFILE_INVALID", "Missing secret line")
    try:
        ciphertext = strict_b64decode(lines[7][len("secret ") :])
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid secret base64: {e}") from None

    passphrase_bytes = _normalize_passphrase(passphrase)
    kdf = Scrypt(salt=salt, length=SCRYPT_LEN, n=n, r=r, p=p)
    derived_key = kdf.derive(passphrase_bytes)

    header_text = "\n".join(lines[:7]) + "\n"
    aad = header_text.encode("utf-8")

    chacha = ChaCha20Poly1305(derived_key)
    try:
        secret_bytes = chacha.decrypt(nonce, ciphertext, aad)
    except InvalidTag:
        raise KeyFileError(
            "KEYFILE_PASSPHRASE", "Incorrect passphrase or tampered keyfile"
        ) from None

    return secret_bytes


def _validate_key_file_permissions(path: Path) -> None:
    try:
        st = os.lstat(path)
    except OSError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Cannot stat key file: {e}") from None

    if _IS_POSIX and (st.st_mode & 0o077 != 0):
        raise KeyFileError(
            "KEYFILE_PERMISSIONS",
            f"Key file {path} has permissions {oct(st.st_mode & 0o777)}, wider than 0600",
        )

    if st.st_size > MAX_KEYFILE_BYTES:
        raise KeyFileError(
            "KEYFILE_INVALID", f"Key file size {st.st_size} exceeds {MAX_KEYFILE_BYTES} bytes"
        )


def _parse_keyfile_header(lines: list[str]) -> tuple[SignatureBackend, Pid, bytes, str]:
    """Parse and validate header lines (0-4) of an AKF-1 key file."""
    if lines[0] != MAGIC_KEY:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid key magic: {lines[0]!r}")

    if not lines[1].startswith("alg "):
        raise KeyFileError("KEYFILE_INVALID", "Line 1 must start with 'alg '")
    alg_name = lines[1][len("alg ") :]
    try:
        backend = get_backend(alg_name)
    except AethelError:
        raise KeyFileError("KEYFILE_INVALID", f"Unknown algorithm name: {alg_name!r}") from None

    if not lines[2].startswith("key "):
        raise KeyFileError("KEYFILE_INVALID", "Line 2 must start with 'key '")
    try:
        key_pid = Pid.parse(lines[2][len("key ") :])
        if key_pid.pid_type != "k":
            raise KeyFileError("KEYFILE_INVALID", "Key PID type must be 'k'")
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid key PID: {e}") from None

    if not lines[3].startswith("public-key "):
        raise KeyFileError("KEYFILE_INVALID", "Line 3 must start with 'public-key '")
    try:
        public_key = strict_b64decode(lines[3][len("public-key ") :])
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid public-key base64: {e}") from None

    if not lines[4].startswith("protection "):
        raise KeyFileError("KEYFILE_INVALID", "Line 4 must start with 'protection '")
    protection = lines[4][len("protection ") :]

    return backend, key_pid, public_key, protection


def _parse_unencrypted_secret(lines: list[str]) -> bytes:
    """Parse secret line from unencrypted AKF-1 key file."""
    if len(lines) != 6:
        raise KeyFileError(
            "KEYFILE_INVALID", f"Unencrypted keyfile must have 6 lines, got {len(lines)}"
        )
    if not lines[5].startswith("secret "):
        raise KeyFileError("KEYFILE_INVALID", "Line 5 must start with 'secret '")
    try:
        return strict_b64decode(lines[5][len("secret ") :])
    except AethelError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Invalid secret base64: {e}") from None


def _check_key_consistency(
    backend: SignatureBackend,
    key_pid: Pid,
    public_key: bytes,
    secret_bytes: bytes,
) -> None:
    """Validate public key hash, secret length, and public key derivation."""
    expected_k_id = key_id(backend.alg_id, public_key)
    if str(key_pid) != expected_k_id:
        raise KeyFileError(
            "KEYFILE_INVALID",
            f"Public key does not hash to declared key ID: {key_pid} != {expected_k_id}",
        )

    expected_secret_size = ALGORITHMS[backend.alg_id].secret_key_size
    if len(secret_bytes) != expected_secret_size:
        raise KeyFileError(
            "KEYFILE_INVALID",
            f"Secret key length mismatch for {backend.name}: "
            f"got {len(secret_bytes)}, expected {expected_secret_size}",
        )

    derived_public = backend.public_from_secret(secret_bytes)
    if derived_public != public_key:
        raise KeyFileError(
            "KEYFILE_INVALID", "Derived public key does not match declared public key"
        )


def _read_and_split_keyfile(target_path: Path) -> list[str]:
    """Read binary key file and strictly validate line formatting."""
    _validate_key_file_permissions(target_path)
    try:
        data = target_path.read_bytes()
    except OSError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Cannot read key file: {e}") from None

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise KeyFileError("KEYFILE_INVALID", f"Key file is not valid UTF-8: {e}") from None

    if "\r" in text:
        raise KeyFileError("KEYFILE_INVALID", "Carriage return is forbidden in key file")
    if not text.endswith("\n"):
        raise KeyFileError("KEYFILE_INVALID", "Key file must end with linefeed")

    lines = text.split("\n")[:-1]
    if len(lines) < 6:
        raise KeyFileError("KEYFILE_INVALID", f"Key file has too few lines: {len(lines)}")
    return lines


def load_key(path: Path | str, passphrase: str | bytes | None = None) -> SecretKey:
    """Load, decrypt (if encrypted), and validate an AKF-1 key file.

    Normative reference: specs.md §13, security.md §4.
    """
    target_path = Path(path).resolve()
    lines = _read_and_split_keyfile(target_path)
    backend, key_pid, public_key, protection = _parse_keyfile_header(lines)

    if protection == "none":
        secret_bytes = _parse_unencrypted_secret(lines)
    elif protection == "scrypt-chacha20poly1305":
        secret_bytes = _parse_and_decrypt_encrypted_body(lines, passphrase)
    else:
        raise KeyFileError("KEYFILE_INVALID", f"Unknown protection scheme: {protection!r}")

    _check_key_consistency(backend, key_pid, public_key, secret_bytes)

    return SecretKey(
        alg=ALGORITHMS[backend.alg_id],
        key_pid=key_pid,
        public_key=public_key,
        secret=secret_bytes,
    )
