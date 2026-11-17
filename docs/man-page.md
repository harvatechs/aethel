# AETHEL(1) — General Commands Manual

## NAME
`aethel` — reference CLI for the Permanent Ink Protocol (PIP-1)

## SYNOPSIS
```text
aethel [--json] [--ascii] [-v] <command> [arguments...]
aethel --help
aethel --version
```

## DESCRIPTION
`aethel` is the reference implementation of the Permanent Ink Protocol profile **pip-1** (PIP-YP-1 v1.0.0-rc.3). It gives a piece of writing a name made from the writing itself, signs it with post-quantum digital signatures, and verifies bundles offline from the files alone.

The tool operates completely offline without network sockets, telemetry, accounts, or clocks.

## GLOBAL OPTIONS
- `--json`: Emit machine-readable JSON matching defined schemas (`aethel.<command>/1`).
- `--ascii`: Restrict terminal output to 7-bit ASCII characters (no Unicode box-drawing or bullet characters).
- `-v, --verbose`: Enable verbose reporting and detailed verification check outputs.
- `--no-color`: Disable ANSI color escape codes (also respected via the `NO_COLOR` environment variable).

## COMMANDS

### `aethel canon`
```text
aethel canon <file> [--check] [--report] [-o <out_file>]
```
Normalize UTF-8 Markdown or plain text to Canonical Text Form (CTF-1) using Unicode 18.0.0 NFC normalization, LF line endings, and byte-order mark stripping. Returns exit code 0 if canonical, 1 if non-canonical (under `--check`), or 3 on invalid UTF-8.

### `aethel id`
```text
aethel id <file> [--kind text|asset] [--json] [-v]
```
Compute the content-addressed PIP identifier for a text (`pip1:t:...`) or binary asset (`pip1:a:...`).

### `aethel keygen`
```text
aethel keygen [--alg ml-dsa-87|ml-dsa-65|slh-dsa-sha2-256s|slh-dsa-shake-256s] --out <key.aek> [--passphrase]
```
Generate an AKF-1 key file. Protected keys are encrypted using Argon2id key derivation and AES-256-GCM.

### `aethel publish`
```text
aethel publish <manuscript> --title <title> --license <spdx> [--lang <code>] [--asset <file>...] [--key <key.aek>...] [--unsigned] --out-dir <dir>
```
Package a manuscript and assets into a signed PIP-1 bundle. The bundle is written atomically only after passing self-verification.

### `aethel sign`
```text
aethel sign <bundle> --key <key.aek> [--out <name.sig>]
```
Generate and attach a detached SGE-1 signature envelope to an existing bundle.

### `aethel verify`
```text
aethel verify <bundle...> [--parents <dir>] [--json] [--ascii] [-v]
```
Verify the integrity, attribution, history, and time evidence of one or more bundles. Checks V1 through V8 are evaluated independently.

### `aethel inspect`
```text
aethel inspect <bundle> [--json]
```
Inspect manifest metadata, declared authors, assets, and citations without executing full cryptographic checks.

### `aethel revise`
```text
aethel revise <parent_bundle> <manuscript> [--title <title>] [--key <key.aek>...] --out-dir <dir>
```
Publish a revised edition linked to prior manifest parent identifiers.

### `aethel cite`
```text
aethel cite make <bundle> [--chunk <n>] [--char <n>]
aethel cite check <bundle> <uri>
aethel cite show <bundle> <uri>
```
Generate, validate, and resolve canonical citation locators.

### `aethel proof`
```text
aethel proof make <bundle> <chunk_index> --out <proof.tfp>
aethel proof verify <bundle> <proof.tfp>
```
Generate and verify Merkle audit paths (TFP-1) proving inclusion of a 4,096-byte chunk.

### `aethel attest`
```text
aethel attest add <bundle> <attestation.att>
```
Attach an external attestation envelope (ATT-1) to a bundle.

### `aethel selftest`
```text
aethel selftest [--json]
```
Execute 13 built-in offline conformance checks against embedded vectors, validating Unicode tables, CTF-1, manifests, and crypto backends.

### `aethel explain`
```text
aethel explain <code> [--list] [--json]
```
Look up error codes from the registry and print explanations and remediation guidance.

### `aethel version`
```text
aethel version [--json]
```
Display detailed version, Unicode data version, and registered backend information.

## EXIT STATUS
- `0`: Success (all requested checks or operations passed).
- `1`: Failure (integrity failure, non-canonical text under `--check`, or validation failure).
- `2`: Invocation error (missing arguments, unknown flag, unknown command).
- `3`: Input data error (invalid UTF-8, syntax error in manifest or envelope).
- `4`: Key or cryptographic error (corrupt keyfile, bad passphrase, unknown algorithm).
- `5`: File system error (file not found, permission denied, case collision).
- `6`: Inconclusive verification (safety limit exceeded, missing required parent).

## CONFORMANCE
Conforms to Permanent Ink Protocol Profile **pip-1** (Yellow Paper PIP-YP-1 v1.0.0-rc.3).

## BUGS AND ISSUES
Report issues at https://github.com/OWNER/aethel-codex/issues
