# intent.md — Why This Exists and What "Good" Means

Read this before making any design decision the other documents do not settle.

## 1. The idea

A book on a shelf needs no server, no subscription and no one's permission. Writing on the internet needs all three, so it disappears: the host closes, the text is quietly edited, the link stops working, the proof of who wrote it goes with the company that held it.

The Permanent Ink Protocol answers part of that, precisely. It gives every piece of writing **a name made from the writing itself**; change one comma and the name changes. Citations point at names, so they cannot be quietly redirected. A signature binds a key to an exact manifest in a stated role, using the NIST post-quantum signature standards. Anyone can check all of it **offline, from the files alone**.

`aethel` is the tool that makes this usable: the first complete, open implementation of every conformance role of profile `pip-1`, as a command-line tool and a library.

## 2. The promise, and its honest edge

The project's own words set the bar: *we do not promise that a text will never be lost; we promise something smaller, and true: if you hold the words, you can prove they are the words.* The tool must never promise more than that.

It therefore does **not** claim to prove who wrote a text, who had an idea first, that a copy exists anywhere, or that anything is anonymous or confidential (Yellow Paper §2.3). It says so in its output, every time it matters.

## 3. Principles (from the paper, applied to the tool)

| Principle | In the tool |
|---|---|
| Hash the source, never the rendering | Only Markdown, LaTeX and plain text are manuscripts; assets are raw bytes |
| Canonicalise encoding, never authorship | CTF-1 fixes bytes, never words; the tool never "cleans" text silently |
| Self-describing, domain-separated identifiers | Every identifier carries its type; every hash has a label |
| Fixed algorithms per profile | No flags to choose hashes; no negotiation; an unknown profile is reported, not guessed |
| No self-asserted clocks | The tool writes no dates and never reads the clock into output |
| Standard primitives only | No novel cryptography; vetted libraries only |
| Everything checks offline | No network code exists in the package |
| Text is the primary artifact | Manifests, envelopes and key files are plain UTF-8 lines a person can read |

Added for the tool: **small** (three runtime dependencies), **explicit** (nothing permanent is guessed), **boring** (standard library first, no cleverness in protocol code), **auditable** (typed, tested, layered, traceable to the paper).

## 4. Voice

Calm, exact, plain. The site says "We would rather tell you now." Do the same: state limits before being asked. No emoji, no exclamation marks, no hype, no metaphors in error messages. A message names the problem, why it matters, and what to do next. When the tool cannot know something, it says "not checked" or "not shown", never "OK".

## 5. What "world-class" means here

1. **Bit-exact.** Every vector in the paper reproduces; every negative input is rejected.
2. **Honest.** Reports separate integrity, attribution, history and time. Nothing is overclaimed. Limits are shown.
3. **Boring to install and to run.** `pipx install aethel-codex` works on Linux, macOS and Windows with no compiler. The first publish takes five minutes.
4. **Hard to misuse.** Keys are encrypted by default. Overwrites are refused. Signatures are self-verified. Inputs are validated, never repaired.
5. **Auditable.** A cryptographer can read the code in an afternoon: pure core, thin shell, one rule per module, every function citing its paper section.
6. **Reproducible.** Same inputs, same bytes, anywhere, any year.
7. **Survivable.** If this tool disappears, the paper and a stdlib script (`verify_minimal.py`) are enough to verify what it made.

## 6. Decision heuristics for the builder

1. If it is not in the paper or the requirements, do not build it.
2. Choose the option a stranger could verify with the paper alone.
3. Choose the smaller design. Delete before you add.
4. Choose explicit over convenient when the result becomes permanent (titles, licences, languages).
5. If an output would say more than the paper says, say less.
6. If two readings of the paper both seem fine, you have found a Spec Query, not a choice.
7. If you are tempted to edit a test or a vector, the code is wrong.

## 7. Scope boundary

**In the MVP:** the four conformance roles, key files, bundles, the CLI of `cli-spec.md`, the library API, documentation, packaging, CI, release engineering.

**Not in the MVP** (the paper assigns these to consumers of its identifiers): storage and incentives, curation and governance, zero-knowledge identity, quantum random beacons, readers and indexes.

## 8. After the MVP (for the owner; do not build)

These belong in `docs/roadmap-parking-lot.md`, in rough order of value:

- Registered **beacon sources** and **attestation kinds** (OpenTimestamps, RFC 3161, a public randomness network) once the Working Group names verification procedures; then V8 can report "verified".
- **Independent implementations** in other languages and a **browser verifier** on the project site that checks a bundle offline. These close the paper's open item 1 and serve non-technical readers.
- A **bundle archive profile** (a deterministic tar) proposed to the Working Group.
- **Consumers**: storage adapters (IPFS, Arweave), a citation-graph indexer, a mirror tool that keeps plain-text archives in sync.
- A **dual-hash successor profile** (paper §14.5) and the post-quantum anonymity layer the paper names as future work.
