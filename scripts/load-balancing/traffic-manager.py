#!/usr/bin/env python3
"""
Advanced Traffic Manager for Load Balancer
Implements intelligent traffic distribution, rate limiting, and traffic shaping
"""

import asyncio
import time
import json
import logging
import hashlib
import statistics
import redis
import aioredis
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import ipaddress
import geoip2.database
import geoip2.errors
from datetime import datetime, timedelta
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficShapingAlgorithm(Enum):
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    ADAPTIVE = "adaptive"

class PriorityLevel(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TrafficRule:
    name: str
    priority: PriorityLevel
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    rate_limit: Optional[Dict[str, Any]] = None
    enabled: bool = True
    
@dataclass
class TrafficStats:
    total_requests: int = 0
    allowed_requests: int = 0
    blocked_requests: int = 0
    rate_limited_requests: int = 0
    avg_response_time: float = 0.0
    bytes_transferred: int = 0
    last_updated: float = 0.0

class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

class LeakyBucket:
    """Leaky bucket rate limiter"""
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.queue = deque()
        self.last_leak = time.time()
    
    def add(self, item: Any = None) -> bool:
        """Add item to bucket if not full"""
        self._leak()
        
        if len(self.queue) < self.capacity:
            self.queue.append(item)
            return True
        return False
    
    def _leak(self):
        """Leak items from bucket"""
        now = time.time()
        elapsed = now - self.last_leak
        leak_count = int(elapsed * self.leak_rate)
        
        for _ in range(min(leak_count, len(self.queue))):
            self.queue.popleft()
        
        self.last_leak = now

class SlidingWindowCounter:
    """Sliding window rate limiter"""
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
    
    def add_request(self) -> bool:
        """Add request to sliding window"""
        now = time.time()
        
        # Remove old requests outside window
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

class PrometheusMetrics:
    """Prometheus metrics for traffic management"""
    
    def __init__(self):
        self.requests_total = prom.Counter(
            'traffic_manager_requests_total',
            'Total requests processed',
            ['status', 'rule', 'client_ip']
        )
        
        self.request_duration = prom.Histogram(
            'traffic_manager_request_duration_seconds',
            'Request processing duration',
            ['rule', 'client_ip']
        )
        
        self.rate_limit_hits = prom.Counter(
            'traffic_manager_rate_limit_hits_total',
            'Rate limit violations',
            ['rule', 'client_type']
        )
        
        self.traffic_shaping_active = prom.Gauge(
            'traffic_manager_shaping_active',
            'Active traffic shaping rules',
            ['algorithm']
        )
        
        self.queue_length = prom.Gauge(
            'traffic_manager_queue_length',
            'Current queue length',
            ['rule']
        )
        
        self.bytes_transferred = prom.Counter(
            'traffic_manager_bytes_transferred_total',
            'Total bytes transferred',
            ['direction', 'rule']
        )

class AdvancedTrafficManager:
    """Advanced traffic manager with intelligent routing and shaping"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules: List[TrafficRule] = []
        self.rate_limiters: Dict[str, Any] = {}
        self.stats: Dict[str, TrafficStats] = defaultdict(TrafficStats)
        self.redis_client: Optional[aioredis.Redis] = None
        self.geoip_reader: Optional[geoip2.database.Reader] = None
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Traffic shaping configuration
        self.default_rate_limit = config.get('default_rate_limit', {
            'requests_per_second': 100,
            'burst': 200
        })
        
        self.priority_queues = {
            PriorityLevel.CRITICAL: asyncio.Queue(maxsize=1000),
            PriorityLevel.HIGH: asyncio.Queue(maxsize=500),
            PriorityLevel.NORMAL: asyncio.Queue(maxsize=1000),
            PriorityLevel.LOW: asyncio.Queue(maxsize=500)
        }
        
        # Initialize components
        self._initialize_components()
        
        # Start background tasks
        self.processor_task = None
        self.metrics_task = None
    
    def _initialize_components(self):
        """Initialize traffic manager components"""
        # Initialize Redis if configured
        redis_config = self.config.get('redis', {})
        if redis_config.get('enabled', False):
            asyncio.create_task(self._initialize_redis(redis_config))
        
        # Initialize GeoIP if configured
        geoip_config = self.config.get('geoip', {})
        if geoip_config.get('enabled', False):
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_config.get('database_path'))
                logger.info("GeoIP database loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load GeoIP database: {e}")
        
        # Load default rules
        self._load_default_rules()
    
    async def _initialize_redis(self, redis_config: Dict[str, Any]):
        """Initialize Redis client"""
        try:
            self.redis_client = await aioredis.from_url(
                redis_config.get('url', 'redis://localhost:6379'),
                encoding='utf-8'
            )
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
    
    def _load_default_rules(self):
        """Load default traffic rules"""
        default_rules = [
            TrafficRule(
                name="admin_access",
                priority=PriorityLevel.HIGH,
                conditions={"path_prefix": "/admin"},
                actions={"rate_limit_multiplier": 2.0},
                rate_limit={"requests_per_second": 50, "burst": 100}
            ),
            TrafficRule(
                name="api_access",
                priority=PriorityLevel.NORMAL,
                conditions={"path_prefix": "/api"},
                actions={"rate_limit_multiplier": 1.0},
                rate_limit={"requests_per_second": 100, "burst": 200}
            ),
            TrafficRule(
                name="ml_prediction",
                priority=PriorityLevel.HIGH,
                conditions={"path": "/predict"},
                actions={"rate_limit_multiplier": 0.5},
                rate_limit={"requests_per_second": 10, "burst": 20}
            ),
            TrafficRule(
                name="static_assets",
                priority=PriorityLevel.LOW,
                conditions={"path_regex": r"\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$"},
                actions={"rate_limit_multiplier": 5.0},
                rate_limit={"requests_per_second": 500, "burst": 1000}
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: TrafficRule):
        """Add traffic rule"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority.value, reverse=True)
        
        # Initialize rate limiter for rule
        if rule.rate_limit:
            self._initialize_rate_limiter(rule.name, rule.rate_limit)
        
        logger.info(f"Added traffic rule: {rule.name}")
    
    def remove_rule(self, name: str):
        """Remove traffic rule"""
        self.rules = [r for r in self.rules if r.name != name]
        if name in self.rate_limiters:
            del self.rate_limiters[name]
        logger.info(f"Removed traffic rule: {name}")
    
    def _initialize_rate_limiter(self, name: str, config: Dict[str, Any]):
        """Initialize rate limiter for a rule"""
        algorithm = config.get('algorithm', TrafficShapingAlgorithm.TOKEN_BUCKET)
        requests_per_second = config.get('requests_per_second', 100)
        burst = config.get('burst', requests_per_second * 2)
        
        if algorithm == TrafficShapingAlgorithm.TOKEN_BUCKET:
            self.rate_limiters[name] = TokenBucket(burst, requests_per_second)
        elif algorithm == TrafficShapingAlgorithm.LEAKY_BUCKET:
            self.rate_limiters[name] = LeakyBucket(burst, requests_per_second)
        elif algorithm == TrafficShapingAlgorithm.SLIDING_WINDOW:
            self.rate_limiters[name] = SlidingWindowCounter(60, requests_per_second * 60)
        
        logger.info(f"Initialized rate limiter for {name}: {algorithm.value}")
    
    async def process_request(self, request_info: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Process incoming request"""
        start_time = time.time()
        
        try:
            # Extract request information
            client_ip = request_info.get('client_ip', 'unknown')
            path = request_info.get('path', '/')
            method = request_info.get('method', 'GET')
            headers = request_info.get('headers', {})
            user_agent = headers.get('User-Agent', '')
            
            # Find matching rule
            rule = self._find_matching_rule(request_info)
            
            # Apply rate limiting
            rate_limit_result = await self._apply_rate_limit(rule, request_info)
            
            if not rate_limit_result['allowed']:
                self.stats[rule.name].rate_limited_requests += 1
                self.metrics.rate_limit_hits.labels(
                    rule=rule.name,
                    client_type=self._get_client_type(request_info)
                ).inc()
                
                return False, {
                    'status': 429,
                    'message': 'Rate limit exceeded',
                    'rule': rule.name,
                    'retry_after': rate_limit_result.get('retry_after', 60)
                }
            
            # Apply traffic shaping
            shaping_result = await self._apply_traffic_shaping(rule, request_info)
            
            if not shaping_result['allowed']:
                self.stats[rule.name].blocked_requests += 1
                return False, {
                    'status': 503,
                    'message': 'Service temporarily unavailable',
                    'rule': rule.name
                }
            
            # Update statistics
            self.stats[rule.name].total_requests += 1
            self.stats[rule.name].allowed_requests += 1
            self.stats[rule.name].last_updated = time.time()
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.requests_total.labels(
                status='allowed',
                rule=rule.name,
                client_ip=client_ip
            ).inc()
            self.metrics.request_duration.labels(
                rule=rule.name,
                client_ip=client_ip
            ).observe(processing_time)
            
            return True, {
                'rule': rule.name,
                'priority': rule.priority.name,
                'actions': rule.actions
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            self.metrics.requests_total.labels(
                status='error',
                rule='unknown',
                client_ip=request_info.get('client_ip', 'unknown')
            ).inc()
            return False, {
                'status': 500,
                'message': 'Internal server error'
            }
    
    def _find_matching_rule(self, request_info: Dict[str, Any]) -> TrafficRule:
        """Find matching traffic rule"""
        path = request_info.get('path', '/')
        method = request_info.get('method', 'GET')
        headers = request_info.get('headers', {})
        client_ip = request_info.get('client_ip', 'unknown')
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            conditions = rule.conditions
            
            # Check path conditions
            if 'path' in conditions and conditions['path'] != path:
                continue
            
            if 'path_prefix' in conditions and not path.startswith(conditions['path_prefix']):
                continue
            
            if 'path_regex' in conditions:
                import re
                if not re.match(conditions['path_regex'], path):
                    continue
            
            # Check method conditions
            if 'method' in conditions and conditions['method'] != method:
                continue
            
            # Check header conditions
            if 'headers' in conditions:
                header_match = True
                for header, value in conditions['headers'].items():
                    if headers.get(header) != value:
                        header_match = False
                        break
                if not header_match:
                    continue
            
            # Check IP conditions
            if 'ip_range' in conditions:
                try:
                    client_addr = ipaddress.ip_address(client_ip)
                    network = ipaddress.ip_network(conditions['ip_range'])
                    if client_addr not in network:
                        continue
                except ValueError:
                    continue
            
            # Check geographic conditions
            if 'country' in conditions and self.geoip_reader:
                try:
                    response = self.geoip_reader.country(client_ip)
                    if response.country.iso_code not in conditions['country']:
                        continue
                except (geoip2.errors.AddressNotFoundError, ValueError):
                    continue
            
            return rule
        
        # Return default rule if no match
        return TrafficRule(
            name="default",
            priority=PriorityLevel.NORMAL,
            conditions={},
            actions={},
            rate_limit=self.default_rate_limit
        )
    
    async def _apply_rate_limit(self, rule: TrafficRule, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rate limiting based on rule"""
        if not rule.rate_limit:
            return {'allowed': True}
        
        rate_limiter_key = f"{rule.name}:{request_info.get('client_ip', 'unknown')}"
        
        # Check distributed rate limiting if Redis is available
        if self.redis_client:
            return await self._distributed_rate_limit(rate_limiter_key, rule.rate_limit)
        
        # Check local rate limiting
        if rule.name in self.rate_limiters:
            rate_limiter = self.rate_limiters[rule.name]
            
            if isinstance(rate_limiter, TokenBucket):
                allowed = rate_limiter.consume()
            elif isinstance(rate_limiter, LeakyBucket):
                allowed = rate_limiter.add()
            elif isinstance(rate_limiter, SlidingWindowCounter):
                allowed = rate_limiter.add_request()
            else:
                allowed = True
            
            return {'allowed': allowed}
        
        return {'allowed': True}
    
    async def _distributed_rate_limit(self, key: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply distributed rate limiting using Redis"""
        try:
            requests_per_second = config.get('requests_per_second', 100)
            burst = config.get('burst', requests_per_second * 2)
            window = 60  # 1 minute window
            
            # Use Redis sliding window algorithm
            now = int(time.time())
            pipeline = self.redis_client.pipeline()
            
            # Remove old entries
            pipeline.zremrangebyscore(key, 0, now - window)
            
            # Count current requests
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiration
            pipeline.expire(key, window)
            
            results = await pipeline.execute()
            current_requests = results[1]
            
            allowed = current_requests < requests_per_second * window
            
            return {
                'allowed': allowed,
                'current_requests': current_requests,
                'limit': requests_per_second * window,
                'retry_after': max(1, window - (now % window))
            }
            
        except Exception as e:
            logger.error(f"Distributed rate limiting error: {e}")
            return {'allowed': True}  # Fail open
    
    async def _apply_traffic_shaping(self, rule: TrafficRule, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply traffic shaping based on rule priority"""
        try:
            # Add to priority queue
            queue = self.priority_queues[rule.priority]
            
            # Check if queue is full
            if queue.full():
                return {'allowed': False, 'reason': 'queue_full'}
            
            # Add to queue
            await queue.put(request_info)
            
            # Update metrics
            self.metrics.queue_length.labels(rule=rule.name).set(queue.qsize())
            
            return {'allowed': True}
            
        except asyncio.QueueFull:
            return {'allowed': False, 'reason': 'queue_full'}
        except Exception as e:
            logger.error(f"Traffic shaping error: {e}")
            return {'allowed': True}  # Fail open
    
    def _get_client_type(self, request_info: Dict[str, Any]) -> str:
        """Determine client type for metrics"""
        user_agent = request_info.get('headers', {}).get('User-Agent', '').lower()
        
        if 'bot' in user_agent or 'crawler' in user_agent:
            return 'bot'
        elif 'mobile' in user_agent or 'android' in user_agent or 'ios' in user_agent:
            return 'mobile'
        else:
            return 'desktop'
    
    async def start_processing(self):
        """Start background traffic processing"""
        if self.processor_task is None:
            self.processor_task = asyncio.create_task(self._process_traffic_queues())
        
        if self.metrics_task is None:
            self.metrics_task = asyncio.create_task(self._update_metrics())
        
        logger.info("Traffic manager started")
    
    async def stop_processing(self):
        """Stop background processing"""
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        if self.metrics_task:
            self.metrics_task.cancel()
            try:
                await self.metrics_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Traffic manager stopped")
    
    async def _process_traffic_queues(self):
        """Process traffic from priority queues"""
        while True:
            try:
                # Process queues in priority order
                for priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH, 
                               PriorityLevel.NORMAL, PriorityLevel.LOW]:
                    queue = self.priority_queues[priority]
                    
                    # Process multiple items from high priority queues
                    max_items = 10 if priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH] else 1
                    
                    for _ in range(max_items):
                        try:
                            request_info = queue.get_nowait()
                            # Here you would forward the request to the backend
                            # For now, we just simulate processing
                            await asyncio.sleep(0.01)  # Simulate processing time
                            
                        except asyncio.QueueEmpty:
                            break
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing traffic queues: {e}")
                await asyncio.sleep(1)
    
    async def _update_metrics(self):
        """Update metrics periodically"""
        while True:
            try:
                # Update queue length metrics
                for priority, queue in self.priority_queues.items():
                    rule_name = f"priority_{priority.name.lower()}"
                    self.metrics.queue_length.labels(rule=rule_name).set(queue.qsize())
                
                # Update traffic shaping metrics
                for name, limiter in self.rate_limiters.items():
                    algorithm = type(limiter).__name__
                    self.metrics.traffic_shaping_active.labels(algorithm=algorithm).set(1)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get traffic management statistics"""
        stats = {
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules if r.enabled]),
            'active_rate_limiters': len(self.rate_limiters),
            'queue_sizes': {
                priority.name: queue.qsize() 
                for priority, queue in self.priority_queues.items()
            },
            'rule_stats': {}
        }
        
        for rule_name, rule_stats in self.stats.items():
            stats['rule_stats'][rule_name] = asdict(rule_stats)
        
        return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Prometheus metrics"""
        return {
            'requests_total': self.metrics.requests_total._value._value,
            'rate_limit_hits': self.metrics.rate_limit_hits._value._value,
            'traffic_shaping_active': self.metrics.traffic_shaping_active._value._value,
            'queue_length': self.metrics.queue_length._value._value,
            'bytes_transferred': self.metrics.bytes_transferred._value._value
        }

# Example usage
if __name__ == "__main__":
    async def main():
        config = {
            'default_rate_limit': {
                'requests_per_second': 100,
                'burst': 200
            },
            'redis': {
                'enabled': True,
                'url': 'redis://localhost:6379'
            },
            'geoip': {
                'enabled': False,
                'database_path': '/path/to/GeoLite2-Country.mmdb'
            }
        }
        
        manager = AdvancedTrafficManager(config)
        await manager.start_processing()
        
        # Example request
        request_info = {
            'client_ip': '192.168.1.100',
            'path': '/api/predict',
            'method': 'POST',
            'headers': {
                'User-Agent': 'Mozilla/5.0...',
                'Content-Type': 'application/json'
            }
        }
        
        result = await manager.process_request(request_info)
        print(f"Request processed: {result}")
        
        # Get statistics
        stats = manager.get_statistics()
        print(f"Statistics: {json.dumps(stats, indent=2, default=str)}")
        
        await asyncio.sleep(60)
        await manager.stop_processing()
    
    asyncio.run(main())
