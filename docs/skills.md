# skills.md — Skills the Builder Must Apply

Each skill is self-contained: a trigger, a procedure, a "done when" and the pitfalls seen in this domain. If your tooling supports skill files, split each `###` section into `.claude/skills/<name>/SKILL.md` (use the `name` and "Use when" line as front matter). Otherwise treat this file as a checklist library. The skill to start a task with is named in the WP table of `division-of-work.md`.

### SKILL-01 `byte-exact-protocol-implementation`
**Use when** coding anything in PT0 (`precision-scale-index.md`).
1. Quote the Yellow Paper clause. Write it as a comment-free test using the matching vector before any implementation.
2. Compute the vector's expected value **independently** with plain `hashlib` and a few lines of code. If you cannot reproduce it, you misread the spec: stop (RB-1).
3. Implement the smallest function that passes. Keep it pure: bytes in, bytes out.
4. Add property tests for the invariant (fixed point, equivalence, round trip).
5. Add reject-path tests.
**Done when** vectors pass, branch coverage is 100 %, and a second reader could re-derive every constant from the paper.
**Pitfalls** text-mode I/O; hashing hex instead of bytes; forgetting the label length prefix; trusting memory of "how Merkle trees work".

### SKILL-02 `unicode-handling`
**Use when** touching `unicode18`, `ctf1`, value text, or anything printed.
1. Never import `unicodedata`. Use `unicodedata2` behind the guard (`specs.md` §3).
2. Generate `_repertoire.py` with the tool, never by hand; keep the sweep test and canary.
3. Decode strictly, check forbidden then unassigned, then normalise line endings, then NFC, then the final LF.
4. Report offsets, code points, line and column in diagnostics.
5. Run the full `NormalizationTest.txt` for 18.0.0.
**Done when** T1, T2, 12 negatives, fixed-point property and the Unicode conformance file all pass on all OSes.
**Pitfalls** `splitlines`; accepting or rejecting the wrong characters (U+2028 is accepted, VT and FF are forbidden); `len()` for bytes.

### SKILL-03 `merkle-and-proofs`
**Use when** writing `merkle.py` or `proof.py`.
1. Write the recursive `merkle_root`, `audit_path` and `root_from_path` first: they are the specification and the test oracle.
2. Write the streaming `TreeHasher` and prove it equal to the oracle for many sizes and irregular feed slices.
3. Add the length-aware verification procedure of YP §5.4 with every rejection branch.
4. For large blobs, build proofs bottom-up from a leaf list and compare with the oracle.
**Done when** T3's leaves, node, root and audit paths match, all `blob_sizes` match, and forged proofs fail.
**Pitfalls** duplicating the last node; chunking by characters; forgetting `u64be(length)` in the blob id.

### SKILL-04 `strict-parsing`
**Use when** writing `manifest.py`, `envelope.py`, `citations.py`, `pid.py`, `keyfile.py`.
1. Write the field table first (key, count, grammar, order rank). Parse by field, never with one giant regex.
2. Use `fullmatch` with `[0-9]`, never `\d`, `$` or `int()` alone.
3. Implement the error precedence of `specs.md` §7 so one input yields one code.
4. Re-serialise and compare bytes. Test that check by injecting a faulty serializer.
5. Property test: a one-byte mutation is rejected or re-serialises to exactly the mutated bytes.
**Done when** every positive and negative vector passes and the fuzz run finds nothing.
**Pitfalls** lenient modes; ignoring unknown keys; sorting by `str` instead of bytes; `.strip()`.

### SKILL-05 `pq-signature-integration`
**Use when** writing `backends/` and `signing.py`.
1. Probe each library call in a scratch script and paste the output in the work log (names, argument order, exceptions). Known facts are in `specs.md` §8; verify them still hold.
2. Wrap each library behind the `SignatureBackend` protocol. Check exact key and signature lengths first.
3. Always pass the context `pip1.sig`. Sign `u8(role) ‖ raw digest`. Hedged signing only.
4. Verify the paper's A.2 signature. Cross-check with the oracles in tests.
5. Make `sign_manifest` verify its own result and fail closed.
**Done when** A.2, the ML-DSA-65 vector and both SLH-DSA vectors verify, every negative fails, and a deliberately broken backend is caught.
**Pitfalls** `InvalidSignatureError` being a `ValueError`; passing wrapper objects; using the pre-hash parameter; importing oracles from `src/`.

