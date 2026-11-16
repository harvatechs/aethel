# analysis.md — Step 0 Analysis & Environment Audit

## 1. Mission and The Twelve Non-Negotiables

### The Mission
`aethel` is the shippable reference CLI and Python library (`aethel-codex` / `aethel_codex`) for the Permanent Ink Protocol, profile `pip-1` (Yellow Paper PIP-YP-1 v1.0.0-rc.3). Its purpose is to provide verifiable, permanent, content-addressed identity, post-quantum signatures (ML-DSA / SLH-DSA), strict provenance manifests, and offline verification for written human works. Correctness against the Yellow Paper outranks speed, elegance, and features.

### The Twelve Non-Negotiables (In Own Words)
1. **Yellow Paper Is Supreme:** The Yellow Paper PDF and immutable test vectors in `tests/vectors/` are absolute ground truth. If code fails a vector, the code is wrong.
2. **Binary Fidelity (Bytes In, Bytes Out):** File I/O is strictly binary (`"rb"`/`"wb"`). Implicit text decodings, locale-dependent line-ending conversions, and lossy error handlers (`errors="replace"`) are forbidden.
3. **Unicode 18.0.0 Exclusivity:** Character normalization and classification rely strictly on `unicodedata2==18.0.0`. Python's standard `unicodedata` library is strictly banned from `src/`.
4. **FIPS 202 SHA3-256 with Domain Separation:** SHA3-256 is FIPS 202 (never Keccak). Every hash operation strictly applies length-prefixed domain labels: `H(label, x) = SHA3-256(u8(len(label)) ‖ label ‖ x)`.
5. **Strict Parsing without Forgiveness:** Manifests, envelopes, citations, and keys follow single strict grammars. No leniency, no auto-repair, no guessing, and no trailing whitespace tolerance.
6. **Zero Context Leakage:** Manifests, texts, and envelopes contain zero ambient metadata: no timestamps, no hostnames, no usernames, no paths, and no tool versions beyond normative schema fields.
7. **Complete Offline Operation:** The library and CLI perform zero network I/O. Verification operates purely from local files.
8. **Honest, Unbundled Verdicts:** Verification presents integrity, attribution, history, and temporal status as independent statements. It never combines them into a blanket "valid", and never promises properties outside YP §2.3.
9. **Zero Placeholders:** Shipped paths contain no `TODO`, `pass`, `NotImplementedError`, mock crypto, or dummy data. Unfinished features are never exposed.
10. **Standard Cryptographic Primitives:** No custom implementations of ML-DSA, SLH-DSA, or Unicode algorithms. Production dependencies are strictly `cryptography`, `pqcrypto`, and `unicodedata2`.
11. **Self-Verification Before Release:** Every signature generated must be verified by the signer before being emitted to disk or stdout; if self-verification fails, fail closed.
12. **Evidence-Based Acceptance:** Every claim requires verifiable command execution output. After three failed attempts at a problem, stop and report immediately (three-strikes rule).

---

## 2. Requirement Traceability Matrix (P0 Requirements)

