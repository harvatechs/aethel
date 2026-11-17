# PIP-1 Conformance and Verification Report

**Reference Implementation**: `aethel-codex` (CLI: `aethel`)  
**Specification**: Permanent Ink Protocol Profile **pip-1** (Yellow Paper PIP-YP-1 v1.0.0-rc.3)  
**Report Date**: 2026-11-17  
**Distribution Version**: `0.1.0`  

---

## 1. Conformance Matrix (YP §14.1)

| Role | Profile Requirements | Status | Proven By |
|---|---|---|---|
| **Canonicalizer** | Canonical Text Form (CTF-1); Unicode 18.0.0 NFC normalization; CRLF/CR to LF; BOM stripping; rejection of 12 negative vectors, unassigned codepoints, C0/C1 controls, and noncharacters. | **CONFORMANT** | `tests/conformance/test_ctf1_vectors.py`, `tests/conformance/test_unicode_edge_corpus.py`, `tests/property/test_ctf1_properties.py`, 100% of Unicode 18.0.0 `NormalizationTest.txt`. |
| **Manifest Producer** | Permanent Manifest Form (PMF-1); byte-sorted fields; duplicate rejection; strict grammar `0|[1-9][0-9]*`; 4,096-byte chunk Merkle tree roots; atomic bundle writing; self-verification prior to release. | **CONFORMANT** | `tests/conformance/test_manifest_vectors.py`, `tests/conformance/test_merkle_vectors.py`, `tests/unit/test_publish.py`, `tests/property/test_merkle_properties.py`. |
| **Signer** | Detached signature envelopes (SGE-1); pure variants with context `pip1.sig`; role byte `0x01` prepended to raw 32-byte manifest digest; hedged signing by default; self-verify before release. | **CONFORMANT** | `tests/conformance/test_crypto_vectors.py`, `tests/unit/test_crypto_coverage.py`, `tests/unit/test_keyfile.py`, `tools/recompute_yp_vectors.py`. |
| **Verifier** | Evaluation of checks V1 through V8; separate reporting of Integrity, Attribution, History, and Time; rejection of all 9 manifest mutation vectors; single-bit tamper detection across all files. | **CONFORMANT** | `tests/conformance/test_fixtures.py`, `tests/unit/test_tamper_matrix.py`, `tests/differential/test_minimal_verifier.py`, `tests/cli/test_cli_contracts.py`. |

---

## 2. Test Execution and Coverage Evidence

- **Total Test Suite**: 239 passed, 1 skipped (symlinks requiring Windows administrative privileges), 0 failed.
- **Coverage By Tier** (`tools/check_coverage.py`):
  - **PT0 (Core Foundations & Normalization)**: 100% branch and statement coverage (`constants.py`, `hashing.py`, `unicode18.py`, `_repertoire.py`, `ctf1.py`, `pid.py`, `citations.py`, `signing.py`, `report.py`, `limits.py`).
  - **PT1 (Parsers, Merkle, Crypto, Verification)**: >= 95% branch coverage (`merkle.py`: 99%, `manifest.py`: 96%, `envelope.py`: 99%, `verify.py`: 97%, `publish.py`: 97%, `bundle.py`: 96%, `keyfile.py`: 100%, `proof.py`: 93%).
  - **Overall Package Coverage**: 91.04% (exceeding the >= 90% threshold).
- **Oracle Verification** (`tools/recompute_yp_vectors.py`):
  - 100% of Yellow Paper test vectors reproduced independently from first principles.
  - Appendix A.2 ML-DSA-87 signature verified under `cryptography` and `pqcrypto`.
  - Negative vectors (wrong context, role `0x02`, revision ID) all strictly rejected.
- **Golden Fixtures Conformance** (`tests/conformance/test_fixtures.py`):
  - `genesis-unsigned`: V1 PASS, V2 PASS, Integrity PASS, Unattributed (0 of 0).
  - `genesis-attributed`: V1 PASS, V2 PASS, V6 PASS, Integrity PASS, Attributed (1 of 1).
  - `dual-family`: V1 PASS, V2 PASS, V6 PASS, Integrity PASS, Dual-family (2 of 2).
  - `partial-attribution`: V1 PASS, V2 PASS, V6 PASS, Integrity PASS, Partially attributed (1 of 2).
  - `revision`: V1 PASS, V2 PASS, V5 PASS, V6 PASS, Integrity PASS (when parents provided).
- **Differential Verification** (`scripts/verify_minimal.py` & `tests/differential/`):
  - Zero-dependency Python standard library verifier agrees 100% with the full package verifier across all 5 golden fixtures and 200 pseudo-randomly mutated bundles (single-bit flips, truncations, additions, deletions, directory renames).
- **Hardening and Scale Budgets**:
  - 1 GiB asset stream verified in 3.29 seconds with bounded memory and $O(\log N)$ stack depth <= 30.
  - ReDoS probe (10 MB repeated citations) completes in < 0.1s.
  - Property and fuzzing targets executed clean across CTF-1, PMF-1, SGE-1, ATT-1, TFP-1, and bundle inputs.
- **Traceability** (`tools/trace.py`):
  - 30 of 30 tracked P0 user requirements traced to explicit passing tests with `@pytest.mark.req(...)`.
- **Reproducible Distribution** (`tools/install_smoke.py`, `tools/determinism_check.py`):
  - Two independent builds produce byte-for-byte identical wheels (`SHA256: b2c43fe73ba94ea16fa8aa5d73525da81cb70c024882a583df6229aef8b7c9c7`).
  - Clean virtual environment installation verified with offline `aethel selftest` and `aethel verify`.
  - CycloneDX 1.6 SBOM generated reproducibly.

---

## 3. What Remains Unproven (Yellow Paper Open Items §14.3)

In accordance with PIP-1 transparency requirements, the following items remain unproven and out of scope for v0.1.0:

1. **Independent Non-Python Implementations (Open Item 14.3.1)**:
   While `scripts/verify_minimal.py` provides an independent, stdlib-only second implementation, no non-Python implementation (e.g. Rust, Go, or TypeScript browser verifier) has been tested for cross-implementation differential conformance.
2. **Independent Cryptographic Audit (Open Item 14.3.2)**:
   This codebase and the Permanent Ink Protocol specification have **not yet undergone formal third-party security or cryptographic review**.
3. **NIST CAVP Validation (Open Item 14.3.3)**:
   While the cryptographic primitives rely on standard libraries (`cryptography` for ML-DSA, `pqcrypto` for SLH-DSA), formal NIST Cryptographic Algorithm Validation Program (CAVP) certificate testing has not been run against the bundled binaries.
4. **Registered Randomness Beacons (Open Item 14.3.4)**:
   No public randomness beacon sources (such as `nist-beacon` or `drand`) are currently registered in profile `pip-1`. Beacon lines are carried and reported as "present, unchecked".
5. **Standardized External Attestation Procedures (Open Item 14.3.5)**:
   Procedures for RFC 3161 timestamps or OpenTimestamps proofs are not defined in `pip-1`. All external attestations are reported as "present and unverified".
6. **Yellow Paper Final Status (Open Item 14.3.6)**:
   This implementation targets Yellow Paper release candidate **v1.0.0-rc.3**. Any byte changes between rc.3 and final v1.0.0 will require a corresponding minor release.
