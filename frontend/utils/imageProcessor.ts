/**
 * Client-side Image Optimization Pipeline
 * 
 * Handles image compression, format conversion (WebP), and responsive image generation
 * to optimize images for web delivery and reduce upload times/bandwidth.
 */

export interface OptimizedImage {
  original: Blob;
  optimized: Blob;
  webp?: Blob;
  compressed: Blob;
  thumbnails: {
    small: Blob;    // 256px
    medium: Blob;   // 512px
    large: Blob;    // 1024px
  };
  metadata: {
    originalSize: number;
    optimizedSize: number;
    compressionRatio: number;
    format: string;
    dimensions: {
      width: number;
      height: number;
    };
    optimizedDimensions: {
      width: number;
      height: number;
    };
  };
}

export interface ImageOptimizationOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
  targetFormat?: 'webp' | 'jpeg' | 'png';
  preserveAspectRatio?: boolean;
  generateThumbnails?: boolean;
  generateWebP?: boolean;
}

const DEFAULT_OPTIONS: ImageOptimizationOptions = {
  maxWidth: 1920,
  maxHeight: 1080,
  quality: 0.8,
  targetFormat: 'webp',
  preserveAspectRatio: true,
  generateThumbnails: true,
  generateWebP: true,
};

/**
 * Validate image file before processing
 */
