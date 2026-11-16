"""Generates tests/vectors/*.json and tests/fixtures/ as shipped in the build pack (2026-11-14).

Yellow Paper values are recomputed and asserted against the paper; SLH-DSA keys are random once, signatures deterministic via the
independent pure-Python oracle and cross-checked with pqcrypto. Spec Guardian only. Run: PACK_ROOT=/tmp/regen uv run python tools/gen_pack_data.py
"""

import base64
import hashlib
import json
import os
import pathlib
import shutil
import sys

import pqcrypto.sign.slh_dsa_sha2_256s as pq_sha2
import pqcrypto.sign.slh_dsa_shake_256s as pq_shake
import unicodedata2 as ud
from cryptography.hazmat.primitives.asymmetric import mldsa
from dilithium_py.ml_dsa import ML_DSA_65, ML_DSA_87
from slhdsa import KeyPair, sha2_256s, shake_256s

ROOT = pathlib.Path(os.environ.get("PACK_ROOT", ""))
if not os.environ.get("PACK_ROOT"):
    sys.exit(
        "Set PACK_ROOT to an EMPTY scratch directory. This script regenerates test data (random SLH-DSA keys change the dual-family fixture); never point it at a repository with frozen oracles."
    )
if (ROOT / "tests/vectors/pip1-vectors.json").exists():
    sys.exit("Refusing to overwrite existing vectors (R-PROTO-02). Use an empty PACK_ROOT.")
(ROOT / "tests/vectors").mkdir(parents=True, exist_ok=True)


def H(label, x):
    return hashlib.sha3_256(bytes([len(label)]) + label + x).digest()


def mth(l):
    n = len(l)
    if n == 1:
        return l[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return H(b"pip1.node", mth(l[:k]) + mth(l[k:]))


def chunks(d):
    return [b""] if not d else [d[i : i + 4096] for i in range(0, len(d), 4096)]


def root(d):
    return mth([H(b"pip1.leaf", c) for c in chunks(d)])


def blob(label, d):
    return H(label, len(d).to_bytes(8, "big") + root(d)).hex()


def b64(b):
    return base64.b64encode(b).decode()


class CE(Exception):
    pass


def ctf1(b):
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise CE("E_INVALID_UTF8")
    for ch in s:
        cp = ord(ch)
        if (
            cp <= 8
            or cp in (0xB, 0xC)
            or 0xE <= cp <= 0x1F
            or 0x7F <= cp <= 0x9F
            or cp == 0xFEFF
            or 0xFDD0 <= cp <= 0xFDEF
            or (cp & 0xFFFE) == 0xFFFE
        ):
            raise CE("E_FORBIDDEN_CODEPOINT")
        if ud.category(ch) == "Cn":
            raise CE("E_UNASSIGNED_CODEPOINT")
    s = ud.normalize("NFC", s.replace("\r\n", "\n").replace("\r", "\n"))
    if s == "":
        raise CE("E_EMPTY_TEXT")
    return (s if s.endswith("\n") else s + "\n").encode()


CTX = b"pip1.sig"


def key_id(alg, pk):
    return H(b"pip1.key", bytes([alg]) + pk).hex()


def envelope(mid_hex, role, algname, kid_hex, pk, sig):
    return (
        f"pip-signature 1\nmanifest pip1:m:{mid_hex}\nrole {role}\nalg {algname}\nkey pip1:k:{kid_hex}\npublic-key {b64(pk)}\nsignature {b64(sig)}\n"
    ).encode()


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data, str) else data)


