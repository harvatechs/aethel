# release-and-deployment.md — Shipping It

Owner of this document: the Release Engineer (WP-00, WP-15, WP-17). The skeletons below are starting points: **verify each in WP-00** (`uv build`, `twine check`, a clean install) rather than trusting them.

## 1. Packaging model

- One distribution `aethel-codex`, `src/` layout, `hatchling` backend, pure-Python wheel plus sdist. Native code arrives only through the three dependencies.
- Package data inside the wheel: `schemas/*.json`, `data/pip1-vectors.json`, `data/pip1-slh-dsa-vectors.json`, `py.typed`. **Nothing else** (no `tests/`, no fixtures). A test unpacks the wheel and compares the file list.
- The version lives only in `pyproject.toml`; `__version__` reads it with `importlib.metadata`.
- `.gitattributes` (WP-00) so Windows never rewrites test bytes:

```
tests/vectors/**   -text
tests/fixtures/**  -text
tests/data/**      -text
*.pip -text
*.sig -text
*.att -text
*.aek -text
```

## 2. `pyproject.toml` skeleton

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aethel-codex"
version = "0.1.0"
description = "Name your writing by what it says. Reference CLI and library for the Permanent Ink Protocol (PIP-1)."
readme = "README.md"
requires-python = ">=3.11"
license = "Apache-2.0"                       # OD-1. If the backend rejects PEP 639 fields, use license = { text = "Apache-2.0" }
license-files = ["LICENSE"]
keywords = ["pip-1", "content-addressing", "post-quantum", "ml-dsa", "slh-dsa", "canonical-text", "cli"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Environment :: Console",
  "Intended Audience :: Developers",
  "Intended Audience :: Science/Research",
  "Operating System :: POSIX :: Linux",
  "Operating System :: MacOS",
  "Operating System :: Microsoft :: Windows",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Topic :: Security :: Cryptography",
  "Topic :: Text Processing",
  "Typing :: Typed",
]
dependencies = [
  "cryptography>=50.0.2,<51",
  "pqcrypto>=1.0.0,<2",
  "unicodedata2>=18.0.0,<19",
]

[project.urls]
Homepage = "https://aethel-codex.pages.dev/"
Source = "https://github.com/OWNER/aethel-codex"       # OD-6
Issues = "https://github.com/OWNER/aethel-codex/issues"
Changelog = "https://github.com/OWNER/aethel-codex/blob/main/CHANGELOG.md"

[project.scripts]
aethel = "aethel_codex.cli:main"

[dependency-groups]
dev = [
  "pytest", "pytest-cov", "hypothesis", "mypy", "ruff", "import-linter", "jsonschema",
  "build", "twine", "pip-audit", "cyclonedx-bom",
  "dilithium-py==1.5.1", "slh-dsa==0.2.5",
]

[tool.hatch.build.targets.wheel]
packages = ["src/aethel_codex"]

[tool.hatch.build.targets.sdist]
include = ["src/aethel_codex", "tests", "docs", "tools", "scripts", "README.md", "LICENSE", "CHANGELOG.md", "SECURITY.md"]
```

Add the `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` blocks from `guidelines.md` §9, plus coverage and import-linter contracts from `architecture.md` §3.

## 3. `Makefile`

```make
.PHONY: setup lint type test conformance check fuzz build clean
PYTEST ?= uv run pytest

setup:
	uv sync --all-groups
lint:
	uv run ruff check . && uv run ruff format --check .
type:
	uv run mypy src tests
test:
	$(PYTEST) -m "not conformance and not slow and not fuzz" -q
conformance:
	$(PYTEST) -m conformance -q
	uv run aethel selftest
check: lint type
	$(PYTEST) -m "not slow and not fuzz" --cov=aethel_codex --cov-branch -q
	uv run python tools/check_coverage.py
	uv run python tools/trace.py
	uv run aethel selftest
fuzz:
	$(PYTEST) -m fuzz --hypothesis-profile=fuzz -q
