import { Request, Response, NextFunction } from 'express';
import { body, param, query, validationResult } from 'express-validator';
import DOMPurify from 'isomorphic-dompurify';

// Input sanitization middleware
export const sanitizeInput = (req: Request, res: Response, next: NextFunction) => {
  // Sanitize request body
  if (req.body) {
    sanitizeObject(req.body);
  }

  // Sanitize query parameters
  if (req.query) {
    sanitizeObject(req.query);
  }

  // Sanitize URL parameters
  if (req.params) {
    sanitizeObject(req.params);
  }

  next();
};

// Recursive function to sanitize object properties
function sanitizeObject(obj: any): void {
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      if (typeof obj[key] === 'string') {
        // Remove potential XSS attacks and trim whitespace
        obj[key] = DOMPurify.sanitize(obj[key].trim());
      } else if (typeof obj[key] === 'object' && obj[key] !== null) {
        sanitizeObject(obj[key]);
      }
    }
  }
}

// Validation result handler middleware
export const handleValidationErrors = (req: Request, res: Response, next: NextFunction) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'Invalid input data provided',
      details: errors.array().map(error => ({
        field: error.param,
        message: error.msg,
        value: error.value
      }))
    });
  }
  next();
};

// Common validation chains
export const validateUserRegistration = [
  body('email')
    .isEmail()
    .normalizeEmail()
    .withMessage('Valid email is required'),
  body('username')
    .isLength({ min: 3, max: 30 })
    .matches(/^[a-zA-Z0-9_]+$/)
    .withMessage('Username must be 3-30 characters and contain only letters, numbers, and underscores'),
  body('password')
    .isLength({ min: 8 })
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
    .withMessage('Password must be at least 8 characters and contain uppercase, lowercase, number, and special character'),
  body('first_name')
    .optional()
    .isLength({ min: 1, max: 100 })
    .matches(/^[a-zA-Z\s]+$/)
    .withMessage('First name must contain only letters and spaces'),
  body('last_name')
    .optional()
    .isLength({ min: 1, max: 100 })
    .matches(/^[a-zA-Z\s]+$/)
    .withMessage('Last name must contain only letters and spaces')
];

export const validateUserLogin = [
  body('email')
    .isEmail()
    .normalizeEmail()
    .withMessage('Valid email is required'),
  body('password')
    .notEmpty()
    .withMessage('Password is required')
];

export const validateUserProfileUpdate = [
  body('first_name')
    .optional()
    .isLength({ min: 1, max: 100 })
    .matches(/^[a-zA-Z\s]+$/)
    .withMessage('First name must contain only letters and spaces'),
  body('last_name')
    .optional()
    .isLength({ min: 1, max: 100 })
    .matches(/^[a-zA-Z\s]+$/)
    .withMessage('Last name must contain only letters and spaces'),
  body('avatar_url')
    .optional()
    .isURL()
    .withMessage('Avatar URL must be a valid URL')
];

export const validatePredictionFeedback = [
  body('classification_id')
    .isUUID()
    .withMessage('Valid classification ID is required'),
  body('is_correct')
    .isBoolean()
    .withMessage('is_correct must be a boolean value'),
  body('correct_label')
    .optional()
    .isLength({ min: 1, max: 100 })
    .matches(/^[a-zA-Z\s]+$/)
    .withMessage('Correct label must contain only letters and spaces')
];

export const validateUUID = [
  param('id')
    .isUUID()
    .withMessage('Valid UUID is required')
];

export const validatePagination = [
  query('page')
    .optional()
    .isInt({ min: 1 })
    .withMessage('Page must be a positive integer'),
  query('limit')
    .optional()
    .isInt({ min: 1, max: 100 })
    .withMessage('Limit must be between 1 and 100')
];

export const validateConfidenceThreshold = [
  query('confidence_threshold')
    .optional()
    .isFloat({ min: 0, max: 1 })
    .withMessage('Confidence threshold must be between 0 and 1')
];

// File upload validation (for multer)
export const validateImageFile = (req: Request, res: Response, next: NextFunction) => {
  if (!req.file) {
    return res.status(400).json({
      error: 'No file uploaded',
      message: 'An image file is required for prediction'
    });
  }

  // Check file type
  const allowedMimeTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (!allowedMimeTypes.includes(req.file.mimetype)) {
    return res.status(400).json({
      error: 'Invalid file type',
      message: 'Only JPEG, PNG, and WebP images are allowed'
    });
  }

  // Check file size (10MB limit)
  const maxSize = 10 * 1024 * 1024; // 10MB in bytes
  if (req.file.size > maxSize) {
    return res.status(400).json({
      error: 'File too large',
      message: 'Maximum file size is 10MB'
    });
  }

  next();
};

// SQL injection prevention for raw queries
export const sanitizeSQLParams = (params: any[]): any[] => {
  return params.map(param => {
    if (typeof param === 'string') {
      // Remove potential SQL injection characters
      return param.replace(/['"\\;]/g, '');
    }
    return param;
  });
};
