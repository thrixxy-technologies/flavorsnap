#!/usr/bin/env python3
"""
Integration script for FlavorSnap ML Pipeline
Integrates all ML components and provides unified interface
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import all ML components
from ml_pipeline import MLPipelineOrchestrator, PipelineConfig, TriggerType
from model_training import ModelTrainer, TrainingConfig
from model_deployment import ModelDeploymentOrchestrator, DeploymentSpec, Environment, DeploymentStrategy
from model_monitoring import ModelMonitoringSystem, MonitoringConfig
from model_registry import ModelRegistry
from ab_testing import ABTestManager
from federated_training import FederatedLearningCoordinator, FederatedConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlavorSnapMLPipeline:
    """Unified ML Pipeline for FlavorSnap"""
    
    def __init__(self, config_path: str = "pipeline_config.yaml"):
        """Initialize the complete ML pipeline"""
        self.config_path = config_path
        
        # Initialize core components
        self.model_registry = ModelRegistry()
        
        # Initialize pipeline orchestrator
        self.pipeline_config = self._load_pipeline_config()
        self.pipeline_orchestrator = MLPipelineOrchestrator(
            config=self.pipeline_config,
            config_path=config_path
        )
        
        # Initialize individual components
        self.trainer = ModelTrainer()
        self.deployment_orchestrator = ModelDeploymentOrchestrator(self.model_registry)
        self.monitoring_system = ModelMonitoringSystem(
            self.model_registry,
            config=self._load_monitoring_config()
        )
        self.ab_test_manager = ABTestManager(self.model_registry)
        
        # Initialize federated learning if enabled
        self.federated_coordinator = None
        if self.pipeline_config.federated_learning_enabled:
            federated_config = FederatedConfig(
                min_participants=self.pipeline_config.min_participants
            )
            self.federated_coordinator = FederatedLearningCoordinator(federated_config)
        
        logger.info("FlavorSnap ML Pipeline initialized successfully")
    
    def _load_pipeline_config(self) -> PipelineConfig:
        """Load pipeline configuration"""
        if os.path.exists(self.config_path):
            try:
                import yaml
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                return PipelineConfig(**config_data)
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        return PipelineConfig()
    
    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration"""
        return MonitoringConfig()
    
    # Pipeline Management Methods
    def execute_full_pipeline(self, trigger_type: TriggerType = TriggerType.MANUAL) -> str:
        """Execute the complete ML pipeline"""
        return self.pipeline_orchestrator.execute_pipeline(trigger_type)
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return self.pipeline_orchestrator.get_pipeline_status()
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        return self.pipeline_orchestrator.get_pipeline_metrics()
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pipeline execution history"""
        return self.pipeline_orchestrator.get_execution_history(limit)
    
    # Training Methods
    def start_training(self, training_config: TrainingConfig = None) -> str:
        """Start model training"""
        if training_config is None:
            training_config = TrainingConfig()
        return self.trainer.start_training(training_config)
    
    def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """Get training job status"""
        return self.trainer.get_training_status(job_id)
    
    def list_training_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List training jobs"""
        return self.trainer.list_training_jobs(limit)
    
    def cancel_training(self, job_id: str) -> bool:
        """Cancel training job"""
        return self.trainer.cancel_training(job_id)
    
    # Deployment Methods
    def deploy_model(self, model_version: str, environment: Environment = Environment.PRODUCTION,
                    strategy: DeploymentStrategy = DeploymentStrategy.IMMEDIATE) -> str:
        """Deploy model to specified environment"""
        spec = DeploymentSpec(
            model_version=model_version,
            environment=environment,
            strategy=strategy,
            auto_rollback=True
        )
        return self.deployment_orchestrator.deploy_model(spec)
    
    def deploy_to_staging(self, model_version: str) -> bool:
        """Deploy model to staging"""
        return self.deployment_orchestrator.deploy_to_staging(model_version)
    
    def canary_deploy(self, model_version: str) -> bool:
        """Perform canary deployment"""
        return self.deployment_orchestrator.canary_deploy(model_version)
    
    def blue_green_deploy(self, model_version: str) -> bool:
        """Perform blue-green deployment"""
        return self.deployment_orchestrator.blue_green_deploy(model_version)
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        return self.deployment_orchestrator.get_deployment_status(deployment_id)
    
    def list_deployments(self, environment: Environment = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List deployments"""
        return self.deployment_orchestrator.list_deployments(environment, limit)
    
    def rollback_model(self, target_version: str, reason: str = "") -> bool:
        """Rollback to previous model version"""
        return self.pipeline_orchestrator.rollback_model(target_version, reason)
    
    # Monitoring Methods
    def get_model_performance(self, model_version: str, time_window: int = 24) -> Dict[str, Any]:
        """Get model performance metrics"""
        return self.monitoring_system.get_model_performance(model_version, time_window)
    
    def get_alerts(self, model_version: str = None, resolved: bool = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get monitoring alerts"""
        return self.monitoring_system.get_alerts(model_version, resolved, limit)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve monitoring alert"""
        return self.monitoring_system.resolve_alert(alert_id)
    
    def calculate_data_drift(self, model_version: str = None) -> float:
        """Calculate data drift score"""
        return self.monitoring_system.calculate_data_drift(model_version)
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        return self.monitoring_system.get_monitoring_dashboard()
    
    # A/B Testing Methods
    def create_ab_test(self, model_a_version: str, model_b_version: str,
                      traffic_split: float = 0.5, description: str = "") -> str:
        """Create A/B test"""
        return self.ab_test_manager.create_test(
            model_a_version, model_b_version, traffic_split, description
        )
    
    def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get A/B test results"""
        return self.ab_test_manager.get_test_results(test_id)
    
    def list_ab_tests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List A/B tests"""
        return self.ab_test_manager.list_tests(limit)
    
    def complete_ab_test(self, test_id: str, winner: str = None) -> bool:
        """Complete A/B test and declare winner"""
        return self.ab_test_manager.complete_test(test_id, winner)
    
    # Model Registry Methods
    def list_models(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List registered models"""
        models = self.model_registry.list_models()
        if not include_inactive:
            models = [m for m in models if m.is_active]
        return [self._model_to_dict(m) for m in models]
    
    def get_model_details(self, version: str) -> Dict[str, Any]:
        """Get model details"""
        model = self.model_registry.get_model(version)
        return self._model_to_dict(model) if model else None
    
    def get_active_model(self) -> Dict[str, Any]:
        """Get currently active model"""
        model = self.model_registry.get_active_model()
        return self._model_to_dict(model) if model else None
    
    def activate_model(self, version: str) -> bool:
        """Activate model version"""
        return self.model_registry.activate_model(version)
    
    def deactivate_model(self, version: str) -> bool:
        """Deactivate model version"""
        return self.model_registry.deactivate_model(version)
    
    def _model_to_dict(self, model) -> Dict[str, Any]:
        """Convert model metadata to dictionary"""
        if not model:
            return None
        
        return {
            'version': model.version,
            'model_path': model.model_path,
            'created_at': model.created_at,
            'created_by': model.created_by,
            'description': model.description,
            'accuracy': model.accuracy,
            'loss': model.loss,
            'epochs_trained': model.epochs_trained,
            'dataset_version': model.dataset_version,
            'model_hash': model.model_hash,
            'is_active': model.is_active,
            'is_stable': model.is_stable,
            'tags': model.tags,
            'hyperparameters': model.hyperparameters
        }
    
    # Federated Learning Methods
    def start_federated_training(self, num_rounds: int = 10) -> str:
        """Start federated learning training"""
        if not self.federated_coordinator:
            raise ValueError("Federated learning is not enabled")
        return self.federated_coordinator.start_federated_training(num_rounds)
    
    def register_federated_participant(self, participant_id: str, address: str,
                                     data_size: int, computation_power: float) -> bool:
        """Register federated learning participant"""
        if not self.federated_coordinator:
            raise ValueError("Federated learning is not enabled")
        return self.federated_coordinator.register_participant(
            participant_id, address, data_size, computation_power
        )
    
    def get_federated_training_status(self) -> Dict[str, Any]:
        """Get federated learning status"""
        if not self.federated_coordinator:
            return {"error": "Federated learning is not enabled"}
        return {
            'status': self.federated_coordinator.training_status.value,
            'current_round': self.federated_coordinator.current_round,
            'participants': len(self.federated_coordinator.participants)
        }
    
    # Comprehensive Dashboard Methods
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive ML pipeline dashboard"""
        try:
            # Get pipeline status
            pipeline_status = self.get_pipeline_status()
            
            # Get active model
            active_model = self.get_active_model()
            
            # Get recent metrics
            model_performance = None
            if active_model:
                model_performance = self.get_model_performance(active_model['version'])
            
            # Get recent alerts
            recent_alerts = self.get_alerts(resolved=False, limit=5)
            
            # Get recent deployments
            recent_deployments = self.list_deployments(limit=5)
            
            # Get recent training jobs
            recent_training = self.list_training_jobs(limit=5)
            
            # Get A/B tests
            active_ab_tests = self.ab_test_manager.active_tests
            
            # Get federated learning status
            federated_status = self.get_federated_training_status()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'pipeline_status': pipeline_status,
                'active_model': active_model,
                'model_performance': model_performance,
                'recent_alerts': recent_alerts,
                'recent_deployments': recent_deployments,
                'recent_training': recent_training,
                'active_ab_tests': list(active_ab_tests.values()),
                'federated_learning': federated_status,
                'system_health': self._get_system_health()
            }
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive dashboard: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            health_checks = {
                'model_registry': self._check_model_registry_health(),
                'training_system': self._check_training_system_health(),
                'deployment_system': self._check_deployment_system_health(),
                'monitoring_system': self._check_monitoring_system_health(),
                'ab_testing': self._check_ab_testing_health()
            }
            
            overall_health = all(check['healthy'] for check in health_checks.values())
            
            return {
                'overall_healthy': overall_health,
                'components': health_checks
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'overall_healthy': False, 'error': str(e)}
    
    def _check_model_registry_health(self) -> Dict[str, Any]:
        """Check model registry health"""
        try:
            # Try to list models
            models = self.model_registry.list_models()
            return {'healthy': True, 'model_count': len(models)}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _check_training_system_health(self) -> Dict[str, Any]:
        """Check training system health"""
        try:
            # Try to get training jobs
            jobs = self.trainer.list_training_jobs(limit=1)
            return {'healthy': True, 'active_jobs': len(jobs)}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _check_deployment_system_health(self) -> Dict[str, Any]:
        """Check deployment system health"""
        try:
            # Try to get deployments
            deployments = self.deployment_orchestrator.list_deployments(limit=1)
            return {'healthy': True, 'deployment_count': len(deployments)}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _check_monitoring_system_health(self) -> Dict[str, Any]:
        """Check monitoring system health"""
        try:
            # Try to get alerts
            alerts = self.monitoring_system.get_alerts(limit=1)
            return {'healthy': True, 'alert_count': len(alerts)}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _check_ab_testing_health(self) -> Dict[str, Any]:
        """Check A/B testing health"""
        try:
            # Try to get A/B tests
            tests = self.ab_test_manager.list_tests(limit=1)
            return {'healthy': True, 'test_count': len(tests)}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    # Configuration Management
    def update_pipeline_config(self, config_updates: Dict[str, Any]) -> bool:
        """Update pipeline configuration"""
        try:
            import yaml
            
            # Load current config
            current_config = self._load_pipeline_config()
            
            # Update with new values
            config_dict = current_config.__dict__
            config_dict.update(config_updates)
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            # Reload config
            self.pipeline_config = PipelineConfig(**config_dict)
            
            logger.info("Pipeline configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update pipeline config: {e}")
            return False
    
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get current pipeline configuration"""
        return self.pipeline_config.__dict__

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap ML Pipeline Integration")
    parser.add_argument("--dashboard", action="store_true", help="Show comprehensive dashboard")
    parser.add_argument("--execute", action="store_true", help="Execute full pipeline")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--metrics", action="store_true", help="Show pipeline metrics")
    parser.add_argument("--health", action="store_true", help="Check system health")
    parser.add_argument("--config", type=str, help="Configuration file path")
    
    # Training commands
    parser.add_argument("--train", action="store_true", help="Start training")
    parser.add_argument("--training-status", type=str, help="Get training status")
    
    # Deployment commands
    parser.add_argument("--deploy", type=str, help="Deploy model version")
    parser.add_argument("--staging", type=str, help="Deploy to staging")
    parser.add_argument("--canary", type=str, help="Canary deploy model")
    parser.add_argument("--rollback", type=str, help="Rollback model version")
    
    # Monitoring commands
    parser.add_argument("--performance", type=str, help="Get model performance")
    parser.add_argument("--alerts", action="store_true", help="Show alerts")
    parser.add_argument("--drift", type=str, help="Calculate data drift")
    
    # A/B testing commands
    parser.add_argument("--ab-test", nargs=2, metavar=('MODEL_A', 'MODEL_B'), help="Create A/B test")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = FlavorSnapMLPipeline(args.config if args.config else "pipeline_config.yaml")
    
    if args.dashboard:
        dashboard = pipeline.get_comprehensive_dashboard()
        print(json.dumps(dashboard, indent=2))
    
    elif args.execute:
        execution_id = pipeline.execute_full_pipeline()
        print(f"Pipeline execution started: {execution_id}")
    
    elif args.status:
        status = pipeline.get_pipeline_status()
        print(json.dumps(status, indent=2))
    
    elif args.metrics:
        metrics = pipeline.get_pipeline_metrics()
        print(json.dumps(metrics, indent=2))
    
    elif args.health:
        health = pipeline._get_system_health()
        print(json.dumps(health, indent=2))
    
    elif args.train:
        job_id = pipeline.start_training()
        print(f"Training started: {job_id}")
    
    elif args.training_status:
        status = pipeline.get_training_status(args.training_status)
        print(json.dumps(status, indent=2))
    
    elif args.deploy:
        deployment_id = pipeline.deploy_model(args.deploy)
        print(f"Deployment started: {deployment_id}")
    
    elif args.staging:
        success = pipeline.deploy_to_staging(args.staging)
        print(f"Staging deployment {'successful' if success else 'failed'}")
    
    elif args.canary:
        success = pipeline.canary_deploy(args.canary)
        print(f"Canary deployment {'successful' if success else 'failed'}")
    
    elif args.rollback:
        success = pipeline.rollback_model(args.rollback)
        print(f"Rollback {'successful' if success else 'failed'}")
    
    elif args.performance:
        performance = pipeline.get_model_performance(args.performance)
        print(json.dumps(performance, indent=2))
    
    elif args.alerts:
        alerts = pipeline.get_alerts()
        print(json.dumps(alerts, indent=2))
    
    elif args.drift:
        drift_score = pipeline.calculate_data_drift(args.drift)
        print(f"Data drift score: {drift_score:.3f}")
    
    elif args.ab_test:
        test_id = pipeline.create_ab_test(args.ab_test[0], args.ab_test[1])
        print(f"A/B test created: {test_id}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
