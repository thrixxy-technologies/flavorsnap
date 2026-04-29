import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import base64
import io
import json
from typing import List, Dict, Any, Tuple, Optional, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from scipy import ndimage
from skimage import feature, measure, filters
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
import torch
import torchvision.transforms as transforms
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd
from pathlib import Path
import hashlib

class ImageAnalyzer:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    async def analyze_image(self, image_data: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Perform comprehensive image analysis"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            
            results = {
                "image_info": self._get_image_info(image, image_np),
                "timestamp": time.time(),
                "analysis_type": analysis_type
            }
            
            if analysis_type in ["comprehensive", "quality"]:
                results["quality"] = await self._analyze_quality(image_np)
            
            if analysis_type in ["comprehensive", "composition"]:
                results["composition"] = await self._analyze_composition(image_np)
            
            if analysis_type in ["comprehensive", "color"]:
                results["color"] = await self._analyze_colors(image_np)
            
            if analysis_type in ["comprehensive", "texture"]:
                results["texture"] = await self._analyze_texture(image_np)
            
            if analysis_type in ["comprehensive", "objects"]:
                results["objects"] = await self._detect_objects(image_np)
            
            return results
            
        except Exception as e:
            print(f"Error in image analysis: {e}")
            raise

# Advanced Image Analysis Features

class AnalysisType(Enum):
    """Types of image analysis"""
    QUALITY = "quality"
    COMPOSITION = "composition"
    COLOR = "color"
    TEXTURE = "texture"
    OBJECTS = "objects"
    SCENE = "scene"
    NUTRITIONAL = "nutritional"
    AESTHETIC = "aesthetic"

@dataclass
class ImageQualityMetrics:
    """Image quality assessment metrics"""
    sharpness: float
    brightness: float
    contrast: float
    saturation: float
    noise_level: float
    overall_quality: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class CompositionMetrics:
    """Image composition analysis metrics"""
    rule_of_thirds_score: float
    symmetry_score: float
    balance_score: float
    leading_lines: List[Tuple[Tuple[int, int], Tuple[int, int]]]
    focal_point: Tuple[int, int]
    depth_of_field_score: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class AdvancedImageAnalyzer:
    """Advanced image analyzer with comprehensive analysis capabilities"""
    
    def __init__(self, cache_dir: str = "image_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger('AdvancedImageAnalyzer')
        
        # Analysis thresholds
        self.quality_thresholds = {
            'sharpness': 100,
            'brightness': [50, 200],
            'contrast': 30,
            'noise': 25
        }
        
        # Load pre-trained models for advanced analysis
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models for image analysis"""
        try:
            # Load aesthetic assessment model (simplified)
            import torchvision.models as models
            self.aesthetic_model = models.resnet50(pretrained=True)
            self.aesthetic_model.fc = torch.nn.Linear(2048, 1)  # Regression for aesthetic score
            self.aesthetic_model.to(self.device)
            self.aesthetic_model.eval()
            
            # Load food classification model
            self.food_classifier = models.resnet50(pretrained=True)
            self.food_classifier.fc = torch.nn.Linear(2048, 10)  # 10 food categories
            self.food_classifier.to(self.device)
            self.food_classifier.eval()
            
            self.logger.info("Analysis models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
    
    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate hash for image caching"""
        return hashlib.md5(image.tobytes()).hexdigest()
    
    async def comprehensive_analysis(self, image: np.ndarray) -> Dict[str, Any]:
        """Perform comprehensive image analysis"""
        
        try:
            # Check cache first
            image_hash = self._get_image_hash(image)
            cache_file = self.cache_dir / f"{image_hash}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_result = json.load(f)
                    # Check if cache is recent (within 1 hour)
                    cache_time = datetime.fromisoformat(cached_result['timestamp'])
                    if (datetime.utcnow() - cache_time).total_seconds() < 3600:
                        return cached_result
            
            # Perform all analyses
            analysis_results = {
                'image_hash': image_hash,
                'timestamp': datetime.utcnow().isoformat(),
                'image_info': self._get_basic_info(image)
            }
            
            # Quality assessment
            analysis_results['quality'] = await self._assess_quality(image)
            
            # Composition analysis
            analysis_results['composition'] = await self._analyze_composition(image)
            
            # Color analysis
            analysis_results['color'] = await self._analyze_colors(image)
            
            # Texture analysis
            analysis_results['texture'] = await self._analyze_texture(image)
            
            # Scene understanding
            analysis_results['scene'] = await self._understand_scene(image)
            
            # Nutritional analysis (for food images)
            analysis_results['nutritional'] = await self._analyze_nutritional_content(image)
            
            # Aesthetic assessment
            analysis_results['aesthetic'] = await self._assess_aesthetic_quality(image)
            
            # Cache results
            with open(cache_file, 'w') as f:
                json.dump(analysis_results, f, indent=2)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Comprehensive analysis failed: {e}")
            return {}
    
    def _get_basic_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Get basic image information"""
        height, width, channels = image.shape
        
        return {
            'dimensions': {'width': width, 'height': height, 'channels': channels},
            'aspect_ratio': width / height,
            'total_pixels': width * height,
            'file_size_estimate': image.nbytes,
            'color_space': 'RGB' if channels == 3 else 'Grayscale' if channels == 1 else 'Unknown'
        }
    
    async def _assess_quality(self, image: np.ndarray) -> ImageQualityMetrics:
        """Assess image quality"""
        
        try:
            # Convert to grayscale for some metrics
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Brightness
            brightness = np.mean(gray)
            
            # Contrast (standard deviation)
            contrast = np.std(gray)
            
            # Saturation (for color images)
            if len(image.shape) == 3:
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                saturation = np.mean(hsv[:, :, 1])
            else:
                saturation = 0
            
            # Noise level (using median filter difference)
            filtered = cv2.medianBlur(gray, 3)
            noise = np.mean(np.abs(gray.astype(float) - filtered.astype(float)))
            
            # Overall quality score (normalized 0-1)
            sharpness_score = min(1.0, sharpness / 1000)
            brightness_score = 1.0 - abs(brightness - 128) / 128
            contrast_score = min(1.0, contrast / 127)
            saturation_score = min(1.0, saturation / 255)
            noise_score = max(0.0, 1.0 - noise / 50)
            
            overall_quality = (sharpness_score + brightness_score + 
                             contrast_score + saturation_score + noise_score) / 5
            
            return ImageQualityMetrics(
                sharpness=float(sharpness),
                brightness=float(brightness),
                contrast=float(contrast),
                saturation=float(saturation),
                noise_level=float(noise),
                overall_quality=float(overall_quality)
            )
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return ImageQualityMetrics(0, 0, 0, 0, 0, 0)
    
    async def _analyze_composition(self, image: np.ndarray) -> CompositionMetrics:
        """Analyze image composition"""
        
        try:
            height, width = image.shape[:2]
            
            # Rule of thirds analysis
            thirds_lines = {
                'vertical': [width // 3, 2 * width // 3],
                'horizontal': [height // 3, 2 * height // 3]
            }
            
            # Find significant points (using edge detection)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            edges = cv2.Canny(gray, 50, 150)
            
            # Find points on rule of thirds lines
            rule_of_thirds_points = 0
            for x in thirds_lines['vertical']:
                rule_of_thirds_points += np.sum(edges[:, x:x+1])
            for y in thirds_lines['horizontal']:
                rule_of_thirds_points += np.sum(edges[y:y+1, :])
            
            total_edge_points = np.sum(edges)
            rule_of_thirds_score = rule_of_thirds_points / total_edge_points if total_edge_points > 0 else 0
            
            # Symmetry analysis (simplified)
            left_half = image[:, :width//2]
            right_half = cv2.flip(image[:, width//2:], 1)
            
            if left_half.shape == right_half.shape:
                diff = cv2.absdiff(left_half, right_half)
                symmetry_score = 1.0 - (np.mean(diff) / 255.0)
            else:
                symmetry_score = 0.0
            
            # Balance analysis (center of mass)
            moments = cv2.moments(gray)
            if moments['m00'] != 0:
                cx = int(moments['m10'] / moments['m00'])
                cy = int(moments['m01'] / moments['m00'])
                focal_point = (cx, cy)
                
                # Distance from center
                center_dist = np.sqrt((cx - width//2)**2 + (cy - height//2)**2)
                max_dist = np.sqrt((width//2)**2 + (height//2)**2)
                balance_score = 1.0 - (center_dist / max_dist)
            else:
                focal_point = (width//2, height//2)
                balance_score = 0.0
            
            # Leading lines detection (simplified)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            leading_lines = []
            
            if lines is not None:
                for line in lines[:10]:  # Limit to top 10 lines
                    x1, y1, x2, y2 = line[0]
                    leading_lines.append(((x1, y1), (x2, y2)))
            
            # Depth of field (gradient analysis)
            gradient_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            gradient_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
            depth_score = np.std(gradient_magnitude) / np.mean(gradient_magnitude) if np.mean(gradient_magnitude) > 0 else 0
            depth_score = min(1.0, depth_score / 10)
            
            return CompositionMetrics(
                rule_of_thirds_score=float(rule_of_thirds_score),
                symmetry_score=float(symmetry_score),
                balance_score=float(balance_score),
                leading_lines=leading_lines,
                focal_point=focal_point,
                depth_of_field_score=float(depth_score)
            )
            
        except Exception as e:
            self.logger.error(f"Composition analysis failed: {e}")
            return CompositionMetrics(0, 0, 0, [], (0, 0), 0)
    
    async def _analyze_colors(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution and harmony"""
        
        try:
            # Convert to different color spaces
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if len(image.shape) == 3 else image
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB) if len(image.shape) == 3 else image
            
            # Color histograms
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Dominant colors using K-means
            pixels = image.reshape(-1, 3)
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            dominant_colors = kmeans.cluster_centers_.astype(int)
            color_percentages = []
            
            for i, color in enumerate(dominant_colors):
                mask = (kmeans.labels_ == i)
                percentage = np.sum(mask) / len(pixels) * 100
                color_percentages.append(percentage)
            
            # Color harmony analysis
            color_harmony = self._analyze_color_harmony(dominant_colors)
            
            # Color temperature
            avg_hue = np.mean(hsv[:, :, 0])
            if avg_hue < 30 or avg_hue > 150:
                color_temp = "cool"
            elif 30 <= avg_hue <= 90:
                color_temp = "warm"
            else:
                color_temp = "neutral"
            
            return {
                'dominant_colors': dominant_colors.tolist(),
                'color_percentages': color_percentages,
                'color_harmony': color_harmony,
                'color_temperature': color_temp,
                'histograms': {
                    'hue': hist_h.flatten().tolist(),
                    'saturation': hist_s.flatten().tolist(),
                    'value': hist_v.flatten().tolist()
                },
                'saturation_level': float(np.mean(hsv[:, :, 1])),
                'brightness_level': float(np.mean(hsv[:, :, 2]))
            }
            
        except Exception as e:
            self.logger.error(f"Color analysis failed: {e}")
            return {}
    
    def _analyze_color_harmony(self, colors: np.ndarray) -> Dict[str, Any]:
        """Analyze color harmony relationships"""
        
        try:
            # Convert to HSV for harmony analysis
            hsv_colors = cv2.cvtColor(colors.reshape(1, -1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
            hues = hsv_colors[:, 0]
            
            harmony_types = []
            
            # Check for complementary colors
            for i in range(len(hues)):
                for j in range(i+1, len(hues)):
                    hue_diff = abs(hues[i] - hues[j])
                    if 170 <= hue_diff <= 190:  # Complementary (around 180 degrees)
                        harmony_types.append("complementary")
                    elif 30 <= hue_diff <= 45:  # Analogous
                        harmony_types.append("analogous")
                    elif 115 <= hue_diff <= 125:  # Triadic (around 120 degrees)
                        harmony_types.append("triadic")
            
            harmony_score = len(harmony_types) / (len(hues) * (len(hues) - 1) / 2) if len(hues) > 1 else 0
            
            return {
                'harmony_types': list(set(harmony_types)),
                'harmony_score': float(harmony_score),
                'color_scheme': self._determine_color_scheme(hues)
            }
            
        except Exception as e:
            self.logger.error(f"Color harmony analysis failed: {e}")
            return {'harmony_types': [], 'harmony_score': 0, 'color_scheme': 'unknown'}
    
    def _determine_color_scheme(self, hues: np.ndarray) -> str:
        """Determine the color scheme type"""
        
        if len(hues) < 2:
            return "monochromatic"
        
        hue_ranges = [0, 60, 120, 180, 240, 300, 360]  # Color wheel segments
        hue_segments = []
        
        for hue in hues:
            for i in range(len(hue_ranges) - 1):
                if hue_ranges[i] <= hue < hue_ranges[i + 1]:
                    hue_segments.append(i)
                    break
        
        unique_segments = len(set(hue_segments))
        
        if unique_segments == 1:
            return "monochromatic"
        elif unique_segments == 2:
            return "complementary"
        elif unique_segments == 3:
            return "triadic"
        else:
            return "polychromatic"
    
    async def _analyze_texture(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze texture characteristics"""
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Texture features using GLCM (Gray Level Co-occurrence Matrix)
            from skimage.feature import graycomatrix, graycoprops
            
            # Calculate GLCM properties
            distances = [1]
            angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
            glcm = graycomatrix(gray, distances=distances, angles=angles, levels=256, symmetric=True, normed=True)
            
            properties = ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation']
            texture_features = {}
            
            for prop in properties:
                texture_features[prop] = float(np.mean(graycoprops(glcm, prop)))
            
            # Local Binary Pattern (LBP) for texture classification
            from skimage.feature import local_binary_pattern
            
            radius = 3
            n_points = 8 * radius
            lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
            
            # LBP histogram
            lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
            lbp_hist = lbp_hist.astype(float)
            lbp_hist /= (lbp_hist.sum() + 1e-7)
            
            # Texture classification based on LBP
            texture_type = self._classify_texture(lbp_hist)
            
            return {
                'glcm_features': texture_features,
                'lbp_histogram': lbp_hist.tolist(),
                'texture_type': texture_type,
                'roughness': float(texture_features['contrast']),
                'smoothness': float(texture_features['homogeneity']),
                'regularity': float(texture_features['energy'])
            }
            
        except Exception as e:
            self.logger.error(f"Texture analysis failed: {e}")
            return {}
    
    def _classify_texture(self, lbp_hist: np.ndarray) -> str:
        """Classify texture type based on LBP histogram"""
        
        # Simplified texture classification
        # In production, this would use a trained classifier
        
        peak_bin = np.argmax(lbp_hist)
        
        if peak_bin < 5:
            return "smooth"
        elif peak_bin < 15:
            return "fine"
        elif peak_bin < 25:
            return "medium"
        else:
            return "coarse"
    
    async def _understand_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """Understand scene context and content"""
        
        try:
            # This would integrate with object detection and scene classification
            # For now, provide a simplified implementation
            
            # Scene type classification based on color and texture
            color_analysis = await self._analyze_colors(image)
            texture_analysis = await self._analyze_texture(image)
            
            scene_indicators = {
                'indoor': color_analysis['brightness_level'] < 100,
                'outdoor': color_analysis['brightness_level'] > 150,
                'food_scene': 'warm' in color_analysis.get('color_temperature', ''),
                'natural_scene': texture_analysis['texture_type'] in ['coarse', 'medium']
            }
            
            # Determine most likely scene type
            scene_scores = {}
            for scene_type, indicator in scene_indicators.items():
                scene_scores[scene_type] = float(indicator)
            
            primary_scene = max(scene_scores, key=scene_scores.get) if scene_scores else 'unknown'
            
            return {
                'primary_scene': primary_scene,
                'scene_scores': scene_scores,
                'complexity': self._calculate_scene_complexity(image),
                'depth_perception': self._estimate_depth(image)
            }
            
        except Exception as e:
            self.logger.error(f"Scene understanding failed: {e}")
            return {}
    
    def _calculate_scene_complexity(self, image: np.ndarray) -> float:
        """Calculate scene complexity based on edge density"""
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            edges = cv2.Canny(gray, 50, 150)
            
            edge_density = np.sum(edges > 0) / edges.size
            return float(edge_density)
            
        except Exception:
            return 0.0
    
    def _estimate_depth(self, image: np.ndarray) -> Dict[str, float]:
        """Estimate depth perception in the image"""
        
        try:
            # Simplified depth estimation using gradient analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Calculate gradients
            gradient_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            gradient_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
            
            # Depth indicators
            depth_variance = np.var(gradient_magnitude)
            depth_range = np.max(gradient_magnitude) - np.min(gradient_magnitude)
            
            return {
                'depth_variance': float(depth_variance),
                'depth_range': float(depth_range),
                'depth_score': min(1.0, depth_variance / 1000)
            }
            
        except Exception:
            return {'depth_variance': 0.0, 'depth_range': 0.0, 'depth_score': 0.0}
    
    async def _analyze_nutritional_content(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze nutritional content for food images"""
        
        try:
            # This would use food recognition and nutritional databases
            # For now, provide a simplified implementation
            
            # Color analysis for food types
            color_analysis = await self._analyze_colors(image)
            dominant_colors = color_analysis.get('dominant_colors', [])
            
            # Estimate food categories based on colors
            food_categories = self._estimate_food_categories(dominant_colors)
            
            # Mock nutritional estimates
            nutritional_estimates = {
                'calories': np.random.randint(100, 800),
                'protein': np.random.uniform(5, 50),
                'carbs': np.random.uniform(10, 100),
                'fat': np.random.uniform(2, 40),
                'fiber': np.random.uniform(1, 20)
            }
            
            return {
                'food_categories': food_categories,
                'nutritional_estimates': nutritional_estimates,
                'health_score': self._calculate_health_score(nutritional_estimates),
                'ingredients_detected': []  # Would be populated by food recognition
            }
            
        except Exception as e:
            self.logger.error(f"Nutritional analysis failed: {e}")
            return {}
    
    def _estimate_food_categories(self, colors: List[List[int]]) -> List[str]:
        """Estimate food categories based on dominant colors"""
        
        categories = []
        
        for color in colors:
            b, g, r = color
            
            # Simple color-based food classification
            if r > 150 and g < 100 and b < 100:  # Red
                categories.append('meat')
            elif r > 150 and g > 150 and b < 100:  # Yellow
                categories.append('grains')
            elif r < 100 and g > 150 and b < 100:  # Green
                categories.append('vegetables')
            elif r < 100 and g < 100 and b > 150:  # Blue
                categories.append('beverages')
            elif r > 200 and g > 150 and b < 100:  # Orange
                categories.append('fruits')
            elif r < 50 and g < 50 and b < 50:  # Dark
                categories.append('dark_chocolate')
            elif r > 200 and g > 200 and b > 200:  # White
                categories.append('dairy')
        
        return list(set(categories))
    
    def _calculate_health_score(self, nutrition: Dict[str, float]) -> float:
        """Calculate health score based on nutritional content"""
        
        try:
            # Simplified health scoring
            protein_score = min(1.0, nutrition['protein'] / 30)
            fiber_score = min(1.0, nutrition['fiber'] / 15)
            carb_penalty = max(0, (nutrition['carbs'] - 50) / 100)
            fat_penalty = max(0, (nutrition['fat'] - 20) / 40)
            
            health_score = (protein_score + fiber_score - carb_penalty - fat_penalty) / 2
            return max(0.0, min(1.0, health_score))
            
        except Exception:
            return 0.5
    
    async def _assess_aesthetic_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Assess aesthetic quality using deep learning"""
        
        try:
            # Preprocess image for aesthetic model
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])
            
            image_pil = Image.fromarray(image)
            input_tensor = transform(image_pil).unsqueeze(0).to(self.device)
            
            # Get aesthetic score
            with torch.no_grad():
                aesthetic_score = self.aesthetic_model(input_tensor)
                aesthetic_score = torch.sigmoid(aesthetic_score).item()
            
            # Composition and quality factors
            composition = await self._analyze_composition(image)
            quality = await self._assess_quality(image)
            
            # Combined aesthetic score
            composition_weight = 0.3
            quality_weight = 0.3
            model_weight = 0.4
            
            combined_score = (
                composition.rule_of_thirds_score * composition_weight +
                quality.overall_quality * quality_weight +
                aesthetic_score * model_weight
            )
            
            return {
                'aesthetic_score': float(combined_score),
                'model_score': float(aesthetic_score),
                'composition_score': composition.rule_of_thirds_score,
                'quality_score': quality.overall_quality,
                'aesthetic_category': self._categorize_aesthetic(combined_score)
            }
            
        except Exception as e:
            self.logger.error(f"Aesthetic assessment failed: {e}")
            return {'aesthetic_score': 0.5, 'aesthetic_category': 'average'}
    
    def _categorize_aesthetic(self, score: float) -> str:
        """Categorize aesthetic quality"""
        
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'average'
        elif score >= 0.2:
            return 'poor'
        else:
            return 'very_poor'

# Factory function
def create_advanced_analyzer(cache_dir: str = "image_cache") -> AdvancedImageAnalyzer:
    """Create advanced image analyzer"""
    return AdvancedImageAnalyzer(cache_dir)
            
            return results
            
        except Exception as e:
            print(f"Error in image analysis: {e}")
            raise
    
    def _get_image_info(self, image: Image.Image, image_np: np.ndarray) -> Dict[str, Any]:
        """Get basic image information"""
        return {
            "width": image.width,
            "height": image.height,
            "channels": image_np.shape[2] if len(image_np.shape) > 2 else 1,
            "mode": image.mode,
            "format": image.format,
            "size_bytes": len(image.tobytes()),
            "aspect_ratio": image.width / image.height,
            "megapixels": (image.width * image.height) / 1000000
        }
    
    async def _analyze_quality(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image quality metrics"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_quality_sync, image_np
        )
    
    def _analyze_quality_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous quality analysis"""
        # Convert to grayscale if needed
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Blur detection (FFT based)
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = np.abs(fft_shift)
        blur_score = np.sum(magnitude_spectrum[magnitude_spectrum > np.percentile(magnitude_spectrum, 95)]) / np.sum(magnitude_spectrum)
        
        # Noise estimation
        if len(image_np.shape) == 3:
            noise = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            noise = image_np
        noise_level = np.std(cv2.GaussianBlur(noise, (3, 3), 0) - noise)
        
        # Brightness and contrast
        brightness = np.mean(gray) / 255.0
        contrast = np.std(gray) / 255.0
        
        # Histogram analysis
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_normalized = hist.flatten() / hist.sum()
        
        # Dynamic range
        dynamic_range = np.percentile(gray, 99) - np.percentile(gray, 1)
        
        # Exposure assessment
        overexposed = np.sum(gray > 240) / gray.size
        underexposed = np.sum(gray < 15) / gray.size
        
        # Overall quality score (0-1)
        quality_score = min(laplacian_var / 1000, 1.0) * 0.3 + \
                       (1 - blur_score) * 0.2 + \
                       (1 - noise_level / 50) * 0.2 + \
                       (1 - abs(0.5 - brightness)) * 0.15 + \
                       contrast * 0.15
        
        return {
            "sharpness": float(laplacian_var),
            "blur_score": float(blur_score),
            "noise_level": float(noise_level),
            "brightness": float(brightness),
            "contrast": float(contrast),
            "dynamic_range": float(dynamic_range),
            "overexposed_ratio": float(overexposed),
            "underexposed_ratio": float(underexposed),
            "histogram": hist_normalized.tolist(),
            "quality_score": float(max(0, min(quality_score, 1.0))),
            "recommendations": self._get_quality_recommendations(laplacian_var, blur_score, noise_level, brightness, contrast)
        }
    
    def _get_quality_recommendations(self, sharpness: float, blur: float, noise: float, brightness: float, contrast: float) -> List[str]:
        """Get quality improvement recommendations"""
        recommendations = []
        
        if sharpness < 100:
            recommendations.append("Image appears blurry - consider using a sharper image or applying sharpening")
        
        if blur > 0.7:
            recommendations.append("High blur detected - check focus and camera stability")
        
        if noise > 20:
            recommendations.append("High noise level - consider using lower ISO or apply denoising")
        
        if brightness < 0.2:
            recommendations.append("Image is too dark - increase exposure or brightness")
        elif brightness > 0.8:
            recommendations.append("Image is too bright - decrease exposure or brightness")
        
        if contrast < 0.1:
            recommendations.append("Low contrast - enhance contrast for better visibility")
        
        return recommendations
    
    async def _analyze_composition(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image composition"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_composition_sync, image_np
        )
    
    def _analyze_composition_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous composition analysis"""
        # Convert to grayscale for analysis
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Rule of thirds analysis
        height, width = gray.shape
        third_h, third_w = height // 3, width // 3
        
        # Calculate edge density in each third
        edges = cv2.Canny(gray, 50, 150)
        thirds_density = []
        
        for i in range(3):
            for j in range(3):
                h_start, h_end = i * third_h, (i + 1) * third_h
                w_start, w_end = j * third_w, (j + 1) * third_w
                third_edges = edges[h_start:h_end, w_start:w_end]
                density = np.sum(third_edges > 0) / third_edges.size
                thirds_density.append(density)
        
        # Center of mass
        moments = cv2.moments(gray)
        if moments['m00'] != 0:
            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])
        else:
            cx, cy = width // 2, height // 2
        
        # Symmetry analysis
        left_half = gray[:, :width//2]
        right_half = cv2.flip(gray[:, width//2:], 1)
        if left_half.shape != right_half.shape:
            right_half = cv2.resize(right_half, (left_half.shape[1], left_half.shape[0]))
        symmetry = 1 - np.mean(np.abs(left_half - right_half)) / 255.0
        
        # Horizon line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=width//4, maxLineGap=20)
        horizontal_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 30 or abs(angle) > 150:  # Nearly horizontal
                    horizontal_lines.append(line[0])
        
        return {
            "rule_of_thirds_score": float(np.std(thirds_density) * 3),  # Higher variance = better composition
            "thirds_density": [float(d) for d in thirds_density],
            "center_of_mass": [cx, cy],
            "symmetry_score": float(symmetry),
            "horizontal_lines_count": len(horizontal_lines),
            "composition_score": float((np.std(thirds_density) * 3 + symmetry) / 2),
            "recommendations": self._get_composition_recommendations(thirds_density, symmetry)
        }
    
    def _get_composition_recommendations(self, thirds_density: List[float], symmetry: float) -> List[str]:
        """Get composition improvement recommendations"""
        recommendations = []
        
        if np.std(thirds_density) < 0.1:
            recommendations.append("Consider applying rule of thirds - place key elements along the grid lines")
        
        if symmetry > 0.8:
            recommendations.append("High symmetry detected - consider adding asymmetry for more dynamic composition")
        
        return recommendations
    
    async def _analyze_colors(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image colors"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_colors_sync, image_np
        )
    
    def _analyze_colors_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous color analysis"""
        # Convert to different color spaces
        if len(image_np.shape) == 3:
            rgb = image_np
            hsv = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
            lab = cv2.cvtColor(image_np, cv2.COLOR_RGB2LAB)
        else:
            # Convert grayscale to RGB for analysis
            rgb = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        
        # Dominant colors (K-means clustering)
        pixels = rgb.reshape(-1, 3)
        k = 5  # Number of dominant colors
        
        # Simple color quantization (mock K-means)
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        dominant_colors = []
        for center in kmeans.cluster_centers_:
            dominant_colors.append({
                "rgb": [int(c) for c in center],
                "hex": '#{:02x}{:02x}{:02x}'.format(int(center[0]), int(center[1]), int(center[2]))
            })
        
        # Color statistics
        mean_rgb = np.mean(rgb, axis=(0, 1))
        std_rgb = np.std(rgb, axis=(0, 1))
        
        # Saturation analysis
        saturation = hsv[:, :, 1]
        avg_saturation = np.mean(saturation) / 255.0
        
        # Brightness analysis
        value = hsv[:, :, 2]
        avg_brightness = np.mean(value) / 255.0
        
        # Color temperature estimation
        warm_pixels = np.sum((hsv[:, :, 0] < 30) | (hsv[:, :, 0] > 150))
        cool_pixels = np.sum((hsv[:, :, 0] >= 30) & (hsv[:, :, 0] <= 150))
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        warm_ratio = warm_pixels / total_pixels
        color_temperature = "warm" if warm_ratio > 0.6 else "cool" if warm_ratio < 0.4 else "balanced"
        
        return {
            "dominant_colors": dominant_colors,
            "mean_rgb": [float(c) for c in mean_rgb],
            "std_rgb": [float(c) for c in std_rgb],
            "avg_saturation": float(avg_saturation),
            "avg_brightness": float(avg_brightness),
            "color_temperature": color_temperature,
            "warm_ratio": float(warm_ratio),
            "color_harmony": self._analyze_color_harmony(dominant_colors)
        }
    
    def _analyze_color_harmony(self, colors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze color harmony"""
        if len(colors) < 2:
            return {"harmony_score": 1.0, "harmony_type": "monochromatic"}
        
        # Simple harmony analysis based on color relationships
        harmony_score = 0.0
        harmony_type = "complementary"
        
        # This is a simplified version - in practice, you'd use more sophisticated color theory
        if len(colors) == 2:
            harmony_score = 0.8
            harmony_type = "complementary"
        elif len(colors) == 3:
            harmony_score = 0.7
            harmony_type = "triadic"
        else:
            harmony_score = 0.6
            harmony_type = "analogous"
        
        return {
            "harmony_score": harmony_score,
            "harmony_type": harmony_type
        }
    
    async def _analyze_texture(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image texture"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_texture_sync, image_np
        )
    
    def _analyze_texture_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous texture analysis"""
        # Convert to grayscale
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Local Binary Pattern (LBP)
        radius = 3
        n_points = 8 * radius
        lbp = feature.local_binary_pattern(gray, n_points, radius, method='uniform')
        
        # LBP histogram
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
        lbp_hist = lbp_hist.astype(float)
        lbp_hist /= (lbp_hist.sum() + 1e-7)
        
        # GLCM (Gray-Level Co-occurrence Matrix)
        distances = [1]
        angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        
        try:
            glcm = feature.graycomatrix(gray, distances=distances, angles=angles, levels=256, symmetric=True, normed=True)
            
            # GLCM features
            contrast = feature.graycoprops(glcm, 'contrast').mean()
            dissimilarity = feature.graycoprops(glcm, 'dissimilarity').mean()
            homogeneity = feature.graycoprops(glcm, 'homogeneity').mean()
            energy = feature.graycoprops(glcm, 'energy').mean()
            correlation = feature.graycoprops(glcm, 'correlation').mean()
            
        except:
            # Fallback values if GLCM fails
            contrast = dissimilarity = homogeneity = energy = correlation = 0.5
        
        # Gabor filters
        frequencies = [0.1, 0.3, 0.5]
        thetas = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        
        gabor_responses = []
        for freq in frequencies:
            for theta in thetas:
                real, imag = filters.gabor(gray, frequency=freq, theta=theta)
                gabor_responses.append(np.mean(real))
        
        gabor_mean = np.mean(gabor_responses)
        gabor_std = np.std(gabor_responses)
        
        # Texture classification
        texture_type = self._classify_texture(lbp_hist, contrast, homogeneity, gabor_std)
        
        return {
            "lbp_histogram": lbp_hist.tolist(),
            "glcm_features": {
                "contrast": float(contrast),
                "dissimilarity": float(dissimilarity),
                "homogeneity": float(homogeneity),
                "energy": float(energy),
                "correlation": float(correlation)
            },
            "gabor_features": {
                "mean": float(gabor_mean),
                "std": float(gabor_std)
            },
            "texture_type": texture_type,
            "texture_complexity": float(self._calculate_texture_complexity(lbp_hist))
        }
    
    def _classify_texture(self, lbp_hist: np.ndarray, contrast: float, homogeneity: float, gabor_std: float) -> str:
        """Classify texture type based on features"""
        # Simple rule-based classification
        if homogeneity > 0.8:
            return "smooth"
        elif contrast > 0.5 and gabor_std > 0.3:
            return "rough"
        elif gabor_std > 0.4:
            return "complex"
        else:
            return "medium"
    
    def _calculate_texture_complexity(self, lbp_hist: np.ndarray) -> float:
        """Calculate texture complexity from LBP histogram"""
        # Use entropy as a measure of complexity
        entropy = -np.sum(lbp_hist * np.log2(lbp_hist + 1e-7))
        return float(entropy / 10)  # Normalize to 0-1 range
    
    async def _detect_objects(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Simple object detection using contour analysis"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._detect_objects_sync, image_np
        )
    
    def _detect_objects_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous simple object detection"""
        # Convert to grayscale
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        min_area = 100
        max_area = gray.shape[0] * gray.shape[1] * 0.5
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate shape properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                else:
                    circularity = 0
                
                # Aspect ratio
                aspect_ratio = w / h if h > 0 else 0
                
                objects.append({
                    "bbox": [x, y, w, h],
                    "area": float(area),
                    "perimeter": float(perimeter),
                    "circularity": float(circularity),
                    "aspect_ratio": float(aspect_ratio),
                    "center": [x + w // 2, y + h // 2]
                })
        
        return {
            "objects_detected": len(objects),
            "objects": objects,
            "object_density": float(len(objects) / (gray.shape[0] * gray.shape[1] / 10000))  # Objects per 10k pixels
        }

class ImageEnhancer:
    """Image enhancement utilities"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def enhance_image(self, image_data: str, enhancement_type: str = "auto") -> Dict[str, Any]:
        """Enhance image based on type"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            if enhancement_type == "auto":
                # Analyze and apply appropriate enhancements
                image_np = np.array(image)
                analyzer = ImageAnalyzer()
                analysis = await analyzer._analyze_quality(image_np)
                
                enhanced_image = image.copy()
                
                # Apply enhancements based on analysis
                if analysis["brightness"] < 0.3:
                    enhancer = ImageEnhance.Brightness(enhanced_image)
                    enhanced_image = enhancer.enhance(1.2)
                
                if analysis["contrast"] < 0.3:
                    enhancer = ImageEnhance.Contrast(enhanced_image)
                    enhanced_image = enhancer.enhance(1.3)
                
                if analysis["sharpness"] < 100:
                    enhanced_image = enhanced_image.filter(ImageFilter.SHARPEN)
                
            elif enhancement_type == "brightness":
                enhancer = ImageEnhance.Brightness(image)
                enhanced_image = enhancer.enhance(1.2)
                
            elif enhancement_type == "contrast":
                enhancer = ImageEnhance.Contrast(image)
                enhanced_image = enhancer.enhance(1.3)
                
            elif enhancement_type == "sharpness":
                enhanced_image = image.filter(ImageFilter.SHARPEN)
                
            elif enhancement_type == "color":
                enhancer = ImageEnhance.Color(image)
                enhanced_image = enhancer.enhance(1.1)
                
            else:
                enhanced_image = image
            
            # Convert back to base64
            buffer = io.BytesIO()
            enhanced_image.save(buffer, format='PNG')
            enhanced_data = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "enhanced_image": enhanced_data,
                "enhancement_type": enhancement_type,
                "original_size": [image.width, image.height],
                "enhanced_size": [enhanced_image.width, enhanced_image.height]
            }
            
        except Exception as e:
            print(f"Error in image enhancement: {e}")
            raise

# Utility functions
def create_analyzer() -> ImageAnalyzer:
    """Create image analyzer instance"""
    return ImageAnalyzer()

def create_enhancer() -> ImageEnhancer:
    """Create image enhancer instance"""
    return ImageEnhancer()
