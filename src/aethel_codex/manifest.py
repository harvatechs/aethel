"""PMF-1 Manifest parser, serializer, and builder (YP §7, specs.md §7)."""

import re
from dataclasses import dataclass

import unicodedata2

from aethel_codex.constants import LABEL_MANIFEST
from aethel_codex.errors import AethelError, ManifestError
from aethel_codex.hashing import H
from aethel_codex.pid import Pid
from aethel_codex.unicode18 import is_forbidden

# Regular expressions for value validation (YP §7.3, §7.4)
PROFILE_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.-]*")
MARKUP_VALID = {"pip-md-1", "pip-tex-1", "pip-txt-1"}
LANG_RE = re.compile(r"[a-z]{2,3}(-([A-Z][a-z]{3}|[A-Z]{2}|[0-9]{3}|[a-z0-9]{2,8}))*")
UINT_RE = re.compile(r"0|[1-9][0-9]*")
MAX_UINT64 = 18446744073709551615

BEACON_BSRC_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
BEACON_BVAL_RE = re.compile(r"([0-9a-f]{2}){1,64}")

DERIVATIVE_KINDS = {"translation", "adaptation", "anthology", "commentary"}

ASSET_ANAME_RE = re.compile(r"(?!\.{1,2}\Z)[A-Za-z0-9._-]{1,128}")
ASSET_MEDIA_RE = re.compile(r"[a-z0-9][a-z0-9!#$&+\-.^_]{0,126}/[a-z0-9][a-z0-9!#$&+\-.^_]{0,126}")

KEY_RANKS: dict[str, int] = {
    "profile": 0,
    "markup": 1,
    "lang": 2,
    "title": 3,
    "license": 4,
    "beacon": 5,
    "text": 6,
    "work": 7,
    "parent": 8,
    "author": 9,
    "derivative": 10,
    "asset": 11,
    "cite": 12,
}

REPEATED_KEYS = {"parent", "author", "derivative", "asset", "cite"}


@dataclass(frozen=True)
class AssetEntry:
    """Declared asset file in manifest."""

    name: str
    pid: Pid
    length: int
    media_type: str


@dataclass(frozen=True)
class DerivativeEntry:
    """Derivative relationship declaration in manifest."""

    kind: str
    target: Pid


@dataclass(frozen=True)
class BeaconEntry:
    """Randomness beacon declaration in manifest."""

    source: str
    sequence: int
    value: bytes


@dataclass(frozen=True)
class Manifest:
    """Parsed PMF-1 Manifest representation."""

    profile: str
    markup: str
    lang: str
    title: str
    license: str
    text_pid: Pid
    text_length: int
    work_pid: Pid | None = None
    beacon: BeaconEntry | None = None
    parents: tuple[Pid, ...] = ()
    authors: tuple[Pid, ...] = ()
    derivatives: tuple[DerivativeEntry, ...] = ()
    assets: tuple[AssetEntry, ...] = ()
    cites: tuple[Pid, ...] = ()
    raw_bytes: bytes = b""

    def manifest_id(self) -> str:
        """Compute canonical manifest PID: pip1:m:<hex>."""
        raw = self.raw_bytes if self.raw_bytes else serialize_manifest(self)
        return f"pip1:m:{H(LABEL_MANIFEST, raw).hex()}"


def parse_uint(s: str) -> int:
    """Parse strictly formatted unsigned 64-bit integer."""
    if not UINT_RE.fullmatch(s):
        raise ManifestError("E_BAD_VALUE", f"Invalid integer syntax: {s!r}")
    val = int(s)
    if val > MAX_UINT64:
        raise ManifestError("E_INTEGER_RANGE", f"Integer exceeds 2^64 - 1: {val}")
    return val


def validate_value_text(s: str, max_bytes: int) -> None:
    """Validate value text constraints according to Yellow Paper §7.4."""
    if not s:
        raise ManifestError("E_BAD_VALUE", "Value text cannot be empty")
    raw = s.encode("utf-8")
    if len(raw) > max_bytes:
        raise ManifestError(
            "E_BAD_VALUE", f"Value text exceeds maximum {max_bytes} bytes: {len(raw)}"
        )
    if s.startswith(" ") or s.endswith(" "):
        raise ManifestError("E_BAD_VALUE", "Value text must not begin or end with space")
    if "\t" in s or "\r" in s or "\n" in s:
        raise ManifestError("E_BAD_VALUE", "Value text contains prohibited whitespace")
    if unicodedata2.normalize("NFC", s) != s:
        raise ManifestError("E_BAD_VALUE", "Value text is not in NFC form")
    for ch in s:
        cp = ord(ch)
        if is_forbidden(cp):
            raise ManifestError(
                "E_BAD_VALUE", f"Value text contains forbidden codepoint U+{cp:04X}"
            )
        if unicodedata2.category(ch) == "Cn":
            raise ManifestError(
                "E_BAD_VALUE", f"Value text contains unassigned codepoint U+{cp:04X}"
            )


