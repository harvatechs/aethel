"""Protocol constants, labels, and parameters (PIP-1, YP §0, §2, §3, §7)."""

from dataclasses import dataclass

# Domain-separation hash labels (YP §3.4)
LABEL_LEAF = b"pip1.leaf"
LABEL_NODE = b"pip1.node"
LABEL_TEXT = b"pip1.text"
LABEL_ASSET = b"pip1.asset"
LABEL_MANIFEST = b"pip1.manifest"
LABEL_KEY = b"pip1.key"

# Signature context string (YP §3.1, §9.1)
# 8 ASCII bytes passed directly as context to signature schemes. Not a hash label.
SIG_CONTEXT = b"pip1.sig"

# Parameters
CHUNK_SIZE = 4096
UNICODE_VERSION = "18.0.0"

# Maximum length for value text fields in bytes (YP §7.4, specs.md §2, §12)
MAX_TITLE_BYTES = 512
MAX_LICENSE_BYTES = 256
MAX_ASSET_NAME_BYTES = 128
MAX_BEACON_VALUE_BYTES = 64
MAX_ENVELOPE_BYTES = 65536

# Profile and Magics
PROFILE_PIP1 = "pip-1"
MAGIC_MANIFEST = "pip-manifest 1"
MAGIC_SIGNATURE = "pip-signature 1"
MAGIC_ATTESTATION = "pip-attestation 1"
MAGIC_KEY = "aethel-key 1"
MAGIC_CHUNK_PROOF = "pip-chunk-proof 1"


@dataclass(frozen=True)
class Algorithm:
    """Algorithm metadata for PIP-1 signature suites (YP §3.1)."""

    alg_id: int
    name: str
    public_key_size: int
    signature_size: int
    secret_key_size: int
    family: str  # "ml" or "slh"


ALG_ML_DSA_65 = Algorithm(
    alg_id=0x01,
    name="ml-dsa-65",
    public_key_size=1952,
    signature_size=3309,
    secret_key_size=32,
    family="ml",
)

ALG_ML_DSA_87 = Algorithm(
    alg_id=0x02,
    name="ml-dsa-87",
    public_key_size=2592,
    signature_size=4627,
    secret_key_size=32,
    family="ml",
)

ALG_SLH_DSA_SHAKE_256S = Algorithm(
    alg_id=0x10,
    name="slh-dsa-shake-256s",
    public_key_size=64,
    signature_size=29792,
    secret_key_size=128,
    family="slh",
)

ALG_SLH_DSA_SHA2_256S = Algorithm(
    alg_id=0x11,
    name="slh-dsa-sha2-256s",
    public_key_size=64,
    signature_size=29792,
    secret_key_size=128,
    family="slh",
)

ALGORITHMS: dict[int, Algorithm] = {
    0x01: ALG_ML_DSA_65,
    0x02: ALG_ML_DSA_87,
    0x10: ALG_SLH_DSA_SHAKE_256S,
    0x11: ALG_SLH_DSA_SHA2_256S,
}

ALGORITHM_BY_NAME: dict[str, Algorithm] = {alg.name: alg for alg in ALGORITHMS.values()}

# Role codes (YP §3.4)
ROLE_AUTHOR = 0x01
ROLE_CONTRIBUTOR = 0x02
ROLE_TRANSLATOR = 0x03
ROLE_ENDORSER = 0x04

ROLES: dict[int, str] = {
    ROLE_AUTHOR: "author",
    ROLE_CONTRIBUTOR: "contributor",
    ROLE_TRANSLATOR: "translator",
    ROLE_ENDORSER: "endorser",
}

ROLE_BY_NAME: dict[str, int] = {name: code for code, name in ROLES.items()}
