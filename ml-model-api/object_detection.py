import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
import base64
import io
import json
from typing import List, Dict, Any, Tuple, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import albumentations as A
from ultralytics import YOLO
import torch.nn as nn
import torchvision.models as models
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

class ObjectDetector:
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.5, nms_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        self.colors = self._generate_colors(len(self.class_names))
        
    def _generate_colors(self, num_classes: int) -> List[Tuple[int, int, int]]:
        """Generate random colors for bounding boxes"""
        np.random.seed(42)
        colors = []
        for i in range(num_classes):
            color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
            colors.append(color)
        return colors
    
    async def load_model(self, model_type: str = "yolov5"):
        """Load object detection model"""
        try:
            if model_type == "yolov5":
                # In a real implementation, you would load the actual YOLOv5 model
                # For now, we'll simulate the model loading
                self.model = {
                    "type": "yolov5",
                    "input_size": (640, 640),
                    "num_classes": len(self.class_names),
                    "loaded": True
                }
                print(f"Loaded {model_type} model on {self.device}")
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
                
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for model input"""
        # Resize image
        image_resized = cv2.resize(image, (640, 640))
        
        # Convert to tensor
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).float() / 255.0
        image_tensor = image_tensor.unsqueeze(0)
        
        return image_tensor.to(self.device)
    
    async def detect_objects(self, image_data: str, max_detections: int = 100) -> List[Dict[str, Any]]:
        """Detect objects in image"""
        start_time = time.time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Preprocess
            input_tensor = self.preprocess_image(image_np)
            
            # Run detection (mock implementation)
            detections = await self._run_detection(input_tensor, image_np.shape[:2])
            
            # Post-process results
            processed_detections = self._post_process_detections(detections, image_np.shape[:2])
            
            # Limit number of detections
            processed_detections = processed_detections[:max_detections]
            
            processing_time = time.time() - start_time
            
            # Add processing time to each detection
            for detection in processed_detections:
                detection["processing_time"] = processing_time
            
            return processed_detections
            
        except Exception as e:
            print(f"Error in object detection: {e}")
            raise
    
    async def _run_detection(self, input_tensor: torch.Tensor, original_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        """Run detection model (mock implementation)"""
        # In a real implementation, this would run the actual model
        # For now, we'll generate mock detections
        
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Mock detections based on image content
        mock_detections = [
            {
                "bbox": [100, 100, 200, 200],
                "confidence": 0.85,
                "class_id": 0,  # person
                "class_name": "person"
            },
            {
                "bbox": [300, 150, 100, 150],
                "confidence": 0.72,
                "class_id": 39,  # bottle
                "class_name": "bottle"
            },
            {
                "bbox": [50, 200, 150, 100],
                "confidence": 0.68,
                "class_id": 46,  # banana
                "class_name": "banana"
            }
        ]
        
        # Filter by confidence threshold
        filtered_detections = [
            det for det in mock_detections 
            if det["confidence"] >= self.confidence_threshold
        ]
        
        return filtered_detections
    
    def _post_process_detections(self, detections: List[Dict[str, Any]], image_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        """Post-process detection results"""
        processed = []
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            
            # Ensure coordinates are within image bounds
            x1 = max(0, min(x1, image_shape[1]))
            y1 = max(0, min(y1, image_shape[0]))
            x2 = max(0, min(x2, image_shape[1]))
            y2 = max(0, min(y2, image_shape[0]))
            
            # Calculate area and center
            width = x2 - x1
            height = y2 - y1
            area = width * height
            center_x = x1 + width // 2
            center_y = y1 + height // 2
            
            processed.append({
                "bbox": [x1, y1, width, height],
                "confidence": det["confidence"],
                "class_id": det["class_id"],
                "class_name": det["class_name"],
                "area": area,
                "center": [center_x, center_y],
                "color": self.colors[det["class_id"]]
            })
        
        # Apply Non-Maximum Suppression
        processed = self._apply_nms(processed)
        
        return processed
    
    def _apply_nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply Non-Maximum Suppression to remove overlapping detections"""
        if not detections:
            return detections
        
        # Sort by confidence
        detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        keep = []
        while detections:
            # Keep the detection with highest confidence
            current = detections.pop(0)
            keep.append(current)
            
            # Remove overlapping detections
            remaining = []
            for det in detections:
                iou = self._calculate_iou(current["bbox"], det["bbox"])
                if iou < self.nms_threshold:
                    remaining.append(det)
            
            detections = remaining
        
        return keep
    
    def _calculate_iou(self, box1: List[int], box2: List[int]) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes"""
        x1_1, y1_1, w1, h1 = box1
        x2_1, y2_1, w2, h2 = box2
        
        x1_2 = x1_1 + w1
        y1_2 = y1_1 + h1
        x2_2 = x2_1 + w2
        y2_2 = y2_1 + h2
        
        # Calculate intersection
        x1_i = max(x1_1, x2_1)
        y1_i = max(y1_1, y2_1)
        x2_i = min(x1_2, x2_2)
        y2_i = min(y1_2, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def visualize_detections(self, image: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Visualize detections on image"""
        vis_image = image.copy()
        
        for det in detections:
            x, y, w, h = det["bbox"]
            color = det["color"]
            class_name = det["class_name"]
            confidence = det["confidence"]
            
            # Draw bounding box
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            # Draw label background
            cv2.rectangle(vis_image, (x, y - label_size[1] - 10), 
                         (x + label_size[0], y), color, -1)
            
            # Draw label text
            cv2.putText(vis_image, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return vis_image
    
    def get_detection_statistics(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about detections"""
        if not detections:
            return {
                "total_detections": 0,
                "classes_detected": [],
                "average_confidence": 0.0,
                "total_area": 0,
                "class_distribution": {}
            }
        
        # Count detections per class
        class_counts = {}
        total_confidence = 0
        total_area = 0
        
        for det in detections:
            class_name = det["class_name"]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            total_confidence += det["confidence"]
            total_area += det["area"]
        
        return {
            "total_detections": len(detections),
            "classes_detected": list(class_counts.keys()),
            "average_confidence": total_confidence / len(detections),
            "total_area": total_area,
            "class_distribution": class_counts
        }
    
    def filter_detections(self, detections: List[Dict[str, Any]], 
                         classes: Optional[List[str]] = None,
                         min_confidence: Optional[float] = None,
                         min_area: Optional[int] = None) -> List[Dict[str, Any]]:
        """Filter detections based on criteria"""
        filtered = detections.copy()
        
        if classes:
            filtered = [det for det in filtered if det["class_name"] in classes]
        
        if min_confidence:
            filtered = [det for det in filtered if det["confidence"] >= min_confidence]
        
        if min_area:
            filtered = [det for det in filtered if det["area"] >= min_area]
        
        return filtered
    
    async def batch_detect(self, image_data_list: List[str], max_detections: int = 100) -> List[List[Dict[str, Any]]]:
        """Detect objects in multiple images"""
        tasks = []
        for image_data in image_data_list:
            task = self.detect_objects(image_data, max_detections)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Error in batch detection: {result}")
                processed_results.append([])
            else:
                processed_results.append(result)
        
        return processed_results

class CustomObjectDetector(ObjectDetector):
    """Custom object detector with additional features"""
    
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.5, nms_threshold: float = 0.4):
        super().__init__(model_path, confidence_threshold, nms_threshold)
        self.custom_classes = []
        self.detection_history = []
    
    def add_custom_class(self, class_name: str, examples: List[str] = None):
        """Add custom class for detection"""
        if class_name not in self.class_names:
            self.class_names.append(class_name)
            self.custom_classes.append(class_name)
            print(f"Added custom class: {class_name}")
    
    def track_detections(self, detections: List[Dict[str, Any]], frame_id: int):
        """Track detections over time"""
        tracking_data = {
            "frame_id": frame_id,
            "timestamp": time.time(),
            "detections": detections,
            "statistics": self.get_detection_statistics(detections)
        }
        
        self.detection_history.append(tracking_data)
        
        # Keep only last 1000 frames
        if len(self.detection_history) > 1000:
            self.detection_history = self.detection_history[-1000:]
    
    def get_detection_trends(self, window_size: int = 100) -> Dict[str, Any]:
        """Analyze detection trends over time"""
        if len(self.detection_history) < window_size:
            recent_history = self.detection_history
        else:
            recent_history = self.detection_history[-window_size:]
        
        # Calculate trends
        class_trends = {}
        total_detections_trend = []
        
        for frame_data in recent_history:
            stats = frame_data["statistics"]
            total_detections_trend.append(stats["total_detections"])
            
            for class_name, count in stats["class_distribution"].items():
                if class_name not in class_trends:
                    class_trends[class_name] = []
                class_trends[class_name].append(count)
        
        # Calculate averages and trends
        trends = {
            "average_detections_per_frame": np.mean(total_detections_trend),
            "detection_trend": "increasing" if total_detections_trend[-1] > total_detections_trend[0] else "decreasing",
            "class_trends": {}
        }
        
        for class_name, counts in class_trends.items():
            trends["class_trends"][class_name] = {
                "average": np.mean(counts),
                "trend": "increasing" if counts[-1] > counts[0] else "decreasing",
                "peak": max(counts),
                "minimum": min(counts)
            }
        
        return trends

# Utility functions
def create_detector(model_type: str = "yolov5", confidence_threshold: float = 0.5) -> ObjectDetector:
    """Create and initialize object detector"""
    detector = ObjectDetector(confidence_threshold=confidence_threshold)
    
    # In a real implementation, you would load the actual model here
    # For now, we'll simulate it
    asyncio.create_task(detector.load_model(model_type))
    
    return detector

def create_custom_detector(confidence_threshold: float = 0.5) -> CustomObjectDetector:
    """Create and initialize custom object detector"""
    detector = CustomObjectDetector(confidence_threshold=confidence_threshold)
    
    # Add food-related custom classes
    food_classes = ["apple", "banana", "orange", "pizza", "burger", "pasta", "salad", "soup"]
    for food_class in food_classes:
        detector.add_custom_class(food_class)
    
    return detector
