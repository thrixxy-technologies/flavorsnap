import fs from 'fs/promises';
import path from 'path';
import sharp from 'sharp';
import { v4 as uuidv4 } from 'uuid';
import { executeQuery, executeNonQuery, executeTransaction } from '../config/database';

// Food categories for ML model
const FOOD_CATEGORIES = [
  'Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam'
];

// Image validation interface
export interface ImageValidation {
  isValid: boolean;
  error?: string;
  metadata?: {
    width: number;
    height: number;
    format: string;
    size: number;
  };
}

// Prediction result interface
export interface PredictionResult {
  predictions: Array<{
    label: string;
    confidence: number;
  }>;
  processingTime: number;
  modelVersion: string;
}

// Classification save interface
export interface ClassificationSave {
  userId: string;
  imageFile: Express.Multer.File;
  predictions: Array<{
    label: string;
    confidence: number;
  }>;
  processingTime: number;
  ipAddress?: string;
  userAgent?: string;
}

// Validate uploaded image file
export async function validateImageFile(file: Express.Multer.File): Promise<ImageValidation> {
  try {
    // Check file size
    const maxSize = parseInt(process.env.MAX_FILE_SIZE || '10485760'); // 10MB
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: `File size exceeds maximum limit of ${maxSize / 1024 / 1024}MB`
      };
    }

    // Check file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.mimetype)) {
      return {
        isValid: false,
        error: 'Invalid file type. Only JPEG, PNG, and WebP images are allowed.'
      };
    }

    // Get image metadata
    const metadata = await sharp(file.path).metadata();
    
    // Check image dimensions
    if (!metadata.width || !metadata.height) {
      return {
        isValid: false,
        error: 'Unable to determine image dimensions'
      };
    }

    if (metadata.width < 100 || metadata.height < 100) {
      return {
        isValid: false,
        error: 'Image is too small. Minimum size is 100x100 pixels'
      };
    }

    if (metadata.width > 4096 || metadata.height > 4096) {
      return {
        isValid: false,
        error: 'Image is too large. Maximum size is 4096x4096 pixels'
      };
    }

    return {
      isValid: true,
      metadata: {
        width: metadata.width,
        height: metadata.height,
        format: metadata.format || 'unknown',
        size: file.size
      }
    };

  } catch (error) {
    return {
      isValid: false,
      error: 'Failed to validate image file'
    };
  }
}

// Process image for ML model (resize, normalize, etc.)
export async function processImageForML(imagePath: string): Promise<{ buffer: Buffer; size: number }> {
  try {
    // Resize to 224x224 (ResNet input size) and convert to RGB
    const processedBuffer = await sharp(imagePath)
      .resize(224, 224, {
        fit: 'fill',
        background: { r: 255, g: 255, b: 255 }
      })
      .toFormat('jpeg', { quality: 90 })
      .toBuffer();

    return {
      buffer: processedBuffer,
      size: processedBuffer.length
    };

  } catch (error) {
    throw new Error('Failed to process image for ML model');
  }
}

// Run ML prediction (mock implementation - replace with actual ML model)
export async function runMLPrediction(imageBuffer: { buffer: Buffer; size: number }): Promise<PredictionResult> {
  const startTime = Date.now();
  
  try {
    // TODO: Replace this with actual ML model inference
    // This is a mock implementation that simulates ML predictions
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 150 + Math.random() * 100));
    
    // Generate mock predictions based on image hash for consistency
    const imageHash = imageBuffer.buffer.slice(0, 10).toString('hex');
    const seed = parseInt(imageHash, 16) || 12345;
    
    // Generate random confidence scores that sum to ~1
    const predictions = FOOD_CATEGORIES.map((category, index) => {
      const randomValue = Math.sin(seed + index) * 0.5 + 0.5;
      return {
        label: category,
        confidence: randomValue
      };
    });
    
    // Sort by confidence and normalize
    predictions.sort((a, b) => b.confidence - a.confidence);
    const totalConfidence = predictions.reduce((sum, pred) => sum + pred.confidence, 0);
    
    const normalizedPredictions = predictions.map(pred => ({
      label: pred.label,
      confidence: Math.round((pred.confidence / totalConfidence) * 10000) / 100
    }));

    const processingTime = Date.now() - startTime;

    return {
      predictions: normalizedPredictions,
      processingTime: processingTime / 1000, // Convert to seconds
      modelVersion: '1.0.0'
    };

  } catch (error) {
    throw new Error('ML model prediction failed');
  }
}

