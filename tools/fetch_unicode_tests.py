"""Download Unicode 18.0.0 NormalizationTest.txt and record SHA256 checksum."""

import hashlib
from pathlib import Path
import sys
import urllib.request

URL = "https://www.unicode.org/Public/18.0.0/ucd/NormalizationTest.txt"
OUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "data" / "unicode-18.0.0"
OUT_FILE = OUT_DIR / "NormalizationTest.txt"
SUMS_FILE = Path(__file__).resolve().parent.parent / "tests" / "data" / "SHA256SUMS"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {URL} ...")
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Aethel-Dev-Tool/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
    except Exception as e:
        sys.stderr.write(f"Failed to fetch {URL}: {e}\n")
        return 1

    first_line = data[:500].decode("utf-8", errors="replace").splitlines()[0]
    print(f"Header: {first_line}")
    if "18.0.0" not in first_line:
        sys.stderr.write(f"ERROR: Expected Unicode 18.0.0 in header, got: {first_line}\n")
        return 1

    OUT_FILE.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"Saved {len(data)} bytes to {OUT_FILE}")
    print(f"SHA-256: {digest}")

    rel_path = "tests/data/unicode-18.0.0/NormalizationTest.txt"
    SUMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMS_FILE.write_text(f"{digest}  {rel_path}\n", encoding="utf-8")
    print(f"Wrote checksum to {SUMS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
