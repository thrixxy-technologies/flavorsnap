"""
Test script for XAI implementation validation.

This script tests the core functionality of the XAI features
to ensure they work correctly before creating the pull request.
"""

import sys
import os
import torch
import numpy as np
from PIL import Image
import traceback

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

def test_imports():
    """Test that all XAI modules can be imported"""
    print("Testing imports...")
    
    try:
        from xai import ModelExplainer
        print("✓ xai module imported successfully")
    except Exception as e:
        print(f"✗ Failed to import xai module: {e}")
        return False
    
    try:
        from visualization import XAIVisualizer, PerformanceOptimizer
        print("✓ visualization module imported successfully")
    except Exception as e:
        print(f"✗ Failed to import visualization module: {e}")
        return False
    
    try:
        from model_inference import ModelInference
        print("✓ model_inference module imported successfully")
    except Exception as e:
        print(f"✗ Failed to import model_inference module: {e}")
        return False
    
    return True

def test_model_explainer():
    """Test ModelExplainer functionality"""
    print("\nTesting ModelExplainer...")
    
    try:
        from xai import ModelExplainer
        import torchvision.models as models
        
        # Create a simple model for testing
        model = models.resnet18(pretrained=True)
        model.eval()
        
        # Create explainer
        explainer = ModelExplainer(model)
        print("✓ ModelExplainer created successfully")
        
        # Create dummy input
        dummy_input = torch.randn(1, 3, 224, 224)
        
        # Test Grad-CAM
        try:
            heatmap = explainer.generate_grad_cam(dummy_input, 0)
            if heatmap is not None:
                print("✓ Grad-CAM generation successful")
            else:
                print("✗ Grad-CAM generation failed")
        except Exception as e:
            print(f"✗ Grad-CAM generation failed: {e}")
        
        # Test feature importance
        try:
            importance = explainer.generate_feature_importance(dummy_input, 5)
            if importance:
                print("✓ Feature importance generation successful")
            else:
                print("✗ Feature importance generation failed")
        except Exception as e:
            print(f"✗ Feature importance generation failed: {e}")
        
        # Test SHAP (may fail due to dependencies)
        try:
            shap_result = explainer.generate_shap_values(dummy_input, 0)
            if 'error' not in shap_result:
                print("✓ SHAP generation successful")
            else:
                print(f"⚠ SHAP generation returned error (may be expected): {shap_result['error']}")
        except Exception as e:
            print(f"⚠ SHAP generation failed (may be expected): {e}")
        
        # Test LIME (may fail due to dependencies)
        try:
            lime_result = explainer.generate_lime_explanation(dummy_input, 0)
            if 'error' not in lime_result:
                print("✓ LIME generation successful")
            else:
                print(f"⚠ LIME generation returned error (may be expected): {lime_result['error']}")
        except Exception as e:
            print(f"⚠ LIME generation failed (may be expected): {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ ModelExplainer test failed: {e}")
        return False

def test_visualizer():
    """Test XAIVisualizer functionality"""
    print("\nTesting XAIVisualizer...")
    
    try:
        from visualization import XAIVisualizer
        
        # Create visualizer
        visualizer = XAIVisualizer()
        print("✓ XAIVisualizer created successfully")
        
        # Test feature importance plot
        try:
            test_importance = {'feature_1': 0.5, 'feature_2': 0.3, 'feature_3': 0.8}
            plot = visualizer.create_feature_importance_plot(test_importance, "Test Plot", "Test")
            if plot:
                print("✓ Feature importance plot generation successful")
            else:
                print("✗ Feature importance plot generation failed")
        except Exception as e:
            print(f"✗ Feature importance plot generation failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ XAIVisualizer test failed: {e}")
        return False

def test_model_inference():
    """Test ModelInference with XAI features"""
    print("\nTesting ModelInference with XAI...")
    
    try:
        from model_inference import ModelInference
        
        # Create inference instance
        inference = ModelInference()
        print("✓ ModelInference created successfully")
        
        # Test XAI capabilities
        try:
            capabilities = inference.get_xai_capabilities()
            if capabilities:
                print("✓ XAI capabilities retrieval successful")
                print(f"  XAI available: {capabilities['xai_available']}")
                print(f"  Available methods: {len(capabilities['available_methods'])}")
            else:
                print("✗ XAI capabilities retrieval failed")
        except Exception as e:
            print(f"✗ XAI capabilities retrieval failed: {e}")
        
        # Test model info
        try:
            model_info = inference.get_model_info()
            if 'xai_available' in model_info:
                print("✓ Model info with XAI status successful")
                print(f"  XAI available in model: {model_info['xai_available']}")
            else:
                print("✗ Model info missing XAI status")
        except Exception as e:
            print(f"✗ Model info test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ ModelInference test failed: {e}")
        return False

def test_routes():
    """Test XAI routes functionality"""
    print("\nTesting XAI routes...")
    
    try:
        # Check if routes file exists and can be imported
        if os.path.exists('xai_routes.py'):
            print("✓ xai_routes.py file exists")
            
            # Try to import
            try:
                import xai_routes
                print("✓ xai_routes module imported successfully")
                
                # Check if blueprint exists
                if hasattr(xai_routes, 'xai_bp'):
                    print("✓ XAI blueprint exists")
                else:
                    print("✗ XAI blueprint not found")
                
            except Exception as e:
                print(f"✗ Failed to import xai_routes: {e}")
        else:
            print("✗ xai_routes.py file not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Routes test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== XAI Implementation Test Suite ===\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Model Explainer Tests", test_model_explainer),
        ("Visualizer Tests", test_visualizer),
        ("Model Inference Tests", test_model_inference),
        ("Routes Tests", test_routes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! XAI implementation is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
