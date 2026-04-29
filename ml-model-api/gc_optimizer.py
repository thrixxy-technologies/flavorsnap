"""
Advanced Garbage Collection Optimizer for FlavorSnap API
Implements intelligent GC optimization with adaptive thresholds and performance monitoring
"""
import gc
import time
import threading
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import weakref
import psutil


class GCStrategy(Enum):
    """Garbage collection strategies"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    ADAPTIVE = "adaptive"
    PERFORMANCE = "performance"


class GCPhase(Enum):
    """GC phases"""
    IDLE = "idle"
    MARK = "mark"
    SWEEP = "sweep"
    FINALIZE = "finalize"


@dataclass
class GCStats:
    """GC statistics data structure"""
    timestamp: datetime
    generation: int
    objects_collected: int
    uncollectable_objects: int
    collection_time: float
    memory_before: int
    memory_after: int
    memory_freed: int
    threshold_before: Tuple[int, int, int]
    threshold_after: Tuple[int, int, int]
    strategy: GCStrategy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['strategy'] = self.strategy.value
        return data


@dataclass
class GCOptimizationResult:
    """GC optimization result"""
    optimization_id: str
    timestamp: datetime
    strategy: GCStrategy
    threshold_before: Tuple[int, int, int]
    threshold_after: Tuple[int, int, int]
    collections_before: int
    collections_after: int
    avg_collection_time_before: float
    avg_collection_time_after: float
    memory_efficiency_before: float
    memory_efficiency_after: float
    performance_impact: float
    success: bool
    details: Dict[str, Any]


class GCConfig:
    """GC optimizer configuration"""
    
    # Default thresholds for different strategies
    STRATEGY_THRESHOLDS = {
        GCStrategy.CONSERVATIVE: (1000, 10, 10),
        GCStrategy.BALANCED: (700, 10, 10),
        GCStrategy.AGGRESSIVE: (400, 5, 5),
        GCStrategy.PERFORMANCE: (200, 5, 5)
    }
    
    # Performance targets
    MAX_COLLECTION_TIME = 0.1  # 100ms max collection time
    MAX_MEMORY_GROWTH = 0.2    # 20% max memory growth between collections
    MIN_COLLECTION_EFFICIENCY = 0.1  # Minimum memory freed / collection time ratio
    
    # Adaptive settings
    ADAPTIVE_WINDOW = 100      # Number of collections to consider for adaptation
    ADAPTIVE_INTERVAL = 300    # Seconds between adaptive adjustments
    
    # Monitoring settings
    STATS_HISTORY_SIZE = 1000
    PERFORMANCE_SAMPLE_SIZE = 50


class AdaptiveGCOptimizer:
    """Adaptive GC optimizer that adjusts thresholds based on performance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_strategy = GCStrategy.BALANCED
        self.stats_history: deque = deque(maxlen=GCConfig.STATS_HISTORY_SIZE)
        self.performance_samples: deque = deque(maxlen=GCConfig.PERFORMANCE_SAMPLE_SIZE)
        self.last_adaptation = datetime.now()
        self.optimization_history: List[GCOptimizationResult] = []
        
        # Performance metrics
        self.collection_times: Dict[int, deque] = {
            0: deque(maxlen=50),
            1: deque(maxlen=50),
            2: deque(maxlen=50)
        }
        
        self.memory_efficiency: Dict[int, deque] = {
            0: deque(maxlen=50),
            1: deque(maxlen=50),
            2: deque(maxlen=50)
        }
    
    def optimize_thresholds(self, strategy: GCStrategy = None) -> GCOptimizationResult:
        """Optimize GC thresholds based on strategy"""
        start_time = time.time()
        
        if strategy is None:
            strategy = self.current_strategy
        
        # Get current state
        threshold_before = gc.get_threshold()
        collections_before = sum(gc.get_count())
        
        # Calculate performance metrics before optimization
        avg_time_before = self._get_avg_collection_time()
        memory_efficiency_before = self._get_avg_memory_efficiency()
        
        try:
            # Apply strategy thresholds
            new_threshold = GCConfig.STRATEGY_THRESHOLDS[strategy]
            gc.set_threshold(*new_threshold)
            
            # Force a collection cycle to test new thresholds
            test_start = time.time()
            collected = gc.collect()
            test_time = time.time() - test_start
            
            # Measure memory impact
            memory_before = self._get_memory_usage()
            time.sleep(0.1)  # Allow memory to stabilize
            memory_after = self._get_memory_usage()
            
            # Calculate new metrics
            collections_after = sum(gc.get_count())
            avg_time_after = self._get_avg_collection_time()
            memory_efficiency_after = self._get_avg_memory_efficiency()
            
            # Calculate performance impact
            performance_impact = self._calculate_performance_impact(
                avg_time_before, avg_time_after,
                memory_efficiency_before, memory_efficiency_after
            )
            
            result = GCOptimizationResult(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                strategy=strategy,
                threshold_before=threshold_before,
                threshold_after=new_threshold,
                collections_before=collections_before,
                collections_after=collections_after,
                avg_collection_time_before=avg_time_before,
                avg_collection_time_after=avg_time_after,
                memory_efficiency_before=memory_efficiency_before,
                memory_efficiency_after=memory_efficiency_after,
                performance_impact=performance_impact,
                success=True,
                details={
                    'test_collection_time': test_time,
                    'objects_collected': collected,
                    'memory_change': memory_after - memory_before
                }
            )
            
            self.optimization_history.append(result)
            self.current_strategy = strategy
            
            self.logger.info(f"GC optimization completed: strategy={strategy.value}, impact={performance_impact:.3f}")
            
            return result
            
        except Exception as e:
            # Restore original thresholds on error
            gc.set_threshold(*threshold_before)
            
            result = GCOptimizationResult(
                optimization_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                strategy=strategy,
                threshold_before=threshold_before,
                threshold_after=threshold_before,
                collections_before=collections_before,
                collections_after=collections_before,
                avg_collection_time_before=avg_time_before,
                avg_collection_time_after=avg_time_before,
                memory_efficiency_before=memory_efficiency_before,
                memory_efficiency_after=memory_efficiency_before,
                performance_impact=0.0,
                success=False,
                details={'error': str(e)}
            )
            
            self.optimization_history.append(result)
            self.logger.error(f"GC optimization failed: {str(e)}")
            
            return result
    
    def adapt_thresholds(self) -> GCOptimizationResult:
        """Adapt thresholds based on recent performance"""
        if len(self.stats_history) < GCConfig.ADAPTIVE_WINDOW:
            # Not enough data for adaptation
            return self.optimize_thresholds(GCStrategy.BALANCED)
        
        # Analyze recent performance
        recent_stats = list(self.stats_history)[-GCConfig.ADAPTIVE_WINDOW:]
        
        # Calculate performance indicators
        avg_collection_time = statistics.mean([s.collection_time for s in recent_stats])
        avg_memory_freed = statistics.mean([s.memory_freed for s in recent_stats])
        collection_frequency = len(recent_stats) / (recent_stats[-1].timestamp - recent_stats[0].timestamp).total_seconds()
        
        # Determine optimal strategy
        if avg_collection_time > GCConfig.MAX_COLLECTION_TIME:
            # Collection too slow - use conservative strategy
            optimal_strategy = GCStrategy.CONSERVATIVE
        elif avg_memory_freed < 1024 * 1024:  # Less than 1MB freed
            # Low efficiency - use aggressive strategy
            optimal_strategy = GCStrategy.AGGRESSIVE
        elif collection_frequency > 10:  # Too many collections
            # Too frequent - use conservative strategy
            optimal_strategy = GCStrategy.CONSERVATIVE
        else:
            # Balanced performance
            optimal_strategy = GCStrategy.BALANCED
        
        # Apply adaptive strategy
        result = self.optimize_thresholds(optimal_strategy)
        result.details['adaptive_reasoning'] = {
            'avg_collection_time': avg_collection_time,
            'avg_memory_freed': avg_memory_freed,
            'collection_frequency': collection_frequency,
            'chosen_strategy': optimal_strategy.value
        }
        
        self.last_adaptation = datetime.now()
        
        return result
    
    def record_collection(self, generation: int, objects_collected: int, 
                         collection_time: float, memory_before: int, memory_after: int):
        """Record GC collection statistics"""
        memory_freed = memory_before - memory_after
        
        stats = GCStats(
            timestamp=datetime.now(),
            generation=generation,
            objects_collected=objects_collected,
            uncollectable_objects=len(gc.garbage),
            collection_time=collection_time,
            memory_before=memory_before,
            memory_after=memory_after,
            memory_freed=memory_freed,
            threshold_before=gc.get_threshold(),
            threshold_after=gc.get_threshold(),
            strategy=self.current_strategy
        )
        
        self.stats_history.append(stats)
        
        # Update performance metrics
        self.collection_times[generation].append(collection_time)
        
        if collection_time > 0:
            efficiency = memory_freed / collection_time
            self.memory_efficiency[generation].append(efficiency)
    
    def _get_avg_collection_time(self) -> float:
        """Get average collection time across all generations"""
        all_times = []
        for gen_times in self.collection_times.values():
            all_times.extend(gen_times)
        
        return statistics.mean(all_times) if all_times else 0.0
    
    def _get_avg_memory_efficiency(self) -> float:
        """Get average memory efficiency across all generations"""
        all_efficiency = []
        for gen_efficiency in self.memory_efficiency.values():
            all_efficiency.extend(gen_efficiency)
        
        return statistics.mean(all_efficiency) if all_efficiency else 0.0
    
    def _calculate_performance_impact(self, time_before: float, time_after: float,
                                    efficiency_before: float, efficiency_after: float) -> float:
        """Calculate performance impact score"""
        # Normalize metrics
        time_impact = (time_before - time_after) / time_before if time_before > 0 else 0
        efficiency_impact = (efficiency_after - efficiency_before) / efficiency_before if efficiency_before > 0 else 0
        
        # Weighted combination (efficiency more important)
        return (time_impact * 0.3 + efficiency_impact * 0.7)
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage"""
        process = psutil.Process()
        return process.memory_info().rss
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary"""
        if not self.optimization_history:
            return {}
        
        successful_optimizations = [opt for opt in self.optimization_history if opt.success]
        
        return {
            'total_optimizations': len(self.optimization_history),
            'successful_optimizations': len(successful_optimizations),
            'current_strategy': self.current_strategy.value,
            'current_threshold': gc.get_threshold(),
            'avg_performance_impact': statistics.mean([opt.performance_impact for opt in successful_optimizations]) if successful_optimizations else 0,
            'last_optimization': self.optimization_history[-1].timestamp.isoformat() if self.optimization_history else None,
            'strategies_used': list(set([opt.strategy.value for opt in self.optimization_history])),
            'collections_tracked': len(self.stats_history)
        }


