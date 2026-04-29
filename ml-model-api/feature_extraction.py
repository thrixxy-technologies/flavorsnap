#!/usr/bin/env python3
"""
Advanced Feature Extraction for FlavorSnap ML Model API
Implements automated feature extraction with various techniques for food image classification
"""

import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import hashlib
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import skimage.feature as skfeature
import skimage.measure as skmeasure
from scipy import ndimage
from scipy.spatial.distance import pdist, squareform
import pandas as pd
from datetime import datetime
import pickle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeatureType(Enum):
    """Feature extraction types"""
    COLOR = "color"
    TEXTURE = "texture"
    SHAPE = "shape"
    DEEP = "deep"
    STATISTICAL = "statistical"
    HISTOGRAM = "histogram"
    GRADIENT = "gradient"
    FREQUENCY = "frequency"

@dataclass
class FeatureConfig:
    """Feature extraction configuration"""
    enable_color_features: bool = True
    enable_texture_features: bool = True
    enable_shape_features: bool = True
    enable_deep_features: bool = True
    enable_statistical_features: bool = True
    enable_histogram_features: bool = True
    enable_gradient_features: bool = True
    enable_frequency_features: bool = True
    
    # Deep learning model configuration
    deep_model_name: str = "resnet18"
    deep_layer_name: str = "avgpool"
    feature_dim: int = 512
    
    # Color feature configuration
    color_spaces: List[str] = None
    hist_bins: int = 256
    
    # Texture feature configuration
    texture_methods: List[str] = None
    glcm_distances: List[int] = None
    glcm_angles: List[int] = None
    
    # Shape feature configuration
    shape_methods: List[str] = None
    
    def __post_init__(self):
        if self.color_spaces is None:
            self.color_spaces = ["rgb", "hsv", "lab"]
        if self.texture_methods is None:
            self.texture_methods = ["glcm", "lbp", "gabor"]
        if self.glcm_distances is None:
            self.glcm_distances = [1, 2, 3]
        if self.glcm_angles is None:
            self.glcm_angles = [0, 45, 90, 135]
        if self.shape_methods is None:
            self.shape_methods = ["hu_moments", "contour", "sift"]

@dataclass
class ExtractedFeatures:
    """Container for extracted features"""
    feature_id: str
    image_path: str
    feature_type: FeatureType
    features: Dict[str, Any]
    metadata: Dict[str, Any]
    extraction_time: datetime
    feature_hash: str

