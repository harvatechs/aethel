# what-not-to-do.md — Forbidden Shortcuts and Traps

Every row below is a mistake that is easy to make, looks reasonable, and breaks the standard, the user's trust, or both. Read the whole file before writing code. Re-read §7 before reporting progress.

## 1. Protocol and Python traps

| # | Don't | Because | Do instead |
|---|---|---|---|
| 1 | `open(p)`, `Path.read_text()`, `write_text()` on manuscripts, manifests, envelopes or bundles | Text mode translates newlines and uses the locale encoding (cp1252 on many Windows setups). One changed byte is a different name | `read_bytes()`, `open(p, "rb")`, `open(p, "wb")` |
| 2 | `str.splitlines()` | Splits on U+2028, U+2029, U+0085, VT, FF, FS, GS, RS. CTF-1 recognises only CR LF and CR | `.replace("\r\n", "\n").replace("\r", "\n")`; for manifests `.split("\n")` |
| 3 | `.strip()`, `.isspace()`, `.lower()`, `.casefold()`, NFKC on protocol data | Changes what the author wrote, or accepts spaces the grammar forbids. "Space" in value text means U+0020 only | Explicit checks such as `v[:1] == " "` |
| 4 | `\d`, `$`, `re.match` | `\d` matches non-ASCII digits (`"٣"`); `$` matches before a final newline; `match` anchors only the start | `[0-9]`, `re.fullmatch` |
| 5 | `int(s)` to parse a number | Accepts `"+1"`, `" 1"`, `"1_0"`, `"٣"`, `"007"` | Full-match `0|[1-9][0-9]*` first, then `int`, then range-check 2⁶⁴−1 |
| 6 | `len(text)` for a byte limit | Counts code points, not bytes | `len(s.encode("utf-8"))` |
| 7 | `sorted(strings)` for manifest order | Correct for ASCII only by coincidence; the paper says byte order | Sort with `key=lambda s: s.encode("utf-8")` |
| 8 | Standard-library `unicodedata` | Python 3.12 ships Unicode 15.0.0; the profile pins 18.0.0 | `unicodedata2` with the import guard |
| 9 | Third-party Merkle libraries, duplicating the last node, padding odd levels | Different root. PIP-1 uses the RFC 6962 split rule with labels | `specs.md` §5 exactly |
| 10 | Chunking by characters or lines, or any size other than 4,096 bytes | Changes every identifier | `CHUNK_SIZE` bytes |
| 11 | Running CTF-1 on assets, or on the manifest | Assets are raw bytes. The manifest has its own strict grammar | CTF-1 only on manuscripts |
| 12 | Signing or hashing the *hex* of an identifier, or signing the text itself | The message is `u8(role) ‖` the raw 32-byte manifest digest | `bytes([role]) + digest` |
| 13 | A hash without `LP(label)`, or a 2-byte length | Breaks domain separation | `H(label, x)` only, from `hashing.py` |
| 14 | `datetime.now()`, `time.time()`, `platform.node()`, `getpass.getuser()`, `os.getcwd()` near any output | The protocol has no clocks and must not leak identity | Nothing. If you think you need one, you misread the spec |
| 15 | JSON, YAML or TOML manifests; pretty printing; trailing spaces; CRLF; missing final LF | The manifest has exactly one valid byte form | The strict serializer |
| 16 | Upper-case hex; `.lower()` on identifiers; case-insensitive comparison | Two spellings of one identifier defeat uniqueness | Reject upper-case |
| 17 | One boolean "valid"; treating WARN as PASS; treating `ASSET_EXTRA` as failure | [YP §11.3] forbids collapsing; extras are warnings | Separate summaries (`specs.md` §9) |
| 18 | Accepting unknown manifest keys "for forward compatibility" | There is no negotiation; new fields mean a new profile | `E_UNKNOWN_KEY` |
| 19 | Rejecting U+2028, U+2029, bidi controls, ZWJ/ZWNJ, private-use, U+FFFD; or accepting VT/FF | Accepted on purpose / forbidden on purpose [YP §4.3] | `is_forbidden()` from `specs.md` §3 |
| 20 | `errors="replace"`, `"ignore"`, `"surrogateescape"` | Silently changes bytes | Strict decoding, named errors |
| 21 | `os.path.join(bundle, name)` with a name from the manifest before validating it; following symlinks; overwriting bundle files | Path traversal; surprises | Validate with the asset-name grammar; `lstat`; atomic create |
| 22 | `except ValueError` around a `pqcrypto` call | `InvalidSignatureError` *is* a `ValueError`, so a length error and a bad signature blur together | Check lengths first; catch `pqcrypto.InvalidSignatureError` only |
| 23 | Passing the `PublicKey` wrapper to `pqcrypto.verify` | It expects raw `bytes` | `bytes(pk)` |
| 24 | Regexes with nested quantifiers on untrusted input | Catastrophic backtracking | The linear patterns in `specs.md` |
| 25 | Unordered `json.dumps` for reports | Unstable output breaks diffing and trust | Build reports with the schema's key order |

