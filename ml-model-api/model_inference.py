"""
Model Inference with Advanced Caching Integration
Provides ML model inference with caching, monitoring, and optimization
"""

import torch
import torchvision.transforms as transforms
from PIL import Image
import io
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib

logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    """Model status"""
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UPDATING = "updating"

class InferenceMode(Enum):
    """Inference modes"""
    SINGLE = "single"
    BATCH = "batch"
    STREAMING = "streaming"

@dataclass
class InferenceRequest:
    """Inference request data"""
    request_id: str
    image_data: bytes
    model_version: str
    mode: InferenceMode
    timestamp: datetime
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class InferenceResult:
    """Inference result data"""
    request_id: str
    predictions: List[Dict[str, Any]]
    confidence_scores: List[float]
    processing_time: float
    model_version: str
    cache_hit: bool
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    model_version: str
    total_inferences: int
    avg_processing_time: float
    cache_hit_rate: float
    error_rate: float
    memory_usage_mb: float
    gpu_utilization: float
    last_updated: datetime

class ModelInference:
    """Advanced model inference with caching and optimization"""
    
    def __init__(self, model_path: str = None, classes_path: str = None):
        self.model_path = model_path or "model.pth"
        self.classes_path = classes_path or "food_classes.txt"
        self.logger = logging.getLogger(__name__)
        
        # Model state
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.classes = []
        self.status = ModelStatus.LOADING
        self.current_version = "1.0.0"
        
        # Performance tracking
        self.metrics = ModelMetrics(
            model_version=self.current_version,
            total_inferences=0,
            avg_processing_time=0.0,
            cache_hit_rate=0.0,
            error_rate=0.0,
            memory_usage_mb=0.0,
            gpu_utilization=0.0,
            last_updated=datetime.now()
        )
        
        # Caching
        self.result_cache = {}
        self.cache_ttl = timedelta(minutes=15)
        self.max_cache_size = 1000
        
        # Optimization
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.batch_size = 8
        self.transform = None
        
        # Initialize model and classes
        self._load_model()
        self._load_classes()
        self._setup_transforms()
    
    def _load_model(self):
        """Load the ML model"""
        try:
            self.logger.info(f"Loading model from {self.model_path}")
            
            # Load model with error handling
            try:
                self.model = torch.load(self.model_path, map_location=self.device)
                self.model.eval()
                self.model.to(self.device)
                self.status = ModelStatus.READY
                self.logger.info("Model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load model: {e}")
                self.status = ModelStatus.ERROR
                raise
                
        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            self.status = ModelStatus.ERROR
            raise
    
    def _load_classes(self):
        """Load class labels"""
        try:
            with open(self.classes_path, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
            self.logger.info(f"Loaded {len(self.classes)} classes")
        except Exception as e:
            self.logger.error(f"Failed to load classes: {e}")
            # Default classes for Nigerian foods
            self.classes = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam']
    
    def _setup_transforms(self):
        """Setup image transforms for inference"""
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
    
    async def predict(self, request: InferenceRequest) -> InferenceResult:
        """
        Perform model inference with caching
        
        Args:
            request: Inference request
        
        Returns:
            InferenceResult with predictions
        """
        start_time = time.time()
        cache_hit = False
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cache_hit = True
                self.logger.info(f"Cache hit for request {request.request_id}")
                return cached_result
            
            # Perform inference
            if request.mode == InferenceMode.SINGLE:
                result = await self._predict_single(request)
            elif request.mode == InferenceMode.BATCH:
                result = await self._predict_batch([request])
            else:
                result = await self._predict_single(request)  # Default to single
            
            result.cache_hit = cache_hit
            result.processing_time = time.time() - start_time
            
            # Cache result
            self._cache_result(cache_key, result)
            
            # Update metrics
            self._update_metrics(result, cache_hit)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Inference failed for request {request.request_id}: {e}")
            self.metrics.error_rate = (self.metrics.error_rate + 1) / (self.metrics.total_inferences + 1)
            
            # Return error result
            return InferenceResult(
                request_id=request.request_id,
                predictions=[],
                confidence_scores=[],
                processing_time=time.time() - start_time,
                model_version=self.current_version,
                cache_hit=cache_hit,
                timestamp=datetime.now(),
                metadata={'error': str(e)}
            )
    
    async def _predict_single(self, request: InferenceRequest) -> InferenceResult:
        """Perform single image inference"""
        try:
            # Load and preprocess image
            image = self._preprocess_image(request.image_data)
            
            # Perform inference
            with torch.no_grad():
                image = image.unsqueeze(0).to(self.device)
                outputs = self.model(image)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                confidence_scores, predicted_indices = torch.topk(probabilities, min(5, len(self.classes)))
            
            # Convert to lists
            predictions = []
            confidences = confidence_scores.cpu().numpy()[0].tolist()
            indices = predicted_indices.cpu().numpy()[0].tolist()
            
            for i, (idx, conf) in enumerate(zip(indices, confidences)):
                predictions.append({
                    'class': self.classes[idx],
                    'confidence': float(conf),
                    'class_index': int(idx),
                    'rank': i + 1
                })
            
            return InferenceResult(
                request_id=request.request_id,
                predictions=predictions,
                confidence_scores=confidences,
                processing_time=0.0,  # Will be set by caller
                model_version=self.current_version,
                cache_hit=False,
                timestamp=datetime.now(),
                metadata={}
            )
            
        except Exception as e:
            self.logger.error(f"Single prediction failed: {e}")
            raise
    
    async def _predict_batch(self, requests: List[InferenceRequest]) -> List[InferenceResult]:
        """Perform batch inference"""
        try:
            # Preprocess all images
            images = []
            for request in requests:
                image = self._preprocess_image(request.image_data)
                images.append(image)
            
            # Create batch
            batch = torch.stack(images).to(self.device)
            
            # Perform batch inference
            with torch.no_grad():
                outputs = self.model(batch)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                confidence_scores, predicted_indices = torch.topk(probabilities, min(5, len(self.classes)))
            
            # Process results
            results = []
            for i, request in enumerate(requests):
                predictions = []
                confidences = confidence_scores[i].cpu().numpy().tolist()
                indices = predicted_indices[i].cpu().numpy().tolist()
                
                for j, (idx, conf) in enumerate(zip(indices, confidences)):
                    predictions.append({
                        'class': self.classes[idx],
                        'confidence': float(conf),
                        'class_index': int(idx),
                        'rank': j + 1
                    })
                
                results.append(InferenceResult(
                    request_id=request.request_id,
                    predictions=predictions,
                    confidence_scores=confidences,
                    processing_time=0.0,  # Will be set by caller
                    model_version=self.current_version,
                    cache_hit=False,
                    timestamp=datetime.now(),
                    metadata={}
                ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch prediction failed: {e}")
            raise
    
    def _preprocess_image(self, image_data: bytes) -> torch.Tensor:
        """Preprocess image for inference"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply transforms
            tensor = self.transform(image)
            
            return tensor
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            raise
    
    def _generate_cache_key(self, request: InferenceRequest) -> str:
        """Generate cache key for request"""
        # Create hash of image data and request parameters
        image_hash = hashlib.md5(request.image_data).hexdigest()
        key_data = f"{image_hash}:{request.model_version}:{request.mode.value}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[InferenceResult]:
        """Get cached result if valid"""
        if cache_key in self.result_cache:
            cached_item = self.result_cache[cache_key]
            if datetime.now() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['result']
            else:
                # Remove expired cache entry
                del self.result_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: InferenceResult):
        """Cache inference result"""
        try:
            # Check cache size limit
            if len(self.result_cache) >= self.max_cache_size:
                # Remove oldest entry
                oldest_key = min(self.result_cache.keys(), 
                               key=lambda k: self.result_cache[k]['timestamp'])
                del self.result_cache[oldest_key]
            
            # Add new entry
            self.result_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cache result: {e}")
    
    def _update_metrics(self, result: InferenceResult, cache_hit: bool):
        """Update performance metrics"""
        try:
            self.metrics.total_inferences += 1
            
            # Update average processing time (excluding cache hits)
            if not cache_hit:
                total_time = self.metrics.avg_processing_time * (self.metrics.total_inferences - 1)
                self.metrics.avg_processing_time = (total_time + result.processing_time) / self.metrics.total_inferences
            
            # Update cache hit rate
            if cache_hit:
                self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * (self.metrics.total_inferences - 1) + 1) / self.metrics.total_inferences
            else:
                self.metrics.cache_hit_rate = self.metrics.cache_hit_rate * (self.metrics.total_inferences - 1) / self.metrics.total_inferences
            
            # Update memory usage
            if torch.cuda.is_available():
                self.metrics.memory_usage_mb = torch.cuda.memory_allocated() / (1024**2)
                self.metrics.gpu_utilization = torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else 0.0
            
            self.metrics.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to update metrics: {e}")
    
    async def update_model(self, new_model_path: str, new_version: str):
        """Update model with new version"""
        try:
            self.logger.info(f"Updating model to version {new_version}")
            self.status = ModelStatus.UPDATING
            
            # Load new model
            new_model = torch.load(new_model_path, map_location=self.device)
            new_model.eval()
            new_model.to(self.device)
            
            # Test new model
            test_image = torch.randn(1, 3, 224, 224).to(self.device)
            with torch.no_grad():
                _ = new_model(test_image)
            
            # Swap models
            old_model = self.model
            self.model = new_model
            self.current_version = new_version
            self.status = ModelStatus.READY
            
            # Clear cache since model changed
            self.result_cache.clear()
            
            # Update metrics
            self.metrics.model_version = new_version
            self.metrics.last_updated = datetime.now()
            
            self.logger.info(f"Model updated successfully to version {new_version}")
            
            # Clean up old model
            del old_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except Exception as e:
            self.logger.error(f"Model update failed: {e}")
            self.status = ModelStatus.ERROR
            raise
    
    def get_metrics(self) -> ModelMetrics:
        """Get current model metrics"""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get model status information"""
        return {
            'status': self.status.value,
            'model_version': self.current_version,
            'device': str(self.device),
            'classes_count': len(self.classes),
            'cache_size': len(self.result_cache),
            'metrics': asdict(self.metrics)
        }
    
    def clear_cache(self):
        """Clear inference cache"""
        self.result_cache.clear()
        self.logger.info("Inference cache cleared")
    
    def optimize_performance(self):
        """Optimize model performance"""
        try:
            # Enable model optimization
            if hasattr(self.model, 'eval'):
                self.model.eval()
            
            # Compile model for better performance (PyTorch 2.0+)
            if hasattr(torch, 'compile') and torch.cuda.is_available():
                try:
                    self.model = torch.compile(self.model)
                    self.logger.info("Model compiled for better performance")
                except Exception as e:
                    self.logger.warning(f"Model compilation failed: {e}")
            
            # Optimize memory usage
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.info("GPU memory optimized")
            
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")

# Utility functions
def create_inference_request(image_data: bytes, user_id: str = None, 
                           mode: InferenceMode = InferenceMode.SINGLE) -> InferenceRequest:
    """Create inference request"""
    return InferenceRequest(
        request_id=f"req_{int(time.time() * 1000)}",
        image_data=image_data,
        model_version="1.0.0",
        mode=mode,
        timestamp=datetime.now(),
        user_id=user_id,
        metadata={}
    )

# Global model inference instance
model_inference = None

def get_model_inference() -> ModelInference:
    """Get global model inference instance"""
    global model_inference
    if not model_inference:
        model_inference = ModelInference()
    return model_inference
