#!/usr/bin/env python3
"""
Cost Optimization Engine for Auto-Scaling
Implements intelligent cost optimization algorithms and strategies
"""

import asyncio
import time
import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CostOptimizationStrategy(Enum):
    COST_FIRST = "cost_first"
    PERFORMANCE_FIRST = "performance_first"
    BALANCED = "balanced"
    SCHEDULED = "scheduled"
    SPOT_OPTIMIZED = "spot_optimized"

class InstanceType(Enum):
    ON_DEMAND = "on_demand"
    SPOT = "spot"
    RESERVED = "reserved"
    PREEMPTIBLE = "preemptible"

@dataclass
class CostMetrics:
    timestamp: float
    component: str
    current_replicas: int
    cpu_request: float
    memory_request_mb: float
    cost_per_hour: float
    instance_type: InstanceType
    utilization_score: float
    performance_score: float
    efficiency_score: float

@dataclass
class CostOptimization:
    component: str
    current_cost: float
    optimized_cost: float
    savings_per_hour: float
    savings_percentage: float
    recommended_replicas: int
    recommended_instance_type: InstanceType
    confidence: float
    reasoning: str
    implementation_time: timedelta

class PrometheusMetrics:
    """Prometheus metrics for cost optimization"""
    
    def __init__(self):
        self.cost_optimization_events = prom.Counter(
            'cost_optimizer_events_total',
            'Total cost optimization events',
            ['strategy', 'component', 'action']
        )
        
        self.cost_savings = prom.Gauge(
            'cost_optimizer_savings_hourly',
            'Hourly cost savings from optimization',
            ['strategy', 'component']
        )
        
        self.efficiency_score = prom.Gauge(
            'cost_optimizer_efficiency_score',
            'Cost efficiency score',
            ['component']
        )
        
        self.optimization_recommendations = prom.Gauge(
            'cost_optimizer_recommendations',
            'Active optimization recommendations',
            ['component', 'type']
        )
        
        self.instance_type_distribution = prom.Gauge(
            'cost_optimizer_instance_distribution',
            'Instance type distribution',
            ['instance_type', 'component']
        )

