import axios from 'axios';
import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';

describe('Model API Integration Tests', () => {
  const API_BASE_URL = 'http://localhost:5000/api';
  let testImagePath: string;

  beforeAll(async () => {
    testImagePath = 'tests/fixtures/test-food.jpg';
  });

  it('should recognize food from image', async () => {
    const response = await axios.post(`${API_BASE_URL}/recognize`, {
      image_path: testImagePath,
    });
    
    expect(response.status).toBe(200);
    expect(response.data).toHaveProperty('classification');
    expect(response.data.classification).toHaveProperty('food_type');
  });

  it('should return confidence scores', async () => {
    const response = await axios.post(`${API_BASE_URL}/recognize`, {
      image_path: testImagePath,
    });
    
    expect(response.data.classification.confidence).toBeGreaterThan(0);
    expect(response.data.classification.confidence).toBeLessThanOrEqual(1);
  });

  it('should batch process multiple images', async () => {
    const images = [testImagePath, testImagePath];
    const response = await axios.post(`${API_BASE_URL}/batch-recognize`, {
      images,
    });
    
    expect(response.data).toHaveLength(2);
    expect(response.data[0]).toHaveProperty('classification');
  });

  it('should handle invalid images gracefully', async () => {
    try {
      await axios.post(`${API_BASE_URL}/recognize`, {
        image_path: 'invalid/path.jpg',
      });
    } catch (error: any) {
      expect(error.response.status).toBe(400);
      expect(error.response.data).toHaveProperty('error');
    }
  });
});
