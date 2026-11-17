"""SGE-1 signature envelope parsing and serialization (YP §9.4, specs.md §8)."""

import base64
import binascii
import re
from dataclasses import dataclass

from aethel_codex.constants import ALGORITHM_BY_NAME, MAX_ENVELOPE_BYTES, ROLE_BY_NAME, ROLES
from aethel_codex.errors import AethelError, EnvelopeError
from aethel_codex.pid import Pid

ROLE_NAME_TO_INT: dict[str, int] = ROLE_BY_NAME
ROLE_INT_TO_NAME: dict[int, str] = ROLES
HEX_ROLE_RE = re.compile(r"0x([0-9a-f]{2})")
KIND_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


def strict_b64decode(s: str) -> bytes:
    """Strictly decode Base64 string, rejecting non-canonical padding and stray bits.

    Normative reference: specs.md §8, Question Q-08.
    """
    try:
        decoded = base64.b64decode(s, validate=True)
    except (ValueError, binascii.Error) as e:
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid base64 payload: {e}") from None
    if base64.b64encode(decoded).decode("ascii") != s:
        raise EnvelopeError("ENVELOPE_INVALID", "Non-canonical base64 encoding")
    return decoded


def strict_b64encode(b: bytes) -> str:
    """Encode bytes to strict canonical Base64 string."""
    return base64.b64encode(b).decode("ascii")


@dataclass(frozen=True)
class SignatureEnvelope:
    """SGE-1 signature envelope."""

    manifest_pid: Pid
    role: int  # 1..255 (0 is forbidden)
    alg_name: str
    key_pid: Pid
    public_key: bytes
    signature: bytes
    raw_bytes: bytes = b""

    def role_name(self) -> str:
        """Return role name for standard roles (1..4) or 0xHH string for custom roles."""
        if self.role in ROLE_INT_TO_NAME:
            return ROLE_INT_TO_NAME[self.role]
        return f"0x{self.role:02x}"

    def envelope_filename(self) -> str:
        """Return canonical envelope file path convention."""
        return f"signatures/{self.role_name()}-{self.alg_name}-{self.key_pid.hex()[:16]}.sig"


def _parse_role(line: str) -> int:
    if not line.startswith("role "):
        raise EnvelopeError("ENVELOPE_INVALID", "Envelope line 2 must start with 'role '")
    role_str = line[len("role ") :]
    if role_str in ROLE_NAME_TO_INT:
        return ROLE_NAME_TO_INT[role_str]
    if HEX_ROLE_RE.fullmatch(role_str):
        role = int(role_str[2:], 16)
        if role == 0:
            raise EnvelopeError("ENVELOPE_INVALID", "Role 0x00 is reserved and forbidden")
        return role
    raise EnvelopeError("ENVELOPE_INVALID", f"Invalid role format: {role_str!r}")


def _parse_pid_field(line: str, prefix: str, expected_type: str, line_num: int) -> Pid:
    if not line.startswith(prefix):
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Envelope line {line_num} must start with {prefix!r}"
        )
    try:
        pid = Pid.parse(line[len(prefix) :])
        if pid.pid_type != expected_type:
            raise EnvelopeError(
                "ENVELOPE_INVALID", f"Expected PID type '{expected_type}', got '{pid.pid_type}'"
            )
        return pid
    except AethelError as e:
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid PID in line {line_num}: {e}") from None


def _parse_b64_field(line: str, prefix: str, line_num: int) -> bytes:
    if not line.startswith(prefix):
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Envelope line {line_num} must start with {prefix!r}"
        )
    return strict_b64decode(line[len(prefix) :])


