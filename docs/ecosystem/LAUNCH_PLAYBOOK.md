# Organic Launch & Community Outreach Playbook

This playbook contains complete, pre-formatted announcements, submission texts, and community outreach templates designed to maximize organic discovery, developer adoption, and archival integration for `aethel` and the Permanent Ink Protocol (PIP-1).

---

## 1. Hacker News — "Show HN" Submission

> **Best Time to Post**: Tuesday or Wednesday between 07:00 AM – 09:00 AM ET (11:00 – 13:00 UTC).  
> **Title**: `Show HN: Aethel – Post-quantum, offline-first document archival bundles`  
> **URL**: `https://github.com/harvatechs/aethel-pip-one` (or `https://github.com/harvatechs/aethel`)

### Post Body:

```text
Hi HN,

I’m HarVa, founder at HarVa Groups and lead architect at Archivist Labs. Over the last year, we’ve been working on a fundamental problem in digital preservation: link rot and silent document mutation.

Today, when we cite or store digital writing, we name documents by where they live on a server (URLs) rather than what they contain. Furthermore, existing digital signatures (RSA, ECDSA) rely on mathematical assumptions that will be broken by quantum computers within our lifetimes.

We built `aethel` (https://github.com/harvatechs/aethel-pip-one), the reference CLI and library for the Permanent Ink Protocol (profile pip-1, defined in Yellow Paper PIP-YP-1 v1.0.0-rc.3).

What aethel does:
1. Canonicalizes writing to CTF-1 (strict Unicode 18.0.0 NFC, strict Unix line endings, BOM stripping, reject unassigned/surrogate code points).
2. Computes a deterministic content identifier: H("pip1.text", CTF1(text)).
3. Packages manuscripts and binary assets into self-contained Merkle-tree directories called bundles.
4. Seals bundles with dual post-quantum digital signatures: NIST FIPS 204 (ML-DSA-87/65/44) and NIST FIPS 205 (SLH-DSA-SHAKE-256s/SHA2-128s).
5. Enforces zero network I/O: the CLI and library contain zero socket calls. Verification requires no blockchain, no cloud APIs, and no certificate authorities. It can be verified completely offline.

We also include a standalone minimal verifier (`scripts/verify_minimal.py`) in under 200 lines of standard Python with zero dependencies so that bundles can be audited by hand decades from now.

Code: https://github.com/harvatechs/aethel-pip-one
Spec & Docs: https://aethel-codex.pages.dev/
Manifesto: https://github.com/harvatechs/aethel-pip-one/blob/main/docs/ecosystem/MANIFESTO.md

I would love to hear feedback from cryptographers, digital archivists, and anyone who cares about long-term knowledge preservation.
```

---

## 2. Reddit Technical Communities

### Subreddit 1: `r/programming`
- **Title**: `Aethel: An offline-first, post-quantum signed document archival tool in Python`
- **Link / Body**:
  ```markdown
  Most digital documents decay within a decade—links break, servers shut down, and files are silently modified without an audit trail. 

  We just released `aethel`, the reference CLI and library for the Permanent Ink Protocol (PIP-1):
  https://github.com/harvatechs/aethel-pip-one

  Some interesting technical decisions we made:
  - **Zero Network Sockets**: The entire library and CLI are strictly offline. There is no telemetry, no cloud dependency, and no blockchain.
  - **Unicode 18.0.0 via `unicodedata2`**: Banned Python's standard library `unicodedata` in `src/` to guarantee deterministic NFC normalization across operating systems and Python minor releases.
  - **Dual Post-Quantum Backends**: Implements NIST FIPS 204 (ML-DSA) and NIST FIPS 205 (SLH-DSA) with both high-performance C bindings and pure-Python fallback.
  - **Hierarchical Merkle Manifest**: 4,096-byte chunked leaves, domain-separated SHA3-256 hashes (`pip1.manifest`, `pip1.leaf`, `pip1.asset`, `pip1.text`).
  - **Self-Verifying Signatures**: Signatures are automatically verified against public keys before writing to disk; the tool refuses to emit any signature that fails self-verification.

  Full documentation and yellow paper are in the repo. Feedback and PRs welcome!
  ```

### Subreddit 2: `r/crypto`
- **Title**: `Implementing NIST FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) for Archival Document Bundles (PIP-1)`
- **Body**: Focuses on state-free hash signatures (SLH-DSA), domain separation in FIPS 202 SHA3-256 (`H(label, x) = SHA3-256(u8(len(label)) || label || x)`), and the separate four-factor verification model (Integrity, Attribution, History, Time).

### Subreddit 3: `r/archivism` & `r/DataHoarder`
- **Title**: `Aethel: A tool to create self-contained, tamper-evident archival document bundles that can be verified offline centuries from now`
- **Body**: Focuses on long-term data preservation, avoiding dependency on remote servers, optical M-DISC backup readiness, and how to verify bundles without installing dependencies using `verify_minimal.py`.

---

## 3. Twitter / X & Bluesky Long-Form Thread

**Tweet 1 (Hook)**:
> In the physical world, 1,000-year-old manuscripts still survive. In the digital world, web links rot in 5 years, and files are silently modified without notice.
> 
> Today we’re open-sourcing Aethel: a post-quantum, offline-first tool to create immortal archival document bundles. 📜🔒  
> https://github.com/harvatechs/aethel-pip-one

**Tweet 2 (The Problem)**:
> When we cite digital writing today, we name documents by *where* they live (URLs), not *what* they say. When a domain expires or a server updates, the link breaks or the history is rewritten.
> 
> Furthermore, current digital signatures (RSA/ECDSA) will not survive quantum computers.

**Tweet 3 (How it works)**:
> Aethel implements PIP-1 (Permanent Ink Protocol):
> 1. Canonicalizes text to CTF-1 (strict Unicode 18.0.0 NFC)
> 2. Computes an intrinsic content ID: H("pip1.text", text)
> 3. Merkle-trees documents and assets into self-contained bundles
> 4. Authenticates with NIST FIPS 204 (ML-DSA) & FIPS 205 (SLH-DSA)

**Tweet 4 (Zero Network)**:
> No blockchain. No tokens. No cloud APIs. Zero network calls.
> 
> Aethel can run in a disconnected bunker or cold archival storage. We even included a 200-line minimal Python verifier with zero external libraries.

**Tweet 5 (Call to Action)**:
> We’re looking for digital archivists, cryptographers, and historians to test it and help build the future of permanent preservation.
> 
> Read the manifesto: https://github.com/harvatechs/aethel-pip-one/blob/main/docs/ecosystem/MANIFESTO.md  
> Star & explore: https://github.com/harvatechs/aethel-pip-one

---

## 4. Key Archival & Research Organizations to Contact

1. **Internet Archive** (`info@archive.org` / Brewster Kahle's digital preservation forums)
   - Angle: Proposing PIP-1 bundles as an authenticated preservation format for digitized manuscripts and open texts.
2. **Software Heritage** (`contact@softwareheritage.org`)
   - Angle: Immutable, cryptographic content-addressing for source code documentation and specifications.
3. **Open Library / Wikimedia Research**
   - Angle: Using immutable `pip1:t:...` identifiers to solve link rot in Wikipedia citation bibliographies.
4. **Digital Humanities Labs** (Stanford, Oxford, MIT digital archival initiatives)
   - Angle: Post-quantum verification for primary historical source texts and open-access scientific preprints.
