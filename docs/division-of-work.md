# division-of-work.md — Who Builds What, In What Order

Works for one agent working sequentially or several agents working in parallel. Sizes are relative (S ≈ half a day of agent work, M ≈ one to two days, L ≈ three or more).

## 1. Roles and file ownership

Only the owner edits a path. Anyone else files a request in the work log.

| Role | Owns | Also does |
|---|---|---|
| **Spec Guardian** | `docs/decision-log.md`, `docs/queries/`, `tests/vectors/` (read-only after WP-00), `tests/fixtures/` | Reviews every PT0/PT1 diff against the paper |
| **Core Engineer** | `constants.py`, `errors.py`, `hashing.py`, `unicode18.py`, `_repertoire.py`, `ctf1.py`, `merkle.py`, `pid.py`, `citations.py`, `manifest.py` | |
| **Crypto Engineer** | `backends/`, `signing.py`, `envelope.py`, `keyfile.py` | Backend interop tests |
| **Verification Engineer** | `bundle.py`, `verify.py`, `report.py`, `publish.py`, `limits.py` | |
| **CLI Engineer** | `cli/` | Message copy, help text |
| **QA / Conformance Engineer** | `tests/` (except vectors and fixtures), `tools/`, traceability script | Property, fuzz, tamper matrix |
| **Release Engineer** | `pyproject.toml`, `Makefile`, `.github/`, `CHANGELOG.md`, `SECURITY.md` | |
| **Docs Engineer** | `README.md`, `docs/tutorial.md`, `docs/verify-by-hand.md`, examples | Doc-example tests |
| **Adversarial Reviewer** | nothing; writes `docs/reviews/WP-xx.md` | Runs prompt R before every gate |

## 2. Work packages

| WP | Deliverables (paths under `src/aethel_codex/` unless noted) | Needs | Gate: evidence you must show | Size |
|---|---|---|---|---|
| **00 Bootstrap** | `pyproject.toml`, `Makefile`, lint/type/test config, CI skeleton, pre-commit, `.gitattributes`, `tests/vectors/SHA256SUMS` check, `tools/check_coverage.py`, `tools/trace.py`, import linter contracts, repo layout from `architecture.md` | – | `make check` green; CI green on 3 OS; vector checksum test passes; `pip install -e .` works | S |
| **01 Foundations** | `constants.py`, `errors.py` (+ code registry), `hashing.py` | 00 | Label length bytes equal `pip1-vectors.json` `constants.labels`; domain-separation property test (Lemma 1); registry lists every code of `specs.md` §14 | S |
| **02 Unicode + CTF-1** | `unicode18.py`, `_repertoire.py`, `ctf1.py`, `tools/gen_repertoire.py`, `tools/fetch_unicode_tests.py` | 01 | T1, T2, 12 negatives; fixed-point property over ≥ 20,000 inputs; **100 % of `NormalizationTest.txt` 18.0.0**; repertoire sweep equals live tables; canary digest equals vector file; version guard test | M |
| **03 Merkle + ids** | `merkle.py`, `pid.py` | 01 | T1–T4 ids; T3 leaves, node, root, audit paths; all `pack_generated.blob_sizes`; streaming equals recursive for n = 1…300 leaves and irregular feed slices; forged proofs rejected; PID grammar accept/reject | M |
| **04 Manifest** | `manifest.py` | 02, 03 | Both A.3 manifests accepted and re-serialise identically; all 9 mutation vectors; `grammar_cases`; builder → parser → serializer property; one-byte-mutation property (reject, or accept and re-serialise to the same bytes) | M |
| **05 Citations** | `citations.py` | 03 | A.5 locator table; every syntax-error string; inline-scanner cases; type `k` refused | S |
| **06 Crypto** | `backends/*`, `signing.py`, `envelope.py` | 01, 03 | A.2: full signature verifies (`cryptography`); wrong context, role 02 and revision id rejected; ML-DSA-65 vector; both SLH-DSA vectors verify and their negatives fail; length checks; `InvalidSignatureError` handling; faulty-backend self-verify test; strict Base64; oracle interop test (dev) | L |
| **07 Bundles + verify** | `bundle.py`, `verify.py`, `report.py`, `limits.py` | 04, 05, 06 | Five fixtures reproduce their `expected.json`; tamper matrix (`testing-and-conformance.md` §6); symlink and traversal tests; limit tests; the seven attribution rows of A.5; report validates against the JSON schema | L |
| **08 Key files** | `keyfile.py` | 06 | AKF-1 round trips (plain and encrypted); wrong passphrase; AAD tamper; mode `0600` and refusal of wider modes (POSIX); `O_EXCL`; secrets absent from output, `repr` and logs; public/secret consistency check | M |
| **09 Publish + revise** | `publish.py` | 07, 08 | Publish → verify = integrity PASS, attribution as expected; revise → verify with `--parents` = V5 PASS; manifest ids identical across OS; `--dry-run` writes nothing; self-verify; atomic write; idempotent re-publish | M |
| **10 CLI (P0)** | `cli/` commands `canon id keygen publish sign verify inspect`, global flags | 07, 08, 09 | Every P0 command per `cli-spec.md`; exit-code table tests; JSON schema tests; `NO_COLOR`, non-TTY and `--ascii` tests; terminal-injection tests; no network test | L |
| **11 Self-test** | `selftest`, `explain`, `version` commands, package data | 10 | `aethel selftest` green offline from package data; `explain` covers every registry code (test); `version --json` schema | S |
| **12 P1 commands** | `revise`, `cite make/check/show`, `proof make/verify`, `attest add` | 10 | Each command's contract tests; proofs verify and forged proofs fail; attestations reported as present and unverified | M |
| **13 Independent verifier** | `scripts/verify_minimal.py` (stdlib only), `tests/differential/` | 07 | Minimal verifier and the package agree on all fixtures and on 200 randomly tampered bundles (V1–V3) | S |
| **14 Hardening** | fuzz targets, DoS and limit tests, Windows path and case-collision tests, 1 GiB streaming test, Unicode edge corpus | 07, 10 | `make fuzz` clean for 30 minutes; 1 GiB asset hashes in bounded memory; no crash on garbage bundles; all FC4 checks in `precision-scale-index.md` §5 pass | M |
| **15 Packaging + CI** | build, wheel/sdist checks, CI matrix, release workflow, SBOM, `pip-audit`, `tools/determinism_check.py`, `tools/install_smoke.py` | 11, 12, 13, 14 | Clean-venv install of the wheel on 3 OS runs `aethel selftest` and verifies a fixture; `twine check` clean; lockfile hashes; reproducible-build comparison | M |
| **16 Docs** | `README.md`, `docs/tutorial.md`, `docs/verify-by-hand.md`, man-page text, examples | 10, 12 | Every command in the docs executes in CI and matches shown output; claims audit against `what-not-to-do.md` §4 | M |
| **17 Acceptance** | `docs/conformance-report.md` (generated), release candidate tag | 15, 16 | MVP exit criteria below | S |

