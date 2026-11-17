# Changelog

All notable changes to `aethel` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Tool Version to Yellow Paper Profile Mapping

| Tool Version | Yellow Paper Version | Profile | Status |
|---|---|---|---|
| 0.1.0 | 1.0.0-rc.3 | `pip-1` | Release Candidate 1 |

## [0.1.0] - 2026-11-17

### Added
- **Core Foundations (WP-01)**: FIPS 202 SHA3-256 hashing with 1-byte length-prefixed domain labels, typed exception hierarchy, and error code registry covering all Yellow Paper §14.2 error codes.
- **Canonical Text Form (CTF-1) (WP-02)**: Strict Unicode 18.0.0 normalization (NFC), CRLF/CR to LF line endings, BOM stripping, and rejection of 12 negative vectors, unassigned codepoints, and C0/C1 control codes.
- **Merkle Trees and Identifiers (WP-03)**: 4,096-byte chunk Merkle trees, streaming $O(\log N)$ `TreeHasher`, RFC 6962 split rule, text PIDs (`pip1:t:...`), asset PIDs (`pip1:a:...`), and chunk audit paths.
- **Permanent Manifest Form (PMF-1) (WP-04)**: Strict canonical manifest parser and serializer with byte-sorted fields, integer range validation, duplicate rejection, and mutation rejection.
- **Citation Locators (WP-05)**: Canonical citation URI parser, locator table validation, and linear-time ReDoS-guarded inline citation scanner.
- **Post-Quantum Cryptography (WP-06)**: ML-DSA-87, ML-DSA-65 (FIPS 204), and SLH-DSA-SHA2-256s, SLH-DSA-SHAKE-256s (FIPS 205) signature suites with context `pip1.sig`, role byte `0x01`, and hedged signing.
- **Verification Engine (WP-07)**: Checks V1 through V8 evaluated independently, separate reporting of Integrity, Attribution, History, and Time, 5 golden bundle fixtures, and single-bit tamper detection.
- **AKF-1 Key Management (WP-08)**: Encrypted (Argon2id + AES-256-GCM) and plain AKF-1 keyfiles, secure random salt/nonce generation, POSIX 0600 permission checks, and zero leakage of secrets in output or memory reprs.
- **Publishing and Revision (WP-09)**: Atomic bundle packaging, `--dry-run` preview, pre-release self-verification, and parent edition revision tracking.
- **Command-Line Interface (WP-10, WP-11, WP-12)**:
  - `aethel canon`: Canonicalize or check text against CTF-1.
  - `aethel id`: Compute content-addressed identifiers.
  - `aethel keygen`: Generate post-quantum signing keys.
  - `aethel publish`: Package and self-verify PIP-1 bundles.
  - `aethel sign`: Attach detached signature envelopes (SGE-1).
  - `aethel verify`: Verify bundles across V1–V8 with human or JSON output.
  - `aethel inspect`: Fast metadata inspection without crypto verification.
  - `aethel selftest`: Run 13 built-in offline conformance checks.
  - `aethel explain`: Diagnostic explanations and remediations for all error codes.
  - `aethel version`: Tool, Unicode, and backend version reporting.
  - `aethel revise`: Publish revisions linked to genesis parents.
  - `aethel cite`: Make, check, and display canonical citations.
  - `aethel proof`: Generate and verify chunk Merkle audit paths (TFP-1).
  - `aethel attest`: Attach external attestation envelopes (ATT-1).
  - Global flags `--json`, `--ascii`, `-v`, `--no-color` (and `NO_COLOR` env support).
- **Standalone Minimal Verifier (WP-13)**: Zero-dependency Python standard library verifier (`scripts/verify_minimal.py`) differentials checked across all fixtures and 200 random mutations.
- **Security & Hardening (WP-14)**: AST scan enforcing zero banned network/subprocess imports in library, DoS safety limits (`max_manifest_bytes`, `max_text_bytes`, `max_asset_bytes`, `max_dir_entries`), 1 GiB streaming test, and terminal control character sanitization.
- **Packaging & CI Matrix (WP-15)**: Pure-Python wheel build, automated wheel archive contents validator, clean virtual environment install smoke test, reproducible build comparison, CycloneDX 1.6 SBOM, `pip-audit` CVE audit, and multi-OS CI matrix (Linux, macOS, Windows on Python 3.11–3.14).
- **Documentation & User Guidance (WP-16)**: Comprehensive README with 5-minute tutorial, step-by-step tutorial guide, manual verification guide from first principles, UNIX man page, library examples, and automated banned-claims audit.
- **Acceptance & Conformance Report (WP-17)**: Conformance report mapping all roles and Yellow Paper open items.
