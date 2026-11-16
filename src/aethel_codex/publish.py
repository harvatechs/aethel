"""Manuscript publishing, atomic bundle writing, and revision (YP §7, §10, §11)."""

import contextlib
import os
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from aethel_codex.constants import (
    ASSET_NAME_RE,
    LABEL_MANIFEST,
)
from aethel_codex.ctf1 import canonicalize
from aethel_codex.envelope import SignatureEnvelope, serialize_envelope
from aethel_codex.errors import AethelError, InternalError, ManifestError
from aethel_codex.hashing import H
from aethel_codex.keyfile import SecretKey, load_key
from aethel_codex.limits import DEFAULT_LIMITS, Limits
from aethel_codex.manifest import Manifest, ManifestBuilder, parse_manifest, serialize_manifest
from aethel_codex.merkle import asset_id, text_id
from aethel_codex.pid import Pid
from aethel_codex.report import VerifyReport
from aethel_codex.signing import sign_manifest
from aethel_codex.verify import verify_bundle

DEFAULT_MEDIA_TYPES: dict[str, str] = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".xml": "application/xml",
}

MARKUP_BY_EXT: dict[str, str] = {
    ".md": "pip-md-1",
    ".markdown": "pip-md-1",
    ".tex": "pip-tex-1",
    ".txt": "pip-txt-1",
}

EXT_BY_MARKUP: dict[str, str] = {
    "pip-md-1": "md",
    "pip-tex-1": "tex",
    "pip-txt-1": "txt",
}


