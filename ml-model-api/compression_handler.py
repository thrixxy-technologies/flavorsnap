#!/usr/bin/env python3
"""
Advanced Compression Handler for FlavorSnap ML Model API
Implements multiple compression algorithms with adaptive selection and optimization
"""

import os
import time
import logging
import threading
import gzip
import zlib
import brotli
import lz4.frame
import lzma
import bz2
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import pytz
from datetime import datetime, timedelta
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/compression_handler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "brotli"
    LZ4 = "lz4"
    LZMA = "lzma"
    BZIP2 = "bzip2"

class CompressionLevel(Enum):
    """Compression levels"""
    FASTEST = 1
    FAST = 3
    BALANCED = 6
    BEST = 9

@dataclass
class CompressionConfig:
    """Compression configuration"""
    default_algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    default_level: CompressionLevel = CompressionLevel.BALANCED
    enable_adaptive_selection: bool = True
    enable_parallel_compression: bool = True
    max_workers: int = 4
    enable_streaming: bool = True
    chunk_size: int = 8192
    enable_caching: bool = True
    cache_size_mb: int = 100
    enable_metrics: bool = True
    min_size_for_compression: int = 1024
    max_compression_ratio: float = 0.9

@dataclass
class CompressionMetrics:
    """Compression performance metrics"""
    algorithm: CompressionAlgorithm
    level: int
    original_size: int
    compressed_size: int
    compression_time_ms: float
    decompression_time_ms: float
    compression_ratio: float
    throughput_mbps: float
    timestamp: datetime

