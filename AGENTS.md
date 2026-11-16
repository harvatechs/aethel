# AGENTS.md — Aethel Codex (`aethel`)

You are building `aethel`, the reference command-line tool and library for the Permanent Ink Protocol profile **pip-1** (Yellow Paper PIP-YP-1 v1.0.0-rc.3). A wrong byte here is a broken standard. **Correctness against the Yellow Paper outranks speed, elegance and features.**

## 0. Load order

1. This file. 2. `docs/rules.md`. 3. `docs/what-not-to-do.md`. 4. `docs/decision-log.md` (skim).
Then only the documents your current work package names (`docs/division-of-work.md`).

## 1. Source of truth

`docs/yellow-paper/*.pdf` → `tests/vectors/*.json` → `docs/specs.md` → `docs/decision-log.md` → everything else.
On conflict, follow the higher one and raise a **Spec Query** (section 6). Never choose silently.

## 2. The twelve non-negotiables (full text and checks: `docs/rules.md`)

1. **The Yellow Paper wins.** Vectors in `tests/vectors/` are immutable oracles. A failing vector means your code is wrong.
2. **Bytes in, bytes out.** Read and write files in binary. No locale, no newline translation, no `errors="replace"`.
3. **Unicode 18.0.0 comes from `unicodedata2`.** The standard-library `unicodedata` is banned from `src/`.
4. **SHA3-256 is FIPS 202**, not Keccak-256. Every hash is `H(label, x) = SHA3-256(u8(len(label)) ‖ label ‖ x)`.
5. **Strict or reject.** One grammar, no repair, no lenient mode, no guessing.
6. **No clocks, no identity leakage, no new protocol fields.** Never emit timestamps, hostnames, usernames, paths or versions into manifests, texts or envelopes.
7. **Offline always.** No network I/O anywhere in the package or CLI.
8. **Honest claims.** The verifier reports integrity, attribution, history and time separately, never one "valid". Copy never promises more than the Yellow Paper (§2.3).
9. **No placeholders.** No `TODO`, `pass` stubs, `NotImplementedError` in shipped paths, mock crypto or fake data. An unfinished feature is not exposed.
10. **Never write your own ML-DSA, SLH-DSA or Unicode normalization.** Runtime dependencies are exactly `cryptography`, `pqcrypto`, `unicodedata2`.
11. **Sign, then self-verify, then release.** Fail closed.
12. **Evidence before "done".** Show commands and output. After three failed attempts at the same problem, stop and report (R-PROC-04).

## 3. Commands (all must exist after WP-00)

| Command | Meaning |
|---|---|
| `make setup` | Create the environment and install everything (`uv sync --all-groups`) |
| `make lint` | `ruff check` and `ruff format --check` |
| `make type` | `mypy --strict src tests` |
| `make test` | Unit and property tests (no network, no sleeps) |
| `make conformance` | Yellow Paper vectors, golden bundles, `aethel selftest` |
| `make check` | lint + type + test + conformance. **Green before every commit** |
| `make fuzz` | Long property and fuzz runs (nightly) |
| `make build` | Build sdist and wheel, run `twine check` |

## 4. Working protocol (every session)

1. Open the WP card in `docs/division-of-work.md`. Read the documents it lists.
2. Restate in at most five lines what you will build and which tests will prove it.
3. For PT0 and PT1 code (`docs/precision-scale-index.md`), write the failing test first.
4. Implement the smallest slice that passes. Keep layering from `docs/architecture.md`.
5. Run `make check`; at a gate also `make conformance`.
6. Append a work-log entry (`docs/prompts.md`, template W) with evidence.
7. Stop at the gate. Do not begin the next package without the hand-off.

## 5. Stop the line

Halt all other work and follow `docs/precision-scale-index.md` playbooks if any of these occur:

- A vector, fixture or conformance test fails (FC3).
- `verify` accepts something it should reject, a secret reaches logs or argv, a network call happens, or a signature is released without self-verification (FC4).
- Two crypto backends disagree, or a dependency is missing, yanked or changed behaviour (FC3/FC4).
- You feel the urge to edit a vector, loosen a test, add `skip`/`xfail`, or write "simplified for now".

## 6. Spec Query (when the paper is silent, ambiguous or seems wrong)

Write to `docs/queries/Q-<n>.md`: the question; the Yellow Paper section(s) quoted by number; what you believe it means; the options; the option you would take and why; which tests depend on it. Then continue only with work that does not depend on the answer.

## 7. How to report

Label every claim **VERIFIED** (you ran it and saw the output), **DERIVED** (follows from cited spec text) or **ASSUMED** (needs confirmation). Never write "should work", "done", or "production ready" without evidence.

## 8. Where things live

```
src/aethel_codex/   core + backends + cli       docs/        this pack's documents
tests/vectors/      oracles (read-only)         tests/fixtures/   golden bundles
tests/unit|property|conformance|cli|security    tools/       dev scripts (never shipped)
```
