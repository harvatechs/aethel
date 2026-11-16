# decision-log.md — Decisions, Interpretations, Evidence

Three parts: **owner decisions** (you choose; defaults are safe), **accepted ADRs** (decided by this pack, with evidence), **interpretations** of places where the Yellow Paper is silent (tagged `[PACK]` in `specs.md`). The agent may not reverse an accepted ADR or change an interpretation without a new entry here and owner approval (R-PROC-03).

## Part 1 — Owner decisions

| ID | Question | Pack default | If you change it |
|---|---|---|---|
| OD-1 | Licences | Code: **Apache-2.0** (explicit patent grant suits cryptographic tooling). Documents: **CC-BY-4.0**. Test vectors: **CC0-1.0** | MIT is simpler but has no patent grant. Update `pyproject.toml`, `LICENSE`, headers |
| OD-2 | Names | PyPI `aethel-codex`; import `aethel_codex`; command `aethel`. **Reserve `aethel-codex` and `aethelcodex` on PyPI now** (upload a `0.0.0` placeholder or use an organisation) | `aethel` and the import name `aethel` are taken by an unrelated project (ADR-002). Do not use them |
| OD-3 | Version policy | Tool `0.1.0` for the MVP. `1.0.0` only after the Yellow Paper reaches 1.0.0 final and open items 14.3.1–14.3.4 close. A table in `CHANGELOG.md` maps tool versions to Yellow Paper versions | Calling it 1.0.0 now promises API stability while the profile is still a release candidate |
| OD-4 | Vulnerability reporting | GitHub private vulnerability reporting plus a `SECURITY.md` with a 90-day coordinated disclosure window | Provide an email and, if wanted, a PIP-1-signed contact statement |
| OD-5 | Key defaults | `keygen` makes an encrypted ML-DSA-87 key. `keygen --dual` also makes an SLH-DSA-SHA2-256s key. `publish --key` may be repeated. Dual-family is recommended, not forced [YP §9.5] | Forcing dual-family would exceed the paper's RECOMMENDED |
| OD-6 | Hosting | GitHub, GitHub Actions, PyPI Trusted Publishing, docs on Cloudflare Pages (already used for the site) | Equivalent CI elsewhere is fine if the gates in `testing-and-conformance.md` are kept |
| OD-7 | Upstreaming | Send the Q-xx clarifications and the SLH-DSA vectors to the Working Group; publish `pip1-vectors.json` at a permanent URL with its SHA-256 | Without this, other implementers cannot reuse the vectors |
| OD-8 | Site update | Move the landing page to rc.3; check the doubled `pip1:t:pip1:t:…` display in the hero and manifesto; link the repository and vectors when released | Site items are listed in `release-and-deployment.md` §6 |

## Part 2 — Accepted ADRs

**ADR-001 Runtime and build.** Python ≥ 3.11 (3.10 reached end of life in October 2026; 3.11 gives `tomllib`, `StrEnum`, `Self`). `src/` layout, `hatchling` build, `uv` with a lockfile for development. CI matrix: 3.11–3.14 on Linux, macOS, Windows. Pure-Python wheel; native code only from dependencies.

**ADR-002 Names.** *Evidence, 14 Nov 2026:* `aethel` on PyPI is an unrelated meta-package (0.1.0, repository `main-path/aethel`) whose wheel ships a top-level `aethel/` module. `aethel-codex`, `aethelcodex`, `pip1` and `permanent-ink` returned 404. *Decision:* distribution `aethel-codex`, import `aethel_codex`, command `aethel` (the other project ships no script of that name). `pip` is the Python installer, so the protocol prefix `pip1` is never a command name. *Consequence:* every install line says `aethel-codex`; docs warn against `pip install aethel`.

**ADR-003 Dependencies.** Exactly three at runtime: `cryptography>=50.0.2,<51`, `pqcrypto>=1.0.0,<2`, `unicodedata2>=18.0.0,<19`. CLI on `argparse`. Floors are the versions verified here; ceilings rise only after a "latest dependencies" CI job passes the full conformance suite. Dev-only: `pytest`, `hypothesis`, `pytest-cov`, `mypy`, `ruff`, `import-linter`, `jsonschema`, `build`, `twine`, `pip-audit`, `cyclonedx-bom`, oracles `dilithium-py==1.5.1` and `slh-dsa==0.2.5`. *Why so few:* a standard's reference tool must be easy to audit.

