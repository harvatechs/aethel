# cli-spec.md — The `aethel` Command Line

The CLI is a PT2 contract (`precision-scale-index.md`). Nothing may be invented that is not here. Priorities: **P0** ships in the MVP, **P1** follows in WP-12, **P2** is parked.

## 1. Global behaviour

- Command `aethel` (also `python -m aethel_codex`). Subcommands, built on `argparse`. Global flags are accepted before or after the subcommand.
- **stdout carries results. stderr carries diagnostics, warnings and progress.** With `--json`, stdout holds exactly one JSON document (JSON Lines when several bundles are verified) and nothing else.
- `FILE` of `-` means standard input (binary) for `canon` and `id`.
- No prompts except a passphrase on a TTY. No network. No configuration files. The only environment variable honoured is `NO_COLOR`.
- Colour only when the stream is a TTY, `NO_COLOR` is unset and `TERM` is not `dumb`. Meaning never depends on colour alone.
- Untrusted text (titles, licences, asset names, error details) is sanitised before it reaches a terminal: C0/C1 controls, bidirectional controls and tag characters print as `\u{202e}`. JSON uses ordinary escaping.
- `aethel` with no subcommand prints usage to stderr and exits 2. Every subcommand has `--help` with at least one worked example.

| Global flag | Meaning |
|---|---|
| `--json` | Machine output (schemas in §4) |
| `-q`, `--quiet` | Suppress non-error stderr |
| `-v`, `--verbose` | Add detail (chunk counts, per-item results) |
| `--no-color` | Disable colour |
| `--ascii` | Plain ASCII output (no `·`, `…`, box drawing) |
| `--debug` | Show tracebacks and library versions on error |
| `--version` | `aethel 0.1.0 (PIP-1 profile pip-1, Yellow Paper 1.0.0-rc.3)` |

## 2. Exit codes (contract)

| Code | Name | When |
|---|---|---|
| 0 | OK | Success. For `verify`: integrity PASS and every `--require-*` satisfied |
| 1 | VERIFY_FAILED | `verify`: integrity FAIL, or a `--require-*` gate unmet. `canon --check`: not already canonical |
| 2 | USAGE | Bad command line |
| 3 | INVALID_INPUT | Input rejected by a grammar: CTF-1, manifest, citation, PID, envelope; limit exceeded while producing |
| 4 | CRYPTO | Key file invalid, wrong passphrase, insecure permissions, backend error |
| 5 | IO | File missing, unreadable, already exists, no permission, disk error |
| 6 | INCONCLUSIVE | `verify` stopped by a limit; nothing failed but something was not checked |
| 70 | INTERNAL | Bug, failed self-verification, Unicode data mismatch |
| 130 | INTERRUPTED | Ctrl-C |

For several bundles, the exit code is the worst: 1 beats 6 beats 0.

## 3. Commands

### `aethel canon FILE` — P0
Apply CTF-1 and write the canonical bytes to stdout, or to `-o OUT`.
`--check` writes nothing; exit 0 if the input is already canonical, 1 if canonicalisation would change it, 3 if it is rejected. `--report` explains the changes on stderr. `--json` prints the report only (use `-o` to also save the bytes).
Rejections name the byte offset or code point, line and column, and the Yellow Paper section. They never guess an encoding.

```
$ aethel canon essay.md --report -o essay.canonical.md
Canonical form: 2,214 bytes (input 2,231).
  removed the byte-order mark
  converted 14 CR LF line endings to LF
  added a final line feed
```

### `aethel id FILE` — P0
Print the identifier. Text files (`.md`, `.markdown`, `.tex`, `.txt`) are canonicalised first and print `pip1:t:…`; other files are raw assets and print `pip1:a:…`. `--kind text|asset` overrides (required for stdin). `-v` adds length and chunk count.

### `aethel keygen` — P0
Create a signing key. `--alg ml-dsa-87` (default) `| ml-dsa-65 | slh-dsa-sha2-256s | slh-dsa-shake-256s`. `--dual` creates ML-DSA-87 and SLH-DSA-SHA2-256s together. `--out PATH` (single key) or `--out-dir DIR` (default names `<first 16 hex of key id>.aek`). The key file is encrypted unless `--no-passphrase` is given. The passphrase is read twice from the TTY, or from `--passphrase-file`. With no TTY and neither option, exit 2. Existing files are never overwritten.
Prints the key id on stdout; on stderr a plain reminder that the file holds the only copy of the secret and should be backed up offline.