# ---------------- core values (all recomputed; asserted against the Yellow Paper's printed values)
t1 = b"# The Aethel Codex\n\nWrite once. Verify forever.\n"
T1 = blob(b"pip1.text", t1)
assert T1 == "8186c5e1db209ab3aa29f88d8073f264a30fa2c54120369503044183e19f96ba"
t2_in = bytes.fromhex("efbbbf43616665cc810d0a6c696e652074776f0d6c696e65207468726565")
t2 = ctf1(t2_in)
T2 = blob(b"pip1.text", t2)
assert T2 == "9e13e0cce8ecb379c0705c7d97e13c8e1f588c194bd0e6982dfde98ed6e8f413"
t3 = (("0123456789" * 1000)[:9999] + "\n").encode()
T3 = blob(b"pip1.text", t3)
assert T3 == "a091ae3693aa95009513658d4cf6f334216d1ab7af81ad0381ea14368d3c08ee"
svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>\n'
ASVG = blob(b"pip1.asset", svg)
leaves = [H(b"pip1.leaf", c) for c in chunks(t3)]
node01 = H(b"pip1.node", leaves[0] + leaves[1])
seed = bytes(range(32))
pk87, sk87 = ML_DSA_87.key_derive(seed)
K87 = key_id(0x02, pk87)
assert K87 == "2b27c5d44b407af5e0a2f37adb4454591aa81accd28d852198ef4ae18999130b"


def manifest(title, text_id, text_len, authors, markup="pip-md-1", extra=""):
    s = f"pip-manifest 1\nprofile pip-1\nmarkup {markup}\nlang en\ntitle {title}\nlicense CC0-1.0\ntext pip1:t:{text_id} {text_len}\n"
    for a in sorted(authors):
        s += f"author pip1:k:{a}\n"
    return (s + extra).encode()


GEN = (
    f"pip-manifest 1\nprofile pip-1\nmarkup pip-md-1\nlang en\ntitle Test Manuscript\nlicense CC0-1.0\ntext pip1:t:{T1} 48\n"
    f"author pip1:k:{K87}\nasset figure1.svg pip1:a:{ASVG} 42 image/svg+xml\ncite pip1:t:{T2}\n"
).encode()
GID = H(b"pip1.manifest", GEN)
assert (
    len(GEN) == 434
    and GID.hex() == "e1bbe279695c1adc756913657cdb84c429b63d039ac5bd955b1b297aad0cd30d"
)
REV = (
    f"pip-manifest 1\nprofile pip-1\nmarkup pip-md-1\nlang en\ntitle Test Manuscript\nlicense CC0-1.0\n"
    "beacon example-beacon 123456 00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff\n"
    f"text pip1:t:{T2} 26\nwork pip1:m:{GID.hex()}\nparent pip1:m:{GID.hex()}\nauthor pip1:k:{K87}\n"
).encode()
RID = H(b"pip1.manifest", REV)
assert RID.hex() == "ee09cf8b094f606ae03d1fe7d6db94e83956a9b9bdd019d2853e4d6c181c050d"


def sign87(mid, role=1):
    M = bytes([role]) + mid
    sig = ML_DSA_87.sign(sk87, M, ctx=CTX, deterministic=True)
    pub = mldsa.MLDSA87PublicKey.from_public_bytes(pk87)
    pub.verify(sig, M, CTX)
    return sig


sigG = sign87(GID)
assert (
    hashlib.sha3_256(sigG).hexdigest()
    == "21c348e8d6bf3ed2c76fc139bcbea76bf4f83951c58b034c9ea11853114cc76d"
)
sigR = sign87(RID)


# ---------------- SLH-DSA test keys (random once, signatures deterministic via the independent oracle, cross-checked with pqcrypto)
def slh_make(par, pqmod, alg_id, algname, M):
    kp = KeyPair.gen(par)
    pk, sk = kp.pub.digest(), kp.sec.digest()
    sig = kp.sign_pure(M, randomize=False, ctx=CTX)
    pqmod.verify(pk, M, sig, context=CTX)  # raises if pqcrypto disagrees
    assert kp.verify_pure(M, pqmod.sign(sk, M, context=CTX), ctx=CTX)
    return dict(alg=algname, alg_id=alg_id, pk=pk, sk=sk, sig=sig, kid=key_id(alg_id, pk))


# ---------------- dual-family fixture manifest (needs the SLH key id first)
slh2 = KeyPair.gen(sha2_256s)
slh2_pk, slh2_sk = slh2.pub.digest(), slh2.sec.digest()
K_SLH2 = key_id(0x11, slh2_pk)
dt = b"# Dual-family fixture\n\nTwo keys. Two mathematical families.\n"
DT = blob(b"pip1.text", dt)
DUAL = manifest("Dual Family Fixture", DT, len(dt), [K87, K_SLH2])
DID = H(b"pip1.manifest", DUAL)
Md = bytes([1]) + DID
sig_dual_ml = ML_DSA_87.sign(sk87, Md, ctx=CTX, deterministic=True)
sig_dual_slh = slh2.sign_pure(Md, randomize=False, ctx=CTX)
pq_sha2.verify(slh2_pk, Md, sig_dual_slh, context=CTX)

