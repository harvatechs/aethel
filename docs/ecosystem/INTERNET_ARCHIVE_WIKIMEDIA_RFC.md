# RFC: Permanent Content-Addressing for Global Knowledge Institutions
## Standardizing PIP-1 Bundles and URN Identifiers for Wikimedia & The Internet Archive

**Document Identifier**: `RFC-PIP1-INSTITUTIONAL-001`  
**Authors**: HarVa (Harsha Vardhan), Lead Architect, Archivist Labs / HarVa Groups  
**Date**: November 2026  
**Status**: Proposal for Institutional Adoption  
**Target Bodies**: 
- Wikimedia Foundation (WikiProject Digital Preservation, WikiProject Reference Citations)
- Internet Archive (Wayback Machine Archival Standards Group, Open Library)
- Digital Preservation Coalition (DPC)
- International Internet Preservation Consortium (IIPC)

---

## 1. Executive Summary

Humanity’s digital record suffers from two existential systemic vulnerabilities:
1. **The Citation Decay Crisis**: Over 30% of external web references on Wikipedia and scholarly publications suffer from "link rot" within seven years, or worse, "content drift" (silent modification where the URL resolves to altered text).
2. **The Post-Quantum Cryptographic Cliff**: Over 99% of digitally signed documents and certificate chains (RSA, ECDSA) will become retroactively forgeable once cryptanalytically relevant quantum computers (CRQCs) arrive.

The **Permanent Ink Protocol (PIP-1)**, implemented in the reference tool **`aethel`**, resolves both problems by providing:
- Intrinsic content-addressing via Canonical Text Form (`CTF-1`) and FIPS 202 SHA3-256.
- Self-contained, immutable Merkle directories (bundles).
- Dual post-quantum cryptographic sealing (NIST FIPS 204 ML-DSA and FIPS 205 SLH-DSA).
- Radical offline autonomy: zero network dependencies, verifiable via a 150-line standard-library script.

This RFC outlines the technical architecture for adopting `pip1:` Uniform Resource Names (URNs) and atomic bundles as the premier archival preservation standard across Wikimedia and the Internet Archive.

---

## 2. Institutional Alignment: Why PIP-1 Extends the Missions of Wikipedia & Internet Archive

| Institution | Current Model & Limitation | PIP-1 Enhanced Architecture |
|---|---|---|
| **Internet Archive (Wayback Machine)** | Captures ephemeral HTTP snapshots tied to domain URLs. Vulnerable if domain ownership changes, certificates expire, or server headers were malformed. | Bundles captured documents into atomic, self-contained Merkle packages sealed with post-quantum signatures (`pip1:m:<manifest_hex>`). |
| **Wikimedia Foundation** | Citations rely on external URLs, DOIs, or ISBNs. URLs decay; DOIs rely on centralized commercial registries; book citations are unlinked. | Citations reference permanent `pip1:t:<text_id>` and `pip1:m:<manifest_id>`. Text identity is mathematically immutable; readers can verify the exact cited version offline. |
| **Scholarly Preprints & Journals** | Centralized PDF repositories subject to silent revisions, paywalls, and platform shutdowns. | Research papers distributed as dual-signed post-quantum bundles containing manuscript, code, and raw data chunks. |

---

## 3. The `pip1:` Citation Standard for Wikipedia

### 3.1 Proposed Citation Syntax

We propose introducing the `pip1` parameter into the standard Wikipedia citation templates (`{{cite web}}`, `{{cite journal}}`, `{{cite book}}`):

```wikitext
{{cite web
  | title       = Declaration on the Foundations of Digital Longevity
  | author      = International Archival Working Group
  | date        = 2026-10-14
  | url         = https://example.org/declaration
  | archive-url = https://web.archive.org/web/20261014120000/https://example.org/declaration
  | pip1-urn    = urn:pip1:t:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069
  | pip1-bundle = urn:pip1:m:a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0
}}
```

### 3.2 Resolving and Verification Lifecycle
1. **Resolution**: A reader clicking the `pip1` link is directed to a decentralized resolution network (local `aethel` verifier, Internet Archive mirror, or Wikimedia toolserver).
2. **Immutable Guarantee**: Even if `example.org` vanishes and the Wayback snapshot is unavailable, any entity possessing the raw text or bundle can verify that it is the exact text cited on Wikipedia.

---

## 4. Internet Archive Ingestion Pipeline Integration

### 4.1 Ingestion Flow
When the Internet Archive crawler (Heritrix or Wayback SPN) archives an important document, article, or book:

1. **Extract Canonical Text**: The crawler passes the clean text through `CTF-1` normalization (Unicode 18.0.0 NFC, LF endings).
2. **Package as PIP-1 Bundle**: Merkle chunks (4,096 bytes) are computed; the byte-sorted manifest `PMF-1` is generated.
3. **Institutional Sealing**: Internet Archive seals the bundle with its institutional post-quantum signing key (SLH-DSA-SHAKE-256s or ML-DSA-87).
4. **Permanent Metadata Indexing**:
   - Store bundle under `s3://archive.org/items/pip1_<manifest_hex>/`
   - Expose endpoints:
     - `https://archive.org/download/pip1_<manifest_hex>/manifest.pmf`
     - `https://archive.org/download/pip1_<manifest_hex>/manuscript.txt`

### 4.2 Autonomous Mirroring and Cold Archival
Because PIP-1 bundles have **zero network calls** and include a standalone minimal verifier (`verify_minimal.py`), Internet Archive can distribute cold-storage tape and optical disc (M-DISC) replicas to libraries worldwide (e.g., Library of Congress, British Library, BnF). These bundles remain 100% auditable without internet connectivity.

---

## 5. Security & Trust Architecture

PIP-1 replaces institutional trust with mathematical proof:
1. **Four-Factor Verification Orthogonality**:
   - **Integrity**: Did the bits change? (Merkle root matching).
   - **Attribution**: Who signed it? (FIPS 204 / 205 cryptographic verification).
   - **History**: Is this an edition or revision? (Ancestry hash link).
   - **Time**: When was it attested? (External signed attestations, without relying on corruptible system clocks).
2. **Fail-Closed Verification**: If an algorithm ID is unrecognized, a chunk hash fails, or padding contains non-zero bytes, the verifier unconditionally rejects the bundle.

---

## 6. Implementation Roadmap for Global Partners

- **Phase I (Q1 2027)**: Pilot deployment with WikiProject Open Access and Internet Archive's Community Web Archivists.
- **Phase II (Q2 2027)**: Release of native browser extension and MediaWiki extension (`Extension:PermanentInk`) allowing one-click bundle verification in browser.
- **Phase III (Q3 2027)**: Formal submission to IETF for `urn:pip1` namespace registration and W3C Permanent Archival Identifiers working group.

---

*Preserve what matters. Name your writing by what it says.*
