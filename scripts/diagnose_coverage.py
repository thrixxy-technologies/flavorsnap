#!/usr/bin/env python3
"""
Diagnostic script to identify and fix Python/coverage issues.
This script helps diagnose common problems with the coverage report.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python():
    """Check Python installation and version."""
    print("🔍 Checking Python installation...")
    
    try:
        version = sys.version_info
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        print(f"📍 Python executable: {sys.executable}")
        return True
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False

def check_dependencies():
    """Check required dependencies."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        'pytest',
        'pytest-cov', 
        'python-multipart',
        'fastapi'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-multipart':
                import multipart
            elif package == 'fastapi':
                import fastapi
            else:
                __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing_packages.append(package)
    
    return missing_packages

def check_test_files():
    """Check if test files exist."""
    print("\n🔍 Checking test files...")
    
    repo_root = Path(__file__).resolve().parents[1]
    tests_dir = repo_root / "tests"
    
    if not tests_dir.exists():
        print(f"❌ Tests directory not found: {tests_dir}")
        return False
    
    test_files = list(tests_dir.rglob("*.py"))
    print(f"✅ Found {len(test_files)} test files")
    
    # Check for specific test files
    key_files = [
        "tests/api/conftest.py",
        "tests/api/test_classify_endpoint.py"
    ]
    
    for file_path in key_files:
        full_path = repo_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
    
    return True

def check_source_files():
    """Check if source files exist."""
    print("\n🔍 Checking source files...")
    
    repo_root = Path(__file__).resolve().parents[1]
    
    source_files = [
        "src/api/main.py",
        "src/api/routes.py", 
        "src/core/__init__.py",
        "src/utils/__init__.py"
    ]
    
    for file_path in source_files:
        full_path = repo_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            return False
    
    return True

def install_dependencies(missing_packages):
    """Install missing dependencies."""
    if not missing_packages:
        return True
    
    print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
    
    try:
        cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

def run_simple_test():
    """Run a simple test to verify setup."""
    print("\n🧪 Running simple test...")
    
    try:
        cmd = [sys.executable, "-m", "pytest", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ pytest working: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ pytest failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def generate_fix_script():
    """Generate a fix script for common issues."""
    repo_root = Path(__file__).resolve().parents[1]
    
    fix_script = f"""#!/bin/bash
# Auto-generated fix script for coverage issues

echo "🔧 Fixing coverage issues..."

# Install/update dependencies
echo "📦 Installing dependencies..."
{sys.executable} -m pip install --upgrade pip
{sys.executable} -m pip install -r requirements-dev.txt

# Install specific packages that might be missing
{sys.executable} -m pip install pytest pytest-cov python-multipart fastapi uvicorn

# Check if everything is working
echo "🧪 Testing setup..."
{sys.executable} -m pytest --version

echo "✅ Setup complete! Try running the coverage report again."
"""
    
    fix_path = repo_root / "fix_coverage.sh"
    with open(fix_path, 'w') as f:
        f.write(fix_script)
    
    os.chmod(fix_path, 0o755)
    print(f"\n📝 Generated fix script: {fix_path}")
    print("Run it with: bash fix_coverage.sh")

def main():
    """Main diagnostic function."""
    print("🚀 FlavorSnap Coverage Diagnostic Tool")
    print("=" * 50)
    
    # Run checks
    checks = [
        ("Python Installation", check_python),
        ("Source Files", check_source_files), 
        ("Test Files", check_test_files),
        ("Dependencies", check_dependencies),
        ("Simple Test", run_simple_test),
    ]
    
    all_passed = True
    missing_deps = []
    
    for name, check_func in checks:
        try:
            if name == "Dependencies":
                missing_deps = check_func()
                if missing_deps:
                    all_passed = False
            else:
                result = check_func()
                if not result:
                    all_passed = False
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    
    if all_passed and not missing_deps:
        print("✅ All checks passed! The coverage report should work.")
        print("\n🏃 Run the coverage report with:")
        print("python scripts/coverage_report.py")
    else:
        print("❌ Some checks failed. Generating fix script...")
        
        if missing_deps:
            install_dependencies(missing_deps)
        
        generate_fix_script()
        
        print("\n🔧 Additional fixes to try:")
        print("1. Ensure Python is in your PATH")
        print("2. Install dependencies: pip install -r requirements-dev.txt")
        print("3. On Windows, try: py scripts/coverage_report.py")
        print("4. Or use the generated fix script")

if __name__ == "__main__":
    main()
