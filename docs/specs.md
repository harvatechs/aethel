# specs.md — Implementation Specification

Derived from **PIP-YP-1 v1.0.0-rc.3**. If this file and the Yellow Paper disagree, the Yellow Paper wins: stop and raise a Spec Query (`AGENTS.md` §6).

Tags used throughout:

- **[YP §x]** normative text of the Yellow Paper.
- **[PACK]** a choice this pack makes where the paper is silent. Recorded in `decision-log.md` (Q-xx).
- **[TOOL]** a tool-level file format. It is **not** part of the protocol and must be labelled as such everywhere.
- **[VERIFIED]** executed on 14 November 2026.

Python blocks are reference snippets. Each reproduces the vectors in `tests/vectors/`. Keep their behaviour exactly; rename freely. MUST/SHOULD follow RFC 2119.

---

## 1. Scope

The tool implements all four conformance roles of [YP §14.1]: **Canonicalizer**, **Manifest producer**, **Signer**, **Verifier**. It also provides tool-level conveniences (key files, chunk proofs). It implements no storage, network, curation, identity or time-service behaviour. [YP §1.3] lists these as consumers of PIP-1 identifiers, not parts of it.

---

## 2. Byte conventions and constants

```python
import hashlib


def lp(label: bytes) -> bytes:  # LP(L) = u8(len(L)) ‖ L, 1..255 bytes
    if not 1 <= len(label) <= 255:
        raise ValueError("label length")
    return bytes([len(label)]) + label


def H(label: bytes, x: bytes) -> bytes:  # H(L, x) = SHA3-256(LP(L) ‖ x)   [YP §0]
    return hashlib.sha3_256(lp(label) + x).digest()


def u64be(n: int) -> bytes:  # raises OverflowError if n >= 2**64
    return n.to_bytes(8, "big")
```

All constants live once, in `constants.py` (R-PROTO-04).

| Constant | Value | Notes |
|---|---|---|
| `LABEL_LEAF` / `LABEL_NODE` / `LABEL_TEXT` | `pip1.leaf` / `pip1.node` / `pip1.text` | length byte `0x09` |
| `LABEL_ASSET` | `pip1.asset` | `0x0A` |
| `LABEL_MANIFEST` | `pip1.manifest` | `0x0D` |
| `LABEL_KEY` | `pip1.key` | `0x08` |
| `SIG_CONTEXT` | `pip1.sig` (8 ASCII bytes) | **Not a hash label.** Passed to ML-DSA/SLH-DSA as the context string |
| `CHUNK_SIZE` | 4096 | Frozen |
| `UNICODE_VERSION` | `18.0.0` | Frozen |
| Max value text | title 512 B · license 256 B · asset name 128 B · beacon value 64 B | Bytes of UTF-8, not characters |

**Algorithms** [YP §3.1, §3.4]. Reject every other `alg_id`.

| `alg_id` | Name | Envelope name | Public key | Signature | Secret form held by the tool | Backend |
|---|---|---|---|---|---|---|
| `0x01` | ML-DSA-65 | `ml-dsa-65` | 1,952 | 3,309 | 32-byte seed | `cryptography` |
| `0x02` | ML-DSA-87 (primary) | `ml-dsa-87` | 2,592 | 4,627 | 32-byte seed | `cryptography` |
| `0x10` | SLH-DSA-SHAKE-256s | `slh-dsa-shake-256s` | 64 | 29,792 | 128-byte secret key | `pqcrypto` |
| `0x11` | SLH-DSA-SHA2-256s (recommended anchor) | `slh-dsa-sha2-256s` | 64 | 29,792 | 128-byte secret key | `pqcrypto` |

**Roles**: `0x01` author, `0x02` contributor, `0x03` translator, `0x04` endorser. `0x00` is reserved: reject. `0x05–0x7F` registry-assigned and `0x80–0xFF` private: accept in envelopes as `0xHH`, verify the signature normally, report separately, never count toward attribution.

---

## 3. Unicode layer (`unicode18.py`, `_repertoire.py`)

**U-1 Version guard [YP §4.4].** At import, assert `unicodedata2.unidata_version == "18.0.0"`; otherwise raise a fatal `UnicodeDataMismatch` (CLI exit 70, message names both versions). **[VERIFIED]** `unicodedata2 18.0.0` reports `18.0.0`; Python 3.12's stdlib `unicodedata` reports `15.0.0`, which is why the stdlib is banned.

**U-2 Forbidden set [YP §4.3].** Exactly:

```python
def is_forbidden(cp: int) -> bool:
    return (
        cp <= 0x08
        or cp in (0x0B, 0x0C)
        or 0x0E <= cp <= 0x1F  # C0 except TAB LF CR
        or 0x7F <= cp <= 0x9F  # DEL and C1 (incl. U+0085)
        or cp == 0xFEFF  # BOM / ZWNBSP after step 1
        or 0xFDD0 <= cp <= 0xFDEF  # noncharacters
        or (cp & 0xFFFE) == 0xFFFE
    )  # last two scalars of every plane
```

**U-3 Unassigned [YP §4.2 step 3].** `unicodedata2.category(chr(cp)) == "Cn"`. This includes all noncharacters.

**U-4 Accepted on purpose [YP §4.3]:** TAB, LF, CR (until step 4), U+2028, U+2029 (ordinary characters, never line terminators), ZWJ, ZWNJ, LRM, RLM, ALM, bidirectional controls and isolates, private-use characters, U+FFFD. Rejecting any of them is a defect.

**U-5 Generated repertoire table.** `tools/gen_repertoire.py` generates `_repertoire.py` (sorted `Cn` ranges plus a SHA-256) **from `unicodedata2`**, never by hand. `unicode18.py` compiles it into one regex character class for speed. A unit test sweeps all 0x110000 scalars and requires the table to equal the live `unicodedata2` categories, and requires the table's digest to equal `unicode_drift_canary.sha256` in `pip1-vectors.json` (312,389 non-`Cn` scalars in 735 ranges). **[VERIFIED]**

**U-6 Precedence [PACK, Q-01].** Check the forbidden set over the whole text first; only if none is found check unassigned. A noncharacter is both forbidden and `Cn`: it reports `E_FORBIDDEN_CODEPOINT` (matches the vector for U+FDD0).

**U-7 Diagnostics [PACK].** Every rejection carries `codepoint` (`U+XXXX`), `line`, `column` (1-based, lines split on LF, CR LF or CR, counted in code points) and, for UTF-8 failures, the byte `offset`. Use these in messages.

---

## 4. CTF-1 (`ctf1.py`) [YP §4]

```python
def canonicalize(data: bytes) -> tuple[bytes, CanonReport]:
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]  # 1  once
    try:
        text = data.decode("utf-8")  # 2  strict: never errors="replace"
    except UnicodeDecodeError as e:
        raise CanonicalizationError("E_INVALID_UTF8", offset=e.start) from None
    reject_forbidden_then_unassigned(text)  # 3  U-2, U-3, U-6
    crlf = text.count("\r\n")
    lone_cr = text.count("\r") - crlf
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # 4  exactly these two replacements
    normalized = unicodedata2.normalize("NFC", text)  # 5  whole text
    if not normalized:
        raise CanonicalizationError("E_EMPTY_TEXT")  # 6
    final_lf = not normalized.endswith("\n")
    if final_lf:
        normalized += "\n"  #    existing trailing blank lines are kept
    return normalized.encode("utf-8"), CanonReport(...)  # 7  no BOM
```

- Errors: `E_INVALID_UTF8`, `E_FORBIDDEN_CODEPOINT`, `E_UNASSIGNED_CODEPOINT`, `E_EMPTY_TEXT`.
- `CanonReport` [PACK]: `input_bytes, output_bytes, bom_removed, crlf_converted, lone_cr_converted, nfc_changed, final_lf_added`. It feeds `aethel canon --report` and teaches the user what was normalised.
- **Properties to test:** determinism; **fixed point** `canonicalize(C) == C`; output has no CR, is NFC, ends with LF, contains no forbidden or unassigned scalar.
- **Whole-text, in memory**, limited by `MAX_TEXT_BYTES` (§12). Assets are never passed through CTF-1.
- **Never use** `splitlines`, `strip`, `casefold`, NFKC, `open(..., "r")`, `errors=` arguments. See `what-not-to-do.md` §1.
- **Acceptance:** T1–T3, 12 negatives, 20,000-input fixed-point property, `NormalizationTest.txt` for 18.0.0 (`https://www.unicode.org/Public/18.0.0/ucd/NormalizationTest.txt`, fetched by a dev tool and pinned by SHA-256; verify the URL when fetching).

---

## 5. Blob identifiers and Merkle trees (`merkle.py`, `pid.py`) [YP §5]

**Chunking.** Empty data has exactly one empty chunk (assets only; canonical text is never empty). Otherwise consecutive 4,096-byte chunks, the last holding 1–4,096 bytes. Boundaries ignore characters.

