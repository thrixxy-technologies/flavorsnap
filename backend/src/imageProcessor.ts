import sharp from 'sharp';
import Jimp from 'jimp';
import { createReadStream, createWriteStream, unlinkSync, existsSync } from 'fs';
import { join } from 'path';
import { promisify } from 'util';
// @ts-ignore
import ExifParser from 'exif-parser';

export interface ProcessedImageResult {
  originalPath: string;
  processedPath: string;
  metadata: ImageMetadata;
  preprocessing: PreprocessingInfo;
}

export interface ImageMetadata {
  width: number;
  height: number;
  format: string;
  size: number;
  orientation?: number;
  hasAlpha?: boolean;
  colorSpace?: string;
}

export interface PreprocessingInfo {
  rotationApplied: number;
  noiseReduction: boolean;
  contrastEnhanced: boolean;
  brightnessAdjusted: boolean;
  sharpeningApplied: boolean;
  resized: boolean;
  formatConverted: boolean;
}

export class ImageProcessor {
  private static readonly SUPPORTED_FORMATS = ['jpeg', 'jpg', 'png', 'webp', 'tiff', 'bmp'];
  private static readonly MAX_SIZE = 4096;
  private static readonly MIN_SIZE = 224;
  private static readonly TARGET_QUALITY = 85;
  private static readonly TARGET_FORMAT = 'jpeg';

