# rules.md — Hard Rules

A rule is binding. "Check" says how a human or CI proves it. If a rule blocks you, do not bend it: raise a Spec Query (`AGENTS.md` §6) or an ADR (`decision-log.md`). Rules marked **★** are enforced by an automated test or lint that fails the build.

## A. Protocol fidelity

| ID | Rule | Why | Check |
|---|---|---|---|
| R-PROTO-01 | The Yellow Paper PDF is the only normative source. `specs.md` is a derived guide. On conflict the paper wins, and you raise a Spec Query. | Silent deviation breaks the standard | Review; Spec Query log |
| R-PROTO-02 ★ | Files in `tests/vectors/` are read-only oracles. Never edit, regenerate, skip or "correct" a value to make a test pass. A mismatch means your code is wrong until a human says otherwise. | Vectors are the contract | CI hashes the vector files against `tests/vectors/SHA256SUMS` |
| R-PROTO-03 ★ | Bytes in, bytes out. Everything hashed, signed or compared is `bytes`. Read and write files in binary. No locale, no newline translation, no implicit encoding, no `errors=` argument in core code. | One hidden translation changes an identity | Ruff rule set bans `open()` without `"rb"`/`"wb"` in `src/`; CRLF/BOM tests on all three OSes |
| R-PROTO-04 ★ | Labels, constants, algorithm ids, role ids and the signature context are defined once, in `constants.py`. | Duplicated constants drift | grep test: each literal appears once in `src/` |
| R-PROTO-05 ★ | Never write timestamps, hostnames, usernames, filesystem paths, tool versions or random values into manifests, texts or envelopes, beyond what the grammar demands. | The protocol has no self-asserted clocks (P5) and must not leak identity | Property test: two publishes on different machines give byte-identical manifests |
| R-PROTO-06 ★ | Strict or reject. Manifests, envelopes, citations, PIDs and key files parse with one grammar and no fallback, no repair, no "lenient" switch. Producers pass their own output through the strict parser. | Parser differentials are the ambiguity PIP-1 exists to remove | Mutation and fuzz tests; `lenient` is a banned identifier |
| R-PROTO-07 | The algorithm set is fixed by profile `pip-1`. Unknown profile ⇒ report "unknown profile" and do not interpret the rest. No negotiation, no downgrade. | [YP §13.2] | Test with `profile pip-2` |
| R-PROTO-08 ★ | Unicode data comes from `unicodedata2` at version 18.0.0, guarded at import. The standard-library `unicodedata` is never imported in `src/`. | Python's own tables are older (15.0.0 on 3.12) | Import linter; version-guard test |
| R-PROTO-09 ★ | "SHA3-256" means FIPS 202 (`hashlib.sha3_256`). Never Keccak-256 or any variant. Hash inputs always use `H(label, x)` with the length-prefixed label. | Keccak and SHA3 differ in padding; unlabelled hashes break domain separation | Vector tests; static check that `hashlib` is only used in `hashing.py` |
| R-PROTO-10 ★ | Signatures use only final ML-DSA (FIPS 204) and SLH-DSA (FIPS 205), pure variants, context `pip1.sig`, message `u8(role) ‖ raw 32-byte manifest digest`. Pre-hash variants and pre-standard Dilithium/SPHINCS+ are forbidden. | [YP §9.1, §9.3] | A.2 verify test; wrong-context/role tests |
| R-PROTO-11 ★ | The package and CLI perform no network I/O, ever. | Offline verification is design principle P7 | Test blocks `socket` and fails on any connect; import test bans `urllib`, `http`, `socket`, `ssl`, `requests` in `src/` |
| R-PROTO-12 | The verifier reports integrity, attribution, history and time as separate statements. A hit limit is reported, never PASS or FAIL. | [YP §11.3, §12.7] | JSON-schema test; limit tests |
| R-PROTO-13 | Do not add protocol objects: no manifest fields, envelope fields, identifier types, bundle files or version numbers beyond the Yellow Paper. Tool-level formats (key file, proof file, JSON reports) are labelled non-protocol. | A private extension is a fork | Review against `specs.md` §13 |

## B. Honesty

| ID | Rule | Check |
|---|---|---|
| R-HON-01 ★ | All user-facing text (help, errors, README, docs) asserts nothing beyond Yellow Paper §2.3. It never says or implies: proves who wrote it, proves who had the idea first, cannot be deleted, permanent storage, quantum-proof, unbreakable, tamper-proof storage. Use the approved phrases in `guidelines.md` §6. | A test greps shipped text for the banned list in `what-not-to-do.md` §4 |
| R-HON-02 | Every progress claim is labelled VERIFIED, DERIVED or ASSUMED. | Review of work logs |
| R-HON-03 | A work package is not done without evidence: the commands run and the relevant output. | Work log template W |
| R-HON-04 ★ | No placeholders in shipped paths: no `TODO`, `FIXME`, `pass` stubs, `NotImplementedError`, mock or fake crypto, sample data standing in for real data, lorem ipsum. An unfinished feature is not exposed in the CLI and is listed under "Not yet" in the docs. | Lint rule + grep in CI |
| R-HON-05 | Documents never describe a feature that is not built and tested. | Doc-example test (WP-12) |

## C. Code

