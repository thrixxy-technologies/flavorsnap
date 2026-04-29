import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

describe('Accessibility Tests', () => {
  test('should have no accessibility violations on home page', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await injectAxe(page);
    
    await checkA11y(page, null, {
      detailedReport: true,
      detailedReportOptions: {
        html: true,
      },
    });
  });

  test('should support screen readers', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    const ariaLabels = await page.locator('[aria-label]').count();
    expect(ariaLabels).toBeGreaterThan(0);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
    
    const hasProperHierarchy = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
      for (let i = 1; i < headings.length; i++) {
        const prevLevel = parseInt(headings[i - 1].tagName[1]);
        const currLevel = parseInt(headings[i].tagName[1]);
        if (currLevel > prevLevel + 1) return false;
      }
      return true;
    });
    
    expect(hasProperHierarchy).toBe(true);
  });

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await injectAxe(page);
    
    const results = await page.evaluate(() => {
      return (window as any).axe.run();
    });
    
    const colorContrastIssues = results.violations.filter(
      (v: any) => v.id === 'color-contrast'
    );
    expect(colorContrastIssues).toHaveLength(0);
  });
});