# ---------------- fixtures
FX = ROOT / "tests/fixtures"
if FX.exists():
    shutil.rmtree(FX)


def bundle(scn, mid, man, text, tname="text.md", assets=None, sigs=None):
    d = FX / scn / mid.hex()
    put(d / "manifest.pip", man)
    put(d / tname, text)
    for n, b in (assets or {}).items():
        put(d / "assets" / n, b)
    for n, b in (sigs or {}).items():
        put(d / "signatures" / n, b)
    return d


sn = lambda role, alg, kid: f"{role}-{alg}-{kid[:16]}.sig"
env87 = lambda mid, sig, role="author": envelope(mid.hex(), role, "ml-dsa-87", K87, pk87, sig)
bundle(
    "genesis-attributed",
    GID,
    GEN,
    t1,
    assets={"figure1.svg": svg},
    sigs={sn("author", "ml-dsa-87", K87): env87(GID, sigG)},
)
bundle("genesis-unsigned", GID, GEN, t1, assets={"figure1.svg": svg})
bundle("revision", RID, REV, t2, sigs={sn("author", "ml-dsa-87", K87): env87(RID, sigR)})
bundle(
    "dual-family",
    DID,
    DUAL,
    dt,
    sigs={
        sn("author", "ml-dsa-87", K87): env87(DID, sig_dual_ml),
        sn("author", "slh-dsa-sha2-256s", K_SLH2): envelope(
            DID.hex(), "author", "slh-dsa-sha2-256s", K_SLH2, slh2_pk, sig_dual_slh
        ),
    },
)
bundle(
    "partial-attribution",
    DID,
    DUAL,
    dt,
    sigs={sn("author", "ml-dsa-87", K87): env87(DID, sig_dual_ml)},
)
exp = lambda **k: json.dumps(k, indent=2) + "\n"
checks = lambda **k: dict(V1="PASS", V2="PASS", V3="PASS", V4="PASS", **k)
put(
    FX / "genesis-attributed/expected.json",
    exp(
        manifest_id="pip1:m:" + GID.hex(),
        integrity="PASS",
        attribution=dict(cls="Attributed", signed=1, declared=1, keccak_independent=False),
        checks=checks(V5="SKIPPED:NO_PARENTS", V6="PASS", V7="PASS", V8="SKIPPED:NO_TIME_EVIDENCE"),
        exit_code_verify=0,
    ),
)
put(
    FX / "genesis-unsigned/expected.json",
    exp(
        manifest_id="pip1:m:" + GID.hex(),
        integrity="PASS",
        attribution=dict(cls="Unattributed", signed=0, declared=1, keccak_independent=False),
        checks=checks(
            V5="SKIPPED:NO_PARENTS",
            V6="SKIPPED:NO_SIGNATURES",
            V7="PASS",
            V8="SKIPPED:NO_TIME_EVIDENCE",
        ),
        exit_code_verify=0,
        exit_code_verify_require_attributed=1,
    ),
)
put(
    FX / "revision/expected.json",
    exp(
        manifest_id="pip1:m:" + RID.hex(),
        integrity="PASS",
        attribution=dict(cls="Attributed", signed=1, declared=1, keccak_independent=False),
        checks_without_parents=checks(
            V5="SKIPPED:PARENTS_UNAVAILABLE", V6="PASS", V7="PASS", V8="WARN:BEACON_UNVERIFIED"
        ),
        checks_with_parents=checks(V5="PASS", V6="PASS", V7="PASS", V8="WARN:BEACON_UNVERIFIED"),
        parents_fixture="../genesis-attributed/" + GID.hex(),
        exit_code_verify=0,
    ),
)
put(
    FX / "dual-family/expected.json",
    exp(
        manifest_id="pip1:m:" + DID.hex(),
        integrity="PASS",
        attribution=dict(cls="Dual-family", signed=2, declared=2, keccak_independent=True),
        checks=checks(V5="SKIPPED:NO_PARENTS", V6="PASS", V7="PASS", V8="SKIPPED:NO_TIME_EVIDENCE"),
        exit_code_verify=0,
    ),
)
put(
    FX / "partial-attribution/expected.json",
    exp(
        manifest_id="pip1:m:" + DID.hex(),
        integrity="PASS",
        attribution=dict(
            cls="Partially attributed", signed=1, declared=2, keccak_independent=False
        ),
        checks=checks(V5="SKIPPED:NO_PARENTS", V6="PASS", V7="PASS", V8="SKIPPED:NO_TIME_EVIDENCE"),
        exit_code_verify=0,
        exit_code_verify_require_attributed=1,
    ),
)


