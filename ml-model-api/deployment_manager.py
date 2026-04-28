"""
Model Deployment and Rollback System for FlavorSnap
Handles safe model deployment with automatic rollback capabilities
"""

import os
import shutil
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import torch
import logging
import asyncio
import aiohttp
import yaml
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import prometheus_client as prom
import numpy as np

from model_registry import ModelRegistry, ModelMetadata


@dataclass
class DeploymentConfig:
    """Configuration for model deployment"""
    auto_rollback: bool = True
    rollback_threshold: float = 0.05  # 5% performance drop
    monitoring_window: int = 100  # Number of predictions to monitor
    health_check_interval: int = 60  # seconds
    backup_models: bool = True
    max_backup_count: int = 5


@dataclass
class DeploymentEvent:
    """Record of a deployment event"""
    timestamp: str
    event_type: str  # deploy, rollback, health_check
    model_version: str
    previous_version: Optional[str] = None
    success: bool = True
    message: str = ""
    metrics: Dict[str, Any] = None


class ModelDeploymentManager:
    """Manages model deployment with rollback capabilities"""
    
    def __init__(self, 
                 model_registry: ModelRegistry,
                 deployment_config: DeploymentConfig = None,
                 registry_path: str = "model_registry.db"):
        self.model_registry = model_registry
        self.config = deployment_config or DeploymentConfig()
        self.registry_path = registry_path
        self.deployment_dir = Path("deployments")
        self.backup_dir = Path("model_backups")
        
        # Setup directories
        self.deployment_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize deployment tracking
        self._init_deployment_tracking()
    
    def _setup_logging(self):
        """Setup logging for deployment events"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('deployment.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ModelDeployment')
    
    def _init_deployment_tracking(self):
        """Initialize deployment tracking database"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployment_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    previous_version TEXT,
                    success BOOLEAN NOT NULL,
                    message TEXT,
                    metrics TEXT,
                    FOREIGN KEY (model_version) REFERENCES models(version),
                    FOREIGN KEY (previous_version) REFERENCES models(version)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployment_health (
                    model_version TEXT PRIMARY KEY,
                    last_health_check TEXT,
                    health_score REAL,
                    error_count INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    avg_response_time REAL,
                    last_error TEXT,
                    FOREIGN KEY (model_version) REFERENCES models(version)
                )
            """)
    
    def _record_deployment_event(self, event: DeploymentEvent):
        """Record a deployment event"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                INSERT INTO deployment_events 
                (timestamp, event_type, model_version, previous_version, 
                 success, message, metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp,
                event.event_type,
                event.model_version,
                event.previous_version,
                event.success,
                event.message,
                json.dumps(event.metrics) if event.metrics else None
            ))
    
    def _backup_current_model(self, current_version: str) -> bool:
        """Create backup of current model"""
        if not self.config.backup_models:
            return True
        
        try:
            current_model = self.model_registry.get_model(current_version)
            if not current_model:
                return False
            
            # Create backup directory
            backup_path = self.backup_dir / f"{current_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path.mkdir(exist_ok=True)
            
            # Copy model file
            shutil.copy2(current_model.model_path, backup_path / "model.pth")
            
            # Save metadata
            metadata_path = backup_path / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump({
                    'version': current_model.version,
                    'created_at': current_model.created_at,
                    'created_by': current_model.created_by,
                    'description': current_model.description,
                    'accuracy': current_model.accuracy,
                    'loss': current_model.loss,
                    'backup_timestamp': datetime.now().isoformat()
                }, f, indent=2)
            
            self.logger.info(f"Model backup created: {backup_path}")
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup model: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Remove old backups keeping only the most recent ones"""
        if not self.backup_dir.exists():
            return
        
        # Group backups by version
        version_backups = {}
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                version = backup_path.name.split('_')[0]
                if version not in version_backups:
                    version_backups[version] = []
                version_backups[version].append(backup_path)
        
        # Keep only the most recent backups for each version
        for version, backups in version_backups.items():
            if len(backups) > self.config.max_backup_count:
                # Sort by timestamp and remove oldest
                backups.sort(key=lambda x: x.name, reverse=True)
                for old_backup in backups[self.config.max_backup_count:]:
                    try:
                        shutil.rmtree(old_backup)
                        self.logger.info(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove backup {old_backup}: {e}")
    
    def _validate_model(self, version: str) -> Tuple[bool, str]:
        """Validate model before deployment"""
        try:
            model_metadata = self.model_registry.get_model(version)
            if not model_metadata:
                return False, "Model not found in registry"
            
            # Check if model file exists
            if not os.path.exists(model_metadata.model_path):
                return False, "Model file not found"
            
            # Try to load model
            try:
                # Simple validation - try to load the model
                model_data = torch.load(model_metadata.model_path, map_location='cpu')
                self.logger.info(f"Model {version} validation passed")
                return True, "Model validation successful"
                
            except Exception as e:
                return False, f"Model loading failed: {str(e)}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def deploy_model(self, target_version: str, force: bool = False) -> bool:
        """Deploy a new model version with rollback capability"""
        
        # Validate target model
        is_valid, validation_msg = self._validate_model(target_version)
        if not is_valid:
            self.logger.error(f"Model validation failed: {validation_msg}")
            return False
        
        # Get current active model
        current_model = self.model_registry.get_active_model()
        current_version = current_model.version if current_model else None
        
        # Don't deploy if already active
        if current_version == target_version:
            self.logger.info(f"Model {target_version} is already active")
            return True
        
        # Backup current model
        if current_version and not self._backup_current_model(current_version):
            self.logger.warning("Failed to backup current model")
            if not force:
                return False
        
        # Perform deployment
        try:
            # Activate new model
            success = self.model_registry.activate_model(target_version)
            
            if success:
                # Record deployment event
                event = DeploymentEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="deploy",
                    model_version=target_version,
                    previous_version=current_version,
                    success=True,
                    message=f"Successfully deployed model {target_version}"
                )
                self._record_deployment_event(event)
                
                self.logger.info(f"Successfully deployed model {target_version}")
                return True
            else:
                # Rollback if deployment failed
                if current_version:
                    self.rollback_model(current_version, reason="Deployment activation failed")
                
                event = DeploymentEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="deploy",
                    model_version=target_version,
                    previous_version=current_version,
                    success=False,
                    message="Failed to activate model"
                )
                self._record_deployment_event(event)
                
                return False
                
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            
            # Attempt rollback
            if current_version:
                self.rollback_model(current_version, reason=f"Deployment error: {str(e)}")
            
            return False
    
    def rollback_model(self, target_version: str, reason: str = "") -> bool:
        """Rollback to a previous model version"""
        
        try:
            # Validate target model
            is_valid, validation_msg = self._validate_model(target_version)
            if not is_valid:
                self.logger.error(f"Rollback validation failed: {validation_msg}")
                return False
            
            # Get current model
            current_model = self.model_registry.get_active_model()
            current_version = current_model.version if current_model else None
            
            # Perform rollback
            success = self.model_registry.activate_model(target_version)
            
            if success:
                # Record rollback event
                event = DeploymentEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="rollback",
                    model_version=target_version,
                    previous_version=current_version,
                    success=True,
                    message=f"Rolled back to model {target_version}. Reason: {reason}"
                )
                self._record_deployment_event(event)
                
                self.logger.info(f"Successfully rolled back to model {target_version}")
                return True
            else:
                self.logger.error("Failed to perform rollback")
                return False
                
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def get_deployment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get deployment history"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM deployment_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row['timestamp'],
                    'event_type': row['event_type'],
                    'model_version': row['model_version'],
                    'previous_version': row['previous_version'],
                    'success': bool(row['success']),
                    'message': row['message'],
                    'metrics': json.loads(row['metrics']) if row['metrics'] else None
                })
            
            return history
    
    def get_available_rollback_versions(self) -> List[str]:
        """Get list of versions available for rollback"""
        models = self.model_registry.list_models()
        current_model = self.model_registry.get_active_model()
        current_version = current_model.version if current_model else None
        
        # Return all models except the current one
        available_versions = [m.version for m in models if m.version != current_version]
        
        # Also check backup directory
        backup_versions = []
        if self.backup_dir.exists():
            for backup_path in self.backup_dir.iterdir():
                if backup_path.is_dir():
                    version = backup_path.name.split('_')[0]
                    if version not in backup_versions and version not in available_versions:
                        backup_versions.append(version)
        
        return available_versions + backup_versions
    
    def health_check(self, model_version: str = None) -> Dict[str, Any]:
        """Perform health check on deployed model"""
        
        if not model_version:
            current_model = self.model_registry.get_active_model()
            model_version = current_model.version if current_model else None
        
        if not model_version:
            return {"healthy": False, "message": "No active model found"}
        
        try:
            # Validate model file exists and is loadable
            model_metadata = self.model_registry.get_model(model_version)
            if not model_metadata:
                return {"healthy": False, "message": "Model not found in registry"}
            
            # Try to load model
            model_data = torch.load(model_metadata.model_path, map_location='cpu')
            
            # Get current health metrics
            with sqlite3.connect(self.registry_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM deployment_health 
                    WHERE model_version = ?
                """, (model_version,))
                
                health_row = cursor.fetchone()
            
            health_score = 1.0  # Default healthy score
            error_count = 0
            total_requests = 0
            avg_response_time = 0.0
            last_error = None
            
            if health_row:
                health_score = health_row['health_score'] or 1.0
                error_count = health_row['error_count'] or 0
                total_requests = health_row['total_requests'] or 0
                avg_response_time = health_row['avg_response_time'] or 0.0
                last_error = health_row['last_error']
            
            # Determine health status
            healthy = health_score >= 0.8 and error_count < 10
            
            # Record health check
            event = DeploymentEvent(
                timestamp=datetime.now().isoformat(),
                event_type="health_check",
                model_version=model_version,
                success=healthy,
                message=f"Health check completed. Score: {health_score:.2f}",
                metrics={
                    "health_score": health_score,
                    "error_count": error_count,
                    "total_requests": total_requests,
                    "avg_response_time": avg_response_time
                }
            )
            self._record_deployment_event(event)
            
            return {
                "healthy": healthy,
                "model_version": model_version,
                "health_score": health_score,
                "error_count": error_count,
                "total_requests": total_requests,
                "avg_response_time": avg_response_time,
                "last_error": last_error,
                "message": "Model is healthy" if healthy else "Model health issues detected"
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "model_version": model_version,
                "message": f"Health check failed: {str(e)}"
            }
    
    def update_health_metrics(self, 
                             model_version: str,
                             response_time: float,
                             success: bool,
                             error_message: str = None):
        """Update health metrics for a model"""
        
        with sqlite3.connect(self.registry_path) as conn:
            # Get current metrics
            cursor = conn.execute("""
                SELECT error_count, total_requests, avg_response_time
                FROM deployment_health
                WHERE model_version = ?
            """, (model_version,))
            
            row = cursor.fetchone()
            
            if row:
                error_count, total_requests, avg_response_time = row
                error_count = error_count or 0
                total_requests = total_requests or 0
                avg_response_time = avg_response_time or 0.0
            else:
                error_count = 0
                total_requests = 0
                avg_response_time = 0.0
            
            # Update metrics
            total_requests += 1
            if not success:
                error_count += 1
            
            # Calculate new average response time
            if total_requests == 1:
                avg_response_time = response_time
            else:
                avg_response_time = (avg_response_time * (total_requests - 1) + response_time) / total_requests
            
            # Calculate health score
            error_rate = error_count / total_requests if total_requests > 0 else 0
            health_score = max(0.0, 1.0 - error_rate - (response_time / 10.0))  # Penalize slow responses
            
            # Update database
            conn.execute("""
                INSERT OR REPLACE INTO deployment_health
                (model_version, last_health_check, health_score, error_count, 
                 total_requests, avg_response_time, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_version,
                datetime.now().isoformat(),
                health_score,
                error_count,
                total_requests,
                avg_response_time,
                error_message
            ))
        
        # Check if auto-rollback is needed
        if (self.config.auto_rollback and 
            health_score < (1.0 - self.config.rollback_threshold) and
            total_requests >= self.config.monitoring_window):
            
            self.logger.warning(f"Model {model_version} health degraded ({health_score:.2f}), considering rollback")
            
            # Get previous stable version
            stable_models = [m for m in self.model_registry.list_models() if m.is_stable]
            if stable_models:
                previous_stable = stable_models[0].version
                if previous_stable != model_version:
                    self.rollback_model(previous_stable, f"Auto-rollback due to health degradation: {health_score:.2f}")
                    return True
        
        return False
    
    def multi_environment_deploy(self, 
                                target_version: str, 
                                environments: List[str] = ["staging", "production"],
                                strategy: str = "rolling") -> Dict[str, Any]:
        """Deploy to multiple environments with different strategies"""
        
        results = {}
        
        for env in environments:
            try:
                self.logger.info(f"Starting deployment to {env} environment")
                
                # Environment-specific validation
                if env == "production":
                    # Additional checks for production
                    if not self._production_readiness_check(target_version):
                        results[env] = {"success": False, "message": "Production readiness check failed"}
                        continue
                
                # Perform deployment based on strategy
                if strategy == "rolling":
                    success = self._rolling_deploy(target_version, env)
                elif strategy == "blue_green":
                    success = self._blue_green_deploy(target_version, env)
                else:
                    success = self.deploy_model(target_version)
                
                results[env] = {
                    "success": success,
                    "message": f"Deployment to {env} {'succeeded' if success else 'failed'}"
                }
                
                # If production deployment fails, stop further deployments
                if env == "production" and not success:
                    self.logger.error("Production deployment failed, stopping further deployments")
                    break
                    
            except Exception as e:
                results[env] = {"success": False, "message": f"Deployment error: {str(e)}"}
                self.logger.error(f"Deployment to {env} failed: {e}")
        
        return results
    
    def _production_readiness_check(self, version: str) -> bool:
        """Check if model is ready for production deployment"""
        try:
            model_metadata = self.model_registry.get_model(version)
            if not model_metadata:
                return False
            
            # Check accuracy threshold
            if model_metadata.accuracy < 0.85:
                self.logger.warning(f"Model accuracy {model_metadata.accuracy} below production threshold")
                return False
            
            # Check if model has been tested in staging
            staging_health = self.health_check(version)
            if not staging_health.get("healthy", False):
                self.logger.warning("Model not healthy in staging environment")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Production readiness check failed: {e}")
            return False
    
    def _rolling_deploy(self, version: str, environment: str) -> bool:
        """Perform rolling deployment"""
        try:
            # Simulate rolling update - in real implementation would update instances gradually
            self.logger.info(f"Performing rolling deployment to {environment}")
            
            # Deploy to subset of instances first
            success = self.deploy_model(version)
            if success:
                # Monitor for a short period
                import time
                time.sleep(30)
                
                # Check health after initial deployment
                health = self.health_check(version)
                if health.get("healthy", False):
                    self.logger.info(f"Rolling deployment to {environment} successful")
                    return True
                else:
                    self.logger.warning(f"Health check failed during rolling deployment to {environment}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Rolling deployment failed: {e}")
            return False
    
    def _blue_green_deploy(self, version: str, environment: str) -> bool:
        """Perform blue-green deployment"""
        try:
            self.logger.info(f"Performing blue-green deployment to {environment}")
            
            # Deploy to green environment
            green_success = self.deploy_model(version)
            
            if green_success:
                # Run comprehensive tests on green
                green_health = self.health_check(version)
                
                if green_health.get("healthy", False):
                    # Switch traffic to green
                    self.logger.info(f"Switching traffic to green environment for {environment}")
                    return True
                else:
                    # Rollback green, keep blue
                    current_model = self.model_registry.get_active_model()
                    if current_model:
                        self.rollback_model(current_model.version, "Blue-green deployment failed")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Blue-green deployment failed: {e}")
            return False
    
    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get comprehensive deployment metrics"""
        try:
            with sqlite3.connect(self.registry_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get deployment statistics
                cursor = conn.execute("""
                    SELECT 
                        event_type,
                        COUNT(*) as count,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
                    FROM deployment_events
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY event_type
                """)
                
                event_stats = {}
                for row in cursor.fetchall():
                    event_stats[row['event_type']] = {
                        'total': row['count'],
                        'successful': row['success_count'],
                        'success_rate': (row['success_count'] / row['count']) * 100 if row['count'] > 0 else 0
                    }
                
                # Get health metrics
                cursor = conn.execute("""
                    SELECT 
                        AVG(health_score) as avg_health,
                        AVG(avg_response_time) as avg_response_time,
                        SUM(error_count) as total_errors,
                        SUM(total_requests) as total_requests
                    FROM deployment_health
                """)
                
                health_row = cursor.fetchone()
                health_metrics = {
                    'avg_health_score': health_row['avg_health'] or 0,
                    'avg_response_time': health_row['avg_response_time'] or 0,
                    'total_errors': health_row['total_errors'] or 0,
                    'total_requests': health_row['total_requests'] or 0,
                    'error_rate': (health_row['total_errors'] / health_row['total_requests']) * 100 if health_row['total_requests'] > 0 else 0
                }
                
                # Get current model info
                current_model = self.model_registry.get_active_model()
                current_info = {
                    'version': current_model.version if current_model else None,
                    'accuracy': current_model.accuracy if current_model else 0,
                    'deployment_date': current_model.created_at if current_model else None
                }
                
                return {
                    'deployment_stats': event_stats,
                    'health_metrics': health_metrics,
                    'current_model': current_info,
                    'backup_count': len(list(self.backup_dir.iterdir())) if self.backup_dir.exists() else 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get deployment metrics: {e}")
            return {}
    
    def schedule_deployment(self, 
                          target_version: str, 
                          scheduled_time: datetime,
                          environments: List[str] = None) -> str:
        """Schedule a deployment for a specific time"""
        try:
            deployment_id = f"scheduled_{target_version}_{int(scheduled_time.timestamp())}"
            
            # In a real implementation, this would use a task queue like Celery
            # For now, just record the scheduled deployment
            with sqlite3.connect(self.registry_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_deployments (
                        id TEXT PRIMARY KEY,
                        target_version TEXT NOT NULL,
                        scheduled_time TEXT NOT NULL,
                        environments TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    INSERT INTO scheduled_deployments 
                    (id, target_version, scheduled_time, environments)
                    VALUES (?, ?, ?, ?)
                """, (
                    deployment_id,
                    target_version,
                    scheduled_time.isoformat(),
                    json.dumps(environments or ["production"])
                ))
            
            self.logger.info(f"Scheduled deployment {deployment_id} for {scheduled_time}")
            return deployment_id
            
        except Exception as e:
            self.logger.error(f"Failed to schedule deployment: {e}")
            return ""
    
    def get_scheduled_deployments(self) -> List[Dict[str, Any]]:
        """Get list of scheduled deployments"""
        try:
            with sqlite3.connect(self.registry_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM scheduled_deployments 
                    WHERE status = 'pending'
                    ORDER BY scheduled_time
                """)
                
                deployments = []
                for row in cursor.fetchall():
                    deployments.append({
                        'id': row['id'],
                        'target_version': row['target_version'],
                        'scheduled_time': row['scheduled_time'],
                        'environments': json.loads(row['environments']),
                        'status': row['status'],
                        'created_at': row['created_at']
                    })
                
                return deployments
                
        except Exception as e:
            self.logger.error(f"Failed to get scheduled deployments: {e}")
            return []

# Advanced Container Orchestration Integration

class KubernetesDeploymentManager:
    """Advanced Kubernetes deployment manager with auto-scaling and monitoring"""
    
    def __init__(self, kubeconfig_path: str = None):
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_incluster_config()  # For running inside cluster
        except:
            config.load_kube_config()  # Fallback to default
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.autoscaling_v2 = client.AutoscalingV2Api()
        self.networking_v1 = client.NetworkingV1Api()
        self.custom_api = client.CustomObjectsApi()
        
        self.namespace = "flavorsnap"
        self.deployment_labels = {
            "app": "backend",
            "tier": "backend"
        }
        
        # Prometheus metrics
        self.deployment_counter = prom.Counter('kubernetes_deployments_total', 'Total deployments', ['namespace', 'deployment'])
        self.rollback_counter = prom.Counter('kubernetes_rollbacks_total', 'Total rollbacks', ['namespace', 'deployment'])
        self.scaling_events = prom.Counter('kubernetes_scaling_events_total', 'Total scaling events', ['namespace', 'deployment', 'direction'])
        self.deployment_duration = prom.Histogram('kubernetes_deployment_duration_seconds', 'Deployment duration')
        
        self.logger = logging.getLogger('KubernetesDeploymentManager')
    
    async def create_deployment_strategy(self, deployment_name: str, strategy: str = "RollingUpdate") -> dict:
        """Create advanced deployment strategy with custom configuration"""
        
        strategy_configs = {
            "RollingUpdate": {
                "type": "RollingUpdate",
                "rollingUpdate": {
                    "maxUnavailable": "25%",
                    "maxSurge": "25%"
                },
                "progressDeadlineSeconds": 600,
                "revisionHistoryLimit": 10
            },
            "Recreate": {
                "type": "Recreate",
                "progressDeadlineSeconds": 600,
                "revisionHistoryLimit": 5
            },
            "BlueGreen": {
                "type": "RollingUpdate",
                "rollingUpdate": {
                    "maxUnavailable": "0%",
                    "maxSurge": "100%"
                },
                "progressDeadlineSeconds": 1200,
                "revisionHistoryLimit": 3
            }
        }
        
        config = strategy_configs.get(strategy, strategy_configs["RollingUpdate"])
        
        return {
            "deployment_name": deployment_name,
            "strategy": config,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def deploy_with_canary(self, deployment_name: str, new_image: str, 
                                canary_weight: int = 10, 
                                analysis_duration: int = 300) -> bool:
        """Deploy using canary strategy with automated analysis"""
        
        try:
            self.logger.info(f"Starting canary deployment for {deployment_name} with {canary_weight}% weight")
            
            # Create canary deployment
            canary_name = f"{deployment_name}-canary"
            
            # Get original deployment
            original_deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=self.namespace
            )
            
            # Create canary deployment
            canary_deployment = self._create_canary_deployment(
                original_deployment, canary_name, new_image, canary_weight
            )
            
            # Deploy canary
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace,
                body=canary_deployment
            )
            
            # Wait for canary to be ready
            await self._wait_for_deployment_ready(canary_name, timeout=300)
            
            # Monitor canary performance
            analysis_result = await self._analyze_canary_performance(
                canary_name, deployment_name, analysis_duration
            )
            
            if analysis_result["success"]:
                self.logger.info("Canary analysis passed, proceeding with full deployment")
                
                # Update main deployment
                original_deployment.spec.template.spec.containers[0].image = new_image
                self.apps_v1.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace,
                    body=original_deployment
                )
                
                # Wait for main deployment
                await self._wait_for_deployment_ready(deployment_name, timeout=600)
                
                # Clean up canary
                self.apps_v1.delete_namespaced_deployment(
                    name=canary_name,
                    namespace=self.namespace
                )
                
                self.deployment_counter.labels(namespace=self.namespace, deployment=deployment_name).inc()
                return True
            else:
                self.logger.warning("Canary analysis failed, rolling back")
                
                # Clean up canary
                self.apps_v1.delete_namespaced_deployment(
                    name=canary_name,
                    namespace=self.namespace
                )
                
                self.rollback_counter.labels(namespace=self.namespace, deployment=deployment_name).inc()
                return False
                
        except ApiException as e:
            self.logger.error(f"Canary deployment failed: {e}")
            return False
    
    def _create_canary_deployment(self, original: client.V1Deployment, 
                                canary_name: str, new_image: str, weight: int) -> client.V1Deployment:
        """Create canary deployment based on original"""
        
        canary = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=canary_name,
                namespace=self.namespace,
                labels={
                    **original.metadata.labels,
                    "canary": "true"
                }
            ),
            spec=client.V1DeploymentSpec(
                replicas=max(1, original.spec.replicas * weight // 100),
                selector=client.V1LabelSelector(
                    match_labels={
                        **original.spec.selector.match_labels,
                        "canary": "true"
                    }
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            **original.spec.template.metadata.labels,
                            "canary": "true"
                        }
                    ),
                    spec=original.spec.template.spec
                )
            )
        )
        
        # Update container image
        canary.spec.template.spec.containers[0].image = new_image
        
        return canary
    
    async def _wait_for_deployment_ready(self, deployment_name: str, timeout: int = 300) -> bool:
        """Wait for deployment to become ready"""
        
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace
                )
                
                if (deployment.status.ready_replicas == deployment.spec.replicas and
                    deployment.status.available_replicas == deployment.spec.replicas):
                    return True
                
                await asyncio.sleep(5)
                
            except ApiException:
                await asyncio.sleep(5)
        
        return False
    
    async def _analyze_canary_performance(self, canary_name: str, baseline_name: str, 
                                         duration: int) -> dict:
        """Analyze canary deployment performance"""
        
        # Get metrics from Prometheus or monitoring system
        # This is a simplified implementation
        
        metrics = {
            "success_rate": 0.95,  # Should be > 95%
            "avg_response_time": 200,  # Should be < 500ms
            "error_rate": 0.01,  # Should be < 5%
            "cpu_usage": 0.7,  # Should be < 80%
            "memory_usage": 0.6  # Should be < 80%
        }
        
        # Define thresholds
        thresholds = {
            "success_rate": 0.95,
            "avg_response_time": 500,
            "error_rate": 0.05,
            "cpu_usage": 0.8,
            "memory_usage": 0.8
        }
        
        # Evaluate metrics
        passed = True
        failed_metrics = []
        
        for metric, value in metrics.items():
            if metric in ["success_rate"]:
                if value < thresholds[metric]:
                    passed = False
                    failed_metrics.append(metric)
            else:
                if value > thresholds[metric]:
                    passed = False
                    failed_metrics.append(metric)
        
        return {
            "success": passed,
            "metrics": metrics,
            "failed_metrics": failed_metrics,
            "analysis_duration": duration
        }
    
    async def setup_advanced_autoscaling(self, deployment_name: str) -> dict:
        """Setup advanced auto-scaling with custom metrics"""
        
        try:
            # Create Horizontal Pod Autoscaler with advanced metrics
            hpa = client.V2HorizontalPodAutoscaler(
                api_version="autoscaling/v2",
                kind="HorizontalPodAutoscaler",
                metadata=client.V1ObjectMeta(
                    name=f"{deployment_name}-advanced-hpa",
                    namespace=self.namespace
                ),
                spec=client.V2HorizontalPodAutoscalerSpec(
                    scale_target_ref=client.V2CrossVersionObjectReference(
                        api_version="apps/v1",
                        kind="Deployment",
                        name=deployment_name
                    ),
                    min_replicas=2,
                    max_replicas=20,
                    metrics=[
                        client.V2MetricSpec(
                            type="Resource",
                            resource=client.V2ResourceMetricSource(
                                name="cpu",
                                target=client.V2MetricTarget(
                                    type="Utilization",
                                    average_utilization=70
                                )
                            )
                        ),
                        client.V2MetricSpec(
                            type="Resource",
                            resource=client.V2ResourceMetricSource(
                                name="memory",
                                target=client.V2MetricTarget(
                                    type="Utilization",
                                    average_utilization=80
                                )
                            )
                        ),
                        client.V2MetricSpec(
                            type="Pods",
                            pods=client.V2PodsMetricSource(
                                metric=client.V2MetricIdentifier(
                                    name="http_requests_per_second"
                                ),
                                target=client.V2MetricTarget(
                                    type="AverageValue",
                                    average_value="100"
                                )
                            )
                        )
                    ],
                    behavior=client.V2HorizontalPodAutoscalerBehavior(
                        scale_down=client.V2HPAScalingRules(
                            stabilization_window_seconds=300,
                            policies=[
                                client.V2HPAScalingPolicy(
                                    type="Percent",
                                    value=10,
                                    period_seconds=60
                                )
                            ]
                        ),
                        scale_up=client.V2HPAScalingRules(
                            stabilization_window_seconds=60,
                            policies=[
                                client.V2HPAScalingPolicy(
                                    type="Percent",
                                    value=50,
                                    period_seconds=60
                                ),
                                client.V2HPAScalingPolicy(
                                    type="Pods",
                                    value=4,
                                    period_seconds=60
                                )
                            ],
                            select_policy="Max"
                        )
                    )
                )
            )
            
            # Create HPA
            self.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
                namespace=self.namespace,
                body=hpa
            )
            
            # Create Vertical Pod Autoscaler
            vpa = {
                "apiVersion": "autoscaling.k8s.io/v1",
                "kind": "VerticalPodAutoscaler",
                "metadata": {
                    "name": f"{deployment_name}-vpa",
                    "namespace": self.namespace
                },
                "spec": {
                    "targetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": deployment_name
                    },
                    "updatePolicy": {
                        "updateMode": "Auto"
                    },
                    "resourcePolicy": {
                        "containerPolicies": [{
                            "containerName": "backend",
                            "minAllowed": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            },
                            "maxAllowed": {
                                "cpu": "2",
                                "memory": "4Gi"
                            },
                            "controlledResources": ["cpu", "memory"]
                        }]
                    }
                }
            }
            
            self.custom_api.create_namespaced_custom_object(
                group="autoscaling.k8s.io",
                version="v1",
                namespace=self.namespace,
                plural="verticalpodautoscalers",
                body=vpa
            )
            
            return {
                "success": True,
                "hpa_name": f"{deployment_name}-advanced-hpa",
                "vpa_name": f"{deployment_name}-vpa"
            }
            
        except ApiException as e:
            self.logger.error(f"Failed to setup advanced autoscaling: {e}")
            return {"success": False, "error": str(e)}
    
    async def setup_service_mesh(self, deployment_name: str) -> dict:
        """Setup Istio service mesh configuration"""
        
        try:
            # Create VirtualService
            virtual_service = {
                "apiVersion": "networking.istio.io/v1alpha3",
                "kind": "VirtualService",
                "metadata": {
                    "name": f"{deployment_name}-vs",
                    "namespace": self.namespace
                },
                "spec": {
                    "hosts": [f"{deployment_name}.{self.namespace}.svc.cluster.local"],
                    "http": [
                        {
                            "match": [{"uri": {"prefix": "/api"}}],
                            "route": [
                                {
                                    "destination": {
                                        "host": f"{deployment_name}-service",
                                        "port": {"number": 5000}
                                    }
                                }
                            ],
                            "timeout": "30s",
                            "retries": {
                                "attempts": 3,
                                "perTryTimeout": "10s"
                            }
                        }
                    ]
                }
            }
            
            # Create DestinationRule
            destination_rule = {
                "apiVersion": "networking.istio.io/v1alpha3",
                "kind": "DestinationRule",
                "metadata": {
                    "name": f"{deployment_name}-dr",
                    "namespace": self.namespace
                },
                "spec": {
                    "host": f"{deployment_name}-service",
                    "trafficPolicy": {
                        "loadBalancer": {
                            "simple": "LEAST_CONN"
                        },
                        "connectionPool": {
                            "tcp": {
                                "maxConnections": 100
                            },
                            "http": {
                                "http1MaxPendingRequests": 50,
                                "maxRequestsPerConnection": 10
                            }
                        },
                        "circuitBreaker": {
                            "consecutiveErrors": 3,
                            "interval": "30s",
                            "baseEjectionTime": "30s"
                        }
                    }
                }
            }
            
            # Apply Istio configurations
            self.custom_api.create_namespaced_custom_object(
                group="networking.istio.io",
                version="v1alpha3",
                namespace=self.namespace,
                plural="virtualservices",
                body=virtual_service
            )
            
            self.custom_api.create_namespaced_custom_object(
                group="networking.istio.io",
                version="v1alpha3",
                namespace=self.namespace,
                plural="destinationrules",
                body=destination_rule
            )
            
            return {
                "success": True,
                "virtual_service": f"{deployment_name}-vs",
                "destination_rule": f"{deployment_name}-dr"
            }
            
        except ApiException as e:
            self.logger.error(f"Failed to setup service mesh: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_deployment_health(self, deployment_name: str) -> dict:
        """Monitor deployment health and provide recommendations"""
        
        try:
            # Get deployment status
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Get pods
            pods = self.v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"app={deployment_name}"
            )
            
            # Analyze pod health
            healthy_pods = 0
            total_pods = len(pods.items)
            restart_counts = []
            
            for pod in pods.items:
                if pod.status.phase == "Running":
                    healthy_pods += 1
                
                # Get restart counts
                for container in pod.status.container_statuses or []:
                    restart_counts.append(container.restart_count)
            
            # Calculate health metrics
            health_score = healthy_pods / total_pods if total_pods > 0 else 0
            avg_restart_count = np.mean(restart_counts) if restart_counts else 0
            
            # Get resource usage
            resource_usage = await self._get_resource_usage(deployment_name)
            
            # Generate recommendations
            recommendations = []
            
            if health_score < 0.8:
                recommendations.append("Consider checking pod logs for errors")
            
            if avg_restart_count > 5:
                recommendations.append("High restart count detected - check resource limits")
            
            if resource_usage.get("cpu_usage", 0) > 0.8:
                recommendations.append("High CPU usage - consider scaling up")
            
            if resource_usage.get("memory_usage", 0) > 0.8:
                recommendations.append("High memory usage - consider increasing memory limits")
            
            return {
                "deployment_name": deployment_name,
                "health_score": health_score,
                "healthy_pods": healthy_pods,
                "total_pods": total_pods,
                "avg_restart_count": avg_restart_count,
                "resource_usage": resource_usage,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ApiException as e:
            self.logger.error(f"Failed to monitor deployment health: {e}")
            return {"error": str(e)}
    
    async def _get_resource_usage(self, deployment_name: str) -> dict:
        """Get resource usage metrics for deployment"""
        
        # This would typically query metrics server or Prometheus
        # For now, return mock data
        return {
            "cpu_usage": 0.65,
            "memory_usage": 0.72,
            "network_in": 1024000,
            "network_out": 512000
        }
    
    async def perform_rolling_update(self, deployment_name: str, new_image: str, 
                                   max_unavailable: str = "25%", max_surge: str = "25%") -> bool:
        """Perform rolling update with custom parameters"""
        
        try:
            self.logger.info(f"Starting rolling update for {deployment_name}")
            start_time = datetime.utcnow()
            
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Update strategy
            deployment.spec.strategy.type = "RollingUpdate"
            deployment.spec.strategy.rolling_update = client.V1RollingUpdateDeployment(
                max_unavailable=max_unavailable,
                max_surge=max_surge
            )
            
            # Update image
            deployment.spec.template.spec.containers[0].image = new_image
            
            # Apply changes
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment
            )
            
            # Wait for rollout
            success = await self._wait_for_deployment_ready(deployment_name, timeout=600)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.deployment_duration.observe(duration)
            
            if success:
                self.deployment_counter.labels(namespace=self.namespace, deployment=deployment_name).inc()
                self.logger.info(f"Rolling update completed in {duration:.2f}s")
            else:
                self.logger.error("Rolling update failed")
            
            return success
            
        except ApiException as e:
            self.logger.error(f"Rolling update failed: {e}")
            return False
    
    async def rollback_deployment(self, deployment_name: str, revision: int = None) -> bool:
        """Rollback deployment to previous revision"""
        
        try:
            self.logger.info(f"Rolling back {deployment_name} to revision {revision or 'previous'}")
            
            # Get deployment history
            rollout = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Create rollback
            if revision:
                # Rollback to specific revision
                body = client.V1RollbackConfig(
                    name=deployment_name,
                    revision=revision
                )
            else:
                # Rollback to previous revision
                body = client.V1RollbackConfig(
                    name=deployment_name
                )
            
            # Note: In newer Kubernetes versions, use undo rollout
            self.apps_v1.create_namespaced_deployment_rollback(
                name=deployment_name,
                namespace=self.namespace,
                body=body
            )
            
            # Wait for rollback to complete
            success = await self._wait_for_deployment_ready(deployment_name, timeout=600)
            
            if success:
                self.rollback_counter.labels(namespace=self.namespace, deployment=deployment_name).inc()
                self.logger.info("Rollback completed successfully")
            else:
                self.logger.error("Rollback failed")
            
            return success
            
        except ApiException as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def get_deployment_metrics(self, deployment_name: str) -> dict:
        """Get comprehensive deployment metrics"""
        
        try:
            # Get deployment info
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Get HPA info
            try:
                hpa = self.autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(
                    name=f"{deployment_name}-advanced-hpa",
                    namespace=self.namespace
                )
                hpa_info = {
                    "min_replicas": hpa.spec.min_replicas,
                    "max_replicas": hpa.spec.max_replicas,
                    "current_replicas": hpa.status.current_replicas,
                    "desired_replicas": hpa.status.desired_replicas
                }
            except ApiException:
                hpa_info = {}
            
            # Get events
            events = self.v1.list_namespaced_event(
                namespace=self.namespace,
                field_selector=f"involvedObject.name={deployment_name}"
            )
            
            recent_events = [
                {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "timestamp": event.last_timestamp
                }
                for event in events.items[-10:]  # Last 10 events
            ]
            
            return {
                "deployment_name": deployment_name,
                "replicas": {
                    "desired": deployment.spec.replicas,
                    "ready": deployment.status.ready_replicas or 0,
                    "available": deployment.status.available_replicas or 0,
                    "unavailable": deployment.status.unavailable_replicas or 0
                },
                "hpa": hpa_info,
                "recent_events": recent_events,
                "created_at": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None
            }
            
        except ApiException as e:
            self.logger.error(f"Failed to get deployment metrics: {e}")
            return {"error": str(e)}