## 3. Dependency graph

```
00 ─ 01 ─┬─ 02 ─┬─ 04 ─┬─ 07 ─┬─ 09 ─ 10 ─┬─ 11 ─┐
         │      │      │      │           ├─ 12 ─┤
         ├─ 03 ─┴─ 05 ─┘      └─ 13 ──────┤      ├─ 15 ─ 17
         │                                └─ 14 ─┤      │
         └─ 06 ───────────── 08 ────────────────┘   16 ─┘
```

**Critical path:** 00 → 01 → 02 → 04 → 07 → 09 → 10 → 15 → 17. WP-03, 05, 06 and 08 run in parallel lanes.
**Parallel lanes for several agents:** Lane A (Core): 01 → 02 → 03 → 04 → 05. Lane B (Crypto): 06 → 08, starting once WP-01 and WP-03 land. They merge at WP-07.

## 4. Hand-off protocol

1. A WP closes only when its **gate evidence** is pasted in a work-log entry (`prompts.md` template W) and `make check` and `make conformance` are green.
2. The Adversarial Reviewer runs prompt R and writes `docs/reviews/WP-xx.md`. Any FC3 or FC4 finding blocks closure (`precision-scale-index.md`).
3. The Spec Guardian confirms no vector, fixture or ADR changed without an entry in `decision-log.md`.
4. The next WP starts from a clean `main`.
5. Open questions go to `docs/queries/Q-n.md`. Work that does not depend on the answer may continue.

## 5. Definition of done (every WP)

Code, tests and docs together; all rules in `rules.md` satisfied; coverage gates met; types and lint clean; reviewer pass recorded; work log complete; no placeholder in a shipped path; decision log current; `CHANGELOG.md` updated for user-visible change.

## 6. MVP exit criteria (WP-17)

1. Every P0 requirement in `user-requirements.md` is met and traced to a passing test.
2. The conformance matrix (`specs.md` §15) is green on Linux, macOS and Windows, Python 3.11 to 3.14.
3. All five golden bundles and all Yellow Paper vectors pass; `aethel selftest` passes from an installed wheel.
4. A clean-environment install of the built wheel works on all three operating systems.
5. The security checklist in `security.md` §8 is complete.
6. Documentation examples run in CI and every claim passes the §4 audit.
7. No open FC3 or FC4 item; the reviewer's final report is attached.
8. The generated `docs/conformance-report.md` lists, role by role, what was tested and what the Yellow Paper's open items still leave unproven. It states plainly that independent review (open item 2) has not happened.
