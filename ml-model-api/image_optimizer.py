"""
Server-side Image Optimization Module

Handles image compression, format conversion (WebP), and responsive image
generation using Pillow to optimize images for web delivery and reduce
bandwidth usage in the ML API.
"""

import os
import io
import logging
from typing import Dict, Tuple, Optional, BinaryIO, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from PIL import Image, ImageOps
import hashlib

logger = logging.getLogger(__name__)


class ImageFormat(Enum):
    """Supported image output formats"""
    WEBP = "webp"
    JPEG = "jpeg"
    PNG = "png"


@dataclass
class OptimizationMetadata:
    """Metadata about optimized image"""
    original_size: int
    optimized_size: int
    compression_ratio: float
    source_format: str
    target_format: str
    original_dimensions: Tuple[int, int]
    optimized_dimensions: Tuple[int, int]
    processing_time: float
    file_hash: str


class ImageOptimizer:
    """Handles image optimization operations"""

    # Default compression quality levels
    QUALITY_LEVELS = {
        "low": 60,
        "medium": 75,
        "high": 85,
        "maximum": 95,
    }

    # Thumbnail sizes (pixels)
    THUMBNAIL_SIZES = {
        "small": 256,
        "medium": 512,
        "large": 1024,
    }

    # Maximum dimensions
    DEFAULT_MAX_WIDTH = 1920
    DEFAULT_MAX_HEIGHT = 1080

    @staticmethod
    def calculate_dimensions(
        original_width: int,
        original_height: int,
        max_width: int = DEFAULT_MAX_WIDTH,
        max_height: int = DEFAULT_MAX_HEIGHT,
        preserve_aspect: bool = True,
    ) -> Tuple[int, int]:
        """
        Calculate new dimensions preserving aspect ratio
        
        Args:
            original_width: Original image width
            original_height: Original image height
            max_width: Maximum allowed width
            max_height: Maximum allowed height
            preserve_aspect: Whether to preserve aspect ratio
            
        Returns:
            Tuple of (width, height)
        """
        if not preserve_aspect:
            return (max_width, max_height)

        width = original_width
        height = original_height

        # Scale if width exceeds maximum
        if width > max_width:
            height = int((max_width / width) * height)
            width = max_width

        # Scale if height still exceeds maximum
        if height > max_height:
            width = int((max_height / height) * width)
            height = max_height

        return (width, height)

    @staticmethod
    def get_file_hash(file_data: bytes) -> str:
        """Generate SHA256 hash of file"""
        return hashlib.sha256(file_data).hexdigest()[:16]

    @staticmethod
    def open_image(file_obj: BinaryIO) -> Image.Image:
        """
        Open image from file object
        
        Args:
            file_obj: File-like object containing image
            
        Returns:
            PIL Image object
            
        Raises:
            ValueError: If image format is unsupported
        """
        try:
            image = Image.open(file_obj)
            # Validate image
            image.verify()
            # Reopen after verify closes it
            file_obj.seek(0)
            image = Image.open(file_obj)
            return image
        except Exception as e:
            logger.error(f"Failed to open image: {str(e)}")
            raise ValueError(f"Invalid or corrupted image: {str(e)}")

    @staticmethod
    def convert_rgba_to_rgb(image: Image.Image) -> Image.Image:
        """
        Convert RGBA images to RGB for JPEG compatibility
        
        Args:
            image: PIL Image object
            
        Returns:
            RGB Image object
        """
        if image.mode in ("RGBA", "LA", "P"):
            # Create white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            return background
        return image

    @staticmethod
    def validate_and_fix_orientation(image: Image.Image) -> Image.Image:
        """
        Fix image orientation based on EXIF data
        
        Args:
            image: PIL Image object
            
        Returns:
            Corrected Image object
        """
        try:
            # Attempt to use PIL's ImageOps.exif_transpose if available
            return ImageOps.exif_transpose(image)
        except Exception as e:
            logger.warning(f"Failed to apply EXIF orientation: {str(e)}")
            return image

    def compress_image(
        self,
        image: Image.Image,
        quality: str = "high",
        target_format: ImageFormat = ImageFormat.WEBP,
        max_width: int = DEFAULT_MAX_WIDTH,
        max_height: int = DEFAULT_MAX_HEIGHT,
    ) -> Tuple[io.BytesIO, Tuple[int, int]]:
        """
        Compress and optimize image
        
        Args:
            image: PIL Image object
            quality: Quality level ('low', 'medium', 'high', 'maximum')
            target_format: Output format
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Tuple of (BytesIO object, new dimensions)
        """
        # Fix orientation
        image = self.validate_and_fix_orientation(image)

        # Get original dimensions
        original_width, original_height = image.size

        # Calculate new dimensions
        new_width, new_height = self.calculate_dimensions(
            original_width, original_height, max_width, max_height
        )

        # Resize if necessary
        if (new_width, new_height) != (original_width, original_height):
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert RGBA to RGB for JPEG
        if target_format == ImageFormat.JPEG:
            image = self.convert_rgba_to_rgb(image)

        # Get quality level
        quality_value = self.QUALITY_LEVELS.get(quality, self.QUALITY_LEVELS["high"])

        # Compress
        output = io.BytesIO()
        save_kwargs: Dict[str, Any] = {
            "format": target_format.value.upper(),
            "quality": quality_value,
            "optimize": True,
        }

        # WebP supports lossless option
        if target_format == ImageFormat.WEBP:
            save_kwargs["method"] = 6  # Slowest/best quality

        image.save(output, **save_kwargs)
        output.seek(0)

        return output, (new_width, new_height)

    def generate_thumbnail(
        self,
        image: Image.Image,
        size: int,
        quality: str = "medium",
    ) -> io.BytesIO:
        """
        Generate thumbnail of specified size
        
        Args:
            image: PIL Image object
            size: Target size (maintains aspect ratio)
            quality: Quality level
            
        Returns:
            BytesIO object containing thumbnail
        """
        # Create thumbnail (maintains aspect ratio)
        image_copy = image.copy()
        image_copy.thumbnail((size, size), Image.Resampling.LANCZOS)

        output = io.BytesIO()
        quality_value = self.QUALITY_LEVELS.get(quality, self.QUALITY_LEVELS["medium"])

        image_copy.save(output, format="JPEG", quality=quality_value, optimize=True)
        output.seek(0)

        return output

    def optimize_image(
        self,
        file_obj: BinaryIO,
        quality: str = "high",
        generate_webp: bool = True,
        generate_thumbnails: bool = True,
        max_width: int = DEFAULT_MAX_WIDTH,
        max_height: int = DEFAULT_MAX_HEIGHT,
    ) -> Dict[str, Any]:
        """
        Complete image optimization pipeline
        
        Args:
            file_obj: Input file object
            quality: Quality level
            generate_webp: Whether to generate WebP version
            generate_thumbnails: Whether to generate thumbnails
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Dictionary with optimization results
        """
        import time

        start_time = time.time()
        
        # Read file into memory to get size and hash
        file_obj.seek(0)
        file_data = file_obj.read()
        file_size = len(file_data)
        file_hash = self.get_file_hash(file_data)

        # Open image
        file_obj.seek(0)
        image = self.open_image(file_obj)
        original_format = image.format or "UNKNOWN"
        original_dimensions = image.size

        # Compress to main format (WebP)
        optimized_webp, optimized_dims = self.compress_image(
            image.copy(),
            quality=quality,
            target_format=ImageFormat.WEBP,
            max_width=max_width,
            max_height=max_height,
        )

        result = {
            "original": {
                "size": file_size,
                "format": original_format,
                "dimensions": original_dimensions,
                "data": io.BytesIO(file_data),
            },
            "optimized": {
                "size": optimized_webp.getbuffer().nbytes,
                "format": "WebP",
                "dimensions": optimized_dims,
                "data": optimized_webp,
            },
            "metadata": {
                "original_size": file_size,
                "optimized_size": optimized_webp.getbuffer().nbytes,
                "compression_ratio": round(
                    (optimized_webp.getbuffer().nbytes / file_size) * 100, 2
                ),
                "source_format": original_format,
                "target_format": "WebP",
                "original_dimensions": original_dimensions,
                "optimized_dimensions": optimized_dims,
                "file_hash": file_hash,
                "processing_time": time.time() - start_time,
            },
        }

        # Generate JPEG fallback
        jpeg_output, _ = self.compress_image(
            image.copy(),
            quality=quality,
            target_format=ImageFormat.JPEG,
            max_width=max_width,
            max_height=max_height,
        )
        result["jpeg_fallback"] = {
            "size": jpeg_output.getbuffer().nbytes,
            "format": "JPEG",
            "data": jpeg_output,
        }

        # Generate thumbnails
        if generate_thumbnails:
            thumbnails = {}
            for thumb_name, thumb_size in self.THUMBNAIL_SIZES.items():
                thumb_data = self.generate_thumbnail(
                    image.copy(), thumb_size, quality="medium"
                )
                thumbnails[thumb_name] = {
                    "size": thumb_data.getbuffer().nbytes,
                    "dimensions": (
                        min(thumb_size, original_dimensions[0]),
                        min(thumb_size, original_dimensions[1]),
                    ),
                    "data": thumb_data,
                }
            result["thumbnails"] = thumbnails

        logger.info(
            f"Image optimization complete: {file_size}B -> "
            f"{result['optimized']['size']}B "
            f"({result['metadata']['compression_ratio']}%) in "
            f"{result['metadata']['processing_time']:.2f}s"
        )

        return result

    def save_optimized_images(
        self,
        optimization_result: Dict[str, Any],
        output_dir: str,
        base_filename: str,
    ) -> Dict[str, str]:
        """
        Save optimized images to disk
        
        Args:
            optimization_result: Result from optimize_image
            output_dir: Output directory path
            base_filename: Base filename without extension
            
        Returns:
            Dictionary mapping format names to file paths
        """
        os.makedirs(output_dir, exist_ok=True)

        saved_paths = {}

        # Save optimized WebP
        webp_path = os.path.join(output_dir, f"{base_filename}.webp")
        with open(webp_path, "wb") as f:
            optimization_result["optimized"]["data"].seek(0)
            f.write(optimization_result["optimized"]["data"].read())
        saved_paths["webp"] = webp_path

        # Save JPEG fallback
        jpeg_path = os.path.join(output_dir, f"{base_filename}_fallback.jpg")
        with open(jpeg_path, "wb") as f:
            optimization_result["jpeg_fallback"]["data"].seek(0)
            f.write(optimization_result["jpeg_fallback"]["data"].read())
        saved_paths["jpeg"] = jpeg_path

        # Save thumbnails
        if "thumbnails" in optimization_result:
            for thumb_name, thumb_data in optimization_result["thumbnails"].items():
                thumb_path = os.path.join(
                    output_dir, f"{base_filename}_thumb_{thumb_name}.jpg"
                )
                with open(thumb_path, "wb") as f:
                    thumb_data["data"].seek(0)
                    f.write(thumb_data["data"].read())
                saved_paths[f"thumb_{thumb_name}"] = thumb_path

        logger.info(f"Saved optimized images to {output_dir}")
        return saved_paths


# Global optimizer instance
_optimizer: Optional[ImageOptimizer] = None


def get_image_optimizer() -> ImageOptimizer:
    """Get or create global image optimizer instance"""
    global _optimizer
    if _optimizer is None:
        _optimizer = ImageOptimizer()
    return _optimizer
