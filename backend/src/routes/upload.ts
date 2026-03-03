import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { ImageProcessor, ProcessedImageResult } from '../imageProcessor';

const router = Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(process.cwd(), 'uploads', 'original');
    
    // Create directory if it doesn't exist
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const ext = path.extname(file.originalname);
    cb(null, `upload-${uniqueSuffix}${ext}`);
  }
});

const fileFilter = (req: Request, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
  // Check file type
  const allowedTypes = /jpeg|jpg|png|webp|tiff|bmp/;
  const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
  const mimetype = allowedTypes.test(file.mimetype);

  if (mimetype && extname) {
    return cb(null, true);
  } else {
    cb(new Error('Invalid file type. Only JPEG, PNG, WebP, TIFF, and BMP files are allowed.'));
  }
};

const upload = multer({
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter
});

// Enhanced upload endpoint with preprocessing
router.post('/', upload.single('file'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        error: 'No file uploaded',
        code: 'NO_FILE'
      });
    }

    const file = req.file;
    console.log(`Processing uploaded file: ${file.originalname}`);

    // Validate file
    const fileExt = path.extname(file.originalname).slice(1);
    if (!ImageProcessor.isSupportedFormat(fileExt)) {
      // Cleanup uploaded file
      fs.unlinkSync(file.path);
      return res.status(400).json({
        error: 'Unsupported file format',
        code: 'UNSUPPORTED_FORMAT',
        supportedFormats: ['jpeg', 'jpg', 'png', 'webp', 'tiff', 'bmp']
      });
    }

    // Process the image
    let processedResult: ProcessedImageResult;
    try {
      processedResult = await ImageProcessor.processImage(file.path);
      console.log('Image preprocessing completed successfully');
    } catch (processingError) {
      console.error('Image preprocessing failed:', processingError);
      // Cleanup uploaded file
      fs.unlinkSync(file.path);
      return res.status(500).json({
        error: 'Image processing failed',
        code: 'PROCESSING_ERROR',
        details: processingError instanceof Error ? processingError.message : 'Unknown error'
      });
    }

    // Create thumbnail
    let thumbnailPath: string | null = null;
    try {
      thumbnailPath = await ImageProcessor.createThumbnail(processedResult.processedPath);
      console.log('Thumbnail created successfully');
    } catch (thumbnailError) {
      console.warn('Thumbnail creation failed:', thumbnailError);
      // Continue without thumbnail
    }

    // Generate URLs
    const baseUrl = `${req.protocol}://${req.get('host')}`;
    const imageUrl = `${baseUrl}/uploads/processed/${path.basename(processedResult.processedPath)}`;
    const thumbnailUrl = thumbnailPath ? `${baseUrl}/uploads/thumbnails/${path.basename(thumbnailPath)}` : null;

    // Mock classification result (replace with actual ML model call)
    const classificationResult = await mockClassification(processedResult.processedPath);

    // Return enhanced response
    const response = {
      success: true,
      classification: classificationResult,
      image: {
        original: {
          filename: file.originalname,
          size: file.size,
          mimetype: file.mimetype,
          url: `${baseUrl}/uploads/original/${file.filename}`
        },
        processed: {
          filename: path.basename(processedResult.processedPath),
          size: processedResult.metadata.size,
          width: processedResult.metadata.width,
          height: processedResult.metadata.height,
          format: processedResult.metadata.format,
          url: imageUrl
        },
        thumbnail: thumbnailUrl ? {
          filename: thumbnailPath ? path.basename(thumbnailPath) : '',
          url: thumbnailUrl
        } : null
      },
      preprocessing: {
        applied: processedResult.preprocessing,
        improvements: getImprovementSummary(processedResult.preprocessing)
      },
      metadata: {
        processingTime: file.filename ? Date.now() - parseInt(file.filename.split('-')[1]) : 0,
        originalSize: file.size,
        processedSize: processedResult.metadata.size,
        compressionRatio: file.size > 0 ? (processedResult.metadata.size / file.size).toFixed(2) : '0'
      }
    };

    // Cleanup temporary files
    setTimeout(() => {
      ImageProcessor.cleanupTempFiles([file.path]);
    }, 5000); // Cleanup after 5 seconds

    res.json(response);

  } catch (error) {
    console.error('Upload endpoint error:', error);
    
    // Cleanup on error
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    
    res.status(500).json({
      error: 'Internal server error',
      code: 'INTERNAL_ERROR',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Mock classification function (replace with actual ML model)
async function mockClassification(imagePath: string): Promise<any> {
  // This would normally call your ML model
  // For now, return a mock result
  const foods = [
    'Pizza Margherita',
    'Caesar Salad', 
    'Grilled Chicken',
    'Sushi Roll',
    'Pasta Carbonara',
    'Beef Burger',
    'Greek Salad',
    'Fish Tacos'
  ];
  
  const randomFood = foods[Math.floor(Math.random() * foods.length)];
  const confidence = 0.75 + Math.random() * 0.24; // 75-99%
  
  return {
    label: randomFood,
    confidence: Math.round(confidence * 100) / 100,
    calories: Math.floor(Math.random() * 800) + 100, // 100-900 calories
    protein: Math.floor(Math.random() * 40) + 5, // 5-45g protein
    carbs: Math.floor(Math.random() * 60) + 10, // 10-70g carbs
    fat: Math.floor(Math.random() * 30) + 2, // 2-32g fat
    fiber: Math.floor(Math.random() * 15) + 1, // 1-16g fiber
    timestamp: new Date().toISOString()
  };
}

function getImprovementSummary(preprocessing: any): string[] {
  const improvements: string[] = [];
  
  if (preprocessing.rotationApplied !== 0) {
    improvements.push(`Auto-rotated ${preprocessing.rotationApplied}°`);
  }
  
  if (preprocessing.resized) {
    improvements.push('Resized for optimal processing');
  }
  
  if (preprocessing.noiseReduction) {
    improvements.push('Noise reduction applied');
  }
  
  if (preprocessing.contrastEnhanced) {
    improvements.push('Contrast enhanced');
  }
  
  if (preprocessing.brightnessAdjusted) {
    improvements.push('Brightness adjusted');
  }
  
  if (preprocessing.sharpeningApplied) {
    improvements.push('Image sharpened');
  }
  
  if (preprocessing.formatConverted) {
    improvements.push('Optimized format conversion');
  }
  
  return improvements;
}

export default router;
