"""
Advanced Stream Processing for FlavorSnap
Implements real-time data ingestion and analysis with Apache Kafka, Apache Flink, and custom stream processing
"""

import os
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import pickle
import hashlib

# Stream processing imports
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import redis
from prometheus_client import Counter, Histogram, Gauge
import aiokafka
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

logger = logging.getLogger(__name__)

class StreamType(Enum):
    """Types of stream processing"""
    KAFKA = "kafka"
    REDIS = "redis"
    WEBSOCKET = "websocket"
    HTTP = "http"
    FILE = "file"

class ProcessingMode(Enum):
    """Stream processing modes"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    MICRO_BATCH = "micro_batch"
    HYBRID = "hybrid"

class WindowType(Enum):
    """Window types for stream aggregation"""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    GLOBAL = "global"

@dataclass
class StreamEvent:
    """Stream event with metadata"""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    partition: Optional[int] = None
    offset: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'partition': self.partition,
            'offset': self.offset,
            'headers': self.headers
        }

@dataclass
class StreamMetrics:
    """Stream processing metrics"""
    events_processed: int = 0
    events_per_second: float = 0.0
    processing_latency_ms: float = 0.0
    error_rate: float = 0.0
    throughput_mb_per_sec: float = 0.0
    queue_depth: int = 0
    last_processed: Optional[datetime] = None
    
    def update_latency(self, start_time: datetime):
        """Update processing latency"""
        self.processing_latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

class StreamWindow:
    """Window for stream aggregation"""
    
    def __init__(self, window_type: WindowType, size_ms: int, slide_ms: int = None):
        self.window_type = window_type
        self.size_ms = size_ms
        self.slide_ms = slide_ms or size_ms
        self.events = deque()
        self.start_time = None
        self.end_time = None
        self.is_active = False
    
    def add_event(self, event: StreamEvent):
        """Add event to window"""
        if not self.is_active:
            self.start_time = event.timestamp
            self.end_time = self.start_time + timedelta(milliseconds=self.size_ms)
            self.is_active = True
        
        if event.timestamp <= self.end_time:
            self.events.append(event)
        else:
            # Window expired
            self.is_active = False
    
    def get_events(self) -> List[StreamEvent]:
        """Get events in window"""
        return list(self.events)
    
    def is_expired(self, current_time: datetime) -> bool:
        """Check if window is expired"""
        return current_time > self.end_time if self.end_time else False

class AdvancedStreamProcessor:
    """Advanced stream processor with multiple input sources and processing modes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processing_mode = ProcessingMode(config.get('processing_mode', 'real_time'))
        self.batch_size = config.get('batch_size', 100)
        self.batch_timeout_ms = config.get('batch_timeout_ms', 1000)
        
        # Stream connections
        self.kafka_producer = None
        self.kafka_consumer = None
        self.redis_client = None
        self.active_connections = {}
        
        # Processing state
        self.is_running = False
        self.event_queue = asyncio.Queue(maxsize=config.get('queue_size', 10000))
        self.processed_events = deque(maxlen=config.get('history_size', 10000))
        
        # Windows and aggregations
        self.windows = {}
        self.aggregations = defaultdict(dict)
        
        # Event handlers
        self.event_handlers = defaultdict(list)
        self.error_handlers = []
        
        # Metrics
        self.metrics = StreamMetrics()
        self.prometheus_metrics = self._init_prometheus_metrics()
        
        # Thread pool for processing
        self.executor = ThreadPoolExecutor(max_workers=config.get('max_workers', 4))
        
        self.logger = logging.getLogger('AdvancedStreamProcessor')
        
        # Initialize connections
        self._init_connections()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        return {
            'events_processed': Counter('stream_events_processed_total', 'Total events processed', ['source', 'event_type']),
            'processing_latency': Histogram('stream_processing_latency_seconds', 'Processing latency'),
            'queue_depth': Gauge('stream_queue_depth', 'Current queue depth'),
            'throughput': Gauge('stream_throughput_mb_per_sec', 'Throughput in MB/sec'),
            'error_rate': Gauge('stream_error_rate', 'Error rate')
        }
    
    def _init_connections(self):
        """Initialize stream connections"""
        try:
            # Initialize Kafka
            if 'kafka' in self.config:
                kafka_config = self.config['kafka']
                
                # Producer
                self.kafka_producer = AIOKafkaProducer(
                    bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                    batch_size=16384,
                    linger_ms=10,
                    buffer_memory=33554432
                )
                
                # Consumer
                self.kafka_consumer = AIOKafkaConsumer(
                    *kafka_config.get('topics', []),
                    bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    group_id=kafka_config.get('group_id', 'flavorsnap-stream'),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=3000
                )
            
            # Initialize Redis
            if 'redis' in self.config:
                redis_config = self.config['redis']
                self.redis_client = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                self.redis_client.ping()
            
            self.logger.info("Stream connections initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
    
    async def start_processing(self):
        """Start stream processing"""
        if self.is_running:
            self.logger.warning("Stream processor is already running")
            return
        
        self.is_running = True
        
        try:
            # Start Kafka connections
            if self.kafka_producer:
                await self.kafka_producer.start()
            
            if self.kafka_consumer:
                await self.kafka_consumer.start()
                # Start consumption task
                asyncio.create_task(self._consume_kafka_events())
            
            # Start processing tasks
            asyncio.create_task(self._process_events())
            asyncio.create_task(self._update_metrics())
            asyncio.create_task(self._cleanup_expired_windows())
            
            self.logger.info("Stream processing started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start stream processing: {e}")
            self.is_running = False
            raise
    
    async def stop_processing(self):
        """Stop stream processing"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            # Stop Kafka connections
            if self.kafka_producer:
                await self.kafka_producer.stop()
            
            if self.kafka_consumer:
                await self.kafka_consumer.stop()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            self.logger.info("Stream processing stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping stream processing: {e}")
    
    async def _consume_kafka_events(self):
        """Consume events from Kafka"""
        try:
            async for message in self.kafka_consumer:
                try:
                    event = StreamEvent(
                        event_id=str(message.key) if message.key else str(hash(message.value)),
                        event_type=message.headers.get('event_type', b'unknown').decode('utf-8') if message.headers else 'unknown',
                        data=message.value,
                        timestamp=datetime.utcnow(),
                        source='kafka',
                        partition=message.partition,
                        offset=message.offset,
                        headers=dict(message.headers) if message.headers else {}
                    )
                    
                    await self.event_queue.put(event)
                    self.prometheus_metrics['events_processed'].labels(source='kafka', event_type=event.event_type).inc()
                    
                except Exception as e:
                    self.logger.error(f"Error processing Kafka message: {e}")
                    self.metrics.error_rate += 1
        
        except Exception as e:
            self.logger.error(f"Kafka consumer error: {e}")
    
    async def _process_events(self):
        """Process events from queue"""
        batch = []
        last_batch_time = time.time()
        
        while self.is_running:
            try:
                # Collect batch
                timeout = self.batch_timeout_ms / 1000.0
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass
                
                current_time = time.time()
                should_process = (
                    len(batch) >= self.batch_size or
                    (batch and (current_time - last_batch_time) * 1000 >= self.batch_timeout_ms)
                )
                
                if should_process and batch:
                    await self._process_batch(batch)
                    batch = []
                    last_batch_time = current_time
                
            except Exception as e:
                self.logger.error(f"Error in event processing loop: {e}")
    
    async def _process_batch(self, events: List[StreamEvent]):
        """Process a batch of events"""
        start_time = datetime.utcnow()
        
        try:
            for event in events:
                # Update windows
                await self._update_windows(event)
                
                # Apply event handlers
                await self._apply_event_handlers(event)
                
                # Update aggregations
                await self._update_aggregations(event)
                
                # Store in processed events
                self.processed_events.append(event)
                
                # Update metrics
                self.metrics.events_processed += 1
                self.metrics.last_processed = datetime.utcnow()
            
            # Update latency
            self.metrics.update_latency(start_time)
            self.prometheus_metrics['processing_latency'].observe((datetime.utcnow() - start_time).total_seconds())
            
        except Exception as e:
            self.logger.error(f"Error processing batch: {e}")
            self.metrics.error_rate += 1
            await self._handle_error(e, events)
    
    async def _update_windows(self, event: StreamEvent):
        """Update time windows with event"""
        current_time = event.timestamp
        
        # Check existing windows
        expired_windows = []
        for window_id, window in list(self.windows.items()):
            if window.is_expired(current_time):
                expired_windows.append(window_id)
            else:
                window.add_event(event)
        
        # Remove expired windows
        for window_id in expired_windows:
            del self.windows[window_id]
        
        # Create new windows if needed
        if self.processing_mode == ProcessingMode.SLIDING:
            await self._create_sliding_windows(event)
    
    async def _create_sliding_windows(self, event: StreamEvent):
        """Create sliding windows for event"""
        # Implementation for sliding window creation
        pass
    
    async def _apply_event_handlers(self, event: StreamEvent):
        """Apply registered event handlers"""
        handlers = self.event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    await asyncio.get_event_loop().run_in_executor(self.executor, handler, event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")
    
    async def _update_aggregations(self, event: StreamEvent):
        """Update aggregations with event data"""
        event_type = event.event_type
        
        # Count aggregation
        if 'count' not in self.aggregations[event_type]:
            self.aggregations[event_type]['count'] = 0
        self.aggregations[event_type]['count'] += 1
        
        # Sum aggregation for numeric fields
        for key, value in event.data.items():
            if isinstance(value, (int, float)):
                agg_key = f"sum_{key}"
                if agg_key not in self.aggregations[event_type]:
                    self.aggregations[event_type][agg_key] = 0
                self.aggregations[event_type][agg_key] += value
        
        # Average aggregation
        for key, value in event.data.items():
            if isinstance(value, (int, float)):
                avg_key = f"avg_{key}"
                sum_key = f"sum_{key}"
                if sum_key in self.aggregations[event_type]:
                    count = self.aggregations[event_type]['count']
                    self.aggregations[event_type][avg_key] = self.aggregations[event_type][sum_key] / count
    
    async def _update_metrics(self):
        """Update performance metrics"""
        while self.is_running:
            try:
                # Calculate events per second
                current_time = datetime.utcnow()
                if self.metrics.last_processed:
                    time_diff = (current_time - self.metrics.last_processed).total_seconds()
                    if time_diff > 0:
                        self.metrics.events_per_second = 1.0 / time_diff
                
                # Update queue depth
                self.metrics.queue_depth = self.event_queue.qsize()
                self.prometheus_metrics['queue_depth'].set(self.metrics.queue_depth)
                
                # Calculate throughput (simplified)
                if self.metrics.events_processed > 0:
                    avg_event_size = 1024  # Assume 1KB per event
                    self.metrics.throughput_mb_per_sec = (self.metrics.events_per_second * avg_event_size) / (1024 * 1024)
                    self.prometheus_metrics['throughput'].set(self.metrics.throughput_mb_per_sec)
                
                # Update error rate
                self.prometheus_metrics['error_rate'].set(self.metrics.error_rate)
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                self.logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_expired_windows(self):
        """Clean up expired windows"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                expired_windows = []
                
                for window_id, window in self.windows.items():
                    if window.is_expired(current_time):
                        expired_windows.append(window_id)
                
                for window_id in expired_windows:
                    del self.windows[window_id]
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error cleaning up windows: {e}")
                await asyncio.sleep(30)
    
    async def _handle_error(self, error: Exception, events: List[StreamEvent]):
        """Handle processing errors"""
        for handler in self.error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error, events)
                else:
                    await asyncio.get_event_loop().run_in_executor(self.executor, handler, error, events)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        self.event_handlers[event_type].append(handler)
        self.logger.info(f"Registered handler for event type: {event_type}")
    
    def register_error_handler(self, handler: Callable):
        """Register error handler"""
        self.error_handlers.append(handler)
        self.logger.info("Registered error handler")
    
    async def publish_event(self, topic: str, event: StreamEvent):
        """Publish event to stream"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.send_and_wait(
                    topic=topic,
                    key=event.event_id,
                    value=event.to_dict(),
                    headers=[('event_type', event.event_type.encode('utf-8'))]
                )
            elif self.redis_client:
                # Use Redis streams as fallback
                await self._publish_to_redis(topic, event)
            else:
                self.logger.warning("No stream publisher available")
                
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            raise
    
    async def _publish_to_redis(self, stream: str, event: StreamEvent):
        """Publish to Redis stream"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.redis_client.xadd(
                    stream,
                    event.to_dict(),
                    maxlen=10000
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to publish to Redis: {e}")
            raise
    
    def create_window(self, window_id: str, window_type: WindowType, size_ms: int, slide_ms: int = None):
        """Create a time window"""
        window = StreamWindow(window_type, size_ms, slide_ms)
        self.windows[window_id] = window
        self.logger.info(f"Created window: {window_id}")
    
    def get_aggregation(self, event_type: str, aggregation_type: str) -> Any:
        """Get aggregation value"""
        return self.aggregations[event_type].get(aggregation_type)
    
    def get_window_events(self, window_id: str) -> List[StreamEvent]:
        """Get events in a window"""
        window = self.windows.get(window_id)
        return window.get_events() if window else []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            'events_processed': self.metrics.events_processed,
            'events_per_second': self.metrics.events_per_second,
            'processing_latency_ms': self.metrics.processing_latency_ms,
            'error_rate': self.metrics.error_rate,
            'throughput_mb_per_sec': self.metrics.throughput_mb_per_sec,
            'queue_depth': self.metrics.queue_depth,
            'active_windows': len(self.windows),
            'active_connections': len(self.active_connections),
            'is_running': self.is_running
        }

