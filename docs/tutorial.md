# Tutorial: Publishing and Verifying with `aethel`

This tutorial guides you through publishing, signing, verifying, and revising documents with `aethel`, the reference implementation of the Permanent Ink Protocol profile **pip-1** (PIP-YP-1 v1.0.0-rc.3).

---

## 1. Concepts

A piece of writing published under PIP-1 is packaged into a **bundle**:
- **Manifest (`manifest.pip`)**: A single-line-oriented, byte-sorted UTF-8 manifest (PMF-1) that binds the title, license, language, text identifier, asset table, citation locators, and declared author keys.
- **Canonical Text (`text.md` or `text.txt`)**: The text normalized to Canonical Text Form (CTF-1) using Unicode 18.0.0 NFC normalization, LF line endings, and no byte-order mark.
- **Assets (`assets/`)**: Associated binary assets (figures, tables, data) stored verbatim.
- **Signatures (`*.sig`)**: Detached cryptographic signature envelopes (SGE-1) signed by the holders of declared author keys.

The bundle directory is named after the hex encoding of the 32-byte manifest digest:
`pip1:m:<64-hex-digits>`

---

## 2. Generating Post-Quantum Keys

PIP-1 uses post-quantum digital signature algorithms:
- **ML-DSA-87** (NIST FIPS 204, primary)
- **ML-DSA-65** (NIST FIPS 204, secondary)
- **SLH-DSA-SHA2-256s** / **SLH-DSA-SHAKE-256s** (NIST FIPS 205, hash-based fallback)

Generate a primary key (stored unencrypted with `--no-passphrase`, or omit flag for interactive passphrase prompt):

```bash
aethel keygen --out author.aek --no-passphrase
```

To protect the secret key with a passphrase (encrypted using Argon2id and AES-256-GCM):

```bash
aethel keygen --alg ml-dsa-87 --out author_encrypted.aek --passphrase-file passphrase.txt
```

---

## 3. Publishing a Manuscript

Suppose you have a manuscript `paper.md`:

```markdown
# Analysis of Systems

This work describes the structure of verified records.
```

Publish with title, license, and signing key:

```bash
aethel publish paper.md \
  --title "Analysis of Systems" \
  --license "CC-BY-4.0" \
  --lang "en" \
  --key author.aek \
  --out-dir bundles/
```

`aethel publish` performs strict validation:
1. Canonicalizes the text to CTF-1.
2. Computes the Merkle tree root over 4,096-byte chunks to derive the text identifier (`pip1:t:...`).
3. Constructs and formats the canonical manifest (`manifest.pip`).
4. Signs the manifest digest with the provided secret key.
5. Self-verifies the produced bundle in memory before writing to disk atomically.

---

## 4. Packaging with Assets

You can bundle images or data tables alongside the text:

```bash
aethel publish paper.md \
  --title "Analysis of Systems" \
  --license "CC-BY-4.0" \
  --asset fig1.svg \
  --asset data.csv \
  --key author.aek \
  --out-dir bundles/
```

Assets are hashed in raw binary form without Unicode canonicalization.

---

## 5. Dual-Family Signing

To protect against unexpected future cryptanalytic breaks in lattice-based cryptography, PIP-1 supports dual-family signing by combining an ML-DSA lattice key and an SLH-DSA hash-based key:

```bash
aethel keygen --alg ml-dsa-87 --out lattice.aek --no-passphrase
aethel keygen --alg slh-dsa-shake-256s --out stateless.aek --no-passphrase

aethel publish paper.md \
  --title "Dual-Signed Paper" \
  --license "Apache-2.0" \
  --key lattice.aek \
  --key stateless.aek \
  --out-dir bundles/
```

Verification reports attribution as `Dual-family (2 of 2)` and confirms dual-family coverage.

---

## 6. Verifying a Bundle

To verify a published bundle:

```bash
aethel verify bundles/<manifest_hex>/
```

The verifier executes eight orthogonal check dimensions:
- **V1 (Manifest format & ID)**: Verifies that `manifest.pip` strictly parses, is sorted, and hashes to the bundle directory name.
- **V2 (Text integrity)**: Verifies that `text.md` matches the canonical text identifier in the manifest.
- **V3 (Asset integrity)**: Verifies that all declared assets match their declared byte counts and Merkle roots.
- **V4 (Citations)**: Verifies that inline citations match declared citation locators.
- **V5 (History)**: Verifies that parent edition manifests match declared prior work.
- **V6 (Attribution)**: Verifies detached signature envelopes against declared author keys.
- **V7 (Time)**: Checks external attestations (if present).
- **V8 (Beacons)**: Carries forward beacon lines (unchecked by this tool).

Output format:

```text
Manifest     pip1:m:e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d
Text         pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba

Integrity    PASS
Attribution  Attributed (1 of 1)
History      Genesis
Time         SKIPPED      no beacon and no attestations

Checks  V1 PASS · V2 PASS · V3 SKIPPED · V4 SKIPPED · V5 SKIPPED · V6 PASS · V7 SKIPPED · V8 SKIPPED
A valid signature shows that the holder of a key approved this manifest. It does not show who that person is.
PIP-1 never produces a time value of its own.
```

---

## 7. Revising a Published Work

When updating an existing work, create a revision bundle that links back to the genesis manifest:

```bash
aethel revise bundles/<genesis_hex>/ revised_paper.md \
  --title "Analysis of Systems (Second Edition)" \
  --key author.aek \
  --out-dir bundles/
```

Verify with the parents directory so the verifier can traverse the edition chain:

```bash
aethel verify bundles/<revision_hex>/ --parents bundles/
```

The verifier confirms check **V5 PASS**, establishing the edition lineage.

---

## 8. Verifying with the Minimal Standalone Verifier

PIP-1 is designed for long-term auditability without complex toolchains.
The repository includes `scripts/verify_minimal.py`, a 150-line verifier using **only the Python standard library** (zero third-party dependencies):

```bash
python scripts/verify_minimal.py bundles/<manifest_hex>/
```

It validates V1 (manifest syntax and digest), V2 (text Merkle tree), and V3 (asset Merkle trees), proving that the files have not been modified since publication.
