# testing-and-conformance.md — Proving It Works

A conformance claim in PIP-1 means: reproduce every positive value exactly and reject every negative input [YP §14.2]. This document turns that sentence, and the rules in `rules.md`, into a test plan with gates.

## 1. Layers

| Layer | Directory | Purpose | Runs in |
|---|---|---|---|
| Unit | `tests/unit/` | One function or class; reject paths as many as accept paths | `make test` |
| Conformance | `tests/conformance/` | Yellow Paper vectors, fixtures, `NormalizationTest.txt` | `make conformance` (marker `conformance`) |
| Property | `tests/property/` | Invariants over generated inputs (Hypothesis) | `make test` (200 examples), `make fuzz` (5,000) |
| Differential | `tests/differential/` | Package vs `scripts/verify_minimal.py`; backends vs oracles | CI |
| CLI contract | `tests/cli/` | Subprocess runs: exit codes, JSON schemas, golden text | `make test` |
| Security | `tests/security/` | Secrets, network, symlinks, terminal injection, DoS | `make test` |
| Slow | `tests/slow/` | Throughput, memory, 1 GiB streaming | nightly (marker `slow`) |

Markers: `conformance`, `oracle` (needs `dilithium-py`/`slh-dsa`), `slow`, `fuzz`, `req("UR-…")`. `--strict-markers` is on. Test data is read from `tests/vectors/` and `tests/fixtures/`, which are read-only (R-PROTO-02).

## 2. Conformance suite (what each vector section drives)

| Data | Test must |
|---|---|
| `constants.labels` | Each label's `lp_hex` equals `lp(label)`; `SIG_CONTEXT` bytes equal; alg ids, roles, sizes equal the code's tables |
| `ctf1.T1`, `T2`, `T3` | Canonicalise input, compare `output_hex`, compare ids, verify `canonicalize(output) == output`; T3 leaves, node, root, audit paths, chunk lengths |
| `ctf1.negative` (12) | Reject with the exact code |
| `assets` | Empty asset id; `figure1.svg` bytes and id |
| `manifests.genesis`, `revision` | Parse; re-serialise identically; ids; genesis is 434 bytes |
| `manifests.negative_mutations` (9) | Reject with the code, except the last (accepted by the parser, fails V2) |
| `signature_ml_dsa_87` | Public key length and key id; `M` and `M'` bytes; **verify** `signature_hex` through the production backend; reject wrong context, role `02`, revision id; with `oracle`, re-derive the signature deterministically and compare the digest |
| `pack_generated.ml_dsa_65`, `pip1-slh-dsa-vectors.json` | Verify; each `must_fail_when` case rejects |
| `locators` | Every range result; every syntax error string |
| `asset_names`, `grammar_cases_derived_from_abnf` | Accept and reject lists |
| `attribution` | Seven rows through the attribution function with synthetic envelopes |
| `pack_generated.blob_sizes` | Asset id for each recipe length |
| `unicode_drift_canary` | Repertoire table digest, count and range count equal |
| `informative_site_vectors` | Reproduce (informative; failure is a Spec Query, not a vector edit) |