| Requirement | Summary | Work Package(s) | Test Name(s) | Verification Gate |
|---|---|---|---|---|
| **UR-01** | `canon` outputs CTF-1 bytes; `--check`, `--report`, `-o` | WP-02, WP-10 | `test_ctf1_vectors`, `test_canon_cli` | WP-02, WP-10 gates |
| **UR-02** | `id` computes `pip1:t:` and `pip1:a:` identifiers | WP-03, WP-10 | `test_merkle_blob_ids`, `test_id_cli` | WP-03, WP-10 gates |
| **UR-03** | Rejections provide exact byte/codepoint, line, col, and YP cite | WP-02, WP-10 | `test_ctf1_diagnostics`, `test_canon_reject_messages` | WP-02, WP-10 gates |
| **UR-04** | `canon` and `id` accept `-` for stdin | WP-02, WP-03, WP-10 | `test_canon_stdin`, `test_id_stdin` | WP-10 gate |
| **UR-05** | `keygen` creates encrypted keys (ML-DSA-87/65, SLH-DSA); no overwrite | WP-08, WP-10 | `test_keyfile_akf1_roundtrip`, `test_keygen_cli` | WP-08, WP-10 gates |
| **UR-06** | `key info` exposes algorithm and key id, never secrets | WP-08, WP-10 | `test_key_info_secrets_absent`, `test_key_info_cli` | WP-08, WP-10 gates |
| **UR-08** | `publish` builds complete genesis bundle | WP-09, WP-10 | `test_publish_genesis`, `test_publish_cli` | WP-09, WP-10 gates |
| **UR-09** | `publish` signs >=1 key, self-verifies, atomic write, full verify | WP-09, WP-10 | `test_publish_atomic_and_verify`, `test_publish_self_verify_fail` | WP-09, WP-10 gates |
| **UR-10** | `publish --dry-run` calculates IDs without touching disk | WP-09, WP-10 | `test_publish_dry_run` | WP-09, WP-10 gates |
| **UR-11** | Byte-identical manifest generation across OS and Python | WP-09, WP-10, WP-15 | `test_manifest_determinism`, `tools/determinism_check.py` | WP-09, WP-15 gates |
| **UR-12** | Refusal of unsafe/ambiguous asset names and collisions | WP-09, WP-10 | `test_publish_refuse_bad_assets`, `test_asset_case_collision` | WP-09, WP-10 gates |
| **UR-15** | `sign` adds signature; checks integrity; warns on undeclared | WP-06, WP-07, WP-10 | `test_sign_manifest`, `test_sign_cli` | WP-06, WP-07, WP-10 gates |
| **UR-17** | `verify` executes V1–V8 and emits four distinct statements | WP-07, WP-10 | `test_verify_bundle_checks`, `test_verify_cli` | WP-07, WP-10 gates |
| **UR-18** | `verify --json` matches JSON schema; JSONL on multi-bundle | WP-07, WP-10 | `test_verify_json_schema`, `test_verify_jsonl` | WP-07, WP-10 gates |
| **UR-19** | Verification gates (`--require-*`) affect exit codes only | WP-07, WP-10 | `test_verify_gate_flags_exit_code` | WP-07, WP-10 gates |
| **UR-20** | Verification is completely offline and self-contained | WP-07, WP-10, WP-14 | `test_verify_offline`, `test_security_no_network` | WP-07, WP-14 gates |
| **UR-21** | Single-bit alteration detection in all components | WP-07, WP-10 | `test_tamper_matrix` | WP-07 gate |
| **UR-22** | Exceeded limits produce `INCONCLUSIVE` (exit 6) | WP-07, WP-10 | `test_verify_resource_limits` | WP-07, WP-10 gates |
| **UR-23** | `inspect` displays manifest content without verification disclaimer | WP-10 | `test_inspect_cli` | WP-10 gate |
| **UR-24** | `explain CODE` documents all registered error codes | WP-11 | `test_explain_completeness` | WP-11 gate |
| **UR-25** | `selftest` executes test vectors offline from installed wheel | WP-11, WP-15 | `test_selftest_offline`, `test_install_smoke` | WP-11, WP-15 gates |
| **UR-26** | `version` reports tool, paper, Unicode, and backend versions | WP-11 | `test_version_schema_and_cli` | WP-11 gate |
| **UR-30** | Pure-wheel non-compiler installation on Linux/macOS/Windows | WP-15 | `tools/install_smoke.py` | WP-15 gate |
| **UR-31** | No network, telemetry, clocks, or persistence outside bundle | WP-14 | `test_security_no_network_or_clocks` | WP-14 gate |
| **UR-32** | Documented public Python library API | WP-16, WP-17 | `test_public_api_doc_contracts` | WP-16, WP-17 gates |
| **UR-35** | README five-minute tutorial and honest claims boundaries | WP-16 | `test_readme_execution`, `test_banned_claims` | WP-16 gate |
| **UR-36** | `verify-by-hand.md` and stdlib `verify_minimal.py` | WP-13, WP-16 | `test_differential_minimal_verifier` | WP-13, WP-16 gates |
| **UR-37** | Worked CLI examples in all command `--help` outputs | WP-10 | `test_cli_help_examples` | WP-10 gate |
| **UR-39** | Secret protection (0600/wipe) & terminal escape sanitization | WP-08, WP-10, WP-14 | `test_security_secrets`, `test_terminal_sanitization` | WP-08, WP-14 gates |
| **UR-40** | Audit clean of all banned marketing/cryptographic claims | WP-10, WP-16 | `test_banned_claims_audit` | WP-10, WP-16 gates |

---

## 3. Ten Biggest Risks and Mitigations

