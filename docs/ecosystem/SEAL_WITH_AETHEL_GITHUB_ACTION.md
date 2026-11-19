# Universal GitHub Action: Automated PIP-1 Sealing for Open Repositories

This document describes how open-source projects, researchers, and technical writers can integrate automated post-quantum document sealing into their CI/CD release pipelines.

---

## The Workflow (`.github/workflows/seal-release.yml`)

Add this workflow to your repository to automatically seal documentation, whitepapers, or source manifests whenever a new release is published:

```yaml
name: Seal Release with Permanent Ink (PIP-1)

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  seal-documents:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Aethel Codex
        run: |
          pip install aethel-codex

      - name: Restore or Generate Signing Key
        id: keys
        run: |
          if [ -n "${{ secrets.PIP1_SIGNING_KEY }}" ]; then
            echo "${{ secrets.PIP1_SIGNING_KEY }}" > author.aek
            chmod 600 author.aek
          else
            echo "Generating ephemeral release signing key..."
            aethel keygen --out author.aek --no-passphrase
          fi

      - name: Publish and Seal Bundle
        run: |
          # Package all Markdown documentation into a self-contained bundle
          mkdir -p build/manuscript
          cp README.md build/manuscript/
          if [ -d "docs" ]; then cp -r docs build/manuscript/; fi
          
          # Seal bundle with Post-Quantum Signatures
          aethel publish build/manuscript/README.md \
            --author-key author.aek \
            --out dist/release-bundle \
            --no-passphrase

      - name: Verify Bundle Integrity (Offline Minimal Verifier)
        run: |
          python -m aethel_codex.cli verify dist/release-bundle

      - name: Upload Bundle to Release Assets
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/release-bundle/*
            author.aek.pub
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## README Seal Badge

Add this badge to your README to indicate that your documentation is cryptographically sealed and preserved:

```markdown
[![Sealed with Permanent Ink](https://img.shields.io/badge/Preserved%20with-Permanent%20Ink%20(PIP--1)-000000.svg?logo=archive)](https://github.com/harvatechs/aethel)
```