Separately, `tools/fetch_unicode_tests.py` downloads the Unicode 18.0.0 `NormalizationTest.txt` once into `tests/data/unicode-18.0.0/` and records its SHA-256 in `tests/data/SHA256SUMS`; the conformance test checks NFC (column 2 for columns 1–3, column 4 for columns 4–5, per the file's header) for every line, plus the repertoire sweep. Network access happens only in that dev tool, never in tests.

## 3. Fixtures (`tests/fixtures/<scenario>/<manifest-id>/` with `expected.json`)

`genesis-attributed`, `genesis-unsigned`, `revision` (also run with `--parents` set to the genesis bundle), `dual-family`, `partial-attribution`. For each, the test runs `verify_bundle` and the CLI and compares integrity, attribution class, signed/declared counts, the Keccak-independent flag, and each check's status and reason with `expected.json`. Their meaning is explained in `tests/README.md`.

## 4. Property tests

Hypothesis, `deadline=None`, seed printed on failure, `derandomize=True` in CI.

1. CTF-1 **fixed point**, no CR, NFC, final LF, no forbidden or unassigned scalar.
2. CTF-1 equivalence: BOM present/absent, LF/CRLF/CR line endings and NFC/NFD forms of one text give identical output.
3. Streaming `TreeHasher` equals recursive `merkle_root` for random leaf counts 1–300 and random feed slicing.
4. Proofs: valid proofs verify for every index; any altered chunk, path element, index or length is rejected.
5. Domain separation: for distinct labels, `H(L1, x) != H(L2, y)`; `lp` is prefix-free.
6. Manifest: builder → serialize → parse → serialize is the identity; **acceptance implies canonical bytes** (mutate one byte of a valid manifest: reject, or accept and re-serialise to exactly the mutated bytes).
7. PIDs: round trip; upper-case and wrong-type rejection.
8. Locators: on random UTF-8 text, a range is accepted iff both ends sit on character boundaries (and `end <= length`, `start < end`).
9. Attribution: compare the production function to a six-line set-based model written independently in the test.
10. Envelopes round trip; strict Base64 rejects non-canonical forms.
11. Key files round trip, plain and encrypted; any single-byte change to an encrypted file is rejected.

## 5. Differential and oracle tests

- **Package vs `scripts/verify_minimal.py`** on all fixtures and 200 randomly tampered bundles (V1–V3 verdicts must agree).
- **Backends vs oracles** (`oracle` marker): ML-DSA-87/65 signatures by `dilithium-py` verify in the production backend and the reverse; SLH-DSA signatures by `slh-dsa` verify in the production backend and the reverse; contexts, roles and tampering are rejected by all.
- **If the owner supplies the paper's reference implementation** under `reference/` (read-only), compare outputs on a random corpus. Never copy its code: independence is the point.

## 6. Tamper matrix

For every fixture, every file, and bit positions {first byte, last byte, middle, 10 random}: flip one bit, run `verify`, assert:

| File changed | Expected |
|---|---|
| `manifest.pip` | V1 FAIL (`ID_MISMATCH`, or `MANIFEST_INVALID` if it no longer parses); V6 FAIL for each envelope (`manifest_mismatch`); integrity **FAIL** |
| `text.*` | V2 FAIL (`TEXT_NOT_CANONICAL`, `TEXT_LENGTH` or `TEXT_MISMATCH`); integrity **FAIL** |
| `assets/*` | V3 FAIL `ASSET_MISMATCH`; integrity **FAIL** |
| `signatures/*.sig` | Integrity **PASS**; V6 FAIL (`SIG_INVALID`, `KEY_MISMATCH` or `ENVELOPE_INVALID`); that signature no longer counts toward attribution |

Structural mutations: delete `manifest.pip` (`MANIFEST_MISSING`, dependants `SKIPPED:DEPENDS_ON_V1`); delete `text.*` (`TEXT_MISSING`); delete an asset (`ASSET_MISSING`); add a file to `assets/` (V3 WARN `ASSET_EXTRA`, integrity PASS); add an unrelated file to `signatures/` (`EXTRA_FILE` warning); rename the directory to another 64-hex name (`ID_MISMATCH`); rename it to a non-hex name (note only); replace a file with a symlink (`UNSAFE_PATH`); swap an envelope in from another bundle (`SIG_INVALID`); change an envelope's `role`, `alg` or `manifest` line (`SIG_INVALID`/`KEY_MISMATCH`); exceed a limit (`SKIPPED:LIMIT_EXCEEDED`, integrity `INCONCLUSIVE`, exit 6).

**The invariant:** a single-bit change to a hashed object is *always* detected (R-PROTO-12, FC4). A pass here is evidence; a miss is a stop-the-line event.

## 7. Security tests (`tests/security/`)

- **No network:** a fixture replaces `socket.socket.connect` and `getaddrinfo` with failures for the whole session; an AST scan fails the build if `src/` imports `socket`, `urllib`, `http`, `ssl`, `requests` or `subprocess`.
- **Secrets:** run keygen, publish and sign with a known passphrase and secret; search stdout, stderr, argv, files, `repr`s, JSON and tracebacks (with `--debug`) for the secret and passphrase bytes in hex, Base64 and raw forms.
- **Files:** key file mode `0600`; refusal at `0644`; `O_EXCL`; refusing to overwrite.
- **Paths:** `..`, absolute names, backslashes, NUL, very long names in asset lines and directory entries; symlink to outside; symlink loops.
- **Terminal injection:** titles and asset names with ESC, CSI, OSC 8, bidirectional controls, tag characters render escaped in human output.
- **Resource attacks:** manifest of 1 MiB of valid lines; 10 MB of repeated `cite:pip1:t:` (ReDoS guard: finishes within 2 s); huge claimed lengths; 100,000 directory entries.
- **Fail closed:** a faulty backend whose `verify` returns `True` for everything is caught by the self-verification wrapper test using the known-bad A.2 variants.

## 8. CLI contract tests (`tests/cli/`)

Subprocess runs of `python -m aethel_codex`. Check: every exit code in `cli-spec.md` §2; `--json` stdout is one valid document and validates against its schema; JSON Lines for several bundles; golden text for `--ascii --no-color` (the golden files live in `tests/cli/golden/` and are produced by the implementation once, reviewed by a human, then frozen); `NO_COLOR` and non-TTY behaviour; stdin handling; `--passphrase-file`; messages contain the code and Yellow Paper section; `aethel --version` imports neither `cryptography` nor `pqcrypto` (inspect `sys.modules` in the child).

## 9. Cross-platform and determinism

- `.gitattributes` marks `tests/vectors/**`, `tests/fixtures/**`, `*.pip`, `*.sig`, `*.att` as `-text` so Windows checkouts never rewrite line endings (this has silently broken hash tests in many projects).
- A CI job runs `aethel publish --dry-run` on the T2 input (BOM, CRLF, lone CR, decomposed é) on Linux, macOS and Windows with every Python version and requires `pip1:t:9e13e0cc…e8f413`. Another publishes a fixed manuscript unsigned and requires one manifest id everywhere.
- Case-insensitive filesystems: two assets differing only in case are refused at publish.

## 10. Performance (nightly, `slow`)

Tree hashing of 256 MiB ≥ 100 MiB/s; 1 GiB streamed with peak memory ≤ 64 MiB above baseline; `--version` ≤ 150 ms; `verify` of `dual-family` ≤ 500 ms cold. Thresholds hold a 2–3× margin over the preparation machine (`precision-scale-index.md` §2).

## 11. Fuzzing (`make fuzz`, 30 minutes nightly)

Hypothesis-driven generators build garbage bundles (random trees, random bytes, truncations, huge claimed lengths) and feed them to `verify_bundle`, the manifest parser, both envelope parsers, the citation parser and `canonicalize`. Assert: no uncaught exception, no exit code 70, no hang beyond 5 s per case, results always typed. Optional: `atheris` on Linux and macOS.

## 12. Coverage, traceability and CI gates

- Coverage: 100 % branch on PT0 modules, ≥ 95 % line on PT1, ≥ 90 % overall (R-TEST-02). No `pragma: no cover` on protocol paths.
- **Traceability:** `tools/trace.py` reads `@pytest.mark.req("UR-12")` markers and `R-…` mentions in docstrings and fails if a P0 requirement or rule lacks a test. Until WP-17 it enforces only requirements whose owning work package (the UR→WP map in `user-requirements.md` §2) is recorded as done in `docs/work-log/`; at WP-17 it enforces all of them.
- Required checks on every pull request: lint, type, unit+property, conformance, security, differential, CLI, docs (README and tutorial commands executed), build (`twine check`), determinism. Matrix: Linux, macOS, Windows × Python 3.11, 3.12, 3.13, 3.14.
- Nightly: fuzz, slow, mutation testing of PT0 modules (`mutmut`, target ≥ 90 % of mutants killed; P2), `latest-deps` job (unpinned dependencies must still pass the whole suite), `pip-audit`.
- A new `skip`, `xfail` or threshold change in `tests/conformance` fails CI (R-TEST-06).

## 13. Regenerating or auditing test data

Only the Spec Guardian touches `tests/vectors/` or `tests/fixtures/`, and only through `tests/README.md`. The golden rule: the Yellow Paper values come from the paper; everything else is regression data.