@dataclass
class _ParserState:
    profile: str | None = None
    markup: str | None = None
    lang: str | None = None
    title: str | None = None
    license_val: str | None = None
    beacon: BeaconEntry | None = None
    text_pid: Pid | None = None
    text_length: int | None = None
    work_pid: Pid | None = None
    prev_rank: int | None = None
    parent_lines: list[str] = None  # type: ignore[assignment]
    parents: list[Pid] = None  # type: ignore[assignment]
    author_lines: list[str] = None  # type: ignore[assignment]
    authors: list[Pid] = None  # type: ignore[assignment]
    derivative_lines: list[str] = None  # type: ignore[assignment]
    derivatives: list[DerivativeEntry] = None  # type: ignore[assignment]
    asset_names: list[str] = None  # type: ignore[assignment]
    assets: list[AssetEntry] = None  # type: ignore[assignment]
    cite_lines: list[str] = None  # type: ignore[assignment]
    cites: list[Pid] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.parent_lines = []
        self.parents = []
        self.author_lines = []
        self.authors = []
        self.derivative_lines = []
        self.derivatives = []
        self.asset_names = []
        self.assets = []
        self.cite_lines = []
        self.cites = []


def _parse_beacon_value(value: str) -> BeaconEntry:
    bparts = value.split(" ")
    if len(bparts) != 3:
        raise ManifestError("E_BAD_VALUE", f"Invalid beacon line format: {value!r}")
    bsrc, bseq_str, bval_str = bparts
    if not BEACON_BSRC_RE.fullmatch(bsrc):
        raise ManifestError("E_BAD_VALUE", f"Invalid beacon source: {bsrc!r}")
    bseq = parse_uint(bseq_str)
    if not BEACON_BVAL_RE.fullmatch(bval_str):
        raise ManifestError("E_BAD_VALUE", f"Invalid beacon value: {bval_str!r}")
    return BeaconEntry(bsrc, bseq, bytes.fromhex(bval_str))


def _parse_text_value(value: str) -> tuple[Pid, int]:
    tparts = value.split(" ")
    if len(tparts) != 2:
        raise ManifestError("E_BAD_VALUE", f"Invalid text line format: {value!r}")
    tpid_str, tlen_str = tparts
    try:
        tpid = Pid.parse(tpid_str)
        if tpid.pid_type != "t":
            raise ManifestError("E_BAD_VALUE", "Text PID must have type 't'")
    except AethelError:
        raise ManifestError("E_BAD_VALUE", f"Invalid text PID: {tpid_str!r}") from None
    tlen = parse_uint(tlen_str)
    if tlen < 1:
        raise ManifestError("E_BAD_VALUE", "Text length must be >= 1")
    return tpid, tlen


def _parse_derivative_value(value: str) -> DerivativeEntry:
    dparts = value.split(" ")
    if len(dparts) != 2:
        raise ManifestError("E_BAD_VALUE", f"Invalid derivative format: {value!r}")
    kind, dpid_str = dparts
    if kind not in DERIVATIVE_KINDS:
        raise ManifestError("E_BAD_VALUE", f"Invalid derivative kind: {kind!r}")
    try:
        dpid = Pid.parse(dpid_str)
        if dpid.pid_type != "m":
            raise ManifestError("E_BAD_VALUE", "Derivative target PID must have type 'm'")
    except AethelError:
        raise ManifestError("E_BAD_VALUE", f"Invalid derivative PID: {dpid_str!r}") from None
    return DerivativeEntry(kind, dpid)


def _parse_asset_value(value: str) -> AssetEntry:
    aparts = value.split(" ")
    if len(aparts) != 4:
        raise ManifestError("E_BAD_VALUE", f"Invalid asset format: {value!r}")
    aname, apid_str, alen_str, media = aparts
    if not ASSET_ANAME_RE.fullmatch(aname):
        raise ManifestError("E_BAD_VALUE", f"Invalid asset filename: {aname!r}")
    try:
        apid = Pid.parse(apid_str)
        if apid.pid_type != "a":
            raise ManifestError("E_BAD_VALUE", "Asset PID must have type 'a'")
    except AethelError:
        raise ManifestError("E_BAD_VALUE", f"Invalid asset PID: {apid_str!r}") from None
    alen = parse_uint(alen_str)
    if not ASSET_MEDIA_RE.fullmatch(media):
        raise ManifestError("E_BAD_VALUE", f"Invalid asset media type: {media!r}")
    return AssetEntry(aname, apid, alen, media)


