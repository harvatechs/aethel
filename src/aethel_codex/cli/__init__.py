"""Command line interface for aethel."""

import sys


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments. If None, sys.argv[1:] is used.

    Returns:
        Exit code integer.
    """
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        sys.stderr.write("usage: aethel <command> [options]\n")
        return 2
    return 0


__all__ = ["main"]
