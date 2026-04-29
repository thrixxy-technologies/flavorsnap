"""
Intelligent Auto-Scaler with Predictive Scaling and Cost Optimization
Implements advanced auto-scaling with machine learning predictions and cost optimization
"""

import asyncio
import time
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import pickle
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import prometheus_client as prom
import aiohttp
import aioredis
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScalingDirection(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_CHANGE = "no_change"

class ScalingAlgorithm(Enum):
    REACTIVE = "reactive"
    PREDICTIVE = "predictive"
    HYBRID = "hybrid"
    SCHEDULED = "scheduled"

class CostOptimizationStrategy(Enum):
    COST_FIRST = "cost_first"
    PERFORMANCE_FIRST = "performance_first"
    BALANCED = "balanced"

@dataclass
class ScalingMetrics:
    timestamp: float
    cpu_utilization: float
    memory_utilization: float
    request_rate: float
    response_time: float
    error_rate: float
    queue_length: float
    active_connections: float
    pod_count: int
    node_count: int
    cost_per_hour: float

@dataclass
class ScalingDecision:
    direction: ScalingDirection
    target_replicas: int
    confidence: float
    reasoning: str
    predicted_metrics: Dict[str, float]
    cost_impact: float
    performance_impact: float

@dataclass
class ScalingPolicy:
    name: str
    min_replicas: int
    max_replicas: int
    scale_up_threshold: float
    scale_down_threshold: float
    scale_up_cooldown: int
    scale_down_cooldown: int
    predictive_enabled: bool
    cost_optimization_enabled: bool
    algorithm: ScalingAlgorithm
    custom_metrics: List[str]

class PrometheusMetrics:
    """Prometheus metrics for autoscaler"""
    
    def __init__(self):
        self.scaling_events = prom.Counter(
            'autoscaler_scaling_events_total',
            'Total scaling events',
            ['direction', 'algorithm', 'confidence_level']
        )
        
        self.scaling_decisions = prom.Histogram(
            'autoscaler_scaling_decisions',
            'Scaling decision confidence',
            ['algorithm']
        )
        
        self.prediction_accuracy = prom.Gauge(
            'autoscaler_prediction_accuracy',
            'Prediction accuracy percentage',
            ['model_type']
        )
        
        self.cost_savings = prom.Gauge(
            'autoscaler_cost_savings_hourly',
            'Hourly cost savings from optimization',
            ['strategy']
        )
        
        self.performance_score = prom.Gauge(
            'autoscaler_performance_score',
            'Overall performance score',
            ['component']
        )
        
        self.resource_utilization = prom.Gauge(
            'autoscaler_resource_utilization',
            'Current resource utilization',
            ['resource', 'component']
        )
        
        self.scaling_latency = prom.Histogram(
            'autoscaler_scaling_latency_seconds',
            'Time to make scaling decision',
            ['algorithm']
        )

class PredictiveModel:
    """Machine learning model for predictive scaling"""
    
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'cpu_utilization', 'memory_utilization', 'request_rate',
            'response_time', 'error_rate', 'queue_length',
            'active_connections', 'hour_of_day', 'day_of_week',
            'pod_count', 'node_count'
        ]
        
    def _create_model(self):
        """Create ML model based on type"""
        if self.model_type == "random_forest":
            return RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=100,
                random_state=42
            )
        else:
            return RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
    
    def prepare_features(self, metrics: List[ScalingMetrics]) -> np.ndarray:
        """Prepare features for ML model"""
        if not metrics:
            return np.array([])
        
        data = []
        for metric in metrics:
            timestamp = datetime.fromtimestamp(metric.timestamp)
            features = [
                metric.cpu_utilization,
                metric.memory_utilization,
                metric.request_rate,
                metric.response_time,
                metric.error_rate,
                metric.queue_length,
                metric.active_connections,
                timestamp.hour,
                timestamp.weekday(),
                metric.pod_count,
                metric.node_count
            ]
            data.append(features)
        
        return np.array(data)
    
    def train(self, training_data: List[ScalingMetrics], 
              target_values: List[float]) -> Dict[str, float]:
        """Train the predictive model"""
        if len(training_data) < 10:
            logger.warning("Insufficient training data")
            return {'error': 'Insufficient data'}
        
        X = self.prepare_features(training_data)
        y = np.array(target_values)
        
        if len(X) == 0:
            return {'error': 'No features prepared'}
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = self._create_model()
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate training metrics
        predictions = self.model.predict(X_scaled)
        mae = mean_absolute_error(y, predictions)
        mse = mean_squared_error(y, predictions)
        
        logger.info(f"Model trained with MAE: {mae:.4f}, MSE: {mse:.4f}")
        
        return {
            'mae': mae,
            'mse': mse,
            'samples': len(training_data)
        }
    
    def predict(self, metrics: List[ScalingMetrics], 
               forecast_minutes: int = 30) -> Dict[str, Any]:
        """Make predictions for future metrics"""
        if not self.is_trained:
            return {'error': 'Model not trained'}
        
        if not metrics:
            return {'error': 'No metrics provided'}
        
        # Prepare features
        X = self.prepare_features(metrics[-1:])  # Use latest metrics
        if len(X) == 0:
            return {'error': 'No features prepared'}
        
        X_scaled = self.scaler.transform(X)
        
        # Make prediction
        prediction = self.model.predict(X_scaled)[0]
        
        # Calculate confidence based on historical accuracy
        confidence = max(0.5, min(0.95, 1.0 - (self.model_type == "random_forest") * 0.1))
        
        # Predict future values with trend analysis
        current_time = time.time()
        future_time = current_time + (forecast_minutes * 60)
        
        return {
            'predicted_value': prediction,
            'confidence': confidence,
            'forecast_time': future_time,
            'current_value': metrics[-1].cpu_utilization if metrics else 0,
            'trend': 'increasing' if prediction > metrics[-1].cpu_utilization else 'decreasing'
        }
    
    def save_model(self, filepath: str):
        """Save trained model to file"""
        if self.is_trained and self.model:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'model_type': self.model_type,
                'feature_columns': self.feature_columns,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model from file"""
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.model_type = model_data['model_type']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = model_data['is_trained']
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

class CostOptimizer:
    """Cost optimization algorithms for auto-scaling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cost_per_cpu_hour = config.get('cost_per_cpu_hour', 0.05)
        self.cost_per_gb_memory_hour = config.get('cost_per_gb_memory_hour', 0.01)
        self.cost_per_node_hour = config.get('cost_per_node_hour', 0.10)
        self.spot_instance_discount = config.get('spot_instance_discount', 0.7)
    
    def calculate_pod_cost(self, cpu_request: float, memory_request_gb: float, 
                         hours: float = 1.0) -> float:
        """Calculate cost for a pod"""
        cpu_cost = cpu_request * self.cost_per_cpu_hour * hours
        memory_cost = memory_request_gb * self.cost_per_gb_memory_hour * hours
        return cpu_cost + memory_cost
    
    def calculate_cluster_cost(self, pod_configs: List[Dict[str, Any]], 
                            node_count: int = 1) -> float:
        """Calculate total cluster cost"""
        total_pod_cost = 0
        for pod_config in pod_configs:
            cpu_cost = pod_config['cpu'] * self.cost_per_cpu_hour
            memory_cost = (pod_config['memory'] / 1024) * self.cost_per_gb_memory_hour
            total_pod_cost += cpu_cost + memory_cost
        
        node_cost = node_count * self.cost_per_node_hour
        return total_pod_cost + node_cost
    
    def optimize_replicas_for_cost(self, current_replicas: int, 
                                target_replicas: int,
                                cpu_per_pod: float,
                                memory_per_pod_mb: float,
                                strategy: CostOptimizationStrategy = CostOptimizationStrategy.BALANCED) -> int:
        """Optimize replica count for cost efficiency"""
        memory_per_pod_gb = memory_per_pod_mb / 1024
        
        if strategy == CostOptimizationStrategy.COST_FIRST:
            # Minimize cost while meeting minimum requirements
            min_required = max(1, int(current_replicas * 0.8))
            return min(target_replicas, max(min_required, 1))
        
        elif strategy == CostOptimizationStrategy.PERFORMANCE_FIRST:
            # Prioritize performance over cost
            return target_replicas
        
        else:  # BALANCED
            # Find optimal balance between cost and performance
            cost_per_replica = self.calculate_pod_cost(cpu_per_pod, memory_per_pod_gb)
            performance_gain = (target_replicas - current_replicas) / current_replicas
            
            # Apply cost optimization if performance gain is small
            if performance_gain < 0.2:  # Less than 20% performance gain
                return min(target_replicas, max(current_replicas, 1))
            
            return target_replicas
    
    def recommend_spot_instances(self, total_cpu: float, total_memory_gb: float) -> Dict[str, Any]:
        """Recommend spot instance usage for cost savings"""
        regular_cost = self.calculate_pod_cost(total_cpu, total_memory_gb)
        spot_cost = regular_cost * self.spot_instance_discount
        savings = regular_cost - spot_cost
        
        return {
            'regular_cost': regular_cost,
            'spot_cost': spot_cost,
            'hourly_savings': savings,
            'savings_percentage': (savings / regular_cost) * 100,
            'recommended_spot_ratio': min(0.5, total_cpu / 10),  # Max 50% spot
            'risk_level': 'medium' if savings > 0.1 else 'low'
        }

