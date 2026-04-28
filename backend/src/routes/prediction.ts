import express from 'express';
import multer from 'multer';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import sharp from 'sharp';
import { body, validationResult } from 'express-validator';
import { 
  executeQuery, 
  executeNonQuery, 
  executeTransaction 
} from '../config/database';
import { 
  validateImageFile, 
  processImageForML, 
  runMLPrediction,
  saveClassification 
} from '../utils/prediction';

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, path.join(__dirname, '../../uploads'));
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const ext = path.extname(file.originalname);
    cb(null, `${file.fieldname}-${uniqueSuffix}${ext}`);
  }
});

const fileFilter = (req: any, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (allowedTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error('Invalid file type. Only JPEG, PNG, and WebP images are allowed.'));
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: parseInt(process.env.MAX_FILE_SIZE || '10485760'), // 10MB
    files: 1
  }
});

// Validation middleware
const validatePrediction = [
  body('user_id').optional().isUUID().withMessage('Invalid user ID format'),
  body('confidence_threshold').optional().isFloat({ min: 0, max: 1 }).withMessage('Confidence threshold must be between 0 and 1')
];

// POST /api/predict - Classify food image
router.post('/', upload.single('image'), validatePrediction, async (req, res) => {
  try {
    // Check for validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    // Check if file was uploaded
    if (!req.file) {
      return res.status(400).json({
        error: 'No image uploaded',
        message: 'Please upload an image file'
      });
    }

    // Validate image file
    const imageValidation = await validateImageFile(req.file);
    if (!imageValidation.isValid) {
      return res.status(400).json({
        error: 'Invalid image',
        message: imageValidation.error
      });
    }

    // Process image for ML model
    const processedImage = await processImageForML(req.file.path);
    
    // Run ML prediction
    const prediction = await runMLPrediction(processedImage);
    
    // Get confidence threshold from request or use default
    const confidenceThreshold = parseFloat(req.body.confidence_threshold) || 0.6;
    
    // Filter predictions by confidence threshold
    const filteredPredictions = prediction.predictions.filter(
      (pred: any) => pred.confidence >= confidenceThreshold
    );

    if (filteredPredictions.length === 0) {
      return res.status(400).json({
        error: 'Low confidence',
        message: `No predictions met the confidence threshold of ${confidenceThreshold}`,
        predictions: prediction.predictions.slice(0, 3) // Show top 3 for reference
      });
    }

    // Save classification to database if user_id is provided
    let classificationId = null;
    if (req.body.user_id) {
      try {
        classificationId = await saveClassification({
          userId: req.body.user_id,
          imageFile: req.file,
          predictions: filteredPredictions,
          processingTime: prediction.processingTime,
          ipAddress: req.ip,
          userAgent: req.get('User-Agent')
        });
      } catch (dbError) {
        console.error('Failed to save classification:', dbError);
        // Continue with response even if database save fails
      }
    }

    // Return prediction results
    res.json({
      success: true,
      classification_id: classificationId,
      label: filteredPredictions[0].label,
      confidence: filteredPredictions[0].confidence,
      all_predictions: filteredPredictions.map((pred: any) => ({
        label: pred.label,
        confidence: pred.confidence
      })),
      processing_time: prediction.processingTime,
      model_version: prediction.modelVersion,
      image_info: {
        original_filename: req.file.originalname,
        file_size: req.file.size,
        mime_type: req.file.mimetype,
        processed_size: processedImage.size
      }
    });

  } catch (error) {
    console.error('Prediction error:', error);
    res.status(500).json({
      error: 'Prediction failed',
      message: 'An error occurred while processing your image'
    });
  }
});

// GET /api/predict/classes - Get available food classes
router.get('/classes', async (req, res) => {
  try {
    const query = `
      SELECT id, name, description, image_url 
      FROM food_categories 
      WHERE is_active = TRUE 
      ORDER BY name
    `;
    
    const categories = await executeQuery(query);
    
    res.json({
      success: true,
      classes: categories,
      count: categories.length
    });

  } catch (error) {
    console.error('Error fetching classes:', error);
    res.status(500).json({
      error: 'Failed to fetch classes',
      message: 'Unable to retrieve food categories'
    });
  }
});

