import express from 'express';
import { executeQuery } from '../config/database';

const router = express.Router();

// GET /api/foods - Get all food categories
router.get('/', async (req, res) => {
  try {
    const query = `
      SELECT id, name, description, image_url, is_active, created_at
      FROM food_categories 
      WHERE is_active = TRUE 
      ORDER BY name
    `;
    
    const categories = await executeQuery(query);
    
    res.json({
      success: true,
      categories,
      count: categories.length
    });

  } catch (error) {
    console.error('Error fetching food categories:', error);
    res.status(500).json({
      error: 'Failed to fetch food categories',
      message: 'Unable to retrieve food categories'
    });
  }
});

// GET /api/foods/:id - Get specific food category
router.get('/:id', async (req, res) => {
  try {
    const categoryId = req.params.id;
    
    const query = `
      SELECT id, name, description, image_url, is_active, created_at, updated_at
      FROM food_categories 
      WHERE id = ? AND is_active = TRUE
    `;
    
    const categories = await executeQuery(query, [categoryId]);
    
    if (categories.length === 0) {
      return res.status(404).json({
        error: 'Food category not found',
        message: 'The specified food category does not exist'
      });
    }

    // Get statistics for this category
    const statsQuery = `
      SELECT 
        COUNT(*) as total_classifications,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(confidence_score) as avg_confidence,
        MAX(created_at) as last_classification
      FROM classifications 
      WHERE food_category_id = ?
    `;
    
    const stats = await executeQuery(statsQuery, [categoryId]);

    res.json({
      success: true,
      category: categories[0],
      statistics: {
        total_classifications: stats[0].total_classifications || 0,
        unique_users: stats[0].unique_users || 0,
        avg_confidence: parseFloat(stats[0].avg_confidence) || 0,
        last_classification: stats[0].last_classification
      }
    });

  } catch (error) {
    console.error('Error fetching food category:', error);
    res.status(500).json({
      error: 'Failed to fetch food category',
      message: 'Unable to retrieve food category'
    });
  }
});

// GET /api/foods/:id/classifications - Get classifications for specific food category
router.get('/:id/classifications', async (req, res) => {
  try {
    const categoryId = req.params.id;
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 10;
    const offset = (page - 1) * limit;

    // Verify category exists
    const categoryQuery = 'SELECT id, name FROM food_categories WHERE id = ? AND is_active = TRUE';
    const categories = await executeQuery(categoryQuery, [categoryId]);
    
    if (categories.length === 0) {
      return res.status(404).json({
        error: 'Food category not found',
        message: 'The specified food category does not exist'
      });
    }

    // Get classifications
    const query = `
      SELECT 
        c.uuid,
        c.confidence_score,
        c.processing_time,
        c.created_at,
        c.is_correct,
        u.username,
        u.email
      FROM classifications c
      JOIN users u ON c.user_id = u.id
      WHERE c.food_category_id = ?
      ORDER BY c.created_at DESC
      LIMIT ? OFFSET ?
    `;

    const classifications = await executeQuery(query, [categoryId, limit, offset]);

    // Get total count for pagination
    const countQuery = 'SELECT COUNT(*) as total FROM classifications WHERE food_category_id = ?';
    const countResult = await executeQuery(countQuery, [categoryId]);
    const total = countResult[0]?.total || 0;

    res.json({
      success: true,
      category: categories[0],
      classifications,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }
    });

  } catch (error) {
    console.error('Error fetching classifications:', error);
    res.status(500).json({
      error: 'Failed to fetch classifications',
      message: 'Unable to retrieve classifications for this food category'
    });
  }
});

export default router;
