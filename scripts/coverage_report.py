from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cov_targets = [
        "src/api",
        "src/core.py",
        "src/utils",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "not performance_smoke and not performance_full",
        "--maxfail=1",
        "--durations=15",
        str(repo_root / "tests"),
    ]

    for target in cov_targets:
        cmd.extend(["--cov", target])

    cmd.extend(
        [
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=90",
        ]
    )

    subprocess.run(cmd, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()

