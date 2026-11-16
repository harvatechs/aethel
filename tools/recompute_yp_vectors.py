"""Independent recomputation of every Yellow Paper (PIP-YP-1 rc.3) vector from first principles.

Audit script used to prepare the build pack on 2026-11-14. Needs the dev group (dilithium-py, cryptography, pqcrypto, unicodedata2).
Run: uv run python tools/recompute_yp_vectors.py        Exit 0 only if every value reproduces.
It is a verification harness, not production code: the package must be written to the repository's own quality bar.
"""

import hashlib
import sys

import unicodedata2 as ud


def H(label: bytes, x: bytes) -> bytes:
    return hashlib.sha3_256(bytes([len(label)]) + label + x).digest()


def mth(leaves):
    n = len(leaves)
    if n == 1:
        return leaves[0]
    k = 1 << ((n - 1).bit_length() - 1)  # largest power of two strictly less than n
    return H(b"pip1.node", mth(leaves[:k]) + mth(leaves[k:]))


def chunks(d, size=4096):
    return [b""] if len(d) == 0 else [d[i : i + size] for i in range(0, len(d), size)]


def tree_root(d):
    return mth([H(b"pip1.leaf", c) for c in chunks(d)])


def blob_hex(label, d):
    return H(label, len(d).to_bytes(8, "big") + tree_root(d)).hex()


class CtfError(Exception):
    pass


def ctf1(b: bytes) -> bytes:
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise CtfError("E_INVALID_UTF8")
    for ch in s:
        cp = ord(ch)
        if (
            cp <= 0x08
            or cp in (0x0B, 0x0C)
            or 0x0E <= cp <= 0x1F
            or 0x7F <= cp <= 0x9F
            or cp == 0xFEFF
            or 0xFDD0 <= cp <= 0xFDEF
            or (cp & 0xFFFE) == 0xFFFE
        ):
            raise CtfError("E_FORBIDDEN_CODEPOINT")
        if ud.category(ch) == "Cn":
            raise CtfError("E_UNASSIGNED_CODEPOINT")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = ud.normalize("NFC", s)
    if s == "":
        raise CtfError("E_EMPTY_TEXT")
    if not s.endswith("\n"):
        s += "\n"
    return s.encode("utf-8")


ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print(
        ("PASS " if good else "FAIL ") + name + ("" if good else f"\n   got  {got}\n   want {want}")
    )


print("unicodedata2", ud.unidata_version)
# ---- T1
t1 = b"# The Aethel Codex\n\nWrite once. Verify forever.\n"
check("T1 len", len(t1), 48)
check("T1 ctf fixed", ctf1(t1), t1)
check(
    "T1 leaf/root",
    tree_root(t1).hex(),
    "bbcc5e9494dabc60e9465e93ab70c0f7436a29d5308a5b80b35f9478521165c4",
)
T1 = blob_hex(b"pip1.text", t1)
check("T1 text id", T1, "8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba")
# ---- T2
t2_in = bytes.fromhex("efbbbf43616665cc810d0a6c696e652074776f0d6c696e65207468726565")
t2_out = ctf1(t2_in)
check("T2 output", t2_out.hex(), "436166c3a90a6c696e652074776f0a6c696e652074687265650a")
check("T2 fixed point", ctf1(t2_out), t2_out)
check("T2 len", len(t2_out), 26)
T2 = blob_hex(b"pip1.text", t2_out)
check("T2 text id", T2, "9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413")
# ---- T3
t3 = (("0123456789" * 1000)[:9999] + "\n").encode()
check("T3 len", len(t3), 10000)
check("T3 chunk sizes", [len(c) for c in chunks(t3)], [4096, 4096, 1808])
leaves = [H(b"pip1.leaf", c) for c in chunks(t3)]
for i, w in enumerate(
    [
        "849736045f32809c9282110436900b8786494a5da81edf4f234fd67d1986fca9",
        "259cdeeeb8f220292ef5171f0bb10bda27a0d8d619e5040e52fde95585706c50",
        "b67db877f1a3983368ac1106daf9d450aa7e2770a331be27c3321b6425c98284",
    ]
):
    check(f"T3 leaf{i}", leaves[i].hex(), w)