build:
	uv build && uv run twine check dist/*
clean:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
```

`tools/check_coverage.py` enforces the per-module gates of R-TEST-02 from `coverage json`. `tools/trace.py` enforces requirement coverage only for work packages recorded as done (`docs/work-log/`), and for everything at WP-17.

## 4. CI/CD

Workflows: `ci.yml` (every pull request and push to `main`), `nightly.yml` (fuzz, slow, mutation, latest-dependencies, `pip-audit`), `release.yml` (tags `v*`). All actions pinned to commit SHAs; default `permissions: contents: read`.

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  lint-type:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@COMMIT_SHA
      - uses: astral-sh/setup-uv@COMMIT_SHA
      - run: uv sync --all-groups --locked
      - run: make lint type
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.11", "3.12", "3.13", "3.14"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@COMMIT_SHA
      - uses: astral-sh/setup-uv@COMMIT_SHA
        with:
          python-version: ${{ matrix.python }}
      - run: uv sync --all-groups --locked
      - run: make check
  determinism:
    needs: test
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@COMMIT_SHA
      - uses: astral-sh/setup-uv@COMMIT_SHA
      - run: uv sync --all-groups --locked
      - run: uv run python tools/determinism_check.py
  build-install-smoke:
    needs: test
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@COMMIT_SHA
      - uses: astral-sh/setup-uv@COMMIT_SHA
      - run: uv build && uv run twine check dist/*
      - run: uv run python tools/install_smoke.py   # clean venv, install wheel, aethel selftest, verify a fixture
```

`release.yml`: on a `v*` tag → build once → run the full suite on the built wheel → provenance attestation → publish to PyPI through Trusted Publishing (`id-token: write` only in the publish job) → GitHub Release with wheel, sdist, CycloneDX SBOM, `SHA256SUMS`. The build is repeated in a second job and the artifacts compared.

## 5. Release ritual

1. WP-17 gate satisfied; `docs/conformance-report.md` generated and committed.
2. Update `CHANGELOG.md` (including the tool ↔ Yellow Paper table) and the version in `pyproject.toml`.
3. `make check` locally; confirm CI is green on `main`.
4. Create a signed tag `vX.Y.Z`; push. `release.yml` runs.
5. In a clean environment on each OS: `pipx install aethel-codex==X.Y.Z`, then `aethel selftest` and `aethel verify` on a fixture.
6. **Dogfood:** publish the release notes as a PIP-1 bundle with an offline, dual-family project key (never in CI); attach a tarball of the bundle directory to the release as a convenience (the tarball is not a PIP-1 format). The first work published is the manifesto (`pip1:t:de93176d…fd4b`, already reproduced).
7. Update the site (§6). Announce only what the tool does, in the approved phrases.

## 6. Site and documentation updates (`aethel-codex.pages.dev`)

Observed on 14 Nov 2026 and to do at release (OD-8):

- Footer and status: the page says rc.1 and the paper is **rc.3**; change both together with the tool version.
- The identifiers in the hero and manifesto display as `pip1:t:pip1:t:…`; check whether the prefix is added twice and fix it.
- Resources marked SOON (Yellow Paper, reference implementation, test vectors): link the PDF, the repository and the vectors once they exist.
- Publish `pip1-vectors.json`, `pip1-slh-dsa-vectors.json` and their `SHA256SUMS` at permanent URLs with `Access-Control-Allow-Origin: *` (Cloudflare Pages `_headers` file) so other implementers and the future browser verifier can fetch them.
- Add an Install section: `pipx install aethel-codex`, with the warning "not `aethel`".
- Change the publishing-tool status from PLANNED only when the release is on PyPI and the install smoke test passed.
- Keep "No cookies. No analytics. No ads." true. Add no trackers.
- Add a test (or a manual checklist item) that the page's demo identifiers equal what `aethel id` prints for the same text.

## 7. Distribution

Now: PyPI (`pipx install aethel-codex`, `uv tool install aethel-codex`, `pip install aethel-codex` in a virtual environment), GitHub Releases. Later (P2): Homebrew tap, container image, a self-contained zipapp, distribution packages. Say plainly in the README: Linux needs glibc ≥ 2.34 or musl; no Linux armv7 and no Windows ARM64 until upstream wheels exist.

## 8. Versioning and compatibility

| Tool | Yellow Paper | Profile |
|---|---|---|
| 0.1.x | 1.0.0-rc.3 | `pip-1` |

The tool implements exactly one profile at a time and never silently accepts two Yellow Paper versions. If the paper's bytes change between the release candidates and the final text, the tool gets a new minor version and a migration note. Anything made under rc.3 remains valid only if the final paper leaves its bytes unchanged; the changelog says so.

## 9. Rollback

Yank the faulty release on PyPI (installers then skip it), publish a fixed version, file an advisory if the fault touches FC4, and say what happened on the site. Never delete a release or rewrite a tag.
