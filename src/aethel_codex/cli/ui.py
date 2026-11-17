"""Terminal UI styling, color handling, and symbol configuration (cli-spec.md §1)."""

import os
import sys
from dataclasses import dataclass


class UsageError(Exception):
    """Command-line usage error (exit code 2)."""

    def __init__(self, message: str) -> None:
        """Initialize usage error with diagnostic message."""
        super().__init__(message)
        self.message = message


@dataclass
class UIContext:
    """Runtime terminal UI presentation settings."""

    json_mode: bool = False
    quiet: bool = False
    verbose: bool = False
    no_color: bool = False
    ascii_mode: bool = False
    debug: bool = False

    def can_color(self, stream: object = sys.stdout) -> bool:
        """Return True if colored output is allowed on given stream."""
        if self.no_color or self.json_mode:
            return False
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        is_tty = getattr(stream, "isatty", None)
        return bool(is_tty and is_tty())

    def dot(self) -> str:
        """Return item separator."""
        return "-" if self.ascii_mode else "·"

    def ellipsis(self) -> str:
        """Return ellipsis string."""
        return "..." if self.ascii_mode else "…"

    def abbreviate_id(self, pid_str: str) -> str:
        """Abbreviate 64-hex PID to first 8 and last 4 hex characters for human display."""
        parts = pid_str.split(":")
        if len(parts) == 3 and len(parts[2]) == 64:
            prefix = f"{parts[0]}:{parts[1]}:"
            hex_part = parts[2]
            return f"{prefix}{hex_part[:8]}{self.ellipsis()}{hex_part[-4:]}"
        return pid_str


def sanitize_terminal_text(text: str) -> str:
    r"""Sanitize untrusted text before printing to terminal (R-SEC-03, YP §12.6).

    Escapes C0/C1 controls, bidirectional controls, and tag characters as \u{...}.
    """
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        is_c0 = cp < 0x20
        is_c1 = 0x7F <= cp <= 0x9F
        is_bidi = cp in (0x200E, 0x200F) or (0x202A <= cp <= 0x202E) or (0x2066 <= cp <= 0x2069)
        is_tag = 0xE0000 <= cp <= 0xE007F

        if is_c0 or is_c1 or is_bidi or is_tag:
            out.append(f"\\u{{{cp:04X}}}")
        else:
            out.append(ch)
    return "".join(out)


def colorize(text: str, code: str, enabled: bool) -> str:
    """Wrap text in ANSI escape sequence if enabled."""
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str, enabled: bool) -> str:
    """Format green text."""
    return colorize(text, "32", enabled)


def red(text: str, enabled: bool) -> str:
    """Format red text."""
    return colorize(text, "31", enabled)


def yellow(text: str, enabled: bool) -> str:
    """Format yellow text."""
    return colorize(text, "33", enabled)


def bold(text: str, enabled: bool) -> str:
    """Format bold text."""
    return colorize(text, "1", enabled)
