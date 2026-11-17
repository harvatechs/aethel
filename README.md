# aethel-codex

Gives a piece of writing a name made from the writing itself.
Reference command-line tool and Python library for the Permanent Ink Protocol profile **pip-1** (Yellow Paper PIP-YP-1 v1.0.0-rc.3).

---

## Installation

Install via `pipx` or `uv`:

```bash
pipx install aethel-codex
```

> **Warning:** Always install **`aethel-codex`**. Never install `aethel` (an unrelated package on PyPI).

`aethel` requires Python 3.11 or newer on Linux, macOS, or Windows. It installs as a pure-Python wheel and brings exactly three runtime dependencies: `cryptography`, `pqcrypto`, and `unicodedata2`.

---

## Five-Minute Tutorial

### 1. Generate an author key

Create an ML-DSA-87 post-quantum signing key:

```bash
aethel keygen --out author.aek --no-passphrase
```

### 2. Publish a manuscript

Write a short manuscript:

```bash
cat << 'EOF' > essay.md
# On Writing

Words written with care.
EOF
```

Publish the manuscript into a self-contained bundle:

```bash
aethel publish essay.md --title "On Writing" --license "CC-BY-4.0" --key author.aek --out-dir bundles/
```

This creates a bundle directory named by its 64-hex manifest identifier containing:
- `manifest.pip`: the strict canonical manifest binding text, metadata, and author keys
- `text.md`: the canonical UTF-8 text (CTF-1)
- `author.sig`: the detached post-quantum signature envelope (SGE-1)

### 3. Verify the bundle

Verify the bundle with nothing but the files:

```bash
aethel verify bundles/61*
```

Example output:

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

### 4. Detect tampering

Change a single byte in `text.md`:

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

A change to the text, assets, metadata, citations or declared authors changes the manifest identifier.

---

## What Verification Does and Does Not Show

PIP-1 and `aethel` adhere to strict and honest claims boundaries:

- **What it shows**:
  - **Integrity**: Proves whether the text and assets match the cryptographic digests in the manifest.
  - **Attribution**: Shows whether the holder of a declared key approved this exact manifest as author.
  - **History**: Shows whether revision parent links match the declared prior manifests.
  - **Time**: Shows external attestations if present. (The tool itself produces no time evidence).

- **What it does NOT show**:
  - **Identity**: A valid signature shows that the holder of key `pip1:k:…` approved this exact manifest as author. PIP-1 cannot say who holds the key.
  - **Originality / First Invention**: Anyone can copy a text and sign it with their own key. A valid signature shows that the key holder approved this exact manifest; it does not determine who conceived the ideas or wrote the words first.
  - **Storage**: Tampering is detectable. This tool does not store or keep copies.
  - **Confidentiality / Anonymity**: PIP-1 provides no anonymity and no confidentiality. All manifests and texts are public.

Signatures use ML-DSA (FIPS 204) and SLH-DSA (FIPS 205), standards designed to resist quantum computers.

---

## Commands at a Glance

| Command | Purpose |
|---|---|
| `aethel canon <path>` | Normalize Markdown/text to Canonical Text Form (CTF-1) |
| `aethel id <path>` | Compute content-addressed identifier (`pip1:t:...` or `pip1:a:...`) |
| `aethel keygen --out <path>` | Generate a post-quantum signing key (`ml-dsa-87`, `slh-dsa-...`) |
| `aethel publish <path>` | Package text and assets into a signed PIP-1 bundle |
| `aethel sign <bundle> --key <path>` | Add a detached signature envelope (SGE-1) to an existing bundle |
| `aethel verify <bundle>` | Verify integrity, attribution, history, and time checks (V1–V8) |
| `aethel inspect <bundle>` | Inspect manifest metadata, declared authors, and asset tables |
| `aethel selftest` | Run 13 built-in offline conformance checks against embedded vectors |
| `aethel explain <code>` | Explain error codes and suggest actionable remediation |
| `aethel revise <bundle>` | Create a revision bundle linked to parent editions |
| `aethel cite make/check/show` | Generate, check, and display canonical citation URIs |
| `aethel proof make/verify` | Generate and verify chunk Merkle audit paths (TFP-1) |
| `aethel attest add` | Attach external attestation envelopes (ATT-1) |

---

## Library Example

`aethel_codex` exposes a small, fully typed, documented Python API:

```python
from pathlib import Path
from aethel_codex import canonicalize, text_id, verify_bundle

# 1. Canonicalize text to CTF-1 (NFC, LF endings, no BOM)
raw_bytes = b"# Hello World\r\n\r\nWritten text.\r\n"
canonical_bytes, report = canonicalize(raw_bytes)

# 2. Compute the PIP-1 text identifier
tid = text_id(canonical_bytes)
print(f"Text ID: {tid}")
# Text ID: pip1:t:770854d92fa62f1c849e755ea7e30d1d73cb6aa3cb478a55dbbb868fbfa59728

# 3. Verify an existing bundle
ver_report = verify_bundle(
    Path(
        "tests/fixtures/genesis-attributed/e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
    )
)
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

See `CITATION.cff` for additional metadata.

---

## Contact & Project Information

- **Author & Lead Architect**:
  **Harsha Vardhan**
  Founder at HarVa Groups
  Lead Architect at Archivist Labs (Init. of Aethel Codex)
  Email: `heyharva@gmail.com`

- **Repository**: [https://github.com/harvatechs/aethel-pip-one](https://github.com/harvatechs/aethel-pip-one)
- **Official Documentation**: [https://aethel-codex.pages.dev/](https://aethel-codex.pages.dev/)

---

## Normative References & Links

- **Normative Specification**: [Yellow Paper PIP-YP-1 v1.0.0-rc.3](docs/yellow-paper/PIP-YP-1_v1.0.0-rc.3.pdf)
- **Conformance Report**: [docs/conformance-report.md](docs/conformance-report.md)
- **Guides**: [Tutorial](docs/tutorial.md) · [Verify By Hand](docs/verify-by-hand.md) · [CLI Manual](docs/man-page.md)
- **Contributing & Research**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Minimal Verifier**: [scripts/verify_minimal.py](scripts/verify_minimal.py) (zero external dependencies, stdlib only)
- **License**: [Apache-2.0](LICENSE)