1. **OS Line-Ending & Encoding Corruption on Disk (Windows/macOS/Linux):** Text-mode I/O converts `\n` to `\r\n` or applies Windows cp1252 encoding, invalidating cryptographic hashes. *Mitigation:* Strict binary file I/O (`"rb"`/`"wb"`), Ruff AST linting banning unflagged `open()`, and `.gitattributes` marking `tests/**`, `*.pip`, `*.sig`, `*.att`, `*.aek` as `-text`.
2. **Unicode Normalization Drift & Stdlib Mismatch:** Standard library `unicodedata` uses Unicode 15.0.0; PIP-1 mandates 18.0.0. *Mitigation:* Runtime assertion on `unicodedata2.unidata_version == "18.0.0"`, complete check against Unicode 18.0.0 `NormalizationTest.txt`, and automated drift canary verification against vector hashes.
3. **Malleable and Non-Canonical Parser Permissiveness:** Lenient parsers, whitespace stripping (`.strip()`), non-ASCII digits (`\d`), or accepting non-canonical Base64 padding allow signature malleability and parser differentials. *Mitigation:* Hand-written strict linear parsers using `[0-9]`, strict regex `re.fullmatch`, exact byte re-serialization comparison (`E_ROUNDTRIP`), and canonical Base64 round-trip verification.
4. **Backend Cryptographic Exception Blur in `pqcrypto`:** In `pqcrypto`, `InvalidSignatureError` subclasses `ValueError`. Catching `ValueError` blurs malformed input length with invalid signature content. *Mitigation:* Enforce explicit length checks before dispatching to `pqcrypto.verify`, catch only `pqcrypto.InvalidSignatureError`, and pass raw `bytes`.
5. **Signed Message Semantic Divergence:** Signing hex strings, pre-hashed digests, or omitting role prefixes or context strings. *Mitigation:* Centralize message assembly in `signing.py` (`M = u8(role) ‖ raw_32_byte_digest`), pin context `pip1.sig`, and assert against Yellow Paper A.2 test vector.
6. **Key File Insecurity and Memory Secret Leakage:** Accidental leakage of private seeds via command-line arguments, process environments, logs, `repr()`, or world-readable files. *Mitigation:* Scrypt + ChaCha20-Poly1305 encryption by default, passphrase input only via TTY prompt or `--passphrase-file`, file creation with `O_EXCL` and mode `0600`, and `bytearray` zeroing on release.
7. **Directory Traversal & Symlink Attacks from Hostile Bundles:** Untrusted bundle directories containing symlinks, absolute paths, or path traversal elements (`../`). *Mitigation:* Mandatory `lstat` inspection of all bundle entries, symlink rejection, regex validation of asset filenames before path construction, and atomic bundle writes.
8. **Overclaiming Cryptographic Properties in User-Facing Surface:** Stating that a signature "proves authorship" or that the bundle is "immutable/quantum-proof" misleads users and fails R-HON-01. *Mitigation:* Automated test grep sweeping all help text, error messages, docs, and code against the banned claim blacklist in `what-not-to-do.md` §4.
9. **Accidental Network I/O or Dependency Creep:** Sneaking in network calls, update checks, or compiling dependencies on user machines. *Mitigation:* Strict dependency ceiling (`cryptography`, `pqcrypto`, `unicodedata2`), test fixture monkeypatching `socket.connect`, and AST import scanning.
10. **ReDoS and Algorithmic Resource Exhaustion:** Hostile inputs causing catastrophic regex backtracking or memory exhaustion. *Mitigation:* Strictly linear regex expressions, chunked 1 MiB stream processing via `TreeHasher`, `MAX_TEXT_BYTES` (64 MiB) enforcement prior to CTF-1 decoding, and directory entry limits.

---

## 4. Contradictions, Ambiguities, and Discrepancies Found