// Save classification to database
export async function saveClassification(data: ClassificationSave): Promise<string> {
  try {
    // Get food category ID for the top prediction
    const categoryQuery = 'SELECT id FROM food_categories WHERE name = ?';
    const categoryResult = await executeQuery(categoryQuery, [data.predictions[0].label]);
    
    if (categoryResult.length === 0) {
      throw new Error(`Food category not found: ${data.predictions[0].label}`);
    }

    const foodCategoryId = categoryResult[0].id;
    const classificationUuid = uuidv4();

    // Create classification record and predictions in a transaction
    const queries = [
      {
        query: `
          INSERT INTO classifications (
            uuid, user_id, food_category_id, image_url, original_filename,
            file_size, mime_type, confidence_score, processing_time,
            model_version, ip_address, user_agent
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `,
        params: [
          classificationUuid,
          data.userId,
          foodCategoryId,
          `/uploads/${data.imageFile.filename}`,
          data.imageFile.originalname,
          data.imageFile.size,
          data.imageFile.mimetype,
          data.predictions[0].confidence,
          data.processingTime,
          '1.0.0',
          data.ipAddress,
          data.userAgent
        ]
      }
    ];

    // Add prediction records for top 3 predictions
    for (let i = 0; i < Math.min(3, data.predictions.length); i++) {
      const pred = data.predictions[i];
      const predCategoryQuery = 'SELECT id FROM food_categories WHERE name = ?';
      const predCategoryResult = await executeQuery(predCategoryQuery, [pred.label]);
      
      if (predCategoryResult.length > 0) {
        queries.push({
          query: `
            INSERT INTO classification_predictions (
              classification_id, food_category_id, confidence_score, rank_order
            ) VALUES (?, ?, ?, ?)
          `,
          params: [
            classificationUuid, // This will be replaced with the actual ID after insertion
            predCategoryResult[0].id,
            pred.confidence,
            i + 1
          ]
        });
      }
    }

    // Execute transaction
    await executeTransaction(queries);

    return classificationUuid;

  } catch (error) {
    console.error('Failed to save classification:', error);
    throw new Error('Failed to save classification to database');
  }
}

// Get food categories from database
export async function getFoodCategories(): Promise<Array<{ id: number; name: string; description: string }>> {
  try {
    const query = `
      SELECT id, name, description 
      FROM food_categories 
      WHERE is_active = TRUE 
      ORDER BY name
    `;
    
    return await executeQuery(query);

  } catch (error) {
    throw new Error('Failed to fetch food categories');
  }
}

// Clean up old uploaded images (maintenance task)
export async function cleanupOldImages(daysOld: number = 30): Promise<number> {
  try {
    // Get classifications older than specified days
    const query = `
      SELECT image_url, original_filename 
      FROM classifications 
      WHERE created_at < DATE_SUB(NOW(), INTERVAL ? DAY)
    `;
    
    const oldClassifications = await executeQuery(query, [daysOld]);
    
    let deletedCount = 0;
    
    for (const classification of oldClassifications) {
      try {
        const imagePath = path.join(__dirname, '../../uploads', path.basename(classification.image_url));
        await fs.unlink(imagePath);
        deletedCount++;
      } catch (error) {
        // File might not exist, continue with others
        console.warn(`Failed to delete image: ${classification.image_url}`);
      }
    }

    // Delete old classification records
    const deleteQuery = `
      DELETE FROM classifications 
      WHERE created_at < DATE_SUB(NOW(), INTERVAL ? DAY)
    `;
    
    await executeNonQuery(deleteQuery, [daysOld]);

    return deletedCount;

  } catch (error) {
    throw new Error('Failed to cleanup old images');
  }
}

// Get model performance statistics
export async function getModelStats(): Promise<{
  totalClassifications: number;
  avgConfidence: number;
  accuracyRate: number;
  mostClassifiedFood: string;
}> {
  try {
    const query = `
      SELECT 
        COUNT(*) as total_classifications,
        AVG(confidence_score) as avg_confidence,
        COUNT(CASE WHEN is_correct = TRUE THEN 1 END) / COUNT(*) as accuracy_rate,
        (SELECT fc.name FROM classifications c2 
         JOIN food_categories fc ON c2.food_category_id = fc.id 
         GROUP BY fc.name 
         ORDER BY COUNT(*) DESC 
         LIMIT 1) as most_classified_food
      FROM classifications
      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    `;
    
    const result = await executeQuery(query);
    const stats = result[0];
    
    return {
      totalClassifications: stats.total_classifications || 0,
      avgConfidence: parseFloat(stats.avg_confidence) || 0,
      accuracyRate: parseFloat(stats.accuracy_rate) || 0,
      mostClassifiedFood: stats.most_classified_food || 'N/A'
    };

  } catch (error) {
    throw new Error('Failed to get model statistics');
  }
}
