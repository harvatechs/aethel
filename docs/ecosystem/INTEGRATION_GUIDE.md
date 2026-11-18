# Preservation & Ecosystem Integration Guide

This guide details how to integrate Permanent Ink Protocol (PIP-1) bundles and `aethel` into global preservation networks, decentralized storage, citation indices, and CI/CD pipelines.

---

## 1. Archiving Bundles to the Internet Archive (archive.org)

The Internet Archive provides permanent, non-profit hosting for digital materials. PIP-1 bundles can be deposited directly into the Archive using the official `ia` command-line client.

### Step-by-Step Deposit:

1. **Install the Internet Archive CLI**:
   ```bash
   pip install internetarchive
   ia configure
   ```

2. **Publish and Archive a Bundle**:
   ```bash
   # 1. Publish the bundle locally with aethel
   aethel publish --text paper.md --key author_key.p8 --out bundle_paper/

   # 2. Upload the bundle directory as a permanent item on Archive.org
   ia upload pip1-bundle-paper bundle_paper/ \
     --metadata="title:Permanent Ink Archival Bundle: Paper" \
     --metadata="creator:HarVa" \
     --metadata="mediatype:texts" \
     --metadata="collection:opensource" \
     --metadata="description:Cryptographically authenticated PIP-1 document bundle."
   ```

3. **Verify Directly from Archive.org**:
   Anyone can download the files from `archive.org/details/pip1-bundle-paper` and verify them locally using `aethel verify` or `scripts/verify_minimal.py`.

---

## 2. Preserving Bundles on IPFS & Filecoin

Because PIP-1 bundles are self-contained filesystem directories, they map cleanly to content-addressed distributed file systems like IPFS.

### Pinning a Bundle to IPFS:

```bash
# Add the bundle directory to IPFS
ipfs add -r -Q bundle_paper/
# Output CID: QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco

# Pin for permanent decentralized persistence
ipfs pin add QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
```

**Architectural Synergy**:
- **IPFS CID**: Provides distributed transport and routing.
- **PIP-1 Manifest**: Provides cryptographic domain separation, Unicode 18.0.0 NFC canonicalization, and NIST FIPS 204/205 post-quantum digital signatures.

---

## 3. Citing PIP-1 Documents in Wikipedia & Academics

Wikipedia suffers from severe **link rot**; over 30% of external web references cited on Wikipedia become broken or altered over time.

PIP-1 provides two persistent identifier schemes:
1. **Text Identifier (`pip1:t:...`)**: Identifies the exact words of the manuscript, independent of metadata or layout.
2. **Manifest Identifier (`pip1:m:...`)**: Identifies the complete multi-file bundle, assets, and author attributions.

### Wikipedia Citation Format:

```wikitext
{{cite web
  | title = On the Mathematical Foundation of Digital Memory
  | author = HarVa
  | date = 2026-11-17
  | url = https://aethel-codex.pages.dev/
  | id = {{hdl|pip1:t:770854d92fa62f1c849e755ea7e30d1d73cb6aa3cb478a55dbbb868fbfa59728}}
  | quote = The permanent record cannot depend on the survival of a single domain name.
}}
```

### LaTeX / BibTeX Academic Citation:

```bibtex
@article{harva2026permanent,
  author       = {HarVa},
  title        = {The Permanent Ink Protocol: Post-Quantum Document Preservation},
  year         = {2026},
  journal      = {Archivist Labs Technical Reports},
  note         = {PIP-1 Text ID: \texttt{pip1:t:770854d92fa62f1c849e755ea7e30d1d73cb6aa3cb478a55dbbb868fbfa59728}}
}
```

---

## 4. Reusable GitHub Action for CI/CD

Projects, legal agreements, and academic whitepapers hosted on GitHub can enforce cryptographic bundle integrity on every pull request using this workflow:

Create `.github/workflows/verify-bundles.yml`:

```yaml
name: Verify Archival Bundles
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - name: Install aethel-codex
        run: uv pip install aethel-codex
      - name: Verify All Bundles in Repository
        run: |
          for bundle in bundles/*/; do
            echo "Verifying $bundle..."
            aethel verify "$bundle"
          done
```
This guarantees that any unauthorized change or byte alteration to a repository's whitepaper or specification will fail the build immediately.