**ADR-004 Signature backends.** ML-DSA (`0x01`, `0x02`) through `cryptography`; SLH-DSA (`0x10`, `0x11`) through `pqcrypto`; behind the `SignatureBackend` protocol.

| Candidate | Finding on 14 Nov 2026 | Verdict |
|---|---|---|
| `cryptography` 50.0.2 | `mldsa` module: ML-DSA-44/65/87, `from_seed_bytes`, `private_bytes_raw` = 32-byte seed, context strings; no SLH-DSA; Windows wheels. Verified the paper's A.2 signature | **ML-DSA backend** |
| `pqcrypto` 1.0.0 (Apache-2.0, `backbone-hq/pqcrypto`) | ML-DSA and all SLH-DSA sets; context strings; `abi3` wheels for macOS, manylinux_2_34, musllinux, **Windows x64**; no seed export; hedged only; SLH-DSA-256s signing 0.7–1.6 s | **SLH-DSA backend**; documented fallback for ML-DSA |
| `dilithium-py` 1.5.1 | Pure Python, educational, deterministic option | **Test oracle only** |
| `slh-dsa` 0.2.5 | Pure Python FIPS 205, deterministic option | **Test oracle only** |
| `liboqs-python` 0.16.0.2 | At import without liboqs it tries to build it with `cmake`; failed with `FileNotFoundError: cmake` | **Rejected** |

*Interoperability evidence:* ML-DSA-87: the paper's signature verifies in `dilithium-py`, `cryptography` and `pqcrypto`; signatures from each verify in the others; wrong context, other role and tampering are rejected. SLH-DSA-SHA2-256s and -SHAKE-256s: oracle signatures verify in `pqcrypto` and the reverse. `pqcrypto`'s platform gap: no Linux armv7 or Windows ARM64 wheels, and manylinux_2_34 needs glibc ≥ 2.34. Document this under "Platform support".

**ADR-005 Unicode.** `unicodedata2` 18.0.0 (PyPI release 18 Sep 2026; Unicode 18.0.0 itself was released mid-September 2026), guarded at import; a generated repertoire table (`_repertoire.py`) with a drift canary; `NormalizationTest.txt` for 18.0.0 pinned by SHA-256 as a dev-time download. Stdlib `unicodedata` banned. *Consequence:* the tool's behaviour does not depend on the user's Python build.

**ADR-006 Merkle.** Streaming `TreeHasher` for hashing; recursive `merkle_root`, `audit_path`, `root_from_path` as the specification-form oracle; proofs for large blobs are built bottom-up and property-tested against the oracle.

**ADR-007 Parsers.** Hand-written strict parsers (no parser generators, no `json`/`yaml` for protocol objects), with the error precedence of `specs.md` §7 and a mandatory round-trip check.

**ADR-008 Bundle.** Adopt the informative layout of [YP §11.1] as the on-disk format. No archive format in the MVP: tar/zip packaging needs a protocol-level definition for byte-exactness. Parked.

**ADR-009 Time evidence.** Carry, store and report beacon and attestation items as "present, unverified". No fetching, no RFC 3161 or OpenTimestamps logic. When the Working Group registers a source or kind, a new WP implements it.

**ADR-010 Key files.** AKF-1 (non-protocol): `scrypt` n = 2¹⁷, r = 8, p = 1, ChaCha20-Poly1305 via `cryptography`; encrypted by default. *Evidence:* 0.52 s derivation; wrong passphrase and AAD tampering rejected.

**ADR-011 CLI contract.** `argparse`; stable exit codes; `--json` everywhere; `NO_COLOR` honoured; no configuration through environment variables or config files (fewer hidden inputs). Passphrases via TTY prompt or `--passphrase-file` only.

**ADR-012 Reports.** Separate statements; statuses PASS/WARN/FAIL/SKIPPED with reason codes; `SKIPPED:LIMIT_EXCEEDED` for hit limits.

**ADR-013 Dogfood and independence.** Ship `scripts/verify_minimal.py` (stdlib only, hash-integrity V1–V3, marks the Unicode repertoire check "not performed") as a second code path for differential tests and for hand-verification. The first work published with the tool is the manifesto text already shown on the site (its identifier `pip1:t:de93176d…fd4b` was reproduced).