class RealTimeAnalytics:
    """Real-time analytics for stream data"""
    
    def __init__(self, stream_processor: AdvancedStreamProcessor):
        self.stream_processor = stream_processor
        self.analytics_cache = {}
        self.logger = logging.getLogger('RealTimeAnalytics')
    
    async def calculate_real_time_stats(self, event_type: str, time_window_ms: int = 60000) -> Dict[str, Any]:
        """Calculate real-time statistics for event type"""
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(milliseconds=time_window_ms)
            
            # Filter events in time window
            recent_events = [
                event for event in self.stream_processor.processed_events
                if event.event_type == event_type and event.timestamp >= window_start
            ]
            
            if not recent_events:
                return {'count': 0, 'time_window_ms': time_window_ms}
            
            # Calculate statistics
            stats = {
                'count': len(recent_events),
                'time_window_ms': time_window_ms,
                'events_per_second': len(recent_events) / (time_window_ms / 1000),
                'first_event': recent_events[0].timestamp.isoformat(),
                'last_event': recent_events[-1].timestamp.isoformat()
            }
            
            # Calculate numeric field statistics
            numeric_fields = defaultdict(list)
            for event in recent_events:
                for key, value in event.data.items():
                    if isinstance(value, (int, float)):
                        numeric_fields[key].append(value)
            
            for field, values in numeric_fields.items():
                stats[f'{field}_avg'] = np.mean(values)
                stats[f'{field}_min'] = np.min(values)
                stats[f'{field}_max'] = np.max(values)
                stats[f'{field}_sum'] = np.sum(values)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating real-time stats: {e}")
            return {}
    
    async def detect_anomalies(self, event_type: str, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies in stream data"""
        try:
            # Get recent events
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(minutes=10)  # 10-minute window
            
            recent_events = [
                event for event in self.stream_processor.processed_events
                if event.event_type == event_type and event.timestamp >= window_start
            ]
            
            if len(recent_events) < 10:
                return []  # Not enough data for anomaly detection
            
            # Extract numeric values
            numeric_values = []
            for event in recent_events:
                for value in event.data.values():
                    if isinstance(value, (int, float)):
                        numeric_values.append(value)
            
            if not numeric_values:
                return []
            
            # Calculate statistics
            mean_val = np.mean(numeric_values)
            std_val = np.std(numeric_values)
            
            # Detect anomalies
            anomalies = []
            for event in recent_events:
                for key, value in event.data.items():
                    if isinstance(value, (int, float)):
                        z_score = abs(value - mean_val) / std_val if std_val > 0 else 0
                        if z_score > threshold_std:
                            anomalies.append({
                                'event_id': event.event_id,
                                'timestamp': event.timestamp.isoformat(),
                                'field': key,
                                'value': value,
                                'z_score': z_score,
                                'threshold': threshold_std
                            })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return []
    
    async def generate_trend_analysis(self, event_type: str, time_windows: List[int] = None) -> Dict[str, Any]:
        """Generate trend analysis across multiple time windows"""
        if time_windows is None:
            time_windows = [60000, 300000, 900000, 3600000]  # 1min, 5min, 15min, 1hour
        
        trends = {}
        
        for window_ms in time_windows:
            stats = await self.calculate_real_time_stats(event_type, window_ms)
            trends[f'{window_ms//1000}s'] = stats
        
        # Calculate trend direction
        trend_analysis = {
            'trends': trends,
            'trend_direction': 'stable'  # Default
        }
        
        # Simple trend detection
        if len(time_windows) >= 2:
            recent_rate = trends[f'{time_windows[0]//1000}s']['events_per_second']
            older_rate = trends[f'{time_windows[-1]//1000}s']['events_per_second']
            
            if recent_rate > older_rate * 1.1:
                trend_analysis['trend_direction'] = 'increasing'
            elif recent_rate < older_rate * 0.9:
                trend_analysis['trend_direction'] = 'decreasing'
        
        return trend_analysis

# Factory functions
def create_stream_processor(config: Dict[str, Any]) -> AdvancedStreamProcessor:
    """Create stream processor with configuration"""
    return AdvancedStreamProcessor(config)

def create_real_time_analytics(stream_processor: AdvancedStreamProcessor) -> RealTimeAnalytics:
    """Create real-time analytics"""
    return RealTimeAnalytics(stream_processor)
