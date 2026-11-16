"""Test error code registry and exception types (R-CODE-04, PT0)."""

import pytest

from aethel_codex.errors import (
    ERROR_CODE_REGISTRY,
    AethelError,
    BundleError,
    CanonicalizationError,
    CitationError,
    CryptoError,
    EnvelopeError,
    InternalError,
    KeyFileError,
    LimitExceeded,
    ManifestError,
    UsageError,
)


def test_registry_contains_all_spec_codes() -> None:
    expected_codes = {
        # CTF-1 rejections
        "E_INVALID_UTF8",
        "E_FORBIDDEN_CODEPOINT",
        "E_UNASSIGNED_CODEPOINT",
        "E_EMPTY_TEXT",
        # Manifest rejections
        "E_FIELD_ORDER",
        "E_BAD_LINES",
        "E_UNKNOWN_PROFILE",
        "E_NOT_SORTED_OR_UNIQUE",
        "E_BAD_VALUE",
        "E_INTEGER_RANGE",
        "E_BAD_MAGIC",
        "E_UNKNOWN_KEY",
        "E_MISSING_FIELD",
        "E_WORK_PARENT_RULE",
        "E_ROUNDTRIP",
        # Verification codes
        "MANIFEST_INVALID",
        "ID_MISMATCH",
        "TEXT_NOT_CANONICAL",
        "TEXT_LENGTH",
        "TEXT_MISMATCH",
        "ASSET_MISSING",
        "ASSET_MISMATCH",
        "ASSET_EXTRA",
        "CITE_UNLISTED",
        "CITE_LOCATOR_INVALID",
        "WORK_MISMATCH",
        "SIG_INVALID",
        "KEY_MISMATCH",
        "ALG_UNKNOWN",
        "BEACON_FAILED",
        "ATT_FAILED",
        # Additional codes
        "MANIFEST_MISSING",
        "TEXT_MISSING",
        "ENVELOPE_INVALID",
        "UNSAFE_PATH",
        "EXTRA_FILE",
        "CITE_SYNTAX",
        "CITE_RANGE",
        "PID_SYNTAX",
        # SKIPPED / WARN reasons
        "NO_PARENTS",
        "PARENTS_UNAVAILABLE",
        "NO_SIGNATURES",
        "NO_TIME_EVIDENCE",
        "BEACON_UNVERIFIED",
        "ATT_UNVERIFIED",
        "DEPENDS_ON_V1",
        "LIMIT_EXCEEDED",
        # Tool errors
        "KEYFILE_INVALID",
        "KEYFILE_PERMISSIONS",
        "KEYFILE_PASSPHRASE",
        "BACKEND_ERROR",
        "UNICODE_DATA_MISMATCH",
    }

    assert expected_codes.issubset(set(ERROR_CODE_REGISTRY.keys()))


def test_exception_properties_and_subclasses() -> None:
    err = CanonicalizationError("E_INVALID_UTF8", "Invalid byte", offset=4)
    assert err.code == "E_INVALID_UTF8"
    assert err.message == "Invalid byte"
    assert err.detail == {"offset": 4}
    assert err.yp_section == "§4.2"
    assert repr(err) == "CanonicalizationError(code='E_INVALID_UTF8', message='Invalid byte')"
    assert isinstance(err, AethelError)

    # Test each specific subclass
    assert isinstance(ManifestError("E_BAD_LINES", "Bad"), AethelError)
    assert isinstance(CitationError("CITE_SYNTAX", "Bad"), AethelError)
    assert isinstance(EnvelopeError("ENVELOPE_INVALID", "Bad"), AethelError)
    assert isinstance(BundleError("MANIFEST_MISSING", "Bad"), AethelError)
    assert isinstance(KeyFileError("KEYFILE_INVALID", "Bad"), AethelError)
    assert isinstance(CryptoError("BACKEND_ERROR", "Bad"), AethelError)
    assert isinstance(LimitExceeded("LIMIT_EXCEEDED", "Bad"), AethelError)
    assert isinstance(UsageError("E_BAD_VALUE", "Bad"), AethelError)
    assert isinstance(InternalError("E_ROUNDTRIP", "Bad"), AethelError)


def test_unknown_code_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown error code"):
        AethelError("NOT_A_REAL_CODE", "Something")
