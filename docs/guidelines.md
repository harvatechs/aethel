# guidelines.md — Common Guidelines

Rules (`rules.md`) are binding; guidelines are the house style that keeps a large codebase calm. Deviate only with a reason in the pull request.

## 1. Python style

- Python ≥ 3.11. Format and lint with `ruff` (line length 100). Type everything; `mypy --strict`.
- Prefer frozen `dataclass`es, `Enum`s and `tuple`s over dicts and lists in the domain model. Immutable by default.
- Use `bytes` for protocol data and `str` only for text that is already decoded or is ASCII grammar. Never mix them implicitly.
- Standard library first. No clever one-liners in PT0 and PT1 code; prefer three plain lines.
- Functions do one thing, fit on a screen, and have complexity ≤ 10. Early returns for rejection.
- Docstring on every public function: one summary line, `YP §x.y`, parameters only if not obvious, **Raises** with registry codes. No restating the code.
- No `print` in library code. Output belongs to `cli/`.
- Third-party libraries without type stubs (`unicodedata2`, `pqcrypto`) are wrapped in one typed adapter module each so the untyped surface never leaks.

## 2. Naming

Use the paper's words: `canonical` (bytes after CTF-1), `text_id`, `asset_id`, `manifest_id`, `key_id`, `work_id`, `chunk`, `leaf`, `node`, `root`, `label`, `context`, `role`, `declared` (author keys in the manifest), `valid` (keys with verified author signatures). Avoid `hash` as a variable (it shadows a built-in) and `id` alone. Error codes are `UPPER_SNAKE` strings from the registry. Private helpers start with `_`. Modules are lower_snake singular nouns.

## 3. Structure of a module

Module docstring (what, which YP sections) → constants → types → public functions → private helpers. Imports sorted by `ruff`. Heavy imports (`cryptography`, `pqcrypto`) inside functions.

## 4. Test style

- File `test_<module>.py`; test names are sentences: `test_rejects_second_byte_order_mark`.
- Arrange the vector, act, assert. One idea per test. Parametrize over vector lists.
- Fixtures create files in `tmp_path`. Never write into the repository.
- Property tests state the invariant in the docstring.
- Mark requirement coverage: `@pytest.mark.req("UR-03")`.
- Golden help text is generated once, reviewed by a human, then frozen; it is the only snapshot allowed.

## 5. CLI output style

- A success is one to six lines. Show what was made, its identifier, and the verdict. Details behind `-v`.
- Identifiers print in full in `--json` and plain output; human tables may abbreviate as `pip1:t:8186c5e1…96ba` (first 8, last 4 hex digits). Never abbreviate in anything meant for copy-paste or scripts.
- Align columns with spaces, never tabs. Use `·` as a separator (ASCII `-` under `--ascii`).
- Errors: `error:` prefix, then what/why/what next, then the code line (`code E_BAD_LINES · run aethel explain E_BAD_LINES`).
- Warnings: `warning:` prefix, one line plus a hint.
- Never print a secret, a passphrase, or an unsanitised untrusted string.

## 6. Approved phrases (use these; they are all within Yellow Paper §2.3)

| Topic | Say |
|---|---|
| What it does | "Gives a piece of writing a name made from the writing itself." |
| Tamper evidence | "A change to the text, assets, metadata, citations or declared authors changes the manifest identifier." |
| Signature | "A valid signature shows that the holder of key `pip1:k:…` approved this exact manifest as author. PIP-1 cannot say who holds the key." |
| Time | "Time evidence bounds when these exact bytes existed. This tool does not produce time evidence." |
| Storage | "Tampering is detectable. This tool does not store or keep copies." |
| Quantum | "Signatures use ML-DSA (FIPS 204) and SLH-DSA (FIPS 205), standards designed to resist quantum computers." |
| Privacy | "PIP-1 provides no anonymity and no confidentiality." |
| Not known | "not checked" · "not shown" · "unverified" · "present, unchecked" |
| Beacons | "A beacon line is carried in the manifest. This tool does not check it." |

## 7. Git, commits, pull requests, versions

- Branch per work package: `wp-02-unicode-ctf1`. One WP per pull request, small commits inside it.
- Conventional Commits: `feat(ctf1): reject unassigned scalars (R-PROTO-08)`, `test(merkle): add T3 audit paths`, `docs(specs): clarify Q-02`, `fix(verify): …`, `build`, `ci`, `chore`, `refactor` (no behaviour change, tests unchanged), `perf`. Body names the WP, UR and R IDs touched and the evidence command.
- Never combine a refactor with a feature. Never reformat unrelated files.
- Pull request template: WP and goal · gate evidence (commands and output) · rules and requirements touched · decisions or queries opened · reviewer report link · checklist from `what-not-to-do.md` §7.
- `CHANGELOG.md` follows Keep a Changelog. Versions follow SemVer for the tool. A table in the changelog maps each tool version to the Yellow Paper version it implements. The version string lives only in `pyproject.toml`; `__version__` reads it through `importlib.metadata`.
- `main` is always green. Tags `vX.Y.Z` are made only by the Release Engineer after WP-17.

## 8. Documentation style

- README order: what it is (two sentences) · install · five-minute tutorial (publish, verify, tamper, verify again) · what a verification does and does not show · commands at a glance · library example · links.
- Every code block that is a command is executed in CI and its shown output equals the real output. No screenshots.
- Write for a writer first, a cryptographer second. Define a term where it first appears. Link the Yellow Paper section instead of re-explaining the standard.
- Limits and non-goals are stated up front, not hidden at the bottom.
- Vocabulary is fixed: "bundle", "manifest", "identifier", "signature", "attestation". Do not call a bundle a "package" or a manifest a "metadata file".

## 9. Tool configuration (put these in `pyproject.toml`)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = ["E","F","W","I","N","UP","B","C4","C90","SIM","RUF","S","BLE","PT","D","ANN","T20"]
[tool.ruff.lint.mccabe]
max-complexity = 10
[tool.ruff.lint.pydocstyle]
convention = "google"
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101","D","ANN"]
"tools/**" = ["T20","S"]

[tool.mypy]
strict = true
python_version = "3.11"
warn_unused_ignores = true
[[tool.mypy.overrides]]
module = ["unicodedata2", "pqcrypto", "pqcrypto.*"]
ignore_missing_imports = true      # untyped third-party; wrapped by adapter modules (guidelines §1)

[tool.pytest.ini_options]
addopts = "-ra --strict-markers --strict-config"
markers = ["conformance", "oracle", "slow", "fuzz", "req(id): requirement covered"]
```

`T20` forbids `print` in `src/` except `cli/` (use a per-file ignore there).

## 10. Review checklist (every pull request)

1. Does it match the WP card and nothing more?
2. Is each new rule, requirement or decision referenced by ID?
3. Are PT0/PT1 changes covered by a failing-first test and reject-path tests?
4. Any banned claim, placeholder, invented flag or unlabelled assumption?
5. Do docs, schemas and help text still match behaviour?
6. Could a cryptographer follow the diff from the paper alone?
