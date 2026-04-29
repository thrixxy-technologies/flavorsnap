#!/usr/bin/env python3
"""
Scaling Policies Manager for Auto-Scaling
Implements intelligent scaling policies and resource optimization
"""

import asyncio
import time
import json
import logging
import yaml
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScalingPolicyType(Enum):
    THRESHOLD_BASED = "threshold_based"
    TIME_BASED = "time_based"
    SCHEDULE_BASED = "schedule_based"
    PREDICTIVE = "predictive"
    CUSTOM = "custom"

class ResourcePriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ScalingDirection(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"

@dataclass
class ScalingThreshold:
    metric: str
    operator: str  # >, <, >=, <=, ==
    value: float
    duration: int  # seconds
    cooldown: int  # seconds

@dataclass
class ScalingSchedule:
    name: str
    timezone: str
    schedules: List[Dict[str, Any]]  # List of schedule objects

@dataclass
class ScalingPolicy:
    name: str
    component: str
    policy_type: ScalingPolicyType
    min_replicas: int
    max_replicas: int
    default_replicas: int
    resource_priority: ResourcePriority
    thresholds: List[ScalingThreshold]
    schedules: List[ScalingSchedule]
    custom_rules: List[Dict[str, Any]]
    enabled: bool
    last_modified: float

@dataclass
class ScalingAction:
    component: str
    direction: ScalingDirection
    target_replicas: int
    reason: str
    confidence: float
    policy_name: str
    timestamp: float

class PrometheusMetrics:
    """Prometheus metrics for scaling policies"""
    
    def __init__(self):
        self.policy_evaluations = prom.Counter(
            'scaling_policy_evaluations_total',
            'Total policy evaluations',
            ['policy', 'component', 'result']
        )
        
        self.policy_actions = prom.Counter(
            'scaling_policy_actions_total',
            'Total scaling actions triggered',
            ['policy', 'component', 'direction']
        )
        
        self.policy_effectiveness = prom.Gauge(
            'scaling_policy_effectiveness',
            'Policy effectiveness score',
            ['policy', 'component']
        )
        
        self.resource_optimization_score = prom.Gauge(
            'scaling_resource_optimization_score',
            'Resource optimization score',
            ['component']
        )
        
        self.policy_violations = prom.Counter(
            'scaling_policy_violations_total',
            'Total policy violations',
            ['policy', 'component', 'violation_type']
        )

class ScalingPolicyManager:
    """Advanced scaling policy manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.policies: Dict[str, ScalingPolicy] = {}
        self.actions_history: List[ScalingAction] = []
        self.active_schedules: Dict[str, Any] = {}
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Initialize default policies
        self._load_default_policies()
        
        # Load custom policies
        self._load_custom_policies()
    
    def _load_default_policies(self):
        """Load default scaling policies"""
        default_policies = {
            'frontend-critical': ScalingPolicy(
                name='frontend-critical',
                component='frontend',
                policy_type=ScalingPolicyType.THRESHOLD_BASED,
                min_replicas=2,
                max_replicas=20,
                default_replicas=3,
                resource_priority=ResourcePriority.HIGH,
                thresholds=[
                    ScalingThreshold(
                        metric='cpu_utilization',
                        operator='>',
                        value=80.0,
                        duration=60,
                        cooldown=120
                    ),
                    ScalingThreshold(
                        metric='memory_utilization',
                        operator='>',
                        value=85.0,
                        duration=60,
                        cooldown=180
                    ),
                    ScalingThreshold(
                        metric='request_rate',
                        operator='>',
                        value=1000.0,
                        duration=30,
                        cooldown=60
                    )
                ],
                schedules=[],
                custom_rules=[],
                enabled=True,
                last_modified=time.time()
            ),
            'backend-ml': ScalingPolicy(
                name='backend-ml',
                component='backend',
                policy_type=ScalingPolicyType.PREDICTIVE,
                min_replicas=2,
                max_replicas=10,
                default_replicas=3,
                resource_priority=ResourcePriority.CRITICAL,
                thresholds=[
                    ScalingThreshold(
                        metric='cpu_utilization',
                        operator='>',
                        value=75.0,
                        duration=45,
                        cooldown=90
                    ),
                    ScalingThreshold(
                        metric='ml_queue_length',
                        operator='>',
                        value=100.0,
                        duration=30,
                        cooldown=60
                    ),
                    ScalingThreshold(
                        metric='ml_processing_time',
                        operator='>',
                        value=5000.0,
                        duration=60,
                        cooldown=120
                    )
                ],
                schedules=[],
                custom_rules=[
                    {
                        'type': 'ml_model_load',
                        'condition': 'high_prediction_volume',
                        'action': 'scale_up',
                        'multiplier': 1.5
                    }
                ],
                enabled=True,
                last_modified=time.time()
            ),
            'load-balancer-throughput': ScalingPolicy(
                name='load-balancer-throughput',
                component='load-balancer',
                policy_type=ScalingPolicyType.THRESHOLD_BASED,
                min_replicas=2,
                max_replicas=5,
                default_replicas=2,
                resource_priority=ResourcePriority.CRITICAL,
                thresholds=[
                    ScalingThreshold(
                        metric='active_connections',
                        operator='>',
                        value=2000.0,
                        duration=30,
                        cooldown=60
                    ),
                    ScalingThreshold(
                        metric='request_rate',
                        operator='>',
                        value=10000.0,
                        duration=30,
                        cooldown=30
                    )
                ],
                schedules=[],
                custom_rules=[],
                enabled=True,
                last_modified=time.time()
            ),
            'business-hours-frontend': ScalingPolicy(
                name='business-hours-frontend',
                component='frontend',
                policy_type=ScalingPolicyType.SCHEDULE_BASED,
                min_replicas=1,
                max_replicas=15,
                default_replicas=2,
                resource_priority=ResourcePriority.MEDIUM,
                thresholds=[
                    ScalingThreshold(
                        metric='cpu_utilization',
                        operator='>',
                        value=90.0,
                        duration=120,
                        cooldown=300
                    )
                ],
                schedules=[
                    ScalingSchedule(
                        name='business_hours',
                        timezone='UTC',
                        schedules=[
                            {
                                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                                'start_time': '09:00',
                                'end_time': '18:00',
                                'replicas': 5
                            },
                            {
                                'days': ['saturday', 'sunday'],
                                'start_time': '10:00',
                                'end_time': '16:00',
                                'replicas': 3
                            }
                        ]
                    )
                ],
                custom_rules=[],
                enabled=True,
                last_modified=time.time()
            ),
            'cost-optimized-backend': ScalingPolicy(
                name='cost-optimized-backend',
                component='backend',
                policy_type=ScalingPolicyType.CUSTOM,
                min_replicas=1,
                max_replicas=8,
                default_replicas=2,
                resource_priority=ResourcePriority.LOW,
                thresholds=[
                    ScalingThreshold(
                        metric='cpu_utilization',
                        operator='>',
                        value=85.0,
                        duration=180,
                        cooldown=600
                    )
                ],
                schedules=[],
                custom_rules=[
                    {
                        'type': 'cost_optimization',
                        'condition': 'low_traffic_period',
                        'action': 'scale_down',
                        'min_replicas': 1,
                        'cost_threshold': 0.8
                    }
                ],
                enabled=True,
                last_modified=time.time()
            )
        }
        
        self.policies.update(default_policies)
        logger.info(f"Loaded {len(default_policies)} default scaling policies")
    
    def _load_custom_policies(self):
        """Load custom policies from configuration"""
        custom_policies_config = self.config.get('custom_policies', [])
        
        for policy_config in custom_policies_config:
            try:
                policy = self._parse_policy_config(policy_config)
                if policy:
                    self.policies[policy.name] = policy
                    logger.info(f"Loaded custom policy: {policy.name}")
            except Exception as e:
                logger.error(f"Failed to load custom policy {policy_config.get('name', 'unknown')}: {e}")
    
    def _parse_policy_config(self, config: Dict[str, Any]) -> Optional[ScalingPolicy]:
        """Parse policy configuration"""
        try:
            thresholds = []
            for thresh_config in config.get('thresholds', []):
                threshold = ScalingThreshold(
                    metric=thresh_config['metric'],
                    operator=thresh_config['operator'],
                    value=float(thresh_config['value']),
                    duration=int(thresh_config['duration']),
                    cooldown=int(thresh_config['cooldown'])
                )
                thresholds.append(threshold)
            
            schedules = []
            for schedule_config in config.get('schedules', []):
                schedule = ScalingSchedule(
                    name=schedule_config['name'],
                    timezone=schedule_config['timezone'],
                    schedules=schedule_config['schedules']
                )
                schedules.append(schedule)
            
            return ScalingPolicy(
                name=config['name'],
                component=config['component'],
                policy_type=ScalingPolicyType(config['policy_type']),
                min_replicas=int(config['min_replicas']),
                max_replicas=int(config['max_replicas']),
                default_replicas=int(config['default_replicas']),
                resource_priority=ResourcePriority(config['resource_priority']),
                thresholds=thresholds,
                schedules=schedules,
                custom_rules=config.get('custom_rules', []),
                enabled=config.get('enabled', True),
                last_modified=time.time()
            )
        except Exception as e:
            logger.error(f"Error parsing policy config: {e}")
            return None
    
    async def evaluate_policies(self, metrics: Dict[str, Dict[str, float]]) -> List[ScalingAction]:
        """Evaluate all active policies against current metrics"""
        actions = []
        
        for policy_name, policy in self.policies.items():
            if not policy.enabled:
                continue
            
            try:
                action = await self._evaluate_policy(policy, metrics.get(policy.component, {}))
                if action:
                    actions.append(action)
                    
                    # Update metrics
                    self.metrics.policy_evaluations.labels(
                        policy=policy_name,
                        component=policy.component,
                        result='action_triggered'
                    ).inc()
                    
                    self.metrics.policy_actions.labels(
                        policy=policy_name,
                        component=policy.component,
                        direction=action.direction.value
                    ).inc()
                else:
                    self.metrics.policy_evaluations.labels(
                        policy=policy_name,
                        component=policy.component,
                        result='no_action'
                    ).inc()
                    
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_name}: {e}")
                self.metrics.policy_violations.labels(
                    policy=policy_name,
                    component=policy.component,
                    violation_type='evaluation_error'
                ).inc()
        
        # Store actions in history
        self.actions_history.extend(actions)
        
        # Keep only last 1000 actions
        if len(self.actions_history) > 1000:
            self.actions_history = self.actions_history[-1000:]
        
        return actions
    
    async def _evaluate_policy(self, policy: ScalingPolicy, 
                             component_metrics: Dict[str, float]) -> Optional[ScalingAction]:
        """Evaluate a single policy"""
        current_time = time.time()
        
        # Check cooldown periods
        if self._is_in_cooldown(policy.name, policy.component):
            return None
        
        # Evaluate based on policy type
        if policy.policy_type == ScalingPolicyType.THRESHOLD_BASED:
            return self._evaluate_threshold_policy(policy, component_metrics)
        elif policy.policy_type == ScalingPolicyType.SCHEDULE_BASED:
            return self._evaluate_schedule_policy(policy, current_time)
        elif policy.policy_type == ScalingPolicyType.PREDICTIVE:
            return await self._evaluate_predictive_policy(policy, component_metrics)
        elif policy.policy_type == ScalingPolicyType.CUSTOM:
            return self._evaluate_custom_policy(policy, component_metrics)
        
        return None
    
    def _evaluate_threshold_policy(self, policy: ScalingPolicy,
                                component_metrics: Dict[str, float]) -> Optional[ScalingAction]:
        """Evaluate threshold-based policy"""
        triggered_thresholds = []
        
        for threshold in policy.thresholds:
            metric_value = component_metrics.get(threshold.metric, 0)
            
            if self._evaluate_threshold(threshold, metric_value):
                triggered_thresholds.append(threshold)
        
        if not triggered_thresholds:
            return None
        
        # Determine scaling direction and target replicas
        current_replicas = component_metrics.get('current_replicas', policy.default_replicas)
        
        # Scale up if any threshold is exceeded
        if triggered_thresholds:
            scale_up_thresholds = [t for t in triggered_thresholds if t.operator in ['>', '>=']]
            scale_down_thresholds = [t for t in triggered_thresholds if t.operator in ['<', '<=']]
            
            if scale_up_thresholds:
                # Scale up based on most critical threshold
                critical_threshold = max(scale_up_thresholds, key=lambda t: t.value)
                multiplier = 1.5 if policy.resource_priority == ResourcePriority.CRITICAL else 1.2
                target_replicas = min(
                    int(current_replicas * multiplier),
                    policy.max_replicas
                )
                
                return ScalingAction(
                    component=policy.component,
                    direction=ScalingDirection.UP,
                    target_replicas=target_replicas,
                    reason=f"Threshold exceeded: {critical_threshold.metric} {critical_threshold.operator} {critical_threshold.value}",
                    confidence=0.9,
                    policy_name=policy.name,
                    timestamp=time.time()
                )
            
            elif scale_down_thresholds and current_replicas > policy.min_replicas:
                # Scale down conservatively
                target_replicas = max(
                    int(current_replicas * 0.8),
                    policy.min_replicas
                )
                
                return ScalingAction(
                    component=policy.component,
                    direction=ScalingDirection.DOWN,
                    target_replicas=target_replicas,
                    reason=f"Threshold met: metrics below thresholds",
                    confidence=0.7,
                    policy_name=policy.name,
                    timestamp=time.time()
                )
        
        return None
    
    def _evaluate_schedule_policy(self, policy: ScalingPolicy,
                               current_time: float) -> Optional[ScalingAction]:
        """Evaluate schedule-based policy"""
        current_dt = datetime.fromtimestamp(current_time)
        
        for schedule in policy.schedules:
            if self._is_schedule_active(schedule, current_dt):
                target_replicas = self._get_schedule_replicas(schedule, current_dt)
                current_replicas = self._get_current_replicas(policy.component)
                
                if target_replicas != current_replicas:
                    return ScalingAction(
                        component=policy.component,
                        direction=ScalingDirection.UP if target_replicas > current_replicas else ScalingDirection.DOWN,
                        target_replicas=target_replicas,
                        reason=f"Schedule-based scaling: {schedule.name}",
                        confidence=1.0,
                        policy_name=policy.name,
                        timestamp=current_time
                    )
        
        return None
    
    def _evaluate_predictive_policy(self, policy: ScalingPolicy,
                                  component_metrics: Dict[str, float]) -> Optional[ScalingAction]:
        """Evaluate predictive policy"""
        # This would integrate with the predictive autoscaler
        # For now, use simple trend analysis
        cpu_util = component_metrics.get('cpu_utilization', 0)
        trend = component_metrics.get('cpu_trend', 0)
        
        if trend > 0.1 and cpu_util > 70:  # Increasing trend and high utilization
            current_replicas = component_metrics.get('current_replicas', policy.default_replicas)
            target_replicas = min(current_replicas + 1, policy.max_replicas)
            
            return ScalingAction(
                component=policy.component,
                direction=ScalingDirection.UP,
                target_replicas=target_replicas,
                reason=f"Predictive scaling: increasing CPU trend detected",
                confidence=0.8,
                policy_name=policy.name,
                timestamp=time.time()
            )
        
        elif trend < -0.1 and cpu_util < 40:  # Decreasing trend and low utilization
            current_replicas = component_metrics.get('current_replicas', policy.default_replicas)
            target_replicas = max(current_replicas - 1, policy.min_replicas)
            
            return ScalingAction(
                component=policy.component,
                direction=ScalingDirection.DOWN,
                target_replicas=target_replicas,
                reason=f"Predictive scaling: decreasing CPU trend detected",
                confidence=0.7,
                policy_name=policy.name,
                timestamp=time.time()
            )
        
        return None
    
    def _evaluate_custom_policy(self, policy: ScalingPolicy,
                              component_metrics: Dict[str, float]) -> Optional[ScalingAction]:
        """Evaluate custom policy rules"""
        for rule in policy.custom_rules:
            if self._evaluate_custom_rule(rule, component_metrics):
                current_replicas = component_metrics.get('current_replicas', policy.default_replicas)
                
                if rule.get('action') == 'scale_up':
                    multiplier = rule.get('multiplier', 1.2)
                    target_replicas = min(
                        int(current_replicas * multiplier),
                        policy.max_replicas
                    )
                    
                    return ScalingAction(
                        component=policy.component,
                        direction=ScalingDirection.UP,
                        target_replicas=target_replicas,
                        reason=f"Custom rule triggered: {rule.get('type', 'unknown')}",
                        confidence=0.8,
                        policy_name=policy.name,
                        timestamp=time.time()
                    )
                
                elif rule.get('action') == 'scale_down':
                    min_replicas = rule.get('min_replicas', policy.min_replicas)
                    target_replicas = max(min_replicas, int(current_replicas * 0.8))
                    
                    return ScalingAction(
                        component=policy.component,
                        direction=ScalingDirection.DOWN,
                        target_replicas=target_replicas,
                        reason=f"Custom rule triggered: {rule.get('type', 'unknown')}",
                        confidence=0.7,
                        policy_name=policy.name,
                        timestamp=time.time()
                    )
        
        return None
    
    def _evaluate_threshold(self, threshold: ScalingThreshold, value: float) -> bool:
        """Evaluate if threshold is met"""
        if threshold.operator == '>':
            return value > threshold.value
        elif threshold.operator == '<':
            return value < threshold.value
        elif threshold.operator == '>=':
            return value >= threshold.value
        elif threshold.operator == '<=':
            return value <= threshold.value
        elif threshold.operator == '==':
            return abs(value - threshold.value) < 0.01
        
        return False
    
    def _is_schedule_active(self, schedule: ScalingSchedule, current_dt: datetime) -> bool:
        """Check if schedule is currently active"""
        # Simple implementation - would need proper timezone handling
        current_weekday = current_dt.strftime('%A').lower()
        current_time = current_dt.time()
        
        for schedule_item in schedule.schedules:
            if current_weekday in [day.lower() for day in schedule_item.get('days', [])]:
                start_time = datetime.strptime(schedule_item['start_time'], '%H:%M').time()
                end_time = datetime.strptime(schedule_item['end_time'], '%H:%M').time()
                
                if start_time <= current_time <= end_time:
                    return True
        
        return False
    
    def _get_schedule_replicas(self, schedule: ScalingSchedule, current_dt: datetime) -> int:
        """Get replica count from active schedule"""
        current_weekday = current_dt.strftime('%A').lower()
        current_time = current_dt.time()
        
        for schedule_item in schedule.schedules:
            if current_weekday in [day.lower() for day in schedule_item.get('days', [])]:
                start_time = datetime.strptime(schedule_item['start_time'], '%H:%M').time()
                end_time = datetime.strptime(schedule_item['end_time'], '%H:%M').time()
                
                if start_time <= current_time <= end_time:
                    return schedule_item.get('replicas', 1)
        
        return 1
    
    def _is_in_cooldown(self, policy_name: str, component: str) -> bool:
        """Check if component is in cooldown period"""
        recent_actions = [
            action for action in self.actions_history
            if action.policy_name == policy_name and action.component == component
        ]
        
        if not recent_actions:
            return False
        
        # Get the most recent action
        last_action = max(recent_actions, key=lambda a: a.timestamp)
        time_since_last_action = time.time() - last_action.timestamp
        
        # Get cooldown from policy
        policy = self.policies.get(policy_name)
        if not policy:
            return False
        
        # Use minimum cooldown from all thresholds
        min_cooldown = min([t.cooldown for t in policy.thresholds]) if policy.thresholds else 300
        
        return time_since_last_action < min_cooldown
    
    def _get_current_replicas(self, component: str) -> int:
        """Get current replica count for component"""
        # This would typically query Kubernetes API
        # For now, return a default value
        return 2
    
    def add_policy(self, policy: ScalingPolicy):
        """Add new scaling policy"""
        self.policies[policy.name] = policy
        logger.info(f"Added scaling policy: {policy.name}")
    
    def update_policy(self, policy_name: str, updates: Dict[str, Any]):
        """Update existing scaling policy"""
        if policy_name not in self.policies:
            logger.error(f"Policy {policy_name} not found")
            return
        
        policy = self.policies[policy_name]
        
        # Update policy fields
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        policy.last_modified = time.time()
        logger.info(f"Updated scaling policy: {policy_name}")
    
    def remove_policy(self, policy_name: str):
        """Remove scaling policy"""
        if policy_name in self.policies:
            del self.policies[policy_name]
            logger.info(f"Removed scaling policy: {policy_name}")
    
    def enable_policy(self, policy_name: str):
        """Enable scaling policy"""
        if policy_name in self.policies:
            self.policies[policy_name].enabled = True
            logger.info(f"Enabled scaling policy: {policy_name}")
    
    def disable_policy(self, policy_name: str):
        """Disable scaling policy"""
        if policy_name in self.policies:
            self.policies[policy_name].enabled = False
            logger.info(f"Disabled scaling policy: {policy_name}")
    
    def get_policy_effectiveness(self, policy_name: str) -> Dict[str, float]:
        """Calculate policy effectiveness metrics"""
        if policy_name not in self.policies:
            return {}
        
        policy = self.policies[policy_name]
        policy_actions = [
            action for action in self.actions_history
            if action.policy_name == policy_name
        ]
        
        if not policy_actions:
            return {'effectiveness_score': 0.0}
        
        # Calculate effectiveness based on action outcomes
        total_actions = len(policy_actions)
        successful_actions = len([
            action for action in policy_actions
            if action.confidence > 0.7
        ])
        
        effectiveness_score = successful_actions / total_actions if total_actions > 0 else 0
        
        # Update Prometheus metrics
        self.metrics.policy_effectiveness.labels(
            policy=policy_name,
            component=policy.component
        ).set(effectiveness_score)
        
        return {
            'effectiveness_score': effectiveness_score,
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'last_action_time': max([a.timestamp for a in policy_actions]) if policy_actions else 0
        }
    
    def get_all_policies(self) -> Dict[str, ScalingPolicy]:
        """Get all scaling policies"""
        return self.policies.copy()
    
    def get_active_policies(self) -> Dict[str, ScalingPolicy]:
        """Get only enabled policies"""
        return {name: policy for name, policy in self.policies.items() if policy.enabled}
    
    def export_policies(self, filepath: str):
        """Export policies to YAML file"""
        policies_data = {}
        
        for name, policy in self.policies.items():
            policies_data[name] = asdict(policy)
        
        try:
            with open(filepath, 'w') as f:
                yaml.dump(policies_data, f, default_flow_style=False)
            logger.info(f"Exported policies to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export policies: {e}")
    
    def import_policies(self, filepath: str):
        """Import policies from YAML file"""
        try:
            with open(filepath, 'r') as f:
                policies_data = yaml.safe_load(f)
            
            for name, policy_data in policies_data.items():
                policy = ScalingPolicy(**policy_data)
                self.policies[name] = policy
            
            logger.info(f"Imported {len(policies_data)} policies from {filepath}")
        except Exception as e:
            logger.error(f"Failed to import policies: {e}")

# Example usage
if __name__ == "__main__":
    config = {
        'custom_policies': [
            {
                'name': 'custom-ml-policy',
                'component': 'backend',
                'policy_type': 'custom',
                'min_replicas': 1,
                'max_replicas': 8,
                'default_replicas': 2,
                'resource_priority': 'high',
                'thresholds': [
                    {
                        'metric': 'cpu_utilization',
                        'operator': '>',
                        'value': 85.0,
                        'duration': 120,
                        'cooldown': 300
                    }
                ],
                'schedules': [],
                'custom_rules': [
                    {
                        'type': 'ml_model_load',
                        'condition': 'high_prediction_volume',
                        'action': 'scale_up',
                        'multiplier': 1.3
                    }
                ],
                'enabled': True
            }
        ]
    }
    
    manager = ScalingPolicyManager(config)
    
    # Example evaluation
    metrics = {
        'frontend': {
            'cpu_utilization': 85.0,
            'memory_utilization': 70.0,
            'request_rate': 1200.0,
            'current_replicas': 3
        },
        'backend': {
            'cpu_utilization': 65.0,
            'memory_utilization': 60.0,
            'ml_queue_length': 150.0,
            'current_replicas': 3
        }
    }
    
    async def test_evaluation():
        actions = await manager.evaluate_policies(metrics)
        print(f"Triggered {len(actions)} scaling actions:")
        for action in actions:
            print(f"  {action.component}: {action.direction} to {action.target_replicas} replicas")
    
    asyncio.run(test_evaluation())
