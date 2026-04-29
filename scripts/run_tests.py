from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run FlavorSnap pytest suites.")
    parser.add_argument(
        "--performance-smoke",
        action="store_true",
        help="Run only tests marked with `performance_smoke`.",
    )
    parser.add_argument(
        "--performance-full",
        action="store_true",
        help="Run only tests marked with `performance_full`.",
    )
    parser.add_argument(
        "--extra-pytest-args",
        nargs="*",
        default=[],
        help="Extra args forwarded to pytest.",
    )
    args = parser.parse_args()

    if args.performance_smoke and args.performance_full:
        raise SystemExit("Choose only one of --performance-smoke/--performance-full.")

    if args.performance_full:
        marker_expr = "performance_full"
    elif args.performance_smoke:
        marker_expr = "performance_smoke"
    else:
        # Default: unit + integration suites only (exclude all performance markers).
        marker_expr = "not performance_smoke and not performance_full"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        marker_expr,
        "--maxfail=1",
        "--durations=15",
        str(repo_root / "tests"),
        *args.extra_pytest_args,
    ]

    subprocess.run(cmd, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()