class CostOptimizer:
    """Advanced cost optimization engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cost_metrics: List[CostMetrics] = []
        self.optimization_history: List[CostOptimization] = []
        
        # Cost configuration
        self.pricing = {
            'on_demand': {
                'cpu_per_hour': config.get('on_demand_cpu_cost', 0.05),
                'memory_per_gb_hour': config.get('on_demand_memory_cost', 0.01),
                'node_per_hour': config.get('on_demand_node_cost', 0.10)
            },
            'spot': {
                'cpu_per_hour': config.get('spot_cpu_cost', 0.03),
                'memory_per_gb_hour': config.get('spot_memory_cost', 0.006),
                'node_per_hour': config.get('spot_node_cost', 0.06),
                'discount': config.get('spot_discount', 0.4)  # 40% discount
            },
            'reserved': {
                'cpu_per_hour': config.get('reserved_cpu_cost', 0.035),
                'memory_per_gb_hour': config.get('reserved_memory_cost', 0.007),
                'node_per_hour': config.get('reserved_node_cost', 0.07),
                'commitment_years': config.get('reserved_years', 1)
            }
        }
        
        # Optimization thresholds
        self.thresholds = {
            'min_savings_percentage': config.get('min_savings_percentage', 10),
            'max_spot_ratio': config.get('max_spot_ratio', 0.5),
            'min_efficiency_score': config.get('min_efficiency_score', 0.7),
            'optimization_interval': config.get('optimization_interval', 300)  # 5 minutes
        }
        
        # Metrics
        self.metrics = PrometheusMetrics()
    
    def calculate_component_cost(self, component: str, replicas: int,
                             cpu_request: float, memory_request_mb: float,
                             instance_type: InstanceType = InstanceType.ON_DEMAND) -> float:
        """Calculate cost for a component"""
        memory_request_gb = memory_request_mb / 1024
        
        if instance_type == InstanceType.ON_DEMAND:
            pricing = self.pricing['on_demand']
        elif instance_type == InstanceType.SPOT:
            pricing = self.pricing['spot']
        elif instance_type == InstanceType.RESERVED:
            pricing = self.pricing['reserved']
        else:
            pricing = self.pricing['on_demand']
        
        # Calculate per-pod cost
        pod_cost = (
            cpu_request * pricing['cpu_per_hour'] +
            memory_request_gb * pricing['memory_per_gb_hour']
        )
        
        # Add node overhead (distributed across replicas)
        node_overhead = pricing['node_per_hour'] / max(1, replicas)
        
        total_cost = (pod_cost + node_overhead) * replicas
        return total_cost
    
    def calculate_efficiency_score(self, component: str, replicas: int,
                               utilization: float, performance: float) -> float:
        """Calculate efficiency score for a component"""
        # Base efficiency from utilization
        utilization_efficiency = min(1.0, utilization / 80.0)  # Target 80% utilization
        
        # Performance factor
        performance_factor = min(1.0, performance / 100.0)
        
        # Replica efficiency (penalize over-provisioning)
        optimal_replicas = self._get_optimal_replicas(component)
        replica_efficiency = min(1.0, optimal_replicas / replicas)
        
        # Combined efficiency score
        efficiency = (
            utilization_efficiency * 0.4 +
            performance_factor * 0.3 +
            replica_efficiency * 0.3
        )
        
        return efficiency
    
    def _get_optimal_replicas(self, component: str) -> int:
        """Get optimal replica count for a component"""
        # Component-specific optimal replicas
        optimal_replicas = {
            'frontend': 3,
            'backend': 2,
            'load-balancer': 2,
            'redis': 1,
            'postgres': 1
        }
        
        return optimal_replicas.get(component, 2)
    
    def analyze_cost_optimization_opportunities(self) -> List[CostOptimization]:
        """Analyze cost optimization opportunities"""
        opportunities = []
        
        for metric in self.cost_metrics[-10:]:  # Analyze last 10 metrics
            # Skip if too recent
            if time.time() - metric.timestamp < 300:
                continue
            
            # Check different optimization strategies
            optimizations = [
                self._optimize_replica_count(metric),
                self._optimize_instance_types(metric),
                self._optimize_spot_usage(metric),
                self._optimize_scheduled_scaling(metric)
            ]
            
            # Find best optimization
            best_optimization = max(optimizations, key=lambda x: x.savings_per_hour)
            
            # Only include if meets minimum savings threshold
            if (best_optimization.savings_percentage >= 
                self.thresholds['min_savings_percentage']):
                opportunities.append(best_optimization)
        
        return opportunities
    
    def _optimize_replica_count(self, metric: CostMetrics) -> CostOptimization:
        """Optimize replica count for cost efficiency"""
        current_cost = metric.cost_per_hour
        current_replicas = metric.current_replicas
        
        # Find optimal replica count based on utilization
        target_utilization = 75.0  # Target 75% utilization
        optimal_replicas = max(
            1, int(current_replicas * metric.utilization_score / target_utilization)
        )
        
        # Calculate cost for optimal replicas
        optimal_cost = self.calculate_component_cost(
            metric.component, optimal_replicas,
            metric.cpu_request, metric.memory_request_mb,
            metric.instance_type
        )
        
        savings = current_cost - optimal_cost
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return CostOptimization(
            component=metric.component,
            current_cost=current_cost,
            optimized_cost=optimal_cost,
            savings_per_hour=savings,
            savings_percentage=savings_percentage,
            recommended_replicas=optimal_replicas,
            recommended_instance_type=metric.instance_type,
            confidence=0.8,
            reasoning=f"Optimize replicas from {current_replicas} to {optimal_replicas} based on {metric.utilization_score:.1f}% utilization",
            implementation_time=timedelta(minutes=5)
        )
    
    def _optimize_instance_types(self, metric: CostMetrics) -> CostOptimization:
        """Optimize instance types for cost efficiency"""
        current_cost = metric.cost_per_hour
        
        # Calculate costs for different instance types
        instance_costs = {}
        for instance_type in [InstanceType.ON_DEMAND, InstanceType.SPOT, InstanceType.RESERVED]:
            cost = self.calculate_component_cost(
                metric.component, metric.current_replicas,
                metric.cpu_request, metric.memory_request_mb,
                instance_type
            )
            instance_costs[instance_type] = cost
        
        # Find cheapest instance type
        cheapest_type = min(instance_costs.keys(), key=lambda x: instance_costs[x])
        cheapest_cost = instance_costs[cheapest_type]
        
        savings = current_cost - cheapest_cost
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        # Apply spot ratio constraints
        if cheapest_type == InstanceType.SPOT:
            max_spot_cost = current_cost * self.thresholds['max_spot_ratio']
            if cheapest_cost < max_spot_cost:
                cheapest_cost = max_spot_cost
                savings = current_cost - cheapest_cost
                savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return CostOptimization(
            component=metric.component,
            current_cost=current_cost,
            optimized_cost=cheapest_cost,
            savings_per_hour=savings,
            savings_percentage=savings_percentage,
            recommended_replicas=metric.current_replicas,
            recommended_instance_type=cheapest_type,
            confidence=0.9,
            reasoning=f"Switch from {metric.instance_type.value} to {cheapest_type.value} for cost savings",
            implementation_time=timedelta(minutes=15)
        )
    
    def _optimize_spot_usage(self, metric: CostMetrics) -> CostOptimization:
        """Optimize spot instance usage"""
        current_cost = metric.cost_per_hour
        current_replicas = metric.current_replicas
        
        # Calculate optimal spot ratio
        spot_ratio = min(
            self.thresholds['max_spot_ratio'],
            1.0 - (metric.utilization_score / 100.0)  # Less utilization = more spot
        )
        
        spot_replicas = max(1, int(current_replicas * spot_ratio))
        on_demand_replicas = current_replicas - spot_replicas
        
        # Calculate mixed cost
        spot_cost = self.calculate_component_cost(
            metric.component, spot_replicas,
            metric.cpu_request, metric.memory_request_mb,
            InstanceType.SPOT
        )
        
        on_demand_cost = self.calculate_component_cost(
            metric.component, on_demand_replicas,
            metric.cpu_request, metric.memory_request_mb,
            InstanceType.ON_DEMAND
        )
        
        optimized_cost = spot_cost + on_demand_cost
        
        savings = current_cost - optimized_cost
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return CostOptimization(
            component=metric.component,
            current_cost=current_cost,
            optimized_cost=optimized_cost,
            savings_per_hour=savings,
            savings_percentage=savings_percentage,
            recommended_replicas=current_replicas,
            recommended_instance_type=InstanceType.SPOT,
            confidence=0.7,
            reasoning=f"Use {spot_replicas} spot and {on_demand_replicas} on-demand instances ({spot_ratio:.1%} spot ratio)",
            implementation_time=timedelta(minutes=30)
        )
    
    def _optimize_scheduled_scaling(self, metric: CostMetrics) -> CostOptimization:
        """Optimize with scheduled scaling patterns"""
        current_cost = metric.cost_per_hour
        
        # Analyze usage patterns (simplified)
        hour = datetime.fromtimestamp(metric.timestamp).hour
        
        # Business hours vs off-hours optimization
        if 9 <= hour <= 17:  # Business hours
            target_multiplier = 1.0
        elif 18 <= hour <= 22:  # Evening
            target_multiplier = 0.7
        else:  # Night/early morning
            target_multiplier = 0.5
        
        optimized_replicas = max(1, int(metric.current_replicas * target_multiplier))
        optimized_cost = self.calculate_component_cost(
            metric.component, optimized_replicas,
            metric.cpu_request, metric.memory_request_mb,
            metric.instance_type
        )
        
        savings = current_cost - optimized_cost
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return CostOptimization(
            component=metric.component,
            current_cost=current_cost,
            optimized_cost=optimized_cost,
            savings_per_hour=savings,
            savings_percentage=savings_percentage,
            recommended_replicas=optimized_replicas,
            recommended_instance_type=metric.instance_type,
            confidence=0.6,
            reasoning=f"Scheduled scaling: {target_multiplier:.0%} of current replicas during {hour}:00",
            implementation_time=timedelta(minutes=10)
        )
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        opportunities = self.analyze_cost_optimization_opportunities()
        
        # Calculate total potential savings
        total_current_cost = sum(op.current_cost for op in opportunities)
        total_optimized_cost = sum(op.optimized_cost for op in opportunities)
        total_savings = total_current_cost - total_optimized_cost
        total_savings_percentage = (total_savings / total_current_cost) * 100 if total_current_cost > 0 else 0
        
        # Group by component
        by_component = {}
        for op in opportunities:
            if op.component not in by_component:
                by_component[op.component] = []
            by_component[op.component].append(op)
        
        # Group by optimization type
        by_type = {
            'replica_optimization': [],
            'instance_optimization': [],
            'spot_optimization': [],
            'scheduled_optimization': []
        }
        
        for op in opportunities:
            if 'replicas' in op.reasoning.lower():
                by_type['replica_optimization'].append(op)
            elif 'instance' in op.reasoning.lower():
                by_type['instance_optimization'].append(op)
            elif 'spot' in op.reasoning.lower():
                by_type['spot_optimization'].append(op)
            elif 'scheduled' in op.reasoning.lower():
                by_type['scheduled_optimization'].append(op)
        
        # Calculate efficiency scores
        efficiency_scores = {}
        for component, metrics in self._group_metrics_by_component().items():
            if metrics:
                latest_metric = metrics[-1]
                efficiency_scores[component] = latest_metric.efficiency_score
        
        report = {
            'timestamp': time.time(),
            'summary': {
                'total_opportunities': len(opportunities),
                'total_current_cost': total_current_cost,
                'total_optimized_cost': total_optimized_cost,
                'total_savings_per_hour': total_savings,
                'total_savings_percentage': total_savings_percentage,
                'components_analyzed': len(by_component)
            },
            'opportunities': [asdict(op) for op in opportunities],
            'by_component': {
                comp: [asdict(op) for op in ops]
                for comp, ops in by_component.items()
            },
            'by_optimization_type': {
                opt_type: [asdict(op) for op in ops]
                for opt_type, ops in by_type.items()
            },
            'efficiency_scores': efficiency_scores,
            'recommendations': self._generate_recommendations(opportunities, efficiency_scores)
        }
        
        return report
    
    def _group_metrics_by_component(self) -> Dict[str, List[CostMetrics]]:
        """Group cost metrics by component"""
        grouped = {}
        for metric in self.cost_metrics:
            if metric.component not in grouped:
                grouped[metric.component] = []
            grouped[metric.component].append(metric)
        return grouped
    
    def _generate_recommendations(self, opportunities: List[CostOptimization],
                               efficiency_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # High-impact optimizations
        high_impact = [op for op in opportunities if op.savings_percentage > 20]
        if high_impact:
            recommendations.append({
                'priority': 'high',
                'type': 'cost_savings',
                'title': 'High-Impact Cost Optimizations Available',
                'description': f"Found {len(high_impact)} optimizations with >20% savings potential",
                'actions': ['review_high_impact_optimizations'],
                'estimated_savings': sum(op.savings_per_hour for op in high_impact)
            })
        
        # Low efficiency components
        low_efficiency = [
            comp for comp, score in efficiency_scores.items()
            if score < self.thresholds['min_efficiency_score']
        ]
        if low_efficiency:
            recommendations.append({
                'priority': 'medium',
                'type': 'efficiency',
                'title': 'Low Efficiency Components Detected',
                'description': f"Components with low efficiency: {', '.join(low_efficiency)}",
                'actions': ['optimize_resource_requests', 'review_scaling_policies'],
                'affected_components': low_efficiency
            })
        
        # Spot instance opportunities
        spot_opportunities = [op for op in opportunities if op.recommended_instance_type == InstanceType.SPOT]
        if spot_opportunities:
            recommendations.append({
                'priority': 'medium',
                'type': 'instance_optimization',
                'title': 'Spot Instance Opportunities',
                'description': f"Potential spot instance optimizations for {len(spot_opportunities)} components",
                'actions': ['enable_spot_instances', 'implement_fallback_mechanisms'],
                'estimated_savings': sum(op.savings_per_hour for op in spot_opportunities)
            })
        
        # Scheduled scaling benefits
        scheduled_opportunities = [op for op in opportunities if 'scheduled' in op.reasoning.lower()]
        if scheduled_opportunities:
            recommendations.append({
                'priority': 'low',
                'type': 'scheduling',
                'title': 'Scheduled Scaling Benefits',
                'description': f"Scheduled scaling can save ${sum(op.savings_per_hour for op in scheduled_opportunities):.2f}/hour",
                'actions': ['implement_scheduled_scaling', 'define_business_hours'],
                'estimated_savings': sum(op.savings_per_hour for op in scheduled_opportunities)
            })
        
        return recommendations
    
    async def apply_optimization(self, optimization: CostOptimization) -> bool:
        """Apply cost optimization"""
        try:
            # Update Prometheus metrics
            self.metrics.cost_optimization_events.labels(
                strategy='cost_optimization',
                component=optimization.component,
                action='apply'
            ).inc()
            
            self.metrics.cost_savings.labels(
                strategy='cost_optimization',
                component=optimization.component
            ).set(optimization.savings_per_hour)
            
            # Log optimization
            logger.info(f"Applying cost optimization for {optimization.component}: {optimization.reasoning}")
            
            # Implementation would depend on the specific optimization type
            # This is a placeholder for the actual implementation
            if optimization.recommended_replicas != optimization.current_cost:
                logger.info(f"Would scale {optimization.component} to {optimization.recommended_replicas} replicas")
            
            if optimization.recommended_instance_type != InstanceType.ON_DEMAND:
                logger.info(f"Would switch {optimization.component} to {optimization.recommended_instance_type.value} instances")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply optimization for {optimization.component}: {e}")
            return False
    
    def update_cost_metrics(self, metrics: List[CostMetrics]):
        """Update cost metrics"""
        self.cost_metrics.extend(metrics)
        
        # Keep only last 24 hours of metrics
        cutoff_time = time.time() - 86400
        self.cost_metrics = [m for m in self.cost_metrics if m.timestamp > cutoff_time]
        
        # Update Prometheus metrics
        for metric in metrics:
            self.metrics.efficiency_score.labels(
                component=metric.component
            ).set(metric.efficiency_score)
            
            self.metrics.instance_type_distribution.labels(
                instance_type=metric.instance_type.value,
                component=metric.component
            ).set(metric.current_replicas)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        recent_metrics = [m for m in self.cost_metrics if time.time() - m.timestamp < 3600]
        
        if not recent_metrics:
            return {'status': 'no_data', 'message': 'No recent cost metrics available'}
        
        total_current_cost = sum(m.cost_per_hour for m in recent_metrics)
        avg_efficiency = np.mean([m.efficiency_score for m in recent_metrics])
        
        opportunities = self.analyze_cost_optimization_opportunities()
        total_savings = sum(op.savings_per_hour for op in opportunities)
        
        return {
            'status': 'active',
            'metrics_analyzed': len(recent_metrics),
            'total_current_cost': total_current_cost,
            'average_efficiency': avg_efficiency,
            'optimization_opportunities': len(opportunities),
            'potential_savings': total_savings,
            'last_analysis': time.time(),
            'components': list(set(m.component for m in recent_metrics))
        }

# Example usage
if __name__ == "__main__":
    config = {
        'on_demand_cpu_cost': 0.05,
        'on_demand_memory_cost': 0.01,
        'on_demand_node_cost': 0.10,
        'spot_cpu_cost': 0.03,
        'spot_memory_cost': 0.006,
        'spot_node_cost': 0.06,
        'spot_discount': 0.4,
        'reserved_cpu_cost': 0.035,
        'reserved_memory_cost': 0.007,
        'reserved_node_cost': 0.07,
        'reserved_years': 1,
        'min_savings_percentage': 10,
        'max_spot_ratio': 0.5,
        'min_efficiency_score': 0.7,
        'optimization_interval': 300
    }
    
    optimizer = CostOptimizer(config)
    
    # Example cost metrics
    example_metrics = [
        CostMetrics(
            timestamp=time.time(),
            component='frontend',
            current_replicas=3,
            cpu_request=0.5,
            memory_request_mb=512,
            cost_per_hour=0.45,
            instance_type=InstanceType.ON_DEMAND,
            utilization_score=60.0,
            performance_score=85.0,
            efficiency_score=0.75
        )
    ]
    
    optimizer.update_cost_metrics(example_metrics)
    
    # Generate optimization report
    report = optimizer.generate_optimization_report()
    print(json.dumps(report, indent=2, default=str))
