# Aethel Codex — Build Pack for the `aethel` CLI

**Pack 1.0 · prepared 14 November 2026 · implements Yellow Paper PIP-YP-1 v1.0.0-rc.3 (profile `pip-1`)**

This pack tells an AI coding agent, or a human team, exactly how to build **`aethel`**: a clean, offline-first Python command-line tool and library that gives a piece of writing a name made from the writing itself, signs it with post-quantum signatures, and verifies it with nothing but the files.

It is written to prevent the usual failure of AI-built projects: plausible code that quietly deviates from the standard. Every protocol rule traces to the Yellow Paper. Every claim in this pack that could be checked was checked on 14 November 2026 (see "What was verified").

## What you are building

| | |
|---|---|
| Distribution / import / command | `aethel-codex` (PyPI) · `aethel_codex` (import) · `aethel` (command) |
| Runtime | Python ≥ 3.11 on Linux, macOS, Windows. Pure-Python wheel; compiled code comes only from three vetted dependencies |
| Conformance roles of PIP-1 | Canonicalizer (CTF-1), Manifest producer (PMF-1), Signer (ML-DSA, SLH-DSA), Verifier (V1–V8) |
| Behaviour | Offline always. No account, no network, no telemetry, no clock. Plain-text formats a future reader can decode |
| Core commands (P0) | `canon` `id` `keygen` `publish` `sign` `verify` `inspect` `selftest` `explain` `--version` |
| Next commands (P1) | `revise` `cite` `proof` `attest` |
| Not in this MVP | Blockchain, tokens, storage networks, curation, zero-knowledge identity, quantum random beacons. The Yellow Paper itself puts all of these out of scope of PIP-1 |

## How to use this pack (owner, 10 minutes)

1. Create the repository. Copy this pack in as-is: `AGENTS.md`, `.gitattributes`, `docs/`, `tests/` and `tools/` at the repository root.
2. Read `docs/decision-log.md`, section "Owner decisions". Each has a safe default. Change only what you disagree with.
3. Reserve the package names now (see "Needs your attention", item 1).
4. Start your agent and paste the kickoff prompt from `docs/prompts.md`.
5. Accept each work package only with its gate evidence (`docs/division-of-work.md`). Do not accept "done" without command output.

## File map

| File | Purpose | Read when |
|---|---|---|
| `AGENTS.md` | One-page constitution the agent loads first | Always |
| `docs/rules.md` | Numbered hard rules (R-…) with how each is checked | Always |
| `docs/what-not-to-do.md` | Forbidden shortcuts, Python traps, banned claims | Always |
| `docs/intent.md` | Why this exists, voice, quality bar, scope boundary | Before design decisions |
| `docs/user-requirements.md` | Personas, requirements (UR-…), acceptance criteria | Before each WP |
| `docs/specs.md` | The implementation spec: algorithms, grammar, verification, formats | While coding any protocol code |
| `docs/architecture.md` | Layout, layering, public API, backend contract | While structuring code |
| `docs/cli-spec.md` | Every command, flag, output, JSON schema, exit code | While building the CLI |
| `docs/testing-and-conformance.md` | Test layers, vectors, fixtures, tamper matrix, CI gates | While writing tests |
| `docs/division-of-work.md` | Work packages, dependencies, gates, roles, hand-offs | Planning and reporting |
| `docs/precision-scale-index.md` | Precision tiers, scale bands, failure classes, recovery playbooks | When anything goes wrong |
| `docs/skills.md` | Skills the agent must apply, each with a procedure | When starting a new kind of task |
| `docs/guidelines.md` | Style, naming, messages, commits, reviews | Always while coding |
| `docs/security.md` | Threat model, key handling, supply chain | WP-06, WP-08, WP-13, WP-14 |
| `docs/release-and-deployment.md` | Packaging, CI, release ritual, site updates | WP-14 onward |
| `docs/decision-log.md` | Accepted decisions, spec interpretations, owner decisions | Always (before deviating) |
| `docs/prompts.md` | Ready-to-paste prompts and report templates | Operating the agent |
| `docs/yellow-paper/PIP-YP-1_v1.0.0-rc.3.pdf` | The normative source | Whenever in doubt |
| `tests/vectors/pip1-vectors.json` | Yellow Paper vectors plus pack-generated regression data | WP-01 onward |
| `tests/vectors/pip1-slh-dsa-vectors.json` | SLH-DSA verify vectors (pack-generated) | WP-06 |
| `tests/fixtures/` | Five golden bundles with `expected.json` verdicts | WP-07 onward |
| `tests/README.md` | Provenance of every data file and how to regenerate | When touching test data |
| `tools/recompute_yp_vectors.py` | Recomputes every Yellow Paper value independently (audit script) | RB-1, RB-13 |
| `tools/gen_pack_data.py` | Regenerates pack data (guarded; Spec Guardian only) | Rarely |
| `.gitattributes` | Stops Git rewriting test bytes | WP-00 |
| `docs/work-log/ queries/ reviews/ incidents/` | Where the agent's evidence, questions, reviews and incident notes accumulate | Every WP |

