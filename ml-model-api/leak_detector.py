"""
Advanced Memory Leak Detector for FlavorSnap API
Implements sophisticated memory leak detection with object tracking and analysis
"""
import gc
import sys
import time
import threading
import weakref
import inspect
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import psutil
import uuid


class LeakType(Enum):
    """Memory leak types"""
    REFERENCE_CYCLE = "reference_cycle"
    UNRELEASED_OBJECT = "unreleased_object"
    GROWING_CACHE = "growing_cache"
    CIRCULAR_IMPORT = "circular_import"
    LISTENER_LEAK = "listener_leak"
    THREAD_LEAK = "thread_leak"
    FILE_HANDLE_LEAK = "file_handle_leak"
    UNKNOWN = "unknown"


class LeakSeverity(Enum):
    """Leak severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ObjectInfo:
    """Object tracking information"""
    object_id: int
    type_name: str
    size_estimate: int
    creation_time: datetime
    last_seen: datetime
    ref_count: int
    backtrace: List[str]
    module: str
    is_container: bool
    contained_objects: Set[int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['creation_time'] = self.creation_time.isoformat()
        data['last_seen'] = self.last_seen.isoformat()
        data['contained_objects'] = list(self.contained_objects)
        return data


@dataclass
class LeakDetection:
    """Memory leak detection result"""
    leak_id: str
    detected_at: datetime
    leak_type: LeakType
    severity: LeakSeverity
    object_type: str
    object_count: int
    memory_size: int
    growth_rate: float
    confidence: float
    evidence: Dict[str, Any]
    backtrace_samples: List[List[str]]
    affected_modules: List[str]
    false_positive: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['detected_at'] = self.detected_at.isoformat()
        data['leak_type'] = self.leak_type.value
        data['severity'] = self.severity.value
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class LeakConfig:
    """Leak detector configuration"""
    
    # Detection thresholds
    MIN_OBJECTS_FOR_LEAK = 50
    MIN_MEMORY_FOR_LEAK = 1024 * 1024  # 1MB
    MIN_GROWTH_RATE = 1024  # 1KB per minute
    CONFIDENCE_THRESHOLD = 0.7
    
    # Tracking settings
    TRACKING_INTERVAL = 60  # seconds
    MAX_TRACKED_OBJECTS = 10000
    OBJECT_HISTORY_SIZE = 10
    
    # Analysis settings
    REFERENCE_CYCLE_DEPTH = 10
    BACKTRACE_SAMPLE_SIZE = 5
    MODULE_TRACKING_ENABLED = True
    
    # Leak type specific thresholds
    CACHE_GROWTH_THRESHOLD = 1000  # objects
    THREAD_LEAK_THRESHOLD = 10    # threads
    FILE_HANDLE_THRESHOLD = 100    # file handles


class ObjectTracker:
    """Track object creation and lifecycle"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tracked_objects: Dict[int, ObjectInfo] = {}
        self.object_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=LeakConfig.OBJECT_HISTORY_SIZE))
        self.type_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=LeakConfig.OBJECT_HISTORY_SIZE))
        self.module_objects: Dict[str, Set[int]] = defaultdict(set)
        self.tracking_enabled = False
        self.tracking_lock = threading.Lock()
    
    def start_tracking(self):
        """Start object tracking"""
        with self.tracking_lock:
            if not self.tracking_enabled:
                self.tracking_enabled = True
                self.logger.info("Object tracking started")
    
    def stop_tracking(self):
        """Stop object tracking"""
        with self.tracking_lock:
            self.tracking_enabled = False
            self.tracked_objects.clear()
            self.object_history.clear()
            self.type_counts.clear()
            self.module_objects.clear()
            self.logger.info("Object tracking stopped")
    
    def track_object(self, obj_id: int, obj_type: type, size_estimate: int = 0):
        """Track a new object"""
        if not self.tracking_enabled:
            return
        
        with self.tracking_lock:
            if len(self.tracked_objects) >= LeakConfig.MAX_TRACKED_OBJECTS:
                # Remove oldest objects
                oldest_ids = sorted(
                    self.tracked_objects.keys(),
                    key=lambda x: self.tracked_objects[x].creation_time
                )[:100]
                for old_id in oldest_ids:
                    del self.tracked_objects[old_id]
            
            # Get object info
            type_name = obj_type.__name__
            module = obj_type.__module__
            
            # Get backtrace (simplified)
            backtrace = self._get_backtrace()
            
            # Check if container
            is_container = hasattr(obj_type, '__iter__') and obj_type not in (str, bytes, bytearray)
            contained_objects = set()
            
            if is_container:
                try:
                    # Track contained objects (simplified)
                    for contained in obj_type():
                        if hasattr(contained, '__id__'):
                            contained_objects.add(id(contained))
                except:
                    pass
            
            object_info = ObjectInfo(
                object_id=obj_id,
                type_name=type_name,
                size_estimate=size_estimate,
                creation_time=datetime.now(),
                last_seen=datetime.now(),
                ref_count=sys.getrefcount(obj_id) if hasattr(obj_id, '__refcount__') else 0,
                backtrace=backtrace,
                module=module,
                is_container=is_container,
                contained_objects=contained_objects
            )
            
            self.tracked_objects[obj_id] = object_info
            self.object_history[obj_id].append(datetime.now())
            self.type_counts[type_name].append(datetime.now())
            
            if LeakConfig.MODULE_TRACKING_ENABLED:
                self.module_objects[module].add(obj_id)
    
    def update_object(self, obj_id: int):
        """Update object last seen time"""
        if not self.tracking_enabled or obj_id not in self.tracked_objects:
            return
        
        with self.tracking_lock:
            if obj_id in self.tracked_objects:
                self.tracked_objects[obj_id].last_seen = datetime.now()
                self.object_history[obj_id].append(datetime.now())
    
    def remove_object(self, obj_id: int):
        """Remove tracked object"""
        if not self.tracking_enabled:
            return
        
        with self.tracking_lock:
            if obj_id in self.tracked_objects:
                object_info = self.tracked_objects[obj_id]
                del self.tracked_objects[obj_id]
                
                # Clean up history
                if obj_id in self.object_history:
                    del self.object_history[obj_id]
                
                # Clean up module tracking
                if LeakConfig.MODULE_TRACKING_ENABLED:
                    self.module_objects[object_info.module].discard(obj_id)
    
    def get_object_snapshot(self) -> Dict[str, Any]:
        """Get current object tracking snapshot"""
        with self.tracking_lock:
            if not self.tracking_enabled:
                return {}
            
            # Count objects by type
            type_counts = defaultdict(int)
            type_memory = defaultdict(int)
            
            for obj_info in self.tracked_objects.values():
                type_counts[obj_info.type_name] += 1
                type_memory[obj_info.type_name] += obj_info.size_estimate
            
            # Count by module
            module_counts = {}
            if LeakConfig.MODULE_TRACKING_ENABLED:
                for module, obj_ids in self.module_objects.items():
                    module_counts[module] = len(obj_ids)
            
            return {
                'total_objects': len(self.tracked_objects),
                'type_counts': dict(type_counts),
                'type_memory': dict(type_memory),
                'module_counts': module_counts,
                'tracking_enabled': self.tracking_enabled,
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_backtrace(self) -> List[str]:
        """Get simplified backtrace"""
        try:
            stack = inspect.stack()
            # Skip internal frames
            relevant_frames = stack[3:8]  # Get 5 frames from caller
            
            backtrace = []
            for frame in relevant_frames:
                filename = frame.filename
                lineno = frame.lineno
                function = frame.function
                backtrace.append(f"{filename}:{lineno} in {function}")
            
            return backtrace
        except:
            return []
    
    def find_growing_objects(self, minutes: int = 10) -> List[Tuple[str, int, float]]:
        """Find object types with growing counts"""
        growing_objects = []
        
        for type_name, timestamps in self.type_counts.items():
            if len(timestamps) < 2:
                continue
            
            # Calculate growth rate
            time_span = (timestamps[-1] - timestamps[0]).total_seconds()
            if time_span == 0:
                continue
            
            growth_rate = len(timestamps) / (time_span / 60)  # objects per minute
            
            if growth_rate > LeakConfig.MIN_GROWTH_RATE:
                current_count = len(timestamps)
                growing_objects.append((type_name, current_count, growth_rate))
        
        # Sort by growth rate
        growing_objects.sort(key=lambda x: x[2], reverse=True)
        
        return growing_objects


class ReferenceCycleDetector:
    """Detect reference cycles in objects"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_reference_cycles(self) -> List[List[int]]:
        """Find reference cycles in tracked objects"""
        cycles = []
        
        try:
            # Get all objects
            all_objects = gc.get_objects()
            
            # Build reference graph (simplified)
            graph = {}
            for obj in all_objects:
                obj_id = id(obj)
                refs = []
                
                try:
                    # Get object references
                    if hasattr(obj, '__dict__'):
                        refs.extend([id(v) for v in obj.__dict__.values() if hasattr(v, '__id__')])
                    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
                        refs.extend([id(item) for item in obj if hasattr(item, '__id__')])
                except:
                    pass
                
                graph[obj_id] = refs
            
            # Find cycles using DFS
            visited = set()
            for obj_id in graph:
                if obj_id not in visited:
                    cycle = self._find_cycle_dfs(graph, obj_id, visited, set(), [])
                    if cycle and len(cycle) > 2:  # At least 3 objects
                        cycles.append(cycle)
        
        except Exception as e:
            self.logger.error(f"Reference cycle detection failed: {str(e)}")
        
        return cycles
    
    def _find_cycle_dfs(self, graph: Dict[int, List[int]], node: int, visited: Set[int], 
                      path: Set[int], current_path: List[int]) -> Optional[List[int]]:
        """Find cycle using DFS"""
        if node in path:
            # Found cycle
            cycle_start = current_path.index(node)
            return current_path[cycle_start:]
        
        if node in visited:
            return None
        
        visited.add(node)
        path.add(node)
        current_path.append(node)
        
        for neighbor in graph.get(node, []):
            cycle = self._find_cycle_dfs(graph, neighbor, visited, path, current_path)
            if cycle:
                return cycle
        
        path.remove(node)
        current_path.pop()
        
        return None


class SpecificLeakDetectors:
    """Specialized detectors for specific leak types"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_cache_leaks(self) -> List[Dict[str, Any]]:
        """Detect growing cache leaks"""
        cache_leaks = []
        
        try:
            # Check common cache patterns
            for obj in gc.get_objects():
                if isinstance(obj, dict) and 'cache' in str(type(obj)).lower():
                    # Check if dict is growing
                    if len(obj) > LeakConfig.CACHE_GROWTH_THRESHOLD:
                        cache_leaks.append({
                            'type': 'cache_leak',
                            'object_type': type(obj).__name__,
                            'size': len(obj),
                            'module': type(obj).__module__,
                            'sample_keys': list(obj.keys())[:5]
                        })
        except Exception as e:
            self.logger.error(f"Cache leak detection failed: {str(e)}")
        
        return cache_leaks
    
    def detect_thread_leaks(self) -> List[Dict[str, Any]]:
        """Detect thread leaks"""
        thread_leaks = []
        
        try:
            # Count active threads
            active_threads = threading.enumerate()
            
            if len(active_threads) > LeakConfig.THREAD_LEAK_THRESHOLD:
                thread_leaks.append({
                    'type': 'thread_leak',
                    'thread_count': len(active_threads),
                    'threads': [
                        {
                            'name': thread.name,
                            'daemon': thread.daemon,
                            'alive': thread.is_alive()
                        }
                        for thread in active_threads[:10]  # Sample first 10
                    ]
                })
        except Exception as e:
            self.logger.error(f"Thread leak detection failed: {str(e)}")
        
        return thread_leaks
    
    def detect_file_handle_leaks(self) -> List[Dict[str, Any]]:
        """Detect file handle leaks"""
        file_leaks = []
        
        try:
            # Count open file handles
            process = psutil.Process()
            open_files = process.open_files()
            
            if len(open_files) > LeakConfig.FILE_HANDLE_THRESHOLD:
                file_leaks.append({
                    'type': 'file_handle_leak',
                    'file_count': len(open_files),
                    'files': [
                        {
                            'path': f.path,
                            'fd': f.fd
                        }
                        for f in open_files[:10]  # Sample first 10
                    ]
                })
        except Exception as e:
            self.logger.error(f"File handle leak detection failed: {str(e)}")
        
        return file_leaks
    
    def detect_listener_leaks(self) -> List[Dict[str, Any]]:
        """Detect event listener leaks"""
        listener_leaks = []
        
        try:
            # Look for common listener patterns
            for obj in gc.get_objects():
                obj_type = type(obj)
                
                # Check for callback lists
                if (hasattr(obj, '__iter__') and 
                    ('callback' in str(obj_type).lower() or 
                     'listener' in str(obj_type).lower() or
                     'handler' in str(obj_type).lower())):
                    
                    if hasattr(obj, '__len__') and len(obj) > 100:
                        listener_leaks.append({
                            'type': 'listener_leak',
                            'object_type': obj_type.__name__,
                            'size': len(obj),
                            'module': obj_type.__module__
                        })
        except Exception as e:
            self.logger.error(f"Listener leak detection failed: {str(e)}")
        
        return listener_leaks


class MemoryLeakDetector:
    """Main memory leak detector"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.object_tracker = ObjectTracker()
        self.cycle_detector = ReferenceCycleDetector()
        self.specific_detectors = SpecificLeakDetectors()
        
        self.detection_history: List[LeakDetection] = []
        self.detection_active = False
        self.detection_thread = None
        self.alert_callbacks: List[Callable[[LeakDetection], None]] = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize leak detector with Flask app"""
        self.app = app
        self.start_detection()
        self.logger.info("Memory leak detector initialized")
    
    def start_detection(self):
        """Start leak detection"""
        if self.detection_active:
            return
        
        self.detection_active = True
        self.object_tracker.start_tracking()
        
        self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.detection_thread.start()
        
        self.logger.info("Memory leak detection started")
    
    def stop_detection(self):
        """Stop leak detection"""
        self.detection_active = False
        if self.detection_thread:
            self.detection_thread.join(timeout=5)
        
        self.object_tracker.stop_tracking()
        self.logger.info("Memory leak detection stopped")
    
    def _detection_loop(self):
        """Main detection loop"""
        while self.detection_active:
            try:
                # Run leak detection
                leaks = self.detect_leaks()
                
                # Process new leaks
                for leak in leaks:
                    if not any(l.leak_id == leak.leak_id for l in self.detection_history):
                        self.detection_history.append(leak)
                        
                        # Trigger alerts
                        for callback in self.alert_callbacks:
                            try:
                                callback(leak)
                            except Exception as e:
                                self.logger.error(f"Leak alert callback failed: {str(e)}")
                
                # Sleep until next detection
                time.sleep(LeakConfig.TRACKING_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Leak detection error: {str(e)}")
                time.sleep(LeakConfig.TRACKING_INTERVAL)
    
    def detect_leaks(self) -> List[LeakDetection]:
        """Run comprehensive leak detection"""
        leaks = []
        
        # Detect growing objects
        growing_objects = self.object_tracker.find_growing_objects()
        
        for obj_type, count, growth_rate in growing_objects:
            if count >= LeakConfig.MIN_OBJECTS_FOR_LEAK:
                # Estimate memory size
                memory_size = self._estimate_type_memory(obj_type, count)
                
                if memory_size >= LeakConfig.MIN_MEMORY_FOR_LEAK:
                    leak = LeakDetection(
                        leak_id=str(uuid.uuid4()),
                        detected_at=datetime.now(),
                        leak_type=LeakType.UNRELEASED_OBJECT,
                        severity=self._calculate_severity(memory_size, growth_rate),
                        object_type=obj_type,
                        object_count=count,
                        memory_size=memory_size,
                        growth_rate=growth_rate,
                        confidence=min(1.0, growth_rate / LeakConfig.MIN_GROWTH_RATE),
                        evidence={
                            'growth_samples': self._get_growth_samples(obj_type),
                            'type_history': list(self.object_tracker.type_counts[obj_type])
                        },
                        backtrace_samples=self._get_backtrace_samples(obj_type),
                        affected_modules=self._get_affected_modules(obj_type)
                    )
                    leaks.append(leak)
        
        # Detect reference cycles
        cycles = self.cycle_detector.find_reference_cycles()
        
        if cycles:
            for cycle in cycles[:5]:  # Limit to top 5 cycles
                memory_size = self._estimate_cycle_memory(cycle)
                
                leak = LeakDetection(
                    leak_id=str(uuid.uuid4()),
                    detected_at=datetime.now(),
                    leak_type=LeakType.REFERENCE_CYCLE,
                    severity=self._calculate_severity(memory_size, 0),
                    object_type="reference_cycle",
                    object_count=len(cycle),
                    memory_size=memory_size,
                    growth_rate=0,
                    confidence=0.8,
                    evidence={
                        'cycle_objects': cycle,
                        'cycle_length': len(cycle)
                    },
                    backtrace_samples=[],
                    affected_modules=[]
                )
                leaks.append(leak)
        
        # Detect specific leak types
        specific_leaks = []
        specific_leaks.extend(self.specific_detectors.detect_cache_leaks())
        specific_leaks.extend(self.specific_detectors.detect_thread_leaks())
        specific_leaks.extend(self.specific_detectors.detect_file_handle_leaks())
        specific_leaks.extend(self.specific_detectors.detect_listener_leaks())
        
        for leak_info in specific_leaks:
            leak_type = LeakType(leak_info['type'])
            
            leak = LeakDetection(
                leak_id=str(uuid.uuid4()),
                detected_at=datetime.now(),
                leak_type=leak_type,
                severity=LeakSeverity.MEDIUM,
                object_type=leak_info.get('object_type', leak_type.value),
                object_count=leak_info.get('size', 0),
                memory_size=self._estimate_specific_leak_memory(leak_info),
                growth_rate=0,
                confidence=0.7,
                evidence=leak_info,
                backtrace_samples=[],
                affected_modules=[leak_info.get('module', 'unknown')]
            )
            leaks.append(leak)
        
        return leaks
    
    def _estimate_type_memory(self, obj_type: str, count: int) -> int:
        """Estimate memory usage for object type"""
        # Rough size estimates
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
            'module': 1040
        }
        
        base_size = size_estimates.get(obj_type, 64)
        return base_size * count
    
    def _estimate_cycle_memory(self, cycle: List[int]) -> int:
        """Estimate memory usage of reference cycle"""
        total_size = 0
        
        for obj_id in cycle:
            # Get object from gc (simplified)
            for obj in gc.get_objects():
                if id(obj) == obj_id:
                    total_size += sys.getsizeof(obj)
                    break
        
        return total_size
    
    def _estimate_specific_leak_memory(self, leak_info: Dict[str, Any]) -> int:
        """Estimate memory usage for specific leak types"""
        leak_type = leak_info['type']
        
        if leak_type == 'cache_leak':
            return leak_info['size'] * 100  # Assume 100 bytes per cache entry
        elif leak_type == 'thread_leak':
            return leak_info['thread_count'] * 8192  # Assume 8KB per thread
        elif leak_type == 'file_handle_leak':
            return leak_info['file_count'] * 1024  # Assume 1KB per file handle
        elif leak_type == 'listener_leak':
            return leak_info['size'] * 64  # Assume 64 bytes per listener
        else:
            return 0
    
    def _calculate_severity(self, memory_size: int, growth_rate: float) -> LeakSeverity:
        """Calculate leak severity"""
        if memory_size > 100 * 1024 * 1024:  # > 100MB
            return LeakSeverity.CRITICAL
        elif memory_size > 10 * 1024 * 1024:  # > 10MB
            return LeakSeverity.HIGH
        elif memory_size > 1024 * 1024:  # > 1MB
            return LeakSeverity.MEDIUM
        else:
            return LeakSeverity.LOW
    
    def _get_growth_samples(self, obj_type: str) -> List[Dict[str, Any]]:
        """Get growth samples for object type"""
        timestamps = list(self.object_tracker.type_counts[obj_type])
        
        samples = []
        for i, ts in enumerate(timestamps):
            samples.append({
                'index': i,
                'timestamp': ts.isoformat(),
                'count': i + 1
            })
        
        return samples[-10:]  # Last 10 samples
    
    def _get_backtrace_samples(self, obj_type: str) -> List[List[str]]:
        """Get backtrace samples for object type"""
        backtraces = []
        
        for obj_info in self.object_tracker.tracked_objects.values():
            if obj_info.type_name == obj_type and obj_info.backtrace:
                backtraces.append(obj_info.backtrace)
                
                if len(backtraces) >= LeakConfig.BACKTRACE_SAMPLE_SIZE:
                    break
        
        return backtraces
    
    def _get_affected_modules(self, obj_type: str) -> List[str]:
        """Get modules affected by object type"""
        modules = set()
        
        for obj_info in self.object_tracker.tracked_objects.values():
            if obj_info.type_name == obj_type:
                modules.add(obj_info.module)
        
        return list(modules)
    
    def add_alert_callback(self, callback: Callable[[LeakDetection], None]):
        """Add leak alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_leak_summary(self) -> Dict[str, Any]:
        """Get leak detection summary"""
        active_leaks = [leak for leak in self.detection_history if not leak.resolved]
        
        return {
            'total_leaks_detected': len(self.detection_history),
            'active_leaks': len(active_leaks),
            'resolved_leaks': len(self.detection_history) - len(active_leaks),
            'leaks_by_type': defaultdict(int),
            'leaks_by_severity': defaultdict(int),
            'total_memory_leaked': sum(leak.memory_size for leak in active_leaks),
            'high_confidence_leaks': len([leak for leak in active_leaks if leak.confidence > LeakConfig.CONFIDENCE_THRESHOLD]),
            'tracking_enabled': self.object_tracker.tracking_enabled,
            'detection_active': self.detection_active
        }
    
    def get_leak_details(self, leak_id: str) -> Optional[LeakDetection]:
        """Get detailed leak information"""
        for leak in self.detection_history:
            if leak.leak_id == leak_id:
                return leak
        return None
    
    def resolve_leak(self, leak_id: str, resolution_notes: str = None) -> bool:
        """Mark leak as resolved"""
        for leak in self.detection_history:
            if leak.leak_id == leak_id:
                leak.resolved = True
                leak.resolved_at = datetime.now()
                
                self.logger.info(f"Memory leak {leak_id} resolved")
                return True
        
        return False
    
    def mark_false_positive(self, leak_id: str) -> bool:
        """Mark leak as false positive"""
        for leak in self.detection_history:
            if leak.leak_id == leak_id:
                leak.false_positive = True
                self.logger.info(f"Memory leak {leak_id} marked as false positive")
                return True
        
        return False
    
    def get_object_tracking_info(self) -> Dict[str, Any]:
        """Get object tracking information"""
        return self.object_tracker.get_object_snapshot()
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return results"""
        start_time = time.time()
        
        # Get counts before collection
        counts_before = gc.get_count()
        objects_before = len(gc.get_objects())
        
        # Force collection
        collected = gc.collect()
        
        # Get counts after collection
        counts_after = gc.get_count()
        objects_after = len(gc.get_objects())
        
        collection_time = time.time() - start_time
        
        return {
            'objects_collected': collected,
            'collection_time': collection_time,
            'counts_before': list(counts_before),
            'counts_after': list(counts_after),
            'objects_before': objects_before,
            'objects_after': objects_after,
            'uncollectable_objects': len(gc.garbage)
        }
    
    def export_leak_report(self, hours: int = 24, format: str = 'json') -> str:
        """Export leak detection report"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_leaks = [leak for leak in self.detection_history if leak.detected_at >= cutoff_time]
        
        if format == 'json':
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'summary': self.get_leak_summary(),
                'object_tracking': self.get_object_tracking_info(),
                'leaks': [leak.to_dict() for leak in recent_leaks],
                'leak_statistics': {
                    'leaks_by_type': dict(LeakType(leak.leak_type).value for leak in recent_leaks),
                    'leaks_by_severity': dict(LeakSeverity(leak.severity).value for leak in recent_leaks),
                    'avg_confidence': sum(leak.confidence for leak in recent_leaks) / len(recent_leaks) if recent_leaks else 0,
                    'total_memory_leaked': sum(leak.memory_size for leak in recent_leaks)
                }
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['leak_id', 'detected_at', 'leak_type', 'severity', 'object_type',
                     'object_count', 'memory_size', 'growth_rate', 'confidence', 'resolved']
            writer.writerow(header)
            
            # Write leaks
            for leak in recent_leaks:
                row = [
                    leak.leak_id,
                    leak.detected_at.isoformat(),
                    leak.leak_type.value,
                    leak.severity.value,
                    leak.object_type,
                    leak.object_count,
                    leak.memory_size,
                    leak.growth_rate,
                    leak.confidence,
                    leak.resolved
                ]
                writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Initialize global leak detector
leak_detector = MemoryLeakDetector()