**Tree.** `leaf = H(LABEL_LEAF, chunk)`. For `n > 1`, `k` is the largest power of two strictly less than `n`, and `MTH = H(LABEL_NODE, MTH(left k) ‖ MTH(rest))`. No node is ever duplicated or padded. Do not use any third-party Merkle library: Bitcoin-style trees duplicate nodes and differ from this one.

**Blob id.** `H(label, u64be(len) ‖ root)` with `LABEL_TEXT` for canonical text and `LABEL_ASSET` for assets.

```python
class TreeHasher:  # streaming, O(log n) memory. [VERIFIED] equals the recursive definition
    def __init__(self):  # for 40+ sizes incl. 0, 1, 4095, 4096, 4097, 8192, 8193, 12288, 20000
        self._stack: list[tuple[int, bytes]] = []  # (height, hash); heights strictly decrease
        self._buf = bytearray()
        self.length = 0
        self._leaves = 0

    def _push(self, chunk: bytes) -> None:
        h, height = H(LABEL_LEAF, chunk), 0
        self._leaves += 1
        while self._stack and self._stack[-1][0] == height:
            _, left = self._stack.pop()
            h, height = H(LABEL_NODE, left + h), height + 1
        self._stack.append((height, h))

    def update(self, data) -> None:
        self.length += len(data)
        self._buf += data
        while len(self._buf) >= CHUNK_SIZE:
            self._push(bytes(self._buf[:CHUNK_SIZE]))
            del self._buf[:CHUNK_SIZE]

    def root(self) -> bytes:  # call once
        if self._buf or self._leaves == 0:
            self._push(bytes(self._buf))
            self._buf.clear()
        acc = self._stack[-1][1]
        for _, h in reversed(self._stack[:-1]):
            acc = H(LABEL_NODE, h + acc)
        return acc


def merkle_root(leaves):  # the specification form; used by proofs and as the test oracle
    n = len(leaves)
    if n == 1:
        return leaves[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return H(LABEL_NODE, merkle_root(leaves[:k]) + merkle_root(leaves[k:]))


def audit_path(m, leaves):  # [YP §5.4] leaf level first
    n = len(leaves)
    if n == 1:
        return []
    k = 1 << ((n - 1).bit_length() - 1)
    return (
        audit_path(m, leaves[:k]) + [merkle_root(leaves[k:])]
        if m < k
        else audit_path(m - k, leaves[k:]) + [merkle_root(leaves[:k])]
    )


def root_from_path(m, n, h, path):  # None means structural FAIL
    if n == 1:
        return h if not path else None
    if not path:
        return None
    k = 1 << ((n - 1).bit_length() - 1)
    s, rest = path[-1], path[:-1]
    if m < k:
        r = root_from_path(m, k, h, rest)
        return None if r is None else H(LABEL_NODE, r + s)
    r = root_from_path(m - k, n - k, h, rest)
    return None if r is None else H(LABEL_NODE, s + r)
```

**Chunk-proof verification** [YP §5.4], in order: `n = max(1, ceil(N/4096))`; reject if `m >= n`; chunk length must be 4096 when `m < n-1`, `N − 4096(n−1)` when `m = n−1`, 0 when `N = 0`; compute the root with `root_from_path(m, n, H(LABEL_LEAF, chunk), path)`; reject on `None`; accept iff `H(label, u64be(N) ‖ root) == id`. For very large blobs build proofs bottom-up from a leaf-hash list; the recursive form above is the oracle the iterative form is tested against.

**Streaming rule.** Feed 1 MiB blocks. **[VERIFIED]** ≈ 260 MiB/s on the preparation machine.

**PIDs** [YP §6.1]: `pip1:<type>:<64 lowercase hex>` with `m` manifest, `t` canonical text, `a` asset, `k` key. Parse with `re.fullmatch(r"pip1:([mtak]):([0-9a-f]{64})", s)`. Upper-case hex is **not** a PID; never normalise case. `Pid` is a frozen value type holding `type` and 32-byte `digest`; `str(pid)` is the canonical form.
**Key id** [YP §6.2]: `H(LABEL_KEY, u8(alg_id) ‖ public_key)`, public key of exactly the table length.

---

## 6. Citations (`citations.py`) [YP §6.3]

