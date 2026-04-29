"""
Advanced Image Segmentation for FlavorSnap
Implements semantic, instance, and panoptic segmentation
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
import albumentations as A
from albumentations.pytorch import ToTensorV2
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from sklearn.cluster import KMeans
import colorsys

logger = logging.getLogger(__name__)

class SegmentationType(Enum):
    """Types of segmentation"""
    SEMANTIC = "semantic"
    INSTANCE = "instance"
    PANOPTIC = "panoptic"

class SegmentationModel(Enum):
    """Available segmentation models"""
    UNET = "unet"
    DEEPLABV3 = "deeplabv3"
    PSPNET = "pspnet"
    MASK_RCNN = "mask_rcnn"
    UPPERNET = "uppernet"

@dataclass
class SegmentationResult:
    """Segmentation result with metadata"""
    mask: np.ndarray
    class_id: int
    class_name: str
    confidence: float
    area: int
    bbox: List[int]
    centroid: Tuple[int, int]
    segmentation_type: SegmentationType
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class SegmentationMetrics:
    """Segmentation quality metrics"""
    pixel_accuracy: float
    mean_iou: float
    dice_coefficient: float
    boundary_f1: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class AdvancedSegmentationProcessor:
    """Advanced image segmentation processor"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models
        self.semantic_models = {}
        self.instance_models = {}
        
        # Color palette for visualization
        self.color_palette = self._generate_color_palette(21)
        
        # Transforms
        self.transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Augmentation for training
        self.augmentation = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(p=0.2),
            A.Rotate(limit=15, p=0.3),
            A.GaussianBlur(blur_limit=3, p=0.1),
            A.ElasticTransform(p=0.1),
            A.GridDistortion(p=0.1),
            A.Normalize(mean=[0.485, 0.456, 0.406], 
                       std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
        
        # Class names for food segmentation
        self.food_classes = [
            'background', 'apple', 'banana', 'orange', 'grape', 'strawberry',
            'pizza', 'burger', 'pasta', 'bread', 'rice', 'chicken', 'beef',
            'fish', 'vegetable', 'fruit', 'dairy', 'grain', 'legume', 'other'
        ]
        
        self.logger = logging.getLogger('AdvancedSegmentationProcessor')
        
        # Load models
        self._load_models()
    
    def _load_models(self):
        """Load segmentation models"""
        try:
            # Load semantic segmentation models
            self.semantic_models[SegmentationModel.UNET] = smp.Unet(
                encoder_name='resnet34',
                encoder_weights='imagenet',
                in_channels=3,
                classes=len(self.food_classes)
            ).to(self.device)
            
            self.semantic_models[SegmentationModel.DEEPLABV3] = smp.DeepLabV3(
                encoder_name='resnet101',
                encoder_weights='imagenet',
                in_channels=3,
                classes=len(self.food_classes)
            ).to(self.device)
            
            self.semantic_models[SegmentationModel.PSPNET] = smp.PSPNet(
                encoder_name='resnet101',
                encoder_weights='imagenet',
                in_channels=3,
                classes=len(self.food_classes)
            ).to(self.device)
            
            self.logger.info("Segmentation models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
    
    def _generate_color_palette(self, num_classes: int) -> List[Tuple[int, int, int]]:
        """Generate distinct colors for each class"""
        colors = []
        for i in range(num_classes):
            hue = i / num_classes
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.8)
            colors.append(tuple(int(c * 255) for c in rgb))
        return colors
    
    async def semantic_segmentation(self, image: np.ndarray,
                                  model: SegmentationModel = SegmentationModel.UNET) -> List[SegmentationResult]:
        """Perform semantic segmentation"""
        
        try:
            if model not in self.semantic_models:
                raise ValueError(f"Model {model} not available for semantic segmentation")
            
            seg_model = self.semantic_models[model]
            
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
                
                # Find bounding box
                coords = np.column_stack(np.where(mask))
                if len(coords) == 0:
                    continue
                
                y_min, x_min = coords.min(axis=0)
                y_max, x_max = coords.max(axis=0)
                bbox = [x_min, y_min, x_max, y_max]
                
                # Calculate centroid
                moments = cv2.moments(mask)
                if moments['m00'] != 0:
                    cx = int(moments['m10'] / moments['m00'])
                    cy = int(moments['m01'] / moments['m00'])
                    centroid = (cx, cy)
                else:
                    centroid = (bbox[0] + (bbox[2] - bbox[0]) // 2,
                              bbox[1] + (bbox[3] - bbox[1]) // 2)
                
                # Calculate confidence
                class_mask = masks[class_id]
                confidence = np.mean(class_mask[mask == 1])
                
                segmentation = SegmentationResult(
                    mask=mask,
                    class_id=class_id,
                    class_name=self.food_classes[class_id] if class_id < len(self.food_classes) else f"class_{class_id}",
                    confidence=confidence,
                    area=area,
                    bbox=bbox,
                    centroid=centroid,
                    segmentation_type=SegmentationType.SEMANTIC
                )
                segmentations.append(segmentation)
            
            return segmentations
            
        except Exception as e:
            self.logger.error(f"Semantic segmentation failed: {e}")
            return []
    
    async def instance_segmentation(self, image: np.ndarray) -> List[SegmentationResult]:
        """Perform instance segmentation"""
        
        try:
            # For instance segmentation, we'll use a simplified approach
            # In production, you would use Mask R-CNN or similar
            
            # First, get semantic segmentation
            semantic_results = await self.semantic_segmentation(image)
            
            # Then, separate instances within each semantic class
            instance_results = []
            
            for semantic_result in semantic_results:
                mask = semantic_result.mask
                
                # Find connected components (instances)
                num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                    mask, connectivity=8
                )
                
                # Skip background (label 0)
                for label in range(1, num_labels):
                    instance_mask = (labels == label).astype(np.uint8)
                    area = stats[label, cv2.CC_STAT_AREA]
                    
                    if area < 50:  # Skip small instances
                        continue
                    
                    # Get bounding box
                    x = stats[label, cv2.CC_STAT_LEFT]
                    y = stats[label, cv2.CC_STAT_TOP]
                    w = stats[label, cv2.CC_STAT_WIDTH]
                    h = stats[label, cv2.CC_STAT_HEIGHT]
                    bbox = [x, y, x + w, y + h]
                    
                    centroid = (int(centroids[label][0]), int(centroids[label][1]))
                    
                    instance_segmentation = SegmentationResult(
                        mask=instance_mask,
                        class_id=semantic_result.class_id,
                        class_name=semantic_result.class_name,
                        confidence=semantic_result.confidence,
                        area=area,
                        bbox=bbox,
                        centroid=centroid,
                        segmentation_type=SegmentationType.INSTANCE
                    )
                    instance_results.append(instance_segmentation)
            
            return instance_results
            
        except Exception as e:
            self.logger.error(f"Instance segmentation failed: {e}")
            return []
    
    async def panoptic_segmentation(self, image: np.ndarray) -> List[SegmentationResult]:
        """Perform panoptic segmentation (semantic + instance)"""
        
        try:
            # Get both semantic and instance segmentations
            semantic_results = await self.semantic_segmentation(image)
            instance_results = await self.instance_segmentation(image)
            
            # Combine results
            panoptic_results = []
            
            # Add semantic results for stuff classes (background, walls, etc.)
            for result in semantic_results:
                if result.class_name in ['background', 'other']:
                    result.segmentation_type = SegmentationType.PANOPTIC
                    panoptic_results.append(result)
            
            # Add instance results for thing classes (objects)
            for result in instance_results:
                result.segmentation_type = SegmentationType.PANOPTIC
                panoptic_results.append(result)
            
            return panoptic_results
            
        except Exception as e:
            self.logger.error(f"Panoptic segmentation failed: {e}")
            return []
    
    async def segment_food_items(self, image: np.ndarray) -> Dict[str, Any]:
        """Specialized food item segmentation"""
        
        try:
            # Use semantic segmentation with food classes
            segmentations = await self.semantic_segmentation(image)
            
            # Filter for food items only
            food_items = []
            total_food_area = 0
            
            for seg in segmentations:
                if seg.class_name in self.food_classes[1:]:  # Skip background
                    food_items.append({
                        'name': seg.class_name,
                        'confidence': seg.confidence,
                        'area': seg.area,
                        'bbox': seg.bbox,
                        'centroid': seg.centroid,
                        'percentage': (seg.area / (image.shape[0] * image.shape[1])) * 100
                    })
                    total_food_area += seg.area
            
            # Calculate food composition
            food_composition = {}
            for item in food_items:
                food_composition[item['name']] = food_composition.get(item['name'], 0) + item['area']
            
            # Convert to percentages
            if total_food_area > 0:
                for food_type in food_composition:
                    food_composition[food_type] = (food_composition[food_type] / total_food_area) * 100
            
            return {
                'food_items': food_items,
                'food_composition': food_composition,
                'total_food_area': total_food_area,
                'image_area': image.shape[0] * image.shape[1],
                'food_coverage_percentage': (total_food_area / (image.shape[0] * image.shape[1])) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Food segmentation failed: {e}")
            return {}
    
    def calculate_segmentation_metrics(self, predicted_mask: np.ndarray,
                                     ground_truth_mask: np.ndarray) -> SegmentationMetrics:
        """Calculate segmentation quality metrics"""
        
        try:
            # Pixel accuracy
            pixel_accuracy = np.mean(predicted_mask == ground_truth_mask)
            
            # Mean Intersection over Union (mIoU)
            intersection = np.logical_and(predicted_mask, ground_truth_mask)
            union = np.logical_or(predicted_mask, ground_truth_mask)
            iou_score = np.sum(intersection) / np.sum(union) if np.sum(union) > 0 else 0
            
            # Dice coefficient
            dice = (2 * np.sum(intersection)) / (np.sum(predicted_mask) + np.sum(ground_truth_mask))
            
            # Boundary F1 score (simplified)
            pred_boundary = cv2.Canny(predicted_mask.astype(np.uint8) * 255, 100, 200)
            gt_boundary = cv2.Canny(ground_truth_mask.astype(np.uint8) * 255, 100, 200)
            
            boundary_intersection = np.logical_and(pred_boundary, gt_boundary)
            boundary_union = np.logical_or(pred_boundary, gt_boundary)
            
            if np.sum(boundary_union) > 0:
                boundary_f1 = 2 * np.sum(boundary_intersection) / np.sum(boundary_union)
            else:
                boundary_f1 = 1.0  # Perfect score if no boundaries
            
            return SegmentationMetrics(
                pixel_accuracy=float(pixel_accuracy),
                mean_iou=float(iou_score),
                dice_coefficient=float(dice),
                boundary_f1=float(boundary_f1)
            )
            
        except Exception as e:
            self.logger.error(f"Metrics calculation failed: {e}")
            return SegmentationMetrics(0, 0, 0, 0)
    
    def visualize_segmentation(self, image: np.ndarray,
                              segmentations: List[SegmentationResult],
                              show_confidence: bool = True,
                              show_labels: bool = True) -> np.ndarray:
        """Visualize segmentation results"""
        
        try:
            vis_image = image.copy()
            
            # Create overlay
            overlay = np.zeros_like(image)
            
            for i, seg in enumerate(segmentations):
                color = self.color_palette[seg.class_id % len(self.color_palette)]
                mask = seg.mask
                
                # Apply color to mask
                overlay[mask == 1] = color
                
                # Draw bounding box
                x1, y1, x2, y2 = seg.bbox
                cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
                
                # Draw centroid
                cv2.circle(vis_image, seg.centroid, 5, color, -1)
                
                # Draw label
                if show_labels:
                    label = f"{seg.class_name}"
                    if show_confidence:
                        label += f": {seg.confidence:.2f}"
                    
                    # Draw label background
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(vis_image, (x1, y1 - label_size[1] - 10),
                                 (x1 + label_size[0], y1), color, -1)
                    
                    # Draw label text
                    cv2.putText(vis_image, label, (x1, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Blend overlay with original image
            alpha = 0.5
            vis_image = cv2.addWeighted(vis_image, 1 - alpha, overlay, alpha, 0)
            
            return vis_image
            
        except Exception as e:
            self.logger.error(f"Visualization failed: {e}")
            return image
    
    def create_segmentation_map(self, image: np.ndarray,
                             segmentations: List[SegmentationResult]) -> np.ndarray:
        """Create a segmentation map image"""
        
        try:
            # Create blank segmentation map
            seg_map = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
            
            for seg in segmentations:
                color = self.color_palette[seg.class_id % len(self.color_palette)]
                mask = seg.mask
                seg_map[mask == 1] = color
            
            return seg_map
            
        except Exception as e:
            self.logger.error(f"Segmentation map creation failed: {e}")
            return np.zeros_like(image)
    
    async def batch_segment_images(self, images: List[np.ndarray],
                                 segmentation_type: SegmentationType = SegmentationType.SEMANTIC) -> List[List[SegmentationResult]]:
        """Batch segment multiple images"""
        
        results = []
        
        for image in images:
            try:
                if segmentation_type == SegmentationType.SEMANTIC:
                    segmentations = await self.semantic_segmentation(image)
                elif segmentation_type == SegmentationType.INSTANCE:
                    segmentations = await self.instance_segmentation(image)
                elif segmentation_type == SegmentationType.PANOPTIC:
                    segmentations = await self.panoptic_segmentation(image)
                else:
                    segmentations = []
                
                results.append(segmentations)
                
            except Exception as e:
                self.logger.error(f"Batch segmentation failed: {e}")
                results.append([])
        
        return results
    
    def analyze_segmentation_statistics(self, segmentations: List[SegmentationResult]) -> Dict[str, Any]:
        """Analyze segmentation statistics"""
        
        try:
            if not segmentations:
                return {
                    'total_segments': 0,
                    'average_area': 0,
                    'largest_segment': None,
                    'class_distribution': {},
                    'area_distribution': []
                }
            
            # Calculate statistics
            areas = [seg.area for seg in segmentations]
            total_segments = len(segmentations)
            average_area = np.mean(areas)
            largest_segment_idx = np.argmax(areas)
            
            # Class distribution
            class_distribution = {}
            for seg in segmentations:
                class_distribution[seg.class_name] = class_distribution.get(seg.class_name, 0) + 1
            
            # Area distribution
            area_bins = [0, 100, 500, 1000, 5000, 10000, float('inf')]
            area_labels = ['<100', '100-500', '500-1K', '1K-5K', '5K-10K', '>10K']
            area_distribution = [0] * len(area_bins)
            
            for area in areas:
                for i, (min_area, max_area) in enumerate(zip(area_bins[:-1], area_bins[1:])):
                    if min_area <= area < max_area:
                        area_distribution[i] += 1
                        break
            
            return {
                'total_segments': total_segments,
                'average_area': float(average_area),
                'largest_segment': {
                    'class_name': segmentations[largest_segment_idx].class_name,
                    'area': areas[largest_segment_idx],
                    'confidence': segmentations[largest_segment_idx].confidence
                },
                'class_distribution': class_distribution,
                'area_distribution': dict(zip(area_labels, area_distribution)),
                'total_area_covered': sum(areas)
            }
            
        except Exception as e:
            self.logger.error(f"Statistics analysis failed: {e}")
            return {}
    
    def export_segmentation_data(self, segmentations: List[SegmentationResult],
                               format: str = "json") -> str:
        """Export segmentation data"""
        
        try:
            export_data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'segmentations': []
            }
            
            for seg in segmentations:
                seg_data = {
                    'class_id': seg.class_id,
                    'class_name': seg.class_name,
                    'confidence': seg.confidence,
                    'area': seg.area,
                    'bbox': seg.bbox,
                    'centroid': list(seg.centroid),
                    'segmentation_type': seg.segmentation_type.value,
                    'timestamp': seg.timestamp.isoformat()
                }
                export_data['segmentations'].append(seg_data)
            
            if format == "json":
                return json.dumps(export_data, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return ""

# Global segmentation processor instance
segmentation_processor = None

def get_segmentation_processor() -> AdvancedSegmentationProcessor:
    """Get or create global segmentation processor instance"""
    global segmentation_processor
    if segmentation_processor is None:
        segmentation_processor = AdvancedSegmentationProcessor()
    return segmentation_processor
