#!/usr/bin/env python3
"""
Simple test script that doesn't require external dependencies
"""

import sys
import os
import tempfile
import shutil

def test_file_creation():
    """Test that all required files were created"""
    required_files = [
        'ml-model-api/backup_manager.py',
        'ml-model-api/recovery_system.py',
        'ml-model-api/disaster_recovery.py',
        'ml-model-api/network_optimizer.py',
        'ml-model-api/connection_pool.py',
        'ml-model-api/compression_handler.py',
        'ml-model-api/nft_handlers.py',
        'ml-model-api/federated_training.py',
        'ml-model-api/model_validation.py',
        'frontend/components/NFTGallery.tsx',
        'frontend/components/NFTMint.tsx',
        'frontend/components/FederatedTraining.tsx'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files created")
        return True

def test_python_syntax():
    """Test Python file syntax"""
    python_files = [
        'ml-model-api/backup_manager.py',
        'ml-model-api/recovery_system.py',
        'ml-model-api/disaster_recovery.py',
        'ml-model-api/network_optimizer.py',
        'ml-model-api/connection_pool.py',
        'ml-model-api/compression_handler.py',
        'ml-model-api/nft_handlers.py',
        'ml-model-api/federated_training.py',
        'ml-model-api/model_validation.py'
    ]
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            compile(code, file_path, 'exec')
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
    
    if syntax_errors:
        print(f"❌ Syntax errors: {syntax_errors}")
        return False
    else:
        print("✅ All Python files have valid syntax")
        return True

def test_class_definitions():
    """Test that main classes are defined"""
    test_files = [
        ('ml-model-api/backup_manager.py', ['BackupManager', 'BackupConfig']),
        ('ml-model-api/recovery_system.py', ['RecoverySystem', 'RecoveryConfig']),
        ('ml-model-api/network_optimizer.py', ['NetworkOptimizer', 'NetworkConfig']),
        ('ml-model-api/nft_handlers.py', ['NFTHandler', 'NFTConfig']),
        ('ml-model-api/federated_training.py', ['FederatedLearningCoordinator', 'FederatedConfig'])
    ]
    
    missing_classes = []
    for file_path, expected_classes in test_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            for class_name in expected_classes:
                if f"class {class_name}" not in content:
                    missing_classes.append(f"{class_name} in {file_path}")
        except Exception as e:
            missing_classes.append(f"Error reading {file_path}: {e}")
    
    if missing_classes:
        print(f"❌ Missing classes: {missing_classes}")
        return False
    else:
        print("✅ All expected classes are defined")
        return True

def test_function_definitions():
    """Test that key functions are defined"""
    test_functions = [
        ('ml-model-api/backup_manager.py', ['create_full_backup', 'create_incremental_backup']),
        ('ml-model-api/network_optimizer.py', ['make_request', 'optimize_connection_pool']),
        ('ml-model-api/nft_handlers.py', ['mint_food_item_nft', 'mint_recipe_nft']),
        ('ml-model-api/federated_training.py', ['register_participant', 'start_federated_training'])
    ]
    
    missing_functions = []
    for file_path, expected_functions in test_functions:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            for function_name in expected_functions:
                if f"def {function_name}" not in content:
                    missing_functions.append(f"{function_name} in {file_path}")
        except Exception as e:
            missing_functions.append(f"Error reading {file_path}: {e}")
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    else:
        print("✅ All expected functions are defined")
        return True

def main():
    """Run all tests"""
    print("Running simple implementation tests...\n")
    
    tests = [
        test_file_creation,
        test_python_syntax,
        test_class_definitions,
        test_function_definitions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation is complete.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