  static async processImage(inputPath: string, outputPath?: string): Promise<ProcessedImageResult> {
    try {
      // Generate output path if not provided
      const finalOutputPath = outputPath || this.generateOutputPath(inputPath);
      
      // Get original metadata
      const metadata = await this.getImageMetadata(inputPath);
      
      // Initialize preprocessing info
      const preprocessing: PreprocessingInfo = {
        rotationApplied: 0,
        noiseReduction: false,
        contrastEnhanced: false,
        brightnessAdjusted: false,
        sharpeningApplied: false,
        resized: false,
        formatConverted: false
      };

      // Start processing pipeline
      let pipeline = sharp(inputPath);
      
      // 1. Auto-rotate based on EXIF data
      const rotation = await this.detectRotation(inputPath);
      if (rotation !== 0) {
        pipeline = pipeline.rotate(rotation);
        preprocessing.rotationApplied = rotation;
      }

      // 2. Resize if too large
      if (metadata.width > this.MAX_SIZE || metadata.height > this.MAX_SIZE) {
        const { width, height } = this.calculateTargetDimensions(
          metadata.width, 
          metadata.height, 
          this.MAX_SIZE, 
          this.MAX_SIZE
        );
        pipeline = pipeline.resize(width, height, {
          fit: 'inside',
          withoutEnlargement: true
        });
        preprocessing.resized = true;
      }

      // 3. Noise reduction for noisy images
      if (await this.detectNoise(inputPath)) {
        pipeline = this.applyNoiseReduction(pipeline);
        preprocessing.noiseReduction = true;
      }

      // 4. Contrast and brightness adjustment
      const adjustments = await this.analyzeImageQuality(inputPath);
      if (adjustments.contrast !== 1 || adjustments.brightness !== 1) {
        pipeline = pipeline.modulate({
          // @ts-ignore
          brightness: adjustments.brightness,
          // @ts-ignore
          contrast: adjustments.contrast
        });
        preprocessing.contrastEnhanced = adjustments.contrast !== 1;
        preprocessing.brightnessAdjusted = adjustments.brightness !== 1;
      }

      // 5. Apply sharpening for better detail
      pipeline = this.applySharpening(pipeline);
      preprocessing.sharpeningApplied = true;

      // 6. Convert to target format if needed
      if (metadata.format.toLowerCase() !== this.TARGET_FORMAT) {
        pipeline = pipeline.toFormat(this.TARGET_FORMAT, {
          quality: this.TARGET_QUALITY,
          progressive: true
        });
        preprocessing.formatConverted = true;
      } else {
        pipeline = pipeline.jpeg({ 
          quality: this.TARGET_QUALITY,
          progressive: true 
        });
      }

      // Process the image
      await pipeline.toFile(finalOutputPath);

      // Get final metadata
      const finalMetadata = await this.getImageMetadata(finalOutputPath);

      return {
        originalPath: inputPath,
        processedPath: finalOutputPath,
        metadata: finalMetadata,
        preprocessing
      };

    } catch (error) {
      console.error('Image processing failed:', error);
      throw new Error(`Failed to process image: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private static async getImageMetadata(imagePath: string): Promise<ImageMetadata> {
    try {
      const metadata = await sharp(imagePath).metadata();
      return {
        width: metadata.width || 0,
        height: metadata.height || 0,
        format: metadata.format || 'unknown',
        size: metadata.size || 0,
        orientation: metadata.orientation,
        hasAlpha: metadata.hasAlpha,
        colorSpace: metadata.space
      };
    } catch (error) {
      throw new Error(`Failed to read image metadata: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private static async detectRotation(imagePath: string): Promise<number> {
    try {
      const buffer = await sharp(imagePath).raw().toBuffer();
      const parser = ExifParser.create(buffer);
      const result = parser.parse();
      
      // EXIF orientation values
      const orientation = result.tags?.Orientation;
      if (!orientation) return 0;

      switch (orientation) {
        case 3: return 180;
        case 6: return 90;
        case 8: return 270;
        default: return 0;
      }
    } catch (error) {
      // If EXIF reading fails, try to detect rotation using Jimp
      try {
        // @ts-ignore
        const JimpClass = Jimp.default || Jimp;
        const jimpImage = await JimpClass.read(imagePath);
        // @ts-ignore
        const exif = jimpImage._exif;
        if (exif && exif.orientation) {
          switch (exif.orientation) {
            case 3: return 180;
            case 6: return 90;
            case 8: return 270;
            default: return 0;
          }
        }
      } catch (jimpError) {
        // Both methods failed, assume no rotation needed
      }
      return 0;
    }
  }

  private static async detectNoise(imagePath: string): Promise<boolean> {
    try {
      // Simple noise detection using sharp's statistics
      const { channels } = await sharp(imagePath).raw().stats();
      
      if (!channels || channels.length === 0) return false;
      
      // Calculate standard deviation across all channels
      let totalStdDev = 0;
      for (const channel of channels) {
        totalStdDev += channel.stdev;
      }
      const avgStdDev = totalStdDev / channels.length;
      
      // If standard deviation is high, likely noisy
      // Threshold is empirical and may need adjustment
      return avgStdDev > 30;
    } catch (error) {
      console.warn('Noise detection failed:', error);
      return false;
    }
  }

  private static async analyzeImageQuality(imagePath: string): Promise<{ contrast: number; brightness: number }> {
    try {
      const { channels } = await sharp(imagePath).raw().stats();
      
      if (!channels || channels.length === 0) {
        return { contrast: 1, brightness: 1 };
      }

      // Use the first channel (usually grayscale or red)
      const channel = channels[0];
      const mean = channel.mean;
      const stdDev = channel.stdev;
      
      // Calculate brightness adjustment (target middle gray)
      let brightness = 1;
      if (mean < 80) {
        brightness = 1.2; // Brighten dark images
      } else if (mean > 180) {
        brightness = 0.9; // Darken bright images
      }
      
      // Calculate contrast adjustment
      let contrast = 1;
      if (stdDev < 20) {
        contrast = 1.15; // Increase contrast for flat images
      } else if (stdDev > 60) {
        contrast = 0.95; // Slightly reduce contrast for very high contrast
      }
      
      return { contrast, brightness };
    } catch (error) {
      console.warn('Image quality analysis failed:', error);
      return { contrast: 1, brightness: 1 };
    }
  }

  private static applyNoiseReduction(pipeline: sharp.Sharp): sharp.Sharp {
    return pipeline.median(3); // Apply median filter for noise reduction
  }

  private static applySharpening(pipeline: sharp.Sharp): sharp.Sharp {
    // @ts-ignore
    return pipeline.sharpen({
      sigma: 1.0,
      // @ts-ignore
      flat: 1.0,
      // @ts-ignore
      jagged: 2.0
    });
  }

  private static calculateTargetDimensions(
    originalWidth: number, 
    originalHeight: number, 
    maxWidth: number, 
    maxHeight: number
  ): { width: number; height: number } {
    const aspectRatio = originalWidth / originalHeight;
    
    let width = originalWidth;
    let height = originalHeight;
    
    if (width > maxWidth) {
      width = maxWidth;
      height = Math.round(width / aspectRatio);
    }
    
    if (height > maxHeight) {
      height = maxHeight;
      width = Math.round(height * aspectRatio);
    }
    
    return { width, height };
  }

  private static generateOutputPath(inputPath: string): string {
    const ext = this.TARGET_FORMAT;
    const timestamp = Date.now();
    const dir = join(process.cwd(), 'uploads', 'processed');
    const filename = `processed_${timestamp}.${ext}`;
    return join(dir, filename);
  }

  static async createThumbnail(inputPath: string, size: number = 150): Promise<string> {
    try {
      const outputPath = this.generateThumbnailPath(inputPath, size);
      
      await sharp(inputPath)
        .resize(size, size, {
          fit: 'cover',
          position: 'center'
        })
        .jpeg({ quality: 80 })
        .toFile(outputPath);
      
      return outputPath;
    } catch (error) {
      console.error('Thumbnail creation failed:', error);
      throw new Error(`Failed to create thumbnail: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private static generateThumbnailPath(inputPath: string, size: number): string {
    const timestamp = Date.now();
    const dir = join(process.cwd(), 'uploads', 'thumbnails');
    const filename = `thumb_${size}_${timestamp}.jpg`;
    return join(dir, filename);
  }

  static isSupportedFormat(format: string): boolean {
    return this.SUPPORTED_FORMATS.includes(format.toLowerCase());
  }

  static async cleanupTempFiles(paths: string[]): Promise<void> {
    for (const path of paths) {
      try {
        if (existsSync(path)) {
          unlinkSync(path);
        }
      } catch (error) {
        console.warn(`Failed to delete temp file ${path}:`, error);
      }
    }
  }
}
