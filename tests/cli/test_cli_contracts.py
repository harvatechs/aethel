"""CLI contract and exit code tests (WP-10, cli-spec.md §1, §2, §3, §4)."""

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest

from aethel_codex.cli import main
from aethel_codex.constants import TOOL_NAME, TOOL_VERSION, YELLOW_PAPER_VERSION

SCHEMAS_DIR = Path(__file__).parents[2] / "src" / "aethel_codex" / "schemas"
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


def _load_schema(name: str) -> dict[str, Any]:
    schema_path = SCHEMAS_DIR / f"{name}.json"
    data: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    return data


def _make_capture_stream(initial_bytes: bytes = b"") -> tuple[io.TextIOWrapper, io.BytesIO]:
    buf = io.BytesIO(initial_bytes)
    wrapper = io.TextIOWrapper(buf, encoding="utf-8", write_through=True)
    return wrapper, buf


def _run_cli(
    argv: list[str],
    stdin_data: bytes | str | None = None,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> tuple[int, str, str]:
    """Run CLI main in-process with captured stdout and stderr."""
    stdout_wrapper, stdout_buf = _make_capture_stream()
    stderr_wrapper, stderr_buf = _make_capture_stream()

    if stdin_data is not None:
        raw_bytes = stdin_data.encode("utf-8") if isinstance(stdin_data, str) else stdin_data
    else:
        raw_bytes = b""
    stdin_wrapper, _ = _make_capture_stream(raw_bytes)

    if monkeypatch:
        monkeypatch.setattr(sys, "stdout", stdout_wrapper)
        monkeypatch.setattr(sys, "stderr", stderr_wrapper)
        monkeypatch.setattr(sys, "stdin", stdin_wrapper)
        exit_code = main(argv)
    else:
        old_stdout, old_stderr, old_stdin = sys.stdout, sys.stderr, sys.stdin
        try:
            sys.stdout = stdout_wrapper
            sys.stderr = stderr_wrapper
            sys.stdin = stdin_wrapper
            exit_code = main(argv)
        finally:
            sys.stdout, sys.stderr, sys.stdin = old_stdout, old_stderr, old_stdin

    out = stdout_buf.getvalue().decode("utf-8", errors="replace")
    err = stderr_buf.getvalue().decode("utf-8", errors="replace")

    return exit_code, out, err


# -----------------------------------------------------------------------------
# 1. Version, help, usage, and crypto module check
# -----------------------------------------------------------------------------


def test_cli_no_args_shows_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_code, out, err = _run_cli([], monkeypatch=monkeypatch)
    assert exit_code == 2
    assert "usage:" in err
    assert out == ""


def test_cli_unknown_command(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_code, _out, err = _run_cli(["unknown-command"], monkeypatch=monkeypatch)
    assert exit_code == 2
    assert "usage:" in err or "Unknown command" in err


def test_cli_version_subprocess() -> None:
    """Verify aethel --version prints expected string and does not import crypto."""
    script = (
        "import sys\n"
        "from aethel_codex.cli import main\n"
        "code = main(['--version'])\n"
        "crypto_loaded = 'cryptography' in sys.modules\n"
        "pqcrypto_loaded = 'pqcrypto' in sys.modules\n"
        "print(f'EXIT:{code}')\n"
        "print(f'CRYPTO:{crypto_loaded}')\n"
        "print(f'PQCRYPTO:{pqcrypto_loaded}')\n"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"{TOOL_NAME} {TOOL_VERSION}" in result.stdout
    assert f"Yellow Paper {YELLOW_PAPER_VERSION}" in result.stdout
    assert "EXIT:0" in result.stdout
    assert "CRYPTO:False" in result.stdout
    assert "PQCRYPTO:False" in result.stdout


def test_cli_help_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_code, out, _err = _run_cli(["--help"], monkeypatch=monkeypatch)
    assert exit_code == 0
    assert "Reference CLI for Permanent Ink Protocol (PIP-1)" in out
    assert "canon" in out
    assert "publish" in out
    assert "verify" in out


# -----------------------------------------------------------------------------
# 2. canon command tests
# -----------------------------------------------------------------------------


def test_cli_canon_check_canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    canon_file = tmp_path / "valid.txt"
    canon_file.write_bytes(b"Clean text line.\n")

    exit_code, out, _err = _run_cli(["canon", str(canon_file), "--check"], monkeypatch=monkeypatch)
    assert exit_code == 0
    assert out == ""


def test_cli_canon_check_non_canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    crlf_file = tmp_path / "crlf.txt"
    crlf_file.write_bytes(b"Line with CRLF\r\n")

    exit_code, out, _err = _run_cli(["canon", str(crlf_file), "--check"], monkeypatch=monkeypatch)
    assert exit_code == 1
    assert out == ""


def test_cli_canon_report_and_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_file = tmp_path / "in.txt"
    out_file = tmp_path / "out.txt"
    in_file.write_bytes(b"\xef\xbb\xbfHello world\r\n")

    exit_code, _out, err = _run_cli(
        ["canon", str(in_file), "-o", str(out_file), "--report"],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    assert "removed the byte-order mark" in err
    assert "converted 1 CR LF" in err
    assert out_file.read_bytes() == b"Hello world\n"


def test_cli_canon_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_file = tmp_path / "in.txt"
    in_file.write_bytes(b"Simple text\n")

    exit_code, out, _err = _run_cli(["canon", str(in_file), "--json"], monkeypatch=monkeypatch)
    assert exit_code == 0
    doc = json.loads(out)
    schema = _load_schema("canon")
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["schema"] == "aethel.canon/1"
    assert doc["canonical"] is True


def test_cli_canon_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_input = b"\xef\xbb\xbfLine with CRLF\r\n"
    exit_code, out, _ = _run_cli(["canon", "-"], stdin_data=raw_input, monkeypatch=monkeypatch)
    assert exit_code == 0
    assert out == "Line with CRLF\n"


def test_cli_canon_invalid_utf8_exit_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_file = tmp_path / "invalid.bin"
    in_file.write_bytes(b"\xff\xfe\x00")

    exit_code, _out, err = _run_cli(["canon", str(in_file)], monkeypatch=monkeypatch)
    assert exit_code == 3
    assert "E_INVALID_UTF8" in err


# -----------------------------------------------------------------------------
# 3. id command tests
# -----------------------------------------------------------------------------


def test_cli_id_text_and_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    txt_file = tmp_path / "doc.md"
    txt_file.write_bytes(b"Hello world\n")

    bin_file = tmp_path / "image.png"
    bin_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    code_t, out_t, _ = _run_cli(["id", str(txt_file)], monkeypatch=monkeypatch)
    assert code_t == 0
    assert out_t.strip().startswith("pip1:t:")

    code_a, out_a, _ = _run_cli(["id", str(bin_file)], monkeypatch=monkeypatch)
    assert code_a == 0
    assert out_a.strip().startswith("pip1:a:")


def test_cli_id_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    txt_file = tmp_path / "doc.md"
    txt_file.write_bytes(b"Hello world\n")

    exit_code, out, _ = _run_cli(["id", str(txt_file), "--json", "-v"], monkeypatch=monkeypatch)
    assert exit_code == 0
    doc = json.loads(out)
    schema = _load_schema("id")
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["schema"] == "aethel.id/1"
    assert doc["kind"] == "text"
    assert doc["chunks"] == 1


def test_cli_id_stdin_and_missing_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stdin with --kind text
    exit_code, out, _ = _run_cli(
        ["id", "-", "--kind", "text"], stdin_data=b"Hello text\n", monkeypatch=monkeypatch
    )
    assert exit_code == 0
    assert out.strip().startswith("pip1:t:")

    # Stdin without --kind should fail with E_BAD_VALUE (exit 3)
    code_err, _, err = _run_cli(["id", "-"], stdin_data=b"Hello\n", monkeypatch=monkeypatch)
    assert code_err == 3
    assert "E_BAD_VALUE" in err


def test_cli_no_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that CLI runs without attempting network calls."""
    import socket

    def _forbidden_connect(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Network connection forbidden by PIP-1 rules")

    monkeypatch.setattr(socket.socket, "connect", _forbidden_connect)

    ms = tmp_path / "net_test.md"
    ms.write_bytes(b"# Offline\n\nContent.\n")
    exit_code, _out, _err = _run_cli(
        [
            "publish",
            str(ms),
            "--title-from-heading",
            "--license",
            "MIT",
            "--unsigned",
            "--out-dir",
            str(tmp_path / "bundle"),
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0


# -----------------------------------------------------------------------------
# 4. keygen and key info command tests
# -----------------------------------------------------------------------------


def test_cli_keygen_unencrypted_and_key_info(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_key = tmp_path / "test.aek"
    exit_code, out, _err = _run_cli(
        ["keygen", "--out", str(out_key), "--no-passphrase"],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    k_id = out.strip()
    assert k_id.startswith("pip1:k:")
    assert out_key.exists()

    # Inspect with key info
    info_code, info_out, _ = _run_cli(
        ["key", "info", str(out_key), "--public"],
        monkeypatch=monkeypatch,
    )
    assert info_code == 0
    assert "Algorithm:   ml-dsa-87" in info_out
    assert f"Key ID:      {k_id}" in info_out
    assert "Protection:  none" in info_out
    assert "Public key:  " in info_out


def test_cli_keygen_encrypted_via_passphrase_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pw_file = tmp_path / "pass.txt"
    pw_file.write_bytes(b"correct horse battery staple\n")
    out_key = tmp_path / "enc.aek"

    exit_code, _out, _ = _run_cli(
        ["keygen", "--out", str(out_key), "--passphrase-file", str(pw_file)],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    assert out_key.exists()

    # Check key info shows protection
    info_code, info_out, _ = _run_cli(["key", "info", str(out_key)], monkeypatch=monkeypatch)
    assert info_code == 0
    assert "Protection:  scrypt-chacha20poly1305" in info_out


def test_cli_keygen_dual_and_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "keys"
    exit_code, out, _ = _run_cli(
        ["keygen", "--dual", "--no-passphrase", "--out-dir", str(out_dir), "--json"],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    doc = json.loads(out)
    schema = _load_schema("keygen")
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["schema"] == "aethel.keygen/1"
    assert len(doc["keys"]) == 2
    algs = {k["alg"] for k in doc["keys"]}
    assert algs == {"ml-dsa-87", "slh-dsa-sha2-256s"}


def test_cli_keygen_missing_tty_and_no_passphrase_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_key = tmp_path / "missing.aek"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    exit_code, _out, err = _run_cli(["keygen", "--out", str(out_key)], monkeypatch=monkeypatch)
    assert exit_code == 2
    assert "Passphrase required" in err


# -----------------------------------------------------------------------------
# 5. publish and inspect command tests
# -----------------------------------------------------------------------------


def test_cli_publish_unsigned_and_inspect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ms = tmp_path / "essay.md"
    ms.write_bytes(b"# A Title\n\nBody of manuscript.\n")
    out_dir = tmp_path / "bundles"

    exit_code, out, _err = _run_cli(
        [
            "publish",
            str(ms),
            "--title-from-heading",
            "--license",
            "CC-BY-4.0",
            "--unsigned",
            "--out-dir",
            str(out_dir),
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    assert "Published   pip1:m:" in out
    assert "Integrity PASS" in out
    assert "Attribution Unattributed" in out

    # Find bundle dir
    bundle_dirs = list(out_dir.glob("*"))
    assert len(bundle_dirs) == 1
    bundle_dir = bundle_dirs[0]

    # Inspect command
    insp_code, insp_out, _ = _run_cli(["inspect", str(bundle_dir)], monkeypatch=monkeypatch)
    assert insp_code == 0
    assert "inspect parses a manifest. It does not verify anything." in insp_out
    assert "Title:        A Title" in insp_out
    assert "License:      CC-BY-4.0" in insp_out

    # Inspect with --json
    insp_j_code, insp_j_out, _ = _run_cli(
        ["inspect", str(bundle_dir), "--json"], monkeypatch=monkeypatch
    )
    assert insp_j_code == 0
    insp_doc = json.loads(insp_j_out)
    schema = _load_schema("inspect")
    jsonschema.validate(instance=insp_doc, schema=schema)
    assert insp_doc["schema"] == "aethel.inspect/1"
    assert insp_doc["manifest"]["title"] == "A Title"


def test_cli_publish_signed_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ms = tmp_path / "doc.txt"
    ms.write_bytes(b"Simple test document.\n")
    key_file = tmp_path / "author.aek"
    _run_cli(
        ["keygen", "--out", str(key_file), "--no-passphrase"],
        monkeypatch=monkeypatch,
    )

    exit_code, out, _ = _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            "Signed Document",
            "--license",
            "MIT",
            "--key",
            str(key_file),
            "--out-dir",
            str(tmp_path / "out"),
            "--json",
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    doc = json.loads(out)
    schema = _load_schema("publish")
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["schema"] == "aethel.publish/1"
    assert doc["attribution"]["class"] == "Attributed"
    assert doc["attribution"]["signed"] == 1


def test_cli_publish_dry_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ms = tmp_path / "doc.md"
    ms.write_bytes(b"# Test\n")
    out_dir = tmp_path / "should_not_exist"

    exit_code, _out, _ = _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            "Dry Run",
            "--license",
            "MIT",
            "--unsigned",
            "--dry-run",
            "--out-dir",
            str(out_dir),
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    assert not out_dir.exists()


# -----------------------------------------------------------------------------
# 6. sign and verify command tests
# -----------------------------------------------------------------------------


def test_cli_sign_and_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ms = tmp_path / "doc.md"
    ms.write_bytes(b"Content for signing.\n")
    key_file = tmp_path / "signer.aek"
    _run_cli(["keygen", "--out", str(key_file), "--no-passphrase"], monkeypatch=monkeypatch)

    out_dir = tmp_path / "bundle_pub"
    _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            "Sign Test",
            "--license",
            "MIT",
            "--unsigned",
            "--out-dir",
            str(out_dir),
        ],
        monkeypatch=monkeypatch,
    )
    bundle_dir = next(out_dir.glob("*"))

    # Verify bundle before signing
    v_code0, v_out0, _ = _run_cli(["verify", str(bundle_dir)], monkeypatch=monkeypatch)
    assert v_code0 == 0
    assert "Attribution  Unattributed" in v_out0

    # Sign as contributor
    sign_code, sign_out, _ = _run_cli(
        [
            "sign",
            str(bundle_dir),
            "--key",
            str(key_file),
            "--role",
            "contributor",
            "--json",
        ],
        monkeypatch=monkeypatch,
    )
    assert sign_code == 0
    sign_doc = json.loads(sign_out)
    schema = _load_schema("sign")
    jsonschema.validate(instance=sign_doc, schema=schema)
    assert sign_doc["schema"] == "aethel.sign/1"
    assert sign_doc["role"] == "contributor"

    # Attempt duplicate signature -> exit 5
    dup_code, _, dup_err = _run_cli(
        ["sign", str(bundle_dir), "--key", str(key_file), "--role", "contributor"],
        monkeypatch=monkeypatch,
    )
    assert dup_code == 5
    assert "already exists" in dup_err

    # Verify after signing
    v_code1, v_out1, _ = _run_cli(["verify", str(bundle_dir), "--json"], monkeypatch=monkeypatch)
    assert v_code1 == 0
    v_doc = json.loads(v_out1)
    v_schema = _load_schema("verify")
    jsonschema.validate(instance=v_doc, schema=v_schema)
    assert v_doc["schema"] == "aethel.verify/1"
    assert len(v_doc["attribution"]["other_signatures"]) == 1


def test_cli_sign_refuses_on_tampered_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ms = tmp_path / "doc.md"
    ms.write_bytes(b"Good text.\n")
    out_dir = tmp_path / "bundle"
    _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            "Tamper Test",
            "--license",
            "MIT",
            "--unsigned",
            "--out-dir",
            str(out_dir),
        ],
        monkeypatch=monkeypatch,
    )
    bundle_dir = next(out_dir.glob("*"))

    # Tamper with text file
    text_file = bundle_dir / "text.md"
    text_file.write_bytes(b"Tampered bad text.\n")

    key_file = tmp_path / "signer.aek"
    _run_cli(["keygen", "--out", str(key_file), "--no-passphrase"], monkeypatch=monkeypatch)

    sign_code, _, sign_err = _run_cli(
        ["sign", str(bundle_dir), "--key", str(key_file)], monkeypatch=monkeypatch
    )
    assert sign_code == 1
    assert "refusing to sign" in sign_err


def _get_fixture_bundle(scenario: str) -> Path:
    scenario_dir = FIXTURES_DIR / scenario
    data: dict[str, Any] = json.loads((scenario_dir / "expected.json").read_text(encoding="utf-8"))
    manifest_hex = str(data["manifest_id"]).split(":")[-1]
    return scenario_dir / manifest_hex


def test_cli_verify_golden_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify golden fixtures 01 through 05 via CLI."""
    parent_bundle = _get_fixture_bundle("genesis-attributed")
    fixtures = [
        ("genesis-unsigned", []),
        ("genesis-attributed", []),
        ("dual-family", []),
        ("partial-attribution", []),
        ("revision", ["--parents", str(parent_bundle)]),
    ]
    for name, extra_args in fixtures:
        bundle_path = _get_fixture_bundle(name)
        assert bundle_path.exists(), f"Fixture bundle {name} must exist"
        exit_code, out, _ = _run_cli(
            ["verify", str(bundle_path), *extra_args, "--json"],
            monkeypatch=monkeypatch,
        )
        assert exit_code == 0
        doc = json.loads(out)
        schema = _load_schema("verify")
        jsonschema.validate(instance=doc, schema=schema)
        assert doc["integrity"] == "PASS"


def test_cli_verify_multiple_bundles_json_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    b1 = _get_fixture_bundle("genesis-unsigned")
    b2 = _get_fixture_bundle("genesis-attributed")
    assert b1.exists()
    assert b2.exists()

    exit_code, out, _ = _run_cli(["verify", str(b1), str(b2), "--json"], monkeypatch=monkeypatch)
    assert exit_code == 0
    lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
    assert len(lines) == 2
    for line in lines:
        doc = json.loads(line)
        schema = _load_schema("verify")
        jsonschema.validate(instance=doc, schema=schema)
        assert doc["integrity"] == "PASS"


def test_cli_verify_require_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    b1 = _get_fixture_bundle("genesis-unsigned")
    assert b1.exists()

    # genesis-unsigned has no signatures, so --require-attributed must exit 1
    code_req, _, _ = _run_cli(["verify", str(b1), "--require-attributed"], monkeypatch=monkeypatch)
    assert code_req == 1

    # genesis-attributed is ML-DSA-87 single family, so --require-dual-family must exit 1
    b2 = _get_fixture_bundle("genesis-attributed")
    assert b2.exists()
    code_dual, _, _ = _run_cli(
        ["verify", str(b2), "--require-dual-family"], monkeypatch=monkeypatch
    )
    assert code_dual == 1


def test_cli_verify_exit_code_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit code precedence: 1 beats 6 beats 0."""
    b1 = _get_fixture_bundle("genesis-unsigned")
    assert b1.exists()

    # genesis-unsigned with --require-attributed yields 1, normal yields 0
    # Combined must return 1
    exit_code, _, _ = _run_cli(
        ["verify", str(b1), str(b1), "--require-attributed"],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 1


# -----------------------------------------------------------------------------
# 7. Global flags, formatting, and terminal sanitization
# -----------------------------------------------------------------------------


def test_cli_ascii_and_no_color_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ms = tmp_path / "test.txt"
    ms.write_bytes(b"ASCII mode test.\n")
    exit_code, out, _ = _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            "ASCII Title",
            "--license",
            "MIT",
            "--unsigned",
            "--ascii",
            "--no-color",
            "--out-dir",
            str(tmp_path / "b"),
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    # In ASCII mode, '·' is replaced with '-' and '…' is replaced with '...'
    assert "·" not in out
    assert "…" not in out


def test_cli_terminal_sanitization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Untrusted text with bidi controls or C0/C1 must be escaped in terminal output."""
    ms = tmp_path / "evil.txt"
    ms.write_bytes(b"Untrusted text.\n")
    # Title containing bidi override U+202E and tag character U+E0001
    evil_title = "Secret\u202e\U000e0001Report"

    exit_code, _out, _ = _run_cli(
        [
            "publish",
            str(ms),
            "--title",
            evil_title,
            "--license",
            "MIT",
            "--unsigned",
            "--out-dir",
            str(tmp_path / "b"),
        ],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 0
    bundle_dir = next((tmp_path / "b").glob("*"))

    # Inspect human output
    insp_code, insp_out, _ = _run_cli(["inspect", str(bundle_dir)], monkeypatch=monkeypatch)
    assert insp_code == 0
    assert "\\u{202e}" in insp_out
    assert "\\u{0e0001}" in insp_out
    assert "\u202e" not in insp_out


def test_cli_error_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """All errors with --json must print valid aethel.error/1 schema."""
    exit_code, out, _ = _run_cli(
        ["canon", str(tmp_path / "nonexistent.txt"), "--json"],
        monkeypatch=monkeypatch,
    )
    assert exit_code == 5
    doc = json.loads(out)
    schema = _load_schema("error")
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["schema"] == "aethel.error/1"
    assert doc["exit"] == 5
    assert doc["code"] == "TEXT_MISSING"