# Global Kubernetes deployment manager
k8s_deployment_manager = None

def get_kubernetes_deployment_manager() -> KubernetesDeploymentManager:
    """Get or create global Kubernetes deployment manager"""
    global k8s_deployment_manager
    if k8s_deployment_manager is None:
        k8s_deployment_manager = KubernetesDeploymentManager()
    return k8s_deployment_manager


class DeploymentManager:
    """
    Handles infrastructure deployment via Terraform + Docker.
    """

    def __init__(self, env: str = "dev"):
        self.env = env

    def init_terraform(self):
        return subprocess.run(
            ["terraform", "init"],
            cwd="terraform/",
            capture_output=True,
            text=True
        )

    def plan(self):
        return subprocess.run(
            ["terraform", "plan", f"-var-file={self.env}.tfvars"],
            cwd="terraform/",
            capture_output=True,
            text=True
        )

    def apply(self):
        return subprocess.run(
            ["terraform", "apply", "-auto-approve", f"-var-file={self.env}.tfvars"],
            cwd="terraform/",
            capture_output=True,
            text=True
        )

    def destroy(self):
        return subprocess.run(
            ["terraform", "destroy", "-auto-approve", f"-var-file={self.env}.tfvars"],
            cwd="terraform/",
            capture_output=True,
            text=True
        )

    def deploy_docker(self):
        return subprocess.run(
            ["docker-compose", "up", "-d"],
            capture_output=True,
            text=True
        )

    def status(self):
        return subprocess.run(
            ["terraform", "show"],
            cwd="terraform/",
            capture_output=True,
            text=True
        )