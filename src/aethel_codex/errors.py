"""Error code registry and typed exception hierarchy (YP §14.2, specs.md §14)."""


class ErrorCodeInfo:
    """Metadata describing a registered error code."""

    def __init__(self, code: str, source: str, meaning: str, yp_section: str) -> None:
        """Initialize error code metadata."""
        self.code = code
        self.source = source  # "Y" = Yellow Paper normative, "P" = Pack defined
        self.meaning = meaning
        self.yp_section = yp_section


ERROR_CODE_REGISTRY: dict[str, ErrorCodeInfo] = {
    # CTF-1 rejections (YP §4.2, §14.2)
    "E_INVALID_UTF8": ErrorCodeInfo("E_INVALID_UTF8", "Y", "Input is not valid UTF-8", "§4.2"),
    "E_FORBIDDEN_CODEPOINT": ErrorCodeInfo(
        "E_FORBIDDEN_CODEPOINT", "Y", "Text contains a forbidden scalar value", "§4.3"
    ),
    "E_UNASSIGNED_CODEPOINT": ErrorCodeInfo(
        "E_UNASSIGNED_CODEPOINT", "Y", "Text contains an unassigned scalar value", "§4.3"
    ),
    "E_EMPTY_TEXT": ErrorCodeInfo(
        "E_EMPTY_TEXT", "Y", "Text is empty after canonicalization", "§4.2"
    ),
    # Manifest rejections (YP §7.6, A.3)
    "E_FIELD_ORDER": ErrorCodeInfo(
        "E_FIELD_ORDER", "Y", "Manifest fields appear in incorrect order", "§7.2"
    ),
    "E_BAD_LINES": ErrorCodeInfo(
        "E_BAD_LINES", "Y", "Manifest lines violate syntax or line terminator rules", "§7.1"
    ),
    "E_UNKNOWN_PROFILE": ErrorCodeInfo(
        "E_UNKNOWN_PROFILE", "Y", "Profile token is unrecognized", "§7.3"
    ),
    "E_NOT_SORTED_OR_UNIQUE": ErrorCodeInfo(
        "E_NOT_SORTED_OR_UNIQUE", "Y", "Repeated fields are not strictly sorted or unique", "§7.4"
    ),
    "E_BAD_VALUE": ErrorCodeInfo(
        "E_BAD_VALUE", "Y", "Field value violates grammar or character constraints", "§7.3"
    ),
    "E_INTEGER_RANGE": ErrorCodeInfo(
        "E_INTEGER_RANGE", "Y", "Integer value exceeds 2^64 - 1", "§7.3"
    ),
    "E_BAD_MAGIC": ErrorCodeInfo(
        "E_BAD_MAGIC", "P", "Manifest does not begin with pip-manifest 1", "§7.1"
    ),
    "E_UNKNOWN_KEY": ErrorCodeInfo(
        "E_UNKNOWN_KEY", "P", "Manifest contains an unrecognized field key", "§7.2"
    ),
    "E_MISSING_FIELD": ErrorCodeInfo(
        "E_MISSING_FIELD", "P", "Required manifest field is missing", "§7.2"
    ),
    "E_WORK_PARENT_RULE": ErrorCodeInfo(
        "E_WORK_PARENT_RULE", "P", "work field present without parent or vice versa", "§7.3"
    ),
    "E_ROUNDTRIP": ErrorCodeInfo(
        "E_ROUNDTRIP", "P", "Re-serialized manifest does not match input bytes", "§7.6"
    ),
    # Verification codes (YP §11.2)
    "MANIFEST_INVALID": ErrorCodeInfo(
        "MANIFEST_INVALID", "Y", "Manifest failed strict grammar parsing", "§11.2"
    ),
    "ID_MISMATCH": ErrorCodeInfo(
        "ID_MISMATCH", "Y", "Computed manifest identifier does not match directory name", "§11.2"
    ),
    "TEXT_NOT_CANONICAL": ErrorCodeInfo(
        "TEXT_NOT_CANONICAL", "Y", "Text does not equal its own CTF-1 output", "§11.2"
    ),
    "TEXT_LENGTH": ErrorCodeInfo(
        "TEXT_LENGTH", "Y", "Text byte length differs from manifest declaration", "§11.2"
    ),
    "TEXT_MISMATCH": ErrorCodeInfo(
        "TEXT_MISMATCH", "Y", "Text Merkle identifier differs from manifest", "§11.2"
    ),
    "ASSET_MISSING": ErrorCodeInfo(
        "ASSET_MISSING", "Y", "Declared asset file does not exist", "§11.2"
    ),
    "ASSET_MISMATCH": ErrorCodeInfo(
        "ASSET_MISMATCH", "Y", "Asset content or length does not match manifest", "§11.2"
    ),
    "ASSET_EXTRA": ErrorCodeInfo(
        "ASSET_EXTRA", "Y", "Unlisted file found in assets directory", "§11.2"
    ),
    "CITE_UNLISTED": ErrorCodeInfo(
        "CITE_UNLISTED", "Y", "Inline citation URI is not listed in manifest", "§11.2"
    ),
    "CITE_LOCATOR_INVALID": ErrorCodeInfo(
        "CITE_LOCATOR_INVALID", "Y", "Citation byte locator is invalid for cited blob", "§11.2"
    ),
    "WORK_MISMATCH": ErrorCodeInfo(
        "WORK_MISMATCH", "Y", "Parent bundle does not share declared work identifier", "§11.2"
    ),
    "SIG_INVALID": ErrorCodeInfo("SIG_INVALID", "Y", "Signature verification failed", "§11.2"),
    "KEY_MISMATCH": ErrorCodeInfo(
        "KEY_MISMATCH", "Y", "Public key does not hash to declared key identifier", "§11.2"
    ),
    "ALG_UNKNOWN": ErrorCodeInfo(
        "ALG_UNKNOWN", "Y", "Signature algorithm is not permitted by pip-1", "§11.2"
    ),
    "BEACON_FAILED": ErrorCodeInfo(
        "BEACON_FAILED", "Y", "Beacon proof verification failed", "§11.2"
    ),
    "ATT_FAILED": ErrorCodeInfo(
        "ATT_FAILED", "Y", "Attestation proof verification failed", "§11.2"
    ),
    # Additional verification codes (specs.md §14)
    "MANIFEST_MISSING": ErrorCodeInfo(
        "MANIFEST_MISSING", "P", "manifest.pip file not found in bundle", "§11.2"
    ),
    "TEXT_MISSING": ErrorCodeInfo(
        "TEXT_MISSING", "P", "Manuscript text file not found in bundle", "§11.2"
    ),
    "ENVELOPE_INVALID": ErrorCodeInfo(
        "ENVELOPE_INVALID", "P", "Signature or attestation envelope failed strict parsing", "§9.4"
    ),
    "UNSAFE_PATH": ErrorCodeInfo(
        "UNSAFE_PATH", "P", "Bundle entry is a symlink or unsafe path", "§11.1"
    ),
    "EXTRA_FILE": ErrorCodeInfo(
        "EXTRA_FILE", "P", "Unrecognized file in bundle directory", "§11.1"
    ),
    "CITE_SYNTAX": ErrorCodeInfo("CITE_SYNTAX", "P", "Citation URI syntax is malformed", "§6.3"),
    "CITE_RANGE": ErrorCodeInfo(
        "CITE_RANGE", "P", "Citation locator falls outside blob bounds or boundaries", "§6.3"
    ),
    "PID_SYNTAX": ErrorCodeInfo(
        "PID_SYNTAX", "P", "Identifier string does not match pip1:<type>:<hex>", "§6.1"
    ),
    # SKIPPED / WARN reasons (specs.md §14)
    "NO_PARENTS": ErrorCodeInfo(
        "NO_PARENTS", "P", "Genesis manifest has no parent bundles", "§11.2"
    ),
    "PARENTS_UNAVAILABLE": ErrorCodeInfo(
        "PARENTS_UNAVAILABLE", "P", "Parent bundles not supplied to verifier", "§11.2"
    ),
    "NO_SIGNATURES": ErrorCodeInfo(
        "NO_SIGNATURES", "P", "Bundle carries no signature envelopes", "§11.2"
    ),
    "NO_TIME_EVIDENCE": ErrorCodeInfo(
        "NO_TIME_EVIDENCE", "P", "Bundle carries neither beacon nor attestations", "§10.4"
    ),
    "BEACON_UNVERIFIED": ErrorCodeInfo(
        "BEACON_UNVERIFIED", "P", "Beacon value is present but unverified", "§10.2"
    ),
    "ATT_UNVERIFIED": ErrorCodeInfo(
        "ATT_UNVERIFIED", "P", "Attestation proof is present but unverified", "§10.3"
    ),
    "DEPENDS_ON_V1": ErrorCodeInfo(
        "DEPENDS_ON_V1", "P", "Check skipped because manifest failed verification", "§11.2"
    ),
    "LIMIT_EXCEEDED": ErrorCodeInfo(
        "LIMIT_EXCEEDED", "P", "Resource limit exceeded during verification", "§12.7"
    ),
    # Tool errors (specs.md §14)
    "KEYFILE_INVALID": ErrorCodeInfo(
        "KEYFILE_INVALID", "P", "Key file is malformed or corrupted", "§13"
    ),
    "KEYFILE_PERMISSIONS": ErrorCodeInfo(
        "KEYFILE_PERMISSIONS", "P", "Key file permissions are wider than 0600", "§13"
    ),
    "KEYFILE_PASSPHRASE": ErrorCodeInfo(
        "KEYFILE_PASSPHRASE", "P", "Incorrect passphrase for encrypted key file", "§13"
    ),
    "BACKEND_ERROR": ErrorCodeInfo("BACKEND_ERROR", "P", "Cryptographic backend error", "§8"),
    "UNICODE_DATA_MISMATCH": ErrorCodeInfo(
        "UNICODE_DATA_MISMATCH", "P", "Unicode library version is not 18.0.0", "§4.4"
    ),
}


