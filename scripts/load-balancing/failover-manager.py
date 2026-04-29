#!/usr/bin/env python3
"""
Advanced Failover Manager for Load Balancer
Implements intelligent failover mechanisms with circuit breakers and disaster recovery
"""

import asyncio
import time
import json
import logging
import random
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import aiohttp
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FailoverStrategy(Enum):
    ACTIVE_ACTIVE = "active_active"
    ACTIVE_PASSIVE = "active_passive"
    GEOGRAPHIC = "geographic"
    WEIGHTED = "weighted"
    ADAPTIVE = "adaptive"

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered

class DisasterLevel(Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DISASTER = "disaster"

@dataclass
class FailoverNode:
    id: str
    host: str
    port: int
    region: str
    weight: float = 1.0
    is_primary: bool = False
    is_active: bool = True
    health_score: float = 1.0
    last_health_check: float = 0
    consecutive_failures: int = 0
    response_times: deque = None
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_open_time: float = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = deque(maxlen=100)
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def is_healthy(self) -> bool:
        return (self.circuit_state == CircuitState.CLOSED and 
                self.health_score > 0.5 and 
                self.consecutive_failures < 3)

@dataclass
class FailoverConfig:
    strategy: FailoverStrategy = FailoverStrategy.ACTIVE_ACTIVE
    health_check_interval: int = 30
    health_check_timeout: int = 5
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    failover_timeout: int = 10
    max_failures: int = 3
    recovery_timeout: int = 30
    geographic_preference: List[str] = None
    disaster_recovery_enabled: bool = True
    auto_failback: bool = True
    failback_delay: int = 300

class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class PrometheusMetrics:
    """Prometheus metrics for failover management"""
    
    def __init__(self):
        self.failover_events = prom.Counter(
            'failover_events_total',
            'Total failover events',
            ['node', 'reason', 'strategy']
        )
        
        self.circuit_breaker_state = prom.Gauge(
            'failover_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=half_open, 2=open)',
            ['node']
        )
        
        self.node_health_score = prom.Gauge(
            'failover_node_health_score',
            'Health score of failover node',
            ['node', 'region']
        )
        
        self.active_nodes = prom.Gauge(
            'failover_active_nodes',
            'Number of active failover nodes',
            ['region']
        )
        
        self.disaster_level = prom.Gauge(
            'failover_disaster_level',
            'Current disaster level (0=normal, 1=degraded, 2=critical, 3=disaster)',
            []
        )
        
        self.recovery_time = prom.Histogram(
            'failover_recovery_time_seconds',
            'Time taken for node recovery',
            ['node']
        )

class AdvancedFailoverManager:
    """Advanced failover manager with intelligent routing and recovery"""
    
    def __init__(self, config: FailoverConfig):
        self.config = config
        self.nodes: List[FailoverNode] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.disaster_level = DisasterLevel.NORMAL
        self.current_primary: Optional[FailoverNode] = None
        self.failover_history: List[Dict[str, Any]] = []
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Background tasks
        self.health_check_task = None
        self.recovery_task = None
        
        # Failover state
        self.last_failover_time = 0
        self.failover_count = 0
        
        # Initialize components
        self._initialize_circuit_breakers()
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all nodes"""
        for node in self.nodes:
            self.circuit_breakers[node.id] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
    
    def add_node(self, node: FailoverNode):
        """Add failover node"""
        self.nodes.append(node)
        self.circuit_breakers[node.id] = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout
        )
        
        # Set as primary if specified
        if node.is_primary:
            self.current_primary = node
        
        logger.info(f"Added failover node: {node.id} ({node.host}:{node.port})")
    
    def remove_node(self, node_id: str):
        """Remove failover node"""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        if node_id in self.circuit_breakers:
            del self.circuit_breakers[node_id]
        
        if self.current_primary and self.current_primary.id == node_id:
            self.current_primary = None
        
        logger.info(f"Removed failover node: {node_id}")
    
    async def start(self):
        """Start failover manager"""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        if self.recovery_task is None:
            self.recovery_task = asyncio.create_task(self._recovery_loop())
        
        logger.info("Failover manager started")
    
    async def stop(self):
        """Stop failover manager"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.recovery_task:
            self.recovery_task.cancel()
            try:
                await self.recovery_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Failover manager stopped")
    
    async def _health_check_loop(self):
        """Background health checking loop"""
        while True:
            try:
                await self._perform_health_checks()
                await self._assess_disaster_level()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self):
        """Perform health checks on all nodes"""
        for node in self.nodes:
            try:
                is_healthy = await self._check_node_health(node)
                await self._update_node_health(node, is_healthy)
            except Exception as e:
                logger.error(f"Health check failed for {node.id}: {e}")
                await self._update_node_health(node, False)
    
    async def _check_node_health(self, node: FailoverNode) -> bool:
        """Check health of specific node"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{node.url}/health") as response:
                    if response.status == 200:
                        content = await response.text()
                        return "healthy" in content.lower()
                    return False
        except Exception as e:
            logger.debug(f"Health check failed for {node.id}: {e}")
            return False
    
    async def _update_node_health(self, node: FailoverNode, is_healthy: bool):
        """Update node health status"""
        start_time = time.time()
        
        if is_healthy:
            node.consecutive_failures = 0
            node.health_score = min(1.0, node.health_score + 0.1)
            
            # Update circuit breaker
            circuit_breaker = self.circuit_breakers[node.id]
            circuit_breaker.on_success()
            node.circuit_state = CircuitState.CLOSED
            
        else:
            node.consecutive_failures += 1
            node.health_score = max(0.0, node.health_score - 0.2)
            
            # Update circuit breaker
            circuit_breaker = self.circuit_breakers[node.id]
            circuit_breaker.on_failure()
            node.circuit_state = circuit_breaker.state
            
            if circuit_breaker.state == CircuitState.OPEN:
                node.circuit_open_time = time.time()
        
        node.last_health_check = time.time()
        
        # Update metrics
        self.metrics.node_health_score.labels(
            node=node.id, 
            region=node.region
        ).set(node.health_score)
        
        self.metrics.circuit_breaker_state.labels(
            node=node.id
        ).set({
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2
        }[node.circuit_state])
        
        # Trigger failover if needed
        if not node.is_healthy and node.is_primary:
            await self._trigger_failover(node, "health_check_failed")
        
        # Update response time
        response_time = time.time() - start_time
        node.response_times.append(response_time)
    
    async def _assess_disaster_level(self):
        """Assess current disaster level"""
        healthy_nodes = [n for n in self.nodes if n.is_healthy]
        total_nodes = len(self.nodes)
        
        if total_nodes == 0:
            self.disaster_level = DisasterLevel.DISASTER
        elif len(healthy_nodes) == 0:
            self.disaster_level = DisasterLevel.DISASTER
        elif len(healthy_nodes) < total_nodes * 0.25:
            self.disaster_level = DisasterLevel.CRITICAL
        elif len(healthy_nodes) < total_nodes * 0.5:
            self.disaster_level = DisasterLevel.DEGRADED
        else:
            self.disaster_level = DisasterLevel.NORMAL
        
        # Update metrics
        self.metrics.disaster_level.set({
            DisasterLevel.NORMAL: 0,
            DisasterLevel.DEGRADED: 1,
            DisasterLevel.CRITICAL: 2,
            DisasterLevel.DISASTER: 3
        }[self.disaster_level])
        
        # Update active nodes by region
        active_by_region = defaultdict(int)
        for node in healthy_nodes:
            active_by_region[node.region] += 1
        
        for region, count in active_by_region.items():
            self.metrics.active_nodes.labels(region=region).set(count)
    
    async def _trigger_failover(self, failed_node: FailoverNode, reason: str):
        """Trigger failover to another node"""
        logger.warning(f"Triggering failover from {failed_node.id}: {reason}")
        
        # Record failover event
        failover_event = {
            'timestamp': time.time(),
            'failed_node': failed_node.id,
            'reason': reason,
            'disaster_level': self.disaster_level.value,
            'strategy': self.config.strategy.value
        }
        self.failover_history.append(failover_event)
        
        # Update metrics
        self.metrics.failover_events.labels(
            node=failed_node.id,
            reason=reason,
            strategy=self.config.strategy.value
        ).inc()
        
        # Select new primary
        new_primary = await self._select_failover_target(failed_node)
        
        if new_primary:
            self.current_primary = new_primary
            self.last_failover_time = time.time()
            self.failover_count += 1
            
            logger.info(f"Failover completed: {failed_node.id} -> {new_primary.id}")
        else:
            logger.error("No suitable failover target available")
    
    async def _select_failover_target(self, failed_node: FailoverNode) -> Optional[FailoverNode]:
        """Select appropriate failover target based on strategy"""
        healthy_nodes = [n for n in self.nodes if n.is_healthy and n.id != failed_node.id]
        
        if not healthy_nodes:
            return None
        
        if self.config.strategy == FailoverStrategy.ACTIVE_PASSIVE:
            return self._select_active_passive_target(healthy_nodes)
        elif self.config.strategy == FailoverStrategy.GEOGRAPHIC:
            return self._select_geographic_target(healthy_nodes, failed_node)
        elif self.config.strategy == FailoverStrategy.WEIGHTED:
            return self._select_weighted_target(healthy_nodes)
        elif self.config.strategy == FailoverStrategy.ADAPTIVE:
            return self._select_adaptive_target(healthy_nodes)
        else:  # ACTIVE_ACTIVE
            return self._select_active_active_target(healthy_nodes)
    
    def _select_active_passive_target(self, healthy_nodes: List[FailoverNode]) -> Optional[FailoverNode]:
        """Select target for active-passive failover"""
        # Prefer passive nodes first
        passive_nodes = [n for n in healthy_nodes if not n.is_primary]
        if passive_nodes:
            return passive_nodes[0]
        
        # Fallback to any healthy node
        return healthy_nodes[0] if healthy_nodes else None
    
    def _select_geographic_target(self, healthy_nodes: List[FailoverNode], 
                                failed_node: FailoverNode) -> Optional[FailoverNode]:
        """Select target based on geographic preference"""
        preferred_regions = self.config.geographic_preference or [failed_node.region]
        
        # Try preferred regions first
        for region in preferred_regions:
            regional_nodes = [n for n in healthy_nodes if n.region == region]
            if regional_nodes:
                return min(regional_nodes, key=lambda n: n.avg_response_time)
        
        # Fallback to any healthy node
        return min(healthy_nodes, key=lambda n: n.avg_response_time)
    
    def _select_weighted_target(self, healthy_nodes: List[FailoverNode]) -> Optional[FailoverNode]:
        """Select target based on weights"""
        total_weight = sum(n.weight for n in healthy_nodes)
        if total_weight == 0:
            return healthy_nodes[0]
        
        # Weighted random selection
        rand = random.uniform(0, total_weight)
        current_weight = 0
        
        for node in healthy_nodes:
            current_weight += node.weight
            if rand <= current_weight:
                return node
        
        return healthy_nodes[-1]
    
    def _select_adaptive_target(self, healthy_nodes: List[FailoverNode]) -> Optional[FailoverNode]:
        """Select target based on adaptive scoring"""
        def score_node(node: FailoverNode) -> float:
            health_score = node.health_score * 0.4
            response_score = max(0, 1 - node.avg_response_time / 5.0) * 0.3
            weight_score = node.weight / max(n.weight for n in healthy_nodes) * 0.3
            return health_score + response_score + weight_score
        
        return max(healthy_nodes, key=score_node)
    
    def _select_active_active_target(self, healthy_nodes: List[FailoverNode]) -> Optional[FailoverNode]:
        """Select target for active-active configuration"""
        # Select node with best performance
        return min(healthy_nodes, key=lambda n: n.avg_response_time)
    
    async def _recovery_loop(self):
        """Background recovery loop"""
        while True:
            try:
                await self._attempt_recovery()
                await asyncio.sleep(self.config.recovery_timeout)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery error: {e}")
                await asyncio.sleep(30)
    
    async def _attempt_recovery(self):
        """Attempt to recover failed nodes"""
        for node in self.nodes:
            if not node.is_healthy:
                # Check if circuit breaker can be reset
                circuit_breaker = self.circuit_breakers[node.id]
                
                if (circuit_breaker.state == CircuitState.OPEN and
                    time.time() - node.circuit_open_time > self.config.circuit_breaker_timeout):
                    
                    # Try to recover node
                    logger.info(f"Attempting to recover node {node.id}")
                    
                    try:
                        is_healthy = await self._check_node_health(node)
                        if is_healthy:
                            recovery_time = time.time() - node.circuit_open_time
                            self.metrics.recovery_time.labels(node=node.id).observe(recovery_time)
                            logger.info(f"Node {node.id} recovered in {recovery_time:.2f}s")
                    
                    except Exception as e:
                        logger.warning(f"Recovery failed for {node.id}: {e}")
        
        # Attempt failback if enabled
        if self.config.auto_failback:
            await self._attempt_failback()
    
    async def _attempt_failback(self):
        """Attempt to failback to original primary"""
        if not self.current_primary or not self.config.auto_failback:
            return
        
        # Find original primary
        original_primary = next((n for n in self.nodes if n.is_primary), None)
        
        if (original_primary and 
            original_primary.id != self.current_primary.id and
            original_primary.is_healthy and
            time.time() - self.last_failover_time > self.config.failback_delay):
            
            logger.info(f"Failing back to original primary: {original_primary.id}")
            old_primary = self.current_primary
            self.current_primary = original_primary
            
            # Record failback event
            failback_event = {
                'timestamp': time.time(),
                'old_primary': old_primary.id,
                'new_primary': original_primary.id,
                'type': 'failback'
            }
            self.failover_history.append(failback_event)
    
    def get_active_nodes(self) -> List[FailoverNode]:
        """Get list of active nodes"""
        return [n for n in self.nodes if n.is_healthy]
    
    def get_primary_node(self) -> Optional[FailoverNode]:
        """Get current primary node"""
        return self.current_primary
    
    async def route_request(self, request_info: Dict[str, Any]) -> Optional[FailoverNode]:
        """Route request to appropriate node"""
        healthy_nodes = self.get_active_nodes()
        
        if not healthy_nodes:
            logger.error("No healthy nodes available for request routing")
            return None
        
        # Route based on strategy
        if self.config.strategy == FailoverStrategy.ACTIVE_ACTIVE:
            return self._select_active_active_target(healthy_nodes)
        elif self.config.strategy == FailoverStrategy.GEOGRAPHIC:
            client_region = request_info.get('client_region', 'unknown')
            regional_nodes = [n for n in healthy_nodes if n.region == client_region]
            if regional_nodes:
                return min(regional_nodes, key=lambda n: n.avg_response_time)
        
        # Default to primary for other strategies
        return self.current_primary or healthy_nodes[0]
    
    def get_status(self) -> Dict[str, Any]:
        """Get failover manager status"""
        healthy_nodes = self.get_active_nodes()
        
        return {
            'disaster_level': self.disaster_level.value,
            'total_nodes': len(self.nodes),
            'healthy_nodes': len(healthy_nodes),
            'current_primary': self.current_primary.id if self.current_primary else None,
            'strategy': self.config.strategy.value,
            'last_failover_time': self.last_failover_time,
            'failover_count': self.failover_count,
            'nodes': [
                {
                    'id': node.id,
                    'host': node.host,
                    'port': node.port,
                    'region': node.region,
                    'is_primary': node.is_primary,
                    'is_healthy': node.is_healthy,
                    'health_score': node.health_score,
                    'circuit_state': node.circuit_state.value,
                    'consecutive_failures': node.consecutive_failures,
                    'avg_response_time': node.avg_response_time
                }
                for node in self.nodes
            ],
            'recent_failovers': self.failover_history[-10:] if self.failover_history else []
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update failover configuration"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        logger.info("Failover configuration updated")

# Example usage
if __name__ == "__main__":
    async def main():
        config = FailoverConfig(
            strategy=FailoverStrategy.ACTIVE_ACTIVE,
            health_check_interval=30,
            circuit_breaker_threshold=5,
            geographic_preference=['us-east-1', 'us-west-2'],
            auto_failback=True
        )
        
        manager = AdvancedFailoverManager(config)
        
        # Add nodes
        manager.add_node(FailoverNode(
            id="primary",
            host="primary.example.com",
            port=5000,
            region="us-east-1",
            is_primary=True
        ))
        
        manager.add_node(FailoverNode(
            id="secondary",
            host="secondary.example.com",
            port=5000,
            region="us-west-2"
        ))
        
        await manager.start()
        
        # Route a request
        request_info = {'client_region': 'us-east-1'}
        target_node = await manager.route_request(request_info)
        
        if target_node:
            print(f"Request routed to: {target_node.id}")
        else:
            print("No available nodes")
        
        # Get status
        status = manager.get_status()
        print(f"Status: {json.dumps(status, indent=2, default=str)}")
        
        await asyncio.sleep(60)
        await manager.stop()
    
    asyncio.run(main())