### `aethel key info KEYFILE` — P0
Print algorithm, key id, protection state, and with `--public` the Base64 public key. Never prints or asks for the secret.

### `aethel publish MANUSCRIPT` — P0
Build, sign and write a bundle.

| Flag | Meaning |
|---|---|
| `--title T` (required), `--title-from-heading` | Title; or use the first `# ` heading of a Markdown file (printed so you can check it) |
| `--license L` (required) | SPDX expression or `LicenseRef-…` |
| `--markup md\|tex\|txt` | Default from the extension; otherwise required |
| `--lang TAG` | Default `und`. The tool never guesses a language |
| `--key KEYFILE` (repeatable) / `--unsigned` | Sign as `author` and declare the key as an author; or publish without a signature (reports Unattributed). One of them is required |
| `--author KEYID` (repeatable) | Declare a co-author key that will sign later (reports Partially attributed until it does) |
| `--asset PATH` (repeatable), `--asset-name PATH=NAME`, `--asset-media NAME=TYPE` | Attach files. Name defaults to the file name and must satisfy the asset-name grammar; the media type comes from a fixed built-in table, else `application/octet-stream`. **Never** `mimetypes` (system-dependent) |
| `--cite PID` (repeatable) | `pip1:m:`, `pip1:t:` or `pip1:a:` identifiers |
| `--derivative REL:PID` (repeatable) | `translation`, `adaptation`, `anthology` or `commentary` plus a manifest id |
| `--beacon SRC:ROUND:HEX` | Carried and reported as unchecked |
| `--out-dir DIR` | Default `.`; the bundle is `DIR/<manifest-hex>/` |
| `--dry-run` | Print identifiers and the manifest; write and sign nothing |
| `--passphrase-file PATH` | Used for every key given |

Order of work: canonicalise → hash text and assets → build and strictly re-parse the manifest → sign with each key → verify each signature → write atomically → run the full verifier on the result. Any failure leaves nothing behind. SLH-DSA signing takes seconds; one calm line on stderr says so.

```
$ aethel publish essay.md --title "On Names" --license CC-BY-4.0 --lang en --key ./2b27c5d44b407af5.aek
Passphrase: ********
Published   pip1:m:e1bbe279…cd30d
  text      pip1:t:8186c5e1…96ba   48 bytes, 1 chunk
  signed    author · ml-dsa-87 · pip1:k:2b27c5d4…130b
  written   ./e1bbe279…cd30d/
Integrity PASS · Attribution Attributed (1 of 1)
```

### `aethel revise PARENT_BUNDLE MANUSCRIPT` — P1
Same flags as `publish`. Inherits only `title`, `license`, `markup`, `lang` and `author` declarations from the parent; assets, cites and derivatives are restated (`--keep-assets`, `--keep-cites` copy them). Sets `work` and `parent` per `specs.md` §7.

### `aethel sign BUNDLE --key KEYFILE [--role ROLE]` — P0
Add a signature in `author` (default), `contributor`, `translator`, `endorser` or `0xHH` role. Refuses if integrity (V1–V3) fails. Refuses to overwrite an existing signature of the same key and role (exit 5). Self-verifies. If the key is not a declared author and the role is `author`, warn that it will be reported separately and will not count toward attribution.

### `aethel verify BUNDLE...` — P0
Run V1–V8 and print four separate statements. `--parents DIR` supplies parent bundles. Gates (exit code only): `--require-attributed`, `--require-dual-family`, `--require-parents`, `--warnings-as-errors`. Limits: `--max-text-bytes`, `--max-asset-bytes`.

```
$ aethel verify ./e1bbe279…cd30d
pip1:m:e1bbe279…cd30d

Integrity    PASS         manifest, text and 1 asset match their identifiers
Attribution  Attributed (1 of 1)
               pip1:k:2b27c5d4…130b   signed   ml-dsa-87
History      not checked  genesis manifest, no parents
Time         none         no beacon and no attestations

Checks  V1 PASS · V2 PASS · V3 PASS · V4 PASS · V5 SKIPPED · V6 PASS · V7 PASS · V8 SKIPPED
A valid signature shows that the holder of a key approved this manifest. It does not show who that person is.
```

### `aethel inspect TARGET` — P0
Parse a bundle directory or a `manifest.pip` and print its fields. The first line says: "inspect parses a manifest. It does not verify anything."

### `aethel cite make|check|show` — P1
`make PID [--range S-E]` prints a citation URI. `check URI (--bundle DIR | --file FILE)` validates the locator on the cited canonical text. `show URI --bundle DIR` prints the cited bytes (sanitised when stdout is a TTY).

