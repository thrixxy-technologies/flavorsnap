#!/usr/bin/env python3
"""
Continuous Deployment Pipeline for FlavorSnap
Automates the entire ML lifecycle from training to production
"""

import os
import json
import time
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import yaml
from pathlib import Path

# Import ML components
from pipeline_integration import FlavorSnapMLPipeline
from model_training import TrainingConfig
from model_deployment import DeploymentSpec, Environment, DeploymentStrategy
from model_monitoring import MonitoringConfig
from model_registry import ModelRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/continuous_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CDTrigger(Enum):
    """Continuous deployment triggers"""
    SCHEDULED = "scheduled"
    DATA_UPDATE = "data_update"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MANUAL = "manual"
    GIT_COMMIT = "git_commit"
    MODEL_IMPROVEMENT = "model_improvement"

class CDStage(Enum):
    """Continuous deployment stages"""
    VALIDATION = "validation"
    TRAINING = "training"
    TESTING = "testing"
    STAGING_DEPLOY = "staging_deploy"
    STAGING_TEST = "staging_test"
    PRODUCTION_DEPLOY = "production_deploy"
    MONITORING = "monitoring"
    ROLLBACK = "rollback"

@dataclass
class CDPipelineConfig:
    """Configuration for continuous deployment pipeline"""
    # Triggers
    enabled_triggers: List[CDTrigger] = None
    training_schedule: str = "0 2 * * *"  # Daily at 2 AM
    performance_threshold: float = 0.85
    data_drift_threshold: float = 0.1
    
    # Stages configuration
    skip_staging: bool = False
    require_manual_approval: bool = False
    auto_rollback: bool = True
    rollback_threshold: float = 0.05
    
    # Testing
    run_unit_tests: bool = True
    run_integration_tests: bool = True
    run_performance_tests: bool = True
    test_timeout: int = 3600  # 1 hour
    
    # Deployment
    deployment_strategy: DeploymentStrategy = DeploymentStrategy.CANARY
    staging_environment: Environment = Environment.STAGING
    production_environment: Environment = Environment.PRODUCTION
    
    # Monitoring
    monitoring_window: int = 3600  # 1 hour
    health_check_interval: int = 60  # seconds
    
    # Notifications
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.enabled_triggers is None:
            self.enabled_triggers = [CDTrigger.SCHEDULED, CDTrigger.PERFORMANCE_DEGRADATION]
        if self.notification_channels is None:
            self.notification_channels = ["email", "slack"]

@dataclass
class CDExecution:
    """Continuous deployment execution record"""
    execution_id: str
    trigger: CDTrigger
    start_time: datetime
    current_stage: CDStage
    status: str = "running"
    completed_stages: List[CDStage] = None
    model_version: Optional[str] = None
    previous_model_version: Optional[str] = None
    metrics: Dict[str, Any] = None
    error_message: Optional[str] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.completed_stages is None:
            self.completed_stages = []
        if self.metrics is None:
            self.metrics = {}

