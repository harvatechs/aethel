"""Enforce precision tier coverage gates (R-TEST-02).

Usage:
    python tools/check_coverage.py [coverage_json_path]
"""

import json
import sys
from pathlib import Path

PT0_MODULES = {
    "constants.py",
    "hashing.py",
    "unicode18.py",
    "_repertoire.py",
    "ctf1.py",
    "merkle.py",
    "pid.py",
}

PT1_MODULES = {
    "manifest.py",
    "envelope.py",
    "citations.py",
    "signing.py",
    "limits.py",
    "bundle.py",
    "keyfile.py",
    "verify.py",
    "report.py",
}


def main() -> int:
    cov_path = Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.json")
    if not cov_path.exists():
        sys.stderr.write(f"Error: {cov_path} not found. Run coverage json first.\n")
        return 1

    with open(cov_path, encoding="utf-8") as f:
        data = json.load(f)

    files = data.get("files", {})
    totals = data.get("totals", {})

    overall_percent = totals.get("percent_covered", 0.0)
    print(f"Overall coverage: {overall_percent:.2f}%")

    failed = False

    for file_path, file_data in files.items():
        base_name = Path(file_path).name
        summary = file_data.get("summary", {})
        covered_lines = summary.get("covered_lines", 0)
        num_statements = summary.get("num_statements", 0)
        line_rate = (covered_lines / num_statements * 100.0) if num_statements > 0 else 100.0

        num_branches = summary.get("num_branches", 0)
        covered_branches = summary.get("covered_branches", 0)
        branch_rate = (covered_branches / num_branches * 100.0) if num_branches > 0 else 100.0

        if base_name in PT0_MODULES and (branch_rate < 100.0 or line_rate < 100.0):
            sys.stderr.write(
                f"FAIL: PT0 module {base_name} requires 100% branch coverage "
                f"(got {branch_rate:.1f}% branch, {line_rate:.1f}% line)\n"
            )
            failed = True
        elif base_name in PT1_MODULES and line_rate < 95.0:
            sys.stderr.write(
                f"FAIL: PT1 module {base_name} requires >= 95% line coverage "
                f"(got {line_rate:.1f}% line)\n"
            )
            failed = True

    if failed:
        return 1

    print("All coverage tier gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