The specifications in `specs.md` and `decision-log.md` systematically address 17 ambiguities (`[PACK]` Q-01 through Q-17). The primary findings are:
1. **Citation Syntax vs Range Error (YP §6.3 vs Appendix A.5 / Q-02):** YP §6.3 categorizes `start >= end` as a range error, whereas Appendix A.5 classifies `#b=3-3` and `#b=5-3` as syntax errors (`CITE_SYNTAX`). *Resolution:* Reject both at parse time with `CITE_SYNTAX`.
2. **Repertoire Precedence on Noncharacters (YP §4.2 step 3 / Q-01):** U+FDD0 is both in the forbidden range and in category `Cn`. *Resolution:* Evaluate forbidden codepoints over the entire text before checking unassigned scalars; U+FDD0 yields `E_FORBIDDEN_CODEPOINT` (matching vector).
3. **Manifest Grammar Token vs Value Rules (YP §7.3 vs ABNF / Q-14, Q-15):** The ABNF for `text` allows integer 0, while prose demands length >= 1; `bval` ABNF does not enforce even hex length, while prose requires hex bytes. *Resolution:* Prose takes precedence; enforce text length >= 1 and even-length beacon hex strings.
4. **Attribution Algorithm Key Discovery (YP §9.5 / Q-16):** Key identifiers (`pip1:k:...`) do not disclose the underlying algorithm, but Dual-family attribution requires distinguishing ML-DSA and SLH-DSA keys. *Resolution:* Extract key algorithm from the verified envelope that authenticated the key.
5. **Website Discrepancies (decision-log.md Part 4 / OD-8):** The project website (`aethel-codex.pages.dev`) footer specifies rc.1 while the Yellow Paper is rc.3; hero and manifesto duplicate prefixes (`pip1:t:pip1:t:...`). *Resolution:* Documented in OD-8; tool adheres strictly to rc.3.

No unaddressed contradictions or unrecorded ambiguities were found.

---

## 5. Environment Audit Findings

1. **Operating System:** Windows 11 (win32, x86_64).
2. **Tooling & Runtimes:**
   - `python.exe`: **Python 3.11.15** (satisfies `>= 3.11`).
   - `uv.exe`: **uv 0.11.33** (x86_64-pc-windows-msvc).
   - `sha256sum`: Located at `E:\Git\usr\bin\sha256sum.exe`.
3. **Oracle Vector & Fixture Checksums:**
   - `sha256sum -c tests/vectors/SHA256SUMS`: **ALL 2 CHECKSUMS OK**.
   - `sha256sum -c tests/fixtures/SHA256SUMS`: **ALL 24 CHECKSUMS OK**.
4. **Audit Virtual Environment (`$env:TEMP\audit`):**
   - Installed `unicodedata2==18.0.0`, `cryptography==50.0.2`, `pqcrypto==1.0.0`, `dilithium-py==1.5.1`. All packages resolved and installed cleanly with prebuilt wheels.
5. **Vector Recomputation:**
   - Ran `tools/recompute_yp_vectors.py`. Output verified: **ALL VECTORS REPRODUCED**.
6. **Platform-Specific Considerations:**
   - POSIX file mode 0600 checks for keyfiles will report an advisory on Windows (as specified in ADR-011 and `architecture.md` §11).
   - `.gitattributes` `-text` rule prevents CRLF corruption on git operations on Windows.

---

## 6. Critical Path & First Three Work Packages

### Critical Path
```
WP-00 (Bootstrap) ──► WP-01 (Foundations) ──► WP-02 (Unicode + CTF-1)
  ──► WP-04 (Manifest) ──► WP-07 (Bundles + Verify) ──► WP-09 (Publish + Revise)
  ──► WP-10 (CLI P0) ──► WP-15 (Packaging + CI) ──► WP-17 (Acceptance)
```
*(Parallel Tracks: WP-03 Merkle, WP-05 Citations, WP-06 Crypto, WP-08 Keyfiles feed into WP-07 and WP-09).*

### First Three Work Packages
1. **WP-00 Bootstrap (Size S):**
   - Set up `pyproject.toml`, `Makefile`, git repository, `.gitattributes`, Ruff, Mypy, pytest configuration, import-linter contracts, `tools/check_coverage.py`, `tools/trace.py`, and base directory structure (`src/aethel_codex`).
   - *Gate:* `make check` passes, vector checksum verification passes, editable install clean.
2. **WP-01 Foundations (Size S):**
   - Implement `constants.py`, `errors.py` (complete error code registry), and `hashing.py` (`H(label, x)` and `lp(label)`).
   - *Gate:* Label lengths match `pip1-vectors.json`, domain separation property test green, all error codes registered.
3. **WP-02 Unicode + CTF-1 (Size M):**
   - Implement `unicode18.py`, generated `_repertoire.py`, `ctf1.py`, `tools/gen_repertoire.py`, and `tools/fetch_unicode_tests.py`.
   - *Gate:* T1, T2, and 12 negative vectors pass; 20,000-input fixed-point property passes; `unicodedata2` 18.0.0 version guard verified; repertoire table canary digest matches vector file.
