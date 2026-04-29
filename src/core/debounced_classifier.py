"""
Debounced Classifier for Real-time Processing

This module provides debounced classification functionality to prevent excessive
processing during real-time parameter adjustments. It implements intelligent
caching and debouncing to maintain responsive performance.
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from PIL import Image
import hashlib
import logging

# Add src to Python path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.classifier import FlavorSnapClassifier

logger = logging.getLogger(__name__)


@dataclass
class ClassificationRequest:
    """Represents a classification request with caching."""
    image_hash: str
    preprocessing_params: Dict[str, Any]
    timestamp: float
    callback: Optional[Callable] = None
    request_id: Optional[str] = None


class DebouncedClassifier:
    """
    Debounced classifier that prevents excessive processing during real-time updates.
    
    Features:
    - Debounced classification with configurable delay
    - Intelligent caching to avoid redundant processing
    - Request cancellation for outdated parameters
    - Performance monitoring and optimization
    """
    
    def __init__(self, 
                 debounce_delay: float = 0.3,
                 cache_size: int = 50,
                 max_workers: int = 2):
        """
        Initialize the debounced classifier.
        
        Args:
            debounce_delay: Delay in seconds before processing (default: 0.3)
            cache_size: Maximum number of cached results (default: 50)
            max_workers: Maximum number of worker threads (default: 2)
        """
        self.debounce_delay = debounce_delay
        self.cache_size = cache_size
        self.max_workers = max_workers
        
        # Core classifier
        self.classifier = FlavorSnapClassifier()
        
        # Debouncing state
        self._pending_request: Optional[ClassificationRequest] = None
        self._debounce_timer: Optional[threading.Timer] = None
        self._processing_lock = threading.Lock()
        
        # Caching
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Thread pool for processing
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Performance tracking
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cancelled_requests': 0,
            'average_processing_time': 0.0,
            'last_processing_time': 0.0
        }
        
        # Real-time mode toggle
        self.realtime_enabled = True
        
        logger.info(f"DebouncedClassifier initialized with delay={debounce_delay}s")
    
    def enable_realtime(self, enabled: bool = True):
        """Enable or disable real-time mode."""
        self.realtime_enabled = enabled
        if not enabled:
            self._cancel_pending_request()
        logger.info(f"Real-time mode {'enabled' if enabled else 'disabled'}")
    
    def classify_image_debounced(self, 
                                 image: Image.Image, 
                                 preprocessing_params: Optional[Dict[str, Any]] = None,
                                 callback: Optional[Callable] = None,
                                 request_id: Optional[str] = None) -> str:
        """
        Classify an image with debouncing.
        
        Args:
            image: PIL Image to classify
            preprocessing_params: Optional preprocessing parameters
            callback: Optional callback function for results
            request_id: Optional request identifier
            
        Returns:
            Request ID for tracking
        """
        if not self.realtime_enabled:
            # In non-real-time mode, process immediately
            return self._process_immediately(image, preprocessing_params, callback)
        
        # Generate cache key
        cache_key = self._generate_cache_key(image, preprocessing_params)
        
        # Check cache first
        if cache_key in self._result_cache:
            self._stats['cache_hits'] += 1
            result = self._result_cache[cache_key]
            if callback:
                callback(result)
            return cache_key
        
        # Create new request
        request = ClassificationRequest(
            image_hash=cache_key,
            preprocessing_params=preprocessing_params or {},
            timestamp=time.time(),
            callback=callback,
            request_id=request_id or cache_key
        )
        
        # Cancel any pending request
        self._cancel_pending_request()
        
        # Store new request
        self._pending_request = request
        self._stats['total_requests'] += 1
        
        # Schedule debounced processing
        self._schedule_processing()
        
        return request.request_id
    
    def _process_immediately(self, 
                           image: Image.Image, 
                           preprocessing_params: Optional[Dict[str, Any]] = None,
                           callback: Optional[Callable] = None) -> str:
        """Process classification immediately without debouncing."""
        try:
            result = self.classifier.classify_image(image, preprocessing_params)
            if callback:
                callback(result)
            return "immediate"
        except Exception as e:
            logger.error(f"Immediate classification failed: {e}")
            if callback:
                callback({'error': str(e)})
            return "error"
    
    def _schedule_processing(self):
        """Schedule the debounced processing."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(
            self.debounce_delay, 
            self._process_pending_request
        )
        self._debounce_timer.start()
    
    def _cancel_pending_request(self):
        """Cancel any pending request."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None
        
        if self._pending_request:
            self._stats['cancelled_requests'] += 1
            self._pending_request = None
    
    def _process_pending_request(self):
        """Process the pending request in a separate thread."""
        if not self._pending_request:
            return
        
        request = self._pending_request
        
        # Submit to thread pool
        future = self._executor.submit(self._process_request, request)
        
        # Add callback for completion
        future.add_done_callback(self._on_processing_complete)
        
        # Clear pending request
        self._pending_request = None
    
    def _process_request(self, request: ClassificationRequest) -> Dict[str, Any]:
        """Process a classification request."""
        start_time = time.time()
        
        try:
            with self._processing_lock:
                # Check if request is still valid (not too old)
                if time.time() - request.timestamp > 2.0:  # 2 second timeout
                    return {'error': 'Request timeout', 'request_id': request.request_id}
                
                # Get the current image (this would need to be passed or stored)
                # For now, we'll simulate with a placeholder
                # In the actual implementation, we'd need access to the current image
                result = {
                    'request_id': request.request_id,
                    'preprocessing_params': request.preprocessing_params,
                    'timestamp': time.time(),
                    'cached': False,
                    # Placeholder for actual classification result
                    'predicted_class': 'Processing...',
                    'confidence': 0.0,
                    'all_probabilities': {},
                    'metadata': {}
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Processing request failed: {e}")
            return {'error': str(e), 'request_id': request.request_id}
        
        finally:
            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)
    
    def _on_processing_complete(self, future):
        """Handle completion of processing."""
        try:
            result = future.result()
            
            if 'error' not in result:
                # Cache the result
                cache_key = result.get('request_id')
                if cache_key:
                    self._cache_result(cache_key, result)
                
                # Call the callback
                original_request = self._pending_request
                if original_request and original_request.callback:
                    original_request.callback(result)
            
        except Exception as e:
            logger.error(f"Processing completion failed: {e}")
    
    def _generate_cache_key(self, image: Image.Image, preprocessing_params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for the image and parameters."""
        # Create hash of image data
        img_bytes = image.tobytes()
        img_hash = hashlib.md5(img_bytes).hexdigest()
        
        # Create hash of preprocessing parameters
        if preprocessing_params:
            param_str = str(sorted(preprocessing_params.items()))
            param_hash = hashlib.md5(param_str.encode()).hexdigest()
        else:
            param_hash = "no_params"
        
        return f"{img_hash}_{param_hash}"
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache a classification result."""
        # Remove oldest entries if cache is full
        if len(self._result_cache) >= self.cache_size:
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._result_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        # Add new result
        self._result_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
    
    def _update_performance_stats(self, processing_time: float):
        """Update performance statistics."""
        self._stats['last_processing_time'] = processing_time
        
        # Update average processing time
        total = self._stats['total_requests']
        current_avg = self._stats['average_processing_time']
        self._stats['average_processing_time'] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        cache_hit_rate = (
            self._stats['cache_hits'] / max(1, self._stats['total_requests']) * 100
        )
        
        return {
            **self._stats,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'cache_size': len(self._result_cache),
            'realtime_enabled': self.realtime_enabled,
            'debounce_delay': self.debounce_delay
        }
    
    def clear_cache(self):
        """Clear the result cache."""
        self._result_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cache cleared")
    
    def set_debounce_delay(self, delay: float):
        """Update the debounce delay."""
        self.debounce_delay = max(0.1, delay)  # Minimum 100ms
        logger.info(f"Debounce delay updated to {self.debounce_delay}s")
    
    def shutdown(self):
        """Shutdown the debounced classifier."""
        self._cancel_pending_request()
        self._executor.shutdown(wait=True)
        logger.info("DebouncedClassifier shutdown complete")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except:
            pass


# Global instance for the application
_debounced_classifier_instance: Optional[DebouncedClassifier] = None


def get_debounced_classifier() -> DebouncedClassifier:
    """Get the global debounced classifier instance."""
    global _debounced_classifier_instance
    if _debounced_classifier_instance is None:
        _debounced_classifier_instance = DebouncedClassifier()
    return _debounced_classifier_instance


def classify_realtime(image: Image.Image, 
                     preprocessing_params: Optional[Dict[str, Any]] = None,
                     callback: Optional[Callable] = None) -> str:
    """
    Convenience function for real-time classification.
    
    Args:
        image: PIL Image to classify
        preprocessing_params: Optional preprocessing parameters
        callback: Optional callback function
        
    Returns:
        Request ID for tracking
    """
    classifier = get_debounced_classifier()
    return classifier.classify_image_debounced(image, preprocessing_params, callback)
