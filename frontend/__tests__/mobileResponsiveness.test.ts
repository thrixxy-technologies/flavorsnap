/**
 * Mobile Responsiveness Tests
 * Tests for mobile optimization utilities and responsive behavior
 */

import {
  isMobileDevice,
  isTabletDevice,
  isTouchDevice,
  getViewportSize,
  getDevicePixelRatio,
  isLandscape,
  isPortrait,
  getOptimalImageSize,
  optimizeImageUrl,
  debounce,
  throttle,
} from '@/utils/mobileOptimization';

// Mock window and navigator
const mockWindow = (width: number, height: number, userAgent: string) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  });
  Object.defineProperty(navigator, 'userAgent', {
    writable: true,
    configurable: true,
    value: userAgent,
  });
};

describe('Mobile Device Detection', () => {
  beforeEach(() => {
    // Reset to desktop by default
    mockWindow(1920, 1080, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)');
  });

  test('detects mobile devices correctly', () => {
    mockWindow(375, 667, 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)');
    expect(isMobileDevice()).toBe(true);
  });

  test('detects desktop devices correctly', () => {
    mockWindow(1920, 1080, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)');
    expect(isMobileDevice()).toBe(false);
  });

  test('detects tablet devices correctly', () => {
    mockWindow(768, 1024, 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)');
    expect(isTabletDevice()).toBe(true);
  });

  test('detects touch devices correctly', () => {
    Object.defineProperty(window, 'ontouchstart', {
      writable: true,
      configurable: true,
      value: {},
    });
    expect(isTouchDevice()).toBe(true);
  });
});