def _check_order_and_rank(key: str, state: _ParserState) -> None:
    if key not in KEY_RANKS:
        raise ManifestError("E_UNKNOWN_KEY", f"Unknown manifest key: {key!r}")
    rank = KEY_RANKS[key]
    if state.prev_rank is not None:
        if rank < state.prev_rank:
            raise ManifestError(
                "E_FIELD_ORDER", f"Field {key} out of order after rank {state.prev_rank}"
            )
        if rank == state.prev_rank and key not in REPEATED_KEYS:
            raise ManifestError("E_FIELD_ORDER", f"Duplicate singleton field {key}")
    state.prev_rank = rank


def _handle_header_fields(key: str, value: str, state: _ParserState) -> bool:
    if key == "profile":
        if value == "pip-1":
            state.profile = value
        elif PROFILE_TOKEN_RE.fullmatch(value):
            raise ManifestError("E_UNKNOWN_PROFILE", f"Unrecognized profile: {value!r}")
        else:
            raise ManifestError("E_BAD_VALUE", f"Invalid profile syntax: {value!r}")
        return True
    if key == "markup":
        if value in MARKUP_VALID:
            state.markup = value
        else:
            raise ManifestError("E_BAD_VALUE", f"Unrecognized markup: {value!r}")
        return True
    if key == "lang":
        if len(value.encode("utf-8")) <= 35 and LANG_RE.fullmatch(value):
            state.lang = value
        else:
            raise ManifestError("E_BAD_VALUE", f"Invalid language tag: {value!r}")
        return True
    if key == "title":
        validate_value_text(value, max_bytes=512)
        state.title = value
        return True
    if key == "license":
        validate_value_text(value, max_bytes=256)
        state.license_val = value
        return True
    return False


def _handle_doc_fields(key: str, value: str, state: _ParserState) -> bool:
    if key == "beacon":
        state.beacon = _parse_beacon_value(value)
        return True
    if key == "text":
        state.text_pid, state.text_length = _parse_text_value(value)
        return True
    if key == "work":
        try:
            wpid = Pid.parse(value)
            if wpid.pid_type != "m":
                raise ManifestError("E_BAD_VALUE", "Work PID must have type 'm'")
        except AethelError:
            raise ManifestError("E_BAD_VALUE", f"Invalid work PID: {value!r}") from None
        state.work_pid = wpid
        return True
    if key == "parent":
        try:
            ppid = Pid.parse(value)
            if ppid.pid_type != "m":
                raise ManifestError("E_BAD_VALUE", "Parent PID must have type 'm'")
        except AethelError:
            raise ManifestError("E_BAD_VALUE", f"Invalid parent PID: {value!r}") from None
        state.parent_lines.append(value)
        state.parents.append(ppid)
        return True
    return False


def _handle_relation_fields(key: str, value: str, state: _ParserState) -> None:
    if key == "author":
        try:
            apid = Pid.parse(value)
            if apid.pid_type != "k":
                raise ManifestError("E_BAD_VALUE", "Author PID must have type 'k'")
        except AethelError:
            raise ManifestError("E_BAD_VALUE", f"Invalid author PID: {value!r}") from None
        state.author_lines.append(value)
        state.authors.append(apid)
    elif key == "derivative":
        entry = _parse_derivative_value(value)
        state.derivative_lines.append(value)
        state.derivatives.append(entry)
    elif key == "asset":
        asset_entry = _parse_asset_value(value)
        state.asset_names.append(asset_entry.name)
        state.assets.append(asset_entry)
    elif key == "cite":
        try:
            cpid = Pid.parse(value)
            if cpid.pid_type not in ("m", "t", "a"):
                raise ManifestError("E_BAD_VALUE", "Citation PID must be m, t, or a")
        except AethelError:
            raise ManifestError("E_BAD_VALUE", f"Invalid citation PID: {value!r}") from None
        state.cite_lines.append(value)
        state.cites.append(cpid)


def _handle_body_fields(key: str, value: str, state: _ParserState) -> None:
    if _handle_header_fields(key, value, state):
        return
    if _handle_doc_fields(key, value, state):
        return
    _handle_relation_fields(key, value, state)


