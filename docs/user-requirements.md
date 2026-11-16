# user-requirements.md — What People Need From `aethel`

Priorities: **P0** must ship in the MVP · **P1** next (WP-12) · **P2** parked. Every P0 requirement needs a test with `@pytest.mark.req("UR-nn")` (R-TEST-01).

## 1. People we build for

| Persona | Needs | Judges us by |
|---|---|---|
| **Writer** (essayist, scientist, translator) | Give a text a name made from the text itself and sign it, in a few commands, without learning cryptography | Whether the first publish works in five minutes and every message makes sense |
| **Researcher** (citer) | Cite an exact passage by identifier and check someone else's citation | Whether a citation cannot be quietly redirected and a locator is checked precisely |
| **Archivist / mirror operator** | Verify thousands of bundles in a script; spot any change | Stable exit codes, JSON Lines, speed, no false PASS |
| **Developer / integrator** | Call the logic from Python and from CI | A small documented API, versioned JSON schemas |
| **Auditor / cryptographer** | See exactly what is computed and why; reproduce vectors | Traceability to the Yellow Paper, deterministic output, honest limits |
| **Future reader** (decades on) | Verify without our tool | Plain-text formats, `verify-by-hand.md`, the independent minimal verifier |

## 2. Functional requirements

| ID | Pri | Requirement | Acceptance (summary) |
|---|---|---|---|
| UR-01 | P0 | `canon` writes CTF-1 canonical bytes; `--check`, `--report`, `-o` | T2 input gives `output_hex`; `--check` exit 0/1/3 |
| UR-02 | P0 | `id` prints `pip1:t:…` for text, `pip1:a:…` for assets | T1 file → `pip1:t:8186c5e1…96ba`; empty asset id matches |
| UR-03 | P0 | Rejections name code point or byte offset, line, column, Yellow Paper section | All 12 negatives show code and position |
| UR-04 | P0 | `canon` and `id` accept `-` for stdin | Piped input gives the same result as a file |
| UR-05 | P0 | `keygen` creates ML-DSA-87, ML-DSA-65, SLH-DSA-SHA2-256s or SHAKE-256s keys; encrypted by default; never overwrites | Key file mode `0600`; refuses overwrite; refuses with no TTY and no passphrase option |
| UR-06 | P0 | `key info` shows algorithm and key id, never the secret | Output contains no secret bytes in any encoding |
| UR-07 | P1 | `keygen --dual` | Two files; classes can reach Dual-family |
| UR-08 | P0 | `publish` builds a genesis bundle with text, assets, cites, authors, title, licence, language, markup | Output parses strictly; verifier gives integrity PASS |
| UR-09 | P0 | `publish` signs with ≥ 1 key, self-verifies, writes atomically, then runs the full verifier | A forced failure leaves no bundle behind |
| UR-10 | P0 | `publish --dry-run` shows identifiers and the manifest, writes and signs nothing | No files created; ids equal the real run |
| UR-11 | P0 | Same inputs give identical manifest bytes on every OS and Python | Determinism CI job |
| UR-12 | P0 | Unsafe or ambiguous inputs are refused: bad asset names, case collisions, same name with different bytes, wrong cite types | Each gives a named error |
| UR-13 | P1 | `revise` creates a revision with `work` and `parent` | `verify --parents` gives V5 PASS |
| UR-14 | P1 | `--derivative` and `--beacon` are carried in the manifest | Parsed and reported; beacon "unchecked" |
| UR-15 | P0 | `sign` adds a signature in any role; refuses if integrity fails; warns for undeclared author keys | Matches `cli-spec.md` |
| UR-16 | P1 | Co-author flow: declare with `--author`, sign later | Partially attributed → Attributed without a new revision |
| UR-17 | P0 | `verify` runs V1–V8 and prints integrity, attribution, history, time separately | Fixtures match `expected.json` |
| UR-18 | P0 | `verify --json` follows a versioned schema; several bundles give JSON Lines | Schema validation |
| UR-19 | P0 | `--require-attributed`, `--require-dual-family`, `--require-parents`, `--warnings-as-errors` change only the exit code | Check statuses unchanged |
| UR-20 | P0 | Verification needs only the bundle (and optional `--parents DIR`): no network, registry or clock | Network-blocked test passes |
| UR-21 | P0 | A single-bit change to manifest, text or asset is always detected | Tamper matrix |
| UR-22 | P0 | A hit limit is reported as inconclusive (exit 6), never PASS or FAIL | Limit tests |
| UR-23 | P0 | `inspect` prints a manifest without verifying and says so | First line text |
| UR-24 | P0 | `explain CODE` covers every registry code | Completeness test |
| UR-25 | P0 | `selftest` runs the packaged vectors offline from an installed wheel | Passes in a clean venv |
| UR-26 | P0 | `version` and `--version` show tool, Yellow Paper, Unicode, backend versions | Schema test |
| UR-27 | P1 | `cite make/check/show` | A.5 locators behave identically |
| UR-28 | P1 | `proof make/verify` | Valid proofs pass, altered ones fail |
| UR-29 | P1 | `attest add` stores an attestation reported as present and unverified | Reported WARN `ATT_UNVERIFIED` |
| UR-30 | P0 | Installs with `pipx install aethel-codex` or `uv tool install aethel-codex` on Linux, macOS, Windows; Python ≥ 3.11; no compiler needed | Clean-environment CI job |
| UR-31 | P0 | No network, telemetry, accounts, update checks, or clock | Security tests |
| UR-32 | P0 | Importable library with a small documented API (`architecture.md` §4) | Doc example tests |
| UR-35 | P0 | README: install, five-minute tutorial, and an honest "what this does and does not show" section | Doc tests and claims audit |
| UR-36 | P0 | `docs/verify-by-hand.md` and `scripts/verify_minimal.py` | Differential test |
| UR-37 | P0 | Every command's `--help` has a worked example | Help snapshot test |
| UR-38 | P1 | Generated `docs/conformance-report.md` | Produced by WP-17 |
| UR-39 | P0 | Secrets are protected; terminal output is sanitised | Security tests |
| UR-40 | P0 | User-facing text contains no banned claim | Banned-phrase test |
| UR-33/34 | P2 | Shell completion; `lint` | Parked |

