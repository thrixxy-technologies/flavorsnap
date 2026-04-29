#!/usr/bin/env python3
"""
Test runner for advanced features
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'numpy', 'pandas', 'torch', 'cv2', 'PIL',
        'neo4j', 'redis', 'kafka', 'kubernetes',
        'pytest', 'pytest_asyncio'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {missing_packages}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def run_unit_tests():
    """Run unit tests"""
    try:
        # Try to run pytest
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_advanced_features.py', 
            '-v', '--tb=short'
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def run_syntax_checks():
    """Run syntax checks on all Python files"""
    python_files = list(Path('ml-model-api').glob('*.py')) + list(Path('tests').glob('*.py'))
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), str(file_path), 'exec')
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
    
    if syntax_errors:
        print("Syntax errors found:")
        for error in syntax_errors:
            print(f"  - {error}")
        return False
    
    print("All syntax checks passed!")
    return True

def main():
    """Main test runner"""
    print("FlavorSnap Advanced Features Test Runner")
    print("=" * 50)
    
    # Check syntax first
    print("\n1. Running syntax checks...")
    if not run_syntax_checks():
        sys.exit(1)
    
    # Check dependencies
    print("\n2. Checking dependencies...")
    if not check_dependencies():
        print("Dependencies check failed, but continuing with syntax tests...")
    
    # Run unit tests
    print("\n3. Running unit tests...")
    success = run_unit_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
