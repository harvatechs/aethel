# architecture.md — Structure of the Code

## 1. Principles

**Functional core, imperative shell.** Protocol logic is pure: bytes in, bytes or typed values out, no files, no clocks, no globals. Only `bundle`, `keyfile` and `cli` touch the filesystem or terminal. Every layer can be tested without the layers above it, and a second implementation can be compared with the first at the byte level.

## 2. Repository layout

```
aethel-codex/
├── AGENTS.md  README.md  CHANGELOG.md  SECURITY.md  LICENSE  Makefile  pyproject.toml  uv.lock
├── docs/                          this pack (decision-log, queries/, reviews/, incidents/ grow here)
├── src/aethel_codex/
│   ├── __init__.py                __version__ (single source), small public re-export set
│   ├── __main__.py                python -m aethel_codex
│   ├── constants.py  errors.py  hashing.py
│   ├── unicode18.py  _repertoire.py  ctf1.py
│   ├── merkle.py  pid.py  citations.py  manifest.py
│   ├── envelope.py  signing.py
│   ├── backends/                  base.py  mldsa.py (cryptography)  slhdsa.py (pqcrypto)  __init__.py (registry by alg_id)
│   ├── limits.py  bundle.py  keyfile.py
│   ├── verify.py  report.py  proof.py  publish.py
│   ├── explain.py  selftest.py
│   ├── schemas/*.json             JSON Schema 2020-12 for every --json output (package data)
│   ├── data/                      pip1-vectors.json  pip1-slh-dsa-vectors.json (package data)
│   └── cli/                       __init__.py (main)  parser.py  output.py  sanitize.py  commands/<one module per command>.py
├── scripts/verify_minimal.py      stdlib-only second verifier (ADR-013); not part of the wheel
├── tools/                         gen_repertoire.py  fetch_unicode_tests.py  check_coverage.py  trace.py  determinism_check.py  install_smoke.py  recompute_yp_vectors.py  gen_pack_data.py (dev only)
└── tests/                         unit/ property/ conformance/ differential/ cli/ security/ slow/ + vectors/ fixtures/
```

## 3. Layering contract

A module may import only from lower layers. `import-linter` enforces it (R-CODE-03).

| Layer | Modules | May also use |
|---|---|---|
| L0 | `constants`, `errors` | stdlib only |
| L1 | `hashing`, `unicode18` (+`_repertoire`) | `hashlib`, `unicodedata2`, `re` |
| L2 | `ctf1`, `merkle`, `pid` | L0–L1 |
| L3 | `citations`, `manifest`, `envelope` | L0–L2 |
| L4 | `backends/*`, `signing` | L0–L3; `cryptography`, `pqcrypto` (backends only) |
| L5 | `limits`, `bundle`, `keyfile` | L0–L4; filesystem access begins here |
| L6 | `verify`, `report`, `proof`, `publish` | L0–L5 |
| L7 | `explain`, `selftest` | L0–L6 |
| L8 | `cli/*` | everything; terminal I/O lives here |

Extra contracts: L0–L4 import no `os`, `pathlib`, `sys`, `socket`, `urllib`, `http`, `ssl`, `subprocess`. `hashlib` appears only in `hashing.py`. Only `backends/*` import `cryptography` and `pqcrypto`, lazily (R-DEP-02, §9). `src/` never imports `dilithium_py`, `slhdsa` or `unicodedata`.

## 4. Modules and public API

Signatures are the contract between work packages. Names may be refined only through the decision log.

```python
# hashing.py   (YP §0)
def H(label: bytes, x: bytes) -> bytes
# unicode18.py (YP §4.3–4.4)   guard runs at import
def find_forbidden(text: str) -> int | None;  def find_unassigned(text: str) -> int | None;  def nfc(text: str) -> str
# ctf1.py      (YP §4)
def canonicalize(data: bytes) -> tuple[bytes, CanonReport]
# pid.py       (YP §6)
class PidType(Enum): MANIFEST="m"; TEXT="t"; ASSET="a"; KEY="k"
@dataclass(frozen=True) class Pid: type: PidType; digest: bytes; parse(cls, s: str) -> Pid; __str__
def key_id(alg: Algorithm, public_key: bytes) -> Pid
# merkle.py    (YP §5)
class TreeHasher: update(data) -> None; root() -> bytes; length: int
def text_id(canonical: bytes) -> Pid;  def asset_id(chunks: Iterable[bytes]) -> tuple[Pid, int]
def make_proof(index: int, leaf_hashes: Sequence[bytes]) -> list[bytes];  def verify_chunk(...) -> bool
# citations.py (YP §6.3)
def parse_citation(uri: str) -> Citation;  def validate_locator(c: Citation, length: int, byte_at: Callable[[int], int]) -> None
def scan_inline(text: str) -> list[Pid]
# manifest.py  (YP §7)
def parse_manifest(data: bytes) -> Manifest;  def serialize_manifest(m: Manifest) -> bytes;  def manifest_id(data: bytes) -> Pid
class ManifestBuilder: ...   # sorts, de-duplicates, builds genesis or revision, then strict re-parse
# envelope.py  (YP §9.4, §10.3)
def parse_signature_envelope(data: bytes) -> SignatureEnvelope;  def serialize_signature_envelope(e) -> bytes
def parse_attestation_envelope(data: bytes) -> AttestationEnvelope;  def serialize_attestation_envelope(e) -> bytes
# signing.py   (YP §9)
def sign_manifest(manifest: Pid, role: int, secret: SecretKey) -> SignatureEnvelope      # signs, self-verifies, fails closed
def verify_signature(env: SignatureEnvelope, manifest: Pid) -> SignatureResult           # §8 steps 1–7, never raises for bad input
# bundle.py / keyfile.py    (filesystem edge)
def read_bundle(path: Path, limits: Limits) -> BundleView;  def write_bundle(...) -> Path
def create_key(alg, protection) -> Path;  def load_key(path: Path, passphrase: bytes | None) -> SecretKey
# verify.py / publish.py
def verify_bundle(path: Path, *, parents: Path | None, limits: Limits) -> VerifyReport
def publish(request: PublishRequest) -> PublishResult
```

