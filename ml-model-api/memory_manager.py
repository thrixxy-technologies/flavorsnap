"""
Advanced Memory Manager for FlavorSnap API
Implements comprehensive memory management with profiling, optimization, and leak detection
"""
import os
import sys
import gc
import time
import threading
import psutil
import tracemalloc
import resource
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import logging
from pathlib import Path


class MemoryStatus(Enum):
    """Memory status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MemoryUnit(Enum):
    """Memory units"""
    BYTES = "bytes"
    KB = "kb"
    MB = "mb"
    GB = "gb"


@dataclass
class MemorySnapshot:
    """Memory snapshot data structure"""
    timestamp: datetime
    process_memory: int  # bytes
    system_memory: int  # bytes
    available_memory: int  # bytes
    memory_usage_percent: float
    gc_stats: Dict[str, int]
    object_counts: Dict[str, int]
    heap_size: int
    tracked_allocations: int
    untracked_allocations: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MemoryLeak:
    """Memory leak detection result"""
    leak_id: str
    detected_at: datetime
    object_type: str
    allocation_count: int
    memory_size: int
    growth_rate: float  # bytes per second
    stack_trace: List[str]
    confidence: float  # 0-1
    false_positive: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class MemoryOptimization:
    """Memory optimization result"""
    optimization_id: str
    timestamp: datetime
    optimization_type: str
    memory_before: int
    memory_after: int
    memory_freed: int
    time_taken: float
    objects_collected: int
    success: bool
    details: Dict[str, Any]


class MemoryConfig:
    """Memory management configuration"""
    
    # Memory thresholds (in MB)
    WARNING_THRESHOLD = 70.0  # 70% of system memory
    CRITICAL_THRESHOLD = 85.0  # 85% of system memory
    EMERGENCY_THRESHOLD = 95.0  # 95% of system memory
    
    # GC settings
    GC_THRESHOLD = 700  # Number of allocations before GC
    GC_GENERATIONS = 3  # Number of generations
    
    # Leak detection settings
    LEAK_DETECTION_INTERVAL = 300  # seconds
    LEAK_GROWTH_THRESHOLD = 1024 * 1024  # 1MB growth
    LEAK_MIN_OBJECTS = 100  # Minimum objects to consider leak
    
    # Monitoring settings
    SNAPSHOT_INTERVAL = 60  # seconds
    MAX_SNAPSHOTS = 1440  # 24 hours of minute data
    PROFILING_ENABLED = True
    
    # Optimization settings
    AUTO_OPTIMIZATION = True
    OPTIMIZATION_INTERVAL = 600  # seconds
    MIN_MEMORY_TO_OPTIMIZE = 100 * 1024 * 1024  # 100MB


class MemoryProfiler:
    """Memory profiling utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tracking_enabled = False
        self.allocator_stats = defaultdict(int)
    
    def start_tracking(self):
        """Start memory tracking"""
        if not self.tracking_enabled:
            tracemalloc.start()
            self.tracking_enabled = True
            self.logger.info("Memory tracking started")
    
    def stop_tracking(self):
        """Stop memory tracking"""
        if self.tracking_enabled:
            tracemalloc.stop()
            self.tracking_enabled = False
            self.logger.info("Memory tracking stopped")
    
    def get_memory_info(self) -> Tuple[int, int, Dict[str, int]]:
        """Get current memory information"""
        if not self.tracking_enabled:
            return 0, 0, {}
        
        current, peak = tracemalloc.get_traced_memory()
        
        # Get allocation statistics
        stats = tracemalloc.get_traced_mallocs()
        allocator_stats = defaultdict(int)
        
        for alloc in stats:
            allocator_stats[alloc[2]] += 1  # filename
        
        return current, peak, dict(allocator_stats)
    
    def get_top_allocations(self, limit: int = 10) -> List[Tuple[str, int, int]]:
        """Get top memory allocations"""
        if not self.tracking_enabled:
            return []
        
        # Get statistics by traceback
        stats = tracemalloc.get_traced_mallocs()
        
        # Group by traceback
        traceback_stats = defaultdict(lambda: [0, 0])
        for size, count, filename, lineno in stats:
            key = f"{filename}:{lineno}"
            traceback_stats[key][0] += size
            traceback_stats[key][1] += count
        
        # Sort by size
        sorted_stats = sorted(
            [(key, size, count) for key, (size, count) in traceback_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_stats[:limit]


class GCOptimizer:
    """Garbage collection optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.original_threshold = None
        self.optimization_history: List[MemoryOptimization] = []
    
    def optimize_gc_settings(self) -> MemoryOptimization:
        """Optimize garbage collection settings"""
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        # Get current GC settings
        original_threshold = gc.get_threshold()
        original_debug = gc.get_debug()
        
        try:
            # Optimize threshold based on memory usage
            memory_usage = memory_before
            system_memory = psutil.virtual_memory().total
            
            if memory_usage > system_memory * 0.8:
                # High memory usage - more aggressive GC
                new_threshold = (200, 10, 5)
            elif memory_usage > system_memory * 0.6:
                # Medium memory usage - moderate GC
                new_threshold = (400, 20, 10)
            else:
                # Low memory usage - less aggressive GC
                new_threshold = (700, 10, 5)
            
            gc.set_threshold(*new_threshold)
            gc.set_debug(gc.DEBUG_SAVEALL)
            
            # Force garbage collection
            collected = gc.collect()
            
            memory_after = self._get_memory_usage()
            memory_freed = memory_before - memory_after
            time_taken = time.time() - start_time
            
            optimization = MemoryOptimization(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                optimization_type="gc_settings",
                memory_before=memory_before,
                memory_after=memory_after,
                memory_freed=memory_freed,
                time_taken=time_taken,
                objects_collected=collected,
                success=True,
                details={
                    'original_threshold': original_threshold,
                    'new_threshold': new_threshold,
                    'original_debug': original_debug
                }
            )
            
            self.optimization_history.append(optimization)
            self.logger.info(f"GC optimization completed: freed {memory_freed / 1024 / 1024:.2f} MB")
            
            return optimization
            
        except Exception as e:
            # Restore original settings on error
            gc.set_threshold(*original_threshold)
            gc.set_debug(original_debug)
            
            optimization = MemoryOptimization(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                optimization_type="gc_settings",
                memory_before=memory_before,
                memory_after=memory_before,
                memory_freed=0,
                time_taken=time.time() - start_time,
                objects_collected=0,
                success=False,
                details={'error': str(e)}
            )
            
            self.optimization_history.append(optimization)
            self.logger.error(f"GC optimization failed: {str(e)}")
            
            return optimization
    
    def optimize_object_caches(self) -> MemoryOptimization:
        """Optimize object caches and references"""
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        try:
            # Clear common caches
            cleared_caches = []
            
            # Clear module caches
            for module_name, module in list(sys.modules.items()):
                if hasattr(module, '__dict__'):
                    # Clear module-level caches
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, dict) and 'cache' in attr_name.lower():
                            attr.clear()
                            cleared_caches.append(f"{module_name}.{attr_name}")
            
            # Clear reference cycles
            collected = gc.collect()
            
            # Clear weakref collections
            weakref.collect()
            
            memory_after = self._get_memory_usage()
            memory_freed = memory_before - memory_after
            time_taken = time.time() - start_time
            
            optimization = MemoryOptimization(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                optimization_type="cache_optimization",
                memory_before=memory_before,
                memory_after=memory_after,
                memory_freed=memory_freed,
                time_taken=time_taken,
                objects_collected=collected,
                success=True,
                details={'cleared_caches': cleared_caches}
            )
            
            self.optimization_history.append(optimization)
            self.logger.info(f"Cache optimization completed: freed {memory_freed / 1024 / 1024:.2f} MB")
            
            return optimization
            
        except Exception as e:
            optimization = MemoryOptimization(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                optimization_type="cache_optimization",
                memory_before=memory_before,
                memory_after=memory_before,
                memory_freed=0,
                time_taken=time.time() - start_time,
                objects_collected=0,
                success=False,
                details={'error': str(e)}
            )
            
            self.optimization_history.append(optimization)
            self.logger.error(f"Cache optimization failed: {str(e)}")
            
            return optimization
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        process = psutil.Process()
        return process.memory_info().rss


class LeakDetector:
    """Memory leak detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.object_snapshots: deque = deque(maxlen=10)
        self.leak_history: List[MemoryLeak] = []
        self.detection_enabled = False
    
    def start_detection(self):
        """Start leak detection"""
        if not self.detection_enabled:
            self.detection_enabled = True
            self.logger.info("Memory leak detection started")
    
    def stop_detection(self):
        """Stop leak detection"""
        self.detection_enabled = False
        self.logger.info("Memory leak detection stopped")
    
    def take_snapshot(self) -> Dict[str, int]:
        """Take object count snapshot"""
        if not self.detection_enabled:
            return {}
        
        snapshot = {}
        
        # Count objects by type
        for obj_type in gc.get_objects():
            type_name = type(obj_type).__name__
            snapshot[type_name] = snapshot.get(type_name, 0) + 1
        
        self.object_snapshots.append(snapshot)
        return snapshot
    
    def detect_leaks(self) -> List[MemoryLeak]:
        """Detect memory leaks from snapshots"""
        if len(self.object_snapshots) < 2:
            return []
        
        leaks = []
        
        # Get oldest and newest snapshots
        oldest_snapshot = self.object_snapshots[0]
        newest_snapshot = self.object_snapshots[-1]
        
        # Calculate time difference
        time_diff = time.time() - (datetime.now() - timedelta(minutes=len(self.object_snapshots) - 1)).timestamp()
        
        # Analyze object growth
        for obj_type in newest_snapshot:
            old_count = oldest_snapshot.get(obj_type, 0)
            new_count = newest_snapshot[obj_type]
            
            growth = new_count - old_count
            
            if growth > MemoryConfig.LEAK_MIN_OBJECTS:
                # Estimate growth rate
                growth_rate = growth / time_diff if time_diff > 0 else 0
                
                # Estimate memory size (rough approximation)
                avg_size = self._estimate_object_size(obj_type)
                memory_size = growth * avg_size
                
                # Calculate confidence based on growth consistency
                confidence = min(1.0, growth / (MemoryConfig.LEAK_MIN_OBJECTS * 2))
                
                if memory_size > MemoryConfig.LEAK_GROWTH_THRESHOLD:
                    leak = MemoryLeak(
                        leak_id=str(uuid.uuid4()),
                        detected_at=datetime.now(),
                        object_type=obj_type,
                        allocation_count=growth,
                        memory_size=memory_size,
                        growth_rate=growth_rate,
                        stack_trace=[],  # Would need more sophisticated tracking
                        confidence=confidence
                    )
                    
                    leaks.append(leak)
                    self.leak_history.append(leak)
        
        return leaks
    
    def _estimate_object_size(self, obj_type: str) -> int:
        """Estimate average object size by type"""
        # Rough size estimates in bytes
        size_estimates = {
            'str': 50,
            'int': 28,
            'float': 24,
            'list': 56,
            'dict': 56,
            'tuple': 40,
            'set': 216,
            'bytes': 33,
            'bytearray': 56,
            'function': 136,
            'module': 1040,
            'type': 1056,
            'class': 1056
        }
        
        return size_estimates.get(obj_type, 64)  # Default to 64 bytes
    
    def get_leak_summary(self) -> Dict[str, Any]:
        """Get leak detection summary"""
        active_leaks = [leak for leak in self.leak_history if not leak.resolved]
        
        return {
            'total_leaks_detected': len(self.leak_history),
            'active_leaks': len(active_leaks),
            'resolved_leaks': len(self.leak_history) - len(active_leaks),
            'total_memory_leaked': sum(leak.memory_size for leak in active_leaks),
            'leaks_by_type': defaultdict(int),
            'high_confidence_leaks': len([leak for leak in active_leaks if leak.confidence > 0.7])
        }


class MemoryManager:
    """Main memory manager class"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.profiler = MemoryProfiler()
        self.gc_optimizer = GCOptimizer()
        self.leak_detector = LeakDetector()
        
        self.snapshots: deque = deque(maxlen=MemoryConfig.MAX_SNAPSHOTS)
        self.monitoring_active = False
        self.monitor_thread = None
        self.optimization_thread = None
        self.alert_callbacks: List[Callable[[str, MemoryStatus], None]] = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize memory manager with Flask app"""
        self.app = app
        
        # Start profiling if enabled
        if MemoryConfig.PROFILING_ENABLED:
            self.profiler.start_tracking()
        
        # Start monitoring
        self.start_monitoring()
        
        # Register cleanup
        import atexit
        atexit.register(self.cleanup)
        
        self.logger.info("Memory manager initialized")
    
    def start_monitoring(self):
        """Start memory monitoring in background"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        self.logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5)
        self.logger.info("Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Take memory snapshot
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                
                # Check memory status
                status = self._get_memory_status(snapshot)
                
                # Trigger alerts if needed
                if status != MemoryStatus.HEALTHY:
                    self._trigger_alert(status, snapshot)
                
                # Take leak detection snapshot
                if self.leak_detector.detection_enabled:
                    self.leak_detector.take_snapshot()
                
                # Sleep until next snapshot
                time.sleep(MemoryConfig.SNAPSHOT_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Memory monitoring error: {str(e)}")
                time.sleep(MemoryConfig.SNAPSHOT_INTERVAL)
    
    def _optimization_loop(self):
        """Optimization loop"""
        while self.monitoring_active:
            try:
                if MemoryConfig.AUTO_OPTIMIZATION:
                    # Check if optimization is needed
                    latest_snapshot = self.snapshots[-1] if self.snapshots else None
                    
                    if latest_snapshot and latest_snapshot.memory_usage_percent > MemoryConfig.WARNING_THRESHOLD:
                        self._optimize_memory()
                
                # Sleep until next optimization check
                time.sleep(MemoryConfig.OPTIMIZATION_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Memory optimization error: {str(e)}")
                time.sleep(MemoryConfig.OPTIMIZATION_INTERVAL)
    
    def _take_snapshot(self) -> MemorySnapshot:
        """Take memory snapshot"""
        # Get process memory info
        process = psutil.Process()
        process_memory = process.memory_info().rss
        
        # Get system memory info
        system_memory = psutil.virtual_memory().total
        available_memory = psutil.virtual_memory().available
        memory_usage_percent = psutil.virtual_memory().percent
        
        # Get GC stats
        gc_stats = {
            'generation_0': gc.get_count()[0],
            'generation_1': gc.get_count()[1],
            'generation_2': gc.get_count()[2],
            'collected': gc.collect(),
            'uncollectable': len(gc.garbage)
        }
        
        # Get object counts
        object_counts = defaultdict(int)
        for obj in gc.get_objects():
            object_counts[type(obj).__name__] += 1
        
        # Get heap info
        heap_size = 0
        tracked_allocations = 0
        untracked_allocations = 0
        
        if self.profiler.tracking_enabled:
            current, peak, _ = self.profiler.get_memory_info()
            heap_size = current
            tracked_allocations = len(gc.get_objects())
        
        return MemorySnapshot(
            timestamp=datetime.now(),
            process_memory=process_memory,
            system_memory=system_memory,
            available_memory=available_memory,
            memory_usage_percent=memory_usage_percent,
            gc_stats=gc_stats,
            object_counts=dict(object_counts),
            heap_size=heap_size,
            tracked_allocations=tracked_allocations,
            untracked_allocations=0  # Would need more complex tracking
        )
    
    def _get_memory_status(self, snapshot: MemorySnapshot) -> MemoryStatus:
        """Get memory status from snapshot"""
        if snapshot.memory_usage_percent >= MemoryConfig.EMERGENCY_THRESHOLD:
            return MemoryStatus.EMERGENCY
        elif snapshot.memory_usage_percent >= MemoryConfig.CRITICAL_THRESHOLD:
            return MemoryStatus.CRITICAL
        elif snapshot.memory_usage_percent >= MemoryConfig.WARNING_THRESHOLD:
            return MemoryStatus.WARNING
        else:
            return MemoryStatus.HEALTHY
    
    def _trigger_alert(self, status: MemoryStatus, snapshot: MemorySnapshot):
        """Trigger memory alert"""
        for callback in self.alert_callbacks:
            try:
                callback(f"Memory {status.value.upper()}: {snapshot.memory_usage_percent:.1f}% usage", status)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {str(e)}")
        
        # Log alert
        if status == MemoryStatus.EMERGENCY:
            self.logger.critical(f"Memory emergency: {snapshot.memory_usage_percent:.1f}%")
        elif status == MemoryStatus.CRITICAL:
            self.logger.error(f"Memory critical: {snapshot.memory_usage_percent:.1f}%")
        elif status == MemoryStatus.WARNING:
            self.logger.warning(f"Memory warning: {snapshot.memory_usage_percent:.1f}%")
    
    def _optimize_memory(self):
        """Optimize memory usage"""
        # Run GC optimization
        gc_optimization = self.gc_optimizer.optimize_gc_settings()
        
        # Run cache optimization
        cache_optimization = self.gc_optimizer.optimize_object_caches()
        
        total_freed = gc_optimization.memory_freed + cache_optimization.memory_freed
        
        if total_freed > 0:
            self.logger.info(f"Memory optimization completed: freed {total_freed / 1024 / 1024:.2f} MB")
    
    def add_alert_callback(self, callback: Callable[[str, MemoryStatus], None]):
        """Add memory alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get current memory information"""
        latest_snapshot = self.snapshots[-1] if self.snapshots else self._take_snapshot()
        
        return {
            'current': latest_snapshot.to_dict(),
            'status': self._get_memory_status(latest_snapshot).value,
            'profiling_enabled': self.profiler.tracking_enabled,
            'leak_detection_enabled': self.leak_detector.detection_enabled,
            'monitoring_active': self.monitoring_active
        }
    
    def get_memory_history(self, hours: int = 24) -> List[MemorySnapshot]:
        """Get memory history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        snapshots = [s for s in self.snapshots if s.timestamp >= cutoff_time]
        snapshots.sort(key=lambda x: x.timestamp, reverse=True)
        
        return snapshots
    
    def get_memory_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get memory usage trends"""
        snapshots = self.get_memory_history(hours)
        
        if len(snapshots) < 2:
            return {}
        
        # Calculate trends
        memory_usage = [s.memory_usage_percent for s in snapshots]
        process_memory = [s.process_memory for s in snapshots]
        
        return {
            'memory_usage_trend': {
                'current': memory_usage[0],
                'average': sum(memory_usage) / len(memory_usage),
                'min': min(memory_usage),
                'max': max(memory_usage),
                'growth_rate': (memory_usage[0] - memory_usage[-1]) / len(memory_usage) if len(memory_usage) > 1 else 0
            },
            'process_memory_trend': {
                'current': process_memory[0],
                'average': sum(process_memory) / len(process_memory),
                'min': min(process_memory),
                'max': max(process_memory),
                'growth_rate': (process_memory[0] - process_memory[-1]) / len(process_memory) if len(process_memory) > 1 else 0
            },
            'sample_count': len(snapshots),
            'time_range': {
                'start': snapshots[-1].timestamp.isoformat(),
                'end': snapshots[0].timestamp.isoformat()
            }
        }
    
    def detect_leaks(self) -> List[MemoryLeak]:
        """Detect memory leaks"""
        return self.leak_detector.detect_leaks()
    
    def get_leak_report(self) -> Dict[str, Any]:
        """Get leak detection report"""
        return self.leak_detector.get_leak_summary()
    
    def resolve_leak(self, leak_id: str) -> bool:
        """Mark leak as resolved"""
        for leak in self.leak_detector.leak_history:
            if leak.leak_id == leak_id:
                leak.resolved = True
                leak.resolved_at = datetime.now()
                self.logger.info(f"Memory leak {leak_id} marked as resolved")
                return True
        
        return False
    
    def get_optimization_history(self, limit: int = 50) -> List[MemoryOptimization]:
        """Get optimization history"""
        history = sorted(self.gc_optimizer.optimization_history, key=lambda x: x.timestamp, reverse=True)
        return history[:limit]
    
    def force_optimization(self, optimization_type: str = "all") -> MemoryOptimization:
        """Force memory optimization"""
        if optimization_type == "gc":
            return self.gc_optimizer.optimize_gc_settings()
        elif optimization_type == "cache":
            return self.gc_optimizer.optimize_object_caches()
        elif optimization_type == "all":
            # Run both optimizations
            gc_opt = self.gc_optimizer.optimize_gc_settings()
            cache_opt = self.gc_optimizer.optimize_object_caches()
            
            # Return combined result
            return MemoryOptimization(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                optimization_type="combined",
                memory_before=gc_opt.memory_before,
                memory_after=cache_opt.memory_after,
                memory_freed=gc_opt.memory_freed + cache_opt.memory_freed,
                time_taken=gc_opt.time_taken + cache_opt.time_taken,
                objects_collected=gc_opt.objects_collected + cache_opt.objects_collected,
                success=gc_opt.success and cache_opt.success,
                details={
                    'gc_optimization': gc_opt.to_dict(),
                    'cache_optimization': cache_opt.to_dict()
                }
            )
        else:
            raise ValueError(f"Unknown optimization type: {optimization_type}")
    
    def get_top_allocations(self, limit: int = 10) -> List[Tuple[str, int, int]]:
        """Get top memory allocations"""
        return self.profiler.get_top_allocations(limit)
    
    def export_memory_report(self, hours: int = 24, format: str = 'json') -> str:
        """Export memory report"""
        snapshots = self.get_memory_history(hours)
        trends = self.get_memory_trends(hours)
        leaks = self.detect_leaks()
        optimizations = self.get_optimization_history()
        
        if format == 'json':
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'current_memory': self.get_memory_info(),
                'trends': trends,
                'snapshots': [s.to_dict() for s in snapshots],
                'leaks': [asdict(leak) for leak in leaks],
                'optimizations': [asdict(opt) for opt in optimizations],
                'summary': {
                    'total_snapshots': len(snapshots),
                    'active_leaks': len(leaks),
                    'optimizations_run': len(optimizations),
                    'memory_trend': trends.get('memory_usage_trend', {})
                }
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['timestamp', 'memory_usage_percent', 'process_memory_mb', 
                     'available_memory_mb', 'gc_generation_0', 'gc_generation_1', 'gc_generation_2']
            writer.writerow(header)
            
            # Write snapshots
            for snapshot in snapshots:
                row = [
                    snapshot.timestamp.isoformat(),
                    snapshot.memory_usage_percent,
                    snapshot.process_memory / 1024 / 1024,
                    snapshot.available_memory / 1024 / 1024,
                    snapshot.gc_stats['generation_0'],
                    snapshot.gc_stats['generation_1'],
                    snapshot.gc_stats['generation_2']
                ]
                writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_monitoring()
        self.profiler.stop_tracking()
        self.leak_detector.stop_detection()
        self.logger.info("Memory manager cleanup completed")


# Initialize global memory manager
memory_manager = MemoryManager()
