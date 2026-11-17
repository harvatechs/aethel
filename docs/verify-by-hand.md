# Verifying a PIP-1 Bundle by Hand

This guide explains how to verify the cryptographic integrity of a Permanent Ink Protocol profile **pip-1** bundle from first principles using standard command-line tools (such as Python standard library, `openssl`, or `sha3sum`).

No specialized dependencies or toolchain installations are required.

---

## 1. Bundle Structure

A PIP-1 bundle is a directory named by its 64-hex manifest identifier:

```text
e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d/
├── manifest.pip     # Plain-text, byte-sorted manifest
├── text.md          # Canonical text file (CTF-1)
└── author.sig       # Detached signature envelope (SGE-1)
```

---

## 2. Step 1: Verify the Manifest Identifier (Check V1)

In PIP-1, all cryptographic hashing uses **FIPS 202 SHA3-256** with 1-byte length-prefixed domain labels:
`H(label, x) = SHA3-256(chr(len(label)) || label || x)`

For the manifest:
- Domain label: `pip1.manifest` (13 bytes)
- Length prefix: `\x0d` (0x0d = 13)
- Message: `\x0dpip1.manifest` followed by the raw bytes of `manifest.pip`

Using standard Python:

```python
import hashlib
from pathlib import Path

bundle_dir = Path("e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d")
manifest_bytes = (bundle_dir / "manifest.pip").read_bytes()

prefix = b"\x0dpip1.manifest"
digest = hashlib.sha3_256(prefix + manifest_bytes).hexdigest()

print(f"Computed Manifest ID: {digest}")
print(f"Directory Name:       {bundle_dir.name}")
assert digest == bundle_dir.name, "Manifest ID does not match directory name!"
```

---

## 3. Step 2: Verify the Text Identifier (Check V2)

The text identifier (`pip1:t:<64-hex>`) is derived from the canonical text (`text.md` or `text.txt`) via a balanced binary Merkle tree over 4,096-byte chunks:
`text_id = H("pip1.text", u64be(len(text)) || blob_root)`

For a text smaller than or equal to 4,096 bytes (a single chunk):
1. **Leaf root**:
   `root = H("pip1.leaf", text_bytes) = SHA3-256(b"\x09pip1.leaf" + text_bytes)`
2. **Text identifier**:
   `u64_len = len(text_bytes).to_bytes(8, "big")`
   `text_id = H("pip1.text", u64_len + root) = SHA3-256(b"\x09pip1.text" + u64_len + root)`

Using Python:

```python
text_bytes = (bundle_dir / "text.md").read_bytes()

# 1. Compute leaf root
leaf_prefix = b"\x09pip1.leaf"
leaf_hash = hashlib.sha3_256(leaf_prefix + text_bytes).digest()

# 2. Compute text ID
text_prefix = b"\x09pip1.text"
u64_len = len(text_bytes).to_bytes(8, "big")
text_id = hashlib.sha3_256(text_prefix + u64_len + leaf_hash).hexdigest()

print(f"Computed Text ID: pip1:t:{text_id}")
```

Inspect `manifest.pip` and verify that the `text` line contains this exact identifier:

```text
text pip1:t:8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba 48 text.md
```

---

## 4. Step 3: Verify Asset Identifiers (Check V3)

If the bundle declares assets in `manifest.pip`:
```text
asset figure1.svg pip1:a:334f590bc93158c3... 1024
```

Each asset is chunked in 4,096-byte blocks and hashed using the `pip1.asset` label prefix (`b"\x0apip1.asset"`):

```python
asset_bytes = (bundle_dir / "assets" / "figure1.svg").read_bytes()
asset_root = hashlib.sha3_256(b"\x09pip1.leaf" + asset_bytes).digest()
u64_asset_len = len(asset_bytes).to_bytes(8, "big")
asset_id = hashlib.sha3_256(b"\x0apip1.asset" + u64_asset_len + asset_root).hexdigest()
print(f"Asset ID: pip1:a:{asset_id}")
```

---

## 5. Step 4: Verify Detached Signature Envelopes (Check V6)

Detached signatures (`*.sig`) use the SGE-1 format:

```text
sge-1
alg ml-dsa-87
key pip1:k:a2c5...
sig <base64-encoded-signature>
```

In PIP-1, the signed message $M'$ is defined as:
`M' = u8(role) || raw_32_byte_manifest_digest`
where `role = 0x01` (author role).

The signature is verified under the context string `b"pip1.sig"`.

Using `cryptography` in Python:

```python
from cryptography.hazmat.primitives.asymmetric import mldsa

# Load public key bytes from manifest or key record
# Load signature bytes from author.sig
# pk = mldsa.MLDSA87PublicKey.from_public_bytes(public_key_bytes)
# pk.verify(signature_bytes, b"\x01" + bytes.fromhex(manifest_digest), context=b"pip1.sig")
```

---

## 6. Using the Standalone Minimal Verifier Script

To verify all V1, V2, and V3 integrity checks in a single command using only the Python standard library, run:

```bash
python scripts/verify_minimal.py <path_to_bundle_directory>
```

The script parses the manifest, verifies line sorting, recomputes the Merkle roots for all texts and assets, and outputs a JSON report with exact pass/fail verdicts for each check.