node01 = H(b"pip1.node", leaves[0] + leaves[1])
check("T3 node01", node01.hex(), "e159d410f37a936ff97cc2d679cbf368e5624948a674d3cf41dcff7c969795fb")
check(
    "T3 root",
    H(b"pip1.node", node01 + leaves[2]).hex(),
    "de3987ca0f5a42670f34b9c2b061b09205429154942b770141adc0b8ccdac85a",
)
check(
    "T3 text id",
    blob_hex(b"pip1.text", t3),
    "a091ae3693aa95009513658d4cf6f334216d1ab7af81ad0381ea14368d3c08ee",
)
# ---- T4
check(
    "T4 empty asset",
    blob_hex(b"pip1.asset", b""),
    "e2a25df839aeba38c694f01b361c2e607f44f1e08c72353e806e0561139837f7",
)
svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>\n'
check("T4 svg len", len(svg), 42)
A_SVG = blob_hex(b"pip1.asset", svg)
check("T4 svg id", A_SVG, "e7df5b50afd41b1621ceddbe590fe6ebaac58d393ff5da9b1f84a8f447da7462")
# ---- negative vectors
neg = [
    ("6f6bc0806261640a", "E_INVALID_UTF8"),
    ("6f6beda0800a", "E_INVALID_UTF8"),
    ("6f6bf49080800a", "E_INVALID_UTF8"),
    ("610062 0a".replace(" ", ""), "E_FORBIDDEN_CODEPOINT"),
    ("610c620a", "E_FORBIDDEN_CODEPOINT"),
    ("61c285620a", "E_FORBIDDEN_CODEPOINT"),
    ("61efb790620a", "E_FORBIDDEN_CODEPOINT"),
    ("61f09fbfbe620a", "E_FORBIDDEN_CODEPOINT"),
    ("efbbbfefbbbf610a", "E_FORBIDDEN_CODEPOINT"),
    ("61cdb8620a", "E_UNASSIGNED_CODEPOINT"),
    ("", "E_EMPTY_TEXT"),
    ("efbbbf", "E_EMPTY_TEXT"),
]
for h, code in neg:
    try:
        ctf1(bytes.fromhex(h))
        got = "ACCEPTED"
    except CtfError as e:
        got = str(e)
    check(f"NEG {h or '(empty)'}", got, code)
# ---- manifests
GEN = (
    "pip-manifest 1\nprofile pip-1\nmarkup pip-md-1\nlang en\ntitle Test Manuscript\nlicense CC0-1.0\n"
    f"text pip1:t:{T1} 48\n"
    "author pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b\n"
    f"asset figure1.svg pip1:a:{A_SVG} 42 image/svg+xml\n"
    f"cite pip1:t:{T2}\n"
).encode()
check("Genesis manifest len", len(GEN), 434)
GEN_ID = H(b"pip1.manifest", GEN)
check(
    "Genesis manifest id",
    GEN_ID.hex(),
    "e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d",
)
REV = (
    "pip-manifest 1\nprofile pip-1\nmarkup pip-md-1\nlang en\ntitle Test Manuscript\nlicense CC0-1.0\n"
    "beacon example-beacon 123456 00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff\n"
    f"text pip1:t:{T2} 26\n"
    f"work pip1:m:{GEN_ID.hex()}\nparent pip1:m:{GEN_ID.hex()}\n"
    "author pip1:k:2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b\n"
).encode()
REV_ID = H(b"pip1.manifest", REV)
check(
    "Revision manifest id",
    REV_ID.hex(),
    "ee09cf8b094f606ae03d1fe7d6db94e83956a9b9bdd019d2853e4d6c181c050d",
)
print("revision manifest len", len(REV))
# ---- site-derived vectors (informative)
nofs = b"# The Aethel Codex\n\nWrite once. Verify forever\n"
check(
    "SITE no-full-stop id",
    blob_hex(b"pip1.text", nofs),
    "a9336d3c9940dda18e296b479a97e8a75b9432ef4240911a8d0323a2795e1aeb",
)
manifesto = (
    "# The Aethel Codex\n\nWrite once. Verify forever.\n\n"
    "A book on a shelf needs nothing. No server. No subscription. No one\u2019s permission.\n\n"
    "Writing on the internet needs all of it. So it disappears. The host closes. The text is quietly edited. The link stops working. The proof of who wrote it goes with the company that held it.\n\n"
    "We are building the other thing: an open standard that gives every piece of writing a name made from the writing itself. Change one comma and the name changes. Cite a work, and the citation cannot be quietly pointed somewhere else. Sign it, and the signature is designed to hold up against the quantum computers of the future.\n\n"
    "We do not promise that a text will never be lost. We promise something smaller, and true: if you hold the words, you can prove they are the words.\n\n"
    "Permanent ink. Open to everyone.\n"
).encode()
mc = ctf1(manifesto)
print("manifesto canonical len", len(mc), "(site says 834)")
check(
    "SITE manifesto id",
    blob_hex(b"pip1.text", mc),
    "de93176d900a2b525e6da0c1d9eda52d21005cd1f9ebaa39cc29f9b94c42fd4b",
)
# ---- ML-DSA-87: derive key, deterministic signature, cross-validate with 2 other libraries
from dilithium_py.ml_dsa import ML_DSA_87