## Source-of-truth order

1. **Yellow Paper PDF** (normative).
2. **`tests/vectors/`** (oracles; see `rules.md` R-PROTO-02).
3. **`docs/specs.md`** (derived guide; if it disagrees with 1, report it and follow 1).
4. **`docs/decision-log.md`** (resolutions where the Yellow Paper is silent, each flagged `[PACK]`).
5. Everything else.

## What was verified while preparing this pack (14 Nov 2026)

| Check | Result |
|---|---|
| Every Yellow Paper vector (T1–T4, 12 CTF-1 negatives, both manifests, 8 manifest mutations, locator table, key id, signature digest) recomputed from first principles | All reproduce exactly |
| The ML-DSA-87 signature from Appendix A.2 | Verified by three independent libraries: `dilithium-py` 1.5.1, `cryptography` 50.0.2, `pqcrypto` 1.0.0 |
| SLH-DSA-SHA2-256s and SHAKE-256s | `pqcrypto` 1.0.0 and the independent pure-Python `slh-dsa` 0.2.5 verify each other's signatures, with context `pip1.sig` |
| `unicodedata2` 18.0.0 | Installable with wheels; `unidata_version == "18.0.0"`. Python 3.12's own `unicodedata` is **15.0.0** |
| Streaming Merkle tree, audit paths, strict manifest parser, citation locators | Prototyped and tested against the paper's tables |
| Landing-page vectors (`aethel-codex.pages.dev`) | Both reproduce, including the 834-byte manifesto |
| Golden bundles | Five fixtures verified by an independent mini-verifier |

## Needs your attention

1. **PyPI name collision.** `aethel` is already registered by an unrelated project that ships a top-level module `aethel`. This pack therefore uses `aethel-codex` / `aethel_codex`. At the time of checking, `aethel-codex`, `aethelcodex`, `pip1` and `permanent-ink` were unregistered. Reserve them. Tell users to install `aethel-codex`, never `aethel`.
2. **The paper's reference implementation is not production crypto.** It uses `dilithium-py`, an educational pure-Python library. The Yellow Paper (§12.7) itself asks for maintained, constant-time implementations. This pack's backend plan: `cryptography` for ML-DSA, `pqcrypto` for SLH-DSA, and the two pure-Python libraries as test oracles only.
3. **Landing page drift.** The site says rc.1 while the paper is rc.3, and two identifiers display with a doubled prefix (`pip1:t:pip1:t:…`). Check whether that is a rendering issue. The release plan lists the site updates.
4. **Where the paper is silent**, this pack made explicit choices, each tagged `[PACK]` in `docs/decision-log.md`. Send them to the Working Group as clarification requests.

## Glossary

**CTF-1** canonical text form. **PID** PIP identifier such as `pip1:t:<64 hex>`. **Blob** canonical text or asset bytes. **Manifest (PMF-1)** the plain-text record that binds text, assets, citations, history and authors. **Bundle** a directory holding a manifest, text, assets, signatures, attestations. **Envelope** a detached signature (SGE-1) or attestation (ATT-1) file. **Profile** the fixed algorithm set; here `pip-1`. **YP** the Yellow Paper. **WP** work package. **ADR** architecture decision record. **OD** owner decision. **PT / FC** precision tier / failure class (see `precision-scale-index.md`).
