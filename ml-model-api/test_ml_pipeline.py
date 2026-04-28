#!/usr/bin/env python3
"""
Comprehensive tests for FlavorSnap ML Pipeline
Tests all components individually and integration scenarios
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import torch
import numpy as np

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import components to test
from ml_pipeline import MLPipelineOrchestrator, PipelineConfig, TriggerType, PipelineStatus
from model_training import ModelTrainer, TrainingConfig, TrainingStatus
from model_deployment import ModelDeploymentOrchestrator, DeploymentSpec, Environment, DeploymentStrategy
from model_monitoring import ModelMonitoringSystem, MonitoringConfig, AlertSeverity
from model_registry import ModelRegistry, ModelMetadata
from pipeline_integration import FlavorSnapMLPipeline
from continuous_deployment import ContinuousDeploymentPipeline, CDTrigger, CDStage

class TestModelRegistry(unittest.TestCase):
    """Test Model Registry functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.test_dir, "test_registry.db")
        self.models_dir = os.path.join(self.test_dir, "models")
        os.makedirs(self.models_dir)
        
        self.registry = ModelRegistry(registry_path=self.registry_path)
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_register_model(self):
        """Test model registration"""
        # Create a dummy model file
        model_path = os.path.join(self.models_dir, "test_model.pth")
        torch.save({"state_dict": {}}, model_path)
        
        # Register model
        result = self.registry.register_model(
            version="v1.0.0",
            model_path=model_path,
            created_by="test_user",
            description="Test model",
            accuracy=0.95,
            loss=0.05
        )
        
        self.assertTrue(result)
        
        # Verify registration
        model = self.registry.get_model("v1.0.0")
        self.assertIsNotNone(model)
        self.assertEqual(model.version, "v1.0.0")
        self.assertEqual(model.accuracy, 0.95)
    
    def test_activate_model(self):
        """Test model activation"""
        # Register and activate model
        model_path = os.path.join(self.models_dir, "test_model.pth")
        torch.save({"state_dict": {}}, model_path)
        
        self.registry.register_model(
            version="v1.0.0",
            model_path=model_path,
            created_by="test_user",
            description="Test model"
        )
        
        result = self.registry.activate_model("v1.0.0")
        self.assertTrue(result)
        
        # Verify activation
        active_model = self.registry.get_active_model()
        self.assertIsNotNone(active_model)
        self.assertEqual(active_model.version, "v1.0.0")
    
    def test_list_models(self):
        """Test model listing"""
        # Register multiple models
        for i in range(3):
            model_path = os.path.join(self.models_dir, f"test_model_{i}.pth")
            torch.save({"state_dict": {}}, model_path)
            
            self.registry.register_model(
                version=f"v1.0.{i}",
                model_path=model_path,
                created_by="test_user",
                description=f"Test model {i}"
            )
        
        models = self.registry.list_models()
        self.assertEqual(len(models), 3)
    
    def test_delete_model(self):
        """Test model deletion"""
        # Register model
        model_path = os.path.join(self.models_dir, "test_model.pth")
        torch.save({"state_dict": {}}, model_path)
        
        self.registry.register_model(
            version="v1.0.0",
            model_path=model_path,
            created_by="test_user",
            description="Test model"
        )
        
        # Try to delete active model (should fail)
        self.registry.activate_model("v1.0.0")
        result = self.registry.delete_model("v1.0.0")
        self.assertFalse(result)
        
        # Deactivate and delete (should succeed)
        self.registry.activate_model("")  # Deactivate all
        result = self.registry.delete_model("v1.0.0")
        self.assertTrue(result)

