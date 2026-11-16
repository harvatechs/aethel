# precision-scale-index.md — How Exact, How Big, What If It Goes Wrong

One index answers three questions for any piece of work: **how exact must it be** (precision tiers), **how big must it cope** (scale bands), and **what do I do when it fails** (failure classes, priority stack, playbooks). When unsure which tier applies, choose the higher.

## 1. Precision tiers

| Tier | Meaning | Where | Tolerance | Required evidence | Workflow consequence |
|---|---|---|---|---|---|
| **PT0** | Bit-exact and frozen. A deviation changes identifiers or signatures | `constants`, `hashing`, `unicode18`, `_repertoire`, `ctf1`, `merkle`, `pid`, manifest serialization, signed-message construction, backend context handling | Zero | Yellow Paper vectors, 100 % branch coverage, property and differential tests | Test first. Spec Guardian reviews every diff. Reviewer prompt R mandatory |
| **PT1** | Normative behaviour: accept/reject decisions and verification semantics | Manifest parser, envelope parsers, citations, `verify`, attribution, bundle reading, limits, key-file validation | Zero deviation in accept/reject. Code names recommended | Negative vectors, fixtures, fuzz, ≥ 95 % line coverage | Test first. ADR for any interpretation |
| **PT2** | Contract-stable, versioned | Public Python API, CLI flags, exit codes, JSON schemas, error-code strings | A breaking change is a major version | Schema tests, golden help text | Changelog entry; deprecation before removal |
| **PT3** | Craft and judgement | Message wording, layout, colour, progress output, internal helpers, performance tuning | Reviewer's taste, within `guidelines.md` | Review | Normal review |

## 2. Scale bands

Measured on the preparation machine (14 Nov 2026): tree hashing 260 MiB/s; ML-DSA-87 verify 0.3 ms; SLH-DSA verify 1–2 ms; SLH-DSA-256s sign 0.7–1.6 s; scrypt n = 2¹⁷ 0.52 s. Budgets below keep a 2–3× margin and are checked by benchmarks marked `slow`, run nightly.

| Band | Input | Required behaviour | Budget |
|---|---|---|---|
| **S0** | ≤ 4 KiB text, no assets | Trivial | `canon` + `id` ≤ 100 ms wall time cold |
| **S1** | Essay ≤ 1 MiB | Whole text in memory | `publish` (ML-DSA-87) ≤ 500 ms; `verify` ≤ 500 ms cold |
| **S2** | Book ≤ 64 MiB text, assets | Text in memory (≈ 6× its size peak); assets streamed | Text limit enforced; `verify` ≤ 3 s |
| **S3** | Asset 1–64 GiB | **Streamed only.** Memory ≤ 64 MiB + O(log n). Proofs from a leaf-hash list (32 B per 4 KiB) | ≥ 100 MiB/s; 1 GiB ≤ 15 s |
| **S4** | Mirror: 10⁴–10⁶ bundles | No global state; `verify` takes many paths and emits JSON Lines; one bundle's failure never stops the rest; exit code summarises | Memory independent of the number of bundles |

Also: `aethel --version` and `--help` ≤ 150 ms (import `cryptography` and `pqcrypto` lazily, only in commands that need them). SLH-DSA signing takes seconds: print one calm line to stderr before it starts.

## 3. Failure classes

| Class | Name | Examples | Required response |
|---|---|---|---|
| **FC0** | Cosmetic | Lint, typo, wording | Fix in the same commit |
| **FC1** | Local defect | Failing test in non-protocol code; bug with no contract impact | Regression test, fix, continue |
| **FC2** | Contract defect | CLI flag, exit code, JSON or API break; docs that disagree with behaviour; **a banned claim in shipped text** | Stop feature work, fix, update schemas and docs, changelog, reviewer pass. Release-blocking |
| **FC3** | Protocol deviation | Any vector or fixture mismatch; a spec ambiguity that changes accept/reject; two backends disagreeing; a rule of the paper violated | **Stop the line** (§4) |
| **FC4** | Trust failure | `verify` accepts a tampered or malformed input; a secret reaches output, argv or logs; network access; a signature released without self-verification; a symlink followed | **Stop the line, revert, incident note** (§4). Release-blocking |

## 4. Stop-the-line procedures

**FC3**
1. Halt all other work. Say so in the work log.
2. Reduce to the smallest failing input. Save it as a permanent test (do not yet fix).
3. Bisect to the commit that introduced it, or the line of the spec you misread.
4. Read the Yellow Paper section and `decision-log.md`. Decide: *my code deviates* (fix it) or *the paper is unclear or seems wrong* (write a Spec Query and park the dependent work).
5. Never change a vector, fixture or expected value. Never add a workaround that hides the case.
6. Re-run `make conformance` in full. Log the cause in one sentence.

**FC4**
1. Revert to the last green commit.
2. Write `docs/incidents/I-<n>.md`: what happened, scope, root cause, fix, regression test, how it escaped.
3. Fix, then run the full security suite and `make fuzz` for 10 minutes.
4. Tell the owner. The release stays blocked until the incident is closed.

## 5. Stop-the-line checks (any one triggers §4)