```python
CITE_RE = re.compile(
    r"cite:(pip1:[mta]:[0-9a-f]{64})(?:#b=(0|[1-9][0-9]*)-(0|[1-9][0-9]*))?"
)  # fullmatch only
INLINE_RE = re.compile(
    r"(?<![A-Za-z0-9+.\-])cite:pip1:[mta]:[0-9a-f]{64}(?![0-9A-Fa-f])"
)  # search/finditer
```

- Type `k` is not citable. Upper-case hex is not a PID. A trailing newline must not match (use `fullmatch`; `$` matches before a final newline).
- **Syntax errors** (code `CITE_SYNTAX`): leading zeros, missing end, unknown locator kind, `start >= end` [PACK, Q-02: the paper classifies `start >= end` as syntax in A.5 and as a range error in §6.3; both reject, we reject at parse], numbers above 2⁶⁴−1.
- **Range errors** (`CITE_RANGE`) given the blob: `end > length`; for types `m` and `t` also `start` on a UTF-8 continuation byte (`0x80–0xBF`), or `end < length` with the byte at `end` a continuation byte. Type `a` is a plain byte range. Only bytes at `start` and `end` are needed, so a verifier using chunk proofs may need the chunk after the last cited byte.
- Verified against the A.5 table **[VERIFIED]**: `0-3`, `3-5`, `3-6`, `0-26` valid on T2; `0-4`, `4-9`, `5-5`, `0-27` invalid.
- Inline scanning is **lexical only**: it finds the pid part and ignores locators. A manifest `cite` field is authoritative; inline URIs missing from it produce the warning `CITE_UNLISTED`.

---

## 7. Manifest PMF-1 (`manifest.py`) [YP §7]

**Form:** UTF-8, first line `pip-manifest 1`, then `key SP value LF` lines in fixed order, no blank lines, comments, unknown keys or alternative spellings. The manifest id is `H(LABEL_MANIFEST, exact bytes)`.

**Order and counts:** `profile`(1) `markup`(1) `lang`(1) `title`(1) `license`(1) `beacon`(0–1) `text`(1) `work`(0–1) `parent`(0+) `author`(0+) `derivative`(0+) `asset`(0+) `cite`(0+).

**Field grammars.** Full-match each value. ASCII only except `title` and `license`. Use `[0-9]`, never `\d`.

```
profile    pip-1                              (anything else token-shaped [a-z0-9][a-z0-9.-]* → E_UNKNOWN_PROFILE)
markup     pip-md-1 | pip-tex-1 | pip-txt-1
lang       [a-z]{2,3}(-([A-Z][a-z]{3}|[A-Z]{2}|[0-9]{3}|[a-z0-9]{2,8}))*       ≤ 35 bytes, lexical only, "und" allowed
title      value text, 1–512 bytes          license  value text, 1–256 bytes
beacon     bsrc SP uint SP bval      bsrc [a-z0-9][a-z0-9._-]{0,63}     bval ([0-9a-f]{2}){1,64}   (even length)
text       pip1:t:<64hex> SP uint            uint ≥ 1
work       pip1:m:<64hex>                    present iff at least one parent
parent     pip1:m:<64hex>
author     pip1:k:<64hex>
derivative translation|adaptation|anthology|commentary SP pip1:m:<64hex>
asset      aname SP pip1:a:<64hex> SP uint SP media
             aname (?!\.{1,2}\Z)[A-Za-z0-9._-]{1,128}      media  mtok/mtok  with mtok [a-z0-9][a-z0-9!#$&+\-.^_]{0,126}
cite       pip1:m:<64hex> | pip1:t:<64hex> | pip1:a:<64hex>
uint       0 | [1-9][0-9]*        and ≤ 2^64 − 1 (above → E_INTEGER_RANGE; a syntactic failure → E_BAD_VALUE)
```

**Value text** [YP §7.4]: assigned scalars, none forbidden (§3), no TAB/CR/LF, already NFC, must not begin or end with U+0020 [PACK, Q-09: "a space" means U+0020 only; never call `.strip()`], length measured in UTF-8 bytes.

**Ordering:** `parent`, `author`, `derivative`, `cite` lines ascend by the UTF-8 bytes of the text after the key and never repeat. `asset` lines ascend by asset name and names are unique.

**Parse algorithm (strict, deterministic error precedence) [PACK, Q-03].**