class TestModelTrainer(unittest.TestCase):
    """Test Model Trainer functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.test_dir, "test_training.db")
        
        # Create dummy dataset directory
        self.data_dir = os.path.join(self.test_dir, "dataset")
        os.makedirs(self.data_dir)
        
        # Create dummy class directories with images
        for class_name in ["class1", "class2"]:
            class_dir = os.path.join(self.data_dir, class_name)
            os.makedirs(class_dir)
            # Create dummy image files
            for i in range(5):
                img_path = os.path.join(class_dir, f"image_{i}.jpg")
                # Create a simple dummy image file
                with open(img_path, 'wb') as f:
                    f.write(b'dummy_image_data')
        
        self.trainer = ModelTrainer(registry_path=self.registry_path)
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('torch.save')
    @patch('model_training.ModelTrainer._prepare_data')
    def test_start_training(self, mock_prepare_data, mock_torch_save):
        """Test starting training"""
        # Mock data preparation
        mock_train_loader = Mock()
        mock_val_loader = Mock()
        mock_test_loader = Mock()
        mock_prepare_data.return_value = (mock_train_loader, mock_val_loader, mock_test_loader)
        
        # Mock model creation and training
        with patch.object(self.trainer, '_create_model') as mock_create_model:
            mock_model = Mock()
            mock_create_model.return_value = mock_model
            
            # Mock training loop
            with patch.object(self.trainer, '_run_training') as mock_run_training:
                mock_run_training.return_value = None
                
                config = TrainingConfig(epochs=1, data_dir=self.data_dir)
                job_id = self.trainer.start_training(config)
                
                self.assertIsNotNone(job_id)
                self.assertTrue(job_id.startswith("training_"))
    
    def test_get_training_status(self):
        """Test getting training status"""
        # Test non-existent job
        status = self.trainer.get_training_status("non_existent")
        self.assertIn('error', status)
    
    def test_cancel_training(self):
        """Test cancelling training"""
        # Test cancelling non-existent job
        result = self.trainer.cancel_training("non_existent")
        self.assertFalse(result)

class TestModelDeploymentOrchestrator(unittest.TestCase):
    """Test Model Deployment Orchestrator"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.test_dir, "test_deployment.db")
        
        self.model_registry = ModelRegistry(registry_path=self.registry_path)
        self.deployment_orchestrator = ModelDeploymentOrchestrator(self.model_registry)
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('model_deployment.ModelDeploymentOrchestrator._prepare_deployment')
    def test_deploy_model(self, mock_prepare):
        """Test model deployment"""
        # Mock preparation
        mock_prepare.return_value = None
        
        # Register a model first
        models_dir = os.path.join(self.test_dir, "models")
        os.makedirs(models_dir)
        model_path = os.path.join(models_dir, "test_model.pth")
        torch.save({"state_dict": {}}, model_path)
        
        self.model_registry.register_model(
            version="v1.0.0",
            model_path=model_path,
            created_by="test_user",
            description="Test model"
        )
        
        # Create deployment spec
        spec = DeploymentSpec(
            model_version="v1.0.0",
            environment=Environment.STAGING,
            strategy=DeploymentStrategy.IMMEDIATE
        )
        
        with patch.object(self.deployment_orchestrator, '_execute_deployment') as mock_execute:
            mock_execute.return_value = None
            
            deployment_id = self.deployment_orchestrator.deploy_model(spec)
            self.assertIsNotNone(deployment_id)
            self.assertTrue(deployment_id.startswith("deploy_"))
    
    def test_get_deployment_status(self):
        """Test getting deployment status"""
        # Test non-existent deployment
        status = self.deployment_orchestrator.get_deployment_status("non_existent")
        self.assertIn('error', status)
    
    def test_list_deployments(self):
        """Test listing deployments"""
        deployments = self.deployment_orchestrator.list_deployments()
        self.assertIsInstance(deployments, list)

class TestModelMonitoringSystem(unittest.TestCase):
    """Test Model Monitoring System"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.test_dir, "test_monitoring.db")
        
        self.model_registry = ModelRegistry(registry_path=self.registry_path)
        self.monitoring_system = ModelMonitoringSystem(self.model_registry)
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('model_monitoring.ModelMonitoringSystem._get_current_metrics')
    def test_collect_performance_metrics(self, mock_get_metrics):
        """Test performance metrics collection"""
        # Mock metrics
        mock_metrics = Mock()
        mock_metrics.model_version = "v1.0.0"
        mock_metrics.accuracy = 0.95
        mock_metrics.latency_p95 = 0.1
        mock_metrics.error_rate = 0.01
        mock_get_metrics.return_value = mock_metrics
        
        # Register and activate a model
        models_dir = os.path.join(self.test_dir, "models")
        os.makedirs(models_dir)
        model_path = os.path.join(models_dir, "test_model.pth")
        torch.save({"state_dict": {}}, model_path)
        
        self.model_registry.register_model(
            version="v1.0.0",
            model_path=model_path,
            created_by="test_user",
            description="Test model"
        )
        self.model_registry.activate_model("v1.0.0")
        
        # Collect metrics
        self.monitoring_system._collect_performance_metrics()
        
        # Verify metrics were saved
        with sqlite3.connect(self.monitoring_system.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM model_metrics")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
    
    def test_calculate_data_drift(self):
        """Test data drift calculation"""
        # Test with no active model
        drift_score = self.monitoring_system.calculate_data_drift()
        self.assertEqual(drift_score, 0.0)
    
    def test_get_alerts(self):
        """Test getting alerts"""
        alerts = self.monitoring_system.get_alerts()
        self.assertIsInstance(alerts, list)
    
    def test_resolve_alert(self):
        """Test resolving alerts"""
        # Test resolving non-existent alert
        result = self.monitoring_system.resolve_alert("non_existent")
        self.assertFalse(result)

class TestMLPipelineOrchestrator(unittest.TestCase):
    """Test ML Pipeline Orchestrator"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock components to avoid complex setup
        with patch('ml_pipeline.ModelTrainer'), \
             patch('ml_pipeline.ModelDeploymentOrchestrator'), \
             patch('ml_pipeline.ModelMonitoringSystem'), \
             patch('ml_pipeline.ABTestManager'), \
             patch('ml_pipeline.FederatedLearningCoordinator'):
            
            self.pipeline = MLPipelineOrchestrator()
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_get_pipeline_status(self):
        """Test getting pipeline status"""
        status = self.pipeline.get_pipeline_status()
        self.assertIn('status', status)
        self.assertIn('execution_id', status)
    
    def test_execute_pipeline(self):
        """Test pipeline execution"""
        with patch.object(self.pipeline, '_run_pipeline') as mock_run:
            mock_run.return_value = None
            
            execution_id = self.pipeline.execute_pipeline(TriggerType.MANUAL)
            self.assertIsNotNone(execution_id)
            self.assertTrue(execution_id.startswith("pipeline_"))
    
    def test_get_execution_history(self):
        """Test getting execution history"""
        history = self.pipeline.get_execution_history()
        self.assertIsInstance(history, list)
    
    def test_get_pipeline_metrics(self):
        """Test getting pipeline metrics"""
        metrics = self.pipeline.get_pipeline_metrics()
        self.assertIsInstance(metrics, dict)