- A Yellow Paper vector, fixture or negative case fails on any OS or Python version.
- `verify` returns integrity PASS for a bundle with one flipped bit in `manifest.pip`, `text.*`, an asset or a signed field (tamper matrix).
- Any output file differs between two publishes of the same inputs on different machines.
- Any network connection attempt is observed in tests.
- A secret appears in stdout, stderr, argv, environment, a log or a traceback.
- `sign` or `publish` can release a signature that does not verify.
- A symlink is followed, or a path outside the bundle is read or written.
- Two crypto backends disagree about a signature, or a backend rejects the paper's A.2 signature.
- The Unicode guard, the repertoire sweep or the canary digest fails.

## 6. Priority stack (how to balance)

When goals conflict, the higher one wins:

1. Protocol correctness (PT0, PT1)
2. Security and trust (FC4 items)
3. Honest reporting (no overclaims, separate statements, evidence)
4. Contract stability (PT2)
5. Reliability: determinism, portability, offline behaviour
6. Clarity for the user
7. Performance
8. Features beyond P0
9. Polish

**Trade scope for time, never correctness for time.** If you are behind, cut in this order: P2 items → P1 breadth (`proof`, `attest`, `cite show`) → polish (colour, `--ascii` variants) → documentation extras. **Never cut:** PT0/PT1 tests, self-verification of signatures, the banned-claim test, secret handling, the offline guarantee, the conformance gates.

Common conflicts: helpful error text vs. secrecy → secrecy wins, the message omits the secret. Friendly output vs. precision → say less, say it exactly. Convenience default vs. explicitness → explicit (for example `--title` is required; the tool never guesses metadata that becomes permanent). Coverage target vs. deadline → write the tests.

## 7. Recovery playbooks

| ID | Symptom | First move | Do not | Done when |
|---|---|---|---|---|
| **RB-1** | A Yellow Paper vector fails | Recompute the value independently from the prose with `hashlib` only (`tests/README.md` shows how). Compare byte by byte, find the first divergence | Edit the vector; "fix" by special-casing | Code reproduces the vector and a regression test exists |
| **RB-2** | Two backends disagree | Test with the paper's A.2 signature and the SLH-DSA vectors; check context handling, role byte and raw-vs-hex digest; try the oracle | Pick the backend that agrees with you; disable the check | Cause found; interop test added; owner told (FC3) |
| **RB-3** | A dependency is missing, yanked, or behaves differently | Pin to the last good version in the lockfile; run `selftest`; read the changelog | Vendor or reimplement the library | Lockfile green; ADR updated if the dependency changes |
| **RB-4** | The paper is ambiguous or contradicts itself | Write the Spec Query with quotes and options | Choose silently; implement the "usual" behaviour | Owner or Working Group answered; ADR and `specs.md` updated |
| **RB-5** | Unicode mismatch (normalization test, canary, version guard) | Print `unicodedata2.unidata_version`; rerun the repertoire sweep; check for a different package version | Fall back to the standard library | Guard passes; all of `NormalizationTest.txt` passes |
| **RB-6** | You are looping or stuck | Apply the three-strike rule: stop, write what you tried and saw, ask | Try a fourth variation | A human decision is recorded |
| **RB-7** | Scope or abstraction is growing | Re-read `what-not-to-do.md` §2 and §5; delete the extra | Keep it "for later" | Diff matches the WP card |
| **RB-8** | Regression after a refactor | `git bisect` with `make conformance` as the test | Patch the symptom | Bisected commit understood; test added |
| **RB-9** | A benchmark misses its budget | Profile first (`cProfile`); check chunk feed size, per-byte Python loops, repeated copies | Micro-optimise PT0 logic without vectors green | Budget met with all vectors still green |
| **RB-10** | CI red on one OS only | Suspect paths, newline translation, permissions, wheel availability, case-insensitive names | Add an OS-specific skip | Fixed with a test that runs everywhere |
| **RB-11** | A flaky test | Find the hidden input (time, order, randomness, temp path) | Retry until green | Deterministic again |
| **RB-12** | Context lost, resuming | Use prompt C in `prompts.md`: re-read `AGENTS.md`, the latest work log and the open queries | Continue from memory | State restated and confirmed |
| **RB-13** | A fixture or oracle looks wrong | Recompute independently; compare with the paper; write a Spec Query | Edit the fixture | Discrepancy explained in writing |

## 8. Uncertainty protocol

Label every claim: **VERIFIED** (ran it, saw it), **DERIVED** (follows from cited text), **ASSUMED** (unconfirmed). Anything ASSUMED that touches PT0 or PT1 must be turned into VERIFIED or a Spec Query before the WP closes.

## 9. One-page card

| Area | Tier | Scale | If wrong | First response |
|---|---|---|---|---|
| Hash labels, constants | PT0 | – | FC3 | RB-1 |
| CTF-1, Unicode | PT0 | S0–S2 | FC3 | RB-1, RB-5 |
| Merkle, ids | PT0 | S0–S3 | FC3 | RB-1 |
| Manifest bytes | PT0 | S1 | FC3 | RB-1 |
| Manifest/envelope parsing | PT1 | S1 | FC3/FC4 | RB-1, RB-4 |
| Signatures, backends | PT0/PT1 | S1 | FC3/FC4 | RB-2 |
| Verification and report | PT1 | S1–S4 | FC4 | §4 |
| Key files, secrets | PT1 | S0 | FC4 | §4 |
| CLI, JSON, exit codes | PT2 | S0–S4 | FC2 | Fix, schema, changelog |
| Messages, layout | PT3 | – | FC0 | Fix |
