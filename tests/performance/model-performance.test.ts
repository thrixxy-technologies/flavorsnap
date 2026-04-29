import axios from 'axios';
import { performance } from 'perf_hooks';

describe('Performance Tests', () => {
  const API_BASE_URL = 'http://localhost:5000/api';
  const PERFORMANCE_THRESHOLDS = {
    imageRecognition: 2000, // 2 seconds
    batchProcessing: 5000,  // 5 seconds
    memoryUsage: 512,       // 512 MB
  };

  it('should recognize food within threshold', async () => {
    const startTime = performance.now();
    
    await axios.post(`${API_BASE_URL}/recognize`, {
      image_path: 'tests/fixtures/test-food.jpg',
    });
    
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.imageRecognition);
    console.log(`Image recognition took ${duration.toFixed(2)}ms`);
  });

  it('should handle concurrent requests', async () => {
    const concurrentRequests = 10;
    const startTime = performance.now();
    
    const requests = Array(concurrentRequests)
      .fill(null)
      .map(() => 
        axios.post(`${API_BASE_URL}/recognize`, {
          image_path: 'tests/fixtures/test-food.jpg',
        })
      );
    
    await Promise.all(requests);
    
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    console.log(`${concurrentRequests} concurrent requests took ${duration.toFixed(2)}ms`);
    expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.batchProcessing);
  });

  it('should maintain consistent performance under load', async () => {
    const iterations = 5;
    const times: number[] = [];
    
    for (let i = 0; i < iterations; i++) {
      const startTime = performance.now();
      
      await axios.post(`${API_BASE_URL}/recognize`, {
        image_path: 'tests/fixtures/test-food.jpg',
      });
      
      times.push(performance.now() - startTime);
    }
    
    const avgTime = times.reduce((a, b) => a + b) / times.length;
    const variance = Math.max(...times) - Math.min(...times);
    
    console.log(`Average recognition time: ${avgTime.toFixed(2)}ms`);
    console.log(`Time variance: ${variance.toFixed(2)}ms`);
    
    expect(avgTime).toBeLessThan(PERFORMANCE_THRESHOLDS.imageRecognition);
  });
});
