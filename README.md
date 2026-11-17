<div align="center">

# Aethel Codex (`aethel`)

**Reference Command-Line Tool & Python Library for the Permanent Ink Protocol (`pip-1`)**

[![Specification](https://img.shields.io/badge/Specification-PIP--YP--1%20v1.0.0--rc.3-blue.svg)](docs/yellow-paper/PIP-YP-1_v1.0.0-rc.3.pdf)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Post-Quantum](https://img.shields.io/badge/Post--Quantum-NIST%20FIPS%20204%20%26%20205-purple.svg)](https://csrc.nist.gov/pubs/fips/204/final)
[![Network](https://img.shields.io/badge/Network-Offline%20Only%20(Zero%20Sockets)-darkgreen.svg)](SECURITY.md)
[![Coverage](https://img.shields.io/badge/Coverage-91.04%25-brightgreen.svg)](docs/conformance-report.md)

<p align="center">
  <em>Gives a piece of writing a permanent name made from the writing itself.</em>
</p>

</div>

---

## Executive Overview

In digital publishing and archival preservation, web links rot, cloud repositories change, and documents are silently modified. 

**`aethel`** implements the **Permanent Ink Protocol profile `pip-1`** (defined in Yellow Paper PIP-YP-1 v1.0.0-rc.3). It transforms manuscripts and associated assets into self-contained, content-addressed, tamper-evident directories called **bundles**. 

Every bundle is cryptographically sealed with post-quantum digital signatures (NIST FIPS 204 ML-DSA and FIPS 205 SLH-DSA), verified completely offline, and auditable for decades using nothing but standard mathematics.

```
Manuscript (Markdown / Text) + Binary Assets
                     │
                     ▼
  1. Canonicalize (Unicode 18.0.0 NFC, LF line endings, no BOM)
                     │
                     ▼
  2. Merkle Tree Fingerprinting (4,096-byte chunks, SHA3-256)
                     │
                     ▼
  3. Strict Manifest Generation (PMF-1 byte-sorted index)
                     │
                     ▼
  4. Post-Quantum Signing (ML-DSA-87 / SLH-DSA-SHAKE-256s)
                     │
                     ▼
  5. Atomic Self-Contained Bundle (`pip1:m:<manifest_hex>/`)
```

---

## Architectural Highlights

- **Post-Quantum Cryptography by Default**: Employs **ML-DSA** (Module-Lattice Digital Signatures, FIPS 204) and **SLH-DSA** (Stateless Hash-Based Signatures, FIPS 205). Supports dual-family signatures to safeguard documents against prospective cryptanalytic advances.
- **Air-Gapped & Offline Always**: Contains zero network socket imports, zero telemetry, zero tracking, and no external daemon. Verification executes entirely locally against the files on disk.
- **Standard Library Minimal Verifier**: Accompanied by [`scripts/verify_minimal.py`](scripts/verify_minimal.py)—a 150-line verifier requiring **only the Python standard library** (no external packages)—ensuring documents remain verifiable even if package ecosystems fade.
- **Cross-Platform Determinism**: Eliminates OS line-ending discrepancies and Unicode ambiguities via Canonical Text Form (`CTF-1`), guaranteeing byte-for-byte identical identifiers on Windows, macOS, and Linux.
- **Radical Claims Honesty**: Does not overclaim. Reports integrity, attribution, edition history, and time attestations as separate, orthogonal dimensions.

---

## Installation

Install via `pipx` (recommended) or `uv`:

```bash
pipx install aethel-codex
```

Or using `pip` in a virtual environment:

```bash
pip install aethel-codex
```

> [!IMPORTANT]
> Always install **`aethel-codex`**. Never install `aethel` (an unrelated package on PyPI).

### Requirements
- **Runtime**: Python 3.11, 3.12, 3.13, or 3.14.
- **Platforms**: Linux (glibc >= 2.34 or musl), macOS (x86_64, arm64), Windows (x86_64).
- **Dependencies**: Exactly three audited runtime packages: `cryptography`, `pqcrypto`, and `unicodedata2`.

---

## Five-Minute Tutorial

### 1. Generate an Author Signing Key

Generate an ML-DSA-87 keypair stored in an AKF-1 keyfile:

```bash
aethel keygen --out author.aek --no-passphrase
```

*(To encrypt the key with Argon2id + AES-256-GCM, omit `--no-passphrase` or use `--passphrase-file`).*

### 2. Publish a Manuscript

Create a sample text manuscript:

```bash
cat << 'EOF' > essay.md
# On Writing

Words written with care.
EOF
```

Package the text into a cryptographically sealed bundle:

```bash
aethel publish essay.md --title "On Writing" --license "CC-BY-4.0" --key author.aek --out-dir bundles/
```

This creates an atomic directory named after the 64-hex manifest identifier containing:
- `manifest.pip`: The PMF-1 canonical manifest binding text, metadata, and author keys.
- `text.md`: The normalized UTF-8 text (CTF-1).
- `author.sig`: The detached post-quantum signature envelope (SGE-1).

### 3. Verify the Bundle

Verify the bundle with nothing but the files:

```bash
aethel verify bundles/61*
```

Output:

```text
Manifest     pip1:m:61...
Text         pip1:t:18...

Integrity    PASS
Attribution  Attributed (1 of 1)
History      Genesis
Time         SKIPPED      no beacon and no attestations

Checks  V1 PASS · V2 PASS · V3 SKIPPED · V4 SKIPPED · V5 SKIPPED · V6 PASS · V7 SKIPPED · V8 SKIPPED
A valid signature shows that the holder of a key approved this manifest. It does not show who that person is.
PIP-1 never produces a time value of its own.
```

### 4. Detect Tampering

Modify a single byte in `text.md`:

```bash
echo "tampered" >> bundles/61*/text.md
aethel verify bundles/61*
```

Output:

```text
Integrity    FAIL
Attribution  Attributed (1 of 1)
               pip1:k:256c3fc3...   signed   ml-dsa-87
History      SKIPPED      genesis manifest, no parents
Time         SKIPPED      no beacon and no attestations

Checks  V1 PASS · V2 FAIL · V3 PASS · V4 PASS · V5 SKIPPED · V6 PASS · V7 PASS · V8 SKIPPED
```

*A change to the text, assets, metadata, citations or declared authors changes the manifest identifier.*

---

## Bundle Anatomy

A PIP-1 bundle directory is fully inspectable as plain UTF-8 text and binary files:

```text
e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d/
├── manifest.pip     # Canonical PMF-1 manifest (title, license, hashes, authors)
├── text.md          # Normalized canonical text (CTF-1)
├── assets/          # (Optional) Binary assets (figures, tables, datasets)
│   ├── figure1.svg
│   └── data.csv
└── author.sig       # Detached post-quantum signature envelope (SGE-1)
```

---

## Verification Model (Checks V1–V8)

`aethel verify` evaluates eight orthogonal verification dimensions:

| Check | Target | What It Verifies |
|---|---|---|
| **V1** | Manifest | PMF-1 syntax, field ordering, unique sorting, and directory name match. |
| **V2** | Text | CTF-1 compliance, byte length, and Merkle text identifier match. |
| **V3** | Assets | File existence, declared byte lengths, and asset Merkle root matches. |
| **V4** | Citations | Consistency between inline citations and declared citation locators. |
| **V5** | History | Parent edition manifests exist, share work ID, and form a valid lineage. |
| **V6** | Signatures | Detached signature envelopes verify against declared author keys. |
| **V7** | Attribution | Evaluates attribution class (`Attributed`, `Dual-family`, `Partially attributed`). |
| **V8** | Time | Reports external attestations and beacon lines (carried, unverified). |

---

## What Verification Does and Does Not Show

PIP-1 adheres to strict, scientifically honest claims boundaries:

- **What It Shows**:
  - **Integrity**: Proves whether the text and assets match the cryptographic digests in the manifest.
  - **Attribution**: Shows whether the holder of a declared key approved this exact manifest as author.
  - **History**: Shows whether revision parent links match declared prior manifests.
  - **Time Evidence**: Reports external third-party attestations if bundled.

- **What It Does NOT Show**:
  - **Identity**: A valid signature shows that the holder of key `pip1:k:…` approved this exact manifest as author. PIP-1 cannot say who holds the key.
  - **Originality / First Invention**: Anyone can copy a text and sign it with their own key. A valid signature shows approval of this exact manifest; it does not determine who conceived the ideas first.
  - **Storage / Availability**: Tampering is detectable. This tool does not store or keep copies.
  - **Confidentiality / Anonymity**: PIP-1 provides no anonymity and no confidentiality. All manifests and texts are public.

*Signatures use ML-DSA (FIPS 204) and SLH-DSA (FIPS 205), standards designed to resist quantum computers.*

---

## Command Reference

| Command | Syntax | Description |
|---|---|---|
| `canon` | `aethel canon <file> [--check]` | Normalize text to Canonical Text Form (CTF-1). |
| `id` | `aethel id <file> [--kind text\|asset]` | Calculate content-addressed identifier (`pip1:t:...` or `pip1:a:...`). |
| `keygen` | `aethel keygen --out <key.aek>` | Generate post-quantum AKF-1 keypair (`ml-dsa-87`, `slh-dsa-...`). |
| `publish` | `aethel publish <file> --title ... --key ...` | Package manuscript and assets into an atomic bundle. |
| `sign` | `aethel sign <bundle> --key <key.aek>` | Attach a detached signature envelope (SGE-1) to a bundle. |
| `verify` | `aethel verify <bundle...> [--json]` | Verify bundle integrity, attribution, history, and time evidence. |
| `inspect` | `aethel inspect <bundle> [--json]` | Fast inspection of manifest metadata without crypto verification. |
| `selftest` | `aethel selftest [--json]` | Execute 13 built-in offline conformance checks against vectors. |
| `explain` | `aethel explain <code> [--list]` | Look up diagnostic explanations and remediations for error codes. |
| `version` | `aethel version [--json]` | Output tool, Unicode, and cryptographic backend versions. |
| `revise` | `aethel revise <bundle> <manuscript>` | Create a revision bundle linked to prior edition manifest parents. |
| `cite` | `aethel cite make\|check\|show <bundle>` | Generate and validate canonical citation locators. |
| `proof` | `aethel proof make\|verify <bundle>` | Generate and verify chunk Merkle inclusion proofs (TFP-1). |
| `attest` | `aethel attest add <bundle> <att.att>` | Attach an external attestation envelope (ATT-1). |

---

## Python Library API

`aethel_codex` exposes a concise, fully typed, documented Python interface:

```python
from pathlib import Path
from aethel_codex import canonicalize, text_id, verify_bundle

# 1. Canonicalize text to CTF-1 (NFC, LF line endings, stripped BOM)
raw_bytes = b"# Hello World\r\n\r\nWritten text.\r\n"
canonical_bytes, report = canonicalize(raw_bytes)

# 2. Compute content-addressed text identifier
tid = text_id(canonical_bytes)
print(f"Text ID: {tid}")
# Text ID: pip1:t:770854d92fa62f1c849e755ea7e30d1d73cb6aa3cb478a55dbbb868fbfa59728

# 3. Verify an existing bundle directory
bundle_path = Path(
    "tests/fixtures/genesis-attributed/e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
)
ver_report = verify_bundle(bundle_path)

print(f"Integrity:   {ver_report.integrity}")
print(f"Attribution: {ver_report.attribution.cls}")
# Integrity:   PASS
# Attribution: Attributed
```

---

## Research & Academic Citation

If you use `aethel` or the Permanent Ink Protocol in academic research, archival preservation, or security studies, please cite this reference implementation:

```bibtex
@software{vardhan2026aethel,
  author       = {Harsha Vardhan},
  title        = {aethel-codex: Reference CLI and Python Library for the Permanent Ink Protocol (PIP-1)},
  year         = {2026},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/harvatechs/aethel-pip-one}},
  version      = {0.1.0-rc.1}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

---

## Project Information & Contacts

- **Author & Lead Architect**:  
  **Harsha Vardhan**  
  Founder at HarVa Groups  
  Lead Architect at Archivist Labs (Init. of Aethel Codex)  
  Email: `heyharva@gmail.com`
- **Repository**: [https://github.com/harvatechs/aethel-pip-one](https://github.com/harvatechs/aethel-pip-one)
- **Official Documentation**: [https://aethel-codex.pages.dev/](https://aethel-codex.pages.dev/)

---

## Normative References & Documentation

- **Normative Specification**: [Yellow Paper PIP-YP-1 v1.0.0-rc.3](docs/yellow-paper/PIP-YP-1_v1.0.0-rc.3.pdf)
- **Formal Conformance Report**: [docs/conformance-report.md](docs/conformance-report.md)
- **Guides**: [Tutorial](docs/tutorial.md) · [Verify By Hand](docs/verify-by-hand.md) · [CLI Manual](docs/man-page.md)
- **Contributing & Community**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Minimal Verifier**: [`scripts/verify_minimal.py`](scripts/verify_minimal.py) (zero external dependencies)
- **License**: [Apache-2.0](LICENSE)