1. Decode strictly → `E_INVALID_UTF8`.
2. Any CR, no final LF, or an empty line → `E_BAD_LINES`.
3. First line ≠ `pip-manifest 1` → `E_BAD_MAGIC`.
4. For each later line in order: no space → `E_BAD_LINES`; unknown key → `E_UNKNOWN_KEY`; key rank lower than the previous, or a repeated singleton → `E_FIELD_ORDER`; then the value grammar (`E_UNKNOWN_PROFILE`, `E_BAD_VALUE`, `E_INTEGER_RANGE`).
5. After the last line: a missing mandatory field → `E_MISSING_FIELD`; `work` without `parent` or the reverse → `E_WORK_PARENT_RULE`; list ordering or duplicates → `E_NOT_SORTED_OR_UNIQUE`.
6. Re-serialise and compare byte for byte; mismatch → `E_ROUNDTRIP` (unreachable by construction; test it by injecting a faulty serializer).

**[VERIFIED]** this procedure reproduces all eight mutation vectors of A.3 and accepts both A.3 manifests (434 and 500 bytes) and the text length 2⁶⁴−1.

**Builder rules.** Sort, then drop *identical* duplicate lines. Two assets with one name and different content are an error. A genesis manifest has no `work` and no `parent`. A revision sets `work` to the parent's work id (the parent's own manifest id if the parent is a genesis) and one or more `parent` lines. Producers must pass their own output through the strict parser before emitting (R-PROTO-06). Never emit a field the grammar lacks.

---

## 8. Signatures, envelopes, backends (`signing.py`, `envelope.py`, `backends/`) [YP §9, §10.3]

**Signed message** [YP §9.1]: `M = u8(role) ‖ manifest_digest` where `manifest_digest` is the **raw 32 bytes**, not hex. 33 bytes in total. Pure ML-DSA / SLH-DSA with context `pip1.sig`. No pre-hash variant, ever. **[VERIFIED]** `M' = 00 08 70697031 2e736967 ‖ M` reproduces the digest in A.2.

**Backend contract** (`backends/base.py`):

```python
class SignatureBackend(Protocol):
    alg_id: int; name: str; public_key_size: int; signature_size: int
    def generate(self) -> tuple[bytes, bytes]: ...                         # (secret, public)
    def public_from_secret(self, secret: bytes) -> bytes: ...
    def sign(self, secret: bytes, message: bytes, context: bytes) -> bytes # hedged (fresh randomness)
    def verify(self, public: bytes, message: bytes, signature: bytes, context: bytes) -> bool
```

`verify` returns `False` for an invalid signature and raises only for programmer errors. Check exact public-key and signature lengths **before** calling the library.

| | `cryptography` ≥ 50.0.2 (ML-DSA) | `pqcrypto` ≥ 1.0.0 (SLH-DSA) |
|---|---|---|
| Classes / modules | `mldsa.MLDSA65/87PrivateKey`, `PublicKey` | `pqcrypto.sign.slh_dsa_sha2_256s`, `slh_dsa_shake_256s` |
| Secret | `from_seed_bytes(seed)`, `private_bytes_raw()` returns the 32-byte seed | `keygen()` returns `(pk, sk)`; `sk` is 128 bytes; `pk == sk[64:]` |
| Sign | `key.sign(message, context)` | `sign(sk, message, context=ctx)` |
| Verify | `pub.verify(sig, message, context)`; raises `cryptography.exceptions.InvalidSignature` | `verify(pk_bytes, message, sig, context=ctx)` returns `None`; raises `pqcrypto.InvalidSignatureError` |
| Trap | no deterministic mode | `InvalidSignatureError` **subclasses `ValueError`**, as does the wrong-length error. Check lengths first and catch `InvalidSignatureError` specifically. Pass raw `bytes`, not the `PublicKey` wrapper. Never pass `hash_algorithm` |

**[VERIFIED]** interoperability: ML-DSA-87 signatures from `dilithium-py`, `cryptography` and `pqcrypto` verify across all three, including the paper's deterministic signature; wrong context, other role byte and tampered signatures are rejected. SLH-DSA (both variants) signatures from the independent `slh-dsa` oracle verify under `pqcrypto` and the reverse. Deterministic signing exists only in the test oracles (`dilithium-py`, `slh-dsa`), never in `src/`.

