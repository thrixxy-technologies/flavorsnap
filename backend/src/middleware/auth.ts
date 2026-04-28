import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

// Extend Request interface to include user
declare global {
  namespace Express {
    interface Request {
      user?: {
        userId: string;
        email: string;
        username: string;
      };
    }
  }
}

// JWT Authentication Middleware
export const authenticateToken = (req: Request, res: Response, next: NextFunction) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({
      error: 'Access denied',
      message: 'Authentication token is required'
    });
  }

  const JWT_SECRET = process.env.JWT_SECRET;
  if (!JWT_SECRET) {
    console.error('JWT_SECRET is not defined in environment variables');
    return res.status(500).json({
      error: 'Server configuration error',
      message: 'Authentication system not properly configured'
    });
  }

  jwt.verify(token, JWT_SECRET, (err: any, decoded: any) => {
    if (err) {
      if (err.name === 'TokenExpiredError') {
        return res.status(401).json({
          error: 'Token expired',
          message: 'Please login again to get a new token'
        });
      }
      if (err.name === 'JsonWebTokenError') {
        return res.status(401).json({
          error: 'Invalid token',
          message: 'Authentication token is malformed or invalid'
        });
      }
      return res.status(401).json({
        error: 'Token verification failed',
        message: 'Unable to verify authentication token'
      });
    }

    req.user = {
      userId: decoded.userId,
      email: decoded.email,
      username: decoded.username
    };

    next();
  });
};

// API Key Authentication Middleware (for production)
export const authenticateApiKey = (req: Request, res: Response, next: NextFunction) => {
  // Skip API key authentication in development
  if (process.env.NODE_ENV !== 'production') {
    return next();
  }

  const apiKey = req.headers['x-api-key'] as string;
  const validApiKey = process.env.API_KEY;

  if (!validApiKey) {
    console.error('API_KEY is not defined in environment variables');
    return res.status(500).json({
      error: 'Server configuration error',
      message: 'API authentication not properly configured'
    });
  }

  if (!apiKey) {
    return res.status(401).json({
      error: 'API key required',
      message: 'X-API-Key header is required for production environment'
    });
  }

  if (apiKey !== validApiKey) {
    return res.status(401).json({
      error: 'Invalid API key',
      message: 'The provided API key is invalid'
    });
  }

  next();
};

// Optional authentication - doesn't fail if no token, but sets user if valid token
export const optionalAuthentication = (req: Request, res: Response, next: NextFunction) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return next(); // No token provided, continue without authentication
  }

  const JWT_SECRET = process.env.JWT_SECRET;
  if (!JWT_SECRET) {
    return next(); // No JWT secret, continue without authentication
  }

  jwt.verify(token, JWT_SECRET, (err: any, decoded: any) => {
    if (!err && decoded) {
      req.user = {
        userId: decoded.userId,
        email: decoded.email,
        username: decoded.username
      };
    }
    // If token is invalid, we just continue without authentication
    next();
  });
};