# ---------------- independent mini-verifier: confirm every fixture matches its expected.json
def parse_env(b):
    L = b.decode().split("\n")
    assert L[-1] == "" and L[0] == "pip-signature 1"
    d = {}
    for ln in L[1:-1]:
        k, v = ln.split(" ", 1)
        d[k] = v
    return d


ALG = {
    "ml-dsa-65": (1, "ml"),
    "ml-dsa-87": (2, "ml"),
    "slh-dsa-shake-256s": (0x10, "slh"),
    "slh-dsa-sha2-256s": (0x11, "slh"),
}


def verify_sig(e, mid_hex):
    aid, fam = ALG[e["alg"]]
    pk = base64.b64decode(e["public-key"], validate=True)
    sig = base64.b64decode(e["signature"], validate=True)
    if "pip1:k:" + key_id(aid, pk) != e["key"] or e["manifest"] != "pip1:m:" + mid_hex:
        return False
    M = bytes([{"author": 1}[e["role"]]]) + bytes.fromhex(mid_hex)
    try:
        if e["alg"] == "ml-dsa-87":
            mldsa.MLDSA87PublicKey.from_public_bytes(pk).verify(sig, M, CTX)
        elif e["alg"] == "slh-dsa-sha2-256s":
            pq_sha2.verify(pk, M, sig, context=CTX)
        elif e["alg"] == "slh-dsa-shake-256s":
            pq_shake.verify(pk, M, sig, context=CTX)
        return True
    except Exception:
        return False


for scn in sorted(os.listdir(FX)):
    d = next(p for p in (FX / scn).iterdir() if p.is_dir())
    man = (d / "manifest.pip").read_bytes()
    mid = H(b"pip1.manifest", man).hex()
    assert d.name == mid, (scn, "ID_MISMATCH")
    lines = man.decode().split("\n")
    tf = next(d.glob("text.*"))
    tb = tf.read_bytes()
    assert ctf1(tb) == tb
    tl = [l for l in lines if l.startswith("text ")][0].split(" ")
    assert tl[1] == "pip1:t:" + blob(b"pip1.text", tb) and int(tl[2]) == len(tb)
    for l in lines:
        if l.startswith("asset "):
            _, n, pid, ln, _m = l.split(" ")
            ab = (d / "assets" / n).read_bytes()
            assert pid == "pip1:a:" + blob(b"pip1.asset", ab) and int(ln) == len(ab)
    declared = [l.split(" ")[1] for l in lines if l.startswith("author ")]
    good = {}
    for sf in sorted((d / "signatures").glob("*.sig")) if (d / "signatures").exists() else []:
        e = parse_env(sf.read_bytes())
        assert verify_sig(e, mid), sf
        if e["role"] == "author" and e["key"] in declared:
            good[e["key"]] = e["alg"]
    fam = {ALG[a][1] for a in good.values()}
    n, m = len(declared), len(good)
    cls = (
        "Unattributed"
        if m == 0
        else "Partially attributed"
        if m < n
        else "Dual-family"
        if fam == {"ml", "slh"}
        else "Attributed"
    )
    ex = json.loads((FX / scn / "expected.json").read_text())
    a = ex["attribution"]
    assert (cls, m, n, "slh-dsa-sha2-256s" in good.values()) == (
        a["cls"],
        a["signed"],
        a["declared"],
        a["keccak_independent"],
    ), (scn, cls, m, n)
    print("fixture OK:", scn.ljust(20), d.name[:16], "->", cls, f"{m} of {n}")

