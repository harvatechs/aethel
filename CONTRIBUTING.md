# Contributing to `aethel` and Permanent Ink Protocol (`pip-1`)

Thank you for your interest in contributing to `aethel`, the reference implementation of profile **pip-1** (Yellow Paper PIP-YP-1 v1.0.0-rc.3).

---

## 1. Project Mission & Non-Negotiables

`aethel` is built on a standard where **correctness against the Yellow Paper outranks speed, elegance, and features**.

Every contributor, whether developing new backends, adding research tooling, or refining documentation, must adhere to the core principles:

1. **The Yellow Paper wins**: Normative vectors in `tests/vectors/` are immutable oracles. A failing vector indicates code error.
2. **Offline always**: Zero network socket imports, zero telemetry, zero analytics.
3. **Bytes in, bytes out**: Binary file I/O only (`read_bytes()`, `open(p, "rb")`). No locale-dependent conversions.
4. **Unicode 18.0.0**: Unicode normalization tables strictly come from `unicodedata2` pinned to 18.0.0.
5. **No clocks or identity leakage**: Manifests, texts, and envelopes contain no timestamps, paths, or usernames.
6. **Honest claims**: We report integrity, attribution, history, and time separately; we never claim more than the cryptographic properties prove.
7. **No placeholders**: No `TODO`, `pass` stubs, or mock cryptography in shipped paths.

---

## 2. Research & Academic Contributions

Researchers in cryptography, document preservation, and distributed systems are actively encouraged to contribute:

- **Alternative Language Implementations (YP Open Item 14.3.1)**: We welcome independent cross-verifiers in Rust, Go, Zig, and TypeScript.
- **Cryptographic Review (YP Open Item 14.3.2)**: Formal analysis of our FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) parameterizations, key derivation, and domain separation is strongly invited.
- **Citation & Locators**: Exploration of fine-grained document citations and Merkle chunk proof verification in scholarly corpora.

### Citing This Work
See `CITATION.cff` or use the BibTeX format provided in `README.md`.

---

## 3. Development Workflow

### Setting up the Environment
We use `uv` for fast, reproducible dependency management:

```bash
git clone https://github.com/harvatechs/aethel-pip-one.git
cd aethel-pip-one
uv sync --all-groups
```

### Running the Quality Gates
Before submitting any pull request, ensure the complete gate is green:

```bash
# 1. Lint and format
uv run ruff check .
uv run ruff format --check .

# 2. Type checking
uv run mypy src tests

# 3. Layering contracts
uv run lint-imports

# 4. Test suite with coverage enforcement
uv run pytest -m "not slow and not fuzz" --cov=aethel_codex --cov-branch -q
uv run python tools/check_coverage.py

# 5. Traceability and determinism
uv run python tools/trace.py
uv run python tools/determinism_check.py
uv run python tools/recompute_yp_vectors.py
```

---

## 4. Contact & Community

For architectural questions, research collaboration, or protocol discussions:

- **Harsha Vardhan**  
  Founder at HarVa Groups  
  Lead Architect at Archivist Labs (Init. of Aethel Codex)  
  Email: `heyharva@gmail.com`  
  Repository: https://github.com/harvatechs/aethel-pip-one
