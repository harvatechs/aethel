# tests/ — Test Data, Provenance and How to Audit It

`tests/vectors/` and `tests/fixtures/` are **read-only oracles** (R-PROTO-02). Only the Spec Guardian changes them, only through this file's procedure, and never to make a test pass.

## 1. Provenance

| File or section | Source | Authority |
|---|---|---|
| `pip1-vectors.json` → `constants`, `ctf1`, `assets`, `manifests`, `signature_ml_dsa_87`, `locators`, `asset_names`, `attribution` | Yellow Paper Appendix A.1–A.5 (rc.3). Recomputed from first principles on 14 Nov 2026 with `hashlib.sha3_256` and `unicodedata2` 18.0.0; the A.2 signature was also verified by three independent ML-DSA libraries | **Normative values** |
| `→ pack_generated` (`blob_sizes`, `ml_dsa_65`, dual-family text id) | Produced by `tools/gen_pack_data.py`, cross-checked as stated in each entry | Regression data. Never overrides the paper |
| `→ grammar_cases_derived_from_abnf` | Derived from the paper's ABNF by this pack | If it disagrees with the paper, the paper wins: raise a Spec Query |
| `→ unicode_drift_canary` | Computed from `unicodedata2` 18.0.0 (312,389 scalars, 735 ranges) | Drift detector only |
| `→ informative_site_vectors` | `aethel-codex.pages.dev` landing page (the manifesto, 834 bytes, `pip1:t:de93176d…fd4b`, also reproduced separately) | Informative |
| `pip1-slh-dsa-vectors.json` | Pack-generated: deterministic signatures from the independent pure-Python `slh-dsa` 0.2.5, verified by `pqcrypto` 1.0.0; `pqcrypto` signatures verified by the oracle | Regression data; propose to the Working Group (OD-7) |
| `fixtures/*` | Pack-generated bundles, verified by an independent mini-verifier | Regression data |

Every YP-defined value is machine-readable; nothing here needs the PDF to run.

## 2. Fixtures (`fixtures/<scenario>/<manifest-id>/` plus `expected.json`)

`expected.json` encodes each check as `STATUS` or `STATUS:REASON`. `cls` is the attribution class (`class` is a Python keyword).

| Scenario | Shows | Expected |
|---|---|---|
| `genesis-attributed` | The A.3 genesis manifest, text T1, asset `figure1.svg`, ML-DSA-87 author signature (the A.2 signature) | Integrity PASS · Attributed (1 of 1) · V5 `SKIPPED:NO_PARENTS` · V8 `SKIPPED:NO_TIME_EVIDENCE` |
| `genesis-unsigned` | Same bundle without `signatures/` | Integrity PASS · Unattributed (0 of 1) · V6 `SKIPPED:NO_SIGNATURES`; `--require-attributed` exits 1 |
| `revision` | The A.3 revision (text T2, beacon line, parent and work), signed | Integrity PASS · Attributed · V8 `WARN:BEACON_UNVERIFIED`; V5 `SKIPPED:PARENTS_UNAVAILABLE`, or PASS with `--parents` pointing at the genesis bundle |
| `dual-family` | Two declared authors: ML-DSA-87 and SLH-DSA-SHA2-256s, both signed | Dual-family (2 of 2) · Keccak-independent **true** |
| `partial-attribution` | Same manifest, only the ML-DSA-87 signature present | Partially attributed (1 of 2) · Keccak-independent false; `--require-attributed` exits 1 |

**Test keys.** The ML-DSA key derives from the public seed `000102…1f`. The SLH-DSA keys in the vectors file include `test_only_secret_key_hex`. They are public. **Never use them for real work**, and never let a tool treat them as trusted.

## 3. Audit it yourself

Hand check of vector T1 with the standard library only (prints `pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba`):

```python
import hashlib


def H(label, x):
    return hashlib.sha3_256(bytes([len(label)]) + label + x).digest()


text = b"# The Aethel Codex\n\nWrite once. Verify forever.\n"
leaf = H(b"pip1.leaf", text)  # one chunk, so the root equals the leaf
print("pip1:t:" + H(b"pip1.text", len(text).to_bytes(8, "big") + leaf).hex())
```

A fixture's directory name must equal `H(b"pip1.manifest", manifest.pip bytes)` (hex). `tools/recompute_yp_vectors.py` recomputes **every** Yellow Paper value and cross-validates the ML-DSA-87 signature across `dilithium-py`, `cryptography` and `pqcrypto`; it exits non-zero on any difference. It is the first tool to run when RB-1 or RB-13 applies.

## 4. Checksums

```
sha256sum -c tests/vectors/SHA256SUMS      # run from the repository root
sha256sum -c tests/fixtures/SHA256SUMS
```

CI runs both. `.gitattributes` marks these paths `-text` so no checkout rewrites a byte.

## 5. Regeneration policy

1. Yellow Paper values are never regenerated: they come from the paper.
2. Pack-generated data is regenerated only when the Yellow Paper changes or a bug in the data is proven. Use `PACK_ROOT=/tmp/regen uv run python tools/gen_pack_data.py`, review the diff with the Spec Guardian and the owner, then update both `SHA256SUMS` files in the same commit with an entry in `decision-log.md`.
3. Regeneration draws new random SLH-DSA keys, so the dual-family and partial-attribution manifest identifiers change. That is expected and must be explained in the commit.
4. When the Working Group publishes SLH-DSA vectors or NIST validation data, add them as new files and cross-check; do not replace these.