@dataclass(frozen=True)
class AssetInput:
    """Declared input asset for publishing."""

    path: Path
    name: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class PublishRequest:
    """Parameters for publishing a manuscript bundle."""

    manuscript_path: Path
    title: str | None = None
    title_from_heading: bool = False
    license: str | None = None
    markup: str | None = None
    lang: str = "und"
    keys: Sequence[SecretKey | Path] = field(default_factory=tuple)
    passphrases: Sequence[str | bytes | None] = field(default_factory=tuple)
    unsigned: bool = False
    authors: Sequence[Pid | str] = field(default_factory=tuple)
    assets: Sequence[AssetInput] = field(default_factory=tuple)
    cites: Sequence[Pid | str] = field(default_factory=tuple)
    derivatives: Sequence[tuple[str, Pid | str]] = field(default_factory=tuple)
    beacon: tuple[str, int, bytes | str] | None = None
    out_dir: Path | str = Path(".")
    dry_run: bool = False
    parents: Sequence[Pid | str] = field(default_factory=tuple)
    work: Pid | str | None = None
    parents_dir: Path | str | None = None
    limits: Limits = DEFAULT_LIMITS


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing a manuscript bundle."""

    manifest_pid: Pid
    text_pid: Pid
    manifest: Manifest
    bundle_path: Path | None
    envelopes: tuple[SignatureEnvelope, ...]
    dry_run: bool
    verify_report: VerifyReport | None = None


def _extract_heading_title(raw_text: str) -> str:
    """Extract title from the first Markdown level-1 heading (# Title)."""
    for line in raw_text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    raise AethelError("E_BAD_VALUE", "No markdown heading found for --title-from-heading")


def _resolve_markup(manuscript_path: Path, markup_arg: str | None) -> str:
    """Resolve markup string to pip-md-1, pip-tex-1, or pip-txt-1."""
    if markup_arg:
        normalized = markup_arg.lower()
        if normalized in ("md", "pip-md-1"):
            return "pip-md-1"
        if normalized in ("tex", "pip-tex-1"):
            return "pip-tex-1"
        if normalized in ("txt", "pip-txt-1"):
            return "pip-txt-1"
        raise AethelError("E_BAD_VALUE", f"Unsupported markup: {markup_arg!r}")

    suffix = manuscript_path.suffix.lower()
    if suffix in MARKUP_BY_EXT:
        return MARKUP_BY_EXT[suffix]
    raise AethelError(
        "E_BAD_VALUE", f"Cannot infer markup format from extension: {manuscript_path.suffix!r}"
    )


def _resolve_keys(
    keys: Sequence[SecretKey | Path], passphrases: Sequence[str | bytes | None]
) -> list[SecretKey]:
    """Resolve and load all signing keys."""
    resolved: list[SecretKey] = []
    for i, k in enumerate(keys):
        if isinstance(k, SecretKey):
            resolved.append(k)
        else:
            pwd = passphrases[i] if i < len(passphrases) else None
            resolved.append(load_key(k, passphrase=pwd))
    return resolved


def _prepare_assets(
    assets: Sequence[AssetInput],
) -> list[tuple[str, Path, bytes, Pid, int, str]]:
    """Validate, read, and hash input assets.

    Returns:
        List of (asset_name, path, raw_bytes, asset_pid, length, media_type).
    """
    seen_lower: dict[str, str] = {}
    prepared: list[tuple[str, Path, bytes, Pid, int, str]] = []

    for a in assets:
        name = a.name if a.name else a.path.name
        if not ASSET_NAME_RE.fullmatch(name):
            raise AethelError(
                "E_BAD_VALUE", f"Asset name does not match required grammar: {name!r}"
            )

        lower = name.lower()
        if lower in seen_lower:
            conflict = seen_lower[lower]
            raise AethelError(
                "E_NOT_SORTED_OR_UNIQUE",
                f"Asset name collision (case-insensitive): {name!r} conflicts with {conflict!r}",
            )
        seen_lower[lower] = name

        try:
            data = a.path.read_bytes()
        except OSError as e:
            raise AethelError("ASSET_MISSING", f"Cannot read asset file {a.path}: {e}") from None

        media_type = a.media_type
        if not media_type:
            media_type = DEFAULT_MEDIA_TYPES.get(a.path.suffix.lower(), "application/octet-stream")

        a_pid = Pid.parse(asset_id(data))
        prepared.append((name, a.path, data, a_pid, len(data), media_type))

    return prepared


def _compare_directory_contents(target_dir: Path, expected_files: dict[str, bytes]) -> bool:
    """Check if target_dir has exactly expected_files and identical binary contents."""
    if not target_dir.is_dir():
        return False

    actual_files: dict[str, bytes] = {}
    for root, _, files in os.walk(target_dir):
        for f in files:
            p = Path(root) / f
            rel = p.relative_to(target_dir).as_posix()
            try:
                actual_files[rel] = p.read_bytes()
            except OSError:
                return False

    return actual_files == expected_files


def _atomic_write_bundle(target_dir: Path, expected_files: dict[str, bytes]) -> None:
    """Atomically write files to target_dir via a sibling temporary directory."""
    parent_dir = target_dir.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(dir=parent_dir, prefix=".tmp-bundle-"))
    try:
        for rel_path, data in expected_files.items():
            dest = tmp_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
                f.flush()
                with contextlib.suppress(OSError):
                    os.fsync(f.fileno())

        with contextlib.suppress(OSError):
            fd = os.open(tmp_dir, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

        os.replace(tmp_dir, target_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def _read_and_canonicalize_manuscript(req: PublishRequest) -> tuple[bytes, bytes, Pid]:
    """Read manuscript and return (raw_bytes, canon_bytes, text_pid)."""
    try:
        raw_text_bytes = req.manuscript_path.read_bytes()
    except OSError as e:
        msg = f"Cannot read manuscript {req.manuscript_path}: {e}"
        raise AethelError("TEXT_MISSING", msg) from None

    if len(raw_text_bytes) > req.limits.max_text_bytes:
        raise AethelError(
            "LIMIT_EXCEEDED",
            f"Manuscript size {len(raw_text_bytes)} exceeds limit {req.limits.max_text_bytes}",
        )

    canon_bytes, _ = canonicalize(raw_text_bytes)
    t_pid = Pid.parse(text_id(canon_bytes))
    return raw_text_bytes, canon_bytes, t_pid


def _resolve_title(req: PublishRequest, raw_bytes: bytes, canon_bytes: bytes) -> str:
    """Resolve manuscript title from parameters or heading."""
    title = req.title
    if req.title_from_heading or not title:
        try:
            raw_str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_str = canon_bytes.decode("utf-8")
        extracted = _extract_heading_title(raw_str)
        if not title:
            title = extracted
    return title


def _resolve_authors(
    authors_arg: Sequence[Pid | str], secret_keys: Sequence[SecretKey]
) -> list[Pid]:
    """Combine declared authors and signing key PIDs."""
    declared: list[Pid] = []
    for a in authors_arg:
        declared.append(a if isinstance(a, Pid) else Pid.parse(a))
    for sk in secret_keys:
        if sk.key_pid not in declared:
            declared.append(sk.key_pid)
    return declared


def _construct_manifest(
    req: PublishRequest,
    title: str,
    markup: str,
    t_pid: Pid,
    canon_bytes: bytes,
    declared_authors: list[Pid],
    prepared_assets: list[tuple[str, Path, bytes, Pid, int, str]],
) -> tuple[Manifest, bytes, Pid]:
    """Construct and serialize manifest."""
    builder = ManifestBuilder()
    builder.set_profile("pip-1")
    builder.set_markup(markup)
    builder.set_lang(req.lang)
    builder.set_title(title)
    builder.set_license(req.license or "")
    builder.set_text(t_pid, len(canon_bytes))

    if req.beacon:
        src, seq, bval = req.beacon
        b_bytes = bytes.fromhex(bval) if isinstance(bval, str) else bval
        builder.set_beacon(src, seq, b_bytes)

    if req.work:
        w_pid = req.work if isinstance(req.work, Pid) else Pid.parse(req.work)
        builder.set_work(w_pid)

    for p in req.parents:
        builder.add_parent(p if isinstance(p, Pid) else Pid.parse(p))

    for a in declared_authors:
        builder.add_author(a)

    for kind, target in req.derivatives:
        t = target if isinstance(target, Pid) else Pid.parse(target)
        builder.add_derivative(kind, t)

    for name, _, _, a_pid, length, media_type in prepared_assets:
        builder.add_asset(name, a_pid, length, media_type)

    for c in req.cites:
        builder.add_cite(c if isinstance(c, Pid) else Pid.parse(c))

    try:
        manifest = builder.build()
    except ManifestError as e:
        raise AethelError(e.code, str(e)) from None

    manifest_bytes = serialize_manifest(manifest)
    if len(manifest_bytes) > req.limits.max_manifest_bytes:
        raise AethelError(
            "LIMIT_EXCEEDED",
            f"Manifest size {len(manifest_bytes)} exceeds limit {req.limits.max_manifest_bytes}",
        )

    manifest_digest = H(LABEL_MANIFEST, manifest_bytes)
    m_pid = Pid.create("m", manifest_digest)
    return manifest, manifest_bytes, m_pid


def _sign_and_assemble_files(
    manifest_digest: bytes,
    secret_keys: Sequence[SecretKey],
    manifest_bytes: bytes,
    text_filename: str,
    canon_bytes: bytes,
    prepared_assets: list[tuple[str, Path, bytes, Pid, int, str]],
) -> tuple[list[SignatureEnvelope], dict[str, bytes]]:
    """Sign manifest and assemble relative file path map."""
    envelopes: list[SignatureEnvelope] = []
    for sk in secret_keys:
        env = sign_manifest(manifest_digest, role=1, alg=sk.alg.alg_id, secret_key=sk.secret_bytes)
        envelopes.append(env)

    expected_files: dict[str, bytes] = {
        "manifest.pip": manifest_bytes,
        text_filename: canon_bytes,
    }
    for name, _, data, _, _, _ in prepared_assets:
        expected_files[f"assets/{name}"] = data
    for env in envelopes:
        expected_files[env.envelope_filename()] = serialize_envelope(env)

    return envelopes, expected_files


def publish_bundle(req: PublishRequest) -> PublishResult:
    """Publish a manuscript into an atomic PIP-1 bundle directory."""
    raw_text, canon_text, t_pid = _read_and_canonicalize_manuscript(req)
    title = _resolve_title(req, raw_text, canon_text)
    markup = _resolve_markup(req.manuscript_path, req.markup)
    text_filename = f"text.{EXT_BY_MARKUP[markup]}"

    if not req.license:
        raise AethelError("E_MISSING_FIELD", "--license is required")
    if not req.keys and not req.unsigned:
        raise AethelError("NO_SIGNATURES", "Either --key or --unsigned is required")

    secret_keys = _resolve_keys(req.keys, req.passphrases)
    declared_authors = _resolve_authors(req.authors, secret_keys)
    prepared_assets = _prepare_assets(req.assets)

    manifest, manifest_bytes, m_pid = _construct_manifest(
        req, title, markup, t_pid, canon_text, declared_authors, prepared_assets
    )

    envelopes, expected_files = _sign_and_assemble_files(
        m_pid.digest, secret_keys, manifest_bytes, text_filename, canon_text, prepared_assets
    )

    if req.dry_run:
        return PublishResult(
            manifest_pid=m_pid,
            text_pid=t_pid,
            manifest=manifest,
            bundle_path=None,
            envelopes=tuple(envelopes),
            dry_run=True,
        )

    out_dir = Path(req.out_dir).resolve()
    target_dir = out_dir / m_pid.hex()

    if target_dir.exists():
        if not _compare_directory_contents(target_dir, expected_files):
            raise AethelError(
                "ID_MISMATCH",
                f"Bundle directory exists with differing content: {target_dir}",
            )
    else:
        _atomic_write_bundle(target_dir, expected_files)

    report = verify_bundle(target_dir, parents=req.parents_dir, limits=req.limits)
    if report.integrity != "PASS":
        raise InternalError(
            "BACKEND_ERROR",
            f"Published bundle failed self-verification: {report.checks_dict()}",
        )

    return PublishResult(
        manifest_pid=m_pid,
        text_pid=t_pid,
        manifest=manifest,
        bundle_path=target_dir,
        envelopes=tuple(envelopes),
        dry_run=False,
        verify_report=report,
    )


def revise_bundle(
    parent_bundle_path: Path | str,
    req: PublishRequest,
    keep_assets: bool = False,
    keep_cites: bool = False,
) -> PublishResult:
    """Create a revision of an existing parent bundle."""
    p_path = Path(parent_bundle_path).resolve()
    manifest_file = p_path / "manifest.pip"
    if not manifest_file.exists():
        raise AethelError("MANIFEST_MISSING", f"Parent bundle manifest not found: {manifest_file}")

    parent_manifest_bytes = manifest_file.read_bytes()
    parent_manifest = parse_manifest(parent_manifest_bytes)
    parent_digest = H(LABEL_MANIFEST, parent_manifest_bytes)
    parent_pid = Pid.create("m", parent_digest)

    work_pid = parent_manifest.work_pid if parent_manifest.work_pid else parent_pid
    title = req.title if req.title else parent_manifest.title
    license_str = req.license if req.license else parent_manifest.license
    markup = req.markup if req.markup else parent_manifest.markup
    lang = req.lang if req.lang != "und" else parent_manifest.lang

    authors = list(req.authors) if req.authors else list(parent_manifest.authors)
    parents = list(req.parents)
    if parent_pid not in parents:
        parents.append(parent_pid)

    assets = list(req.assets)
    if keep_assets and not assets:
        for a_entry in parent_manifest.assets:
            a_file = p_path / "assets" / a_entry.name
            if a_file.exists():
                assets.append(
                    AssetInput(path=a_file, name=a_entry.name, media_type=a_entry.media_type)
                )

    cites = list(req.cites) if req.cites else (list(parent_manifest.cites) if keep_cites else [])

    rev_req = PublishRequest(
        manuscript_path=req.manuscript_path,
        title=title,
        title_from_heading=req.title_from_heading,
        license=license_str,
        markup=markup,
        lang=lang,
        keys=req.keys,
        passphrases=req.passphrases,
        unsigned=req.unsigned,
        authors=authors,
        assets=assets,
        cites=cites,
        derivatives=req.derivatives,
        beacon=req.beacon,
        out_dir=req.out_dir,
        dry_run=req.dry_run,
        parents=parents,
        work=work_pid,
        parents_dir=req.parents_dir or p_path.parent,
        limits=req.limits,
    )

    return publish_bundle(rev_req)