**UR → work package map.** Logic is built in the first work package listed; the command in `cli/` follows in WP-10 unless stated.

| Requirements | Work packages |
|---|---|
| UR-01, 03, 04 | WP-02, WP-10 |
| UR-02 | WP-03, WP-10 |
| UR-05, 06 | WP-08, WP-10 |
| UR-07 | WP-08, WP-12 |
| UR-08 to 12 | WP-09, WP-10 |
| UR-13, 14, 16 | WP-09, WP-12 |
| UR-15 | WP-06, WP-07, WP-10 |
| UR-17 to 22 | WP-07, WP-10 |
| UR-23, 37 | WP-10 |
| UR-24, 25, 26 | WP-11 |
| UR-27, 28, 29 | WP-12 |
| UR-30 | WP-15 |
| UR-31 | WP-14 (and every WP) |
| UR-32, 35, 38 | WP-16, WP-17 |
| UR-36 | WP-13, WP-16 |
| UR-39 | WP-08, WP-14 |
| UR-40 | WP-10 onward (banned-claim test), WP-16 |

## 3. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Meet the scale budgets of `precision-scale-index.md` §2 |
| NFR-02 | Deterministic and reproducible: same bytes in, same bytes out, everywhere |
| NFR-03 | Portable: Linux, macOS, Windows × Python 3.11–3.14 |
| NFR-04 | Never crash on hostile input: only typed results (fuzz) |
| NFR-05 | Maintainable: `mypy --strict`, coverage gates, enforced layering |
| NFR-06 | Accessible: `NO_COLOR`, `--ascii`, no cursor control, no animation, readable by screen readers |
| NFR-07 | Long-lived: formats are plain UTF-8 text; anyone can re-implement from the paper; docs enable it |
| NFR-08 | Private: no personal data in any output, no telemetry |
| NFR-09 | Auditable supply chain: three runtime dependencies, hash-pinned lockfile, SBOM |
| NFR-10 | UTF-8 everywhere; messages in English for the MVP; no locale dependence |

## 4. Acceptance scenarios

**S1 First publish.** *Given* a Markdown file with CRLF endings and a key made by `keygen`, *when* the writer runs `publish` with `--title`, `--license`, `--key`, *then* a bundle named by its manifest id appears, the output shows integrity PASS and Attributed (1 of 1), and running `publish` again with the same inputs finds the identical manifest.

**S2 Verify a stranger's bundle.** *Given* a bundle and no network, *when* `verify` runs, *then* four separate statements are printed, with the standing note that a signature does not show who holds the key, and the exit code is 0 only for integrity PASS.

**S3 Tamper.** *Given* a verified bundle, *when* one bit of `text.md` changes, *then* integrity is FAIL with `TEXT_MISMATCH`, exit code 1, and nothing says "valid".

**S4 Co-author.** *Given* a bundle that declares two authors and carries one signature, *when* the second author runs `sign`, *then* attribution moves from Partially attributed (1 of 2) to Attributed (2 of 2) with no new revision; with an ML-DSA key and an SLH-DSA key it reads Dual-family.

**S5 Mirror batch.** *Given* 10,000 bundles, *when* `verify --json` is run over them, *then* one JSON line per bundle appears, one bad bundle does not stop the rest, memory stays flat, and the exit code is the worst result.

**S6 Garbage in.** *Given* a binary file passed as a manuscript, *when* `publish` runs, *then* it exits 3 with the code `E_INVALID_UTF8`, the byte offset, and no partial output.

## 5. Out of scope

Everything listed in `what-not-to-do.md` §2. New ideas go to `docs/roadmap-parking-lot.md`; they never enter a work package by stealth.

## 6. MVP success

The exit criteria in `division-of-work.md` §6 are met; a person who has never seen the Yellow Paper can publish, sign and verify a text in five minutes from the README; and an independent reader can verify the same bundle with `scripts/verify_minimal.py` and the paper alone.