## 2. Scope: do not build these

PIP-1 and this MVP exclude the following. The Yellow Paper (§1.3) assigns them to consumers of its identifiers.

- Blockchains, tokens, smart contracts, endowment pools, royalty routing, wallets.
- IPFS, Arweave or any storage client; erasure coding or sharding of stored bytes.
- Curator guilds, the Canon, governance, the Constitution, reputation tokens.
- Zero-knowledge or anonymous pen names. A pseudonym is a fresh key with no declared link to a person.
- Quantum random number generators, verifiable delay functions, "arrow of time" proofs. PIP-1 replaced them with a committed beacon value and an external attestation, and **this MVP fetches neither**: no beacon source and no attestation kind is registered.
- Verifying RFC 3161 or OpenTimestamps proofs (PIP-1 defines no procedure), fetching `drand` or `nist-beacon`.
- Dead-man switches, estates, encrypted drafts (would need ML-KEM, outside this document).
- A reader app, GUI, web server, daemon, accounts, login, sync.
- Telemetry, analytics, update checks, crash reporters, auto-update. The project's own site promises "No cookies. No analytics."
- Plugin systems, config files beyond flags, databases, caches that outlive a command.

New ideas go to `docs/roadmap-parking-lot.md`, not into the code.

## 3. Cryptography traps

- Importing `dilithium-py` or `slh-dsa` from `src/`. They are pure-Python test oracles, not constant-time.
- Using `liboqs-python`. On 14 Nov 2026 importing it without a prebuilt liboqs tried to build it with `cmake` and failed. A tool must never compile code at import.
- Pre-standard SPHINCS+/Dilithium packages (`pyspx` and similar); the final standards are not interoperable with them [YP §2.4].
- Hand-writing ML-DSA, SLH-DSA, NFC, AEAD or a KDF.
- Deterministic signing in `src/`. Hedged is the default [YP §9.2]; deterministic exists only in test oracles.
- Calling `sign` or `verify` without the `pip1.sig` context; using `hash_algorithm` (pre-hash variants).
- ML-DSA-44, Falcon/FN-DSA, RSA, ECDSA, EdDSA, or any `alg_id` outside the table.
- Accepting a public key of the wrong length, or skipping the key-id check.
- Counting a signature as "author" when its key is not declared in the manifest, or when its role is not `0x01`.
- Storing a secret unencrypted by default; logging, printing or `repr`-ing a secret; passing a passphrase on the command line or in the environment.

## 4. Banned claims (R-HON-01)

A test scans help text, messages and shipped docs for the left column.

