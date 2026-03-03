import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { ImageProcessor } from '../imageProcessor';

const router = Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(process.cwd(), 'uploads', 'temp');
    
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now();
    const ext = path.extname(file.originalname);
    cb(null, `analyze-${uniqueSuffix}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  }
});

// Analyze image quality and provide recommendations
router.post('/', upload.single('file'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        error: 'No file uploaded',
        code: 'NO_FILE'
      });
    }

    const file = req.file;
    console.log(`Analyzing file: ${file.originalname}`);

    // Get basic metadata
    const metadata = await ImageProcessor.getImageMetadata(file.path);
    
    // Perform quality analysis
    const qualityAnalysis = await performQualityAnalysis(file.path);
    
    // Get preprocessing recommendations
    const recommendations = getPreprocessingRecommendations(metadata, qualityAnalysis);
    
    // Cleanup temporary file
    setTimeout(() => {
      ImageProcessor.cleanupTempFiles([file.path]);
    }, 1000);

    res.json({
      success: true,
      metadata: {
        filename: file.originalname,
        size: file.size,
        width: metadata.width,
        height: metadata.height,
        format: metadata.format,
        orientation: metadata.orientation,
        hasAlpha: metadata.hasAlpha,
        colorSpace: metadata.colorSpace
      },
      quality: qualityAnalysis,
      recommendations,
      supported: ImageProcessor.isSupportedFormat(metadata.format)
    });

  } catch (error) {
    console.error('Analysis endpoint error:', error);
    
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    
    res.status(500).json({
      error: 'Analysis failed',
      code: 'ANALYSIS_ERROR',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

async function performQualityAnalysis(imagePath: string): Promise<any> {
  try {
    const sharp = require('sharp');
    
    // Get image statistics
    const { channels } = await sharp(imagePath).raw().stats();
    
    // Calculate quality metrics
    let brightness = 0;
    let contrast = 0;
    let noise = 0;
    let sharpness = 0;
    
    if (channels && channels.length > 0) {
      const mainChannel = channels[0]; // Use first channel (grayscale or red)
      brightness = mainChannel.mean;
      contrast = mainChannel.stdev;
      noise = await estimateNoise(imagePath);
      sharpness = await estimateSharpness(imagePath);
    }
    
    // Overall quality score (0-100)
    const qualityScore = calculateQualityScore(brightness, contrast, noise, sharpness);
    
    return {
      brightness: {
        value: Math.round(brightness),
        assessment: getBrightnessAssessment(brightness),
        ideal: [80, 180] // Ideal range
      },
      contrast: {
        value: Math.round(contrast),
        assessment: getContrastAssessment(contrast),
        ideal: [20, 60] // Ideal range
      },
      noise: {
        value: Math.round(noise),
        assessment: getNoiseAssessment(noise),
        ideal: [0, 20] // Ideal range
      },
      sharpness: {
        value: Math.round(sharpness),
        assessment: getSharpnessAssessment(sharpness),
        ideal: [50, 100] // Ideal range
      },
      overall: {
        score: qualityScore,
        assessment: getOverallAssessment(qualityScore)
      }
    };
    
  } catch (error) {
    console.error('Quality analysis failed:', error);
    return {
      error: 'Quality analysis failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

async function estimateNoise(imagePath: string): Promise<number> {
  try {
    const sharp = require('sharp');
    const { channels } = await sharp(imagePath).raw().stats();
    
    if (!channels || channels.length === 0) return 0;
    
    // Simple noise estimation using standard deviation
    let totalNoise = 0;
    for (const channel of channels) {
      totalNoise += channel.stdev;
    }
    
    return totalNoise / channels.length;
  } catch (error) {
    return 0;
  }
}

async function estimateSharpness(imagePath: string): Promise<number> {
  try {
    const sharp = require('sharp');
    
    // Apply edge detection filter
    const edges = await sharp(imagePath)
      .convolve({
        width: 3,
        height: 3,
        kernel: [0, -1, 0, -1, 4, -1, 0, -1, 0] // Laplacian kernel
      })
      .raw()
      .toBuffer();
    
    // Calculate variance as sharpness metric
    let sum = 0;
    for (let i = 0; i < edges.length; i++) {
      sum += edges[i] * edges[i];
    }
    
    const variance = sum / edges.length;
    return Math.sqrt(variance);
  } catch (error) {
    return 0;
  }
}

function calculateQualityScore(brightness: number, contrast: number, noise: number, sharpness: number): number {
  let score = 100;
  
  // Brightness penalty
  if (brightness < 80 || brightness > 180) {
    score -= 20;
  }
  
  // Contrast penalty
  if (contrast < 20) {
    score -= 25;
  } else if (contrast > 60) {
    score -= 10;
  }
  
  // Noise penalty
  if (noise > 30) {
    score -= 20;
  } else if (noise > 20) {
    score -= 10;
  }
  
  // Sharpness penalty
  if (sharpness < 30) {
    score -= 25;
  } else if (sharpness < 50) {
    score -= 10;
  }
  
  return Math.max(0, Math.min(100, score));
}

function getBrightnessAssessment(value: number): string {
  if (value < 50) return 'Too dark';
  if (value < 80) return 'Slightly dark';
  if (value > 200) return 'Too bright';
  if (value > 180) return 'Slightly bright';
  return 'Good';
}

function getContrastAssessment(value: number): string {
  if (value < 15) return 'Very low contrast';
  if (value < 25) return 'Low contrast';
  if (value > 70) return 'Very high contrast';
  if (value > 60) return 'High contrast';
  return 'Good';
}

function getNoiseAssessment(value: number): string {
  if (value > 40) return 'Very noisy';
  if (value > 25) return 'Noisy';
  if (value > 15) return 'Slightly noisy';
  return 'Low noise';
}

function getSharpnessAssessment(value: number): string {
  if (value < 20) return 'Very blurry';
  if (value < 35) return 'Blurry';
  if (value < 50) return 'Slightly soft';
  return 'Sharp';
}

function getOverallAssessment(score: number): string {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 55) return 'Fair';
  if (score >= 40) return 'Poor';
  return 'Very Poor';
}

function getPreprocessingRecommendations(metadata: any, quality: any): string[] {
  const recommendations: string[] = [];
  
  // Size recommendations
  if (metadata.width > 4096 || metadata.height > 4096) {
    recommendations.push('Consider resizing for faster processing');
  }
  
  // Format recommendations
  if (!['jpeg', 'jpg', 'png'].includes(metadata.format.toLowerCase())) {
    recommendations.push('Convert to JPEG or PNG for better compatibility');
  }
  
  // Quality-based recommendations
  if (quality.brightness.assessment !== 'Good') {
    recommendations.push('Brightness adjustment recommended');
  }
  
  if (quality.contrast.assessment !== 'Good') {
    recommendations.push('Contrast enhancement recommended');
  }
  
  if (quality.noise.assessment !== 'Low noise') {
    recommendations.push('Noise reduction recommended');
  }
  
  if (quality.sharpness.assessment !== 'Sharp') {
    recommendations.push('Sharpening recommended');
  }
  
  if (metadata.orientation && metadata.orientation !== 1) {
    recommendations.push('Auto-rotation needed');
  }
  
  return recommendations;
}

export default router;