### `aethel proof make|verify` — P1
`make BUNDLE --chunk N [--asset NAME] [-o FILE]` writes a TFP-1 proof. `verify FILE` checks it with the `specs.md` §5 procedure.

### `aethel attest add BUNDLE --kind KIND (--proof-b64 STR | --proof-file F)` — P1
Stores an ATT-1 envelope. Verification reports it as present and unverified.

### `aethel selftest` — P0
Runs the packaged Yellow Paper vectors, the backend checks (ML-DSA-87 A.2 signature, ML-DSA-65 and SLH-DSA vectors), the Unicode guard and canary. Prints a table; exit 0 only if everything passes. Works offline from an installed wheel.

### `aethel explain CODE` — P0
Explain any code from `specs.md` §14 (`TEXT_MISMATCH`, `E_BAD_LINES`, …): meaning, usual cause, what to do, Yellow Paper section.

### `aethel version` — P0
Tool version; Yellow Paper version; Unicode data version; backend names and versions; Python; platform. `--json` is a contract.

**P2 (parked):** `lint` (front matter, trailing whitespace, bidirectional controls, tag characters, confusables), shell completion, man pages, parallel `verify --jobs`, tar export.

## 4. JSON output

Schemas are JSON Schema 2020-12 files in `src/aethel_codex/schemas/` (package data). Tests validate real output against them. Key order is fixed as shown. Every document starts with `"schema"` and, for tool output, `"tool"`.

```json
{
  "schema": "aethel.verify/1",
  "tool": {"name": "aethel", "version": "0.1.0", "profile": "pip-1", "yellow_paper": "1.0.0-rc.3"},
  "bundle": {"path": "./e1bbe279…cd30d", "manifest_id": "pip1:m:e1bbe279…", "work_id": "pip1:m:e1bbe279…"},
  "integrity": "PASS",
  "attribution": {
    "class": "Attributed", "signed": 1, "declared": 1, "keccak_independent": false,
    "keys": [{"key": "pip1:k:2b27c5d4…", "status": "signed", "alg": "ml-dsa-87"}],
    "other_signatures": []
  },
  "history": {"status": "SKIPPED", "reason": "NO_PARENTS"},
  "time": {"status": "SKIPPED", "reason": "NO_TIME_EVIDENCE", "items": []},
  "checks": [
    {"id": "V1", "status": "PASS", "code": null, "detail": null, "items": []},
    {"id": "V3", "status": "PASS", "code": null, "detail": null,
     "items": [{"subject": "figure1.svg", "status": "PASS", "code": null, "detail": null}]}
  ],
  "warnings": [],
  "notes": ["PIP-1 cannot say who holds a signing key."]
}
```

(The real output carries full 64-hex identifiers; ellipses above are for reading.) `integrity` is `PASS`, `FAIL` or `INCONCLUSIVE`. `class` is one of the four names in `specs.md` §9. Statuses are `PASS`, `WARN`, `FAIL`, `SKIPPED`. Other schemas: `aethel.canon/1`, `aethel.id/1`, `aethel.keygen/1`, `aethel.publish/1`, `aethel.sign/1`, `aethel.inspect/1`, `aethel.selftest/1`, `aethel.version/1`, `aethel.error/1`. On error with `--json`, stdout holds `{"schema":"aethel.error/1","code":"E_BAD_LINES","message":"…","exit":3,"yp":"§7.6"}`.

Several bundles with `--json` produce JSON Lines: one compact object per line, no wrapper, in argument order.

## 5. Message style

Calm, exact, no emoji, no exclamation marks. A message says what happened, why it matters, what to do, and cites the Yellow Paper section. Examples:

```
error: this file is not valid UTF-8 (byte 0xC0 at offset 4, line 1).
       CTF-1 never guesses an encoding (Yellow Paper §4.2, step 2).
       Convert the file to UTF-8, then try again.

error: line 3 of manifest.pip is out of order: "license" must come before "text" (PMF-1, §7.2).
       code E_FIELD_ORDER · run `aethel explain E_FIELD_ORDER` for more.

error: refusing to sign: the bundle's integrity check failed (TEXT_MISMATCH).
       Signing a bundle that does not match its own manifest would approve nothing real.

error: key file ./2b27c5d44b407af5.aek is readable by other users (mode 0644). Run: chmod 600 ./2b27c5d44b407af5.aek
```

Approved phrases and banned claims: `guidelines.md` §6 and `what-not-to-do.md` §4.
