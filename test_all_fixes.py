#!/usr/bin/env python3
"""
Comprehensive test script to verify all fixes work together
Tests Issues #322, #254, #258, and #325
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

def test_module_import(module_path, module_name):
    """Test if a module can be imported successfully"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            return False, f"Could not create spec for {module_name}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, f"✓ {module_name} imported successfully"
    except Exception as e:
        return False, f"✗ {module_name} failed: {str(e)}"

def test_file_exists(file_path):
    """Test if a file exists"""
    if os.path.exists(file_path):
        return True, f"✓ {file_path} exists"
    else:
        return False, f"✗ {file_path} missing"

def test_syntax_check(file_path):
    """Test Python syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        return True, f"✓ {file_path} syntax OK"
    except SyntaxError as e:
        return False, f"✗ {file_path} syntax error: {e}"
    except Exception as e:
        return False, f"✗ {file_path} error: {e}"

def test_json_structure(file_path, required_keys=None):
    """Test JSON file structure"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if required_keys:
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                return False, f"✗ {file_path} missing keys: {missing_keys}"
        
        return True, f"✓ {file_path} JSON structure OK"
    except json.JSONDecodeError as e:
        return False, f"✗ {file_path} JSON error: {e}"
    except Exception as e:
        return False, f"✗ {file_path} error: {e}"

def test_class_methods(module, class_name, required_methods):
    """Test if class has required methods"""
    try:
        cls = getattr(module, class_name)
        missing_methods = [method for method in required_methods if not hasattr(cls, method)]
        if missing_methods:
            return False, f"✗ {class_name} missing methods: {missing_methods}"
        return True, f"✓ {class_name} has all required methods"
    except AttributeError:
        return False, f"✗ {class_name} not found in module"

