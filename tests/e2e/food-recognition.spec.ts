import { test, expect } from '@playwright/test';

describe('Food Recognition E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('should upload and recognize food image', async ({ page }) => {
    await page.click('[data-testid="upload-button"]');
    await page.setInputFiles('[data-testid="file-input"]', 'tests/fixtures/food-sample.jpg');
    
    const result = page.waitForSelector('[data-testid="recognition-result"]');
    expect(result).toBeTruthy();
  });

  test('should display nutritional information', async ({ page }) => {
    await page.click('[data-testid="upload-button"]');
    await page.setInputFiles('[data-testid="file-input"]', 'tests/fixtures/apple.jpg');
    
    const nutrition = await page.textContent('[data-testid="nutrition-panel"]');
    expect(nutrition).toContain('Calories');
    expect(nutrition).toContain('Protein');
  });

  test('should handle accessibility with keyboard navigation', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    
    const focused = await page.evaluate(() => document.activeElement?.className);
    expect(focused).toContain('focusable');
  });

  test('should perform visual regression check', async ({ page }) => {
    await expect(page).toHaveScreenshot('food-recognition-home.png');
  });
});