| Never say | Why | Say instead |
|---|---|---|
| "proves you wrote it", "proof of authorship" | A signature proves a key signed. Anyone can copy a text and sign it first | "a valid signature shows the holder of key `pip1:k:…` approved this exact manifest as author" |
| "proves when you had the idea", "timestamped authorship" | Time evidence bounds when exact bytes existed | "time evidence bounds when these exact bytes existed" (the MVP produces none) |
| "permanent", "can't be deleted", "immutable" (as a promise about availability) | The hash layer makes tampering evident; keeping copies is storage's job | "a change is detectable; this tool does not store or keep copies" |
| "tamper-proof", "unalterable" | Wrong word | "tamper-evident" |
| "quantum-proof", "quantum-safe", "unbreakable" | Overclaim | "uses the NIST post-quantum signature standards FIPS 204 and FIPS 205" |
| "secure", "trusted" (bare) | Says nothing checkable | State the property |
| "verified author", "verified identity" | PIP-1 cannot say who holds a key | "signature valid for key …; PIP-1 cannot say who holds the key" |
| "blockchain", "decentralized storage", "immutable ledger", "Web3" | Not part of PIP-1 | Omit |
| "anonymous", "private", "confidential" | PIP-1 has no anonymity or confidentiality | "no anonymity or confidentiality in PIP-1" |
| "valid" / "invalid" for a whole bundle | Collapses separate statements | "Integrity PASS · Attribution: Attributed (2 of 2)" |
| "production-ready", "military-grade", "revolutionary", "unhackable" | Marketing | Omit; let the evidence speak |

## 5. Process traps (how AI-built projects go wrong)

- Editing, regenerating or "correcting" a vector; deleting or weakening a failing test; adding `skip`/`xfail`; lowering a threshold; `# pragma: no cover` on protocol paths; `# noqa` or `# type: ignore` without a reason.
- Writing a test that snapshots the implementation's output instead of the specification's.
- Catch-all `except`; returning success to look friendly.
- **Hallucinated APIs.** Before relying on any third-party call you have not run, run a three-line probe and paste it in the work log.
- Inventing CLI flags, error codes, JSON fields, file names or environment variables that are not in `cli-spec.md` or `specs.md`.
- "Simplified for now", "in a real implementation", "placeholder", `...` in code, commented-out code, dead code, unused parameters.
- Large mixed commits; reformatting unrelated files; casual renames of public names.
- Moving on while CI is red; "works on my machine".
- Adding dependencies for convenience (`rich`, `click`, `typer`, `pydantic`, `attrs`, `requests`).
- Premature abstraction: plugin frameworks, registries or base classes beyond `specs.md`.
- Unpinned installs in CI; network access in tests.
- Documenting features that are not built.
- Silent scope growth. Park it.

## 6. UX and packaging traps

- Prompting in pipelines. The only prompt is a passphrase on a TTY, and `--passphrase-file` always works.
- Spinners or progress on stdout; ANSI codes when not a TTY or when `NO_COLOR` is set.
- Changing exit codes or JSON shapes casually (they are contracts).
- Chatty success output. A success is one or two lines.
- Stack traces by default.
- **Package name.** Never publish, document or import `aethel`: that PyPI name and import package belong to an unrelated project. Use `aethel-codex`, `aethel_codex`; the command is `aethel`. Every install instruction says `pip install aethel-codex` (or `pipx` / `uv tool install`).
- Shipping `tests/` or fixtures in the wheel. Only the two vector JSON files ship, as package data for `aethel selftest`.
- `setup.py` or `requirements.txt` as the source of truth; editable installs in a release; the version written in more than one place.

## 7. Red-flag self-check before you say "done"

Answer every line honestly. A "no" means you are not done.

1. Did I run `make check` and `make conformance`, and can I paste the output?
2. Is every vector, fixture and negative test green without any edit to `tests/vectors/` or `tests/fixtures/`?
3. Does every new public function cite its Yellow Paper section and have reject-path tests?
4. Did I read files in binary and never touch the clock, the locale or the network?
5. Did I run each third-party call at least once in this session?
6. Is every message, flag, code and field in `cli-spec.md` / `specs.md`, with nothing invented?
7. Did I avoid every banned claim in §4 and every placeholder in R-HON-04?
8. Did I add or change a decision? Is it in `decision-log.md`?
9. Did the reviewer prompt (R) find nothing I ignored?
10. Would I be comfortable if a cryptographer read this diff line by line?