### SKILL-06 `verification-reporting`
**Use when** writing `verify.py` and `report.py`.
1. Implement each check as a function returning a `CheckResult`; run every check its inputs allow.
2. Use the statuses and reason codes of `specs.md` §9 exactly. A hit limit is `SKIPPED:LIMIT_EXCEEDED`.
3. Compute integrity, attribution, history and time separately. Never output one "valid".
4. Include the standing notes (what a signature does and does not show).
**Done when** the five fixtures match `expected.json` and the tamper matrix holds.
**Pitfalls** treating WARN as PASS; letting a V6 failure change integrity; counting undeclared or non-author signatures.

### SKILL-07 `secure-key-and-file-handling`
**Use when** writing `keyfile.py`, `bundle.py`, `publish.py`.
1. Create secrets with `O_EXCL` and mode `0600`. Refuse wider modes on load (POSIX).
2. Encrypt with scrypt (n = 2¹⁷, r = 8, p = 1) and ChaCha20-Poly1305, AAD = the header bytes.
3. Never place a secret in argv, environment, logs, `repr` or exceptions. Wipe on a best-effort basis and say so.
4. Write bundles atomically (temp directory, `fsync`, rename). `lstat` everything you read; never follow symlinks.
**Done when** the security tests of `testing-and-conformance.md` §7 pass.
**Pitfalls** passphrases on the command line; overwriting files; trusting names from a manifest as paths.

### SKILL-08 `cli-craft`
**Use when** building `cli/`.
1. Build the parser from `cli-spec.md`; one module per command; no logic in the parser.
2. Keep stdout for results, stderr for everything else. `--json` means exactly one document on stdout.
3. Map exceptions to exit codes in one place. Render messages in one module.
4. Sanitise untrusted text for terminals. Honour `NO_COLOR` and non-TTY.
5. Import heavy libraries lazily.
**Done when** the CLI contract tests pass and `--version` imports no crypto library.
**Pitfalls** prompts in pipelines; progress on stdout; stack traces by default; inventing flags.

### SKILL-09 `test-design`
**Use when** writing any test.
1. Start from the vector or the negative case. Make the test name a sentence.
2. Prefer properties for invariants and a tiny independent model for oracles.
3. Test the reject path first.
4. Mark requirement IDs. Keep tests deterministic.
5. Never snapshot your own output as truth, except the reviewed golden help text.
**Done when** the traceability script is green and the tamper matrix passes.

### SKILL-10 `python-packaging-and-release`
**Use when** in WP-00 and WP-15.
1. `src/` layout, `hatchling`, one version source, package data for `schemas/*.json` and `data/*.json`.
2. Lockfile with hashes for releases; `pip-audit`; SBOM.
3. Build in CI, install the built wheel into a clean environment on each OS and run `selftest` plus a fixture verification.
4. Publish with Trusted Publishing; never store a PyPI token.
**Pitfalls** editable installs in release checks; the wrong distribution name; shipping `tests/`.

### SKILL-11 `spec-ambiguity-resolution`
**Use when** the paper is silent, vague, contradictory, or seems wrong.
1. Quote the clauses. List the readings. Check `decision-log.md` first.
2. Write a Spec Query (`prompts.md` template Q). Continue only independent work.
3. After the answer, record an ADR or interpretation and update `specs.md` and tests in one change.
**Pitfalls** choosing silently; changing a vector; "everyone does it this way".

### SKILL-12 `honest-technical-writing`
**Use when** writing help text, docs, README, error messages, commit messages.
1. Claim only what the paper claims (§2.3). Use the approved phrases in `guidelines.md` §6.
2. Every example command is executed in CI and its output pasted from reality.
3. Calm voice: say what happened, why, what next.
**Pitfalls** "proves", "permanent", "quantum-proof"; documenting unbuilt features.

### SKILL-13 `adversarial-review`
**Use when** you are the reviewer (prompt R) or reviewing your own diff.
1. Read `what-not-to-do.md` §1–§5 and attack the diff against each line.
2. Try to make `verify` say PASS for something wrong: flip bits, reorder lines, swap envelopes, rename directories, add symlinks.
3. Search for secrets in output, invented flags, placeholders, unlabelled assumptions.
4. Write findings with severity FC0–FC4 and the exact reproducer.
**Done when** the report is filed in `docs/reviews/` and every FC2+ finding is closed.

### SKILL-14 `evidence-and-hygiene`
**Use when** always.
1. Probe before you rely: run any unfamiliar API in three lines and read the output.
2. Small steps, each ending green.
3. Paste commands and outputs, label claims VERIFIED, DERIVED or ASSUMED.
4. Three strikes, then stop (R-PROC-04).
5. When context is lost, re-read `AGENTS.md`, the latest work log and the open queries before continuing (prompt C).