**Sign procedure** [YP §9.2]: generate keys with an approved RNG (the backend's); compute the manifest id from the exact published bytes; form `M`; sign; **verify before releasing** (R-SEC-02); then emit the envelope.

**Strict Base64 [PACK, Q-08].** Decode with `base64.b64decode(s, validate=True)` and require `b64encode(decoded) == s` (rejects non-canonical padding and stray bits).

**Envelope SGE-1** [YP §9.4]. Seven LF-terminated lines, fixed order:

```
pip-signature 1
manifest pip1:m:<64hex>
role author | contributor | translator | endorser | 0xHH        (HH lowercase hex)
alg ml-dsa-65 | ml-dsa-87 | slh-dsa-shake-256s | slh-dsa-sha2-256s
key pip1:k:<64hex>
public-key <base64>
signature <base64>
```

Parsing rules [PACK, Q-04]: LF only, no blank lines, size ≤ `MAX_ENVELOPE_BYTES`, strict Base64; both spellings of roles `0x01–0x04` are accepted and normalise to the number; `0x00` is invalid; producers emit names for `0x01–0x04` and `0xHH` otherwise. The envelope is neither hashed nor signed. Filename convention [TOOL]: `signatures/<role>-<alg>-<first 16 hex of key id>.sig`.

**Verifying one envelope** [YP §9.3]; codes are normative for accept/reject, `detail` strings are free:

1. Parse fails, or role `0x00` → `ENVELOPE_INVALID`.
2. `alg` not in the table → `ALG_UNKNOWN`.
3. Public key length ≠ table → `SIG_INVALID` (`detail=public_key_length`).
4. `H(LABEL_KEY, u8(alg_id) ‖ pk)` ≠ envelope `key` → `KEY_MISMATCH`.
5. Signature length ≠ table → `SIG_INVALID`.
6. Envelope `manifest` ≠ the bundle's computed manifest id → `SIG_INVALID` (`detail=manifest_mismatch`) [PACK].
7. Backend verification with `M` and context `pip1.sig` fails → `SIG_INVALID`.

**Attestation ATT-1** [YP §10.3]:

```
pip-attestation 1
manifest pip1:m:<64hex>
kind <[a-z0-9][a-z0-9-]{0,31}>
proof <base64>
```

`rfc3161` and `opentimestamps` are reserved names; PIP-1 defines no procedure for any kind. The tool therefore **parses, stores and reports every attestation as present and unverified**. It never claims a time. Beacon sources are likewise unregistered ([YP §10.2, §15]); a `beacon` line is carried and reported "present, unchecked".

---

## 9. Verification engine (`verify.py`) [YP §11] and report semantics

Always run every check that its inputs allow. A check that cannot run reports `SKIPPED` with a reason; it never silently passes.

| Check | PASS | WARN | FAIL | SKIPPED |
|---|---|---|---|---|
| **V1 Manifest** | parses strictly; id computed; if the directory name is 64-hex it equals the id | directory name is not 64-hex (note only) | `MANIFEST_MISSING`, `MANIFEST_INVALID` (detail = parse error code), `ID_MISMATCH` | – |
| **V2 Text** | text file equals its own CTF-1 output; length and id equal the manifest | `EXTRA_FILE`: a `text.*` file that does not match `markup` | `TEXT_MISSING`, `TEXT_NOT_CANONICAL` (detail = CTF-1 error or "differs"), `TEXT_LENGTH`, `TEXT_MISMATCH` | `DEPENDS_ON_V1`, `LIMIT_EXCEEDED` |
| **V3 Assets** | every asset line has a file with matching length and id | `ASSET_EXTRA`: unlisted regular files in `assets/` | `ASSET_MISSING`, `ASSET_MISMATCH` (length or id) | `DEPENDS_ON_V1`, `LIMIT_EXCEEDED` |
| **V4 Citations** | inline cites all listed | `CITE_UNLISTED`, `CITE_LOCATOR_INVALID` | – | `DEPENDS_ON_V1` |
| **V5 History** | all parents available and share the work id | – | `WORK_MISMATCH` | `NO_PARENTS` (genesis), `PARENTS_UNAVAILABLE`, `DEPENDS_ON_V1` |
| **V6 Signatures** | ≥ 1 envelope and every one verifies | `EXTRA_FILE`: other files in `signatures/` | any envelope fails (per-envelope code) | `NO_SIGNATURES`, `DEPENDS_ON_V1` |
| **V7 Attribution** | always computed (PASS means "computed"); class and per-key list are data | – | – | `DEPENDS_ON_V1` |
| **V8 Time** | ≥ 1 item and all verified (not reachable in the MVP) | any item present but unverified: `BEACON_UNVERIFIED`, `ATT_UNVERIFIED`, `EXTRA_FILE` (other files in `attestations/`) | `BEACON_FAILED`, `ATT_FAILED` (not reachable in the MVP) | `NO_TIME_EVIDENCE` |

[PACK, Q-05/Q-06/Q-07]: genesis V5 is `SKIPPED:NO_PARENTS` (literal reading of "where parents are available"); V6 aggregates per-envelope results; a limit hit is `SKIPPED:LIMIT_EXCEEDED` and is reported, never PASS or FAIL.

**Summaries (never collapse them into one verdict) [YP §11.3]:**

- **Integrity:** `FAIL` if any of V1–V3 failed; else `INCONCLUSIVE` if any was skipped for `LIMIT_EXCEEDED`; else `PASS`. WARN does not fail integrity.
- **Attribution** (V7): computed as follows.

```
declared = author key ids in the manifest
valid    = {key_id: alg} for envelopes that verified, have role 0x01, and whose key is in declared   (a key counts once)
n, m = len(declared), len(valid)
class = Unattributed            if m == 0                               (including n == 0)
        Partially attributed    if 0 < m < n          # always list every declared key as signed or missing
        Dual-family             if m == n and the algs include an ML-DSA and an SLH-DSA (either variant)
        Attributed              if m == n otherwise
keccak_independent = any(alg == "slh-dsa-sha2-256s" for alg in valid.values())     # independent of class
other_signatures = verified envelopes of other roles or by undeclared keys, reported separately
```

  **[VERIFIED]** against all seven rows of A.5 and the five golden bundles.
- **History:** V5 with its parents' sources. **Time:** V8, one statement per item with its source, and the sentence "PIP-1 never produces a time value of its own".

**Required behaviour of optional gates:** `--require-attributed` (class ≥ Attributed), `--require-dual-family`. They change the exit code only, never the check statuses.

**Parents** are supplied with `--parents DIR` (a directory of bundles). The verifier never fetches anything.

---

## 10. Bundles (`bundle.py`) [YP §11.1, informative; adopted as the on-disk format]

```
<manifest id, 64 lowercase hex>/
  manifest.pip              exact manifest bytes
  text.md | text.tex | text.txt    exact canonical text bytes, extension chosen by `markup`
  assets/<name>             raw bytes of each asset
  signatures/*.sig          SGE-1 envelopes
  attestations/*.att        ATT-1 envelopes
```

- **Reading untrusted bundles [PACK, Q-10]:** `lstat` every path; never follow symlinks; accept regular files only (anything else: `UNSAFE_PATH`, a V3/V6 failure for that item); build asset paths only from names that passed the asset-name grammar; ignore non-`.sig`/`.att` files in those directories with a `EXTRA_FILE` warning; exactly one `text.*` matching `markup`.
- **Writing:** build in a sibling temporary directory, `fsync`, then rename. If the target exists with identical content, succeed (content addressing makes this safe); if it differs, fail. Never overwrite. Refuse asset names that collide on a case-insensitive filesystem.
- Files are written in binary mode. Nothing in a bundle depends on file times or permissions.

---

## 11. Determinism

Same manuscript bytes and metadata ⇒ identical canonical text, text id, manifest bytes and manifest id on every OS and Python version. Signatures are hedged and differ between runs; verification is identical. A CI job compares manifest ids across the OS matrix (`testing-and-conformance.md`).

---

## 12. Limits [PACK, Q-11] (defaults; flags may change them)

| Name | Default | On exceed |
|---|---|---|
| `MAX_TEXT_BYTES` | 64 MiB | producing: error; verify: `SKIPPED:LIMIT_EXCEEDED` |
| `MAX_MANIFEST_BYTES` | 1 MiB | same |
| `MAX_ENVELOPE_BYTES` | 256 KiB (a SLH-DSA envelope is ≈ 40 KB) | envelope invalid |
| `MAX_SIGNATURES` | 64 | extra ignored with warning |
| asset size | streamed, no cap (`--max-asset-bytes` optional) | – |
| directory entries scanned | 100,000 | `LIMIT_EXCEEDED` |

A verifier stopped by a limit **must say so** and must not report PASS or FAIL for the unfinished check [YP §12.7]. Exit code 6.

---

## 13. Tool-level formats [TOOL] (not part of PIP-1)

**AKF-1 key file** (`.aek`). Same strict line style. Created with `O_EXCL` and mode `0600`. Never overwritten.

```
aethel-key 1
alg ml-dsa-87
key pip1:k:<64hex>
public-key <base64>
protection scrypt-chacha20poly1305          (or: protection none)
kdf-params n=131072,r=8,p=1,salt=<base64, 16 bytes>
nonce <base64, 12 bytes>
secret <base64>                              ciphertext ‖ 16-byte tag; with `protection none`: the raw secret
```

`protection none` has no `kdf-params` or `nonce` lines. The secret is the 32-byte seed (ML-DSA) or the 128-byte secret key (SLH-DSA). Encryption: key = `scrypt(NFC(passphrase) as UTF-8, salt, n, r, p, 32)`; cipher = ChaCha20-Poly1305; AAD = the file's bytes up to but excluding the `secret` line. **[VERIFIED]** this design works with `cryptography` 50.0.2 (0.52 s at n = 2¹⁷; wrong passphrase and AAD tampering raise `InvalidTag`). Loading checks: key id recomputed from `alg` and public key equals `key`; public key derived from the secret equals `public-key` (ML-DSA: derive from the seed; SLH-DSA: `sk[64:]`); on POSIX the mode must have no group/other bits (R-SEC-01); size ≤ 64 KiB. Passphrases come from a TTY prompt or `--passphrase-file`; never argv or environment.

**TFP-1 chunk proof** (P1):

```
pip-chunk-proof 1
blob pip1:t:<64hex>            (or pip1:a:…)
length <uint ≥ 1>
index <uint>
chunk <base64 of the exact chunk>
path <64hex>                   zero or more lines, leaf level first
```

`aethel proof verify` runs the §5 procedure. Empty blobs need no proof.

---

## 14. Error code registry

`E_…` are parse and canonicalisation codes; capitals without prefix are verification codes. **Y** = named by the Yellow Paper, **P** = defined by this pack. The accept/reject decision is normative; names are recommended [YP §14.2]. `aethel explain <CODE>` must cover every row (test).

| Code | Y/P | Meaning |
|---|---|---|
| `E_INVALID_UTF8` `E_FORBIDDEN_CODEPOINT` `E_UNASSIGNED_CODEPOINT` `E_EMPTY_TEXT` | Y | CTF-1 rejections |
| `E_FIELD_ORDER` `E_BAD_LINES` `E_UNKNOWN_PROFILE` `E_NOT_SORTED_OR_UNIQUE` `E_BAD_VALUE` `E_INTEGER_RANGE` | Y | Manifest rejections (A.3) |
| `E_BAD_MAGIC` `E_UNKNOWN_KEY` `E_MISSING_FIELD` `E_WORK_PARENT_RULE` `E_ROUNDTRIP` | P | Manifest rejections the paper does not name |
| `MANIFEST_INVALID` `ID_MISMATCH` `TEXT_NOT_CANONICAL` `TEXT_LENGTH` `TEXT_MISMATCH` `ASSET_MISSING` `ASSET_MISMATCH` `ASSET_EXTRA` `CITE_UNLISTED` `CITE_LOCATOR_INVALID` `WORK_MISMATCH` `SIG_INVALID` `KEY_MISMATCH` `ALG_UNKNOWN` `BEACON_FAILED` `ATT_FAILED` | Y | Verification codes [YP §11.2] |
| `MANIFEST_MISSING` `TEXT_MISSING` `ENVELOPE_INVALID` `UNSAFE_PATH` `EXTRA_FILE` `CITE_SYNTAX` `CITE_RANGE` `PID_SYNTAX` | P | Additional codes |
| `NO_PARENTS` `PARENTS_UNAVAILABLE` `NO_SIGNATURES` `NO_TIME_EVIDENCE` `BEACON_UNVERIFIED` `ATT_UNVERIFIED` `DEPENDS_ON_V1` `LIMIT_EXCEEDED` | P | SKIPPED/WARN reasons |
| `KEYFILE_INVALID` `KEYFILE_PERMISSIONS` `KEYFILE_PASSPHRASE` `BACKEND_ERROR` `UNICODE_DATA_MISMATCH` | P | Tool errors (exit codes in `cli-spec.md`) |

---

## 15. Conformance matrix [YP §14.1]

| Role | Requirements | Proven by (see `testing-and-conformance.md`) |
|---|---|---|
| Canonicalizer | CTF-1 exact; Unicode ≥ 18.0.0 data; every vector in A.1 | `test_ctf1_vectors`, normalization conformance, fixed-point property |
| Manifest producer | strict parser accepts own output; sort and de-duplicate; no unknown fields | `test_manifest_*`, builder → parser → serializer property |
| Signer | sign `M` with `pip1.sig`; verify own signature before release | `test_signing_*`, A.2 verify, oracle interop |
| Verifier | V1–V3 and V6–V7; report as §9; reject every A.3 mutation | `test_verify_*`, fixtures, tamper matrix |
