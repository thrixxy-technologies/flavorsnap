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

    # Try to find the best Python executable
    python_exe = None
    
    # First try sys.executable (might work in some cases)
    if sys.executable and not sys.executable.endswith("python.exe"):
        # If we're running from a different Python, try to find the right one
        python_candidates = [
            "py",  # Windows Python launcher
            "python3", 
            "python",
        ]
        
        for candidate in python_candidates:
            try:
                result = subprocess.run([candidate, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    python_exe = candidate
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
    else:
        python_exe = sys.executable or "python"

    if not python_exe:
        print("Error: Could not find a working Python executable")
        print("Please install Python or ensure it's in your PATH")
        sys.exit(1)

    print(f"Using Python executable: {python_exe}")

    cmd = [
        python_exe,
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

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=repo_root, check=True)
        print("Coverage report completed successfully!")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Coverage report failed with exit code: {e.returncode}")
        print("\nTroubleshooting tips:")
        print("1. Ensure all required packages are installed:")
        print("   pip install -r requirements-dev.txt")
        print("2. Check that pytest is available:")
        print(f"   {python_exe} -m pytest --version")
        print("3. Verify test files exist:")
        print(f"   ls {repo_root / 'tests'}")
        sys.exit(e.returncode)
    except FileNotFoundError as e:
        print(f"Python executable not found: {python_exe}")
        print("Please install Python or ensure it's in your PATH")
        sys.exit(1)


if __name__ == "__main__":
    main()