# ---------------- vectors JSON (YP-defined + pack-generated, clearly separated)
neg_ctf = [
    ("6f6bc08062616 40a".replace(" ", ""), "E_INVALID_UTF8", "Overlong encoding of U+0000"),
    ("6f6beda0800a", "E_INVALID_UTF8", "Encoded surrogate U+D800"),
    ("6f6bf49080800a", "E_INVALID_UTF8", "Scalar value above U+10FFFF"),
    ("6100620a", "E_FORBIDDEN_CODEPOINT", "NUL"),
    ("610c620a", "E_FORBIDDEN_CODEPOINT", "Form feed"),
    ("61c285620a", "E_FORBIDDEN_CODEPOINT", "U+0085 NEL"),
    ("61efb790620a", "E_FORBIDDEN_CODEPOINT", "U+FDD0 noncharacter"),
    ("61f09fbfbe620a", "E_FORBIDDEN_CODEPOINT", "U+1FFFE noncharacter"),
    ("efbbbfefbbbf610a", "E_FORBIDDEN_CODEPOINT", "Second byte-order mark"),
    ("61cdb8620a", "E_UNASSIGNED_CODEPOINT", "U+0378, unassigned in Unicode 18.0.0"),
    ("", "E_EMPTY_TEXT", "Nothing to identify"),
    ("efbbbf", "E_EMPTY_TEXT", "Only a byte-order mark"),
]
for h, code, _ in neg_ctf:
    try:
        ctf1(bytes.fromhex(h))
        raise SystemExit("negative accepted: " + h)
    except CE as e:
        assert str(e) == code, (h, e)