class CompressionHandler:
    """Advanced compression handler with adaptive algorithms"""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Compression registry
        self.compressors = {}
        self.decompressors = {}
        self._init_compressors()
        
        # Performance tracking
        self.metrics_history = []
        self.algorithm_performance = {}
        self.adaptive_weights = {}
        
        # Caching
        self.compression_cache = {}
        self.cache_lock = threading.Lock()
        
        # Thread pool for parallel compression
        self.executor = None
        if config.enable_parallel_compression:
            from concurrent.futures import ThreadPoolExecutor
            self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # Initialize adaptive weights
        self._init_adaptive_weights()
        
        logger.info(f"CompressionHandler initialized with {config.default_algorithm.value}")
    
    def _init_compressors(self):
        """Initialize compression and decompression functions"""
        self.compressors = {
            CompressionAlgorithm.NONE: self._compress_none,
            CompressionAlgorithm.GZIP: self._compress_gzip,
            CompressionAlgorithm.DEFLATE: self._compress_deflate,
            CompressionAlgorithm.BROTLI: self._compress_brotli,
            CompressionAlgorithm.LZ4: self._compress_lz4,
            CompressionAlgorithm.LZMA: self._compress_lzma,
            CompressionAlgorithm.BZIP2: self._compress_bzip2
        }
        
        self.decompressors = {
            CompressionAlgorithm.NONE: self._decompress_none,
            CompressionAlgorithm.GZIP: self._decompress_gzip,
            CompressionAlgorithm.DEFLATE: self._decompress_deflate,
            CompressionAlgorithm.BROTLI: self._decompress_brotli,
            CompressionAlgorithm.LZ4: self._decompress_lz4,
            CompressionAlgorithm.LZMA: self._decompress_lzma,
            CompressionAlgorithm.BZIP2: self._decompress_bzip2
        }
        
        logger.info(f"Initialized {len(self.compressors)} compression algorithms")
    
    def _init_adaptive_weights(self):
        """Initialize adaptive algorithm weights"""
        for algorithm in CompressionAlgorithm:
            if algorithm != CompressionAlgorithm.NONE:
                self.adaptive_weights[algorithm] = {
                    'speed_weight': 0.5,
                    'ratio_weight': 0.5,
                    'overall_score': 0.5,
                    'usage_count': 0,
                    'avg_compression_time': 0.0,
                    'avg_compression_ratio': 0.0
                }
    
    def compress(self, data: Union[str, bytes], 
                algorithm: Optional[CompressionAlgorithm] = None,
                level: Optional[int] = None) -> bytes:
        """Compress data using specified or optimal algorithm"""
        try:
            # Convert to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Check if compression is beneficial
            if len(data) < self.config.min_size_for_compression:
                return data
            
            # Check cache first
            if self.config.enable_caching:
                cached_result = self._get_cached_compression(data, algorithm, level)
                if cached_result:
                    return cached_result
            
            # Select algorithm
            if algorithm is None:
                algorithm = self._select_optimal_algorithm(data)
            
            # Select compression level
            if level is None:
                level = self.config.default_level.value
            
            # Compress data
            start_time = time.time()
            compressed_data = self.compressors[algorithm](data, level)
            compression_time = (time.time() - start_time) * 1000
            
            # Verify compression was beneficial
            if len(compressed_data) >= len(data) * self.config.max_compression_ratio:
                return data
            
            # Cache result
            if self.config.enable_caching:
                self._cache_compression(data, compressed_data, algorithm, level)
            
            # Record metrics
            self._record_compression_metrics(
                algorithm, level, len(data), len(compressed_data), compression_time
            )
            
            return compressed_data
            
        except Exception as e:
            self.logger.error(f"Compression failed: {str(e)}")
            return data if isinstance(data, bytes) else data.encode('utf-8')
    
    def decompress(self, compressed_data: bytes, 
                  algorithm: CompressionAlgorithm) -> bytes:
        """Decompress data using specified algorithm"""
        try:
            start_time = time.time()
            decompressed_data = self.decompressors[algorithm](compressed_data)
            decompression_time = (time.time() - start_time) * 1000
            
            # Record decompression metrics
            self._record_decompression_metrics(
                algorithm, len(compressed_data), len(decompressed_data), decompression_time
            )
            
            return decompressed_data
            
        except Exception as e:
            self.logger.error(f"Decompression failed: {str(e)}")
            raise
    
    def compress_streaming(self, data_stream, algorithm: Optional[CompressionAlgorithm] = None,
                         level: Optional[int] = None):
        """Compress data in streaming fashion"""
        if not self.config.enable_streaming:
            raise ValueError("Streaming compression is disabled")
        
        algorithm = algorithm or self._select_optimal_algorithm(b'')
        level = level or self.config.default_level.value
        
        # Implementation would depend on the specific algorithm
        # This is a simplified version
        for chunk in data_stream:
            compressed_chunk = self.compress(chunk, algorithm, level)
            yield compressed_chunk
    
    def _select_optimal_algorithm(self, data: bytes) -> CompressionAlgorithm:
        """Select optimal compression algorithm based on data characteristics"""
        if not self.config.enable_adaptive_selection:
            return self.config.default_algorithm
        
        # Analyze data characteristics
        data_size = len(data)
        entropy = self._calculate_entropy(data)
        
        # Calculate scores for each algorithm
        best_algorithm = self.config.default_algorithm
        best_score = 0.0
        
        for algorithm in CompressionAlgorithm:
            if algorithm == CompressionAlgorithm.NONE:
                continue
            
            # Get adaptive weights
            weights = self.adaptive_weights.get(algorithm, {})
            
            # Calculate score based on data characteristics and historical performance
            score = self._calculate_algorithm_score(algorithm, data_size, entropy, weights)
            
            if score > best_score:
                best_score = score
                best_algorithm = algorithm
        
        return best_algorithm
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate entropy of data for compression prediction"""
        if not data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        data_len = len(data)
        
        for count in byte_counts.values():
            probability = count / data_len
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    def _calculate_algorithm_score(self, algorithm: CompressionAlgorithm, 
                                data_size: int, entropy: float, 
                                weights: Dict[str, Any]) -> float:
        """Calculate algorithm selection score"""
        base_score = 0.5
        
        # Factor in data size
        if data_size < 1024:  # Small data
            if algorithm in [CompressionAlgorithm.LZ4, CompressionAlgorithm.NONE]:
                base_score += 0.2
        elif data_size > 1024 * 1024:  # Large data
            if algorithm in [CompressionAlgorithm.BROTLI, CompressionAlgorithm.LZMA]:
                base_score += 0.2
        
        # Factor in entropy
        if entropy < 6.0:  # Low entropy (highly compressible)
            if algorithm in [CompressionAlgorithm.BROTLI, CompressionAlgorithm.LZMA, CompressionAlgorithm.BZIP2]:
                base_score += 0.2
        elif entropy > 7.5:  # High entropy (less compressible)
            if algorithm in [CompressionAlgorithm.LZ4, CompressionAlgorithm.NONE]:
                base_score += 0.2
        
        # Factor in historical performance
        if weights:
            speed_score = 1.0 - weights.get('avg_compression_time', 0) / 1000  # Normalize
            ratio_score = 1.0 - weights.get('avg_compression_ratio', 0)
            
            base_score += (speed_score * weights.get('speed_weight', 0.5))
            base_score += (ratio_score * weights.get('ratio_weight', 0.5))
        
        return max(0.0, min(1.0, base_score))
    
    def _compress_none(self, data: bytes, level: int) -> bytes:
        """No compression (pass-through)"""
        return data
    
    def _decompress_none(self, data: bytes) -> bytes:
        """No decompression (pass-through)"""
        return data
    
    def _compress_gzip(self, data: bytes, level: int) -> bytes:
        """GZIP compression"""
        return gzip.compress(data, compresslevel=level)
    
    def _decompress_gzip(self, data: bytes) -> bytes:
        """GZIP decompression"""
        return gzip.decompress(data)
    
    def _compress_deflate(self, data: bytes, level: int) -> bytes:
        """DEFLATE compression"""
        return zlib.compress(data, level=level)
    
    def _decompress_deflate(self, data: bytes) -> bytes:
        """DEFLATE decompression"""
        return zlib.decompress(data)
    
    def _compress_brotli(self, data: bytes, level: int) -> bytes:
        """Brotli compression"""
        return brotli.compress(data, quality=level)
    
    def _decompress_brotli(self, data: bytes) -> bytes:
        """Brotli decompression"""
        return brotli.decompress(data)
    
    def _compress_lz4(self, data: bytes, level: int) -> bytes:
        """LZ4 compression"""
        return lz4.frame.compress(data, compression_level=level)
    
    def _decompress_lz4(self, data: bytes) -> bytes:
        """LZ4 decompression"""
        return lz4.frame.decompress(data)
    
    def _compress_lzma(self, data: bytes, level: int) -> bytes:
        """LZMA compression"""
        return lzma.compress(data, preset=level)
    
    def _decompress_lzma(self, data: bytes) -> bytes:
        """LZMA decompression"""
        return lzma.decompress(data)
    
    def _compress_bzip2(self, data: bytes, level: int) -> bytes:
        """BZIP2 compression"""
        return bz2.compress(data, compresslevel=level)
    
    def _decompress_bzip2(self, data: bytes) -> bytes:
        """BZIP2 decompression"""
        return bz2.decompress(data)
    
    def _get_cached_compression(self, data: bytes, algorithm: Optional[CompressionAlgorithm],
                               level: Optional[int]) -> Optional[bytes]:
        """Get cached compression result"""
        if not self.config.enable_caching:
            return None
        
        try:
            # Generate cache key
            data_hash = hashlib.md5(data).hexdigest()
            cache_key = f"{data_hash}_{algorithm}_{level}"
            
            with self.cache_lock:
                if cache_key in self.compression_cache:
                    cached_data, timestamp = self.compression_cache[cache_key]
                    
                    # Check if cache is still valid (1 hour TTL)
                    if (datetime.now(pytz.UTC) - timestamp).total_seconds() < 3600:
                        return cached_data
                    else:
                        # Remove expired cache entry
                        del self.compression_cache[cache_key]
            
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {str(e)}")
        
        return None
    
    def _cache_compression(self, data: bytes, compressed_data: bytes,
                          algorithm: CompressionAlgorithm, level: int):
        """Cache compression result"""
        if not self.config.enable_caching:
            return
        
        try:
            # Check cache size limit
            cache_size = sum(len(c[0]) for c in self.compression_cache.values())
            if cache_size > self.config.cache_size_mb * 1024 * 1024:
                # Remove oldest entries
                sorted_items = sorted(self.compression_cache.items(), 
                                   key=lambda x: x[1][1])
                for i in range(len(sorted_items) // 2):
                    del self.compression_cache[sorted_items[i][0]]
            
            # Add to cache
            data_hash = hashlib.md5(data).hexdigest()
            cache_key = f"{data_hash}_{algorithm}_{level}"
            
            with self.cache_lock:
                self.compression_cache[cache_key] = (compressed_data, datetime.now(pytz.UTC))
            
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {str(e)}")
    
    def _record_compression_metrics(self, algorithm: CompressionAlgorithm, level: int,
                                   original_size: int, compressed_size: int,
                                   compression_time_ms: float):
        """Record compression performance metrics"""
        if not self.config.enable_metrics:
            return
        
        try:
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            throughput_mbps = (original_size * 8) / (compression_time_ms / 1000) / (1024 * 1024)
            
            metrics = CompressionMetrics(
                algorithm=algorithm,
                level=level,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_time_ms=compression_time_ms,
                decompression_time_ms=0.0,  # Will be updated later
                compression_ratio=compression_ratio,
                throughput_mbps=throughput_mbps,
                timestamp=datetime.now(pytz.UTC)
            )
            
            self.metrics_history.append(metrics)
            
            # Keep only last 1000 metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            # Update adaptive weights
            self._update_adaptive_weights(algorithm, compression_time_ms, compression_ratio)
            
        except Exception as e:
            self.logger.error(f"Failed to record compression metrics: {str(e)}")
    
    def _record_decompression_metrics(self, algorithm: CompressionAlgorithm,
                                    compressed_size: int, original_size: int,
                                    decompression_time_ms: float):
        """Record decompression performance metrics"""
        if not self.config.enable_metrics:
            return
        
        try:
            # Find corresponding compression metrics and update decompression time
            for metrics in reversed(self.metrics_history):
                if (metrics.algorithm == algorithm and 
                    metrics.compressed_size == compressed_size and 
                    metrics.original_size == original_size and
                    metrics.decompression_time_ms == 0.0):
                    metrics.decompression_time_ms = decompression_time_ms
                    break
            
        except Exception as e:
            self.logger.error(f"Failed to record decompression metrics: {str(e)}")
    
    def _update_adaptive_weights(self, algorithm: CompressionAlgorithm,
                                compression_time_ms: float, compression_ratio: float):
        """Update adaptive algorithm weights based on performance"""
        if algorithm not in self.adaptive_weights:
            return
        
        try:
            weights = self.adaptive_weights[algorithm]
            
            # Update running averages
            usage_count = weights['usage_count']
            if usage_count == 0:
                weights['avg_compression_time'] = compression_time_ms
                weights['avg_compression_ratio'] = compression_ratio
            else:
                weights['avg_compression_time'] = (
                    (weights['avg_compression_time'] * usage_count + compression_time_ms) / (usage_count + 1)
                )
                weights['avg_compression_ratio'] = (
                    (weights['avg_compression_ratio'] * usage_count + compression_ratio) / (usage_count + 1)
                )
            
            weights['usage_count'] += 1
            
            # Update weights based on performance
            # Prefer faster algorithms with better compression
            speed_score = max(0, 1.0 - compression_time_ms / 1000)  # Normalize to 0-1
            ratio_score = max(0, 1.0 - compression_ratio)  # Lower ratio is better
            
            # Adjust weights gradually
            weights['speed_weight'] = (weights['speed_weight'] * 0.8 + speed_score * 0.2)
            weights['ratio_weight'] = (weights['ratio_weight'] * 0.8 + ratio_score * 0.2)
            
            # Calculate overall score
            weights['overall_score'] = (weights['speed_weight'] + weights['ratio_weight']) / 2
            
        except Exception as e:
            self.logger.error(f"Failed to update adaptive weights: {str(e)}")
    
    def get_compression_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get compression performance metrics"""
        try:
            cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {}
            
            # Calculate aggregates by algorithm
            algorithm_stats = {}
            for metrics in recent_metrics:
                algorithm = metrics.algorithm.value
                if algorithm not in algorithm_stats:
                    algorithm_stats[algorithm] = {
                        'count': 0,
                        'total_original_size': 0,
                        'total_compressed_size': 0,
                        'total_compression_time': 0,
                        'total_decompression_time': 0,
                        'avg_compression_ratio': 0,
                        'avg_compression_time': 0,
                        'avg_decompression_time': 0,
                        'avg_throughput_mbps': 0
                    }
                
                stats = algorithm_stats[algorithm]
                stats['count'] += 1
                stats['total_original_size'] += metrics.original_size
                stats['total_compressed_size'] += metrics.compressed_size
                stats['total_compression_time'] += metrics.compression_time_ms
                stats['total_decompression_time'] += metrics.decompression_time_ms
                stats['avg_throughput_mbps'] += metrics.throughput_mbps
            
            # Calculate averages
            for stats in algorithm_stats.values():
                if stats['count'] > 0:
                    stats['avg_compression_ratio'] = (
                        stats['total_compressed_size'] / stats['total_original_size']
                        if stats['total_original_size'] > 0 else 1.0
                    )
                    stats['avg_compression_time'] = (
                        stats['total_compression_time'] / stats['count']
                    )
                    stats['avg_decompression_time'] = (
                        stats['total_decompression_time'] / stats['count']
                    )
                    stats['avg_throughput_mbps'] = (
                        stats['avg_throughput_mbps'] / stats['count']
                    )
            
            # Overall statistics
            total_original = sum(s['total_original_size'] for s in algorithm_stats.values())
            total_compressed = sum(s['total_compressed_size'] for s in algorithm_stats.values())
            overall_ratio = total_compressed / total_original if total_original > 0 else 1.0
            
            return {
                'time_range_hours': hours,
                'total_operations': len(recent_metrics),
                'overall_compression_ratio': overall_ratio,
                'algorithm_stats': algorithm_stats,
                'adaptive_weights': self.adaptive_weights,
                'cache_stats': {
                    'cache_size': len(self.compression_cache),
                    'cache_memory_mb': sum(len(c[0]) for c in self.compression_cache.values()) / (1024 * 1024)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get compression metrics: {str(e)}")
            return {}
    
    def benchmark_algorithms(self, test_data: bytes, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark all compression algorithms with test data"""
        results = {}
        
        for algorithm in CompressionAlgorithm:
            if algorithm == CompressionAlgorithm.NONE:
                continue
            
            try:
                compression_times = []
                decompression_times = []
                compression_ratios = []
                
                for _ in range(iterations):
                    # Compression
                    start_time = time.time()
                    compressed = self.compress(test_data, algorithm)
                    compression_time = (time.time() - start_time) * 1000
                    compression_times.append(compression_time)
                    
                    # Decompression
                    start_time = time.time()
                    decompressed = self.decompress(compressed, algorithm)
                    decompression_time = (time.time() - start_time) * 1000
                    decompression_times.append(decompression_time)
                    
                    # Verify integrity
                    if decompressed != test_data:
                        raise ValueError(f"Integrity check failed for {algorithm}")
                    
                    # Calculate ratio
                    ratio = len(compressed) / len(test_data)
                    compression_ratios.append(ratio)
                
                results[algorithm.value] = {
                    'avg_compression_time_ms': sum(compression_times) / len(compression_times),
                    'avg_decompression_time_ms': sum(decompression_times) / len(decompression_times),
                    'avg_compression_ratio': sum(compression_ratios) / len(compression_ratios),
                    'min_compression_time_ms': min(compression_times),
                    'max_compression_time_ms': max(compression_times),
                    'min_decompression_time_ms': min(decompression_times),
                    'max_decompression_time_ms': max(decompression_times),
                    'best_compression_ratio': min(compression_ratios),
                    'worst_compression_ratio': max(compression_ratios)
                }
                
            except Exception as e:
                self.logger.error(f"Benchmark failed for {algorithm}: {str(e)}")
                results[algorithm.value] = {'error': str(e)}
        
        return {
            'test_data_size': len(test_data),
            'iterations': iterations,
            'results': results
        }
    
    def optimize_config(self) -> Dict[str, Any]:
        """Optimize compression configuration based on metrics"""
        try:
            metrics = self.get_compression_metrics(hours=24)
            
            if not metrics:
                return {'status': 'no_data', 'message': 'No metrics available'}
            
            recommendations = []
            changes_made = []
            
            # Analyze algorithm performance
            algorithm_stats = metrics.get('algorithm_stats', {})
            if algorithm_stats:
                # Find best performing algorithm
                best_algorithm = None
                best_score = 0
                
                for algorithm, stats in algorithm_stats.items():
                    # Calculate performance score
                    speed_score = 1.0 / (stats['avg_compression_time'] + 1)
                    ratio_score = 1.0 - stats['avg_compression_ratio']
                    overall_score = (speed_score + ratio_score) / 2
                    
                    if overall_score > best_score:
                        best_score = overall_score
                        best_algorithm = algorithm
                
                if best_algorithm and best_algorithm != self.config.default_algorithm.value:
                    recommendations.append(f"Consider switching to {best_algorithm} for better performance")
            
            # Analyze compression ratio
            overall_ratio = metrics.get('overall_compression_ratio', 1.0)
            if overall_ratio > 0.8:
                recommendations.append("Low compression efficiency - consider different algorithm or data preprocessing")
            
            # Analyze cache efficiency
            cache_stats = metrics.get('cache_stats', {})
            if cache_stats.get('cache_memory_mb', 0) > self.config.cache_size_mb * 0.9:
                recommendations.append("Cache nearly full - consider increasing cache size")
            
            return {
                'status': 'analyzed',
                'current_metrics': metrics,
                'recommendations': recommendations,
                'changes_made': changes_made,
                'current_config': asdict(self.config)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to optimize config: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def close(self):
        """Close compression handler and cleanup resources"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            
            # Clear cache
            with self.cache_lock:
                self.compression_cache.clear()
            
            logger.info("CompressionHandler closed")
            
        except Exception as e:
            self.logger.error(f"Failed to close CompressionHandler: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = CompressionConfig(
        default_algorithm=CompressionAlgorithm.GZIP,
        default_level=CompressionLevel.BALANCED,
        enable_adaptive_selection=True,
        enable_parallel_compression=True,
        enable_caching=True
    )
    
    # Create compression handler
    handler = CompressionHandler(config)
    
    try:
        # Example compression
        test_data = b"This is test data for compression testing. " * 100
        compressed = handler.compress(test_data)
        decompressed = handler.decompress(compressed, CompressionAlgorithm.GZIP)
        
        print(f"Original size: {len(test_data)}")
        print(f"Compressed size: {len(compressed)}")
        print(f"Compression ratio: {len(compressed) / len(test_data):.2f}")
        print(f"Integrity check: {test_data == decompressed}")
        
        # Get metrics
        metrics = handler.get_compression_metrics()
        print(f"Compression metrics: {metrics}")
        
        # Benchmark algorithms
        benchmark = handler.benchmark_algorithms(test_data)
        print(f"Benchmark results: {benchmark}")
        
    finally:
        handler.close()