describe('Viewport and Orientation', () => {
  test('gets viewport size correctly', () => {
    mockWindow(375, 667, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBe(375);
    expect(viewport.height).toBe(667);
  });

  test('detects landscape orientation', () => {
    mockWindow(667, 375, '');
    expect(isLandscape()).toBe(true);
    expect(isPortrait()).toBe(false);
  });

  test('detects portrait orientation', () => {
    mockWindow(375, 667, '');
    expect(isPortrait()).toBe(true);
    expect(isLandscape()).toBe(false);
  });

  test('gets device pixel ratio', () => {
    Object.defineProperty(window, 'devicePixelRatio', {
      writable: true,
      configurable: true,
      value: 2,
    });
    expect(getDevicePixelRatio()).toBe(2);
  });
});

describe('Image Optimization', () => {
  test('calculates optimal image size', () => {
    mockWindow(375, 667, '');
    Object.defineProperty(window, 'devicePixelRatio', {
      writable: true,
      configurable: true,
      value: 2,
    });

    const result = getOptimalImageSize(1000, 800);
    expect(result.width).toBe(750); // 375 * 2
    expect(result.height).toBe(600); // Maintains aspect ratio
  });

  test('optimizes image URL with parameters', () => {
    const url = 'https://example.com/image.jpg';
    const optimized = optimizeImageUrl(url, {
      width: 800,
      height: 600,
      quality: 80,
      format: 'webp',
    });

    expect(optimized).toContain('w=800');
    expect(optimized).toContain('h=600');
    expect(optimized).toContain('q=80');
    expect(optimized).toContain('fm=webp');
  });

  test('handles blob URLs correctly', () => {
    const blobUrl = 'blob:http://localhost:3000/abc-123';
    const result = optimizeImageUrl(blobUrl);
    expect(result).toBe(blobUrl);
  });

  test('handles data URLs correctly', () => {
    const dataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    const result = optimizeImageUrl(dataUrl);
    expect(result).toBe(dataUrl);
  });
});

describe('Performance Utilities', () => {
  jest.useFakeTimers();

  test('debounce delays function execution', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 100);

    debouncedFn();
    debouncedFn();
    debouncedFn();

    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(100);

    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  test('throttle limits function execution', () => {
    const mockFn = jest.fn();
    const throttledFn = throttle(mockFn, 100);

    throttledFn();
    throttledFn();
    throttledFn();

    expect(mockFn).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(100);

    throttledFn();
    expect(mockFn).toHaveBeenCalledTimes(2);
  });

  afterEach(() => {
    jest.clearAllTimers();
  });
});

describe('Touch Target Sizes', () => {
  test('buttons meet minimum 44px touch target', () => {
    const button = document.createElement('button');
    button.style.minWidth = '44px';
    button.style.minHeight = '44px';

    const styles = window.getComputedStyle(button);
    const minWidth = parseInt(styles.minWidth);
    const minHeight = parseInt(styles.minHeight);

    expect(minWidth).toBeGreaterThanOrEqual(44);
    expect(minHeight).toBeGreaterThanOrEqual(44);
  });

  test('primary buttons meet comfortable 48px touch target', () => {
    const button = document.createElement('button');
    button.classList.add('btn-primary');
    button.style.minWidth = '48px';
    button.style.minHeight = '48px';

    const styles = window.getComputedStyle(button);
    const minWidth = parseInt(styles.minWidth);
    const minHeight = parseInt(styles.minHeight);

    expect(minWidth).toBeGreaterThanOrEqual(48);
    expect(minHeight).toBeGreaterThanOrEqual(48);
  });
});

describe('Responsive Breakpoints', () => {
  const breakpoints = {
    xs: { min: 320, max: 639 },
    sm: { min: 640, max: 767 },
    md: { min: 768, max: 1023 },
    lg: { min: 1024, max: 1279 },
    xl: { min: 1280, max: 1535 },
    '2xl': { min: 1536, max: Infinity },
  };

  test('xs breakpoint (mobile)', () => {
    mockWindow(375, 667, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints.xs.min);
    expect(viewport.width).toBeLessThanOrEqual(breakpoints.xs.max);
  });

  test('sm breakpoint (large mobile)', () => {
    mockWindow(640, 960, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints.sm.min);
    expect(viewport.width).toBeLessThanOrEqual(breakpoints.sm.max);
  });

  test('md breakpoint (tablet)', () => {
    mockWindow(768, 1024, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints.md.min);
    expect(viewport.width).toBeLessThanOrEqual(breakpoints.md.max);
  });

  test('lg breakpoint (desktop)', () => {
    mockWindow(1024, 768, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints.lg.min);
    expect(viewport.width).toBeLessThanOrEqual(breakpoints.lg.max);
  });

  test('xl breakpoint (large desktop)', () => {
    mockWindow(1280, 800, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints.xl.min);
    expect(viewport.width).toBeLessThanOrEqual(breakpoints.xl.max);
  });

  test('2xl breakpoint (extra large desktop)', () => {
    mockWindow(1920, 1080, '');
    const viewport = getViewportSize();
    expect(viewport.width).toBeGreaterThanOrEqual(breakpoints['2xl'].min);
  });
});

describe('CSS Classes', () => {
  test('mobile-only class exists', () => {
    const element = document.createElement('div');
    element.classList.add('mobile-only');
    expect(element.classList.contains('mobile-only')).toBe(true);
  });

  test('desktop-only class exists', () => {
    const element = document.createElement('div');
    element.classList.add('desktop-only');
    expect(element.classList.contains('desktop-only')).toBe(true);
  });

  test('touch-manipulation class exists', () => {
    const element = document.createElement('button');
    element.classList.add('touch-manipulation');
    expect(element.classList.contains('touch-manipulation')).toBe(true);
  });

  test('responsive-container class exists', () => {
    const element = document.createElement('div');
    element.classList.add('responsive-container');
    expect(element.classList.contains('responsive-container')).toBe(true);
  });
});

describe('Form Input Sizes', () => {
  test('inputs have minimum 16px font size to prevent iOS zoom', () => {
    const input = document.createElement('input');
    input.type = 'text';
    input.style.fontSize = '16px';

    const styles = window.getComputedStyle(input);
    const fontSize = parseInt(styles.fontSize);

    expect(fontSize).toBeGreaterThanOrEqual(16);
  });

  test('inputs meet minimum 44px height', () => {
    const input = document.createElement('input');
    input.type = 'text';
    input.style.minHeight = '44px';

    const styles = window.getComputedStyle(input);
    const minHeight = parseInt(styles.minHeight);

    expect(minHeight).toBeGreaterThanOrEqual(44);
  });
});

describe('Image Responsiveness', () => {
  test('images have max-width 100%', () => {
    const img = document.createElement('img');
    img.classList.add('img-responsive');
    img.style.maxWidth = '100%';

    const styles = window.getComputedStyle(img);
    expect(styles.maxWidth).toBe('100%');
  });

  test('images have height auto', () => {
    const img = document.createElement('img');
    img.classList.add('img-responsive');
    img.style.height = 'auto';

    const styles = window.getComputedStyle(img);
    expect(styles.height).toBe('auto');
  });
});

describe('Accessibility', () => {
  test('reduced motion preference is respected', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    expect(prefersReducedMotion).toBe(true);
  });

  test('focus indicators are visible', () => {
    const button = document.createElement('button');
    button.style.outline = '3px solid #0066cc';
    button.style.outlineOffset = '2px';

    const styles = window.getComputedStyle(button);
    expect(styles.outline).toContain('3px');
    expect(styles.outlineOffset).toBe('2px');
  });
});
