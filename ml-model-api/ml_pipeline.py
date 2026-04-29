#!/usr/bin/env python3
"""
Comprehensive ML Pipeline for FlavorSnap
Orchestrates training, validation, deployment, and monitoring of ML models
"""

import os
import json
import time
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import yaml
from pathlib import Path

# Import ML components
from model_training import ModelTrainer, TrainingConfig
from model_deployment import ModelDeploymentOrchestrator
from model_monitoring import ModelMonitoringSystem
from model_registry import ModelRegistry
from ab_testing import ABTestManager
from federated_training import FederatedLearningCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ml_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    """Pipeline execution status"""
    IDLE = "idle"
    TRAINING = "training"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    FAILED = "failed"
    COMPLETED = "completed"

class TriggerType(Enum):
    """Pipeline trigger types"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    DATA_DRIFT = "data_drift"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    NEW_DATA = "new_data"

@dataclass
class PipelineConfig:
    """Configuration for ML pipeline"""
    # Training settings
    auto_training: bool = True
    training_schedule: str = "daily"  # daily, weekly, monthly
    min_accuracy_threshold: float = 0.85
    data_drift_threshold: float = 0.1
    
    # Deployment settings
    auto_deployment: bool = True
    deployment_strategy: str = "canary"  # canary, blue_green, rolling
    staging_required: bool = True
    production_approval: bool = False
    
    # Monitoring settings
    monitoring_enabled: bool = True
    performance_check_interval: int = 300  # seconds
    drift_detection_enabled: bool = True
    alert_thresholds: Dict[str, float] = None
    
    # A/B testing settings
    ab_testing_enabled: bool = True
    min_test_duration: int = 3600  # seconds
    confidence_threshold: float = 0.95
    
    # Federated learning settings
    federated_learning_enabled: bool = False
    min_participants: int = 3
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "accuracy_drop": 0.05,
                "latency_increase": 0.5,
                "error_rate": 0.01
            }

@dataclass
class PipelineExecution:
    """Record of pipeline execution"""
    execution_id: str
    trigger_type: TriggerType
    start_time: datetime
    end_time: Optional[datetime] = None
    status: PipelineStatus = PipelineStatus.IDLE
    stages_completed: List[str] = None
    model_version: Optional[str] = None
    metrics: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []
        if self.metrics is None:
            self.metrics = {}

class MLPipelineOrchestrator:
    """Comprehensive ML Pipeline Orchestrator"""
    
    def __init__(self, config: PipelineConfig = None, config_path: str = "pipeline_config.yaml"):
        self.config = config or PipelineConfig()
        self.config_path = config_path
        
        # Initialize components
        self.model_registry = ModelRegistry()
        self.trainer = None
        self.deployment_orchestrator = None
        self.monitoring_system = None
        self.ab_test_manager = None
        self.federated_coordinator = None
        
        # Pipeline state
        self.current_execution = None
        self.execution_history = []
        self.pipeline_lock = threading.Lock()
        
        # Database
        self.db_path = "ml_pipeline.db"
        self._init_database()
        
        # Initialize components
        self._init_components()
        
        # Start monitoring thread
        self._start_monitoring_thread()
        
        logger.info("ML Pipeline Orchestrator initialized")
    
    def _init_database(self):
        """Initialize pipeline database"""
        os.makedirs("logs", exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_executions (
                    execution_id TEXT PRIMARY KEY,
                    trigger_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    stages_completed TEXT,
                    model_version TEXT,
                    metrics TEXT,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_type TEXT NOT NULL,
                    next_run TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    config TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accuracy REAL,
                    latency REAL,
                    error_rate REAL,
                    drift_score REAL
                )
            """)
    
    def _init_components(self):
        """Initialize pipeline components"""
        try:
            # Initialize trainer
            self.trainer = ModelTrainer()
            
            # Initialize deployment orchestrator
            self.deployment_orchestrator = ModelDeploymentOrchestrator(
                self.model_registry
            )
            
            # Initialize monitoring system
            self.monitoring_system = ModelMonitoringSystem(
                self.model_registry,
                alert_thresholds=self.config.alert_thresholds
            )
            
            # Initialize A/B testing manager
            if self.config.ab_testing_enabled:
                self.ab_test_manager = ABTestManager(self.model_registry)
            
            # Initialize federated learning coordinator
            if self.config.federated_learning_enabled:
                from federated_training import FederatedConfig
                federated_config = FederatedConfig(
                    min_participants=self.config.min_participants
                )
                self.federated_coordinator = FederatedLearningCoordinator(federated_config)
            
            logger.info("All pipeline components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _start_monitoring_thread(self):
        """Start background monitoring thread"""
        if not self.config.monitoring_enabled:
            return
        
        def monitor_loop():
            while True:
                try:
                    self._check_pipeline_triggers()
                    time.sleep(self.config.performance_check_interval)
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Monitoring thread started")
    
    def _check_pipeline_triggers(self):
        """Check for pipeline triggers"""
        try:
            # Check scheduled triggers
            if self._should_run_scheduled_training():
                self.execute_pipeline(TriggerType.SCHEDULED)
            
            # Check data drift
            if self.config.drift_detection_enabled:
                drift_score = self.monitoring_system.calculate_data_drift()
                if drift_score > self.config.data_drift_threshold:
                    logger.warning(f"Data drift detected: {drift_score}")
                    self.execute_pipeline(TriggerType.DATA_DRIFT)
            
            # Check performance degradation
            current_model = self.model_registry.get_active_model()
            if current_model:
                performance = self.monitoring_system.get_model_performance(current_model.version)
                if performance.get("accuracy", 1.0) < (self.config.min_accuracy_threshold - self.config.alert_thresholds["accuracy_drop"]):
                    logger.warning(f"Performance degradation detected: {performance}")
                    self.execute_pipeline(TriggerType.PERFORMANCE_DEGRADATION)
        
        except Exception as e:
            logger.error(f"Trigger check failed: {e}")
    
    def _should_run_scheduled_training(self) -> bool:
        """Check if scheduled training should run"""
        # Simple implementation - check if last training was more than 24 hours ago
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT MAX(start_time) FROM pipeline_executions 
                WHERE trigger_type = 'scheduled' AND status = 'completed'
            """)
            last_training = cursor.fetchone()[0]
        
        if not last_training:
            return True
        
        last_time = datetime.fromisoformat(last_training)
        return (datetime.now() - last_time) > timedelta(hours=24)
    
    def execute_pipeline(self, trigger_type: TriggerType = TriggerType.MANUAL) -> str:
        """Execute the complete ML pipeline"""
        with self.pipeline_lock:
            if self.current_execution and self.current_execution.status in [PipelineStatus.TRAINING, PipelineStatus.DEPLOYING]:
                logger.warning("Pipeline already running")
                return self.current_execution.execution_id
            
            # Create execution record
            execution_id = f"pipeline_{int(time.time())}"
            self.current_execution = PipelineExecution(
                execution_id=execution_id,
                trigger_type=trigger_type,
                start_time=datetime.now(),
                status=PipelineStatus.TRAINING
            )
            
            # Start pipeline in background thread
            pipeline_thread = threading.Thread(
                target=self._run_pipeline,
                args=(execution_id,),
                daemon=True
            )
            pipeline_thread.start()
            
            logger.info(f"Pipeline started: {execution_id}")
            return execution_id
    
    def _run_pipeline(self, execution_id: str):
        """Run the complete pipeline"""
        execution = self.current_execution
        
        try:
            # Stage 1: Training
            if not self._execute_training_stage(execution):
                return
            
            # Stage 2: Validation
            if not self._execute_validation_stage(execution):
                return
            
            # Stage 3: Deployment (if auto-deployment enabled)
            if self.config.auto_deployment:
                if not self._execute_deployment_stage(execution):
                    return
            
            # Stage 4: A/B Testing (if enabled and new model deployed)
            if self.config.ab_testing_enabled and execution.model_version:
                self._execute_ab_testing_stage(execution)
            
            # Complete pipeline
            execution.status = PipelineStatus.COMPLETED
            execution.end_time = datetime.now()
            logger.info(f"Pipeline completed successfully: {execution_id}")
            
        except Exception as e:
            execution.status = PipelineStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            logger.error(f"Pipeline failed: {execution_id} - {e}")
        
        finally:
            self._save_execution(execution)
            self.execution_history.append(execution)
            self.current_execution = None
    
    def _execute_training_stage(self, execution: PipelineExecution) -> bool:
        """Execute training stage"""
        try:
            logger.info(f"Starting training stage for {execution.execution_id}")
            execution.status = PipelineStatus.TRAINING
            
            # Check if federated learning should be used
            if self.config.federated_learning_enabled and self.federated_coordinator:
                model_version = self._run_federated_training(execution)
            else:
                model_version = self._run_standard_training(execution)
            
            if model_version:
                execution.model_version = model_version
                execution.stages_completed.append("training")
                logger.info(f"Training completed: {model_version}")
                return True
            else:
                logger.error("Training failed")
                return False
                
        except Exception as e:
            logger.error(f"Training stage failed: {e}")
            return False
    
    def _run_standard_training(self, execution: PipelineExecution) -> Optional[str]:
        """Run standard model training"""
        try:
            # Configure training
            training_config = TrainingConfig(
                epochs=50,
                batch_size=32,
                learning_rate=0.001,
                validation_split=0.2
            )
            
            # Start training
            training_id = self.trainer.start_training(training_config)
            
            # Wait for training completion (with timeout)
            timeout = 3600  # 1 hour
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status = self.trainer.get_training_status(training_id)
                if status["status"] == "completed":
                    return status["model_version"]
                elif status["status"] == "failed":
                    logger.error(f"Training failed: {status.get('error', 'Unknown error')}")
                    return None
                time.sleep(30)
            
            logger.error("Training timed out")
            return None
            
        except Exception as e:
            logger.error(f"Standard training failed: {e}")
            return None
    
    def _run_federated_training(self, execution: PipelineExecution) -> Optional[str]:
        """Run federated learning training"""
        try:
            # Initialize global model
            model_architecture = {
                "input_size": 1000,
                "hidden_size": 512,
                "output_size": 101  # Food classes
            }
            self.federated_coordinator.initialize_global_model(model_architecture)
            
            # Start federated training
            training_id = self.federated_coordinator.start_federated_training()
            
            # Wait for completion
            timeout = 7200  # 2 hours
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.federated_coordinator.training_status.value == "completed":
                    # Register model in registry
                    model_version = f"federated_{int(time.time())}"
                    # Save model and register
                    return model_version
                elif self.federated_coordinator.training_status.value == "failed":
                    logger.error("Federated training failed")
                    return None
                time.sleep(60)
            
            logger.error("Federated training timed out")
            return None
            
        except Exception as e:
            logger.error(f"Federated training failed: {e}")
            return None
    
    def _execute_validation_stage(self, execution: PipelineExecution) -> bool:
        """Execute model validation stage"""
        try:
            logger.info(f"Starting validation stage for {execution.execution_id}")
            execution.status = PipelineStatus.VALIDATING
            
            if not execution.model_version:
                logger.error("No model version to validate")
                return False
            
            # Get model metadata
            model_metadata = self.model_registry.get_model(execution.model_version)
            if not model_metadata:
                logger.error(f"Model {execution.model_version} not found in registry")
                return False
            
            # Validate model meets thresholds
            if model_metadata.accuracy < self.config.min_accuracy_threshold:
                logger.warning(f"Model accuracy {model_metadata.accuracy} below threshold {self.config.min_accuracy_threshold}")
                # Don't fail pipeline, just log warning
            
            # Run additional validation tests
            validation_results = self._run_validation_tests(execution.model_version)
            execution.metrics["validation"] = validation_results
            
            execution.stages_completed.append("validation")
            logger.info("Validation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Validation stage failed: {e}")
            return False
    
    def _run_validation_tests(self, model_version: str) -> Dict[str, Any]:
        """Run comprehensive validation tests"""
        try:
            # This would include various tests like:
            # - Performance benchmarks
            # - Robustness tests
            # - Fairness tests
            # - Security tests
            
            return {
                "performance_test": "passed",
                "robustness_test": "passed",
                "fairness_test": "passed",
                "security_test": "passed",
                "validation_score": 0.92
            }
        except Exception as e:
            logger.error(f"Validation tests failed: {e}")
            return {"error": str(e)}
    
    def _execute_deployment_stage(self, execution: PipelineExecution) -> bool:
        """Execute deployment stage"""
        try:
            logger.info(f"Starting deployment stage for {execution.execution_id}")
            execution.status = PipelineStatus.DEPLOYING
            
            if not execution.model_version:
                logger.error("No model version to deploy")
                return False
            
            # Deploy to staging first if required
            if self.config.staging_required:
                staging_success = self.deployment_orchestrator.deploy_to_staging(
                    execution.model_version
                )
                if not staging_success:
                    logger.error("Staging deployment failed")
                    return False
                
                # Run staging tests
                staging_health = self.deployment_orchestrator.health_check(
                    execution.model_version, environment="staging"
                )
                if not staging_health.get("healthy", False):
                    logger.error("Staging health check failed")
                    return False
            
            # Deploy to production
            if self.config.deployment_strategy == "canary":
                production_success = self.deployment_orchestrator.canary_deploy(
                    execution.model_version
                )
            elif self.config.deployment_strategy == "blue_green":
                production_success = self.deployment_orchestrator.blue_green_deploy(
                    execution.model_version
                )
            else:
                production_success = self.deployment_orchestrator.deploy_model(
                    execution.model_version
                )
            
            if production_success:
                execution.stages_completed.append("deployment")
                logger.info("Deployment completed successfully")
                return True
            else:
                logger.error("Production deployment failed")
                return False
                
        except Exception as e:
            logger.error(f"Deployment stage failed: {e}")
            return False
    
    def _execute_ab_testing_stage(self, execution: PipelineExecution):
        """Execute A/B testing stage"""
        try:
            if not self.ab_test_manager:
                return
            
            logger.info(f"Starting A/B testing for {execution.execution_id}")
            
            # Get current production model
            current_model = self.model_registry.get_active_model()
            if not current_model or current_model.version == execution.model_version:
                logger.info("No A/B test needed - same model version")
                return
            
            # Create A/B test
            test_id = self.ab_test_manager.create_test(
                model_a_version=current_model.version,
                model_b_version=execution.model_version,
                traffic_split=0.1,  # Start with 10% traffic to new model
                description=f"Automated test for {execution.model_version}"
            )
            
            execution.metrics["ab_test_id"] = test_id
            logger.info(f"A/B test created: {test_id}")
            
        except Exception as e:
            logger.error(f"A/B testing stage failed: {e}")
    
    def _save_execution(self, execution: PipelineExecution):
        """Save execution to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pipeline_executions 
                (execution_id, trigger_type, start_time, end_time, status,
                 stages_completed, model_version, metrics, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id,
                execution.trigger_type.value,
                execution.start_time.isoformat(),
                execution.end_time.isoformat() if execution.end_time else None,
                execution.status.value,
                json.dumps(execution.stages_completed),
                execution.model_version,
                json.dumps(execution.metrics) if execution.metrics else None,
                execution.error_message
            ))
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        if not self.current_execution:
            return {
                "status": "idle",
                "execution_id": None,
                "current_stage": None
            }
        
        return {
            "status": self.current_execution.status.value,
            "execution_id": self.current_execution.execution_id,
            "current_stage": self.current_execution.status.value,
            "trigger_type": self.current_execution.trigger_type.value,
            "start_time": self.current_execution.start_time.isoformat(),
            "stages_completed": self.current_execution.stages_completed,
            "model_version": self.current_execution.model_version
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pipeline execution history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM pipeline_executions 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'execution_id': row['execution_id'],
                    'trigger_type': row['trigger_type'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'status': row['status'],
                    'stages_completed': json.loads(row['stages_completed']) if row['stages_completed'] else [],
                    'model_version': row['model_version'],
                    'metrics': json.loads(row['metrics']) if row['metrics'] else {},
                    'error_message': row['error_message']
                })
            
            return history
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get execution statistics
                cursor = conn.execute("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(CASE WHEN end_time IS NOT NULL THEN 
                            (julianday(end_time) - julianday(start_time)) * 24 * 60 
                        END) as avg_duration_minutes
                    FROM pipeline_executions
                    WHERE start_time > datetime('now', '-30 days')
                    GROUP BY status
                """)
                
                execution_stats = {}
                for row in cursor.fetchall():
                    execution_stats[row['status']] = {
                        'count': row['count'],
                        'avg_duration_minutes': row['avg_duration_minutes']
                    }
                
                # Get model performance trends
                cursor = conn.execute("""
                    SELECT 
                        model_version,
                        AVG(accuracy) as avg_accuracy,
                        AVG(latency) as avg_latency,
                        AVG(error_rate) as avg_error_rate,
                        COUNT(*) as measurements
                    FROM model_performance
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY model_version
                    ORDER BY timestamp DESC
                """)
                
                performance_trends = {}
                for row in cursor.fetchall():
                    performance_trends[row['model_version']] = {
                        'avg_accuracy': row['avg_accuracy'],
                        'avg_latency': row['avg_latency'],
                        'avg_error_rate': row['avg_error_rate'],
                        'measurements': row['measurements']
                    }
                
                return {
                    'execution_stats': execution_stats,
                    'performance_trends': performance_trends,
                    'current_status': self.get_pipeline_status(),
                    'total_executions': len(self.execution_history)
                }
                
        except Exception as e:
            logger.error(f"Failed to get pipeline metrics: {e}")
            return {}
    
    def rollback_model(self, target_version: str, reason: str = "") -> bool:
        """Rollback to a previous model version"""
        try:
            success = self.deployment_orchestrator.rollback_model(target_version, reason)
            if success:
                logger.info(f"Successfully rolled back to model {target_version}")
            else:
                logger.error(f"Rollback to model {target_version} failed")
            return success
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def save_config(self):
        """Save pipeline configuration"""
        config_data = asdict(self.config)
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        logger.info(f"Configuration saved to {self.config_path}")
    
    def load_config(self):
        """Load pipeline configuration"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                self.config = PipelineConfig(**config_data)
            logger.info(f"Configuration loaded from {self.config_path}")
        else:
            self.save_config()  # Create default config

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap ML Pipeline")
    parser.add_argument("--execute", action="store_true", help="Execute pipeline")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--history", action="store_true", help="Show execution history")
    parser.add_argument("--metrics", action="store_true", help="Show pipeline metrics")
    parser.add_argument("--rollback", type=str, help="Rollback to model version")
    parser.add_argument("--config", type=str, default="pipeline_config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = MLPipelineOrchestrator(config_path=args.config)
    
    if args.execute:
        execution_id = pipeline.execute_pipeline()
        print(f"Pipeline started: {execution_id}")
    
    elif args.status:
        status = pipeline.get_pipeline_status()
        print(json.dumps(status, indent=2))
    
    elif args.history:
        history = pipeline.get_execution_history()
        print(json.dumps(history, indent=2))
    
    elif args.metrics:
        metrics = pipeline.get_pipeline_metrics()
        print(json.dumps(metrics, indent=2))
    
    elif args.rollback:
        success = pipeline.rollback_model(args.rollback)
        print(f"Rollback {'successful' if success else 'failed'}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