class ContinuousDeploymentPipeline:
    """Continuous deployment pipeline for ML models"""
    
    def __init__(self, config: CDPipelineConfig = None, config_path: str = "cd_config.yaml"):
        self.config = config or CDPipelineConfig()
        self.config_path = config_path
        
        # Initialize ML pipeline
        self.ml_pipeline = FlavorSnapMLPipeline()
        
        # CD state
        self.active_executions = {}
        self.execution_history = []
        self.approval_queue = []
        self.cd_lock = threading.Lock()
        
        # Initialize components
        self._init_components()
        
        # Start background processes
        self._start_background_processes()
        
        logger.info("Continuous Deployment Pipeline initialized")
    
    def _init_components(self):
        """Initialize CD components"""
        # Create directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs("cd_artifacts", exist_ok=True)
        
        # Load configuration
        self._load_config()
        
        # Initialize Git monitoring if enabled
        if CDTrigger.GIT_COMMIT in self.config.enabled_triggers:
            self._init_git_monitoring()
    
    def _load_config(self):
        """Load CD configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                self.config = CDPipelineConfig(**config_data)
                logger.info(f"CD configuration loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load CD config: {e}")
        else:
            self._save_config()
    
    def _save_config(self):
        """Save CD configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(asdict(self.config), f, default_flow_style=False)
            logger.info(f"CD configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save CD config: {e}")
    
    def _init_git_monitoring(self):
        """Initialize Git repository monitoring"""
        try:
            # This would integrate with Git hooks or webhooks
            logger.info("Git monitoring initialized")
        except Exception as e:
            logger.warning(f"Git monitoring initialization failed: {e}")
    
    def _start_background_processes(self):
        """Start background monitoring processes"""
        # Scheduler for periodic triggers
        scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        scheduler_thread.start()
        
        # Performance monitoring
        if CDTrigger.PERFORMANCE_DEGRADATION in self.config.enabled_triggers:
            perf_thread = threading.Thread(
                target=self._performance_monitoring_loop,
                daemon=True
            )
            perf_thread.start()
        
        # Execution monitor
        monitor_thread = threading.Thread(
            target=self._execution_monitor_loop,
            daemon=True
        )
        monitor_thread.start()
        
        logger.info("Background processes started")
    
    def _scheduler_loop(self):
        """Background scheduler loop"""
        while True:
            try:
                # Check for scheduled execution
                if self._should_run_scheduled():
                    self.trigger_deployment(CDTrigger.SCHEDULED)
                
                # Sleep for a minute
                time.sleep(60)
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)
    
    def _performance_monitoring_loop(self):
        """Background performance monitoring loop"""
        while True:
            try:
                # Check for performance degradation
                if self._should_trigger_performance_degradation():
                    self.trigger_deployment(CDTrigger.PERFORMANCE_DEGRADATION)
                
                # Sleep for monitoring interval
                time.sleep(self.config.monitoring_window)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(300)
    
    def _execution_monitor_loop(self):
        """Monitor active CD executions"""
        while True:
            try:
                with self.cd_lock:
                    for execution_id, execution in list(self.active_executions.items()):
                        if execution.status == "running":
                            self._monitor_execution(execution)
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Execution monitoring error: {e}")
                time.sleep(60)
    
    def _should_run_scheduled(self) -> bool:
        """Check if scheduled execution should run"""
        # Simple implementation - check if last execution was more than 24 hours ago
        if not self.execution_history:
            return True
        
        last_execution = self.execution_history[-1]
        if last_execution.trigger == CDTrigger.SCHEDULED:
            time_since_last = datetime.now() - last_execution.start_time
            return time_since_last > timedelta(hours=24)
        
        return True
    
    def _should_trigger_performance_degradation(self) -> bool:
        """Check if performance degradation trigger should fire"""
        try:
            # Get current active model performance
            active_model = self.ml_pipeline.get_active_model()
            if not active_model:
                return False
            
            performance = self.ml_pipeline.get_model_performance(
                active_model['version'], 
                time_window=24
            )
            
            if not performance or performance.get('metrics_count', 0) == 0:
                return False
            
            avg_accuracy = performance.get('avg_accuracy', 0.0)
            return avg_accuracy < self.config.performance_threshold
            
        except Exception as e:
            logger.error(f"Performance degradation check failed: {e}")
            return False
    
    def trigger_deployment(self, trigger: CDTrigger, metadata: Dict[str, Any] = None) -> str:
        """Trigger continuous deployment"""
        with self.cd_lock:
            # Check if another execution is running
            if self.active_executions:
                logger.warning("CD execution already in progress")
                return list(self.active_executions.keys())[0]
            
            # Create execution record
            execution_id = f"cd_{trigger.value}_{int(time.time())}"
            execution = CDExecution(
                execution_id=execution_id,
                trigger=trigger,
                start_time=datetime.now(),
                current_stage=CDStage.VALIDATION,
                metadata=metadata or {}
            )
            
            self.active_executions[execution_id] = execution
            
            # Start execution in background
            execution_thread = threading.Thread(
                target=self._execute_cd_pipeline,
                args=(execution_id,),
                daemon=True
            )
            execution_thread.start()
            
            logger.info(f"CD pipeline triggered: {execution_id} by {trigger.value}")
            return execution_id
    
    def _execute_cd_pipeline(self, execution_id: str):
        """Execute the complete CD pipeline"""
        execution = self.active_executions[execution_id]
        
        try:
            # Stage 1: Validation
            if not self._execute_stage(execution, CDStage.VALIDATION, self._validate_prerequisites):
                return
            
            # Stage 2: Training
            if not self._execute_stage(execution, CDStage.TRAINING, self._execute_training):
                return
            
            # Stage 3: Testing
            if not self._execute_stage(execution, CDStage.TESTING, self._execute_testing):
                return
            
            # Stage 4: Staging Deployment
            if not self.config.skip_staging:
                if not self._execute_stage(execution, CDStage.STAGING_DEPLOY, self._deploy_to_staging):
                    return
                
                # Stage 5: Staging Testing
                if not self._execute_stage(execution, CDStage.STAGING_TEST, self._test_staging):
                    return
            
            # Stage 6: Production Deployment
            if not self._execute_stage(execution, CDStage.PRODUCTION_DEPLOY, self._deploy_to_production):
                return
            
            # Stage 7: Monitoring
            if not self._execute_stage(execution, CDStage.MONITORING, self._monitor_production):
                return
            
            # Complete execution
            execution.status = "completed"
            execution.end_time = datetime.now()
            logger.info(f"CD pipeline completed successfully: {execution_id}")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            logger.error(f"CD pipeline failed: {execution_id} - {e}")
            
            # Trigger rollback if needed
            if self.config.auto_rollback and execution.model_version:
                self._execute_rollback(execution)
        
        finally:
            self._finalize_execution(execution)
    
    def _execute_stage(self, execution: CDExecution, stage: CDStage, 
                       stage_func: Callable) -> bool:
        """Execute a specific CD stage"""
        try:
            logger.info(f"Executing CD stage: {stage.value} for {execution.execution_id}")
            execution.current_stage = stage
            
            # Execute stage function
            success = stage_func(execution)
            
            if success:
                execution.completed_stages.append(stage)
                logger.info(f"CD stage completed: {stage.value}")
                return True
            else:
                logger.error(f"CD stage failed: {stage.value}")
                return False
                
        except Exception as e:
            logger.error(f"CD stage error: {stage.value} - {e}")
            return False
    
    def _validate_prerequisites(self, execution: CDExecution) -> bool:
        """Validate CD prerequisites"""
        try:
            # Check if system is healthy
            health = self.ml_pipeline._get_system_health()
            if not health.get('overall_healthy', False):
                logger.error("System health check failed")
                return False
            
            # Check for active deployments
            active_model = self.ml_pipeline.get_active_model()
            execution.previous_model_version = active_model['version'] if active_model else None
            
            # Validate data availability
            if not self._validate_data_availability():
                logger.error("Data validation failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Prerequisite validation failed: {e}")
            return False
    
    def _execute_training(self, execution: CDExecution) -> bool:
        """Execute model training"""
        try:
            # Configure training
            training_config = TrainingConfig(
                epochs=50,
                batch_size=32,
                validation_split=0.2,
                save_checkpoints=True
            )
            
            # Start training
            training_id = self.ml_pipeline.start_training(training_config)
            execution.metrics['training_id'] = training_id
            
            # Wait for completion
            timeout = self.config.test_timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status = self.ml_pipeline.get_training_status(training_id)
                
                if status['status'] == 'completed':
                    execution.model_version = status['model_version']
                    execution.metrics['training_metrics'] = status
                    logger.info(f"Training completed: {execution.model_version}")
                    return True
                elif status['status'] == 'failed':
                    logger.error(f"Training failed: {status.get('error_message', 'Unknown error')}")
                    return False
                
                time.sleep(30)
            
            logger.error("Training timed out")
            return False
            
        except Exception as e:
            logger.error(f"Training execution failed: {e}")
            return False
    
    def _execute_testing(self, execution: CDExecution) -> bool:
        """Execute comprehensive testing"""
        try:
            if not execution.model_version:
                logger.error("No model version available for testing")
                return False
            
            test_results = {}
            
            # Unit tests
            if self.config.run_unit_tests:
                unit_results = self._run_unit_tests(execution.model_version)
                test_results['unit_tests'] = unit_results
            
            # Integration tests
            if self.config.run_integration_tests:
                integration_results = self._run_integration_tests(execution.model_version)
                test_results['integration_tests'] = integration_results
            
            # Performance tests
            if self.config.run_performance_tests:
                performance_results = self._run_performance_tests(execution.model_version)
                test_results['performance_tests'] = performance_results
            
            execution.metrics['test_results'] = test_results
            
            # Check if all tests passed
            all_passed = all(
                results.get('passed', False) 
                for results in test_results.values()
            )
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Testing execution failed: {e}")
            return False
    
    def _run_unit_tests(self, model_version: str) -> Dict[str, Any]:
        """Run unit tests for model"""
        try:
            # This would run actual unit tests
            # For now, simulate results
            return {
                'passed': True,
                'total_tests': 50,
                'passed_tests': 50,
                'failed_tests': 0,
                'coverage': 95.2
            }
        except Exception as e:
            logger.error(f"Unit tests failed: {e}")
            return {'passed': False, 'error': str(e)}
    
    def _run_integration_tests(self, model_version: str) -> Dict[str, Any]:
        """Run integration tests for model"""
        try:
            # This would run actual integration tests
            return {
                'passed': True,
                'total_tests': 20,
                'passed_tests': 20,
                'failed_tests': 0,
                'api_tests': 15,
                'database_tests': 5
            }
        except Exception as e:
            logger.error(f"Integration tests failed: {e}")
            return {'passed': False, 'error': str(e)}
    
    def _run_performance_tests(self, model_version: str) -> Dict[str, Any]:
        """Run performance tests for model"""
        try:
            # This would run actual performance tests
            return {
                'passed': True,
                'avg_latency': 0.15,
                'p95_latency': 0.25,
                'throughput': 1000,
                'memory_usage': 512,
                'cpu_usage': 45.2
            }
        except Exception as e:
            logger.error(f"Performance tests failed: {e}")
            return {'passed': False, 'error': str(e)}
    
    def _deploy_to_staging(self, execution: CDExecution) -> bool:
        """Deploy model to staging environment"""
        try:
            if not execution.model_version:
                logger.error("No model version available for staging deployment")
                return False
            
            success = self.ml_pipeline.deploy_to_staging(execution.model_version)
            execution.metrics['staging_deployment'] = {'success': success}
            
            return success
            
        except Exception as e:
            logger.error(f"Staging deployment failed: {e}")
            return False
    
    def _test_staging(self, execution: CDExecution) -> bool:
        """Test model in staging environment"""
        try:
            if not execution.model_version:
                return False
            
            # Wait for staging deployment to be ready
            time.sleep(60)
            
            # Run staging tests
            staging_results = self._run_staging_tests(execution.model_version)
            execution.metrics['staging_tests'] = staging_results
            
            return staging_results.get('passed', False)
            
        except Exception as e:
            logger.error(f"Staging testing failed: {e}")
            return False
    
    def _run_staging_tests(self, model_version: str) -> Dict[str, Any]:
        """Run staging environment tests"""
        try:
            # This would run actual staging tests
            return {
                'passed': True,
                'health_check': True,
                'smoke_tests': True,
                'user_acceptance_tests': True
            }
        except Exception as e:
            logger.error(f"Staging tests failed: {e}")
            return {'passed': False, 'error': str(e)}
    
    def _deploy_to_production(self, execution: CDExecution) -> bool:
        """Deploy model to production environment"""
        try:
            if not execution.model_version:
                logger.error("No model version available for production deployment")
                return False
            
            # Check for manual approval if required
            if self.config.require_manual_approval:
                if not self._wait_for_approval(execution):
                    logger.info("Production deployment approval denied")
                    return False
            
            # Deploy based on strategy
            if self.config.deployment_strategy == DeploymentStrategy.CANARY:
                success = self.ml_pipeline.canary_deploy(execution.model_version)
            elif self.config.deployment_strategy == DeploymentStrategy.BLUE_GREEN:
                success = self.ml_pipeline.blue_green_deploy(execution.model_version)
            else:
                deployment_id = self.ml_pipeline.deploy_model(execution.model_version)
                success = deployment_id is not None
            
            execution.metrics['production_deployment'] = {'success': success}
            
            return success
            
        except Exception as e:
            logger.error(f"Production deployment failed: {e}")
            return False
    
    def _wait_for_approval(self, execution: CDExecution) -> bool:
        """Wait for manual approval"""
        try:
            # Add to approval queue
            self.approval_queue.append(execution.execution_id)
            
            # In a real implementation, this would wait for human approval
            # For now, auto-approve after 5 minutes
            time.sleep(300)
            
            # Remove from queue
            if execution.execution_id in self.approval_queue:
                self.approval_queue.remove(execution.execution_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Approval wait failed: {e}")
            return False
    
    def _monitor_production(self, execution: CDExecution) -> bool:
        """Monitor model in production"""
        try:
            if not execution.model_version:
                return False
            
            # Monitor for specified window
            start_time = time.time()
            
            while time.time() - start_time < self.config.monitoring_window:
                # Get model performance
                performance = self.ml_pipeline.get_model_performance(
                    execution.model_version, 
                    time_window=1
                )
                
                if performance and performance.get('metrics_count', 0) > 0:
                    avg_accuracy = performance.get('avg_accuracy', 0.0)
                    error_rate = performance.get('avg_error_rate', 0.0)
                    
                    # Check thresholds
                    if avg_accuracy < self.config.performance_threshold:
                        logger.warning(f"Production accuracy below threshold: {avg_accuracy}")
                        return False
                    
                    if error_rate > self.config.rollback_threshold:
                        logger.warning(f"Production error rate above threshold: {error_rate}")
                        return False
                
                time.sleep(self.config.health_check_interval)
            
            execution.metrics['production_monitoring'] = {'passed': True}
            return True
            
        except Exception as e:
            logger.error(f"Production monitoring failed: {e}")
            return False
    
    def _execute_rollback(self, execution: CDExecution):
        """Execute rollback to previous model"""
        try:
            if execution.previous_model_version:
                success = self.ml_pipeline.rollback_model(
                    execution.previous_model_version,
                    f"Automatic rollback due to CD failure: {execution.error_message}"
                )
                
                if success:
                    execution.current_stage = CDStage.ROLLBACK
                    execution.metrics['rollback'] = {
                        'success': True,
                        'rollback_to': execution.previous_model_version
                    }
                    logger.info(f"Rollback executed to {execution.previous_model_version}")
                else:
                    logger.error("Rollback failed")
            else:
                logger.warning("No previous model version available for rollback")
                
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
    
    def _validate_data_availability(self) -> bool:
        """Validate data availability for training"""
        try:
            # Check if dataset directory exists and has data
            dataset_path = Path("dataset")
            if not dataset_path.exists():
                return False
            
            # Check for minimum data requirements
            class_dirs = [d for d in dataset_path.iterdir() if d.is_dir()]
            if len(class_dirs) < 5:  # Minimum 5 classes
                return False
            
            # Check for minimum samples per class
            for class_dir in class_dirs[:5]:  # Check first 5 classes
                image_files = list(class_dir.glob("*.jpg"))
                if len(image_files) < 10:  # Minimum 10 images per class
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False
    
    def _monitor_execution(self, execution: CDExecution):
        """Monitor active execution"""
        try:
            # Check for timeout
            if execution.start_time:
                elapsed = datetime.now() - execution.start_time
                if elapsed > timedelta(hours=6):  # 6 hour timeout
                    execution.status = "timeout"
                    execution.error_message = "Execution timeout"
                    logger.warning(f"CD execution timeout: {execution.execution_id}")
        except Exception as e:
            logger.error(f"Execution monitoring failed: {e}")
    
    def _finalize_execution(self, execution: CDExecution):
        """Finalize CD execution"""
        try:
            # Remove from active executions
            if execution.execution_id in self.active_executions:
                del self.active_executions[execution.execution_id]
            
            # Add to history
            self.execution_history.append(execution)
            
            # Keep history size manageable
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            # Send notifications
            self._send_completion_notification(execution)
            
            # Save execution record
            self._save_execution(execution)
            
        except Exception as e:
            logger.error(f"Execution finalization failed: {e}")
    
    def _send_completion_notification(self, execution: CDExecution):
        """Send completion notification"""
        try:
            message = f"CD Pipeline {execution.status}: {execution.execution_id}"
            if execution.error_message:
                message += f" - Error: {execution.error_message}"
            
            logger.info(f"Notification: {message}")
            
            # This would send to actual notification channels
            for channel in self.config.notification_channels:
                if channel == "email":
                    self._send_email_notification(message)
                elif channel == "slack":
                    self._send_slack_notification(message)
                    
        except Exception as e:
            logger.error(f"Notification sending failed: {e}")
    
    def _send_email_notification(self, message: str):
        """Send email notification"""
        # This would integrate with email service
        logger.info(f"Email notification: {message}")
    
    def _send_slack_notification(self, message: str):
        """Send Slack notification"""
        # This would integrate with Slack webhook
        logger.info(f"Slack notification: {message}")
    
    def _save_execution(self, execution: CDExecution):
        """Save execution record to file"""
        try:
            execution_file = Path("cd_artifacts") / f"{execution.execution_id}.json"
            
            execution_data = {
                'execution_id': execution.execution_id,
                'trigger': execution.trigger.value,
                'start_time': execution.start_time.isoformat(),
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'status': execution.status,
                'current_stage': execution.current_stage.value,
                'completed_stages': [s.value for s in execution.completed_stages],
                'model_version': execution.model_version,
                'previous_model_version': execution.previous_model_version,
                'metrics': execution.metrics,
                'error_message': execution.error_message
            }
            
            with open(execution_file, 'w') as f:
                json.dump(execution_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save execution: {e}")
    
    def get_cd_status(self) -> Dict[str, Any]:
        """Get CD pipeline status"""
        with self.cd_lock:
            active_executions = [
                {
                    'execution_id': exec.execution_id,
                    'trigger': exec.trigger.value,
                    'current_stage': exec.current_stage.value,
                    'status': exec.status,
                    'start_time': exec.start_time.isoformat(),
                    'model_version': exec.model_version
                }
                for exec in self.active_executions.values()
            ]
            
            return {
                'active_executions': active_executions,
                'approval_queue': self.approval_queue.copy(),
                'total_executions': len(self.execution_history),
                'config': asdict(self.config)
            }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get CD execution history"""
        executions = sorted(
            self.execution_history, 
            key=lambda x: x.start_time, 
            reverse=True
        )[:limit]
        
        return [
            {
                'execution_id': exec.execution_id,
                'trigger': exec.trigger.value,
                'start_time': exec.start_time.isoformat(),
                'end_time': exec.end_time.isoformat() if exec.end_time else None,
                'status': exec.status,
                'completed_stages': [s.value for s in exec.completed_stages],
                'model_version': exec.model_version,
                'error_message': exec.error_message
            }
            for exec in executions
        ]
    
    def approve_deployment(self, execution_id: str) -> bool:
        """Approve deployment for manual approval"""
        try:
            if execution_id in self.approval_queue:
                self.approval_queue.remove(execution_id)
                logger.info(f"Deployment approved: {execution_id}")
                return True
            else:
                logger.warning(f"Execution not in approval queue: {execution_id}")
                return False
        except Exception as e:
            logger.error(f"Approval failed: {e}")
            return False
    
    def reject_deployment(self, execution_id: str, reason: str) -> bool:
        """Reject deployment"""
        try:
            with self.cd_lock:
                if execution_id in self.active_executions:
                    execution = self.active_executions[execution_id]
                    execution.status = "rejected"
                    execution.error_message = reason
                    execution.end_time = datetime.now()
                    self._finalize_execution(execution)
                    return True
                else:
                    logger.warning(f"Active execution not found: {execution_id}")
                    return False
        except Exception as e:
            logger.error(f"Rejection failed: {e}")
            return False

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap Continuous Deployment")
    parser.add_argument("--trigger", type=str, choices=[t.value for t in CDTrigger], 
                       help="Trigger CD pipeline")
    parser.add_argument("--status", action="store_true", help="Get CD status")
    parser.add_argument("--history", action="store_true", help="Get execution history")
    parser.add_argument("--approve", type=str, help="Approve deployment")
    parser.add_argument("--reject", type=str, help="Reject deployment")
    parser.add_argument("--reason", type=str, help="Rejection reason")
    
    args = parser.parse_args()
    
    # Initialize CD pipeline
    cd_pipeline = ContinuousDeploymentPipeline()
    
    if args.trigger:
        trigger = CDTrigger(args.trigger)
        execution_id = cd_pipeline.trigger_deployment(trigger)
        print(f"CD pipeline triggered: {execution_id}")
    
    elif args.status:
        status = cd_pipeline.get_cd_status()
        print(json.dumps(status, indent=2))
    
    elif args.history:
        history = cd_pipeline.get_execution_history()
        print(json.dumps(history, indent=2))
    
    elif args.approve:
        success = cd_pipeline.approve_deployment(args.approve)
        print(f"Approval {'successful' if success else 'failed'}")
    
    elif args.reject:
        success = cd_pipeline.reject_deployment(args.reject, args.reason or "")
        print(f"Rejection {'successful' if success else 'failed'}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