def _check_sorting(items: list[str], label: str) -> None:
    for i in range(len(items) - 1):
        if items[i].encode("utf-8") >= items[i + 1].encode("utf-8"):
            raise ManifestError(
                "E_NOT_SORTED_OR_UNIQUE",
                f"{label} entries are not strictly sorted or unique: "
                f"{items[i]!r} >= {items[i + 1]!r}",
            )


def _validate_state(state: _ParserState) -> None:
    if (
        state.profile is None
        or state.markup is None
        or state.lang is None
        or state.title is None
        or state.license_val is None
        or state.text_pid is None
        or state.text_length is None
    ):
        raise ManifestError("E_MISSING_FIELD", "One or more required manifest fields are missing")

    if (state.work_pid is not None and not state.parents) or (
        state.work_pid is None and state.parents
    ):
        raise ManifestError(
            "E_WORK_PARENT_RULE", "work must be present if and only if at least one parent exists"
        )

    _check_sorting(state.parent_lines, "parent")
    _check_sorting(state.author_lines, "author")
    _check_sorting(state.derivative_lines, "derivative")
    _check_sorting(state.cite_lines, "cite")
    _check_sorting(state.asset_names, "asset")


def parse_manifest(data: bytes) -> Manifest:
    """Parse PMF-1 manifest bytes under strict normative rules.

    Normative reference: Yellow Paper §7, specs.md §7.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ManifestError("E_INVALID_UTF8", f"Invalid UTF-8 at offset {e.start}") from None

    if "\r" in text:
        raise ManifestError("E_BAD_LINES", "Carriage return is not permitted in manifests")
    if not text.endswith("\n"):
        raise ManifestError("E_BAD_LINES", "Manifest must end with a linefeed")

    lines = text.split("\n")[:-1]
    if any(line == "" for line in lines):
        raise ManifestError("E_BAD_LINES", "Empty lines are not permitted in manifests")

    if lines[0] != "pip-manifest 1":
        raise ManifestError("E_BAD_MAGIC", f"Invalid magic header: {lines[0]!r}")

    state = _ParserState()

    for line in lines[1:]:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            raise ManifestError("E_BAD_LINES", f"Line missing key-value space separator: {line!r}")
        key, value = parts[0], parts[1]
        _check_order_and_rank(key, state)
        _handle_body_fields(key, value, state)

    _validate_state(state)

    manifest = Manifest(
        profile=state.profile,  # type: ignore[arg-type]
        markup=state.markup,  # type: ignore[arg-type]
        lang=state.lang,  # type: ignore[arg-type]
        title=state.title,  # type: ignore[arg-type]
        license=state.license_val,  # type: ignore[arg-type]
        beacon=state.beacon,
        text_pid=state.text_pid,  # type: ignore[arg-type]
        text_length=state.text_length,  # type: ignore[arg-type]
        work_pid=state.work_pid,
        parents=tuple(state.parents),
        authors=tuple(state.authors),
        derivatives=tuple(state.derivatives),
        assets=tuple(state.assets),
        cites=tuple(state.cites),
        raw_bytes=data,
    )

    reserialized = serialize_manifest(manifest)
    if reserialized != data:
        raise ManifestError("E_ROUNDTRIP", "Re-serialized manifest bytes do not match input")

    return manifest


def serialize_manifest(manifest: Manifest) -> bytes:
    """Serialize Manifest to canonical PMF-1 UTF-8 bytes."""
    lines: list[str] = [
        "pip-manifest 1",
        f"profile {manifest.profile}",
        f"markup {manifest.markup}",
        f"lang {manifest.lang}",
        f"title {manifest.title}",
        f"license {manifest.license}",
    ]

    if manifest.beacon is not None:
        b = manifest.beacon
        lines.append(f"beacon {b.source} {b.sequence} {b.value.hex()}")

    lines.append(f"text {manifest.text_pid} {manifest.text_length}")

    if manifest.work_pid is not None:
        lines.append(f"work {manifest.work_pid}")

    for parent in manifest.parents:
        lines.append(f"parent {parent}")

    for author in manifest.authors:
        lines.append(f"author {author}")

    for deriv in manifest.derivatives:
        lines.append(f"derivative {deriv.kind} {deriv.target}")

    for asset in manifest.assets:
        lines.append(f"asset {asset.name} {asset.pid} {asset.length} {asset.media_type}")

    for cite in manifest.cites:
        lines.append(f"cite {cite}")

    return "\n".join(lines).encode("utf-8") + b"\n"


class ManifestBuilder:
    """Fluent builder for constructing validated PMF-1 manifests."""

    def __init__(self) -> None:
        """Initialize empty manifest builder."""
        self._profile: str = "pip-1"
        self._markup: str = "pip-md-1"
        self._lang: str = "en"
        self._title: str = ""
        self._license: str = ""
        self._beacon: BeaconEntry | None = None
        self._text_pid: Pid | None = None
        self._text_length: int = 0
        self._work_pid: Pid | None = None
        self._parents: list[Pid] = []
        self._authors: list[Pid] = []
        self._derivatives: list[DerivativeEntry] = []
        self._assets: dict[str, AssetEntry] = {}
        self._cites: list[Pid] = []

    def set_profile(self, profile: str) -> "ManifestBuilder":
        """Set manifest profile token."""
        self._profile = profile
        return self

    def set_markup(self, markup: str) -> "ManifestBuilder":
        """Set manifest markup profile token."""
        self._markup = markup
        return self

    def set_lang(self, lang: str) -> "ManifestBuilder":
        """Set primary document language tag."""
        self._lang = lang
        return self

    def set_title(self, title: str) -> "ManifestBuilder":
        """Set title text."""
        self._title = title
        return self

    def set_license(self, license_str: str) -> "ManifestBuilder":
        """Set license identifier or declaration text."""
        self._license = license_str
        return self

    def set_beacon(self, source: str, sequence: int, value: bytes) -> "ManifestBuilder":
        """Set randomness beacon evidence."""
        self._beacon = BeaconEntry(source, sequence, value)
        return self

    def set_text(self, text_pid: Pid, text_length: int) -> "ManifestBuilder":
        """Set canonical manuscript text reference."""
        self._text_pid = text_pid
        self._text_length = text_length
        return self

    def set_work(self, work_pid: Pid | None) -> "ManifestBuilder":
        """Set abstract work identifier."""
        self._work_pid = work_pid
        return self

    def add_parent(self, parent_pid: Pid) -> "ManifestBuilder":
        """Add parent manifest identifier."""
        self._parents.append(parent_pid)
        return self

    def add_author(self, author_key_pid: Pid) -> "ManifestBuilder":
        """Add author public key identifier."""
        self._authors.append(author_key_pid)
        return self

    def add_derivative(self, kind: str, target_pid: Pid) -> "ManifestBuilder":
        """Add derivative relationship."""
        self._derivatives.append(DerivativeEntry(kind, target_pid))
        return self

    def add_asset(
        self, name: str, asset_pid: Pid, length: int, media_type: str
    ) -> "ManifestBuilder":
        """Add declared asset. If name already added with identical content, ignore."""
        if name in self._assets:
            existing = self._assets[name]
            if (
                existing.pid != asset_pid
                or existing.length != length
                or existing.media_type != media_type
            ):
                raise ManifestError(
                    "E_NOT_SORTED_OR_UNIQUE",
                    f"Conflicting asset declarations for name {name!r}",
                )
        else:
            self._assets[name] = AssetEntry(name, asset_pid, length, media_type)
        return self

    def add_cite(self, target_pid: Pid) -> "ManifestBuilder":
        """Add citation reference."""
        self._cites.append(target_pid)
        return self

    def build(self) -> Manifest:
        """Construct and strictly self-validate PMF-1 manifest."""
        if self._text_pid is None:
            raise ManifestError("E_MISSING_FIELD", "Text PID must be set")

        sorted_parents = tuple(sorted(set(self._parents), key=lambda p: str(p).encode()))
        sorted_authors = tuple(sorted(set(self._authors), key=lambda a: str(a).encode()))
        sorted_derivatives = tuple(
            sorted(
                set(self._derivatives),
                key=lambda d: f"{d.kind} {d.target}".encode(),
            )
        )
        sorted_assets = tuple(sorted(self._assets.values(), key=lambda a: a.name.encode()))
        sorted_cites = tuple(sorted(set(self._cites), key=lambda c: str(c).encode()))

        manifest = Manifest(
            profile=self._profile,
            markup=self._markup,
            lang=self._lang,
            title=self._title,
            license=self._license,
            beacon=self._beacon,
            text_pid=self._text_pid,
            text_length=self._text_length,
            work_pid=self._work_pid,
            parents=sorted_parents,
            authors=sorted_authors,
            derivatives=sorted_derivatives,
            assets=sorted_assets,
            cites=sorted_cites,
        )

        raw = serialize_manifest(manifest)
        return parse_manifest(raw)
