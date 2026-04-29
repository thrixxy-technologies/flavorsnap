import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict
import docker
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_config, get_config_value
from logger_config import get_logger

class DeploymentStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    HEALTH_CHECKING = "health_checking"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class DeploymentConfig:
    image_name: str
    image_tag: str
    environment: Environment
    port: int
    health_check_url: str
    health_check_interval: int = 30
    health_check_timeout: int = 10
    health_check_retries: int = 3
    rollback_threshold: float = 0.5  # Error rate threshold for auto-rollback
    zero_downtime: bool = True

@dataclass
class DeploymentRecord:
    id: str
    config: DeploymentConfig
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    container_id: Optional[str] = None
    error_message: Optional[str] = None
    health_check_results: List[Dict[str, Any]] = None
    rollback_reason: Optional[str] = None

class DeploymentManager:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.docker_client = None
        self.deployments: Dict[str, DeploymentRecord] = {}
        self.active_deployment: Optional[str] = None
        self.blue_deployment: Optional[str] = None
        self.green_deployment: Optional[str] = None
        self.health_check_thread = None
        self.monitoring_active = False
        
        try:
            self.docker_client = docker.from_env()
            self.logger.info("Docker client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def create_deployment_config(self, **kwargs) -> DeploymentConfig:
        """Create deployment configuration from parameters"""
        defaults = {
            'image_name': get_config_value('deployment.image_name', 'flavorsnap-api'),
            'image_tag': get_config_value('deployment.image_tag', 'latest'),
            'environment': Environment(get_config_value('deployment.environment', 'staging')),
            'port': get_config_value('deployment.port', 5000),
            'health_check_url': get_config_value('deployment.health_check_url', '/health'),
            'health_check_interval': get_config_value('deployment.health_check_interval', 30),
            'health_check_timeout': get_config_value('deployment.health_check_timeout', 10),
            'health_check_retries': get_config_value('deployment.health_check_retries', 3),
            'rollback_threshold': get_config_value('deployment.rollback_threshold', 0.5),
            'zero_downtime': get_config_value('deployment.zero_downtime', True)
        }
        defaults.update(kwargs)
        return DeploymentConfig(**defaults)

    def build_image(self, config: DeploymentConfig) -> str:
        """Build Docker image for deployment"""
        self.logger.info(f"Building Docker image: {config.image_name}:{config.image_tag}")
        
        dockerfile_path = Path(__file__).parent / "Dockerfile"
        build_context = Path(__file__).parent.parent
        
        try:
            image, build_logs = self.docker_client.images.build(
                path=str(build_context),
                dockerfile=str(dockerfile_path),
                tag=f"{config.image_name}:{config.image_tag}",
                rm=True
            )
            
            self.logger.info(f"Successfully built image: {image.id}")
            return image.id
            
        except Exception as e:
            self.logger.error(f"Failed to build Docker image: {e}")
            raise

    def run_health_checks(self, config: DeploymentConfig, container_id: str) -> bool:
        """Run health checks on deployed container"""
        self.logger.info(f"Running health checks for container {container_id}")
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.reload()
            
            # Check if container is running
            if container.status != 'running':
                self.logger.error(f"Container {container_id} is not running: {container.status}")
                return False
            
            # Get container IP
            container_ip = container.attrs['NetworkSettings']['IPAddress']
            if not container_ip:
                # Use host port mapping
                port_mapping = container.attrs['NetworkSettings']['Ports'].get(f'{config.port}/tcp', [])
                if port_mapping:
                    host_ip = port_mapping[0]['HostIp']
                    host_port = port_mapping[0]['HostPort']
                    health_url = f"http://{host_ip}:{host_port}{config.health_check_url}"
                else:
                    self.logger.error("No port mapping found for container")
                    return False
            else:
                health_url = f"http://{container_ip}:{config.port}{config.health_check_url}"
            
            # Perform health check with retries
            for attempt in range(config.health_check_retries):
                try:
                    response = requests.get(
                        health_url,
                        timeout=config.health_check_timeout
                    )
                    
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get('status') == 'healthy':
                            self.logger.info(f"Health check passed on attempt {attempt + 1}")
                            return True
                        else:
                            self.logger.warning(f"Health check returned unhealthy status: {health_data}")
                    
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Health check attempt {attempt + 1} failed: {e}")
                
                if attempt < config.health_check_retries - 1:
                    time.sleep(config.health_check_interval)
            
            self.logger.error(f"Health checks failed after {config.health_check_retries} attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False

    def deploy_blue_green(self, config: DeploymentConfig) -> str:
        """Deploy using blue-green strategy"""
        deployment_id = f"deployment-{int(time.time())}"
        
        # Create deployment record
        deployment = DeploymentRecord(
            id=deployment_id,
            config=config,
            status=DeploymentStatus.PENDING,
            created_at=datetime.now()
        )
        self.deployments[deployment_id] = deployment
        
        try:
            deployment.status = DeploymentStatus.BUILDING
            image_id = self.build_image(config)
            
            deployment.status = DeploymentStatus.DEPLOYING
            deployment.started_at = datetime.now()
            
            # Determine which environment to deploy to
            if self.green_deployment is None:
                target_color = 'green'
            elif self.blue_deployment is None:
                target_color = 'blue'
            else:
                # Both exist, deploy to the inactive one
                blue_record = self.deployments.get(self.blue_deployment)
                if blue_record and blue_record.status == DeploymentStatus.ACTIVE:
                    target_color = 'green'
                else:
                    target_color = 'blue'
            
            # Deploy to target environment
            container_name = f"flavorsnap-{target_color}"
            
            # Stop and remove existing container if it exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                existing_container.stop()
                existing_container.remove()
                self.logger.info(f"Removed existing {target_color} container")
            except docker.errors.NotFound:
                pass
            except Exception as e:
                self.logger.warning(f"Error removing existing container: {e}")
            
            # Start new container
            environment_vars = [
                f"FLASK_ENV={config.environment.value}",
                f"DEPLOYMENT_COLOR={target_color}",
                f"DEPLOYMENT_ID={deployment_id}"
            ]
            
            container = self.docker_client.containers.run(
                f"{config.image_name}:{config.image_tag}",
                name=container_name,
                ports={f'{config.port}/tcp': None},  # Auto-assign host port
                environment=environment_vars,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            deployment.container_id = container.id
            self.logger.info(f"Started {target_color} container: {container.id}")
            
            # Update deployment tracking
            if target_color == 'green':
                self.green_deployment = deployment_id
            else:
                self.blue_deployment = deployment_id
            
            # Run health checks
            deployment.status = DeploymentStatus.HEALTH_CHECKING
            if self.run_health_checks(config, container.id):
                deployment.status = DeploymentStatus.ACTIVE
                deployment.completed_at = datetime.now()
                
                # Switch traffic if zero downtime is enabled
                if config.zero_downtime:
                    self.switch_traffic(target_color)
                
                self.active_deployment = deployment_id
                self.logger.info(f"Successfully deployed {target_color} environment")
                
                # Start monitoring
                self.start_deployment_monitoring(deployment_id)
                
                return deployment_id
            else:
                deployment.status = DeploymentStatus.FAILED
                deployment.error_message = "Health checks failed"
                deployment.completed_at = datetime.now()
                
                # Auto-rollback if enabled
                if self.active_deployment:
                    self.logger.info("Auto-rolling back due to health check failure")
                    self.rollback_deployment(deployment_id, "Health check failure")
                
                raise Exception("Deployment failed health checks")
                
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = datetime.now()
            self.logger.error(f"Deployment {deployment_id} failed: {e}")
            raise

    def switch_traffic(self, target_color: str):
        """Switch traffic between blue and green environments"""
        self.logger.info(f"Switching traffic to {target_color} environment")
        
        try:
            # Update load balancer configuration
            # This would integrate with your load balancer (nginx, AWS ALB, etc.)
            # For now, we'll simulate the switch
            
            if target_color == 'green':
                if self.blue_deployment:
                    blue_record = self.deployments.get(self.blue_deployment)
                    if blue_record and blue_record.container_id:
                        try:
                            blue_container = self.docker_client.containers.get(blue_record.container_id)
                            blue_container.stop()
                            self.logger.info("Stopped blue environment")
                        except Exception as e:
                            self.logger.warning(f"Error stopping blue container: {e}")
            else:
                if self.green_deployment:
                    green_record = self.deployments.get(self.green_deployment)
                    if green_record and green_record.container_id:
                        try:
                            green_container = self.docker_client.containers.get(green_record.container_id)
                            green_container.stop()
                            self.logger.info("Stopped green environment")
                        except Exception as e:
                            self.logger.warning(f"Error stopping green container: {e}")
            
            self.logger.info(f"Traffic switched to {target_color} environment")
            
        except Exception as e:
            self.logger.error(f"Failed to switch traffic: {e}")
            raise

    def rollback_deployment(self, deployment_id: str, reason: str = "Manual rollback"):
        """Rollback a deployment to the previous stable version"""
        self.logger.info(f"Rolling back deployment {deployment_id}: {reason}")
        
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise Exception(f"Deployment {deployment_id} not found")
        
        try:
            # Find the previous stable deployment
            previous_deployment = None
            for dep_id, dep_record in self.deployments.items():
                if (dep_record.status == DeploymentStatus.ACTIVE and 
                    dep_id != deployment_id and
                    dep_record.created_at < deployment.created_at):
                    previous_deployment = dep_record
                    break
            
            if not previous_deployment:
                self.logger.warning("No previous stable deployment found for rollback")
                return False
            
            # Switch traffic back to previous deployment
            if self.blue_deployment == deployment_id:
                self.switch_traffic('blue' if self.green_deployment == previous_deployment.id else 'green')
            elif self.green_deployment == deployment_id:
                self.switch_traffic('green' if self.blue_deployment == previous_deployment.id else 'blue')
            
            # Update deployment status
            deployment.status = DeploymentStatus.ROLLED_BACK
            deployment.rollback_reason = reason
            deployment.completed_at = datetime.now()
            
            # Stop failed deployment container
            if deployment.container_id:
                try:
                    container = self.docker_client.containers.get(deployment.container_id)
                    container.stop()
                    self.logger.info(f"Stopped failed deployment container: {deployment.container_id}")
                except Exception as e:
                    self.logger.warning(f"Error stopping failed container: {e}")
            
            # Update active deployment
            self.active_deployment = previous_deployment.id
            
            self.logger.info(f"Successfully rolled back to deployment {previous_deployment.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

    def start_deployment_monitoring(self, deployment_id: str):
        """Start monitoring a deployment for health and performance"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.logger.info(f"Starting monitoring for deployment {deployment_id}")
        
        # Start monitoring thread (simplified for this implementation)
        # In production, you'd use a proper monitoring system like Prometheus
        
    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentRecord]:
        """Get the status of a deployment"""
        return self.deployments.get(deployment_id)

    def list_deployments(self) -> List[DeploymentRecord]:
        """List all deployments"""
        return list(self.deployments.values())

    def get_active_deployment(self) -> Optional[DeploymentRecord]:
        """Get the currently active deployment"""
        if self.active_deployment:
            return self.deployments.get(self.active_deployment)
        return None

    def cleanup_old_deployments(self, keep_count: int = 5):
        """Clean up old deployment records and containers"""
        self.logger.info(f"Cleaning up old deployments, keeping last {keep_count}")
        
        # Sort deployments by creation time
        sorted_deployments = sorted(
            self.deployments.values(),
            key=lambda d: d.created_at,
            reverse=True
        )
        
        # Keep the most recent deployments
        deployments_to_keep = sorted_deployments[:keep_count]
        deployments_to_remove = sorted_deployments[keep_count:]
        
        for deployment in deployments_to_remove:
            try:
                # Remove container if it exists
                if deployment.container_id:
                    try:
                        container = self.docker_client.containers.get(deployment.container_id)
                        container.remove(force=True)
                        self.logger.info(f"Removed container for deployment {deployment.id}")
                    except docker.errors.NotFound:
                        pass
                
                # Remove from tracking
                del self.deployments[deployment.id]
                
                # Update blue/green tracking
                if self.blue_deployment == deployment.id:
                    self.blue_deployment = None
                elif self.green_deployment == deployment.id:
                    self.green_deployment = None
                
                self.logger.info(f"Cleaned up deployment {deployment.id}")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up deployment {deployment.id}: {e}")

    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get deployment metrics and statistics"""
        total_deployments = len(self.deployments)
        active_deployments = len([d for d in self.deployments.values() if d.status == DeploymentStatus.ACTIVE])
        failed_deployments = len([d for d in self.deployments.values() if d.status == DeploymentStatus.FAILED])
        
        return {
            'total_deployments': total_deployments,
            'active_deployments': active_deployments,
            'failed_deployments': failed_deployments,
            'success_rate': (total_deployments - failed_deployments) / total_deployments if total_deployments > 0 else 0,
            'current_active': self.active_deployment,
            'blue_deployment': self.blue_deployment,
            'green_deployment': self.green_deployment,
            'monitoring_active': self.monitoring_active
        }

# CLI interface for deployment management
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='FlavorSnap Deployment Manager')
    parser.add_argument('action', choices=['deploy', 'rollback', 'status', 'list', 'cleanup'])
    parser.add_argument('--environment', default='staging', help='Deployment environment')
    parser.add_argument('--tag', default='latest', help='Docker image tag')
    parser.add_argument('--deployment-id', help='Deployment ID for rollback')
    parser.add_argument('--reason', default='Manual rollback', help='Rollback reason')
    
    args = parser.parse_args()
    
    try:
        manager = DeploymentManager()
        
        if args.action == 'deploy':
            config = manager.create_deployment_config(
                environment=Environment(args.environment),
                image_tag=args.tag
            )
            deployment_id = manager.deploy_blue_green(config)
            print(f"Deployment started: {deployment_id}")
            
        elif args.action == 'rollback':
            if not args.deployment_id:
                # Get latest deployment to rollback
                active = manager.get_active_deployment()
                if active:
                    args.deployment_id = active.id
                else:
                    print("No active deployment found for rollback")
                    return
            
            success = manager.rollback_deployment(args.deployment_id, args.reason)
            if success:
                print(f"Successfully rolled back deployment {args.deployment_id}")
            else:
                print(f"Rollback failed for deployment {args.deployment_id}")
        
        elif args.action == 'status':
            if args.deployment_id:
                deployment = manager.get_deployment_status(args.deployment_id)
                if deployment:
                    print(json.dumps(asdict(deployment), indent=2, default=str))
                else:
                    print(f"Deployment {args.deployment_id} not found")
            else:
                active = manager.get_active_deployment()
                if active:
                    print(json.dumps(asdict(active), indent=2, default=str))
                else:
                    print("No active deployment")
        
        elif args.action == 'list':
            deployments = manager.list_deployments()
            for deployment in deployments:
                print(f"{deployment.id}: {deployment.status.value} ({deployment.created_at})")
        
        elif args.action == 'cleanup':
            manager.cleanup_old_deployments()
            print("Cleanup completed")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
