"""
Image Optimization and Processing Module
Provides advanced image optimization, validation, and security features
"""

import io
import os
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image, ImageEnhance, ImageFilter
import pillow_heif
from dataclasses import dataclass
from enum import Enum
import logging
import tempfile
from pathlib import Path
import magic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"
    GIF = "GIF"

@dataclass
class OptimizationResult:
    """Result of image optimization"""
    success: bool
    original_size: int
    optimized_size: int
    compression_ratio: float
    format: str
    dimensions: Tuple[int, int]
    processing_time: float
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

class ImageOptimizer:
    """Advanced image optimization and processing"""
    
    def __init__(self):
        self.max_dimension = 2048
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.quality_jpeg = 85
        self.quality_webp = 80
        self.png_compression = 6
        
        # Register HEIF support
        pillow_heif.register_heif_opener()
        
        # Supported formats and their MIME types
        self.format_mapping = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'WEBP': 'image/webp',
            'GIF': 'image/gif'
        }
        
        # Optimization presets
        self.presets = {
            'web': {'max_dimension': 1920, 'quality_jpeg': 80, 'quality_webp': 75},
            'mobile': {'max_dimension': 1280, 'quality_jpeg': 75, 'quality_webp': 70},
            'thumbnail': {'max_dimension': 300, 'quality_jpeg': 70, 'quality_webp': 65},
            'high_quality': {'max_dimension': 4096, 'quality_jpeg': 95, 'quality_webp': 90}
        }
    
    def optimize_image(self, image_data: bytes, output_format: str = 'JPEG', 
                      preset: str = 'web', custom_settings: Dict = None) -> OptimizationResult:
        """
        Optimize image with advanced processing
        
        Args:
            image_data: Raw image bytes
            output_format: Target format (JPEG, PNG, WEBP)
            preset: Optimization preset (web, mobile, thumbnail, high_quality)
            custom_settings: Custom optimization settings
        
        Returns:
            OptimizationResult with details
        """
        import time
        start_time = time.time()
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Load image
            image, original_format = self._load_image(image_data)
            if not image:
                errors.append("Failed to load image")
                return OptimizationResult(False, 0, 0, 0, '', (0, 0), 0, errors, warnings, metadata)
            
            original_size = len(image_data)
            metadata['original_format'] = original_format
            metadata['original_dimensions'] = image.size
            
            # Apply preset settings
            settings = self.presets.get(preset, self.presets['web'])
            if custom_settings:
                settings.update(custom_settings)
            
            # Resize if needed
            image, resize_info = self._resize_image(image, settings['max_dimension'])
            metadata['resize_info'] = resize_info
            
            # Apply enhancements
            image, enhancement_info = self._apply_enhancements(image)
            metadata['enhancement_info'] = enhancement_info
            
            # Convert format if needed
            if output_format != original_format:
                image, conversion_info = self._convert_format(image, output_format)
                metadata['conversion_info'] = conversion_info
            
            # Optimize and save
            optimized_data = self._save_optimized(image, output_format, settings)
            optimized_size = len(optimized_data)
            
            # Calculate metrics
            compression_ratio = (original_size - optimized_size) / original_size if original_size > 0 else 0
            processing_time = time.time() - start_time
            
            # Generate metadata
            metadata['optimization_settings'] = settings
            metadata['file_hash'] = hashlib.md5(optimized_data).hexdigest()
            
            # Store optimized data for retrieval
            metadata['optimized_data'] = optimized_data
            
            return OptimizationResult(
                success=True,
                original_size=original_size,
                optimized_size=optimized_size,
                compression_ratio=compression_ratio,
                format=output_format,
                dimensions=image.size,
                processing_time=processing_time,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            errors.append(f"Optimization failed: {str(e)}")
            processing_time = time.time() - start_time
            
            return OptimizationResult(
                success=False,
                original_size=len(image_data) if image_data else 0,
                optimized_size=0,
                compression_ratio=0,
                format='',
                dimensions=(0, 0),
                processing_time=processing_time,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
    
    def _load_image(self, image_data: bytes) -> Tuple[Optional[Image.Image], str]:
        """Load image from bytes and detect format"""
        try:
            # Detect format using python-magic
            detected_mime = magic.from_buffer(image_data, mime=True)
            
            # Map MIME to PIL format
            format_mapping = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/webp': 'WEBP',
                'image/gif': 'GIF',
                'image/heif': 'HEIF',
                'image/heic': 'HEIC'
            }
            
            pil_format = format_mapping.get(detected_mime, 'JPEG')
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if pil_format in ['JPEG', 'WEBP'] and image.mode in ['RGBA', 'LA', 'P']:
                image = image.convert('RGB')
            
            return image, pil_format
            
        except Exception as e:
            logger.error(f"Failed to load image: {str(e)}")
            return None, ''
    
    def _resize_image(self, image: Image.Image, max_dimension: int) -> Tuple[Image.Image, Dict]:
        """Resize image if it exceeds maximum dimensions"""
        resize_info = {'original_size': image.size, 'resized': False}
        
        width, height = image.size
        max_dim = max(width, height)
        
        if max_dim > max_dimension:
            # Calculate new dimensions
            ratio = max_dimension / max_dim
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # Resize with high-quality resampling
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            resize_info.update({
                'new_size': (new_width, new_height),
                'resized': True,
                'ratio': ratio
            })
        
        return image, resize_info
    
    def _apply_enhancements(self, image: Image.Image) -> Tuple[Image.Image, Dict]:
        """Apply automatic image enhancements"""
        enhancement_info = {'enhancements_applied': []}
        
        try:
            # Auto-contrast adjustment
            if image.mode in ['RGB', 'L']:
                enhancer = ImageEnhance.Contrast(image)
                contrast_factor = 1.1  # Slight contrast boost
                image = enhancer.enhance(contrast_factor)
                enhancement_info['enhancements_applied'].append('contrast')
                enhancement_info['contrast_factor'] = contrast_factor
            
            # Sharpness enhancement
            enhancer = ImageEnhance.Sharpness(image)
            sharpness_factor = 1.05  # Slight sharpening
            image = enhancer.enhance(sharpness_factor)
            enhancement_info['enhancements_applied'].append('sharpness')
            enhancement_info['sharpness_factor'] = sharpness_factor
            
            # Color enhancement (subtle)
            if image.mode == 'RGB':
                enhancer = ImageEnhance.Color(image)
                color_factor = 1.02  # Very subtle color boost
                image = enhancer.enhance(color_factor)
                enhancement_info['enhancements_applied'].append('color')
                enhancement_info['color_factor'] = color_factor
        
        except Exception as e:
            logger.warning(f"Enhancement failed: {str(e)}")
        
        return image, enhancement_info
    
    def _convert_format(self, image: Image.Image, target_format: str) -> Tuple[Image.Image, Dict]:
        """Convert image to target format"""
        conversion_info = {'original_format': image.format, 'target_format': target_format}
        
        try:
            # Handle format-specific conversions
            if target_format == 'JPEG' and image.mode in ['RGBA', 'LA', 'P']:
                # Convert to RGB for JPEG
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
                conversion_info['mode_conversion'] = f"{image.mode} -> RGB"
            
            elif target_format == 'PNG' and image.mode not in ['RGBA', 'RGB', 'L', 'P']:
                # Convert to RGBA for PNG
                image = image.convert('RGBA')
                conversion_info['mode_conversion'] = f"{image.mode} -> RGBA"
            
            elif target_format == 'WEBP' and image.mode in ['RGBA', 'LA', 'P']:
                # Convert to RGB for WEBP
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
                conversion_info['mode_conversion'] = f"{image.mode} -> RGB"
        
        except Exception as e:
            logger.warning(f"Format conversion failed: {str(e)}")
        
        return image, conversion_info
    
    def _save_optimized(self, image: Image.Image, format: str, settings: Dict) -> bytes:
        """Save optimized image to bytes"""
        output = io.BytesIO()
        
        save_kwargs = {}
        
        if format == 'JPEG':
            save_kwargs.update({
                'format': 'JPEG',
                'quality': settings.get('quality_jpeg', self.quality_jpeg),
                'optimize': True,
                'progressive': True
            })
        
        elif format == 'PNG':
            save_kwargs.update({
                'format': 'PNG',
                'compress_level': settings.get('png_compression', self.png_compression),
                'optimize': True
            })
        
        elif format == 'WEBP':
            save_kwargs.update({
                'format': 'WEBP',
                'quality': settings.get('quality_webp', self.quality_webp),
                'optimize': True,
                'method': 6  # Best compression
            })
        
        elif format == 'GIF':
            save_kwargs.update({
                'format': 'GIF',
                'optimize': True
            })
        
        image.save(output, **save_kwargs)
        return output.getvalue()
    
    def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """Get comprehensive image information"""
        try:
            image, format_type = self._load_image(image_data)
            if not image:
                return {'error': 'Failed to load image'}
            
            # Basic info
            info = {
                'format': format_type,
                'mode': image.mode,
                'size': image.size,
                'has_transparency': image.mode in ['RGBA', 'LA'] or 'transparency' in image.info,
                'file_size': len(image_data),
                'aspect_ratio': image.size[0] / image.size[1] if image.size[1] > 0 else 0
            }
            
            # EXIF data for JPEG
            if format_type == 'JPEG':
                try:
                    exif = image._getexif()
                    if exif:
                        from PIL.ExifTags import TAGS
                        exif_data = {}
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_data[tag] = value
                        info['exif'] = exif_data
                except:
                    pass
            
            # Color analysis
            if image.mode == 'RGB':
                colors = image.getcolors(maxcolors=256*256*256)
                if colors:
                    info['unique_colors'] = len(colors)
                    info['dominant_color'] = colors[0][1] if colors else None
            
            return info
            
        except Exception as e:
            return {'error': f'Failed to analyze image: {str(e)}'}
    
    def create_thumbnail(self, image_data: bytes, size: Tuple[int, int] = (150, 150), 
                        crop_to_fit: bool = True) -> bytes:
        """Create thumbnail from image"""
        try:
            image, _ = self._load_image(image_data)
            if not image:
                raise ValueError("Failed to load image")
            
            if crop_to_fit:
                # Crop to fit the aspect ratio
                target_width, target_height = size
                original_width, original_height = image.size
                
                # Calculate crop dimensions
                aspect_ratio = target_width / target_height
                original_aspect = original_width / original_height
                
                if original_aspect > aspect_ratio:
                    # Image is wider, crop sides
                    new_width = int(original_height * aspect_ratio)
                    left = (original_width - new_width) // 2
                    image = image.crop((left, 0, left + new_width, original_height))
                else:
                    # Image is taller, crop top/bottom
                    new_height = int(original_width / aspect_ratio)
                    top = (original_height - new_height) // 2
                    image = image.crop((0, top, original_width, top + new_height))
            
            # Resize to target size
            image = image.resize(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {str(e)}")
            raise
    
    def batch_optimize(self, images_data: List[bytes], **kwargs) -> List[OptimizationResult]:
        """Optimize multiple images"""
        results = []
        for i, image_data in enumerate(images_data):
            result = self.optimize_image(image_data, **kwargs)
            result.metadata['batch_index'] = i
            results.append(result)
        return results
    
    def get_optimization_suggestions(self, image_data: bytes) -> Dict[str, Any]:
        """Get optimization suggestions for an image"""
        try:
            info = self.get_image_info(image_data)
            suggestions = []
            
            # Size suggestions
            if info.get('file_size', 0) > 5 * 1024 * 1024:  # 5MB
                suggestions.append({
                    'type': 'size',
                    'message': 'Large file size detected, consider compression',
                    'priority': 'high'
                })
            
            # Dimension suggestions
            size = info.get('size', (0, 0))
            if max(size) > 2048:
                suggestions.append({
                    'type': 'dimensions',
                    'message': 'Large dimensions detected, consider resizing',
                    'priority': 'medium'
                })
            
            # Format suggestions
            format_type = info.get('format', '')
            if format_type == 'PNG' and info.get('file_size', 0) > 1024 * 1024:  # 1MB
                suggestions.append({
                    'type': 'format',
                    'message': 'Large PNG file, consider converting to JPEG or WEBP',
                    'priority': 'medium'
                })
            
            return {
                'image_info': info,
                'suggestions': suggestions,
                'recommended_preset': self._recommend_preset(info)
            }
            
        except Exception as e:
            return {'error': f'Failed to generate suggestions: {str(e)}'}
    
    def _recommend_preset(self, image_info: Dict) -> str:
        """Recommend optimization preset based on image characteristics"""
        file_size = image_info.get('file_size', 0)
        dimensions = image_info.get('size', (0, 0))
        max_dim = max(dimensions)
        
        if max_dim > 3000 or file_size > 8 * 1024 * 1024:
            return 'web'
        elif max_dim > 1500 or file_size > 3 * 1024 * 1024:
            return 'mobile'
        elif max_dim < 500:
            return 'thumbnail'
        else:
            return 'high_quality'

# Utility functions
def create_image_variants(image_data: bytes) -> Dict[str, bytes]:
    """Create multiple optimized variants of an image"""
    optimizer = ImageOptimizer()
    variants = {}
    
    # Original
    variants['original'] = image_data
    
    # Web optimized
    web_result = optimizer.optimize_image(image_data, output_format='JPEG', preset='web')
    if web_result.success:
        variants['web'] = web_result.metadata['optimized_data']
    
    # Mobile optimized
    mobile_result = optimizer.optimize_image(image_data, output_format='WEBP', preset='mobile')
    if mobile_result.success:
        variants['mobile'] = mobile_result.metadata['optimized_data']
    
    # Thumbnail
    try:
        variants['thumbnail'] = optimizer.create_thumbnail(image_data)
    except:
        pass
    
    return variants

def validate_image_processing_chain(image_data: bytes) -> Dict[str, Any]:
    """Validate the entire image processing chain"""
    optimizer = ImageOptimizer()
    validation_results = {
        'loading': False,
        'optimization': False,
        'thumbnail_creation': False,
        'info_extraction': False,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Test loading
        image, _ = optimizer._load_image(image_data)
        if image:
            validation_results['loading'] = True
        else:
            validation_results['errors'].append('Failed to load image')
            return validation_results
        
        # Test optimization
        result = optimizer.optimize_image(image_data)
        if result.success:
            validation_results['optimization'] = True
        else:
            validation_results['errors'].extend(result.errors)
        
        # Test thumbnail creation
        try:
            thumbnail = optimizer.create_thumbnail(image_data)
            if thumbnail:
                validation_results['thumbnail_creation'] = True
        except Exception as e:
            validation_results['errors'].append(f'Thumbnail creation failed: {str(e)}')
        
        # Test info extraction
        info = optimizer.get_image_info(image_data)
        if 'error' not in info:
            validation_results['info_extraction'] = True
        else:
            validation_results['errors'].append(f'Info extraction failed: {info["error"]}')
        
        return validation_results
        
    except Exception as e:
        validation_results['errors'].append(f'Validation failed: {str(e)}')
        return validation_results
