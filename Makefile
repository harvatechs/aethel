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

check: lint type
	$(PYTEST) -m "not slow and not fuzz" --cov=aethel_codex --cov-branch --cov-report=json:coverage.json -q
	uv run python tools/check_coverage.py
	uv run python tools/trace.py

fuzz:
	$(PYTEST) -m fuzz --hypothesis-profile=fuzz -q

build:
	uv build && uv run twine check dist/*

clean:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.json
