"""
Optimization Suggester for Real-time Preprocessing

This module provides intelligent preprocessing optimization suggestions based on
image analysis and classification confidence. It helps users find the optimal
preprocessing parameters for better classification results.
"""

import numpy as np
from PIL import Image, ImageStat
from typing import Dict, Any, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# Add src to Python path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.classifier import FlavorSnapClassifier

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of optimization suggestions."""
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    ROTATION = "rotation"
    ASPECT_RATIO = "aspect_ratio"
    CROP = "crop"
    COLOR_BALANCE = "color_balance"


@dataclass
class OptimizationSuggestion:
    """Represents an optimization suggestion."""
    type: OptimizationType
    current_value: Any
    suggested_value: Any
    confidence_improvement: float
    reason: str
    priority: str  # "high", "medium", "low"
    estimated_impact: str  # "significant", "moderate", "minimal"


class ImageAnalyzer:
    """Analyzes images to determine optimization opportunities."""
    
    @staticmethod
    def analyze_brightness(image: Image.Image) -> Dict[str, Any]:
        """Analyze image brightness and distribution."""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Calculate brightness metrics
        mean_brightness = np.mean(img_array) / 255.0
        brightness_std = np.std(img_array) / 255.0
        
        # Calculate histogram
        hist = np.histogram(img_array.flatten(), bins=256, range=(0, 256))[0]
        hist_normalized = hist / hist.sum()
        
        # Calculate dynamic range
        non_zero_pixels = np.count_nonzero(img_array)
        dynamic_range = (np.max(img_array) - np.min(img_array)) / 255.0
        
        # Determine if image is under/over exposed
        if mean_brightness < 0.25:
            exposure_status = "underexposed"
        elif mean_brightness > 0.75:
            exposure_status = "overexposed"
        else:
            exposure_status = "well_exposed"
        
        return {
            'mean_brightness': mean_brightness,
            'brightness_std': brightness_std,
            'dynamic_range': dynamic_range,
            'exposure_status': exposure_status,
            'histogram': hist_normalized,
            'recommendations': {
                'underexposed': 1.3,
                'overexposed': 0.8,
                'well_exposed': 1.0
            }
        }
    
    @staticmethod
    def analyze_contrast(image: Image.Image) -> Dict[str, Any]:
        """Analyze image contrast and edge information."""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # Calculate RMS contrast
        rms_contrast = np.std(img_array) / 255.0
        
        # Calculate edge density using simple gradient
        gray = np.mean(img_array, axis=2)
        grad_x = np.abs(np.diff(gray, axis=1))
        grad_y = np.abs(np.diff(gray, axis=0))
        edge_density = np.mean(grad_x) + np.mean(grad_y)
        
        # Determine contrast quality
        if rms_contrast < 0.15:
            contrast_status = "low_contrast"
        elif rms_contrast > 0.4:
            contrast_status = "high_contrast"
        else:
            contrast_status = "good_contrast"
        
        return {
            'rms_contrast': rms_contrast,
            'edge_density': edge_density,
            'contrast_status': contrast_status,
            'recommendations': {
                'low_contrast': 1.4,
                'high_contrast': 0.9,
                'good_contrast': 1.0
            }
        }
    
    @staticmethod
    def analyze_composition(image: Image.Image) -> Dict[str, Any]:
        """Analyze image composition for cropping and aspect ratio suggestions."""
        width, height = image.size
        aspect_ratio = width / height
        
        # Analyze center of mass
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        gray = np.mean(img_array, axis=2)
        
        # Calculate center of mass
        y_indices, x_indices = np.indices(gray.shape)
        total_mass = np.sum(gray)
        center_x = np.sum(x_indices * gray) / total_mass
        center_y = np.sum(y_indices * gray) / total_mass
        
        # Normalize to image center
        center_x_norm = (center_x - width/2) / (width/2)
        center_y_norm = (center_y - height/2) / (height/2)
        
        # Determine if subject is centered
        subject_centered = abs(center_x_norm) < 0.2 and abs(center_y_norm) < 0.2
        
        # Suggest aspect ratios
        suggested_ratios = []
        if abs(aspect_ratio - 1.0) < 0.1:
            suggested_ratios.append(("1:1", "square"))
        elif abs(aspect_ratio - 4/3) < 0.1:
            suggested_ratios.append(("4:3", "standard"))
        elif abs(aspect_ratio - 16/9) < 0.1:
            suggested_ratios.append(("16:9", "widescreen"))
        else:
            suggested_ratios.extend([
                ("1:1", "square"),
                ("4:3", "standard"),
                ("16:9", "widescreen")
            ])
        
        return {
            'aspect_ratio': aspect_ratio,
            'subject_centered': subject_centered,
            'center_offset': (center_x_norm, center_y_norm),
            'suggested_ratios': suggested_ratios,
            'composition_score': 1.0 - (abs(center_x_norm) + abs(center_y_norm)) / 2
        }
    
    @staticmethod
    def analyze_color_balance(image: Image.Image) -> Dict[str, Any]:
        """Analyze color balance and saturation."""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # Calculate channel statistics
        r_mean = np.mean(img_array[:, :, 0]) / 255.0
        g_mean = np.mean(img_array[:, :, 1]) / 255.0
        b_mean = np.mean(img_array[:, :, 2]) / 255.0
        
        # Calculate color cast
        gray_mean = (r_mean + g_mean + b_mean) / 3
        r_cast = r_mean - gray_mean
        g_cast = g_mean - gray_mean
        b_cast = b_mean - gray_mean
        
        # Calculate saturation
        max_channel = np.max(img_array, axis=2) / 255.0
        min_channel = np.min(img_array, axis=2) / 255.0
        saturation = np.mean(max_channel - min_channel)
        
        # Determine color balance status
        max_cast = max(abs(r_cast), abs(g_cast), abs(b_cast))
        if max_cast > 0.1:
            color_status = "color_cast"
        else:
            color_status = "balanced"
        
        return {
            'channel_means': (r_mean, g_mean, b_mean),
            'color_cast': (r_cast, g_cast, b_cast),
            'saturation': saturation,
            'color_status': color_status,
            'dominant_channel': np.argmax([abs(r_cast), abs(g_cast), abs(b_cast)])
        }


class OptimizationSuggester:
    """
    Main optimization suggester that combines image analysis with
    classification confidence to provide preprocessing suggestions.
    """
    
    def __init__(self, classifier: Optional[FlavorSnapClassifier] = None):
        """
        Initialize the optimization suggester.
        
        Args:
            classifier: Optional classifier for confidence-based optimization
        """
        self.classifier = classifier or FlavorSnapClassifier()
        self.analyzer = ImageAnalyzer()
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Optimization weights for different factors
        self.weights = {
            'brightness': 0.3,
            'contrast': 0.25,
            'composition': 0.2,
            'color_balance': 0.15,
            'confidence': 0.1
        }
    
    def get_optimization_suggestions(self, 
                                    image: Image.Image,
                                    current_params: Optional[Dict[str, Any]] = None,
                                    current_confidence: Optional[float] = None) -> List[OptimizationSuggestion]:
        """
        Get optimization suggestions for an image.
        
        Args:
            image: PIL Image to analyze
            current_params: Current preprocessing parameters
            current_confidence: Current classification confidence
            
        Returns:
            List of optimization suggestions
        """
        current_params = current_params or {}
        suggestions = []
        
        # Analyze image properties
        brightness_analysis = self.analyzer.analyze_brightness(image)
        contrast_analysis = self.analyzer.analyze_contrast(image)
        composition_analysis = self.analyzer.analyze_composition(image)
        color_analysis = self.analyzer.analyze_color_balance(image)
        
        # Generate brightness suggestions
        brightness_suggestion = self._suggest_brightness_optimization(
            brightness_analysis, current_params
        )
        if brightness_suggestion:
            suggestions.append(brightness_suggestion)
        
        # Generate contrast suggestions
        contrast_suggestion = self._suggest_contrast_optimization(
            contrast_analysis, current_params
        )
        if contrast_suggestion:
            suggestions.append(contrast_suggestion)
        
        # Generate composition suggestions
        composition_suggestion = self._suggest_composition_optimization(
            composition_analysis, current_params
        )
        if composition_suggestion:
            suggestions.append(composition_suggestion)
        
        # Generate color balance suggestions
        color_suggestion = self._suggest_color_optimization(
            color_analysis, current_params
        )
        if color_suggestion:
            suggestions.append(color_suggestion)
        
        # If confidence is low, suggest more aggressive optimizations
        if current_confidence and current_confidence < 0.7:
            confidence_suggestions = self._suggest_confidence_improvements(
                current_confidence, suggestions
            )
            suggestions.extend(confidence_suggestions)
        
        # Sort suggestions by priority and impact
        suggestions.sort(key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}[x.priority],
            {'significant': 0, 'moderate': 1, 'minimal': 2}[x.estimated_impact]
        ))
        
        return suggestions
    
    def _suggest_brightness_optimization(self, 
                                       analysis: Dict[str, Any],
                                       current_params: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        """Suggest brightness optimization."""
        current_brightness = current_params.get('brightness', 1.0)
        exposure_status = analysis['exposure_status']
        
        if exposure_status == 'well_exposed':
            return None
        
        suggested_brightness = analysis['recommendations'][exposure_status]
        
        # Calculate estimated improvement
        if abs(suggested_brightness - current_brightness) < 0.1:
            return None
        
        confidence_improvement = min(0.15, abs(suggested_brightness - current_brightness) * 0.2)
        
        return OptimizationSuggestion(
            type=OptimizationType.BRIGHTNESS,
            current_value=current_brightness,
            suggested_value=suggested_brightness,
            confidence_improvement=confidence_improvement,
            reason=f"Image appears {exposure_status.replace('_', ' ')}",
            priority="high" if exposure_status in ["underexposed", "overexposed"] else "medium",
            estimated_impact="significant" if abs(suggested_brightness - current_brightness) > 0.3 else "moderate"
        )
    
    def _suggest_contrast_optimization(self, 
                                      analysis: Dict[str, Any],
                                      current_params: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        """Suggest contrast optimization."""
        current_contrast = current_params.get('contrast', 1.0)
        contrast_status = analysis['contrast_status']
        
        if contrast_status == 'good_contrast':
            return None
        
        suggested_contrast = analysis['recommendations'][contrast_status]
        
        if abs(suggested_contrast - current_contrast) < 0.1:
            return None
        
        confidence_improvement = min(0.12, abs(suggested_contrast - current_contrast) * 0.15)
        
        return OptimizationSuggestion(
            type=OptimizationType.CONTRAST,
            current_value=current_contrast,
            suggested_value=suggested_contrast,
            confidence_improvement=confidence_improvement,
            reason=f"Image has {contrast_status.replace('_', ' ')}",
            priority="medium",
            estimated_impact="moderate"
        )
    
    def _suggest_composition_optimization(self, 
                                        analysis: Dict[str, Any],
                                        current_params: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        """Suggest composition optimization."""
        current_aspect_ratio = current_params.get('aspect_ratio', 'Original')
        
        if current_aspect_ratio != 'Original':
            return None
        
        # Suggest best aspect ratio based on composition
        if not analysis['subject_centered']:
            # Suggest cropping to center the subject
            return OptimizationSuggestion(
                type=OptimizationType.CROP,
                current_value="No crop",
                suggested_value="Center crop",
                confidence_improvement=0.08,
                reason="Subject appears off-center",
                priority="medium",
                estimated_impact="moderate"
            )
        
        return None
    
    def _suggest_color_optimization(self, 
                                   analysis: Dict[str, Any],
                                   current_params: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        """Suggest color optimization."""
        if analysis['color_status'] == 'balanced':
            return None
        
        # For now, we'll keep it simple and just suggest general color balance
        return OptimizationSuggestion(
            type=OptimizationType.COLOR_BALANCE,
            current_value="Current",
            suggested_value="Auto color balance",
            confidence_improvement=0.05,
            reason=f"Image has {analysis['color_status'].replace('_', ' ')}",
            priority="low",
            estimated_impact="minimal"
        )
    
    def _suggest_confidence_improvements(self, 
                                       confidence: float,
                                       existing_suggestions: List[OptimizationSuggestion]) -> List[OptimizationSuggestion]:
        """Suggest additional improvements for low confidence."""
        suggestions = []
        
        if confidence < 0.5:
            # Very low confidence - suggest more aggressive changes
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.BRIGHTNESS,
                current_value="Current",
                suggested_value="Auto enhance",
                confidence_improvement=0.2,
                reason="Very low confidence - try auto enhancement",
                priority="high",
                estimated_impact="significant"
            ))
        
        elif confidence < 0.7:
            # Low confidence - suggest rotation adjustment
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.ROTATION,
                current_value=0.0,
                suggested_value="Auto-rotate",
                confidence_improvement=0.1,
                reason="Low confidence - check image orientation",
                priority="medium",
                estimated_impact="moderate"
            ))
        
        return suggestions
    
    def apply_suggestion(self, 
                         image: Image.Image, 
                         suggestion: OptimizationSuggestion) -> Image.Image:
        """Apply an optimization suggestion to an image."""
        # This would integrate with the image enhancer
        # For now, return the original image
        return image
    
    def get_optimization_summary(self, suggestions: List[OptimizationSuggestion]) -> Dict[str, Any]:
        """Get a summary of optimization suggestions."""
        if not suggestions:
            return {
                'total_suggestions': 0,
                'high_priority': 0,
                'estimated_improvement': 0.0,
                'summary': "No optimizations needed"
            }
        
        high_priority = sum(1 for s in suggestions if s.priority == 'high')
        total_improvement = sum(s.confidence_improvement for s in suggestions)
        
        # Generate summary text
        if high_priority > 0:
            summary = f"{high_priority} high-priority optimizations available"
        else:
            summary = f"{len(suggestions)} minor improvements suggested"
        
        return {
            'total_suggestions': len(suggestions),
            'high_priority': high_priority,
            'estimated_improvement': min(0.5, total_improvement),  # Cap at 50%
            'summary': summary,
            'types': list(set(s.type.value for s in suggestions))
        }


# Convenience function for quick optimization suggestions
def get_optimization_suggestions(image: Image.Image, 
                               current_params: Optional[Dict[str, Any]] = None,
                               current_confidence: Optional[float] = None) -> List[OptimizationSuggestion]:
    """
    Get optimization suggestions for an image.
    
    Args:
        image: PIL Image to analyze
        current_params: Current preprocessing parameters
        current_confidence: Current classification confidence
        
    Returns:
        List of optimization suggestions
    """
    suggester = OptimizationSuggester()
    return suggester.get_optimization_suggestions(image, current_params, current_confidence)
