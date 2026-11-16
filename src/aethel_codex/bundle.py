"""Bundle filesystem layout and reading (YP §11.1, specs.md §10)."""

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from aethel_codex.constants import ASSET_NAME_RE
from aethel_codex.limits import DEFAULT_LIMITS, Limits

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class BundleItem:
    """An individual file entry inside a bundle."""

    name: str
    path: Path
    is_safe: bool = True
    error_code: str | None = None
    error_detail: str | None = None

    def read_bytes(self) -> bytes:
        """Read binary contents of this item directly without newline translation."""
        with open(self.path, "rb") as f:
            return f.read()


@dataclass
class BundleView:
    """View of an unpacked bundle on disk."""

    root_path: Path
    dir_name: str
    is_hex_dir_name: bool
    manifest_item: BundleItem | None = None
    text_items: list[BundleItem] = field(default_factory=list)
    asset_items: dict[str, BundleItem] = field(default_factory=dict)
    extra_asset_names: list[str] = field(default_factory=list)
    signature_items: list[BundleItem] = field(default_factory=list)
    extra_signature_names: list[str] = field(default_factory=list)
    attestation_items: list[BundleItem] = field(default_factory=list)
    extra_attestation_names: list[str] = field(default_factory=list)
    limit_exceeded: bool = False
    limit_reason: str | None = None
    scanned_entries: int = 0


def _check_safe_entry(path: Path) -> tuple[bool, str | None, str | None]:
    """Check if file entry is a safe regular file using lstat."""
    try:
        st = os.lstat(path)
        if os.path.islink(path):
            return False, "UNSAFE_PATH", f"Symlinks are forbidden: {path.name}"
        if not stat.S_ISREG(st.st_mode):
            return False, "UNSAFE_PATH", f"Not a regular file: {path.name}"
        return True, None, None
    except OSError as e:
        return False, "UNSAFE_PATH", str(e)


def _scan_dir(dir_path: Path) -> list[Path]:
    if not dir_path.is_dir() or os.path.islink(dir_path):
        return []
    try:
        with os.scandir(dir_path) as it:
            return [Path(entry.path) for entry in it]
    except OSError:
        return []


def _process_root_entries(entries: list[Path], view: BundleView) -> None:
    for entry_path in entries:
        safe, code, detail = _check_safe_entry(entry_path)
        if entry_path.name == "manifest.pip":
            view.manifest_item = BundleItem(
                name=entry_path.name,
                path=entry_path,
                is_safe=safe,
                error_code=code,
                error_detail=detail,
            )
        elif entry_path.name.startswith("text."):
            view.text_items.append(
                BundleItem(
                    name=entry_path.name,
                    path=entry_path,
                    is_safe=safe,
                    error_code=code,
                    error_detail=detail,
                )
            )


def _process_assets_entries(entries: list[Path], view: BundleView) -> None:
    for entry_path in entries:
        safe, code, detail = _check_safe_entry(entry_path)
        if not ASSET_NAME_RE.fullmatch(entry_path.name):
            view.extra_asset_names.append(entry_path.name)
            continue
        view.asset_items[entry_path.name] = BundleItem(
            name=entry_path.name,
            path=entry_path,
            is_safe=safe,
            error_code=code,
            error_detail=detail,
        )


def _process_signatures_entries(entries: list[Path], view: BundleView, limits: Limits) -> None:
    for entry_path in entries:
        safe, code, detail = _check_safe_entry(entry_path)
        if entry_path.name.endswith(".sig"):
            if len(view.signature_items) < limits.max_signatures:
                view.signature_items.append(
                    BundleItem(
                        name=entry_path.name,
                        path=entry_path,
                        is_safe=safe,
                        error_code=code,
                        error_detail=detail,
                    )
                )
            else:
                view.extra_signature_names.append(entry_path.name)
        else:
            view.extra_signature_names.append(entry_path.name)


def _process_attestations_entries(entries: list[Path], view: BundleView) -> None:
    for entry_path in entries:
        safe, code, detail = _check_safe_entry(entry_path)
        if entry_path.name.endswith(".att"):
            view.attestation_items.append(
                BundleItem(
                    name=entry_path.name,
                    path=entry_path,
                    is_safe=safe,
                    error_code=code,
                    error_detail=detail,
                )
            )
        else:
            view.extra_attestation_names.append(entry_path.name)


def read_bundle(path: Path | str, limits: Limits | None = None) -> BundleView:
    """Inspect and index an on-disk bundle directory under resource limits.

    Normative reference: Yellow Paper §11.1, specs.md §10, §12.
    """
    if limits is None:
        limits = DEFAULT_LIMITS

    root = Path(path).resolve()
    dir_name = root.name
    is_hex = bool(HEX64_RE.fullmatch(dir_name))
    view = BundleView(root_path=root, dir_name=dir_name, is_hex_dir_name=is_hex)

    if not root.is_dir():
        return view

    subdirs = [
        (root, _process_root_entries),
        (root / "assets", _process_assets_entries),
        (root / "signatures", lambda e, v: _process_signatures_entries(e, v, limits)),
        (root / "attestations", _process_attestations_entries),
    ]

    total_scanned = 0
    for sdir, processor in subdirs:
        entries = _scan_dir(sdir)
        total_scanned += len(entries)
        if total_scanned > limits.max_dir_entries:
            view.limit_exceeded = True
            view.limit_reason = "LIMIT_EXCEEDED"
            return view
        processor(entries, view)

    view.scanned_entries = total_scanned
    return view
