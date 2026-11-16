"""Aethel Codex: reference CLI and library for the Permanent Ink Protocol (PIP-1)."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("aethel-codex")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