class AethelError(Exception):
    """Base exception for all Aethel errors with stable registry codes."""

    def __init__(self, code: str, message: str, **detail: object) -> None:
        """Initialize an AethelError with code, message, and details."""
        if code not in ERROR_CODE_REGISTRY:
            raise ValueError(f"Unknown error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
        self.yp_section = ERROR_CODE_REGISTRY[code].yp_section

    def __repr__(self) -> str:
        """Return developer-facing representation of the error."""
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class CanonicalizationError(AethelError):
    """Raised when CTF-1 canonicalization rejects an input."""


class ManifestError(AethelError):
    """Raised when manifest parsing or serialization fails."""


class CitationError(AethelError):
    """Raised when citation syntax or range verification fails."""


class EnvelopeError(AethelError):
    """Raised when signature or attestation envelope parsing fails."""


class BundleError(AethelError):
    """Raised when reading or writing a bundle fails."""


class KeyFileError(AethelError):
    """Raised when key file parsing, loading, or saving fails."""


class CryptoError(AethelError):
    """Raised when cryptographic operations fail."""


class LimitExceeded(AethelError):  # noqa: N818
    """Raised when a resource limit is exceeded."""


class UsageError(AethelError):
    """Raised when command-line usage is invalid."""


class InternalError(AethelError):
    """Raised when an internal invariance or self-verification fails."""
