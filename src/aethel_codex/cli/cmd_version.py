"""CLI handler for aethel version (cli-spec.md §3)."""

import argparse
import importlib.metadata
import json
import platform
import sys
from typing import Any

import unicodedata2

from aethel_codex.cli.ui import UIContext
from aethel_codex.constants import TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION


def _get_pkg_version(pkg_name: str) -> str:
    try:
        return importlib.metadata.version(pkg_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _gather_version_data() -> dict[str, Any]:
    crypto_ver = _get_pkg_version("cryptography")
    pqcrypto_ver = _get_pkg_version("pqcrypto")

    backends = [
        {"alg": "ml-dsa-87", "provider": "cryptography", "version": crypto_ver},
        {"alg": "ml-dsa-65", "provider": "pqcrypto", "version": pqcrypto_ver},
        {"alg": "slh-dsa-sha2-256s", "provider": "pqcrypto", "version": pqcrypto_ver},
        {"alg": "slh-dsa-shake-256s", "provider": "pqcrypto", "version": pqcrypto_ver},
    ]

    return {
        "schema": "aethel.version/1",
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "profile": "pip-1",
            "yellow_paper": YELLOW_PAPER_VERSION,
        },
        "unicode": {
            "version": unicodedata2.unidata_version,
            "package": f"unicodedata2 {_get_pkg_version('unicodedata2')}",
        },
        "backends": backends,
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }


def handle_version(args: argparse.Namespace, ui: UIContext) -> int:
    """Execute version command."""
    data = _gather_version_data()

    if ui.json_mode:
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
    else:
        tool_info = data["tool"]
        sys.stdout.write(
            f"{tool_info['name']} {tool_info['version']} "
            f"(PIP-1 profile {tool_info['profile']}, Yellow Paper {tool_info['yellow_paper']})\n"
        )
        sys.stdout.write(
            f"Unicode data: {data['unicode']['version']} ({data['unicode']['package']})\n"
        )
        sys.stdout.write("Backends:\n")
        for b in data["backends"]:
            sys.stdout.write(f"  {b['alg']:<18} {b['provider']} {b['version']}\n")
        py_info = data["python"]
        sys.stdout.write(f"Python:       {py_info['version']} ({py_info['implementation']})\n")
        plat = data["platform"]
        sys.stdout.write(f"Platform:     {plat['system']} {plat['release']} {plat['machine']}\n")

    return 0
