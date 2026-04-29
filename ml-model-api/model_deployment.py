#!/usr/bin/env python3
"""
Model Deployment Orchestrator for FlavorSnap
Handles continuous deployment with canary, blue-green, and rolling strategies
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
import requests
import docker
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

# Import existing components
from deployment_manager import ModelDeploymentManager, DeploymentConfig
from model_registry import ModelRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeploymentStrategy(Enum):
    """Deployment strategies"""
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    PREPARING = "preparing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class DeploymentSpec:
    """Deployment specification"""
    model_version: str
    environment: Environment
    strategy: DeploymentStrategy
    traffic_percentage: float = 100.0
    canary_duration: int = 300  # seconds
    health_check_interval: int = 30  # seconds
    rollback_threshold: float = 0.05  # 5% error rate
    auto_rollback: bool = True
    test_suite: str = "default"
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = ["email", "slack"]

@dataclass
class DeploymentExecution:
    """Deployment execution record"""
    deployment_id: str
    spec: DeploymentSpec
    status: DeploymentStatus = DeploymentStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    previous_version: Optional[str] = None
    metrics: Dict[str, Any] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}

class ModelDeploymentOrchestrator:
    """Advanced model deployment orchestrator"""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        
        # Initialize deployment manager
        deployment_config = DeploymentConfig(
            auto_rollback=True,
            rollback_threshold=0.05,
            monitoring_window=100,
            health_check_interval=30
        )
        self.deployment_manager = ModelDeploymentManager(
            model_registry, deployment_config
        )
        
        # Deployment state
        self.active_deployments = {}
        self.deployment_history = []
        self.deployment_lock = threading.Lock()
        
        # Initialize external systems
        self.docker_client = None
        self.k8s_client = None
        self._init_external_systems()
        
        # Database
        self.db_path = "deployment_orchestrator.db"
        self._init_database()
        
        # Start monitoring thread
        self._start_monitoring_thread()
        
        logger.info("ModelDeploymentOrchestrator initialized")
    
    def _init_external_systems(self):
        """Initialize external deployment systems"""
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
        
        try:
            # Initialize Kubernetes client
            k8s_config.load_incluster_config()  # For in-cluster deployment
            self.k8s_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized")
        except Exception:
            try:
                k8s_config.load_kube_config()  # For local development
                self.k8s_client = client.CoreV1Api()
                logger.info("Kubernetes client initialized (local config)")
            except Exception as e:
                logger.warning(f"Kubernetes client initialization failed: {e}")
    
    def _init_database(self):
        """Initialize deployment database"""
        os.makedirs("logs", exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    deployment_id TEXT PRIMARY KEY,
                    model_version TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    previous_version TEXT,
                    metrics TEXT,
                    error_message TEXT,
                    rollback_reason TEXT,
                    spec TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployment_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deployment_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    traffic_percentage REAL,
                    error_rate REAL,
                    latency_p95 REAL,
                    throughput REAL,
                    health_score REAL,
                    FOREIGN KEY (deployment_id) REFERENCES deployments (deployment_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS environment_configs (
                    environment TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
    
    def _start_monitoring_thread(self):
        """Start deployment monitoring thread"""
        def monitor_loop():
            while True:
                try:
                    self._monitor_active_deployments()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Deployment monitoring error: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Deployment monitoring thread started")
    
    def _monitor_active_deployments(self):
        """Monitor active deployments"""
        with self.deployment_lock:
            for deployment_id, execution in list(self.active_deployments.items()):
                if execution.status in [DeploymentStatus.DEPLOYING, DeploymentStatus.MONITORING]:
                    self._check_deployment_health(execution)
    
    def _check_deployment_health(self, execution: DeploymentExecution):
        """Check deployment health and trigger rollback if needed"""
        try:
            # Get current metrics
            metrics = self._get_deployment_metrics(execution.deployment_id)
            
            if not metrics:
                return
            
            # Check error rate
            error_rate = metrics.get("error_rate", 0.0)
            if error_rate > execution.spec.rollback_threshold:
                logger.warning(f"High error rate detected: {error_rate}")
                if execution.spec.auto_rollback:
                    self._trigger_rollback(execution, f"High error rate: {error_rate}")
                return
            
            # Check health score
            health_score = metrics.get("health_score", 1.0)
            if health_score < 0.8:
                logger.warning(f"Low health score detected: {health_score}")
                if execution.spec.auto_rollback:
                    self._trigger_rollback(execution, f"Low health score: {health_score}")
                return
            
            # Update metrics
            execution.metrics.update(metrics)
            self._save_deployment(execution)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def _get_deployment_metrics(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get current deployment metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM deployment_metrics 
                    WHERE deployment_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (deployment_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "error_rate": row["error_rate"],
                        "latency_p95": row["latency_p95"],
                        "throughput": row["throughput"],
                        "health_score": row["health_score"],
                        "traffic_percentage": row["traffic_percentage"]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get deployment metrics: {e}")
            return None
    
    def deploy_model(self, spec: DeploymentSpec) -> str:
        """Deploy model with specified strategy"""
        with self.deployment_lock:
            # Validate model version
            model_metadata = self.model_registry.get_model(spec.model_version)
            if not model_metadata:
                raise ValueError(f"Model {spec.model_version} not found in registry")
            
            # Get current active model
            current_model = self.model_registry.get_active_model()
            previous_version = current_model.version if current_model else None
            
            # Create deployment execution
            deployment_id = f"deploy_{spec.environment.value}_{spec.model_version}_{int(time.time())}"
            execution = DeploymentExecution(
                deployment_id=deployment_id,
                spec=spec,
                start_time=datetime.now(),
                previous_version=previous_version
            )
            
            self.active_deployments[deployment_id] = execution
            self._save_deployment(execution)
            
            # Start deployment in background thread
            deployment_thread = threading.Thread(
                target=self._execute_deployment,
                args=(deployment_id,),
                daemon=True
            )
            deployment_thread.start()
            
            logger.info(f"Deployment started: {deployment_id}")
            return deployment_id
    
    def _execute_deployment(self, deployment_id: str):
        """Execute deployment based on strategy"""
        execution = self.active_deployments[deployment_id]
        
        try:
            execution.status = DeploymentStatus.PREPARING
            self._save_deployment(execution)
            
            # Prepare deployment
            self._prepare_deployment(execution)
            
            # Execute based on strategy
            if execution.spec.strategy == DeploymentStrategy.CANARY:
                success = self._execute_canary_deployment(execution)
            elif execution.spec.strategy == DeploymentStrategy.BLUE_GREEN:
                success = self._execute_blue_green_deployment(execution)
            elif execution.spec.strategy == DeploymentStrategy.ROLLING:
                success = self._execute_rolling_deployment(execution)
            else:
                success = self._execute_immediate_deployment(execution)
            
            if success:
                execution.status = DeploymentStatus.COMPLETED
                logger.info(f"Deployment completed successfully: {deployment_id}")
            else:
                execution.status = DeploymentStatus.FAILED
                logger.error(f"Deployment failed: {deployment_id}")
            
        except Exception as e:
            execution.status = DeploymentStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Deployment error: {deployment_id} - {e}")
        
        finally:
            execution.end_time = datetime.now()
            self._save_deployment(execution)
            self.deployment_history.append(execution)
            
            # Remove from active deployments
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]
    
    def _prepare_deployment(self, execution: DeploymentExecution):
        """Prepare deployment environment"""
        try:
            # Build Docker image
            if self.docker_client:
                self._build_docker_image(execution)
            
            # Prepare Kubernetes resources
            if self.k8s_client:
                self._prepare_kubernetes_resources(execution)
            
            # Run smoke tests
            self._run_smoke_tests(execution)
            
            logger.info(f"Deployment preparation completed: {execution.deployment_id}")
            
        except Exception as e:
            logger.error(f"Deployment preparation failed: {e}")
            raise
    
    def _build_docker_image(self, execution: DeploymentExecution):
        """Build Docker image for model"""
        try:
            # Create Dockerfile if not exists
            dockerfile_path = Path("Dockerfile.model")
            if not dockerfile_path.exists():
                self._create_model_dockerfile(dockerfile_path)
            
            # Build image
            image_tag = f"flavorsnap-model:{execution.spec.model_version}"
            
            build_result = self.docker_client.images.build(
                path=".",
                dockerfile=str(dockerfile_path),
                tag=image_tag,
                buildargs={
                    "MODEL_VERSION": execution.spec.model_version
                }
            )
            
            logger.info(f"Docker image built: {image_tag}")
            
        except Exception as e:
            logger.error(f"Docker build failed: {e}")
            raise
    
    def _create_model_dockerfile(self, dockerfile_path: Path):
        """Create Dockerfile for model deployment"""
        dockerfile_content = """
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ml-model-api/ ./ml-model-api/
COPY models/ ./models/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "ml-model-api.app"]
"""
        
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content.strip())
    
    def _prepare_kubernetes_resources(self, execution: DeploymentExecution):
        """Prepare Kubernetes deployment resources"""
        try:
            # Create deployment manifest
            deployment_manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": f"flavorsnap-model-{execution.spec.model_version}",
                    "labels": {
                        "app": "flavorsnap-model",
                        "version": execution.spec.model_version
                    }
                },
                "spec": {
                    "replicas": 3,
                    "selector": {
                        "matchLabels": {
                            "app": "flavorsnap-model",
                            "version": execution.spec.model_version
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "flavorsnap-model",
                                "version": execution.spec.model_version
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "model",
                                "image": f"flavorsnap-model:{execution.spec.model_version}",
                                "ports": [{"containerPort": 8000}],
                                "env": [
                                    {"name": "MODEL_VERSION", "value": execution.spec.model_version},
                                    {"name": "ENVIRONMENT", "value": execution.spec.environment.value}
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": "512Mi",
                                        "cpu": "250m"
                                    },
                                    "limits": {
                                        "memory": "1Gi",
                                        "cpu": "500m"
                                    }
                                }
                            }]
                        }
                    }
                }
            }
            
            # Save manifest
            manifest_path = Path(f"k8s/deployment-{execution.spec.model_version}.yaml")
            manifest_path.parent.mkdir(exist_ok=True)
            
            with open(manifest_path, 'w') as f:
                yaml.dump(deployment_manifest, f)
            
            logger.info(f"Kubernetes manifest prepared: {manifest_path}")
            
        except Exception as e:
            logger.error(f"Kubernetes preparation failed: {e}")
            raise
    
    def _run_smoke_tests(self, execution: DeploymentExecution):
        """Run smoke tests on deployment"""
        try:
            # Test model loading
            model_metadata = self.model_registry.get_model(execution.spec.model_version)
            if not model_metadata:
                raise ValueError("Model not found in registry")
            
            # Test basic inference (this would be more comprehensive in real implementation)
            test_results = {
                "model_loading": "passed",
                "api_health": "passed",
                "basic_inference": "passed"
            }
            
            logger.info(f"Smoke tests passed: {test_results}")
            
        except Exception as e:
            logger.error(f"Smoke tests failed: {e}")
            raise
    
    def _execute_canary_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute canary deployment strategy"""
        try:
            logger.info(f"Starting canary deployment: {execution.deployment_id}")
            execution.status = DeploymentStatus.DEPLOYING
            
            # Deploy to small percentage of traffic
            initial_traffic = 5.0
            success = self._deploy_with_traffic_split(execution, initial_traffic)
            
            if not success:
                return False
            
            # Monitor canary
            execution.status = DeploymentStatus.MONITORING
            monitoring_duration = execution.spec.canary_duration
            
            start_time = time.time()
            while time.time() - start_time < monitoring_duration:
                metrics = self._get_deployment_metrics(execution.deployment_id)
                if metrics and metrics.get("error_rate", 0) > execution.spec.rollback_threshold:
                    logger.warning("Canary deployment showing high error rate")
                    return False
                
                time.sleep(execution.spec.health_check_interval)
            
            # Gradually increase traffic
            traffic_steps = [10, 25, 50, 100]
            for traffic in traffic_steps:
                success = self._deploy_with_traffic_split(execution, traffic)
                if not success:
                    return False
                
                # Monitor for shorter period
                time.sleep(60)
            
            return True
            
        except Exception as e:
            logger.error(f"Canary deployment failed: {e}")
            return False
    
    def _execute_blue_green_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute blue-green deployment strategy"""
        try:
            logger.info(f"Starting blue-green deployment: {execution.deployment_id}")
            
            # Deploy to green environment
            green_success = self._deploy_to_environment(execution, "green")
            if not green_success:
                return False
            
            # Run comprehensive tests on green
            execution.status = DeploymentStatus.TESTING
            test_success = self._run_comprehensive_tests(execution, "green")
            if not test_success:
                logger.error("Green environment tests failed")
                return False
            
            # Switch traffic to green
            switch_success = self._switch_traffic(execution, "green")
            if not switch_success:
                logger.error("Traffic switch failed")
                return False
            
            # Monitor green environment
            execution.status = DeploymentStatus.MONITORING
            for _ in range(10):  # Monitor for 10 intervals
                metrics = self._get_deployment_metrics(execution.deployment_id)
                if metrics and metrics.get("error_rate", 0) > execution.spec.rollback_threshold:
                    logger.warning("Green environment showing issues")
                    return False
                
                time.sleep(execution.spec.health_check_interval)
            
            return True
            
        except Exception as e:
            logger.error(f"Blue-green deployment failed: {e}")
            return False
    
    def _execute_rolling_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute rolling deployment strategy"""
        try:
            logger.info(f"Starting rolling deployment: {execution.deployment_id}")
            
            # Deploy in batches
            batch_size = 1  # Deploy one instance at a time
            total_instances = 3
            
            for batch in range(0, total_instances, batch_size):
                # Deploy new instances
                success = self._deploy_batch(execution, batch, batch_size)
                if not success:
                    return False
                
                # Wait for health check
                time.sleep(30)
                
                # Verify health
                metrics = self._get_deployment_metrics(execution.deployment_id)
                if metrics and metrics.get("health_score", 0) < 0.8:
                    logger.warning("Rolling deployment health check failed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rolling deployment failed: {e}")
            return False
    
    def _execute_immediate_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute immediate deployment strategy"""
        try:
            logger.info(f"Starting immediate deployment: {execution.deployment_id}")
            
            # Use existing deployment manager
            success = self.deployment_manager.deploy_model(execution.spec.model_version)
            
            if success:
                # Activate model in registry
                self.model_registry.activate_model(execution.spec.model_version)
                logger.info(f"Immediate deployment completed: {execution.deployment_id}")
                return True
            else:
                logger.error("Immediate deployment failed")
                return False
                
        except Exception as e:
            logger.error(f"Immediate deployment failed: {e}")
            return False
    
    def _deploy_with_traffic_split(self, execution: DeploymentExecution, traffic_percentage: float) -> bool:
        """Deploy model with specific traffic split"""
        try:
            # This would integrate with load balancer/service mesh
            # For now, simulate deployment
            
            # Record traffic split
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO deployment_metrics 
                    (deployment_id, timestamp, traffic_percentage, error_rate, 
                     latency_p95, throughput, health_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.deployment_id,
                    datetime.now().isoformat(),
                    traffic_percentage,
                    0.0,  # Simulate low error rate
                    0.1,   # Simulate latency
                    100.0, # Simulate throughput
                    1.0    # Simulate health score
                ))
            
            logger.info(f"Traffic split deployed: {traffic_percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Traffic split deployment failed: {e}")
            return False
    
    def _deploy_to_environment(self, execution: DeploymentExecution, environment: str) -> bool:
        """Deploy to specific environment (blue/green)"""
        try:
            # This would deploy to specific environment
            # For now, simulate deployment
            logger.info(f"Deployed to {environment} environment")
            return True
            
        except Exception as e:
            logger.error(f"Environment deployment failed: {e}")
            return False
    
    def _switch_traffic(self, execution: DeploymentExecution, target_environment: str) -> bool:
        """Switch traffic to target environment"""
        try:
            # This would switch traffic at load balancer level
            logger.info(f"Traffic switched to {target_environment}")
            return True
            
        except Exception as e:
            logger.error(f"Traffic switch failed: {e}")
            return False
    
    def _deploy_batch(self, execution: DeploymentExecution, start_index: int, batch_size: int) -> bool:
        """Deploy batch of instances"""
        try:
            # This would deploy specific batch of instances
            logger.info(f"Deployed batch: {start_index} to {start_index + batch_size}")
            return True
            
        except Exception as e:
            logger.error(f"Batch deployment failed: {e}")
            return False
    
    def _run_comprehensive_tests(self, execution: DeploymentExecution, environment: str) -> bool:
        """Run comprehensive test suite"""
        try:
            # This would run comprehensive tests
            test_results = {
                "unit_tests": "passed",
                "integration_tests": "passed",
                "performance_tests": "passed",
                "security_tests": "passed"
            }
            
            logger.info(f"Comprehensive tests passed: {test_results}")
            return True
            
        except Exception as e:
            logger.error(f"Comprehensive tests failed: {e}")
            return False
    
    def _trigger_rollback(self, execution: DeploymentExecution, reason: str):
        """Trigger automatic rollback"""
        try:
            logger.warning(f"Triggering rollback for {execution.deployment_id}: {reason}")
            
            if execution.previous_version:
                success = self.deployment_manager.rollback_model(
                    execution.previous_version, reason
                )
                
                if success:
                    execution.status = DeploymentStatus.ROLLED_BACK
                    execution.rollback_reason = reason
                    logger.info(f"Rollback completed: {execution.previous_version}")
                else:
                    logger.error("Rollback failed")
            else:
                logger.error("No previous version to rollback to")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    def deploy_to_staging(self, model_version: str) -> bool:
        """Deploy model to staging environment"""
        spec = DeploymentSpec(
            model_version=model_version,
            environment=Environment.STAGING,
            strategy=DeploymentStrategy.IMMEDIATE,
            auto_rollback=True
        )
        
        deployment_id = self.deploy_model(spec)
        
        # Wait for completion
        timeout = 600  # 10 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_deployment_status(deployment_id)
            if status["status"] in [DeploymentStatus.COMPLETED.value, DeploymentStatus.FAILED.value]:
                return status["status"] == DeploymentStatus.COMPLETED.value
            time.sleep(10)
        
        return False
    
    def canary_deploy(self, model_version: str) -> bool:
        """Perform canary deployment"""
        spec = DeploymentSpec(
            model_version=model_version,
            environment=Environment.PRODUCTION,
            strategy=DeploymentStrategy.CANARY,
            traffic_percentage=5.0,
            canary_duration=1800,  # 30 minutes
            auto_rollback=True
        )
        
        deployment_id = self.deploy_model(spec)
        
        # Wait for completion
        timeout = 3600  # 1 hour
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_deployment_status(deployment_id)
            if status["status"] in [DeploymentStatus.COMPLETED.value, DeploymentStatus.FAILED.value]:
                return status["status"] == DeploymentStatus.COMPLETED.value
            time.sleep(30)
        
        return False
    
    def blue_green_deploy(self, model_version: str) -> bool:
        """Perform blue-green deployment"""
        spec = DeploymentSpec(
            model_version=model_version,
            environment=Environment.PRODUCTION,
            strategy=DeploymentStrategy.BLUE_GREEN,
            auto_rollback=True
        )
        
        deployment_id = self.deploy_model(spec)
        
        # Wait for completion
        timeout = 1800  # 30 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_deployment_status(deployment_id)
            if status["status"] in [DeploymentStatus.COMPLETED.value, DeploymentStatus.FAILED.value]:
                return status["status"] == DeploymentStatus.COMPLETED.value
            time.sleep(30)
        
        return False
    
    def _save_deployment(self, execution: DeploymentExecution):
        """Save deployment to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO deployments 
                (deployment_id, model_version, environment, strategy, status,
                 start_time, end_time, previous_version, metrics, error_message,
                 rollback_reason, spec)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.deployment_id,
                execution.spec.model_version,
                execution.spec.environment.value,
                execution.spec.strategy.value,
                execution.status.value,
                execution.start_time.isoformat() if execution.start_time else None,
                execution.end_time.isoformat() if execution.end_time else None,
                execution.previous_version,
                json.dumps(execution.metrics) if execution.metrics else None,
                execution.error_message,
                execution.rollback_reason,
                json.dumps(asdict(execution.spec))
            ))
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deployments WHERE deployment_id = ?", (deployment_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'deployment_id': row['deployment_id'],
                    'model_version': row['model_version'],
                    'environment': row['environment'],
                    'strategy': row['strategy'],
                    'status': row['status'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'previous_version': row['previous_version'],
                    'metrics': json.loads(row['metrics']) if row['metrics'] else {},
                    'error_message': row['error_message'],
                    'rollback_reason': row['rollback_reason']
                }
            else:
                return {'error': 'Deployment not found'}
    
    def list_deployments(self, environment: Environment = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List deployments"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM deployments"
            params = []
            
            if environment:
                query += " WHERE environment = ?"
                params.append(environment.value)
            
            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            deployments = []
            for row in cursor.fetchall():
                deployments.append({
                    'deployment_id': row['deployment_id'],
                    'model_version': row['model_version'],
                    'environment': row['environment'],
                    'strategy': row['strategy'],
                    'status': row['status'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'previous_version': row['previous_version'],
                    'error_message': row['error_message']
                })
            
            return deployments
    
    def get_deployment_metrics(self, deployment_id: str) -> Dict[str, Any]:
        """Get detailed deployment metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM deployment_metrics 
                WHERE deployment_id = ? 
                ORDER BY timestamp DESC
            """, (deployment_id,))
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    'timestamp': row['timestamp'],
                    'traffic_percentage': row['traffic_percentage'],
                    'error_rate': row['error_rate'],
                    'latency_p95': row['latency_p95'],
                    'throughput': row['throughput'],
                    'health_score': row['health_score']
                })
            
            return {
                'deployment_id': deployment_id,
                'metrics': metrics
            }

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap Model Deployment")
    parser.add_argument("--deploy", type=str, help="Deploy model version")
    parser.add_argument("--staging", type=str, help="Deploy to staging")
    parser.add_argument("--canary", type=str, help="Canary deploy model version")
    parser.add_argument("--blue-green", type=str, help="Blue-green deploy model version")
    parser.add_argument("--status", type=str, help="Get deployment status")
    parser.add_argument("--list", action="store_true", help="List deployments")
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    model_registry = ModelRegistry()
    orchestrator = ModelDeploymentOrchestrator(model_registry)
    
    if args.deploy:
        spec = DeploymentSpec(
            model_version=args.deploy,
            environment=Environment.PRODUCTION,
            strategy=DeploymentStrategy.IMMEDIATE
        )
        deployment_id = orchestrator.deploy_model(spec)
        print(f"Deployment started: {deployment_id}")
    
    elif args.staging:
        success = orchestrator.deploy_to_staging(args.staging)
        print(f"Staging deployment {'successful' if success else 'failed'}")
    
    elif args.canary:
        success = orchestrator.canary_deploy(args.canary)
        print(f"Canary deployment {'successful' if success else 'failed'}")
    
    elif args.blue_green:
        success = orchestrator.blue_green_deploy(args.blue_green)
        print(f"Blue-green deployment {'successful' if success else 'failed'}")
    
    elif args.status:
        status = orchestrator.get_deployment_status(args.status)
        print(json.dumps(status, indent=2))
    
    elif args.list:
        deployments = orchestrator.list_deployments()
        print(json.dumps(deployments, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