class AutomatedFeatureExtractor:
    """Advanced automated feature extraction system"""
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize deep learning model
        self.deep_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Feature extraction cache
        self.feature_cache = {}
        self.cache_file = "feature_cache.pkl"
        
        # Initialize components
        self._init_deep_model()
        self._load_cache()
        
        logger.info("AutomatedFeatureExtractor initialized")
    
    def _init_deep_model(self):
        """Initialize deep learning model for feature extraction"""
        try:
            if self.config.enable_deep_features:
                # Load pretrained model
                if self.config.deep_model_name == "resnet18":
                    self.deep_model = models.resnet18(weights='IMAGENET1K_V1')
                elif self.config.deep_model_name == "resnet50":
                    self.deep_model = models.resnet50(weights='IMAGENET1K_V1')
                elif self.config.deep_model_name == "vgg16":
                    self.deep_model = models.vgg16(weights='IMAGENET1K_V1')
                else:
                    self.deep_model = models.resnet18(weights='IMAGENET1K_V1')
                
                # Remove final classification layer
                if hasattr(self.deep_model, 'fc'):
                    self.deep_model.fc = nn.Identity()
                elif hasattr(self.deep_model, 'classifier'):
                    if isinstance(self.deep_model.classifier, nn.Sequential):
                        self.deep_model.classifier[-1] = nn.Identity()
                
                self.deep_model.eval()
                self.deep_model.to(self.device)
                
                logger.info(f"Deep model {self.config.deep_model_name} loaded")
                
        except Exception as e:
            logger.error(f"Failed to initialize deep model: {str(e)}")
            self.config.enable_deep_features = False
    
    def _load_cache(self):
        """Load feature extraction cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    self.feature_cache = pickle.load(f)
                logger.info(f"Loaded {len(self.feature_cache)} cached features")
        except Exception as e:
            logger.error(f"Failed to load cache: {str(e)}")
            self.feature_cache = {}
    
    def _save_cache(self):
        """Save feature extraction cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.feature_cache, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def extract_all_features(self, image_path: str) -> Dict[FeatureType, ExtractedFeatures]:
        """Extract all types of features from an image"""
        try:
            # Generate feature ID
            feature_id = self._generate_feature_id(image_path)
            
            # Check cache
            cache_key = f"{image_path}_{hash(str(self.config))}"
            if cache_key in self.feature_cache:
                logger.info(f"Features loaded from cache for {image_path}")
                return self.feature_cache[cache_key]
            
            # Load image
            image = self._load_image(image_path)
            if image is None:
                raise ValueError(f"Failed to load image: {image_path}")
            
            all_features = {}
            extraction_time = datetime.now()
            
            # Extract different types of features
            if self.config.enable_color_features:
                color_features = self._extract_color_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.COLOR] = color_features
            
            if self.config.enable_texture_features:
                texture_features = self._extract_texture_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.TEXTURE] = texture_features
            
            if self.config.enable_shape_features:
                shape_features = self._extract_shape_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.SHAPE] = shape_features
            
            if self.config.enable_deep_features:
                deep_features = self._extract_deep_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.DEEP] = deep_features
            
            if self.config.enable_statistical_features:
                statistical_features = self._extract_statistical_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.STATISTICAL] = statistical_features
            
            if self.config.enable_histogram_features:
                histogram_features = self._extract_histogram_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.HISTOGRAM] = histogram_features
            
            if self.config.enable_gradient_features:
                gradient_features = self._extract_gradient_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.GRADIENT] = gradient_features
            
            if self.config.enable_frequency_features:
                frequency_features = self._extract_frequency_features(image, image_path, feature_id, extraction_time)
                all_features[FeatureType.FREQUENCY] = frequency_features
            
            # Cache results
            self.feature_cache[cache_key] = all_features
            self._save_cache()
            
            logger.info(f"Extracted {len(all_features)} feature types from {image_path}")
            return all_features
            
        except Exception as e:
            logger.error(f"Failed to extract features from {image_path}: {str(e)}")
            raise
    
    def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Load and preprocess image"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                # Try with PIL
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Convert to RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {str(e)}")
            return None
    
    def _extract_color_features(self, image: np.ndarray, image_path: str, 
                              feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract color-based features"""
        try:
            features = {}
            
            for color_space in self.config.color_spaces:
                if color_space.lower() == "rgb":
                    # RGB color features
                    rgb_image = image
                    features[f"{color_space}_mean"] = np.mean(rgb_image, axis=(0, 1))
                    features[f"{color_space}_std"] = np.std(rgb_image, axis=(0, 1))
                    features[f"{color_space}_skew"] = self._calculate_skewness(rgb_image, axis=(0, 1))
                    features[f"{color_space}_kurtosis"] = self._calculate_kurtosis(rgb_image, axis=(0, 1))
                
                elif color_space.lower() == "hsv":
                    # HSV color features
                    hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
                    features[f"{color_space}_mean"] = np.mean(hsv_image, axis=(0, 1))
                    features[f"{color_space}_std"] = np.std(hsv_image, axis=(0, 1))
                    features[f"{color_space}_skew"] = self._calculate_skewness(hsv_image, axis=(0, 1))
                    features[f"{color_space}_kurtosis"] = self._calculate_kurtosis(hsv_image, axis=(0, 1))
                
                elif color_space.lower() == "lab":
                    # LAB color features
                    lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
                    features[f"{color_space}_mean"] = np.mean(lab_image, axis=(0, 1))
                    features[f"{color_space}_std"] = np.std(lab_image, axis=(0, 1))
                    features[f"{color_space}_skew"] = self._calculate_skewness(lab_image, axis=(0, 1))
                    features[f"{color_space}_kurtosis"] = self._calculate_kurtosis(lab_image, axis=(0, 1))
            
            # Color dominance
            dominant_colors = self._get_dominant_colors(image, k=5)
            features["dominant_colors"] = dominant_colors
            
            # Color moments
            features["color_moments"] = self._calculate_color_moments(image)
            
            metadata = {
                "method": "color_extraction",
                "color_spaces": self.config.color_spaces,
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.COLOR,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract color features: {str(e)}")
            raise
    
    def _extract_texture_features(self, image: np.ndarray, image_path: str,
                                 feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract texture-based features"""
        try:
            features = {}
            gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            for method in self.config.texture_methods:
                if method.lower() == "glcm":
                    # Gray-Level Co-occurrence Matrix features
                    glcm = skfeature.graycomatrix(
                        gray_image,
                        distances=self.config.glcm_distances,
                        angles=np.array(self.config.glcm_angles) * np.pi / 180,
                        levels=256,
                        symmetric=True,
                        normed=True
                    )
                    
                    # Calculate GLCM properties
                    properties = ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation', 'ASM']
                    for prop in properties:
                        glcm_feature = skfeature.graycoprops(glcm, prop)
                        for i, dist in enumerate(self.config.glcm_distances):
                            for j, angle in enumerate(self.config.glcm_angles):
                                features[f"glcm_{prop}_dist{dist}_angle{angle}"] = glcm_feature[i, j]
                
                elif method.lower() == "lbp":
                    # Local Binary Pattern features
                    radius = 3
                    n_points = 8 * radius
                    lbp = skfeature.local_binary_pattern(gray_image, n_points, radius, method='uniform')
                    
                    # LBP histogram
                    lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
                    lbp_hist = lbp_hist.astype(float)
                    lbp_hist /= (lbp_hist.sum() + 1e-7)
                    
                    for i, val in enumerate(lbp_hist):
                        features[f"lbp_hist_{i}"] = val
                
                elif method.lower() == "gabor":
                    # Gabor filter features
                    frequencies = [0.1, 0.3, 0.5]
                    angles = [0, 45, 90, 135]
                    
                    for freq in frequencies:
                        for angle in angles:
                            real, _ = skfeature.gabor(gray_image, frequency=freq, theta=np.radians(angle))
                            features[f"gabor_mean_freq{freq}_angle{angle}"] = np.mean(real)
                            features[f"gabor_std_freq{freq}_angle{angle}"] = np.std(real)
            
            metadata = {
                "method": "texture_extraction",
                "texture_methods": self.config.texture_methods,
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.TEXTURE,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract texture features: {str(e)}")
            raise
    
    def _extract_shape_features(self, image: np.ndarray, image_path: str,
                              feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract shape-based features"""
        try:
            features = {}
            gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            for method in self.config.shape_methods:
                if method.lower() == "hu_moments":
                    # Hu moments
                    moments = cv2.moments(gray_image)
                    hu_moments = cv2.HuMoments(moments)
                    
                    # Log transform Hu moments
                    for i, moment in enumerate(hu_moments):
                        features[f"hu_moment_{i}"] = -1 * np.sign(moment) * np.log10(abs(moment) + 1e-10)
                
                elif method.lower() == "contour":
                    # Contour-based features
                    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        # Find largest contour
                        largest_contour = max(contours, key=cv2.contourArea)
                        
                        # Contour area and perimeter
                        features["contour_area"] = cv2.contourArea(largest_contour)
                        features["contour_perimeter"] = cv2.arcLength(largest_contour, True)
                        
                        # Contour solidity
                        hull = cv2.convexHull(largest_contour)
                        hull_area = cv2.contourArea(hull)
                        features["contour_solidity"] = float(cv2.contourArea(largest_contour)) / hull_area if hull_area > 0 else 0
                        
                        # Aspect ratio
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        features["aspect_ratio"] = float(w) / h if h > 0 else 0
                        
                        # Extent
                        features["extent"] = float(cv2.contourArea(largest_contour)) / (w * h) if w * h > 0 else 0
                
                elif method.lower() == "sift":
                    # SIFT features (simplified)
                    try:
                        sift = cv2.SIFT_create()
                        keypoints, descriptors = sift.detectAndCompute(gray_image, None)
                        
                        features["sift_keypoint_count"] = len(keypoints)
                        if descriptors is not None and len(descriptors) > 0:
                            features["sift_descriptor_mean"] = np.mean(descriptors)
                            features["sift_descriptor_std"] = np.std(descriptors)
                        else:
                            features["sift_descriptor_mean"] = 0
                            features["sift_descriptor_std"] = 0
                    except:
                        # Fallback if SIFT not available
                        features["sift_keypoint_count"] = 0
                        features["sift_descriptor_mean"] = 0
                        features["sift_descriptor_std"] = 0
            
            metadata = {
                "method": "shape_extraction",
                "shape_methods": self.config.shape_methods,
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.SHAPE,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract shape features: {str(e)}")
            raise
    
    def _extract_deep_features(self, image: np.ndarray, image_path: str,
                             feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract deep learning-based features"""
        try:
            features = {}
            
            if self.deep_model is None:
                raise ValueError("Deep model not initialized")
            
            # Preprocess image for deep model
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            input_tensor = transform(image).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                if hasattr(self.deep_model, self.config.deep_layer_name):
                    # Hook to get intermediate layer features
                    features_tensor = None
                    
                    def hook_fn(module, input, output):
                        nonlocal features_tensor
                        features_tensor = output
                    
                    # Register hook
                    target_layer = dict(self.deep_model.named_modules())[self.config.deep_layer_name]
                    hook = target_layer.register_forward_hook(hook_fn)
                    
                    # Forward pass
                    _ = self.deep_model(input_tensor)
                    
                    # Remove hook
                    hook.remove()
                    
                    if features_tensor is not None:
                        features_tensor = features_tensor.squeeze().cpu().numpy()
                        
                        # Store features
                        for i, val in enumerate(features_tensor):
                            features[f"deep_feature_{i}"] = val
                else:
                    # Use final output
                    output = self.deep_model(input_tensor)
                    features_tensor = output.squeeze().cpu().numpy()
                    
                    for i, val in enumerate(features_tensor):
                        features[f"deep_feature_{i}"] = val
            
            metadata = {
                "method": "deep_extraction",
                "model_name": self.config.deep_model_name,
                "layer_name": self.config.deep_layer_name,
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.DEEP,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract deep features: {str(e)}")
            raise
    
    def _extract_statistical_features(self, image: np.ndarray, image_path: str,
                                    feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract statistical features"""
        try:
            features = {}
            
            # Basic statistics for each channel
            for i, channel_name in enumerate(['R', 'G', 'B']):
                channel = image[:, :, i]
                
                features[f"{channel_name}_mean"] = np.mean(channel)
                features[f"{channel_name}_median"] = np.median(channel)
                features[f"{channel_name}_std"] = np.std(channel)
                features[f"{channel_name}_var"] = np.var(channel)
                features[f"{channel_name}_min"] = np.min(channel)
                features[f"{channel_name}_max"] = np.max(channel)
                features[f"{channel_name}_range"] = np.max(channel) - np.min(channel)
                features[f"{channel_name}_skewness"] = self._calculate_skewness(channel)
                features[f"{channel_name}_kurtosis"] = self._calculate_kurtosis(channel)
                
                # Percentiles
                for p in [25, 50, 75, 90, 95]:
                    features[f"{channel_name}_percentile_{p}"] = np.percentile(channel, p)
            
            # Inter-channel statistics
            features["rg_correlation"] = np.corrcoef(image[:, :, 0].flatten(), image[:, :, 1].flatten())[0, 1]
            features["rb_correlation"] = np.corrcoef(image[:, :, 0].flatten(), image[:, :, 2].flatten())[0, 1]
            features["gb_correlation"] = np.corrcoef(image[:, :, 1].flatten(), image[:, :, 2].flatten())[0, 1]
            
            metadata = {
                "method": "statistical_extraction",
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.STATISTICAL,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract statistical features: {str(e)}")
            raise
    
    def _extract_histogram_features(self, image: np.ndarray, image_path: str,
                                  feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract histogram-based features"""
        try:
            features = {}
            
            # Color histograms
            for i, channel_name in enumerate(['R', 'G', 'B']):
                channel = image[:, :, i]
                hist, bin_edges = np.histogram(channel, bins=self.config.hist_bins, range=(0, 256))
                
                # Normalize histogram
                hist = hist.astype(float)
                hist /= (hist.sum() + 1e-7)
                
                # Store histogram features
                for j, val in enumerate(hist):
                    features[f"{channel_name}_hist_{j}"] = val
                
                # Histogram statistics
                features[f"{channel_name}_hist_mean"] = np.mean(hist)
                features[f"{channel_name}_hist_std"] = np.std(hist)
                features[f"{channel_name}_hist_entropy"] = self._calculate_entropy(hist)
            
            # Grayscale histogram
            gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            gray_hist, _ = np.histogram(gray_image, bins=self.config.hist_bins, range=(0, 256))
            gray_hist = gray_hist.astype(float)
            gray_hist /= (gray_hist.sum() + 1e-7)
            
            for j, val in enumerate(gray_hist):
                features[f"gray_hist_{j}"] = val
            
            features["gray_hist_mean"] = np.mean(gray_hist)
            features["gray_hist_std"] = np.std(gray_hist)
            features["gray_hist_entropy"] = self._calculate_entropy(gray_hist)
            
            metadata = {
                "method": "histogram_extraction",
                "bins": self.config.hist_bins,
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.HISTOGRAM,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract histogram features: {str(e)}")
            raise
    
    def _extract_gradient_features(self, image: np.ndarray, image_path: str,
                                 feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract gradient-based features"""
        try:
            features = {}
            gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Sobel gradients
            grad_x = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
            
            # Gradient magnitude and direction
            grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            grad_direction = np.arctan2(grad_y, grad_x)
            
            # Gradient statistics
            features["grad_magnitude_mean"] = np.mean(grad_magnitude)
            features["grad_magnitude_std"] = np.std(grad_magnitude)
            features["grad_magnitude_max"] = np.max(grad_magnitude)
            features["grad_direction_mean"] = np.mean(grad_direction)
            features["grad_direction_std"] = np.std(grad_direction)
            
            # Gradient histogram
            grad_hist, _ = np.histogram(grad_magnitude, bins=50, range=(0, np.max(grad_magnitude)))
            grad_hist = grad_hist.astype(float)
            grad_hist /= (grad_hist.sum() + 1e-7)
            
            for i, val in enumerate(grad_hist):
                features[f"grad_hist_{i}"] = val
            
            # Edge density
            edges = cv2.Canny(gray_image, 50, 150)
            features["edge_density"] = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            metadata = {
                "method": "gradient_extraction",
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.GRADIENT,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract gradient features: {str(e)}")
            raise
    
    def _extract_frequency_features(self, image: np.ndarray, image_path: str,
                                  feature_id: str, extraction_time: datetime) -> ExtractedFeatures:
        """Extract frequency-domain features"""
        try:
            features = {}
            gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # 2D FFT
            fft = np.fft.fft2(gray_image)
            fft_shift = np.fft.fftshift(fft)
            magnitude_spectrum = np.abs(fft_shift)
            
            # Frequency domain statistics
            features["fft_mean"] = np.mean(magnitude_spectrum)
            features["fft_std"] = np.std(magnitude_spectrum)
            features["fft_max"] = np.max(magnitude_spectrum)
            
            # Radial frequency analysis
            h, w = magnitude_spectrum.shape
            center_h, center_w = h // 2, w // 2
            
            # Create radial bins
            max_radius = min(center_h, center_w)
            radial_bins = 10
            
            for i in range(radial_bins):
                r_inner = i * max_radius / radial_bins
                r_outer = (i + 1) * max_radius / radial_bins
                
                # Create circular mask
                y, x = np.ogrid[:h, :w]
                mask = ((x - center_w)**2 + (y - center_h)**2 >= r_inner**2) & \
                       ((x - center_w)**2 + (y - center_h)**2 < r_outer**2)
                
                if np.any(mask):
                    radial_energy = np.sum(magnitude_spectrum[mask])
                    features[f"radial_energy_{i}"] = radial_energy
                else:
                    features[f"radial_energy_{i}"] = 0
            
            # DCT features
            dct = cv2.dct(gray_image.astype(np.float32))
            
            # DCT statistics
            features["dct_mean"] = np.mean(dct)
            features["dct_std"] = np.std(dct)
            features["dct_max"] = np.max(dct)
            
            # Low-frequency energy (top-left corner)
            low_freq_size = 8
            low_freq_energy = np.sum(np.abs(dct[:low_freq_size, :low_freq_size]))
            total_energy = np.sum(np.abs(dct))
            features["low_freq_ratio"] = low_freq_energy / (total_energy + 1e-7)
            
            metadata = {
                "method": "frequency_extraction",
                "feature_count": len(features)
            }
            
            feature_hash = self._calculate_feature_hash(features)
            
            return ExtractedFeatures(
                feature_id=feature_id,
                image_path=image_path,
                feature_type=FeatureType.FREQUENCY,
                features=features,
                metadata=metadata,
                extraction_time=extraction_time,
                feature_hash=feature_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to extract frequency features: {str(e)}")
            raise
    
    def _generate_feature_id(self, image_path: str) -> str:
        """Generate unique feature ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{image_path}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def _calculate_feature_hash(self, features: Dict[str, Any]) -> str:
        """Calculate hash of feature vector"""
        try:
            # Convert features to string representation
            feature_str = json.dumps(features, sort_keys=True, default=str)
            return hashlib.sha256(feature_str.encode()).hexdigest()[:16]
        except:
            return hashlib.md5(str(features).encode()).hexdigest()[:16]
    
    def _calculate_skewness(self, data: np.ndarray, axis=None) -> float:
        """Calculate skewness of data"""
        if axis is None:
            data = data.flatten()
        
        mean = np.mean(data, axis=axis)
        std = np.std(data, axis=axis)
        
        if std == 0:
            return 0
        
        return np.mean(((data - mean) / std) ** 3, axis=axis)
    
    def _calculate_kurtosis(self, data: np.ndarray, axis=None) -> float:
        """Calculate kurtosis of data"""
        if axis is None:
            data = data.flatten()
        
        mean = np.mean(data, axis=axis)
        std = np.std(data, axis=axis)
        
        if std == 0:
            return 0
        
        return np.mean(((data - mean) / std) ** 4, axis=axis) - 3
    
    def _calculate_entropy(self, histogram: np.ndarray) -> float:
        """Calculate entropy of histogram"""
        histogram = histogram[histogram > 0]  # Remove zero values
        return -np.sum(histogram * np.log2(histogram + 1e-10))
    
    def _get_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[List[float]]:
        """Get dominant colors using k-means clustering"""
        try:
            # Reshape image to pixel array
            pixels = image.reshape(-1, 3)
            
            # Simple k-means clustering
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get dominant colors
            dominant_colors = kmeans.cluster_centers_.tolist()
            
            return dominant_colors
            
        except:
            # Fallback: return color quantiles
            quantiles = [0.1, 0.3, 0.5, 0.7, 0.9]
            colors = []
            for q in quantiles:
                color = np.percentile(image.reshape(-1, 3), q * 100, axis=0)
                colors.append(color.tolist())
            return colors
    
    def _calculate_color_moments(self, image: np.ndarray) -> Dict[str, List[float]]:
        """Calculate color moments for each channel"""
        moments = {}
        
        for i, channel_name in enumerate(['R', 'G', 'B']):
            channel = image[:, :, i]
            
            channel_moments = [
                float(np.mean(channel)),  # Mean
                float(np.std(channel)),   # Standard deviation
                float(self._calculate_skewness(channel))  # Skewness
            ]
            
            moments[channel_name] = channel_moments
        
        return moments
    
    def get_feature_summary(self, image_path: str) -> Dict[str, Any]:
        """Get summary of extracted features for an image"""
        try:
            all_features = self.extract_all_features(image_path)
            
            summary = {
                "image_path": image_path,
                "extraction_time": datetime.now().isoformat(),
                "feature_types": list(all_features.keys()),
                "total_features": sum(len(feat.features) for feat in all_features.values()),
                "feature_details": {}
            }
            
            for feature_type, extracted_features in all_features.items():
                summary["feature_details"][feature_type.value] = {
                    "count": len(extracted_features.features),
                    "metadata": extracted_features.metadata,
                    "hash": extracted_features.feature_hash
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get feature summary: {str(e)}")
            raise
    
    def export_features(self, image_path: str, output_path: str, format: str = "json"):
        """Export extracted features to file"""
        try:
            all_features = self.extract_all_features(image_path)
            
            if format.lower() == "json":
                # Convert to serializable format
                export_data = {}
                for feature_type, extracted_features in all_features.items():
                    export_data[feature_type.value] = {
                        "feature_id": extracted_features.feature_id,
                        "image_path": extracted_features.image_path,
                        "feature_type": extracted_features.feature_type.value,
                        "features": extracted_features.features,
                        "metadata": extracted_features.metadata,
                        "extraction_time": extracted_features.extraction_time.isoformat(),
                        "feature_hash": extracted_features.feature_hash
                    }
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Flatten features for CSV
                flattened_features = {}
                for feature_type, extracted_features in all_features.items():
                    for key, value in extracted_features.features.items():
                        flattened_features[f"{feature_type.value}_{key}"] = value
                
                df = pd.DataFrame([flattened_features])
                df.to_csv(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Features exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export features: {str(e)}")
            raise

# Utility functions
def create_default_extractor() -> AutomatedFeatureExtractor:
    """Create feature extractor with default configuration"""
    config = FeatureConfig()
    return AutomatedFeatureExtractor(config)

def create_custom_extractor(**kwargs) -> AutomatedFeatureExtractor:
    """Create feature extractor with custom configuration"""
    config = FeatureConfig(**kwargs)
    return AutomatedFeatureExtractor(config)

if __name__ == "__main__":
    # Example usage
    extractor = create_default_extractor()
    
    # Test with sample image
    image_path = "test-food.jpg"
    if os.path.exists(image_path):
        try:
            features = extractor.extract_all_features(image_path)
            print(f"Extracted {len(features)} feature types")
            
            # Get summary
            summary = extractor.get_feature_summary(image_path)
            print(f"Total features: {summary['total_features']}")
            
            # Export features
            extractor.export_features(image_path, "features.json", "json")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print(f"Test image {image_path} not found")