seed = bytes(range(32))
pk, sk = ML_DSA_87.key_derive(seed)
check("A2 pk len", len(pk), 2592)
check(
    "A2 sha3(pk)",
    hashlib.sha3_256(pk).hexdigest(),
    "e6cf50a9c2fa5234f59949ff61f8161db4d629532127f4aefa8bb10811ecfb1e",
)
KEY_ID = H(b"pip1.key", bytes([0x02]) + pk).hex()
check("A2 key id", KEY_ID, "2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b")
M = bytes([1]) + GEN_ID
ctx = b"pip1.sig"
Mp = b"\x00" + bytes([len(ctx)]) + ctx + M
check(
    "A2 M'",
    Mp.hex(),
    "0008706970312e73696701e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d",
)
sig_int = ML_DSA_87._sign_internal(sk, Mp, b"\x00" * 32)
sig_det = ML_DSA_87.sign(sk, M, ctx=ctx, deterministic=True)
check("A2 internal==public deterministic", sig_int == sig_det, True)
check("A2 sig len", len(sig_det), 4627)
check(
    "A2 sha3(sig)",
    hashlib.sha3_256(sig_det).hexdigest(),
    "21c348e8d6bf3ed2c76fc139bcbea76bf4f83951c58b034c9ea11853114cc76d",
)
print("--- cross-validation of the deterministic YP signature")
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import mldsa

priv = mldsa.MLDSA87PrivateKey.from_seed_bytes(seed)
check(
    "cryptography: pk from seed == dilithium-py pk",
    priv.public_key().public_bytes_raw() == pk,
    True,
)
check("cryptography: private_bytes_raw is the 32-byte seed", priv.private_bytes_raw() == seed, True)
pub = mldsa.MLDSA87PublicKey.from_public_bytes(pk)
try:
    pub.verify(sig_det, M, ctx)
    r = True
except InvalidSignature:
    r = False
check("cryptography verifies YP signature (ctx pip1.sig)", r, True)
for label, args in (
    ("wrong ctx", (sig_det, M, b"pip1.other")),
    ("role 02", (sig_det, bytes([2]) + GEN_ID, ctx)),
    ("revision id", (sig_det, bytes([1]) + REV_ID, ctx)),
):
    try:
        pub.verify(*args)
        r = True
    except InvalidSignature:
        r = False
    check(f"cryptography rejects ({label})", r, False)
import pqcrypto
import pqcrypto.sign.ml_dsa_87 as pq87


def pq_ok(pk_, m_, s_, c_):
    try:
        pq87.verify(pk_, m_, s_, context=c_)
        return True
    except pqcrypto.InvalidSignatureError:
        return False


check("pqcrypto verifies YP signature (ctx pip1.sig)", pq_ok(pk, M, sig_det, ctx), True)
check("pqcrypto rejects wrong context", pq_ok(pk, M, sig_det, b"pip1.other"), False)
check("pqcrypto rejects other role byte", pq_ok(pk, bytes([2]) + GEN_ID, sig_det, ctx), False)
h1 = priv.sign(M, ctx)
h2 = priv.sign(M, ctx)
check("cryptography hedged signatures differ", h1 != h2, True)
check(
    "dilithium-py verifies cryptography hedged signature",
    ML_DSA_87.verify(pk, M, h1, ctx=ctx),
    True,
)
check("pqcrypto verifies cryptography hedged signature", pq_ok(pk, M, h1, ctx), True)
print("\nALL VECTORS REPRODUCED" if ok else "\n*** SOME CHECKS FAILED ***")
sys.exit(0 if ok else 1)