// GET /api/predict/history - Get classification history (requires user_id)
router.get('/history', async (req, res) => {
  try {
    const userId = req.query.user_id;
    
    if (!userId) {
      return res.status(400).json({
        error: 'Missing user_id',
        message: 'User ID is required to view classification history'
      });
    }

    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 10;
    const offset = (page - 1) * limit;

    const query = `
      SELECT 
        c.uuid,
        c.image_url,
        c.confidence_score,
        c.processing_time,
        c.created_at,
        fc.name as food_category,
        fc.description as category_description,
        c.is_correct
      FROM classifications c
      JOIN food_categories fc ON c.food_category_id = fc.id
      WHERE c.user_id = ?
      ORDER BY c.created_at DESC
      LIMIT ? OFFSET ?
    `;

    const classifications = await executeQuery(query, [userId, limit, offset]);

    // Get total count for pagination
    const countQuery = 'SELECT COUNT(*) as total FROM classifications WHERE user_id = ?';
    const countResult = await executeQuery(countQuery, [userId]);
    const total = countResult[0]?.total || 0;

    res.json({
      success: true,
      classifications,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }
    });

  } catch (error) {
    console.error('Error fetching history:', error);
    res.status(500).json({
      error: 'Failed to fetch history',
      message: 'Unable to retrieve classification history'
    });
  }
});

// POST /api/predict/feedback - Provide feedback on classification accuracy
router.post('/feedback', async (req, res) => {
  try {
    const { classification_id, is_correct, correct_label } = req.body;

    if (!classification_id || typeof is_correct !== 'boolean') {
      return res.status(400).json({
        error: 'Invalid input',
        message: 'classification_id and is_correct are required'
      });
    }

    // Update classification feedback
    const updateQuery = `
      UPDATE classifications 
      SET is_correct = ?
      WHERE uuid = ?
    `;

    const result = await executeNonQuery(updateQuery, [is_correct, classification_id]);

    if (result.affectedRows === 0) {
      return res.status(404).json({
        error: 'Classification not found',
        message: 'The specified classification ID does not exist'
      });
    }

    // If incorrect and correct_label is provided, log for model improvement
    if (!is_correct && correct_label) {
      // This could be stored in a separate feedback table for model training
      console.log(`Feedback: Classification ${classification_id} was incorrect. Correct label: ${correct_label}`);
    }

    res.json({
      success: true,
      message: 'Feedback recorded successfully'
    });

  } catch (error) {
    console.error('Error recording feedback:', error);
    res.status(500).json({
      error: 'Failed to record feedback',
      message: 'Unable to save your feedback'
    });
  }
});

// GET /api/predict/stats - Get prediction statistics
router.get('/stats', async (req, res) => {
  try {
    const timeframe = req.query.timeframe || '24h'; // 24h, 7d, 30d
    
    let timeCondition = '';
    if (timeframe === '24h') {
      timeCondition = 'AND c.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)';
    } else if (timeframe === '7d') {
      timeCondition = 'AND c.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)';
    } else if (timeframe === '30d') {
      timeCondition = 'AND c.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)';
    }

    const statsQuery = `
      SELECT 
        COUNT(c.id) as total_classifications,
        COUNT(DISTINCT c.user_id) as unique_users,
        AVG(c.confidence_score) as avg_confidence,
        AVG(c.processing_time) as avg_processing_time,
        fc.name as most_classified_food,
        COUNT(CASE WHEN c.is_correct = TRUE THEN 1 END) as correct_classifications,
        COUNT(CASE WHEN c.is_correct = FALSE THEN 1 END) as incorrect_classifications
      FROM classifications c
      JOIN food_categories fc ON c.food_category_id = fc.id
      WHERE 1=1 ${timeCondition}
      GROUP BY fc.name
      ORDER BY COUNT(c.id) DESC
      LIMIT 1
    `;

    const stats = await executeQuery(statsQuery);

    res.json({
      success: true,
      timeframe,
      stats: stats[0] || {
        total_classifications: 0,
        unique_users: 0,
        avg_confidence: 0,
        avg_processing_time: 0,
        most_classified_food: null,
        correct_classifications: 0,
        incorrect_classifications: 0
      }
    });

  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({
      error: 'Failed to fetch statistics',
      message: 'Unable to retrieve prediction statistics'
    });
  }
});

export default router;