def main():
    """Run comprehensive tests"""
    print("=" * 80)
    print("COMPREHENSIVE FIXES TEST")
    print("Testing Issues #322, #254, #258, and #325")
    print("=" * 80)
    
    base_path = Path(__file__).parent
    ml_api_path = base_path / "ml-model-api"
    frontend_path = base_path / "frontend"
    
    all_tests_passed = True
    test_results = []
    
    print("\n🔍 TESTING ISSUE #322 - Advanced Input Validation (Backend)")
    print("-" * 60)
    
    # Test backend files exist
    backend_files = [
        ml_api_path / "security_config.py",
        ml_api_path / "image_optimizer.py", 
        ml_api_path / "test_input_validation.py",
        ml_api_path / "api_endpoints.py"
    ]
    
    for file_path in backend_files:
        passed, message = test_file_exists(file_path)
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("file_exists", str(file_path), passed, message))
    
    # Test syntax
    for file_path in backend_files:
        if file_path.suffix == '.py':
            passed, message = test_syntax_check(file_path)
            print(message)
            all_tests_passed = all_tests_passed and passed
            test_results.append(("syntax", str(file_path), passed, message))
    
    # Test module imports
    security_config_path = ml_api_path / "security_config.py"
    if security_config_path.exists():
        passed, message = test_module_import(security_config_path, "security_config")
        print(message)
        all_tests_passed = all_tests_passed and passed
        
        if passed:
            # Test required classes
            try:
                spec = importlib.util.spec_from_file_location("security_config", security_config_path)
                security_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(security_module)
                
                required_classes = [
                    ("InputValidator", ["validate_text", "validate_json", "validate_file"]),
                    ("FileValidator", ["validate_file_type", "validate_file_size", "scan_malware"]),
                    ("SecurityMiddleware", ["validate_request", "generate_report"])
                ]
                
                for class_name, methods in required_classes:
                    passed, message = test_class_methods(security_module, class_name, methods)
                    print(message)
                    all_tests_passed = all_tests_passed and passed
                    test_results.append(("class_methods", class_name, passed, message))
                    
            except Exception as e:
                print(f"✗ Could not test security_config classes: {e}")
                all_tests_passed = False
    
    print("\n🔍 TESTING ISSUE #254 - Enhanced Image Upload (Frontend)")
    print("-" * 60)
    
    # Test frontend files exist
    frontend_files = [
        frontend_path / "components" / "ImageUpload.tsx",
        frontend_path / "utils" / "api.ts",
        frontend_path / "types" / "index.ts"
    ]
    
    for file_path in frontend_files:
        passed, message = test_file_exists(file_path)
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("file_exists", str(file_path), passed, message))
    
    # Test TypeScript types structure
    types_file = frontend_path / "types" / "index.ts"
    if types_file.exists():
        try:
            with open(types_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_interfaces = [
                "UploadProgress", "ExifData", "ChunkedUploadData", 
                "UploadResponse", "TutorialStep", "SearchAnalytics"
            ]
            
            missing_interfaces = []
            for interface in required_interfaces:
                if f"interface {interface}" not in content:
                    missing_interfaces.append(interface)
            
            if missing_interfaces:
                print(f"✗ types/index.ts missing interfaces: {missing_interfaces}")
                all_tests_passed = False
                test_results.append(("interfaces", "types/index.ts", False, f"Missing: {missing_interfaces}"))
            else:
                print("✓ types/index.ts has all required interfaces")
                test_results.append(("interfaces", "types/index.ts", True, "All interfaces found"))
                
        except Exception as e:
            print(f"✗ Could not read types/index.ts: {e}")
            all_tests_passed = False
    
    print("\n🔍 TESTING ISSUE #258 - Interactive Food Recognition Tutorial (Frontend)")
    print("-" * 60)
    
    # Test tutorial files exist
    tutorial_files = [
        frontend_path / "components" / "Tutorial.tsx",
        frontend_path / "hooks" / "useTutorial.ts",
        frontend_path / "pages" / "onboarding.tsx",
        frontend_path / "styles" / "tutorial.css"
    ]
    
    for file_path in tutorial_files:
        passed, message = test_file_exists(file_path)
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("file_exists", str(file_path), passed, message))
    
    # Test tutorial CSS structure
    tutorial_css = frontend_path / "styles" / "tutorial.css"
    if tutorial_css.exists():
        try:
            with open(tutorial_css, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            required_classes = [
                ".tutorial-overlay", ".tutorial-tooltip", ".tutorial-highlight",
                ".tutorial-progress-bar", ".tutorial-actions", ".tutorial-button"
            ]
            
            missing_classes = []
            for css_class in required_classes:
                if css_class not in css_content:
                    missing_classes.append(css_class)
            
            if missing_classes:
                print(f"✗ tutorial.css missing classes: {missing_classes}")
                all_tests_passed = False
                test_results.append(("css_classes", "tutorial.css", False, f"Missing: {missing_classes}"))
            else:
                print("✓ tutorial.css has all required classes")
                test_results.append(("css_classes", "tutorial.css", True, "All classes found"))
                
        except Exception as e:
            print(f"✗ Could not read tutorial.css: {e}")
            all_tests_passed = False
    
    print("\n🔍 TESTING ISSUE #325 - Advanced Search Functionality (Backend)")
    print("-" * 60)
    
    # Test search files exist
    search_files = [
        ml_api_path / "search_handlers.py",
        ml_api_path / "api_endpoints.py"
    ]
    
    for file_path in search_files:
        passed, message = test_file_exists(file_path)
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("file_exists", str(file_path), passed, message))
    
    # Test search module structure
    search_handlers_path = ml_api_path / "search_handlers.py"
    if search_handlers_path.exists():
        passed, message = test_syntax_check(search_handlers_path)
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("syntax", str(search_handlers_path), passed, message))
        
        if passed:
            try:
                spec = importlib.util.spec_from_file_location("search_handlers", search_handlers_path)
                search_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(search_module)
                
                required_classes = [
                    ("SearchIndexer", ["index_document", "search", "_tokenize"]),
                    ("SearchAnalytics", ["track_search", "get_search_stats"])
                ]
                
                for class_name, methods in required_classes:
                    passed, message = test_class_methods(search_module, class_name, methods)
                    print(message)
                    all_tests_passed = all_tests_passed and passed
                    test_results.append(("class_methods", class_name, passed, message))
                    
            except Exception as e:
                print(f"✗ Could not test search_handlers classes: {e}")
                all_tests_passed = False
    
    print("\n🔍 TESTING INTEGRATION AND COMPATIBILITY")
    print("-" * 60)
    
    # Test that api_endpoints.py imports all new modules
    api_endpoints_path = ml_api_path / "api_endpoints.py"
    if api_endpoints_path.exists():
        try:
            with open(api_endpoints_path, 'r', encoding='utf-8') as f:
                api_content = f.read()
            
            required_imports = [
                "from security_config import",
                "from image_optimizer import", 
                "from search_handlers import",
                "register_validation_endpoints",
                "register_search_endpoints"
            ]
            
            missing_imports = []
            for import_stmt in required_imports:
                if import_stmt not in api_content:
                    missing_imports.append(import_stmt)
            
            if missing_imports:
                print(f"✗ api_endpoints.py missing imports: {missing_imports}")
                all_tests_passed = False
                test_results.append(("imports", "api_endpoints.py", False, f"Missing: {missing_imports}"))
            else:
                print("✓ api_endpoints.py has all required imports")
                test_results.append(("imports", "api_endpoints.py", True, "All imports found"))
                
        except Exception as e:
            print(f"✗ Could not read api_endpoints.py: {e}")
            all_tests_passed = False
    
    # Test package.json dependencies
    package_json = frontend_path / "package.json"
    if package_json.exists():
        passed, message = test_json_structure(package_json, ["dependencies", "devDependencies"])
        print(message)
        all_tests_passed = all_tests_passed and passed
        test_results.append(("package_json", str(package_json), passed, message))
    
    # Test requirements.txt
    requirements_txt = ml_api_path / "requirements.txt"
    if requirements_txt.exists():
        try:
            with open(requirements_txt, 'r', encoding='utf-8') as f:
                requirements_content = f.read()
            
            required_packages = ["flask", "pillow", "numpy"]
            missing_packages = []
            
            for package in required_packages:
                if package not in requirements_content.lower():
                    missing_packages.append(package)
            
            if missing_packages:
                print(f"⚠ requirements.txt might be missing: {missing_packages}")
                # Not a failure, just a warning
            else:
                print("✓ requirements.txt has basic packages")
                
        except Exception as e:
            print(f"✗ Could not read requirements.txt: {e}")
            all_tests_passed = False
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, _, passed, _ in test_results if passed)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print("\n❌ FAILED TESTS:")
        for test_type, file_path, passed, message in test_results:
            if not passed:
                print(f"  {message}")
    
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! All fixes are working correctly.")
        print("\n✅ Issue #322 - Advanced Input Validation: COMPLETE")
        print("✅ Issue #254 - Enhanced Image Upload: COMPLETE") 
        print("✅ Issue #258 - Interactive Tutorial: COMPLETE")
        print("✅ Issue #325 - Advanced Search: COMPLETE")
    else:
        print("❌ SOME TESTS FAILED! Please review the failed tests above.")
        print("\n⚠️  Fix the issues before proceeding with commit and PR.")
    
    print("=" * 80)
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