`SecretKey` holds the secret in a `bytearray`, has no `__repr__` content, supports `wipe()` (best effort, documented as such), and is never serialised except by `keyfile`.

## 5. Data models (frozen dataclasses, no behaviour beyond validation)

`Algorithm` (enum with `alg_id`, `name`, sizes, family `ml|slh`) · `Role` (int newtype) · `Pid` · `Manifest` (all PMF-1 fields, tuple-valued lists) · `SignatureEnvelope` · `AttestationEnvelope` · `CanonReport` · `Limits` · `CheckResult(id, status, code, detail, items)` · `AttributionReport` · `VerifyReport` (integrity, attribution, history, time, checks, warnings, notes). `Status` is an enum: `PASS WARN FAIL SKIPPED`.

## 6. Control flow

```
publish:  read bytes ──canonicalize──► text id ─┐
          assets ──stream TreeHasher──► asset ids ─┤
          metadata ──────────────► ManifestBuilder ──serialize──► strict re-parse ──► manifest id
          keyfile ──load──► sign (hedged) ──► verify_signature (self-check) ──► envelope
          bundle writer (temp dir ► fsync ► rename) ──► verify_bundle (full) ──► report

verify:   read_bundle (lstat, limits)
            V1 manifest ─► V2 text ─► V3 assets ─► V4 citations ─► V5 history ─► V6 signatures ─► V7 attribution ─► V8 time
            each check returns CheckResult; a failed V1 makes dependants SKIPPED:DEPENDS_ON_V1
          ──► summaries (integrity, attribution, history, time) ──► report ──► human or JSON renderer
```

## 7. Error model

`AethelError(code, message, **detail)` is the base. Subclasses: `CanonicalizationError`, `ManifestError`, `CitationError`, `EnvelopeError`, `BundleError`, `KeyFileError`, `CryptoError`, `LimitExceeded`, `UsageError`, `InternalError`. `code` is always a registry entry (`specs.md` §14). The CLI maps classes to exit codes (`cli-spec.md` §2) and renders messages; library code never prints. `verify_bundle` converts expected problems into `CheckResult`s and raises only for I/O or internal failures.

## 8. Dependencies (ADR-003)

| Runtime | Range | Used for | Imported by |
|---|---|---|---|
| `cryptography` | `>=50.0.2,<51` | ML-DSA; ChaCha20-Poly1305 and scrypt for key files | `backends/mldsa.py`, `keyfile.py` |
| `pqcrypto` | `>=1.0.0,<2` | SLH-DSA | `backends/slhdsa.py` |
| `unicodedata2` | `>=18.0.0,<19` | Unicode 18.0.0 tables, NFC | `unicode18.py` |

Dev group: `pytest`, `hypothesis`, `pytest-cov`, `mypy`, `ruff`, `import-linter`, `jsonschema`, `build`, `twine`, `pip-audit`, `cyclonedx-bom`, `dilithium-py==1.5.1`, `slh-dsa==0.2.5`. Do not pin tool versions in `pyproject.toml`; the lockfile pins them. Add nothing else without an ADR.

## 9. Performance design

- Import `cryptography` and `pqcrypto` inside the functions that need them. `aethel --version` and `--help` must not import them (≤ 150 ms).
- Hash assets in 1 MiB reads through `TreeHasher`; never `read()` an asset whole.
- CTF-1 works on the whole text; apply `MAX_TEXT_BYTES` before decoding.
- Compile regexes once at module import. Use the linear patterns of `specs.md`.
- No threads or processes in the MVP. Parallel verification is P2 (`--jobs`).

## 10. Extension points (data, not frameworks)

Algorithm table, role table, beacon-source registry and attestation-kind registry are plain tuples and dicts in `constants.py`. The beacon and attestation registries are empty because the Yellow Paper registers nothing yet. A new profile would be a new package version with its own module set; nothing negotiates at run time.

## 11. Platform support

Linux (glibc ≥ 2.34 or musl), macOS (x86-64, arm64), Windows x86-64, Python 3.11–3.14. This matches the wheels available on 14 Nov 2026 for `pqcrypto` (no Linux armv7, no Windows ARM64) and `cryptography`. Other platforms: unsupported, stated plainly in the README. POSIX permission checks on key files are skipped on Windows with a one-time note recommending NTFS access-control hardening.
