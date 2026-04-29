import express from 'express';
import { body, validationResult } from 'express-validator';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { executeQuery, executeNonQuery } from '../database/connection';
import { 
  authenticateToken, 
  optionalAuthentication 
} from '../middleware/auth';
import { 
  handleValidationErrors,
  validateUserRegistration,
  validateUserLogin,
  validateUserProfileUpdate
} from '../middleware/validation';

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET;

// POST /api/users/register - Register new user
router.post('/register', validateUserRegistration, handleValidationErrors, async (req, res) => {
  try {
    const { email, username, password, first_name, last_name } = req.body;

    // Check if user already exists
    const existingUser = await executeQuery(
      'SELECT id, email, username FROM users WHERE email = ? OR username = ?',
      [email, username]
    );

    if (existingUser.length > 0) {
      const field = existingUser[0].email === email ? 'email' : 'username';
      return res.status(409).json({
        error: 'User already exists',
        message: `A user with this ${field} already exists`
      });
    }

    // Hash password
    const saltRounds = 12;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    // Generate UUID
    const { v4: uuidv4 } = require('uuid');
    const userUuid = uuidv4();

    // Create user
    const result = await executeNonQuery(
      `INSERT INTO users (uuid, email, username, password_hash, first_name, last_name) 
       VALUES (?, ?, ?, ?, ?, ?)`,
      [userUuid, email, username, passwordHash, first_name || null, last_name || null]
    );

    // Get created user
    const newUser = await executeQuery(
      'SELECT id, uuid, email, username, first_name, last_name, created_at FROM users WHERE id = ?',
      [result.insertId]
    );

    // Generate JWT token
    const token = jwt.sign(
      { userId: userUuid, email, username },
      JWT_SECRET,
      { expiresIn: '7d' }
    );

    res.status(201).json({
      success: true,
      message: 'User registered successfully',
      user: {
        id: newUser[0].uuid,
        email: newUser[0].email,
        username: newUser[0].username,
        first_name: newUser[0].first_name,
        last_name: newUser[0].last_name,
        created_at: newUser[0].created_at
      },
      token
    });

  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({
      error: 'Registration failed',
      message: 'Unable to register user'
    });
  }
});

// POST /api/users/login - Login user
router.post('/login', validateUserLogin, handleValidationErrors, async (req, res) => {
  try {
    const { email, password } = req.body;

    // Find user by email
    const users = await executeQuery(
      'SELECT id, uuid, email, username, password_hash, first_name, last_name, is_active FROM users WHERE email = ?',
      [email]
    );

    if (users.length === 0) {
      return res.status(401).json({
        error: 'Invalid credentials',
        message: 'Email or password is incorrect'
      });
    }

    const user = users[0];

    if (!user.is_active) {
      return res.status(401).json({
        error: 'Account disabled',
        message: 'Your account has been disabled'
      });
    }

    // Verify password
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      return res.status(401).json({
        error: 'Invalid credentials',
        message: 'Email or password is incorrect'
      });
    }

    // Update last login
    await executeNonQuery(
      'UPDATE users SET last_login = NOW() WHERE id = ?',
      [user.id]
    );

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.uuid, email: user.email, username: user.username },
      JWT_SECRET,
      { expiresIn: '7d' }
    );

    res.json({
      success: true,
      message: 'Login successful',
      user: {
        id: user.uuid,
        email: user.email,
        username: user.username,
        first_name: user.first_name,
        last_name: user.last_name,
        last_login: new Date().toISOString()
      },
      token
    });

  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      error: 'Login failed',
      message: 'Unable to login'
    });
  }
});

// GET /api/users/profile - Get user profile (requires authentication)
router.get('/profile', authenticateToken, async (req, res) => {
  try {
    // Get user profile
    const users = await executeQuery(
      `SELECT id, uuid, email, username, first_name, last_name, avatar_url, 
              email_verified, created_at, last_login 
       FROM users WHERE uuid = ?`,
      [req.user!.userId]
    );

    if (users.length === 0) {
      return res.status(404).json({
        error: 'User not found',
        message: 'User profile not found'
      });
    }

    const user = users[0];

    // Get user statistics
    const stats = await executeQuery(
      `SELECT 
        COUNT(*) as total_classifications,
        AVG(confidence_score) as avg_confidence,
        MAX(created_at) as last_classification
       FROM classifications WHERE user_id = ?`,
      [user.id]
    );

    res.json({
      success: true,
      user: {
        ...user,
        statistics: {
          total_classifications: stats[0].total_classifications || 0,
          avg_confidence: parseFloat(stats[0].avg_confidence) || 0,
          last_classification: stats[0].last_classification
        }
      }
    });

  } catch (error) {
    console.error('Profile error:', error);
    res.status(500).json({
      error: 'Failed to get profile',
      message: 'Unable to retrieve user profile'
    });
  }
});

// PUT /api/users/profile - Update user profile (requires authentication)
router.put('/profile', authenticateToken, validateUserProfileUpdate, handleValidationErrors, async (req, res) => {
  try {
    const { first_name, last_name, avatar_url } = req.body;

    // Update user profile
    await executeNonQuery(
      `UPDATE users SET first_name = ?, last_name = ?, avatar_url = ?, updated_at = NOW()
       WHERE uuid = ?`,
      [first_name || null, last_name || null, avatar_url || null, req.user!.userId]
    );

    // Get updated user
    const users = await executeQuery(
      `SELECT id, uuid, email, username, first_name, last_name, avatar_url, 
              email_verified, created_at, updated_at 
       FROM users WHERE uuid = ?`,
      [req.user!.userId]
    );

    res.json({
      success: true,
      message: 'Profile updated successfully',
      user: users[0]
    });

  } catch (error) {
    console.error('Profile update error:', error);
    res.status(500).json({
      error: 'Failed to update profile',
      message: 'Unable to update user profile'
    });
  }
});

export default router;