**ADR-014 Self-test data.** `aethel selftest` runs from the two vector files shipped as package data, so a user can check an installation without the repository.

## Part 3 — Interpretations of silent or ambiguous points `[PACK]`

Each is also a clarification request for the Working Group (OD-7).

| ID | Yellow Paper text | Interpretation | Reason |
|---|---|---|---|
| Q-01 | §4.2 step 3 lists the forbidden and unassigned checks as two clauses | Check forbidden over the whole text first, then unassigned. A noncharacter reports `E_FORBIDDEN_CODEPOINT` | Property 1 demands one error code per input; matches the U+FDD0 vector |
| Q-02 | §6.3 treats `start >= end` as a range error; A.5 lists `#b=3-3` and `#b=5-3` as syntax errors | Reject at parse with `CITE_SYNTAX` | Both reject; one place is simpler |
| Q-03 | Manifest error names are given only for the eight A.3 mutations | Precedence and extra codes as in `specs.md` §7 | Deterministic, testable behaviour |
| Q-04 | §9.4 grammar admits both `role author` and `role 0x01`; no rule for a mismatched `manifest` field or duplicate envelopes | Accept both role spellings; mismatched manifest ⇒ `SIG_INVALID`; duplicates count once per (key, role); strict canonical Base64 | The envelope is unsigned, so equivalence must be explicit |
| Q-05 | §11.2 V5 "where parents are available… otherwise SKIPPED" | Genesis (no parents): `SKIPPED:NO_PARENTS` | Literal reading |
| Q-06 | V6 gives per-envelope failure codes only | Aggregate FAIL if any envelope fails; `SKIPPED:NO_SIGNATURES` if none | A visible failure beats a silent drop |
| Q-07 | §12.7 forbids PASS or FAIL for a limit-stopped check | `SKIPPED:LIMIT_EXCEEDED`, integrity `INCONCLUSIVE`, exit 6 | Fits the four-status vocabulary |
| Q-08 | §3.1 "padded standard Base64 for keys and signatures"; the envelope grammar `b64` does not force valid padding or length | Strict canonical Base64: `b64decode(validate=True)` and re-encoding must equal the input | Two spellings of one key or signature would give two spellings of one envelope |
| Q-09 | §7.4 "must not begin or end with a space" | U+0020 only | The grammar's `SP` |
| Q-10 | §11.1 layout is informative | Rules for symlinks, extra files and `text.*` naming in `specs.md` §10 | Safe handling of untrusted bundles |
| Q-11 | §12.7 "impose resource limits", no numbers | Defaults in `specs.md` §12 | Needed to be testable |
| Q-12 | §4.4: use Unicode data "18.0.0 or later", yet characters added later are rejected | The repertoire is exactly Unicode 18.0.0. Newer data would be acceptable only for NFC, which the stability policy makes safe. The tool pins 18.0.0 for both | Avoids accepting characters the profile rejects |
| Q-13 | §6.3 inline pattern "not followed by a hex digit" | Hex digit = `[0-9A-Fa-f]` | Conservative |
| Q-14 | ABNF `bval = 2*128(...)` does not force even length; prose says even | Enforce even length | Prose is the rule |
| Q-15 | §7.3 `text` length "MUST be at least 1"; the ABNF allows `0` | `E_BAD_VALUE` for `0` | Prose is the rule |
| Q-16 | §9.5 Dual-family depends on declared key algorithms, which a key id does not reveal | Take each key's algorithm from the envelope that verified it. Dual-family requires `m == n` so every key's algorithm is known | The only source |
| Q-17 | §3.4 roles `0x05–0x7F` are "assigned by the registry" | Verify and report them; never count them toward attribution | Forward compatible without trust |

## Part 4 — Source discrepancies to report

- Landing page: footer says rc.1 (paper is rc.3); hero and manifesto display `pip1:t:pip1:t:…`; resources marked SOON.
- The paper's reference implementation uses `dilithium-py` (see ADR-004) and does not parse the two envelope formats; the envelope behaviour here is therefore specified only by the grammar plus Q-04.
- The paper's open items 14.3.1–14.3.6 remain open; this pack's tool is a second, independently written Python implementation but does not by itself close item 1 (which asks for other languages).