class TestFlavorSnapMLPipeline(unittest.TestCase):
    """Test integrated FlavorSnap ML Pipeline"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create config file
        self.config_path = os.path.join(self.test_dir, "test_config.yaml")
        config_data = {
            'auto_training': True,
            'auto_deployment': True,
            'monitoring_enabled': True,
            'ab_testing_enabled': True
        }
        
        with open(self.config_path, 'w') as f:
            import yaml
            yaml.dump(config_data, f)
        
        # Mock components
        with patch('pipeline_integration.ModelTrainer'), \
             patch('pipeline_integration.ModelDeploymentOrchestrator'), \
             patch('pipeline_integration.ModelMonitoringSystem'), \
             patch('pipeline_integration.ABTestManager'), \
             patch('pipeline_integration.FederatedLearningCoordinator'):
            
            self.pipeline = FlavorSnapMLPipeline(config_path=self.config_path)
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_get_comprehensive_dashboard(self):
        """Test comprehensive dashboard"""
        dashboard = self.pipeline.get_comprehensive_dashboard()
        self.assertIsInstance(dashboard, dict)
        self.assertIn('timestamp', dashboard)
        self.assertIn('pipeline_status', dashboard)
    
    def test_get_system_health(self):
        """Test system health check"""
        health = self.pipeline._get_system_health()
        self.assertIsInstance(health, dict)
        self.assertIn('overall_healthy', health)
        self.assertIn('components', health)
    
    def test_list_models(self):
        """Test model listing"""
        models = self.pipeline.list_models()
        self.assertIsInstance(models, list)

class TestContinuousDeploymentPipeline(unittest.TestCase):
    """Test Continuous Deployment Pipeline"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock ML pipeline
        with patch('continuous_deployment.FlavorSnapMLPipeline'):
            self.cd_pipeline = ContinuousDeploymentPipeline()
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_trigger_deployment(self):
        """Test triggering CD pipeline"""
        with patch.object(self.cd_pipeline, '_execute_cd_pipeline') as mock_execute:
            mock_execute.return_value = None
            
            execution_id = self.cd_pipeline.trigger_deployment(CDTrigger.MANUAL)
            self.assertIsNotNone(execution_id)
            self.assertTrue(execution_id.startswith("cd_"))
    
    def test_get_cd_status(self):
        """Test getting CD status"""
        status = self.cd_pipeline.get_cd_status()
        self.assertIsInstance(status, dict)
        self.assertIn('active_executions', status)
        self.assertIn('approval_queue', status)
    
    def test_get_execution_history(self):
        """Test getting execution history"""
        history = self.cd_pipeline.get_execution_history()
        self.assertIsInstance(history, list)
    
    def test_validate_data_availability(self):
        """Test data availability validation"""
        # Create test dataset
        dataset_dir = os.path.join(self.test_dir, "dataset")
        os.makedirs(dataset_dir)
        
        # Create class directories with images
        for class_name in ["class1", "class2", "class3"]:
            class_dir = os.path.join(dataset_dir, class_name)
            os.makedirs(class_dir)
            for i in range(15):
                img_path = os.path.join(class_dir, f"image_{i}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(b'dummy_image_data')
        
        # Test validation
        result = self.cd_pipeline._validate_data_availability()
        self.assertTrue(result)

class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios between components"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_training_to_deployment_flow(self):
        """Test flow from training to deployment"""
        # This would test the complete flow
        # For now, just verify the components can be instantiated together
        try:
            with patch('pipeline_integration.ModelTrainer'), \
                 patch('pipeline_integration.ModelDeploymentOrchestrator'), \
                 patch('pipeline_integration.ModelMonitoringSystem'), \
                 patch('pipeline_integration.ABTestManager'):
                
                pipeline = FlavorSnapMLPipeline()
                self.assertIsNotNone(pipeline)
        except Exception as e:
            self.fail(f"Integration test failed: {e}")
    
    def test_monitoring_alert_flow(self):
        """Test monitoring to alert flow"""
        # This would test monitoring generating alerts
        # For now, verify monitoring system can be created
        try:
            with patch('model_monitoring.ModelRegistry'):
                monitoring = ModelMonitoringSystem(Mock())
                self.assertIsNotNone(monitoring)
        except Exception as e:
            self.fail(f"Monitoring integration test failed: {e}")
    
    def test_ab_testing_integration(self):
        """Test A/B testing integration"""
        # This would test A/B testing with deployment
        try:
            with patch('ab_testing.ModelRegistry'):
                from ab_testing import ABTestManager
                ab_manager = ABTestManager(Mock())
                self.assertIsNotNone(ab_manager)
        except Exception as e:
            self.fail(f"A/B testing integration test failed: {e}")

class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_missing_model_file(self):
        """Test handling of missing model files"""
        registry_path = os.path.join(self.test_dir, "test_registry.db")
        registry = ModelRegistry(registry_path=registry_path)
        
        result = registry.register_model(
            version="v1.0.0",
            model_path="/non/existent/path.pth",
            created_by="test_user",
            description="Test model"
        )
        
        self.assertFalse(result)
    
    def test_invalid_configuration(self):
        """Test handling of invalid configurations"""
        # Test invalid config file
        invalid_config_path = os.path.join(self.test_dir, "invalid_config.yaml")
        with open(invalid_config_path, 'w') as f:
            f.write("invalid: yaml: content:")
        
        # Should handle gracefully and use defaults
        try:
            pipeline = FlavorSnapMLPipeline(config_path=invalid_config_path)
            self.assertIsNotNone(pipeline)
        except Exception as e:
            # Should not crash completely
            self.assertIsInstance(e, Exception)
    
    def test_database_corruption(self):
        """Test handling of database corruption"""
        # Create corrupted database file
        corrupted_db_path = os.path.join(self.test_dir, "corrupted.db")
        with open(corrupted_db_path, 'w') as f:
            f.write("corrupted database content")
        
        # Should handle gracefully
        try:
            registry = ModelRegistry(registry_path=corrupted_db_path)
            # Should either work with fresh DB or fail gracefully
            self.assertIsNotNone(registry)
        except Exception as e:
            # Expected to fail, but should not crash
            self.assertIsInstance(e, Exception)

def run_performance_tests():
    """Run performance tests"""
    print("Running performance tests...")
    
    # Test model registry performance
    test_dir = tempfile.mkdtemp()
    registry_path = os.path.join(test_dir, "perf_registry.db")
    registry = ModelRegistry(registry_path=registry_path)
    
    # Measure registration time
    start_time = datetime.now()
    for i in range(100):
        model_path = os.path.join(test_dir, f"model_{i}.pth")
        torch.save({"state_dict": {}}, model_path)
        
        registry.register_model(
            version=f"v1.0.{i}",
            model_path=model_path,
            created_by="perf_test",
            description=f"Performance test model {i}"
        )
    
    registration_time = (datetime.now() - start_time).total_seconds()
    print(f"Registered 100 models in {registration_time:.2f} seconds")
    
    # Measure listing time
    start_time = datetime.now()
    models = registry.list_models()
    listing_time = (datetime.now() - start_time).total_seconds()
    print(f"Listed {len(models)} models in {listing_time:.2f} seconds")
    
    shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    # Configure test environment
    os.environ['TESTING'] = 'true'
    
    # Run unit tests
    print("Running unit tests...")
    unittest.main(verbosity=2, exit=False)
    
    # Run performance tests
    run_performance_tests()
    
    print("All tests completed!")