class IntelligentAutoscaler:
    """Intelligent auto-scaler with predictive capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.k8s_client = None
        self.redis_client = None
        self.predictive_model = PredictiveModel(
            config.get('model_type', 'random_forest')
        )
        self.cost_optimizer = CostOptimizer(config.get('cost', {}))
        
        # Metrics storage
        self.metrics_history: List[ScalingMetrics] = []
        self.scaling_policies: Dict[str, ScalingPolicy] = {}
        self.last_scaling_events: Dict[str, float] = {}
        
        # Prometheus metrics
        self.metrics = PrometheusMetrics()
        
        # Initialize components
        self._initialize_kubernetes()
        self._initialize_policies()
        self._load_model()
    
    def _initialize_kubernetes(self):
        """Initialize Kubernetes client"""
        try:
            config.load_incluster_config()
        except:
            try:
                config.load_kube_config()
            except:
                logger.error("Could not load Kubernetes configuration")
                return
        
        self.k8s_client = client.AppsV1Api()
        logger.info("Kubernetes client initialized")
    
    def _initialize_policies(self):
        """Initialize scaling policies"""
        default_policies = {
            'frontend': ScalingPolicy(
                name='frontend',
                min_replicas=2,
                max_replicas=20,
                scale_up_threshold=70,
                scale_down_threshold=40,
                scale_up_cooldown=60,
                scale_down_cooldown=300,
                predictive_enabled=True,
                cost_optimization_enabled=True,
                algorithm=ScalingAlgorithm.HYBRID,
                custom_metrics=['http_requests_per_second', 'response_time_p95']
            ),
            'backend': ScalingPolicy(
                name='backend',
                min_replicas=2,
                max_replicas=10,
                scale_up_threshold=70,
                scale_down_threshold=40,
                scale_up_cooldown=60,
                scale_down_cooldown=300,
                predictive_enabled=True,
                cost_optimization_enabled=True,
                algorithm=ScalingAlgorithm.HYBRID,
                custom_metrics=['ml_requests_per_second', 'processing_time']
            ),
            'load-balancer': ScalingPolicy(
                name='load-balancer',
                min_replicas=2,
                max_replicas=5,
                scale_up_threshold=80,
                scale_down_threshold=30,
                scale_up_cooldown=30,
                scale_down_cooldown=180,
                predictive_enabled=False,
                cost_optimization_enabled=True,
                algorithm=ScalingAlgorithm.REACTIVE,
                custom_metrics=['nginx_connections', 'request_rate']
            )
        }
        
        self.scaling_policies.update(default_policies)
        logger.info("Scaling policies initialized")
    
    def _load_model(self):
        """Load pre-trained predictive model"""
        model_path = self.config.get('model_path', '/models/scaling_model.pkl')
        if self.predictive_model.load_model(model_path):
            logger.info("Predictive model loaded successfully")
        else:
            logger.info("No pre-trained model found, will train on collected data")
    
    async def collect_metrics(self) -> Dict[str, ScalingMetrics]:
        """Collect current metrics from all components"""
        metrics = {}
        
        try:
            # Collect metrics from Prometheus
            async with aiohttp.ClientSession() as session:
                # Frontend metrics
                frontend_metrics = await self._collect_component_metrics(
                    session, 'frontend'
                )
                if frontend_metrics:
                    metrics['frontend'] = frontend_metrics
                
                # Backend metrics
                backend_metrics = await self._collect_component_metrics(
                    session, 'backend'
                )
                if backend_metrics:
                    metrics['backend'] = backend_metrics
                
                # Load balancer metrics
                lb_metrics = await self._collect_component_metrics(
                    session, 'load-balancer'
                )
                if lb_metrics:
                    metrics['load-balancer'] = lb_metrics
        
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    async def _collect_component_metrics(self, session: aiohttp.ClientSession, 
                                   component: str) -> Optional[ScalingMetrics]:
        """Collect metrics for a specific component"""
        try:
            # Query Prometheus for metrics
            prometheus_url = self.config.get('prometheus_url', 'http://prometheus:9090')
            
            queries = {
                'cpu': f'avg(rate(container_cpu_usage_seconds_total{{pod=~"{component}-.*"}}[5m])) * 100',
                'memory': f'avg(container_memory_usage_bytes{{pod=~"{component}-.*"}}) / (1024*1024*1024) * 100',
                'request_rate': f'sum(rate(http_requests_total{{pod=~"{component}-.*"}}[5m]))',
                'response_time': f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{pod=~"{component}-.*"}}[5m]))',
                'error_rate': f'sum(rate(http_requests_total{{pod=~"{component}-.*",status=~"5.."}}[5m])) / sum(rate(http_requests_total{{pod=~"{component}-.*"}}[5m])) * 100',
                'pod_count': f'count(kube_pod_info{{pod=~"{component}-.*"}})'
            }
            
            metric_values = {}
            for metric_name, query in queries.items():
                try:
                    async with session.get(
                        f"{prometheus_url}/api/v1/query",
                        params={'query': query}
                    ) as response:
                        data = await response.json()
                        if data['status'] == 'success' and data['data']['result']:
                            metric_values[metric_name] = float(
                                data['data']['result'][0]['value'][1]
                            )
                        else:
                            metric_values[metric_name] = 0.0
                except Exception as e:
                    logger.debug(f"Error querying {metric_name}: {e}")
                    metric_values[metric_name] = 0.0
            
            # Get current replica count
            try:
                if self.k8s_client:
                    deployment = self.k8s_client.read_namespaced_deployment(
                        name=f"{component}-deployment",
                        namespace=self.config.get('namespace', 'flavorsnap')
                    )
                    current_replicas = deployment.spec.replicas or 0
                else:
                    current_replicas = metric_values.get('pod_count', 0)
            except:
                current_replicas = metric_values.get('pod_count', 0)
            
            # Create metrics object
            scaling_metrics = ScalingMetrics(
                timestamp=time.time(),
                cpu_utilization=metric_values.get('cpu', 0.0),
                memory_utilization=metric_values.get('memory', 0.0),
                request_rate=metric_values.get('request_rate', 0.0),
                response_time=metric_values.get('response_time', 0.0),
                error_rate=metric_values.get('error_rate', 0.0),
                queue_length=0.0,  # Would need custom metric
                active_connections=0.0,  # Would need custom metric
                pod_count=int(current_replicas),
                node_count=1,  # Would need cluster info
                cost_per_hour=self.cost_optimizer.calculate_pod_cost(
                    metric_values.get('cpu', 0.0) / 100,
                    metric_values.get('memory', 0.0) / 100
                )
            )
            
            # Update Prometheus metrics
            self.metrics.resource_utilization.labels(
                resource='cpu', component=component
            ).set(metric_values.get('cpu', 0.0))
            
            self.metrics.resource_utilization.labels(
                resource='memory', component=component
            ).set(metric_values.get('memory', 0.0))
            
            return scaling_metrics
            
        except Exception as e:
            logger.error(f"Error collecting {component} metrics: {e}")
            return None
    
    def make_scaling_decision(self, component: str, 
                          current_metrics: ScalingMetrics,
                          policy: ScalingPolicy) -> ScalingDecision:
        """Make scaling decision for a component"""
        start_time = time.time()
        
        # Check cooldown periods
        last_scale_time = self.last_scaling_events.get(component, 0)
        time_since_last_scale = time.time() - last_scale_time
        
        if time_since_last_scale < min(policy.scale_up_cooldown, policy.scale_down_cooldown):
            return ScalingDecision(
                direction=ScalingDirection.NO_CHANGE,
                target_replicas=current_metrics.pod_count,
                confidence=1.0,
                reasoning=f"Cooldown period active ({time_since_last_change:.0f}s remaining)",
                predicted_metrics={},
                cost_impact=0.0,
                performance_impact=0.0
            )
        
        # Reactive scaling decision
        reactive_decision = self._make_reactive_decision(current_metrics, policy)
        
        # Predictive scaling decision
        predictive_decision = None
        if policy.predictive_enabled and self.predictive_model.is_trained:
            predictive_decision = self._make_predictive_decision(
                current_metrics, policy
            )
        
        # Combine decisions based on algorithm
        final_decision = self._combine_decisions(
            reactive_decision, predictive_decision, policy
        )
        
        # Apply cost optimization
        if policy.cost_optimization_enabled:
            final_decision = self._apply_cost_optimization(
                final_decision, current_metrics, policy
            )
        
        # Update metrics
        decision_time = time.time() - start_time
        self.metrics.scaling_decisions.labels(
            algorithm=policy.algorithm.value
        ).observe(final_decision.confidence)
        
        self.metrics.scaling_latency.labels(
            algorithm=policy.algorithm.value
        ).observe(decision_time)
        
        return final_decision
    
    def _make_reactive_decision(self, metrics: ScalingMetrics, 
                              policy: ScalingPolicy) -> ScalingDecision:
        """Make reactive scaling decision based on current metrics"""
        current_replicas = metrics.pod_count
        
        # Scale up conditions
        scale_up_conditions = [
            metrics.cpu_utilization > policy.scale_up_threshold,
            metrics.memory_utilization > policy.scale_up_threshold,
            metrics.request_rate > (current_replicas * 100),  # 100 req/s per pod
            metrics.response_time > 1.0,  # 1 second response time
            metrics.error_rate > 5.0  # 5% error rate
        ]
        
        # Scale down conditions
        scale_down_conditions = [
            metrics.cpu_utilization < policy.scale_down_threshold,
            metrics.memory_utilization < policy.scale_down_threshold,
            metrics.request_rate < (current_replicas * 50),  # 50 req/s per pod
            metrics.response_time < 0.5,  # 0.5 second response time
            metrics.error_rate < 1.0  # 1% error rate
        ]
        
        if any(scale_up_conditions):
            target_replicas = min(current_replicas + 1, policy.max_replicas)
            return ScalingDecision(
                direction=ScalingDirection.SCALE_UP,
                target_replicas=target_replicas,
                confidence=0.8,
                reasoning=f"Scale up triggered: {self._get_trigger_reason(scale_up_conditions, metrics)}",
                predicted_metrics={'cpu': metrics.cpu_utilization},
                cost_impact=(target_replicas - current_replicas) * metrics.cost_per_hour,
                performance_impact=0.2
            )
        elif all(scale_down_conditions) and current_replicas > policy.min_replicas:
            target_replicas = max(current_replicas - 1, policy.min_replicas)
            return ScalingDecision(
                direction=ScalingDirection.SCALE_DOWN,
                target_replicas=target_replicas,
                confidence=0.7,
                reasoning=f"Scale down triggered: all metrics below thresholds",
                predicted_metrics={'cpu': metrics.cpu_utilization},
                cost_impact=(target_replicas - current_replicas) * metrics.cost_per_hour,
                performance_impact=-0.1
            )
        else:
            return ScalingDecision(
                direction=ScalingDirection.NO_CHANGE,
                target_replicas=current_replicas,
                confidence=0.9,
                reasoning="No scaling conditions met",
                predicted_metrics={'cpu': metrics.cpu_utilization},
                cost_impact=0.0,
                performance_impact=0.0
            )
    
    def _make_predictive_decision(self, metrics: ScalingMetrics,
                               policy: ScalingPolicy) -> Optional[ScalingDecision]:
        """Make predictive scaling decision using ML model"""
        try:
            # Get recent metrics for prediction
            recent_metrics = [m for m in self.metrics_history 
                            if time.time() - m.timestamp < 3600]  # Last hour
            
            if len(recent_metrics) < 10:
                return None
            
            # Make prediction
            prediction = self.predictive_model.predict(
                recent_metrics, forecast_minutes=30
            )
            
            if 'error' in prediction:
                return None
            
            predicted_cpu = prediction['predicted_value']
            confidence = prediction['confidence']
            trend = prediction['trend']
            
            current_replicas = metrics.pod_count
            
            # Scale up if prediction shows increasing trend
            if (trend == 'increasing' and 
                predicted_cpu > policy.scale_up_threshold and
                confidence > 0.7):
                
                target_replicas = min(
                    current_replicas + 1, 
                    policy.max_replicas
                )
                
                return ScalingDecision(
                    direction=ScalingDirection.SCALE_UP,
                    target_replicas=target_replicas,
                    confidence=confidence,
                    reasoning=f"Predictive scale up: CPU predicted to reach {predicted_cpu:.1f}% (trend: {trend})",
                    predicted_metrics={'predicted_cpu': predicted_cpu, 'trend': trend},
                    cost_impact=(target_replicas - current_replicas) * metrics.cost_per_hour,
                    performance_impact=0.3
                )
            
            # Scale down if prediction shows decreasing trend
            elif (trend == 'decreasing' and 
                  predicted_cpu < policy.scale_down_threshold and
                  confidence > 0.7 and
                  current_replicas > policy.min_replicas):
                
                target_replicas = max(
                    current_replicas - 1,
                    policy.min_replicas
                )
                
                return ScalingDecision(
                    direction=ScalingDirection.SCALE_DOWN,
                    target_replicas=target_replicas,
                    confidence=confidence,
                    reasoning=f"Predictive scale down: CPU predicted to drop to {predicted_cpu:.1f}% (trend: {trend})",
                    predicted_metrics={'predicted_cpu': predicted_cpu, 'trend': trend},
                    cost_impact=(target_replicas - current_replicas) * metrics.cost_per_hour,
                    performance_impact=-0.15
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in predictive decision: {e}")
            return None
    
    def _combine_decisions(self, reactive: ScalingDecision,
                         predictive: Optional[ScalingDecision],
                         policy: ScalingPolicy) -> ScalingDecision:
        """Combine reactive and predictive decisions"""
        if policy.algorithm == ScalingAlgorithm.REACTIVE:
            return reactive
        
        elif policy.algorithm == ScalingAlgorithm.PREDICTIVE:
            return predictive or reactive
        
        elif policy.algorithm == ScalingAlgorithm.HYBRID:
            # Combine both decisions with confidence weighting
            if predictive and predictive.confidence > reactive.confidence:
                return predictive
            else:
                return reactive
        
        else:  # SCHEDULED
            return reactive  # Fallback to reactive
    
    def _apply_cost_optimization(self, decision: ScalingDecision,
                               metrics: ScalingMetrics,
                               policy: ScalingPolicy) -> ScalingDecision:
        """Apply cost optimization to scaling decision"""
        if decision.direction == ScalingDirection.NO_CHANGE:
            return decision
        
        strategy = CostOptimizationStrategy(
            self.config.get('cost_optimization_strategy', 'balanced')
        )
        
        optimized_replicas = self.cost_optimizer.optimize_replicas_for_cost(
            current_replicas=metrics.pod_count,
            target_replicas=decision.target_replicas,
            cpu_per_pod=metrics.cpu_utilization / 100,
            memory_per_pod_mb=metrics.memory_utilization,
            strategy=strategy
        )
        
        if optimized_replicas != decision.target_replicas:
            decision.target_replicas = optimized_replicas
            decision.reasoning += f" (cost optimized: {strategy.value})"
            decision.cost_impact = (
                optimized_replicas - metrics.pod_count
            ) * metrics.cost_per_hour
        
        return decision
    
    def _get_trigger_reason(self, conditions: List[bool], 
                          metrics: ScalingMetrics) -> str:
        """Get human-readable reason for scaling trigger"""
        reasons = []
        
        if conditions[0]:
            reasons.append(f"CPU {metrics.cpu_utilization:.1f}%")
        if conditions[1]:
            reasons.append(f"Memory {metrics.memory_utilization:.1f}%")
        if conditions[2]:
            reasons.append(f"Request rate {metrics.request_rate:.1f}/s")
        if conditions[3]:
            reasons.append(f"Response time {metrics.response_time:.3f}s")
        if conditions[4]:
            reasons.append(f"Error rate {metrics.error_rate:.1f}%")
        
        return ", ".join(reasons)
    
    async def apply_scaling_decision(self, component: str, 
                                decision: ScalingDecision) -> bool:
        """Apply scaling decision to Kubernetes"""
        if decision.direction == ScalingDirection.NO_CHANGE:
            return True
        
        try:
            if not self.k8s_client:
                logger.error("Kubernetes client not initialized")
                return False
            
            deployment_name = f"{component}-deployment"
            namespace = self.config.get('namespace', 'flavorsnap')
            
            # Get current deployment
            deployment = self.k8s_client.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            # Update replica count
            deployment.spec.replicas = decision.target_replicas
            
            # Apply patch
            self.k8s_client.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            # Record scaling event
            self.last_scaling_events[component] = time.time()
            
            # Update Prometheus metrics
            self.metrics.scaling_events.labels(
                direction=decision.direction.value,
                algorithm=self.scaling_policies[component].algorithm.value,
                confidence_level=f"{int(decision.confidence * 10)}x"
            ).inc()
            
            logger.info(f"Scaling {component} to {decision.target_replicas} replicas: {decision.reasoning}")
            
            return True
            
        except ApiException as e:
            logger.error(f"Kubernetes API error scaling {component}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error scaling {component}: {e}")
            return False
    
    async def train_predictive_model(self):
        """Train predictive model with collected metrics"""
        try:
            # Get training data from history
            if len(self.metrics_history) < 100:
                logger.info("Insufficient data for training (need at least 100 samples)")
                return
            
            # Prepare training data
            X = []
            y = []
            
            for i in range(10, len(self.metrics_history)):
                # Use 10 previous metrics to predict next CPU utilization
                features = []
                for j in range(i-10, i):
                    metric = self.metrics_history[j]
                    features.extend([
                        metric.cpu_utilization,
                        metric.memory_utilization,
                        metric.request_rate,
                        metric.response_time,
                        metric.error_rate
                    ])
                
                X.append(features)
                y.append(self.metrics_history[i].cpu_utilization)
            
            if len(X) < 50:
                logger.info("Insufficient training samples")
                return
            
            # Train model
            training_metrics = []
            target_values = []
            
            for i, metric in enumerate(self.metrics_history[10:]):
                training_metrics.append(metric)
                target_values.append(metric.cpu_utilization)
            
            result = self.predictive_model.train(training_metrics, target_values)
            
            if 'error' not in result:
                # Save trained model
                model_path = self.config.get('model_path', '/models/scaling_model.pkl')
                self.predictive_model.save_model(model_path)
                
                # Update prediction accuracy metric
                self.metrics.prediction_accuracy.labels(
                    model_type=self.predictive_model.model_type
                ).set(1.0 - result['mae'] / 100)  # Convert to accuracy percentage
                
                logger.info(f"Model training completed: {result}")
            else:
                logger.error(f"Model training failed: {result}")
                
        except Exception as e:
            logger.error(f"Error training predictive model: {e}")
    
    async def run_scaling_loop(self):
        """Main scaling loop"""
        logger.info("Starting intelligent auto-scaler")
        
        while True:
            try:
                # Collect current metrics
                current_metrics = await self.collect_metrics()
                
                # Store metrics in history
                for component, metrics in current_metrics.items():
                    self.metrics_history.append(metrics)
                
                # Keep only last 24 hours of metrics
                cutoff_time = time.time() - 86400  # 24 hours
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
                # Make scaling decisions for each component
                for component, metrics in current_metrics.items():
                    if component in self.scaling_policies:
                        policy = self.scaling_policies[component]
                        
                        # Make scaling decision
                        decision = self.make_scaling_decision(
                            component, metrics, policy
                        )
                        
                        # Apply scaling decision
                        if decision.direction != ScalingDirection.NO_CHANGE:
                            await self.apply_scaling_decision(component, decision)
                
                # Train predictive model periodically
                if time.time() % 3600 < 60:  # Every hour
                    await self.train_predictive_model()
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status"""
        status = {
            'components': {},
            'model_status': {
                'is_trained': self.predictive_model.is_trained,
                'model_type': self.predictive_model.model_type
            },
            'metrics_history_size': len(self.metrics_history),
            'last_scaling_events': self.last_scaling_events
        }
        
        for component, policy in self.scaling_policies.items():
            status['components'][component] = {
                'policy': asdict(policy),
                'last_scale_time': self.last_scaling_events.get(component, 0)
            }
        
        return status

# Example usage
if __name__ == "__main__":
    config = {
        'namespace': 'flavorsnap',
        'prometheus_url': 'http://prometheus:9090',
        'model_path': '/models/scaling_model.pkl',
        'model_type': 'random_forest',
        'cost_optimization_strategy': 'balanced',
        'cost': {
            'cost_per_cpu_hour': 0.05,
            'cost_per_gb_memory_hour': 0.01,
            'cost_per_node_hour': 0.10,
            'spot_instance_discount': 0.7
        }
    }
    
    autoscaler = IntelligentAutoscaler(config)
    
    # Run the scaling loop
    asyncio.run(autoscaler.run_scaling_loop())
