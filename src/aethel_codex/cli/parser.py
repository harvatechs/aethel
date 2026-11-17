"""Command-line argument parser definitions for aethel (cli-spec.md §1, §3)."""

import argparse

from aethel_codex.constants import TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION

VERSION_STRING = (
    f"{TOOL_NAME} {TOOL_VERSION} (PIP-1 profile pip-1, Yellow Paper {YELLOW_PAPER_VERSION})"
)


def _build_global_parent() -> argparse.ArgumentParser:
    """Build shared parent parser holding global flags."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Machine output in JSON format",
    )
    parent.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Suppress non-error stderr",
    )
    parent.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Add detailed progress/output",
    )
    parent.add_argument(
        "--no-color",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Disable ANSI color output",
    )
    parent.add_argument(
        "--ascii",
        dest="ascii_mode",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Plain ASCII output",
    )
    parent.add_argument(
        "--debug",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Show tracebacks and details on error",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    """Build top-level ArgumentParser with all subcommands and flags."""
    global_parent = _build_global_parent()
    parser = argparse.ArgumentParser(
        prog="aethel",
        description="Reference CLI for Permanent Ink Protocol (PIP-1)",
        add_help=True,
        parents=[global_parent],
    )
    parser.add_argument("--version", action="version", version=VERSION_STRING)

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # 1. canon
    canon_parser = subparsers.add_parser(
        "canon",
        parents=[global_parent],
        help="Apply CTF-1 text canonicalization",
        description="Apply CTF-1 and write canonical bytes to stdout or -o OUT.",
    )
    canon_parser.add_argument("file", help="Input file path or '-' for stdin")
    canon_parser.add_argument("-o", "--out", help="Output file path")
    canon_parser.add_argument("--check", action="store_true", help="Exit 0 if canonical, 1 if not")
    canon_parser.add_argument("--report", action="store_true", help="Explain changes on stderr")

    # 2. id
    id_parser = subparsers.add_parser(
        "id",
        parents=[global_parent],
        help="Print Permanent Ink Protocol identifier (PID)",
        description="Compute and print pip1:t:... or pip1:a:... identifier.",
    )
    id_parser.add_argument("file", help="File path or '-' for stdin")
    id_parser.add_argument("--kind", choices=["text", "asset"], help="Override blob kind")

    # 3. keygen
    keygen_parser = subparsers.add_parser(
        "keygen",
        parents=[global_parent],
        help="Create signing key file",
        description="Generate an AKF-1 signing key file.",
    )
    keygen_parser.add_argument(
        "--alg",
        choices=["ml-dsa-87", "ml-dsa-65", "slh-dsa-sha2-256s", "slh-dsa-shake-256s"],
        default="ml-dsa-87",
        help="Signature algorithm (default: ml-dsa-87)",
    )
    keygen_parser.add_argument("--dual", action="store_true", help="Create ML-DSA and SLH-DSA keys")
    keygen_parser.add_argument("--out", help="Single key output file path")
    keygen_parser.add_argument("--out-dir", default=".", help="Output directory (default: .)")
    keygen_parser.add_argument(
        "--no-passphrase", action="store_true", help="Store secret unencrypted"
    )
    keygen_parser.add_argument("--passphrase-file", help="Read passphrase from file")

    # 4. key info
    key_parser = subparsers.add_parser(
        "key", parents=[global_parent], help="Key inspection commands"
    )
    key_sub = key_parser.add_subparsers(dest="key_command", metavar="<subcommand>")
    key_info = key_sub.add_parser("info", parents=[global_parent], help="Print key metadata")
    key_info.add_argument("keyfile", help="Path to AKF-1 key file")
    key_info.add_argument("--public", action="store_true", help="Show base64 public key")

    # 5. publish
    pub_parser = subparsers.add_parser(
        "publish",
        parents=[global_parent],
        help="Build, sign, and write bundle",
        description="Publish a manuscript into an atomic PIP-1 bundle.",
    )
    pub_parser.add_argument("manuscript", help="Path to manuscript file")
    pub_parser.add_argument("--title", help="Manuscript title")
    pub_parser.add_argument(
        "--title-from-heading",
        action="store_true",
        help="Extract title from first # heading",
    )
    pub_parser.add_argument("--license", help="SPDX expression or LicenseRef-...")
    pub_parser.add_argument("--markup", choices=["md", "tex", "txt"], help="Markup syntax")
    pub_parser.add_argument("--lang", default="und", help="BCP 47 language tag (default: und)")
    pub_parser.add_argument(
        "--key", action="append", default=[], help="Signing key file (repeatable)"
    )
    pub_parser.add_argument("--unsigned", action="store_true", help="Publish without signatures")
    pub_parser.add_argument(
        "--author", action="append", default=[], help="Declare author key ID (repeatable)"
    )
    pub_parser.add_argument(
        "--asset", action="append", default=[], help="Attach asset file (repeatable)"
    )
    pub_parser.add_argument(
        "--asset-name", action="append", default=[], help="PATH=NAME override (repeatable)"
    )
    pub_parser.add_argument(
        "--asset-media", action="append", default=[], help="NAME=TYPE override (repeatable)"
    )
    pub_parser.add_argument(
        "--cite", action="append", default=[], help="Add citation PID (repeatable)"
    )
    pub_parser.add_argument(
        "--derivative",
        action="append",
        default=[],
        help="REL:PID relationship (repeatable)",
    )
    pub_parser.add_argument("--beacon", help="SRC:ROUND:HEX randomness beacon")
    pub_parser.add_argument("--out-dir", default=".", help="Target directory (default: .)")
    pub_parser.add_argument("--dry-run", action="store_true", help="Calculate IDs without writing")
    pub_parser.add_argument("--passphrase-file", help="Passphrase file for encrypted keys")

    # 6. sign
    sign_parser = subparsers.add_parser(
        "sign",
        parents=[global_parent],
        help="Add signature envelope to bundle",
        description="Add a signature envelope to an existing bundle.",
    )
    sign_parser.add_argument("bundle", help="Path to bundle directory")
    sign_parser.add_argument("--key", required=True, help="Signing key file path")
    sign_parser.add_argument("--role", default="author", help="Role (default: author)")
    sign_parser.add_argument("--passphrase-file", help="Passphrase file for key")

    # 7. verify
    ver_parser = subparsers.add_parser(
        "verify",
        parents=[global_parent],
        help="Verify bundle integrity, attribution, and history",
        description="Execute checks V1 through V8 on one or more bundles.",
    )
    ver_parser.add_argument("bundle", nargs="+", help="Bundle directory paths")
    ver_parser.add_argument("--parents", help="Directory containing parent bundles")
    ver_parser.add_argument(
        "--require-attributed", action="store_true", help="Require class >= Attributed"
    )
    ver_parser.add_argument(
        "--require-dual-family",
        action="store_true",
        help="Require Dual-family attribution",
    )
    ver_parser.add_argument(
        "--require-parents", action="store_true", help="Require parents to be available"
    )
    ver_parser.add_argument(
        "--warnings-as-errors", action="store_true", help="Treat warnings as failures"
    )
    ver_parser.add_argument("--max-text-bytes", type=int, help="Override text size limit")
    ver_parser.add_argument("--max-asset-bytes", type=int, help="Override asset size limit")

    # 8. inspect
    insp_parser = subparsers.add_parser(
        "inspect",
        parents=[global_parent],
        help="Inspect bundle manifest fields",
        description="Parse and display manifest fields without verifying.",
    )
    insp_parser.add_argument("target", help="Bundle directory or manifest.pip path")

    # 9. selftest
    subparsers.add_parser(
        "selftest",
        parents=[global_parent],
        help="Run self-tests on packaged vectors and backends",
        description="Run packaged Yellow Paper vectors, backend checks, Unicode guard and canary.",
    )

    # 10. explain
    explain_parser = subparsers.add_parser(
        "explain",
        parents=[global_parent],
        help="Explain error codes and rejections",
        description=(
            "Explain any error code from specs.md: meaning, usual cause, "
            "what to do, and Yellow Paper section."
        ),
    )
    explain_parser.add_argument(
        "code", nargs="?", help="Error code to explain (e.g. TEXT_MISMATCH)"
    )
    explain_parser.add_argument(
        "--list", action="store_true", dest="list_codes", help="List all known error codes"
    )

    # 11. version
    subparsers.add_parser(
        "version",
        parents=[global_parent],
        help="Print version and environment information",
        description="Print tool, Yellow Paper, Unicode, backend, Python, and platform versions.",
    )

    return parser
