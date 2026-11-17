"""Example demonstrating publishing and verifying a PIP-1 bundle with aethel_codex."""

import tempfile
from pathlib import Path

from aethel_codex.ctf1 import canonicalize
from aethel_codex.keyfile import create_key, load_key
from aethel_codex.merkle import text_id
from aethel_codex.publish import PublishRequest, publish_bundle
from aethel_codex.verify import verify_bundle


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)

        # 1. Author manuscript
        manuscript_path = tmp_dir / "essay.md"
        manuscript_path.write_bytes(
            b"# The Nature of Permanent Ink\n\nWords recorded without alteration.\n"
        )

        # 2. Canonicalize text
        canonical_bytes, _ = canonicalize(manuscript_path.read_bytes())
        tid = text_id(canonical_bytes)
        print(f"Computed Text ID: {tid}")

        # 3. Create post-quantum signing key (ML-DSA-87)
        key_path = tmp_dir / "author.aek"
        create_key("ml-dsa-87", key_path)
        sk = load_key(key_path)

        # 4. Publish bundle
        bundles_dir = tmp_dir / "bundles"
        req = PublishRequest(
            manuscript_path=manuscript_path,
            title="The Nature of Permanent Ink",
            license="CC-BY-4.0",
            lang="en",
            keys=[sk],
            out_dir=bundles_dir,
        )
        result = publish_bundle(req)
        assert result.bundle_path is not None
        print(f"Published Bundle at: {result.bundle_path.name}")

        # 5. Verify bundle
        report = verify_bundle(result.bundle_path)
        print(f"Integrity:   {report.integrity}")
        print(
            f"Attribution: {report.attribution.cls} ({report.attribution.signed} of {report.attribution.declared})"
        )
        print(f"Exit Code:   {report.exit_code}")

        assert report.integrity == "PASS"
        assert report.attribution.cls == "Attributed"
        print("Verification successful!")


if __name__ == "__main__":
    main()