export const validateImageFile = (
  file: File,
  maxSize: number = 10 * 1024 * 1024 // 10MB
): { valid: boolean; error?: string } => {
  const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

  if (!validTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Invalid image format. Supported: ${validTypes.join(', ')}`,
    };
  }

  if (file.size > maxSize) {
    return {
      valid: false,
      error: `Image size exceeds ${maxSize / 1024 / 1024}MB limit`,
    };
  }

  return { valid: true };
};

/**
 * Get image dimensions
 */
export const getImageDimensions = (
  image: HTMLImageElement
): { width: number; height: number } => {
  return {
    width: image.naturalWidth || image.width,
    height: image.naturalHeight || image.height,
  };
};

/**
 * Calculate new dimensions preserving aspect ratio
 */
export const calculateDimensions = (
  originalWidth: number,
  originalHeight: number,
  maxWidth: number,
  maxHeight: number
): { width: number; height: number } => {
  let width = originalWidth;
  let height = originalHeight;

  if (width > maxWidth) {
    height = Math.round((maxWidth / width) * height);
    width = maxWidth;
  }

  if (height > maxHeight) {
    width = Math.round((maxHeight / height) * width);
    height = maxHeight;
  }

  return { width, height };
};

/**
 * Convert File to canvas for processing
 */
const fileToCanvas = (file: File): Promise<HTMLCanvasElement> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Failed to get 2D context'));
          return;
        }
        ctx.drawImage(img, 0, 0);
        resolve(canvas);
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = e.target?.result as string;
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
};

/**
 * Compress image canvas
 */
const compressCanvas = (
  canvas: HTMLCanvasElement,
  quality: number,
  targetFormat: 'webp' | 'jpeg' | 'png'
): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    const mimeType = targetFormat === 'webp' ? 'image/webp' : 
                     targetFormat === 'jpeg' ? 'image/jpeg' : 
                     'image/png';
    
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new Error('Failed to compress image'));
        else resolve(blob);
      },
      mimeType,
      quality
    );
  });
};

/**
 * Resize canvas to specific dimensions
 */
const resizeCanvas = (
  canvas: HTMLCanvasElement,
  width: number,
  height: number
): HTMLCanvasElement => {
  const newCanvas = document.createElement('canvas');
  newCanvas.width = width;
  newCanvas.height = height;
  const ctx = newCanvas.getContext('2d');
  if (!ctx) {
    throw new Error('Failed to get 2D context for resize');
  }
  ctx.drawImage(canvas, 0, 0, width, height);
  return newCanvas;
};

/**
 * Generate thumbnail from canvas
 */
const generateThumbnail = (
  canvas: HTMLCanvasElement,
  size: number,
  quality: number
): Promise<Blob> => {
  const { width, height } = calculateDimensions(
    canvas.width,
    canvas.height,
    size,
    size
  );
  const resized = resizeCanvas(canvas, width, height);
  return compressCanvas(resized, quality, 'jpeg');
};

/**
 * Optimize image file
 */
export const optimizeImage = async (
  file: File,
  options: ImageOptimizationOptions = {}
): Promise<OptimizedImage> => {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // Validate file
  const validation = validateImageFile(file);
  if (!validation.valid) {
    throw new Error(validation.error);
  }

  // Load image to canvas
  const canvas = await fileToCanvas(file);
  const originalDimensions = getImageDimensions(
    document.createElement('img')
  );

  // Get actual dimensions from loaded canvas
  const actualWidth = canvas.width;
  const actualHeight = canvas.height;

  // Calculate optimized dimensions
  const optimizedDimensions = calculateDimensions(
    actualWidth,
    actualHeight,
    opts.maxWidth || 1920,
    opts.maxHeight || 1080
  );

  // Create optimized version
  const resizedCanvas = resizeCanvas(
    canvas,
    optimizedDimensions.width,
    optimizedDimensions.height
  );

  // Compress to target format
  const optimizedBlob = await compressCanvas(
    resizedCanvas,
    opts.quality || 0.8,
    opts.targetFormat || 'webp'
  );

  // Generate WebP version if different from target format
  let webpBlob: Blob | undefined;
  if (opts.generateWebP && opts.targetFormat !== 'webp') {
    webpBlob = await compressCanvas(resizedCanvas, opts.quality || 0.8, 'webp');
  }

  // Generate compressed JPEG for fallback
  const compressed = await compressCanvas(resizedCanvas, 0.7, 'jpeg');

  // Generate thumbnails
  let thumbnails: OptimizedImage['thumbnails'] = {
    small: compressed,
    medium: compressed,
    large: compressed,
  };

  if (opts.generateThumbnails) {
    thumbnails = {
      small: await generateThumbnail(canvas, 256, 0.75),
      medium: await generateThumbnail(canvas, 512, 0.8),
      large: await generateThumbnail(canvas, 1024, 0.85),
    };
  }

  // Convert file to blob to get size
  const originalBlob = new Blob([file], { type: file.type });

  return {
    original: originalBlob,
    optimized: optimizedBlob,
    webp: webpBlob,
    compressed,
    thumbnails,
    metadata: {
      originalSize: file.size,
      optimizedSize: optimizedBlob.size,
      compressionRatio: (optimizedBlob.size / file.size) * 100,
      format: file.type,
      dimensions: {
        width: actualWidth,
        height: actualHeight,
      },
      optimizedDimensions,
    },
  };
};

/**
 * Prepare FormData with optimized images for upload
 */
export const prepareOptimizedImageData = (
  optimized: OptimizedImage,
  includeWebp: boolean = true
): FormData => {
  const formData = new FormData();

  // Add optimized image
  formData.append('image', optimized.optimized, 'image_optimized.webp');

  // Add WebP alternative
  if (includeWebp && optimized.webp) {
    formData.append('image_webp', optimized.webp, 'image.webp');
  }

  // Add JPEG fallback
  formData.append('image_jpeg', optimized.compressed, 'image_fallback.jpg');

  // Add thumbnails
  formData.append('thumbnail_small', optimized.thumbnails.small, 'thumb_256.jpg');
  formData.append('thumbnail_medium', optimized.thumbnails.medium, 'thumb_512.jpg');
  formData.append('thumbnail_large', optimized.thumbnails.large, 'thumb_1024.jpg');

  // Add metadata
  formData.append(
    'image_metadata',
    JSON.stringify(optimized.metadata)
  );

  return formData;
};

/**
 * Get supported image format with fallback
 */
export const getSupportedFormat = async (): Promise<{
  webp: boolean;
  avif: boolean;
  heic: boolean;
}> => {
  const support = {
    webp: false,
    avif: false,
    heic: false,
  };

  // Test WebP support
  try {
    const webpCanvas = document.createElement('canvas');
    webpCanvas.width = 1;
    webpCanvas.height = 1;
    support.webp = webpCanvas.toDataURL('image/webp').includes('image/webp');
  } catch (e) {
    // WebP not supported
  }

  // Test AVIF support (via picture element)
  const avifTest = document.createElement('picture');
  const avifSource = document.createElement('source');
  avifSource.setAttribute('type', 'image/avif');
  avifTest.appendChild(avifSource);
  support.avif = avifTest.innerHTML.length > 0;

  // HEIC typically only supported on iOS
  support.heic = /iPhone|iPad|iPod/.test(navigator.userAgent);

  return support;
};

/**
 * Create responsive image srcset string
 */
export const createResponsiveImageSrcSet = (
  baseUrl: string,
  baseName: string,
  sizes: number[] = [256, 512, 1024]
): string => {
  return sizes
    .map((size) => `${baseUrl}/${baseName}_${size}w.jpg ${size}w`)
    .join(', ');
};

/**
 * Calculate optimal image size for viewport
 */
export const getOptimalImageSize = (
  containerWidth: number
): number => {
  // Return the smallest size that's larger than 1x the container width
  // to account for high DPI displays
  const sizes = [256, 512, 1024, 1920];
  const optimalSize = sizes.find((size) => size >= containerWidth * 1.5);
  return optimalSize || 1920;
};

/**
 * Monitor image loading performance
 */
export const monitorImagePerformance = (
  imageElement: HTMLImageElement,
  onMetrics?: (metrics: {
    loadTime: number;
    resourceSize: number;
    decodedSize: number;
  }) => void
): void => {
  if (!imageElement.src) return;

  const startTime = performance.now();

  const handleLoad = () => {
    const loadTime = performance.now() - startTime;

    // Try to get resource metrics
    if (window.performance && window.performance.getEntriesByType) {
      try {
        const resources = window.performance.getEntriesByType('resource');
        const imageResource = resources.find(
          (r) => r.name.includes(imageElement.src) || r.name === imageElement.currentSrc
        ) as PerformanceResourceTiming | undefined;

        if (imageResource && onMetrics) {
          onMetrics({
            loadTime,
            resourceSize: imageResource.transferSize || 0,
            decodedSize: imageResource.decodedBodySize || 0,
          });
        }
      } catch (e) {
        // Silently fail if metrics not available
      }
    }

    imageElement.removeEventListener('load', handleLoad);
  };

  imageElement.addEventListener('load', handleLoad);

  // Handle error
  const handleError = () => {
    imageElement.removeEventListener('load', handleLoad);
    console.error('Failed to load image for performance monitoring');
  };

  imageElement.addEventListener('error', handleError);
};
