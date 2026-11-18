# The Archival Manifesto: Naming Writing by What It Says

**Permanent Ink Protocol (PIP-1) — A Foundation for Centuries of Digital Preservation**

*Archivist Labs / HarVa Groups*  
*Author: HarVa (Harsha Vardhan)*  
*Normative Reference: Yellow Paper PIP-YP-1 v1.0.0-rc.3*

---

## 1. The Crisis of the Ephemeral Web

Humankind has built the largest repository of knowledge in history upon the most fragile substrate ever conceived.

Every day, the digital record dissolves. URLs decay; links rot; domain names expire; hosting companies vanish. Even more insidiously, documents undergo **silent mutation**: an essay published in 2020 is silently updated in 2024 to rewrite history; a scientific paper's supplementary dataset changes without notice; a legal declaration is altered on a cloud server without an audit trail.

For five thousand years, physical ink on clay, papyrus, parchment, and acid-free paper provided three essential properties:
1. **Self-Containment**: A physical scroll or book does not depend on a remote server remaining online.
2. **Intrinsic Identity**: The text is inseparable from its physical existence.
3. **Tamper-Evidence**: Altering a word on ancient parchment leaves scratches, chemical discolorations, or erased fibers.

In our rush to digitize, we traded all three properties for convenience:
- We name documents by **where they are hosted** (`https://domain.com/path/doc.pdf`) rather than **what they contain**.
- We rely on centralized platforms and certificate authorities whose keys and companies will not survive the century.
- We face the imminent arrival of cryptanalytically relevant quantum computers, which will retroactively invalidate every RSA and ECDSA digital signature produced over the past forty years.

The Internet Archive proved that humanity desperately cares about preserving its digital record. But a library should not have to fight a losing war against link rot alone. **Preservation must be built into the mathematical fabric of the documents themselves.**

---

## 2. The Core Philosophy of the Permanent Ink Protocol

The Permanent Ink Protocol (PIP-1) was engineered from first principles around four immutable pillars:

### I. Intrinsic Content-Addressing: "Name Your Writing by What It Says"
In PIP-1, a text is not identified by a location, a title, or a database index. It is identified by its deterministic canonical content:
$$\text{Text ID} = \text{SHA3-256}(0x09 \parallel \text{"pip1.text"} \parallel \text{CTF-1}(T))$$

If a single comma, trailing whitespace, or byte order mark changes, the identifier changes. If two authors on opposite sides of the planet write the exact same words without knowing each other, their writings generate the exact same identifier. Text identity is a mathematical fact of nature, not an administrative assignment.

### II. Strict Canonicalization (CTF-1)
Digital text is notoriously ambiguous. Unicode allows the character `é` to be represented as either a single code point (`U+00E9`) or two code points (`U+0065` + `U+0301`). Windows uses `\r\n`; Unix uses `\n`. Different editors attach or strip UTF-8 Byte Order Marks.

PIP-1 solves this with Canonical Text Format 1 (CTF-1):
- Strict Unicode Normalization Form C (NFC) via Unicode 18.0.0.
- Strict Unix line endings (`0x0A`).
- Stripped BOM and mandatory trailing newline.
- Binary rejection of unassigned, surrogate, or private-use code points.

What you write renders identically, computes identically, and hashes identically on every machine across all operating systems.

### III. Post-Quantum Cryptographic Immortality
Digital archives must withstand centuries, not years. Every cryptographic primitive in PIP-1 is post-quantum:
- **Hashing**: SHA3-256 (FIPS 202) domain-separated hashing.
- **Lattice-Based Signatures**: ML-DSA-87 / ML-DSA-65 / ML-DSA-44 (NIST FIPS 204).
- **State-Free Hash-Based Signatures**: SLH-DSA-SHAKE-256s / SLH-DSA-SHA2-128s (NIST FIPS 205).

A bundle signed with SLH-DSA or ML-DSA today will remain mathematically verifiable even in a post-quantum computing era.

### IV. Radical Offline Autonomy
The Permanent Ink Protocol has **zero network dependencies**. It requires no blockchain, no consensus protocol, no external time-stamping authority, no DNS lookup, and no cloud API. A bundle can be verified in a bunker, on a deep-space probe, or in a disconnected library terminal a thousand years from now using simple arithmetic and public mathematical specifications.

---

## 3. The Vision: The Next Great Preservation Layer

Just as **Git** became the universal protocol for source code history, and **HTTP** became the protocol for hyperlinked transfer, **PIP-1** is designed to be the foundational standard for permanent document authentication.

```
+-------------------------------------------------------------------+
|                        Applications                               |
|   Digital Libraries  |  Academic Preprints  |  Legal Treaties     |
|   Investigative News |  Historical Records  |  Open Encyclopedias |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                      aethel Reference Tool                        |
|   Canonicalization  |  Merkle Manifests  |  Dual PQ Backends      |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|              Permanent Ink Protocol (PIP-1 Standard)              |
|        FIPS 202 SHA3-256  |  FIPS 204 ML-DSA  |  FIPS 205 SLH-DSA  |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       Storage Substrates                          |
|    Local Disks  |  Internet Archive  |  IPFS  |  Cold Optical M-DISC|
+-------------------------------------------------------------------+
```

### An Invitation to the World
We do not ask the world to trust an institution or an individual. We provide open mathematics, an unencumbered Apache-2.0 reference implementation, exhaustive oracle test vectors, and a formal Yellow Paper specification.

Preserve what matters. Name your writing by what it says.