| ID | Rule | Check |
|---|---|---|
| R-CODE-01 ★ | Python ≥ 3.11. Fully typed. `mypy --strict` clean. No `Any` in PT0/PT1 modules. Every `# type: ignore` carries a reason. | `make type` |
| R-CODE-02 | Core modules are pure and deterministic. File I/O lives only in `bundle.py`, `keyfile.py` and `cli/`. | Import and dependency tests |
| R-CODE-03 ★ | Layering follows `architecture.md` §3. No import cycles. Core never imports `cli`. | `import-linter` contract |
| R-CODE-04 ★ | Errors are typed exceptions with a stable `.code` from the registry. Callers branch on `.code`, never on message text. Never `except Exception: pass`. Never catch to return a friendlier success. | Ruff `BLE001`, `S110`; tests |
| R-CODE-05 | No mutable global state. No import-time side effects other than constants and the Unicode guard. | Review; import test |
| R-CODE-06 | Every public function has a docstring that cites its Yellow Paper section (`YP §x.y`) and states its failure modes. | Docstring lint (`D` rules) + custom test for `YP §` |
| R-CODE-07 | No magic numbers in protocol code; use named constants. | Review |
| R-CODE-08 ★ | Cyclomatic complexity ≤ 10 in PT0/PT1 modules. Functions that do two jobs are split. | Ruff `C901` |

## D. Testing

| ID | Rule | Check |
|---|---|---|
| R-TEST-01 | Every requirement (UR-…) and every rule has at least one test that names its ID in a marker or docstring. | Traceability script in `make check` |
| R-TEST-02 ★ | Coverage: 100 % branch on PT0 modules, ≥ 95 % line on PT1, ≥ 90 % overall. No `# pragma: no cover` on protocol paths. | `pytest --cov` gates |
| R-TEST-03 | Tests are deterministic: no network, no wall-clock, no sleeps, temporary directories only, seeds printed. | Fixtures; flaky-test policy |
| R-TEST-04 | A bug fix begins with a failing regression test. | PR review |
| R-TEST-05 | Every accept path has reject-path tests. Negative tests are as numerous as positive ones for parsers. | Review; counts in `testing-and-conformance.md` |
| R-TEST-06 ★ | You may not add `skip`, `xfail` or lowered thresholds to turn a failure green. | CI fails on new skips in `tests/conformance` |

## E. Security

| ID | Rule | Check |
|---|---|---|
| R-SEC-01 ★ | Key files are created with `O_EXCL` and mode `0600`, and loading refuses group/other-accessible files on POSIX. Secrets never appear in argv, environment, logs, exception text, `repr`, JSON output or tracebacks. | `tests/security/` |
| R-SEC-02 ★ | Sign, then verify the signature, then release. If self-verification fails, delete nothing, release nothing, exit 70. | Test with a faulty backend |
| R-SEC-03 ★ | Untrusted text is sanitised before it reaches a terminal: escape C0/C1 controls, bidirectional controls and tag characters as `\u{…}`. JSON output uses normal JSON escaping. | Terminal-injection tests |
| R-SEC-04 ★ | Untrusted bundles: never follow symlinks; regular files only; enforce size limits; build paths only from validated names; no `eval`, `exec`, `pickle`, `shell=True`, `yaml.load`. | Ruff `S` rules; path-traversal tests |
| R-SEC-05 | Randomness comes only from the backends or the OS CSPRNG. `random` is never used for security values. | Ruff `S311` |
| R-SEC-06 | Never implement ML-DSA, SLH-DSA or Unicode normalization yourself. The only hand-built primitive composition is `H()` over `hashlib`. | Review |
| R-SEC-07 | Release builds use hash-pinned lockfiles. `pip-audit` is clean. | CI |

## F. Dependencies

| ID | Rule | Check |
|---|---|---|
| R-DEP-01 ★ | Runtime dependencies are exactly `cryptography`, `pqcrypto`, `unicodedata2` (ranges in `architecture.md` §8). Adding one needs an owner-approved ADR. | Test reads `pyproject.toml` |
| R-DEP-02 ★ | Test oracles (`dilithium-py`, `slh-dsa`) are dev-only and never imported by `src/`. | Import linter |
| R-DEP-03 | The CLI is built on `argparse`. No `click`, `typer`, `rich` or similar. | R-DEP-01 test |

## G. Process

| ID | Rule |
|---|---|
| R-PROC-01 | Work in WP order, one WP per branch and pull request, closed only with its gate evidence. |
| R-PROC-02 | Code, tests and docs change together. User-visible changes get a `CHANGELOG.md` entry. |
| R-PROC-03 | A decision that interprets or deviates from the paper is written as an ADR **before** you implement it. |
| R-PROC-04 | **Three strikes.** After three failed attempts at the same failure, stop, write a diagnosis (what you tried, what you saw, what you think), and ask. Do not try a fourth variation. |
| R-PROC-05 | Scope is the P0 and P1 lists in `user-requirements.md`. New ideas go to the parking lot at the end of `docs/roadmap-parking-lot.md` (create on first use). |
| R-PROC-06 | Every WP gets an adversarial review pass (`prompts.md` prompt R) before closure. |
| R-PROC-07 | Commits are small, focused and follow `guidelines.md` §7. No unrelated refactors inside a feature commit. |

## H. User experience

| ID | Rule | Check |
|---|---|---|
| R-UX-01 | Human first, machine friendly. Every read command supports `--json`. stdout carries results, stderr carries diagnostics and progress. | CLI contract tests |
| R-UX-02 | Errors say what happened, why it matters and what to do next, with the Yellow Paper section. No stack trace unless `--debug`. | Message snapshot tests |
| R-UX-03 ★ | Flags, exit codes and JSON schemas are versioned contracts. A breaking change is a major version. | Schema tests |
| R-UX-04 | No colour-only meaning. Honour `NO_COLOR`. No spinners or animations when not a TTY. Plain ASCII output is always available (`--ascii`). | Tests with `NO_COLOR` and non-TTY |
| R-UX-05 | Calm voice: no emoji, no exclamation marks, no hype, no marketing language. Mirror the honesty of the project site. | Banned-phrase test |