class GenerationalGCAnalyzer:
    """Analyzer for generational GC behavior"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.generation_stats: Dict[int, List[GCStats]] = {0: [], 1: [], 2: []}
        self.promotion_rates: Dict[int, deque] = {
            0: deque(maxlen=100),  # Gen 0 to Gen 1
            1: deque(maxlen=100)   # Gen 1 to Gen 2
        }
    
    def analyze_generational_behavior(self) -> Dict[str, Any]:
        """Analyze generational GC behavior"""
        analysis = {}
        
        for generation in range(3):
            gen_stats = self.generation_stats[generation]
            
            if not gen_stats:
                continue
            
            # Calculate metrics
            collection_times = [s.collection_time for s in gen_stats]
            memory_freed = [s.memory_freed for s in gen_stats]
            objects_collected = [s.objects_collected for s in gen_stats]
            
            analysis[f'generation_{generation}'] = {
                'collections': len(gen_stats),
                'avg_collection_time': statistics.mean(collection_times) if collection_times else 0,
                'max_collection_time': max(collection_times) if collection_times else 0,
                'avg_memory_freed': statistics.mean(memory_freed) if memory_freed else 0,
                'total_memory_freed': sum(memory_freed),
                'avg_objects_collected': statistics.mean(objects_collected) if objects_collected else 0,
                'promotion_rate': statistics.mean(self.promotion_rates.get(generation, [0])) if self.promotion_rates.get(generation) else 0
            }
        
        return analysis
    
    def detect_generational_issues(self) -> List[str]:
        """Detect generational GC issues"""
        issues = []
        
        for generation in range(3):
            gen_stats = self.generation_stats[generation]
            
            if len(gen_stats) < 10:
                continue
            
            # Check for long collection times
            collection_times = [s.collection_time for s in gen_stats]
            avg_time = statistics.mean(collection_times)
            
            if avg_time > GCConfig.MAX_COLLECTION_TIME:
                issues.append(f"Generation {generation} has slow collections (avg: {avg_time:.3f}s)")
            
            # Check for low efficiency
            memory_freed = [s.memory_freed for s in gen_stats]
            avg_freed = statistics.mean(memory_freed)
            
            if avg_freed < 1024 * 100:  # Less than 100KB
                issues.append(f"Generation {generation} has low efficiency (avg freed: {avg_freed / 1024:.1f}KB)")
            
            # Check for high promotion rates (objects surviving too long)
            if generation < 2:
                promotion_rate = statistics.mean(self.promotion_rates.get(generation, [0]))
                if promotion_rate > 0.8:  # 80% promotion rate
                    issues.append(f"Generation {generation} has high promotion rate ({promotion_rate:.1%})")
        
        return issues
    
    def record_promotion(self, from_generation: int, to_generation: int, promotion_rate: float):
        """Record object promotion rate"""
        if from_generation in self.promotion_rates:
            self.promotion_rates[from_generation].append(promotion_rate)


class GCPerformanceMonitor:
    """Monitor GC performance in real-time"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.monitoring_active = False
        self.monitor_thread = None
        self.adaptive_optimizer = AdaptiveGCOptimizer()
        self.generation_analyzer = GenerationalGCAnalyzer()
        
        # Performance tracking
        self.collection_callbacks: List[Callable[[GCStats], None]] = []
        self.performance_alerts: List[str] = []
        
        # Install GC hooks
        self._install_gc_hooks()
    
    def _install_gc_hooks(self):
        """Install GC collection hooks"""
        def gc_callback(phase, info):
            if phase == "start":
                self._collection_start_time = time.time()
                self._collection_memory_before = self._get_memory_usage()
            elif phase == "stop":
                collection_time = time.time() - self._collection_start_time
                memory_after = self._get_memory_usage()
                
                # Record statistics
                self.adaptive_optimizer.record_collection(
                    generation=info.get('generation', 0),
                    objects_collected=info.get('collected', 0),
                    collection_time=collection_time,
                    memory_before=self._collection_memory_before,
                    memory_after=memory_after
                )
        
        # Note: Python's gc module doesn't provide direct hooks
        # This would need to be implemented using custom GC or monkey patching
        # For now, we'll use periodic monitoring
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("GC performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("GC performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        last_gc_counts = gc.get_count()
        
        while self.monitoring_active:
            try:
                current_gc_counts = gc.get_count()
                
                # Check if GC ran
                if any(current > last for current, last in zip(current_gc_counts, last_gc_counts)):
                    # GC ran - collect statistics
                    self._collect_gc_statistics(last_gc_counts, current_gc_counts)
                
                last_gc_counts = current_gc_counts
                
                # Check for adaptive optimization
                if (datetime.now() - self.adaptive_optimizer.last_adaptation).total_seconds() > GCConfig.ADAPTIVE_INTERVAL:
                    self.adaptive_optimizer.adapt_thresholds()
                
                # Check for performance issues
                self._check_performance_issues()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"GC monitoring error: {str(e)}")
                time.sleep(1)
    
    def _collect_gc_statistics(self, old_counts: Tuple[int, int, int], new_counts: Tuple[int, int, int]):
        """Collect GC statistics after collection"""
        for generation, (old_count, new_count) in enumerate(zip(old_counts, new_counts)):
            if new_count > old_count:
                # Collection occurred in this generation
                collection_time = 0.001  # Approximate
                memory_before = self._get_memory_usage()
                
                # Force a small collection to get accurate stats
                collected = gc.collect(generation)
                memory_after = self._get_memory_usage()
                
                # Record statistics
                self.adaptive_optimizer.record_collection(
                    generation=generation,
                    objects_collected=collected,
                    collection_time=collection_time,
                    memory_before=memory_before,
                    memory_after=memory_after
                )
    
    def _check_performance_issues(self):
        """Check for performance issues"""
        recent_stats = list(self.adaptive_optimizer.stats_history)[-10:]
        
        if not recent_stats:
            return
        
        # Check for slow collections
        slow_collections = [s for s in recent_stats if s.collection_time > GCConfig.MAX_COLLECTION_TIME]
        if len(slow_collections) > 3:
            alert = f"Multiple slow GC collections detected (max: {max(s.collection_time for s in slow_collections):.3f}s)"
            if alert not in self.performance_alerts:
                self.performance_alerts.append(alert)
                self.logger.warning(alert)
        
        # Check for memory leaks
        memory_usage = [s.memory_after for s in recent_stats]
        if len(memory_usage) > 5:
            memory_trend = (memory_usage[-1] - memory_usage[0]) / len(memory_usage)
            if memory_trend > 1024 * 1024:  # Growing by more than 1MB per collection
                alert = f"Possible memory leak detected (growth rate: {memory_trend / 1024:.1f}KB/collection)"
                if alert not in self.performance_alerts:
                    self.performance_alerts.append(alert)
                    self.logger.warning(alert)
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage"""
        process = psutil.Process()
        return process.memory_info().rss
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'optimization_summary': self.adaptive_optimizer.get_optimization_summary(),
            'generational_analysis': self.generation_analyzer.analyze_generational_behavior(),
            'performance_issues': self.generation_analyzer.detect_generational_issues(),
            'current_thresholds': gc.get_threshold(),
            'gc_counts': gc.get_count(),
            'monitoring_active': self.monitoring_active,
            'performance_alerts': self.performance_alerts[-10:]  # Last 10 alerts
        }
    
    def force_collection(self, generation: int = -1) -> Dict[str, Any]:
        """Force garbage collection and return results"""
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        if generation == -1:
            # Collect all generations
            collected = gc.collect()
        else:
            # Collect specific generation
            collected = gc.collect(generation)
        
        collection_time = time.time() - start_time
        memory_after = self._get_memory_usage()
        memory_freed = memory_before - memory_after
        
        return {
            'generation': generation,
            'objects_collected': collected,
            'collection_time': collection_time,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_freed': memory_freed,
            'gc_counts_before': list(gc.get_count()),
            'gc_counts_after': list(gc.get_count())
        }


# Initialize global GC optimizer
gc_optimizer = GCPerformanceMonitor()