def parse_envelope(data: bytes) -> SignatureEnvelope:
    """Parse SGE-1 signature envelope bytes.

    Normative reference: Yellow Paper §9.4, specs.md §8.
    """
    if len(data) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Envelope exceeds maximum size {MAX_ENVELOPE_BYTES} bytes"
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid UTF-8 in envelope: {e}") from None

    if "\r" in text:
        raise EnvelopeError("ENVELOPE_INVALID", "Carriage return is not permitted in envelope")
    if not text.endswith("\n"):
        raise EnvelopeError("ENVELOPE_INVALID", "Envelope must end with a linefeed")

    lines = text.split("\n")[:-1]
    if len(lines) != 7:
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Envelope must have exactly 7 lines, got {len(lines)}"
        )

    if lines[0] != "pip-signature 1":
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid envelope magic line: {lines[0]!r}")

    manifest_pid = _parse_pid_field(lines[1], "manifest ", "m", 1)
    role = _parse_role(lines[2])

    if not lines[3].startswith("alg "):
        raise EnvelopeError("ENVELOPE_INVALID", "Envelope line 3 must start with 'alg '")
    alg_name = lines[3][len("alg ") :]
    if alg_name not in ALGORITHM_BY_NAME:
        raise EnvelopeError("ENVELOPE_INVALID", f"Unknown algorithm name: {alg_name!r}")

    key_pid = _parse_pid_field(lines[4], "key ", "k", 4)
    public_key = _parse_b64_field(lines[5], "public-key ", 5)
    signature = _parse_b64_field(lines[6], "signature ", 6)

    return SignatureEnvelope(
        manifest_pid=manifest_pid,
        role=role,
        alg_name=alg_name,
        key_pid=key_pid,
        public_key=public_key,
        signature=signature,
        raw_bytes=data,
    )


def serialize_envelope(env: SignatureEnvelope) -> bytes:
    """Serialize signature envelope to canonical SGE-1 UTF-8 bytes."""
    lines: list[str] = [
        "pip-signature 1",
        f"manifest {env.manifest_pid}",
        f"role {env.role_name()}",
        f"alg {env.alg_name}",
        f"key {env.key_pid}",
        f"public-key {strict_b64encode(env.public_key)}",
        f"signature {strict_b64encode(env.signature)}",
    ]
    return "\n".join(lines).encode("utf-8") + b"\n"


@dataclass(frozen=True)
class AttestationEnvelope:
    """ATT-1 attestation envelope (YP §10.3, specs.md §8)."""

    manifest_pid: Pid
    kind: str
    proof: bytes
    raw_bytes: bytes = b""

    def envelope_filename(self) -> str:
        """Return canonical attestation file path convention."""
        return f"attestations/{self.kind}.att"


def parse_attestation_envelope(data: bytes) -> AttestationEnvelope:
    """Parse ATT-1 attestation envelope bytes.

    Normative reference: Yellow Paper §10.3, specs.md §8.
    """
    if len(data) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Envelope exceeds maximum size {MAX_ENVELOPE_BYTES} bytes"
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid UTF-8 in envelope: {e}") from None

    if "\r" in text:
        raise EnvelopeError("ENVELOPE_INVALID", "Carriage return is not permitted in envelope")
    if not text.endswith("\n"):
        raise EnvelopeError("ENVELOPE_INVALID", "Envelope must end with a linefeed")

    lines = text.split("\n")[:-1]
    if len(lines) != 4:
        raise EnvelopeError(
            "ENVELOPE_INVALID", f"Attestation envelope must have exactly 4 lines, got {len(lines)}"
        )

    if lines[0] != "pip-attestation 1":
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid attestation magic line: {lines[0]!r}")

    manifest_pid = _parse_pid_field(lines[1], "manifest ", "m", 1)

    if not lines[2].startswith("kind "):
        raise EnvelopeError("ENVELOPE_INVALID", "Attestation line 2 must start with 'kind '")
    kind = lines[2][len("kind ") :]
    if not KIND_RE.fullmatch(kind):
        raise EnvelopeError("ENVELOPE_INVALID", f"Invalid attestation kind: {kind!r}")

    proof = _parse_b64_field(lines[3], "proof ", 3)

    return AttestationEnvelope(
        manifest_pid=manifest_pid,
        kind=kind,
        proof=proof,
        raw_bytes=data,
    )


def serialize_attestation_envelope(env: AttestationEnvelope) -> bytes:
    """Serialize attestation envelope to canonical ATT-1 UTF-8 bytes."""
    lines: list[str] = [
        "pip-attestation 1",
        f"manifest {env.manifest_pid}",
        f"kind {env.kind}",
        f"proof {strict_b64encode(env.proof)}",
    ]
    return "\n".join(lines).encode("utf-8") + b"\n"
