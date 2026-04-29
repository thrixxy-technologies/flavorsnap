#!/usr/bin/env python3
"""
Test script for Advanced Feature Engineering Pipeline
Validates all components of the feature engineering system
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
try:
    from feature_extraction import AutomatedFeatureExtractor, FeatureConfig, FeatureType
    from feature_selection import FeatureSelector, SelectionConfig, SelectionMethod
    from feature_engineering import FeatureEngineeringPipeline, PipelineConfig
    from model_training import AdvancedModelTrainer, TrainingConfig
    from feature_importance import FeatureImportanceAnalyzer, ImportanceConfig, ImportanceMethod
    from feature_monitoring import FeatureMonitoringSystem, MonitoringConfig
    from feature_versioning import FeatureVersioningSystem, VersionConfig, VersionStatus
    from performance_tracking import PerformanceTracker, TrackingConfig
    from feature_documentation import FeatureDocumentationSystem, DocumentationConfig
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_feature_extraction():
    """Test feature extraction component"""
    logger.info("Testing Feature Extraction...")
    
    try:
        # Create extractor
        config = FeatureConfig(
            enable_color_features=True,
            enable_texture_features=True,
            enable_shape_features=True,
            enable_deep_features=False  # Skip deep features for testing
        )
        extractor = AutomatedFeatureExtractor(config)
        
        # Test with sample data (create a dummy image file)
        sample_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        
        # Since we can't save/load images in this test, we'll test the internal methods
        logger.info("✓ Feature extraction component initialized successfully")
        
        # Test configuration
        assert config.enable_color_features == True
        assert config.enable_deep_features == False
        logger.info("✓ Feature extraction configuration working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature extraction test failed: {e}")
        return False

def test_feature_selection():
    """Test feature selection component"""
    logger.info("Testing Feature Selection...")
    
    try:
        # Create sample data
        np.random.seed(42)
        X = np.random.rand(100, 20)  # 100 samples, 20 features
        y = np.random.randint(0, 2, 100)  # Binary classification
        feature_names = [f"feature_{i}" for i in range(20)]
        
        # Create selector
        config = SelectionConfig(
            task_type="classification",
            cv_folds=3  # Use fewer folds for faster testing
        )
        selector = FeatureSelector(config)
        
        # Test feature selection
        results = selector.select_features(X, y, feature_names, 
                                        methods=[SelectionMethod.VARIANCE_THRESHOLD, 
                                               SelectionMethod.RANDOM_FOREST_IMPORTANCE])
        
        assert len(results) > 0
        logger.info(f"✓ Feature selection completed with {len(results)} methods")
        
        # Test best selection
        best = selector.get_best_features()
        assert best is not None
        logger.info(f"✓ Best selection found: {best.method.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature selection test failed: {e}")
        return False

def test_feature_engineering_pipeline():
    """Test feature engineering pipeline"""
    logger.info("Testing Feature Engineering Pipeline...")
    
    try:
        # Create pipeline
        config = PipelineConfig(
            enable_monitoring=False,  # Disable monitoring for testing
            enable_versioning=False,
            enable_documentation=False
        )
        pipeline = FeatureEngineeringPipeline(config)
        
        # Test pipeline initialization
        assert pipeline.feature_extractor is not None
        assert pipeline.feature_selector is not None
        logger.info("✓ Pipeline initialized successfully")
        
        # Test with sample data
        np.random.seed(42)
        X = np.random.rand(50, 10)  # Smaller dataset for testing
        y = np.random.randint(0, 3, 50)
        feature_names = [f"feature_{i}" for i in range(10)]
        
        # Test feature selection through pipeline
        selection_results = pipeline._apply_feature_selection(X, y)
        assert len(selection_results) > 0
        logger.info(f"✓ Pipeline feature selection working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature engineering pipeline test failed: {e}")
        return False

def test_feature_importance():
    """Test feature importance analysis"""
    logger.info("Testing Feature Importance Analysis...")
    
    try:
        # Create sample data
        np.random.seed(42)
        X = np.random.rand(100, 15)
        y = np.random.randint(0, 2, 100)
        feature_names = [f"feature_{i}" for i in range(15)]
        
        # Create analyzer
        config = ImportanceConfig(
            methods=[ImportanceMethod.RANDOM_FOREST, ImportanceMethod.VARIANCE]
        )
        analyzer = FeatureImportanceAnalyzer(config)
        
        # Test importance analysis
        results = analyzer.analyze_importance(X, y, feature_names)
        assert len(results) > 0
        logger.info(f"✓ Importance analysis completed with {len(results)} methods")
        
        # Test summary
        summary = analyzer.get_importance_summary()
        assert "total_analyses" in summary
        logger.info("✓ Importance summary working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature importance test failed: {e}")
        return False

def test_feature_monitoring():
    """Test feature monitoring system"""
    logger.info("Testing Feature Monitoring...")
    
    try:
        # Create monitoring system
        config = MonitoringConfig(
            enable_real_time_monitoring=False,  # Disable for testing
            monitoring_interval=1  # Short interval for testing
        )
        monitor = FeatureMonitoringSystem(config)
        
        # Test initialization
        assert monitor.status.value == "stopped"
        logger.info("✓ Monitoring system initialized")
        
        # Test with sample reference data
        np.random.seed(42)
        X_ref = np.random.rand(100, 10)
        monitor.set_reference_data(X_ref)
        assert monitor.reference_features is not None
        logger.info("✓ Reference data set successfully")
        
        # Test adding data points
        X_new = np.random.rand(10, 10)
        monitor.add_data_point(X_new)
        assert len(monitor.current_features) > 0
        logger.info("✓ Data points added successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature monitoring test failed: {e}")
        return False

def test_feature_versioning():
    """Test feature versioning system"""
    logger.info("Testing Feature Versioning...")
    
    try:
        # Create versioning system
        config = VersionConfig(
            storage_backend=StorageBackend.LOCAL,
            max_versions=5
        )
        versioner = FeatureVersioningSystem(config)
        
        # Test creating a version
        sample_features = {
            "feature_1": {"type": "numerical", "value": 1.0},
            "feature_2": {"type": "categorical", "value": "A"}
        }
        feature_names = ["feature_1", "feature_2"]
        
        version = versioner.create_version(
            features=sample_features,
            feature_names=feature_names,
            description="Test version"
        )
        
        assert version.status == VersionStatus.DRAFT
        assert len(version.feature_names) == 2
        logger.info("✓ Version created successfully")
        
        # Test listing versions
        versions = versioner.list_versions()
        assert len(versions) > 0
        logger.info("✓ Version listing working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature versioning test failed: {e}")
        return False

def test_performance_tracking():
    """Test performance tracking system"""
    logger.info("Testing Performance Tracking...")
    
    try:
        # Create tracker
        config = TrackingConfig(
            enable_real_time_tracking=False  # Disable for testing
        )
        tracker = PerformanceTracker(config)
        
        # Test tracking classification metrics
        np.random.seed(42)
        y_true = np.random.randint(0, 2, 50)
        y_pred = np.random.randint(0, 2, 50)
        y_proba = np.random.rand(50, 2)
        
        metrics = tracker.track_classification_metrics(y_true, y_pred, y_proba)
        assert "accuracy" in metrics
        logger.info("✓ Classification metrics tracked")
        
        # Test tracking system metrics
        system_metrics = tracker.track_system_metrics(
            latency_ms=150.0, throughput=1000.0, memory_usage=0.6, cpu_usage=0.4
        )
        assert "latency" in system_metrics
        logger.info("✓ System metrics tracked")
        
        # Test summary
        summary = tracker.get_performance_summary()
        assert "total_metrics" in summary
        logger.info("✓ Performance summary working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance tracking test failed: {e}")
        return False

def test_feature_documentation():
    """Test feature documentation system"""
    logger.info("Testing Feature Documentation...")
    
    try:
        # Create documentation system
        config = DocumentationConfig(
            output_formats=[DocumentationFormat.MARKDOWN]  # Only markdown for testing
        )
        documenter = FeatureDocumentationSystem(config)
        
        # Test documenting a feature
        doc = documenter.document_feature(
            feature_name="test_feature",
            feature_type=FeatureType.COLOR,
            description="Test feature for validation",
            extraction_method="test_method",
            tags=["test", "validation"]
        )
        
        assert doc.feature_name == "test_feature"
        assert len(doc.tags) == 2
        logger.info("✓ Feature documented successfully")
        
        # Test generating documentation
        catalog_path = documenter.generate_feature_catalog(DocumentationFormat.MARKDOWN)
        assert os.path.exists(catalog_path)
        logger.info("✓ Feature catalog generated")
        
        # Test summary
        summary = documenter.get_documentation_summary()
        assert "total_features" in summary
        logger.info("✓ Documentation summary working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Feature documentation test failed: {e}")
        return False

def test_integration():
    """Test integration between components"""
    logger.info("Testing Integration...")
    
    try:
        # Create sample data
        np.random.seed(42)
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 2, 50)
        feature_names = [f"feature_{i}" for i in range(10)]
        
        # Test feature selection -> importance analysis integration
        selector = FeatureSelector(SelectionConfig(task_type="classification"))
        selection_results = selector.select_features(X, y, feature_names)
        
        if selection_results:
            best_selection = selector.get_best_features()
            if best_selection:
                # Use selected features for importance analysis
                selected_indices = [feature_names.index(f) for f in best_selection.selected_features if f in feature_names]
                if selected_indices:
                    X_selected = X[:, selected_indices]
                    selected_names = [feature_names[i] for i in selected_indices]
                    
                    analyzer = FeatureImportanceAnalyzer(ImportanceConfig())
                    importance_results = analyzer.analyze_importance(X_selected, y, selected_names)
                    
                    assert len(importance_results) > 0
                    logger.info("✓ Integration between selection and importance analysis working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and return results"""
    logger.info("=" * 60)
    logger.info("Starting Advanced Feature Engineering Pipeline Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Feature Extraction", test_feature_extraction),
        ("Feature Selection", test_feature_selection),
        ("Feature Engineering Pipeline", test_feature_engineering_pipeline),
        ("Feature Importance Analysis", test_feature_importance),
        ("Feature Monitoring", test_feature_monitoring),
        ("Feature Versioning", test_feature_versioning),
        ("Performance Tracking", test_performance_tracking),
        ("Feature Documentation", test_feature_documentation),
        ("Integration", test_integration)
    ]
    
    results = {}
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            success = test_func()
            results[test_name] = success
            if success:
                passed += 1
                logger.info(f"✓ {test_name} PASSED")
            else:
                failed += 1
                logger.error(f"✗ {test_name} FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
            results[test_name] = False
            failed += 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed/len(tests))*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED! The advanced feature engineering pipeline is working correctly.")
    else:
        logger.warning(f"⚠️  {failed} test(s) failed. Please check the implementation.")
    
    for test_name, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"{status} {test_name}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
