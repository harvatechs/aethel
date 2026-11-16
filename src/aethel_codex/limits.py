"""Resource limits configuration and defaults (YP §12.7, specs.md §12)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    """Resource limits enforced by the verification and publishing engines."""

    max_text_bytes: int = 64 * 1024 * 1024  # 64 MiB
    max_manifest_bytes: int = 1024 * 1024  # 1 MiB
    max_envelope_bytes: int = 256 * 1024  # 256 KiB
    max_signatures: int = 64
    max_asset_bytes: int | None = None  # None = unbounded/streamed
    max_dir_entries: int = 100_000


DEFAULT_LIMITS = Limits()
