"""
Advanced Computer Vision Handlers for FlavorSnap
Implements object detection, segmentation, and image analysis
"""

import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image, ImageDraw, ImageFont
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import asyncio
import aiofiles
import base64
from io import BytesIO

# Advanced CV imports
import albumentations as A
from albumentations.pytorch import ToTensorV2
import segmentation_models_pytorch as smp
import face_recognition
import mediapipe as mp
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class CVTaskType(Enum):
    """Computer vision task types"""
    OBJECT_DETECTION = "object_detection"
    IMAGE_SEGMENTATION = "image_segmentation"
    FEATURE_EXTRACTION = "feature_extraction"
    IMAGE_QUALITY = "image_quality"
    FACE_DETECTION = "face_detection"
    SCENE_UNDERSTANDING = "scene_understanding"

class DetectionModel(Enum):
    """Available detection models"""
    YOLOV8 = "yolov8"
    FASTER_RCNN = "faster_rcnn"
    SSD = "ssd"
    DETR = "detr"

class SegmentationModel(Enum):
    """Available segmentation models"""
    UNET = "unet"
    DEEPLABV3 = "deeplabv3"
    PSPNET = "pspnet"
    MASK_RCNN = "mask_rcnn"

@dataclass
class DetectionResult:
    """Object detection result"""
    class_name: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    area: int
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class SegmentationResult:
    """Image segmentation result"""
    mask: np.ndarray
    class_name: str
    confidence: float
    area: int
    centroid: Tuple[int, int]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class FeatureVector:
    """Feature vector for similarity analysis"""
    features: np.ndarray
    feature_type: str
    extraction_method: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class AdvancedImageProcessor:
    """Advanced image processing with multiple CV capabilities"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models
        self.detection_models = {}
        self.segmentation_models = {}
        self.feature_extractors = {}
        
        # MediaPipe for face detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_hands = mp.solutions.hands
        self.mp_objectron = mp.solutions.objectron
        
        # Image transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Augmentation pipeline
        self.augmentation = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(p=0.2),
            A.Rotate(limit=10, p=0.3),
            A.GaussianBlur(blur_limit=3, p=0.1),
            A.Normalize(mean=[0.485, 0.456, 0.406], 
                       std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
        
        self.logger = logging.getLogger('AdvancedImageProcessor')
        
        # Load models
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models"""
        try:
            # Load YOLOv8 for object detection
            from ultralytics import YOLO
            self.detection_models[DetectionModel.YOLOV8] = YOLO('yolov8n.pt')
            
            # Load segmentation models
            self.segmentation_models[SegmentationModel.UNET] = smp.Unet(
                encoder_name='resnet34', 
                encoder_weights='imagenet',
                in_channels=3, 
                classes=21
            ).to(self.device)
            
            # Load feature extractor (ResNet50)
            import torchvision.models as models
            self.feature_extractors['resnet50'] = models.resnet50(pretrained=True).to(self.device)
            self.feature_extractors['resnet50'].eval()
            
            self.logger.info("Models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
    
    async def detect_objects(self, image: np.ndarray, 
                           model: DetectionModel = DetectionModel.YOLOV8,
                           confidence_threshold: float = 0.5) -> List[DetectionResult]:
        """Detect objects in image using specified model"""
        
        try:
            if model not in self.detection_models:
                raise ValueError(f"Model {model} not available")
            
            detection_model = self.detection_models[model]
            
            # Run inference
            results = detection_model(image)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        confidence = box.conf.item()
                        if confidence >= confidence_threshold:
                            class_id = int(box.cls.item())
                            class_name = detection_model.names[class_id]
                            
                            # Get bbox coordinates
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            area = (x2 - x1) * (y2 - y1)
                            
                            detection = DetectionResult(
                                class_name=class_name,
                                confidence=confidence,
                                bbox=[x1, y1, x2, y2],
                                area=area
                            )
                            detections.append(detection)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Object detection failed: {e}")
            return []
    
    async def segment_image(self, image: np.ndarray,
                          model: SegmentationModel = SegmentationModel.UNET,
                          target_classes: List[str] = None) -> List[SegmentationResult]:
        """Perform image segmentation"""
        
        try:
            if model not in self.segmentation_models:
                raise ValueError(f"Model {model} not available")
            
            seg_model = self.segmentation_models[model]
            
            # Preprocess image
            input_tensor = self.transform(Image.fromarray(image)).unsqueeze(0).to(self.device)
            
            # Run inference
            with torch.no_grad():
                output = seg_model(input_tensor)
            
            # Post-process results
            if isinstance(output, dict):  # DeepLabV3 output
                output = output['out']
            
            # Get segmentation mask
            masks = output.squeeze(0).cpu().numpy()
            predicted_masks = np.argmax(masks, axis=0)
            
            # Process each class
            segmentations = []
            unique_classes = np.unique(predicted_masks)
            
            for class_id in unique_classes:
                if class_id == 0:  # Skip background
                    continue
                
                mask = (predicted_masks == class_id).astype(np.uint8)
                area = np.sum(mask)
                
                if area < 100:  # Skip small segments
                    continue
                
                # Calculate centroid
                moments = cv2.moments(mask)
                if moments['m00'] != 0:
                    cx = int(moments['m10'] / moments['m00'])
                    cy = int(moments['m01'] / moments['m00'])
                    centroid = (cx, cy)
                else:
                    centroid = (0, 0)
                
                # Calculate confidence (average probability)
                class_mask = masks[class_id]
                confidence = np.mean(class_mask[mask == 1])
                
                segmentation = SegmentationResult(
                    mask=mask,
                    class_name=f"class_{class_id}",
                    confidence=confidence,
                    area=area,
                    centroid=centroid
                )
                segmentations.append(segmentation)
            
            return segmentations
            
        except Exception as e:
            self.logger.error(f"Image segmentation failed: {e}")
            return []
    
    async def extract_features(self, image: np.ndarray,
                              method: str = "resnet50") -> FeatureVector:
        """Extract feature vectors from image"""
        
        try:
            if method not in self.feature_extractors:
                raise ValueError(f"Feature extraction method {method} not available")
            
            model = self.feature_extractors[method]
            
            # Preprocess image
            input_tensor = self.transform(Image.fromarray(image)).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                # Remove classification layer for feature extraction
                features = model(input_tensor)
                if hasattr(model, 'fc'):
                    features = model.fc(features)
                elif hasattr(model, 'classifier'):
                    features = model.classifier(features)
            
            # Convert to numpy
            feature_vector = features.squeeze(0).cpu().numpy()
            
            return FeatureVector(
                features=feature_vector,
                feature_type="global",
                extraction_method=method
            )
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return None
    
    async def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in image"""
        
        try:
            with self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5) as face_detection:
                
                # Convert image to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_image)
                
                faces = []
                if results.detections:
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        h, w, _ = image.shape
                        
                        # Convert relative coordinates to absolute
                        x1 = int(bbox.xmin * w)
                        y1 = int(bbox.ymin * h)
                        x2 = int((bbox.xmin + bbox.width) * w)
                        y2 = int((bbox.ymin + bbox.height) * h)
                        
                        face_info = {
                            'bbox': [x1, y1, x2, y2],
                            'confidence': detection.score[0],
                            'landmarks': self._extract_face_landmarks(rgb_image, detection)
                        }
                        faces.append(face_info)
                
                return faces
                
        except Exception as e:
            self.logger.error(f"Face detection failed: {e}")
            return []
    
    def _extract_face_landmarks(self, image: np.ndarray, detection) -> List[Tuple[int, int]]:
        """Extract facial landmarks"""
        try:
            with self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True) as face_mesh:
                
                results = face_mesh.process(image)
                if results.multi_face_landmarks:
                    landmarks = []
                    for landmark in results.multi_face_landmarks[0].landmark:
                        h, w, _ = image.shape
                        x = int(landmark.x * w)
                        y = int(landmark.y * h)
                        landmarks.append((x, y))
                    return landmarks
                
        except Exception as e:
            self.logger.error(f"Landmark extraction failed: {e}")
        
        return []
    
    async def analyze_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """Analyze image quality metrics"""
        
        try:
            quality_metrics = {}
            
            # Calculate sharpness (Laplacian variance)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            quality_metrics['sharpness'] = float(sharpness)
            
            # Calculate brightness
            brightness = np.mean(gray)
            quality_metrics['brightness'] = float(brightness)
            
            # Calculate contrast
            contrast = np.std(gray)
            quality_metrics['contrast'] = float(contrast)
            
            # Calculate noise (using median filter)
            filtered = cv2.medianBlur(gray, 3)
            noise = np.mean(np.abs(gray.astype(float) - filtered.astype(float)))
            quality_metrics['noise'] = float(noise)
            
            # Calculate saturation
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1])
            quality_metrics['saturation'] = float(saturation)
            
            # Overall quality score (normalized)
            quality_score = min(1.0, (sharpness / 1000) * (contrast / 127) * (1 - noise / 50))
            quality_metrics['overall_quality'] = float(quality_score)
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"Image quality analysis failed: {e}")
            return {}
    
    async def understand_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """Perform scene understanding analysis"""
        
        try:
            scene_info = {}
            
            # Object detection for scene context
            detections = await self.detect_objects(image)
            scene_info['objects'] = [
                {
                    'class': det.class_name,
                    'confidence': det.confidence,
                    'area': det.area
                }
                for det in detections
            ]
            
            # Face detection for human presence
            faces = await self.detect_faces(image)
            scene_info['face_count'] = len(faces)
            scene_info['has_people'] = len(faces) > 0
            
            # Image quality assessment
            quality = await self.analyze_image_quality(image)
            scene_info['image_quality'] = quality
            
            # Color analysis
            scene_info['color_analysis'] = self._analyze_colors(image)
            
            # Scene classification (simplified)
            scene_info['scene_type'] = self._classify_scene(detections, faces)
            
            return scene_info
            
        except Exception as e:
            self.logger.error(f"Scene understanding failed: {e}")
            return {}
    
    def _analyze_colors(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution"""
        
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Calculate color histograms
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Find dominant colors using K-means
            pixels = image.reshape(-1, 3)
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            dominant_colors = kmeans.cluster_centers_.astype(int)
            
            return {
                'dominant_colors': dominant_colors.tolist(),
                'hue_distribution': hist_h.flatten().tolist(),
                'saturation_distribution': hist_s.flatten().tolist(),
                'value_distribution': hist_v.flatten().tolist()
            }
            
        except Exception as e:
            self.logger.error(f"Color analysis failed: {e}")
            return {}
    
    def _classify_scene(self, detections: List[DetectionResult], faces: List[Dict]) -> str:
        """Classify scene type based on detections"""
        
        try:
            # Count different object types
            object_counts = {}
            for det in detections:
                object_counts[det.class_name] = object_counts.get(det.class_name, 0) + 1
            
            # Simple scene classification rules
            if len(faces) > 0:
                if 'person' in object_counts and object_counts['person'] > 1:
                    return 'group_photo'
                else:
                    return 'portrait'
            
            if 'food' in object_counts or any('fruit' in obj or 'vegetable' in obj for obj in object_counts):
                return 'food_scene'
            
            if 'car' in object_counts or 'truck' in object_counts:
                return 'street_scene'
            
            if 'chair' in object_counts or 'table' in object_counts:
                return 'indoor_scene'
            
            if 'tree' in object_counts or 'plant' in object_counts:
                return 'nature_scene'
            
            return 'general_scene'
            
        except Exception as e:
            self.logger.error(f"Scene classification failed: {e}")
            return 'unknown'
    
    async def enhance_image(self, image: np.ndarray, 
                          enhancement_type: str = "auto") -> np.ndarray:
        """Enhance image quality"""
        
        try:
            if enhancement_type == "auto":
                # Auto enhancement based on quality metrics
                quality = await self.analyze_image_quality(image)
                
                enhanced = image.copy()
                
                # Adjust brightness if needed
                if quality.get('brightness', 128) < 100:
                    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.2, beta=20)
                elif quality.get('brightness', 128) > 150:
                    enhanced = cv2.convertScaleAbs(enhanced, alpha=0.9, beta=-10)
                
                # Adjust contrast if needed
                if quality.get('contrast', 50) < 30:
                    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.3, beta=0)
                
                # Apply denoising if noisy
                if quality.get('noise', 0) > 20:
                    enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
                
                return enhanced
            
            elif enhancement_type == "sharpen":
                # Apply sharpening filter
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                return cv2.filter2D(image, -1, kernel)
            
            elif enhancement_type == "denoise":
                # Apply denoising
                return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            
            elif enhancement_type == "histogram_equalization":
                # Apply histogram equalization
                yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
                yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
                return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
            
            else:
                return image
                
        except Exception as e:
            self.logger.error(f"Image enhancement failed: {e}")
            return image
    
    def visualize_detections(self, image: np.ndarray, 
                           detections: List[DetectionResult]) -> np.ndarray:
        """Visualize detection results on image"""
        
        try:
            vis_image = image.copy()
            
            for det in detections:
                x1, y1, x2, y2 = det.bbox
                
                # Draw bounding box
                cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"{det.class_name}: {det.confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(vis_image, (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0], y1), (0, 255, 0), -1)
                cv2.putText(vis_image, label, (x1, y1 - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            return vis_image
            
        except Exception as e:
            self.logger.error(f"Detection visualization failed: {e}")
            return image
    
    def visualize_segmentation(self, image: np.ndarray, 
                             segmentations: List[SegmentationResult]) -> np.ndarray:
        """Visualize segmentation results on image"""
        
        try:
            vis_image = image.copy()
            
            # Create overlay
            overlay = np.zeros_like(image)
            
            colors = [
                (255, 0, 0), (0, 255, 0), (0, 0, 255),
                (255, 255, 0), (255, 0, 255), (0, 255, 255)
            ]
            
            for i, seg in enumerate(segmentations):
                color = colors[i % len(colors)]
                mask = seg.mask
                
                # Apply color to mask
                overlay[mask == 1] = color
                
                # Draw centroid
                cv2.circle(overlay, seg.centroid, 5, color, -1)
            
            # Blend overlay with original image
            alpha = 0.5
            vis_image = cv2.addWeighted(vis_image, 1 - alpha, overlay, alpha, 0)
            
            return vis_image
            
        except Exception as e:
            self.logger.error(f"Segmentation visualization failed: {e}")
            return image
    
    async def batch_process_images(self, image_paths: List[str],
                                tasks: List[CVTaskType]) -> List[Dict[str, Any]]:
        """Batch process multiple images with multiple tasks"""
        
        results = []
        
        for image_path in image_paths:
            try:
                # Load image
                image = cv2.imread(image_path)
                if image is None:
                    results.append({"error": f"Failed to load image: {image_path}"})
                    continue
                
                image_results = {"image_path": image_path}
                
                # Process each task
                for task in tasks:
                    if task == CVTaskType.OBJECT_DETECTION:
                        detections = await self.detect_objects(image)
                        image_results["detections"] = [
                            {
                                "class": det.class_name,
                                "confidence": det.confidence,
                                "bbox": det.bbox,
                                "area": det.area
                            }
                            for det in detections
                        ]
                    
                    elif task == CVTaskType.IMAGE_SEGMENTATION:
                        segmentations = await self.segment_image(image)
                        image_results["segmentations"] = [
                            {
                                "class_name": seg.class_name,
                                "confidence": seg.confidence,
                                "area": seg.area,
                                "centroid": seg.centroid
                            }
                            for seg in segmentations
                        ]
                    
                    elif task == CVTaskType.FEATURE_EXTRACTION:
                        features = await self.extract_features(image)
                        if features:
                            image_results["features"] = features.features.tolist()
                    
                    elif task == CVTaskType.IMAGE_QUALITY:
                        quality = await self.analyze_image_quality(image)
                        image_results["quality"] = quality
                    
                    elif task == CVTaskType.FACE_DETECTION:
                        faces = await self.detect_faces(image)
                        image_results["faces"] = faces
                    
                    elif task == CVTaskType.SCENE_UNDERSTANDING:
                        scene = await self.understand_scene(image)
                        image_results["scene"] = scene
                
                results.append(image_results)
                
            except Exception as e:
                self.logger.error(f"Failed to process image {image_path}: {e}")
                results.append({"error": str(e), "image_path": image_path})
        
        return results

# Global image processor instance
image_processor = None

def get_image_processor() -> AdvancedImageProcessor:
    """Get or create global image processor instance"""
    global image_processor
    if image_processor is None:
        image_processor = AdvancedImageProcessor()
    return image_processor
