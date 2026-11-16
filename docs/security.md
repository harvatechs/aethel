# security.md — Threat Model and Controls

## 1. What we protect

1. **The truth of every verdict.** `verify` must never say PASS for something altered. (FC4 if it does.)
2. **Signing keys.** A leaked secret lets someone sign as you; PIP-1 has no revocation (Yellow Paper §9.6).
3. **The user's terminal and filesystem** while processing hostile bundles.
4. **Honesty of output.** Overclaiming is a security defect: people rely on what the tool says.
5. **The tool's own supply chain.**

Not protected, by design: confidentiality of manuscripts (they are public), availability of copies, anonymity (all excluded by Yellow Paper §2.3).

## 2. Threat model

| Adversary | Capability | Mitigation | Residual |
|---|---|---|---|
| Editor, substitutor, forger, confuser, future cryptanalyst [YP §2.1] | Alter bytes, swap content, forge signatures, exploit ambiguity | The protocol: content addressing, strict grammar, domain separation, ML-DSA/SLH-DSA | SHA3-256 collision; broken lattice or hash assumptions; renewal path [YP §13.3] |
| Hostile bundle author | Crafted files to crash, exhaust, or escape the tool | Limits, strict parsers, `lstat`, name grammar, sanitised output, linear regexes, typed errors | Unknown bugs; fuzzing narrows it |
| Other local user | Reads key files, watches process list | `0600` files, scrypt + ChaCha20-Poly1305, passphrase never in argv or environment | Root, malware, memory scraping |
| Lookalike author | Visually identical titles, bidirectional "Trojan Source" text, invisible tag characters [YP §12.6] | Human output escapes controls, bidirectional and tag characters; a `warning:` is printed when a title or licence contains them | Humans can still be fooled by homoglyphs; UTS #39 checks are P2 (`lint`) |
| Supply-chain attacker | Malicious or compromised dependency or release | Three runtime dependencies, hash-pinned lockfile, `pip-audit`, SBOM, Trusted Publishing, pinned CI actions | A compromised upstream release before detection |
| Network attacker | – | There is no network code | None |
| Side-channel or fault attacker on the signing machine | Timing, power, fault injection | Vetted constant-time backends; hedged signing by default [YP §9.2, §12.3] | Outside the paper's own model |

## 3. Controls (each maps to a rule)

| Control | Rule |
|---|---|
| Final-standard post-quantum signatures only, pure variants, context `pip1.sig` | R-PROTO-10 |
| No network code; tested | R-PROTO-11 |
| Strict parsers, no repair; round trip | R-PROTO-06 |
| Self-verify every signature before release | R-SEC-02 |
| Key files `O_EXCL`, `0600`, refused if wider; encrypted by default | R-SEC-01 |
| Terminal sanitisation of untrusted text | R-SEC-03 |
| No symlink following, regular files only, validated names, limits | R-SEC-04 |
| No `eval`, `exec`, `pickle`, `shell=True`, unsafe YAML; Ruff `S` rules | R-SEC-04 |
| No homemade ML-DSA, SLH-DSA, NFC, AEAD, KDF | R-SEC-06 |
| Hash-pinned lockfile, audit, SBOM | R-SEC-07, R-DEP-01 |
| Banned claims | R-HON-01 |

## 4. Key handling

- **Generation:** the backend's CSPRNG. ML-DSA keeps a 32-byte seed; SLH-DSA a 128-byte secret key. Never `random`.
- **Storage:** AKF-1 (`specs.md` §13). Default is encrypted. `--no-passphrase` exists for automation and prints a warning that anyone who reads the file can sign as the key.
- **Passphrase input:** TTY prompt with echo off, entered twice on creation; or `--passphrase-file` (mode must be `0600` on POSIX; one trailing newline is removed, nothing else). Never argv, never environment. NFC-normalise before the KDF so a passphrase typed on different systems derives the same key.
- **In memory:** hold secrets in `bytearray`, overwrite on release, drop references promptly. Python cannot guarantee erasure; the docs say "best effort" and never promise more.
- **Backup:** copy the encrypted `.aek` file to offline storage. The MVP does not export raw seeds.
- **Rotation and compromise:** PIP-1 has no revocation. A signature is a statement about the past. Obtain an attestation at publication time so a signature predating a compromise stays credible [YP §9.6, §10]. Key succession is an ordinary work signed by the old key that declares the new one; PIP-1 gives it no special meaning.

## 5. Handling untrusted input

Order for any file: `lstat` (regular file only) → size check against the limit **before reading** → read bytes → decode strictly → parse strictly → validate semantics. Never recurse on input structure. Never build a path from an unvalidated name. Treat every string from a bundle as hostile when printing. A limit hit is reported, not swallowed. Regexes are linear (see `specs.md`); the ReDoS guard test must stay green.

## 6. Supply chain

- Runtime dependencies are exactly `cryptography`, `pqcrypto`, `unicodedata2` (ADR-003). `pqcrypto` is Apache-2.0 with `abi3` wheels, no compilation on install. Re-check platform coverage and licences at each release.
- Development: `uv` lockfile; release builds install with `--require-hashes`. `pip-audit` on every pull request and nightly.
- CI: GitHub Actions pinned to commit SHAs; `permissions: contents: read` by default; no secrets in pull-request jobs; branch protection with required checks; two-factor authentication for all maintainers.
- Release: Trusted Publishing to PyPI (OIDC), **no long-lived token anywhere**; signed git tags; wheel, sdist, CycloneDX SBOM and `SHA256SUMS` attached to the GitHub release; the build is repeated and the artifacts compared.
- Updates: Dependabot or Renovate pull requests run the full conformance suite; a new major version needs an ADR.
- The project signs its own releases with its own protocol (ADR-013): the changelog text is published as a PIP-1 bundle signed with an offline, dual-family project key. The key never enters CI.

## 7. Vulnerability disclosure (`SECURITY.md`)

Scope: the package, the CLI and the build pipeline. Report through GitHub private vulnerability reporting (OD-4). Acknowledge within 72 hours; plan within 14 days; coordinated disclosure within 90 days, sooner when a fix ships. Supported versions: the latest release. Good-faith research is welcome. Anything that can make `verify` accept a bad bundle, leak a secret, or touch the network is treated as FC4.

## 8. Release security checklist (WP-15, WP-17)

1. All FC3 and FC4 items closed; reviewer report attached.
2. `tests/security/` green on all OSes; no network, no secrets in any stream.
3. Tamper matrix green; fuzz clean for 30 minutes.
4. `pip-audit` clean; lockfile hashes verified; SBOM generated.
5. Build repeated; artifacts identical.
6. Wheel installed in a clean environment per OS; `aethel selftest` and a fixture verification pass.
7. Trusted Publishing configured; no tokens in repository or CI settings.
8. `SECURITY.md` present; contact tested.
9. README and help text pass the banned-claim audit.
10. Key-file behaviour verified on POSIX (modes) and on Windows (documented limits).
11. `--version` and `selftest` show the exact dependency versions released.
12. `docs/conformance-report.md` states what remains unproven (independent review, other-language implementations, NIST validation data).
