"""Verify basic package structure and importability."""

import aethel_codex


def test_package_version() -> None:
    assert hasattr(aethel_codex, "__version__")
    assert aethel_codex.__version__ == "0.1.0"
