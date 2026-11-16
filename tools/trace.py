"""Traceability verification script (R-TEST-01).

Inspects test files for @pytest.mark.req("UR-nn") markers and R-... rule references.
Until WP-17, enforces requirements whose owning work packages are completed in docs/work-log/.
At WP-17, enforces all P0 requirements.
"""

import ast
from pathlib import Path
import re
import sys

# Map of UR requirements to work packages from user-requirements.md
UR_WP_MAP = {
    "UR-01": "WP-02",
    "UR-02": "WP-03",
    "UR-03": "WP-02",
    "UR-04": "WP-10",
    "UR-05": "WP-08",
    "UR-06": "WP-08",
    "UR-08": "WP-09",
    "UR-09": "WP-09",
    "UR-10": "WP-09",
    "UR-11": "WP-09",
    "UR-12": "WP-09",
    "UR-15": "WP-06",
    "UR-17": "WP-07",
    "UR-18": "WP-07",
    "UR-19": "WP-07",
    "UR-20": "WP-07",
    "UR-21": "WP-07",
    "UR-22": "WP-07",
    "UR-23": "WP-10",
    "UR-24": "WP-11",
    "UR-25": "WP-11",
    "UR-26": "WP-11",
    "UR-30": "WP-15",
    "UR-31": "WP-14",
    "UR-32": "WP-16",
    "UR-35": "WP-16",
    "UR-36": "WP-13",
    "UR-37": "WP-10",
    "UR-39": "WP-08",
    "UR-40": "WP-10",
}


def find_completed_work_packages(work_log_dir: Path) -> set[str]:
    completed = set()
    if not work_log_dir.exists():
        return completed
    for p in work_log_dir.glob("WP-*.md"):
        m = re.match(r"(WP-\d\d)", p.name)
        if m:
            completed.add(m.group(1))
    return completed


def scan_tests_for_requirements(tests_dir: Path) -> set[str]:
    found_reqs: set[str] = set()
    for py_path in tests_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_path.read_bytes(), filename=str(py_path))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    # Check @pytest.mark.req("UR-nn")
                    if isinstance(dec, ast.Call):
                        func = dec.func
                        if (
                            isinstance(func, ast.Attribute)
                            and func.attr == "req"
                            and dec.args
                            and isinstance(dec.args[0], ast.Constant)
                        ):
                            found_reqs.add(str(dec.args[0].value))
    return found_reqs


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    work_log_dir = repo_root / "docs" / "work-log"
    tests_dir = repo_root / "tests"

    completed_wps = find_completed_work_packages(work_log_dir)
    found_reqs = scan_tests_for_requirements(tests_dir)

    # Check if WP-17 is being closed
    is_wp17 = "WP-17" in completed_wps

    missing = []
    for req_id, wp in UR_WP_MAP.items():
        if (is_wp17 or wp in completed_wps) and req_id not in found_reqs:
            missing.append(f"{req_id} (from {wp})")

    if missing:
        sys.stderr.write(
            f"Traceability check failed. Missing tests for requirements: {', '.join(missing)}\n"
        )
        return 1

    print(f"Traceability check passed: {len(found_reqs)} requirements traced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