g = GEN.decode()
mut = lambda name, s, err: dict(
    name=name, input_hex=(s if isinstance(s, bytes) else s.encode()).hex(), expect=err
)
neg_man = [
    mut(
        "Swap the title and license lines",
        g.replace(
            "title Test Manuscript\nlicense CC0-1.0\n", "license CC0-1.0\ntitle Test Manuscript\n"
        ),
        "E_FIELD_ORDER",
    ),
    mut("Remove the final LF", GEN[:-1], "E_BAD_LINES"),
    mut("Use CR LF line endings", g.replace("\n", "\r\n"), "E_BAD_LINES"),
    mut(
        "Change the profile to pip-2",
        g.replace("profile pip-1", "profile pip-2"),
        "E_UNKNOWN_PROFILE",
    ),
    mut(
        "Append a cite line for pip1:t: followed by 64 zeros (sorts before the existing cite line)",
        g + "cite pip1:t:" + "0" * 64 + "\n",
        "E_NOT_SORTED_OR_UNIQUE",
    ),
    mut(
        "Write the title with two spaces after the key",
        g.replace("title Test", "title  Test"),
        "E_BAD_VALUE",
    ),
    mut(
        "Insert a work line before the text line",
        g.replace("text pip1:t:", "work pip1:m:" + GID.hex() + "\ntext pip1:t:", 1),
        "E_FIELD_ORDER",
    ),
    mut(
        "Set the text length to 18446744073709551616",
        g.replace(" 48\n", " 18446744073709551616\n"),
        "E_INTEGER_RANGE",
    ),
    mut(
        "Set the text length to 18446744073709551615 (parser accepts; check V2 would fail)",
        g.replace(" 48\n", " 18446744073709551615\n"),
        "ACCEPTED",
    ),
]
T2h = t2.hex()
loc = [
    ("0-3", True),
    ("3-5", True),
    ("3-6", True),
    ("0-26", True),
    ("0-4", False),
    ("4-9", False),
    ("5-5", False),
    ("0-27", False),
]
recipe = lambda n: bytes((i * 31 + 7) & 0xFF for i in range(n))
sizes = [0, 1, 4095, 4096, 4097, 8192, 8193, 12288, 20000, 1048576]
V = {
    "schema": "aethel.vectors/1",
    "normative_source": {
        "document": "PIP-YP-1",
        "version": "1.0.0-rc.3",
        "date": "2026-11-06",
        "sections": "Appendix A.1-A.5",
    },
    "verification": {
        "date": "2026-11-14",
        "method": "Every hash below recomputed from first principles (hashlib.sha3_256 + unicodedata2 18.0.0) and matched to the Yellow Paper; ML-DSA-87 signature cross-validated with dilithium-py 1.5.1, cryptography 50.0.2 and pqcrypto 1.0.0.",
        "yp_defined_sections": [
            "constants",
            "ctf1",
            "merkle_t3",
            "assets",
            "manifests",
            "signature_ml_dsa_87",
            "locators",
            "asset_names",
            "attribution",
        ],
        "pack_generated_sections": [
            "pack_generated",
            "grammar_cases_derived_from_abnf",
            "unicode_drift_canary",
        ],
        "informative_sections": ["informative_site_vectors"],
        "rule": "yp_defined values are oracles. pack_generated values are regression data and never override the Yellow Paper. If any value here disagrees with the Yellow Paper PDF, STOP and raise a Spec Query.",
    },
    "constants": {
        "labels": {
            l: {"length_byte_hex": "%02x" % len(l), "lp_hex": ("%02x" % len(l)) + l.encode().hex()}
            for l in [
                "pip1.leaf",
                "pip1.node",
                "pip1.text",
                "pip1.asset",
                "pip1.manifest",
                "pip1.key",
            ]
        },
        "signature_context": {
            "ascii": "pip1.sig",
            "hex": CTX.hex(),
            "note": "context string for ML-DSA/SLH-DSA, NOT a hash label",
        },
        "chunk_size": 4096,
        "unicode_version": "18.0.0",
        "alg_ids": {
            "ml-dsa-65": 1,
            "ml-dsa-87": 2,
            "slh-dsa-shake-256s": 16,
            "slh-dsa-sha2-256s": 17,
        },
        "roles": {"author": 1, "contributor": 2, "translator": 3, "endorser": 4},
        "sizes": {
            "ml-dsa-65": {"pk": 1952, "sig": 3309},
            "ml-dsa-87": {"pk": 2592, "sig": 4627},
            "slh-dsa-shake-256s": {"pk": 64, "sig": 29792},
            "slh-dsa-sha2-256s": {"pk": 64, "sig": 29792},
        },
    },
    "ctf1": {
        "T1": {
            "input_hex": t1.hex(),
            "output_hex": t1.hex(),
            "text_id": "pip1:t:" + T1,
            "leaf_equals_root_hex": root(t1).hex(),
        },
        "T2": {
            "input_hex": t2_in.hex(),
            "output_hex": t2.hex(),
            "output_length": 26,
            "text_id": "pip1:t:" + T2,
        },
        "T3": {
            "input_recipe": "(('0123456789'*1000)[:9999] + LF) as ASCII; 10000 bytes",
            "chunk_lengths": [4096, 4096, 1808],
            "text_id": "pip1:t:" + T3,
            "leaf0": leaves[0].hex(),
            "leaf1": leaves[1].hex(),
            "leaf2": leaves[2].hex(),
            "node01": node01.hex(),
            "root": H(b"pip1.node", node01 + leaves[2]).hex(),
            "audit_paths_leaf_level_first": {
                "0": [leaves[1].hex(), leaves[2].hex()],
                "1": [leaves[0].hex(), leaves[2].hex()],
                "2": [node01.hex()],
            },
        },
        "negative": [{"input_hex": h, "expect": c, "reason": r} for h, c, r in neg_ctf],
    },
    "assets": {
        "empty": "pip1:a:" + blob(b"pip1.asset", b""),
        "figure1_svg": {"content_utf8": svg.decode(), "length": 42, "asset_id": "pip1:a:" + ASVG},
    },
    "manifests": {
        "genesis": {"text": GEN.decode(), "length": 434, "manifest_id": "pip1:m:" + GID.hex()},
        "revision": {
            "text": REV.decode(),
            "length": len(REV),
            "manifest_id": "pip1:m:" + RID.hex(),
        },
        "negative_mutations": neg_man,
    },
    "signature_ml_dsa_87": {
        "seed_hex": seed.hex(),
        "public_key_length": 2592,
        "sha3_256_of_public_key_unlabelled": hashlib.sha3_256(pk87).hexdigest(),
        "key_id": "pip1:k:" + K87,
        "role_byte_hex": "01",
        "message_M_hex": (b"\x01" + GID).hex(),
        "context_hex": CTX.hex(),
        "M_prime_fips204_hex": (b"\x00\x08" + CTX + b"\x01" + GID).hex(),
        "mode": "deterministic (rnd = 32 zero bytes)",
        "public_key_hex": pk87.hex(),
        "signature_length": 4627,
        "signature_hex": sigG.hex(),
        "sha3_256_of_signature": hashlib.sha3_256(sigG).hexdigest(),
        "must_verify": True,
        "must_fail_when": [
            "context is pip1.other",
            "role byte is 02",
            "message uses the revision manifest id",
        ],
    },
    "locators": {
        "canonical_text_hex": T2h,
        "canonical_text_length": 26,
        "range_results": [{"locator": "#b=" + r, "valid": v} for r, v in loc],
        "syntax_errors_for_pid_t_T2": ["#b=00-3", "#b=3-3", "#b=5-3", "#b=1-", "#line=3"],
        "also_syntax_errors": [
            "upper-case hex digits in the PID",
            "a citation of a type k identifier",
        ],
    },
    "asset_names": {
        "accept": ["figure1.svg", "fig_1-a.v2.png", "x", "A.B", "a" * 128],
        "reject": ["a b", "a/b", "..", ".", "a" * 129, "caf\u00e9.svg", "a\tb"],
    },
    "attribution": [
        {
            "declared_and_signed": "3 declared, 2 signed with ML-DSA-87",
            "class": "Partially attributed",
            "m_of_n": "2 of 3",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "2 declared, none signed",
            "class": "Unattributed",
            "m_of_n": "0 of 2",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "None declared",
            "class": "Unattributed",
            "m_of_n": "0 of 0",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "1 declared, signed only by a different undeclared key",
            "class": "Unattributed",
            "m_of_n": "0 of 1",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "2 declared, both signed with ML-DSA-87",
            "class": "Attributed",
            "m_of_n": "2 of 2",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "2 declared, ML-DSA-87 and SLH-DSA-SHAKE-256s",
            "class": "Dual-family",
            "m_of_n": "2 of 2",
            "keccak_independent": False,
        },
        {
            "declared_and_signed": "2 declared, ML-DSA-87 and SLH-DSA-SHA2-256s",
            "class": "Dual-family",
            "m_of_n": "2 of 2",
            "keccak_independent": True,
        },
    ],
    "informative_site_vectors": {
        "source": "https://aethel-codex.pages.dev/ (rc.1 landing page, recomputed 2026-11-14)",
        "no_full_stop": {
            "input_utf8": "# The Aethel Codex\n\nWrite once. Verify forever\n",
            "text_id": "pip1:t:"
            + blob(b"pip1.text", b"# The Aethel Codex\n\nWrite once. Verify forever\n"),
        },
    },
    "pack_generated": {
        "note": "Not Yellow Paper normative. Regression data produced by this pack on 2026-11-14.",
        "blob_sizes": {
            "data_recipe": "byte i = (i*31+7) & 0xFF",
            "entries": [
                {
                    "length": n,
                    "chunks": max(1, -(-n // 4096)),
                    "asset_id": "pip1:a:" + blob(b"pip1.asset", recipe(n)),
                    "text_label_id_if_it_were_text": "pip1:t:" + blob(b"pip1.text", recipe(n)),
                }
                for n in sizes
            ],
        },
        "dual_family_fixture_text": {"text_id": "pip1:t:" + DT},
    },
}
# ML-DSA-65 pack-generated vector (verify-only KAT)
pk65, sk65 = ML_DSA_65.key_derive(seed)
M65 = bytes([1]) + GID
sig65 = ML_DSA_65.sign(sk65, M65, ctx=CTX, deterministic=True)
mldsa.MLDSA65PublicKey.from_public_bytes(pk65).verify(sig65, M65, CTX)
V["pack_generated"]["ml_dsa_65"] = {
    "seed_hex": seed.hex(),
    "key_id": "pip1:k:" + key_id(1, pk65),
    "message_M_hex": M65.hex(),
    "public_key_hex": pk65.hex(),
    "signature_hex": sig65.hex(),
    "must_verify": True,
    "produced_by": "dilithium-py 1.5.1 deterministic; verified by cryptography 50.0.2",
}
# grammar cases (from the ABNF; used by tests of the strict parser)
V["grammar_cases_derived_from_abnf"] = {
    "lang_accept": [
        "en",
        "und",
        "en-US",
        "zh-Hant",
        "zh-Hant-TW",
        "sr-Latn-RS",
        "es-419",
        "de-1996",
        "fil",
    ],
    "lang_reject": ["EN", "e", "en_US", "en-", "en-x-foo", "en-us-", "eng-", "en--US"],
    "uint_accept": ["0", "1", "18446744073709551615"],
    "uint_reject_syntax": ["00", "01", "", "-1", "+1", "1_0", " 1", "1 ", "\u0663"],
    "uint_reject_range": ["18446744073709551616"],
    "media_accept": ["image/svg+xml", "text/plain", "application/octet-stream"],
    "media_reject": ["Image/svg", "text/", "/plain", "text/plain; charset=utf-8"],
    "beacon_value_reject": ["", "0", "abc", "00ff0", "00FF"],
}
# Unicode drift canary
rs = []
st = None
for cp in range(0x110000):
    okc = ud.category(chr(cp)) != "Cn"
    if okc and st is None:
        st = cp
    if not okc and st is not None:
        rs.append((st, cp - 1))
        st = None
if st is not None:
    rs.append((st, 0x10FFFF))
V["unicode_drift_canary"] = {
    "not_normative": True,
    "unicodedata2_unidata_version": ud.unidata_version,
    "definition": "ranges of scalar values whose General_Category != Cn (Cs, Co, Cc included); lines 'XXXX-XXXX' uppercase hex, LF-joined, no final LF, SHA-256",
    "code_points": sum(b - a + 1 for a, b in rs),
    "ranges": len(rs),
    "sha256": hashlib.sha256("\n".join(f"{a:04X}-{b:04X}" for a, b in rs).encode()).hexdigest(),
}
(ROOT / "tests/vectors/pip1-vectors.json").write_text(
    json.dumps(V, indent=2, ensure_ascii=True) + "\n"
)

# ---------------- SLH-DSA vectors (pack-generated)
M = bytes([1]) + GID
S = {
    "schema": "aethel.slh-dsa-vectors/1",
    "status": "PACK-GENERATED, NOT YELLOW-PAPER NORMATIVE (closes the spirit of open item 14.3.3 pending Working Group adoption)",
    "generated": "2026-11-14",
    "signer": "slh-dsa 0.2.5 (independent pure-Python FIPS 205 implementation), deterministic mode",
    "verifier_cross_check": "pqcrypto 1.0.0 verified every signature; pqcrypto-made signatures verified by the pure-Python implementation",
    "context_hex": CTX.hex(),
    "message_M_hex": M.hex(),
    "warning": "test_only_secret_key_hex are public test keys. NEVER use them for real work.",
    "vectors": [],
}
for par, pqm, aid, nm in (
    (sha2_256s, pq_sha2, 0x11, "slh-dsa-sha2-256s"),
    (shake_256s, pq_shake, 0x10, "slh-dsa-shake-256s"),
):
    v = slh_make(par, pqm, aid, nm, M)
    bad = bytearray(v["sig"])
    bad[100] ^= 1
    S["vectors"].append(
        {
            "alg": nm,
            "alg_id": aid,
            "key_id": "pip1:k:" + v["kid"],
            "public_key_b64": b64(v["pk"]),
            "test_only_secret_key_hex": v["sk"].hex(),
            "signature_b64": b64(v["sig"]),
            "sha3_256_of_signature": hashlib.sha3_256(v["sig"]).hexdigest(),
            "must_verify": True,
            "must_fail_when": [
                "context is pip1.other",
                "role byte is 02",
                "one signature byte flipped (offset 100)",
            ],
            "flipped_signature_b64": b64(bytes(bad)),
        }
    )
(ROOT / "tests/vectors/pip1-slh-dsa-vectors.json").write_text(json.dumps(S, indent=1) + "\n")
print("JSON written.")
