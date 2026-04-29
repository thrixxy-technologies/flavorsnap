// Accessibility Utilities

export interface A11yTestResult {
  type: string;
  passed: boolean;
  message: string;
  element?: Element;
  details?: any;
}

export interface A11yTestSuite {
  name: string;
  tests: A11yTestResult[];
  passed: number;
  failed: number;
  total: number;
}

export interface ColorContrastResult {
  ratio: number;
  aa: boolean;
  aaa: boolean;
  foreground: string;
  background: string;
}

export interface KeyboardNavigationMap {
  [key: string]: {
    element: Element;
    index: number;
    group?: string;
  };
}

class A11yUtils {
  private static instance: A11yUtils;
  private colorCache: Map<string, ColorContrastResult> = new Map();

  private constructor() {}

  public static getInstance(): A11yUtils {
    if (!A11yUtils.instance) {
      A11yUtils.instance = new A11yUtils();
    }
    return A11yUtils.instance;
  }

  // Color contrast utilities
  public hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }

  public getLuminance(rgb: { r: number; g: number; b: number }): number {
    const { r, g, b } = rgb;
    const [rs, gs, bs] = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  public getContrastRatio(foreground: string, background: string): ColorContrastResult {
    const cacheKey = `${foreground}-${background}`;
    if (this.colorCache.has(cacheKey)) {
      return this.colorCache.get(cacheKey)!;
    }

    const fgRgb = this.hexToRgb(foreground);
    const bgRgb = this.hexToRgb(background);

    if (!fgRgb || !bgRgb) {
      throw new Error('Invalid color format');
    }

    const fgLuminance = this.getLuminance(fgRgb);
    const bgLuminance = this.getLuminance(bgRgb);
    
    const ratio = (Math.max(fgLuminance, bgLuminance) + 0.05) / (Math.min(fgLuminance, bgLuminance) + 0.05);
    
    const result: ColorContrastResult = {
      ratio: Math.round(ratio * 100) / 100,
      aa: ratio >= 4.5,
      aaa: ratio >= 7,
      foreground,
      background
    };

    this.colorCache.set(cacheKey, result);
    return result;
  }

  public getComputedColor(element: Element, property: 'color' | 'backgroundColor'): string {
    const styles = window.getComputedStyle(element);
    const color = styles.getPropertyValue(property);
    
    // Convert RGB to hex
    if (color.startsWith('rgb')) {
      const rgbMatch = color.match(/\d+/g);
      if (rgbMatch && rgbMatch.length >= 3) {
        const r = parseInt(rgbMatch[0]).toString(16).padStart(2, '0');
        const g = parseInt(rgbMatch[1]).toString(16).padStart(2, '0');
        const b = parseInt(rgbMatch[2]).toString(16).padStart(2, '0');
        return `#${r}${g}${b}`;
      }
    }
    
    return color;
  }

  // Focus management
  public getFocusableElements(container: Element = document.body): Element[] {
    const focusableSelectors = [
      'button:not([disabled])',
      '[href]',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      'details summary',
      'audio controls',
      'video controls',
      '[role="button"]',
      '[role="link"]',
      '[role="menuitem"]',
      '[role="option"]',
      '[role="tab"]'
    ].join(', ');

    return Array.from(container.querySelectorAll(focusableSelectors)).filter(
      element => this.isVisible(element) && !this.isDisabled(element)
    );
  }

  public getKeyboardNavigationMap(): KeyboardNavigationMap {
    const focusableElements = this.getFocusableElements();
    const map: KeyboardNavigationMap = {};

    focusableElements.forEach((element, index) => {
      const group = this.getNavigationGroup(element);
      map[index.toString()] = { element, index, group };
    });

    return map;
  }

  private getNavigationGroup(element: Element): string | undefined {
    // Determine navigation group based on context
    const parent = element.closest('[role="navigation"], nav, [role="menu"], [role="toolbar"]');
    if (parent) {
      return parent.id || parent.tagName.toLowerCase();
    }
    return undefined;
  }

  // Screen reader utilities
  public announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  public createLiveRegion(id: string, priority: 'polite' | 'assertive' = 'polite'): HTMLElement {
    const existingRegion = document.getElementById(id);
    if (existingRegion) {
      return existingRegion;
    }

    const region = document.createElement('div');
    region.id = id;
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', priority);
    region.setAttribute('aria-atomic', 'true');
    region.className = 'sr-only';
    
    document.body.appendChild(region);
    return region;
  }

  public updateLiveRegion(id: string, message: string): void {
    const region = document.getElementById(id);
    if (region) {
      region.textContent = message;
    }
  }

  // ARIA utilities
  public generateUniqueId(prefix: string = 'a11y'): string {
    return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
  }

  public setAriaLabel(element: Element, label: string): void {
    element.setAttribute('aria-label', label);
  }

  public setAriaDescribedBy(element: Element, descriptionId: string): void {
    const current = element.getAttribute('aria-describedby');
    const ids = current ? `${current} ${descriptionId}` : descriptionId;
    element.setAttribute('aria-describedby', ids.trim());
  }

  public setAriaLabelledBy(element: Element, labelId: string): void {
    element.setAttribute('aria-labelledby', labelId);
  }

  public setAriaExpanded(element: Element, expanded: boolean): void {
    element.setAttribute('aria-expanded', expanded.toString());
  }

  public setAriaPressed(element: Element, pressed: boolean): void {
    element.setAttribute('aria-pressed', pressed.toString());
  }

  public setAriaDisabled(element: Element, disabled: boolean): void {
    element.setAttribute('aria-disabled', disabled.toString());
  }

  // Visibility utilities
  public isVisible(element: Element): boolean {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }

    const styles = window.getComputedStyle(element);
    return (
      styles.display !== 'none' &&
      styles.visibility !== 'hidden' &&
      styles.opacity !== '0' &&
      element.offsetWidth > 0 &&
      element.offsetHeight > 0
    );
  }

  public isDisabled(element: Element): boolean {
    return (
      element.hasAttribute('disabled') ||
      element.getAttribute('aria-disabled') === 'true' ||
      (element as HTMLInputElement).disabled
    );
  }

  // Skip link utilities
  public createSkipLink(targetId: string, label: string): HTMLElement {
    const skipLink = document.createElement('a');
    skipLink.href = `#${targetId}`;
    skipLink.textContent = label;
    skipLink.className = 'skip-link';
    skipLink.setAttribute('role', 'navigation');
    skipLink.setAttribute('aria-label', `Skip to ${label}`);

    document.body.insertBefore(skipLink, document.body.firstChild);
    return skipLink;
  }

  public removeSkipLink(skipLink: HTMLElement): void {
    if (skipLink && skipLink.parentNode) {
      skipLink.parentNode.removeChild(skipLink);
    }
  }

  // Focus trap utilities
  public createFocusTrap(container: Element): {
    activate: () => void;
    deactivate: () => void;
    isActive: () => boolean;
  } {
    let isActive = false;
    let previousFocus: Element | null = null;
    const focusableElements = this.getFocusableElements(container);
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        if (event.shiftKey) {
          if (document.activeElement === firstElement) {
            event.preventDefault();
            (lastElement as HTMLElement).focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            event.preventDefault();
            (firstElement as HTMLElement).focus();
          }
        }
      }
    };

    return {
      activate: () => {
        if (isActive) return;
        
        isActive = true;
        previousFocus = document.activeElement;
        container.addEventListener('keydown', handleKeyDown);
        
        if (firstElement) {
          (firstElement as HTMLElement).focus();
        }
      },
      deactivate: () => {
        if (!isActive) return;
        
        isActive = false;
        container.removeEventListener('keydown', handleKeyDown);
        
        if (previousFocus && previousFocus !== document.body) {
          (previousFocus as HTMLElement).focus();
        }
      },
      isActive: () => isActive
    };
  }

  // Testing utilities
  public runAccessibilityTests(): A11yTestSuite {
    const tests: A11yTestResult[] = [
      this.testColorContrast(),
      this.testKeyboardNavigation(),
      this.testFocusIndicators(),
      this.testARIALabels(),
      this.testHeadingStructure(),
      this.testFormLabels(),
      this.testImageAltText(),
      this.testLinkPurpose(),
      this.testTableHeaders(),
      this.testLandmarks()
    ];

    const passed = tests.filter(test => test.passed).length;
    const failed = tests.length - passed;

    return {
      name: 'Comprehensive Accessibility Test',
      tests,
      passed,
      failed,
      total: tests.length
    };
  }

  private testColorContrast(): A11yTestResult {
    const elements = document.querySelectorAll('*');
    const failures: Element[] = [];

    elements.forEach(element => {
      const styles = window.getComputedStyle(element);
      const color = this.getComputedColor(element, 'color');
      const bg = this.getComputedColor(element, 'backgroundColor');

      if (color && bg && color !== 'transparent' && bg !== 'transparent') {
        try {
          const contrast = this.getContrastRatio(color, bg);
          if (!contrast.aa) {
            failures.push(element);
          }
        } catch (error) {
          // Skip invalid colors
        }
      }
    });

    return {
      type: 'Color Contrast',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All elements meet WCAG AA contrast requirements'
        : `${failures.length} elements fail contrast requirements`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testKeyboardNavigation(): A11yTestResult {
    const focusableElements = this.getFocusableElements();
    const hasFocusableElements = focusableElements.length > 0;
    
    return {
      type: 'Keyboard Navigation',
      passed: hasFocusableElements,
      message: hasFocusableElements 
        ? `Found ${focusableElements.length} focusable elements`
        : 'No focusable elements found',
      details: { focusableCount: focusableElements.length }
    };
  }

  private testFocusIndicators(): A11yTestResult {
    const focusableElements = this.getFocusableElements();
    const failures: Element[] = [];

    focusableElements.forEach(element => {
      const styles = window.getComputedStyle(element);
      const hasFocusStyle = styles.outline !== 'none' || styles.boxShadow !== 'none';
      
      if (!hasFocusStyle) {
        failures.push(element);
      }
    });

    return {
      type: 'Focus Indicators',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All focusable elements have visible focus indicators'
        : `${failures.length} elements lack focus indicators`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testARIALabels(): A11yTestResult {
    const interactiveElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [role="button"], [role="link"]'
    );
    const failures: Element[] = [];

    interactiveElements.forEach(element => {
      const hasLabel = 
        element.getAttribute('aria-label') ||
        element.getAttribute('aria-labelledby') ||
        element.getAttribute('title') ||
        element.textContent?.trim() ||
        (element as HTMLInputElement).placeholder;

      if (!hasLabel) {
        failures.push(element);
      }
    });

    return {
      type: 'ARIA Labels',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All interactive elements have accessible labels'
        : `${failures.length} interactive elements lack labels`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testHeadingStructure(): A11yTestResult {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const failures: Element[] = [];
    let lastLevel = 0;

    headings.forEach(heading => {
      const level = parseInt(heading.tagName.charAt(1));
      
      if (level > lastLevel + 1) {
        failures.push(heading);
      }
      
      lastLevel = level;
    });

    return {
      type: 'Heading Structure',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'Heading structure is logical'
        : `${failures.length} heading level skips detected`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testFormLabels(): A11yTestResult {
    const inputs = document.querySelectorAll('input, select, textarea');
    const failures: Element[] = [];

    inputs.forEach(input => {
      const hasLabel = 
        input.getAttribute('aria-label') ||
        input.getAttribute('aria-labelledby') ||
        document.querySelector(`label[for="${input.id}"]`) ||
        input.closest('label');

      if (!hasLabel) {
        failures.push(input);
      }
    });

    return {
      type: 'Form Labels',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All form inputs have associated labels'
        : `${failures.length} form inputs lack labels`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testImageAltText(): A11yTestResult {
    const images = document.querySelectorAll('img');
    const failures: Element[] = [];

    images.forEach(img => {
      const alt = img.getAttribute('alt');
      
      // Check if image is decorative (empty alt) or has descriptive alt text
      if (alt === null) {
        failures.push(img);
      }
    });

    return {
      type: 'Image Alt Text',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All images have alt attributes'
        : `${failures.length} images lack alt text`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testLinkPurpose(): A11yTestResult {
    const links = document.querySelectorAll('a[href]');
    const failures: Element[] = [];

    links.forEach(link => {
      const text = link.textContent?.trim();
      const href = link.getAttribute('href');
      
      if (!text || text === 'click here' || text === 'read more' || text === 'learn more') {
        failures.push(link);
      }
    });

    return {
      type: 'Link Purpose',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All links have descriptive text'
        : `${failures.length} links have unclear purpose`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testTableHeaders(): A11yTestResult {
    const tables = document.querySelectorAll('table');
    const failures: Element[] = [];

    tables.forEach(table => {
      const hasHeaders = table.querySelector('th') || table.querySelector('[scope]');
      const hasCaption = table.querySelector('caption');
      
      if (!hasHeaders || !hasCaption) {
        failures.push(table);
      }
    });

    return {
      type: 'Table Headers',
      passed: failures.length === 0,
      message: failures.length === 0 
        ? 'All tables have proper headers and captions'
        : `${failures.length} tables lack headers or captions`,
      element: failures[0],
      details: { failures: failures.length }
    };
  }

  private testLandmarks(): A11yTestResult {
    const hasMain = document.querySelector('main, [role="main"]');
    const hasNav = document.querySelector('nav, [role="navigation"]');
    const hasHeader = document.querySelector('header, [role="banner"]');
    const hasFooter = document.querySelector('footer, [role="contentinfo"]');
    
    const hasRequiredLandmarks = hasMain;
    const hasOptionalLandmarks = hasNav || hasHeader || hasFooter;

    return {
      type: 'Landmarks',
      passed: hasRequiredLandmarks,
      message: hasRequiredLandmarks 
        ? 'Page has required landmarks'
        : 'Page missing main landmark',
      details: { 
        hasMain: !!hasMain,
        hasNav: !!hasNav,
        hasHeader: !!hasHeader,
        hasFooter: !!hasFooter
      }
    };
  }

  // Device detection utilities
  public detectScreenReader(): boolean {
    return (
      window.speechSynthesis !== undefined ||
      navigator.userAgent.includes('NVDA') ||
      navigator.userAgent.includes('JAWS') ||
      navigator.userAgent.includes('VoiceOver') ||
      navigator.userAgent.includes('ChromeVox')
    );
  }

  public detectHighContrast(): boolean {
    return (
      window.matchMedia('(prefers-contrast: high)').matches ||
      window.matchMedia('(forced-colors: active)').matches
    );
  }

  public detectReducedMotion(): boolean {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  public detectKeyboardNavigation(): boolean {
    let lastKeyboardUse = 0;
    let detected = false;

    const handleKeyboardUse = () => {
      lastKeyboardUse = Date.now();
      detected = true;
    };

    document.addEventListener('keydown', handleKeyboardUse);

    return () => {
      document.removeEventListener('keydown', handleKeyboardUse);
      return detected && (Date.now() - lastKeyboardUse) < 5000;
    };
  }

  // Utility methods for common accessibility patterns
  public createAccessibleButton(
    text: string,
    onClick: () => void,
    options: {
      ariaLabel?: string;
      ariaDescribedBy?: string;
      ariaExpanded?: boolean;
      ariaPressed?: boolean;
      disabled?: boolean;
      className?: string;
    } = {}
  ): HTMLButtonElement {
    const button = document.createElement('button');
    button.textContent = text;
    button.className = `accessible-button ${options.className || ''}`;
    
    if (options.ariaLabel) {
      this.setAriaLabel(button, options.ariaLabel);
    }
    
    if (options.ariaDescribedBy) {
      this.setAriaDescribedBy(button, options.ariaDescribedBy);
    }
    
    if (options.ariaExpanded !== undefined) {
      this.setAriaExpanded(button, options.ariaExpanded);
    }
    
    if (options.ariaPressed !== undefined) {
      this.setAriaPressed(button, options.ariaPressed);
    }
    
    if (options.disabled) {
      button.disabled = true;
    }
    
    button.addEventListener('click', onClick);
    
    return button;
  }

  public createAccessibleLink(
    href: string,
    text: string,
    options: {
      ariaLabel?: string;
      ariaDescribedBy?: string;
      target?: string;
      className?: string;
    } = {}
  ): HTMLAnchorElement {
    const link = document.createElement('a');
    link.href = href;
    link.textContent = text;
    link.className = `accessible-link ${options.className || ''}`;
    
    if (options.ariaLabel) {
      this.setAriaLabel(link, options.ariaLabel);
    }
    
    if (options.ariaDescribedBy) {
      this.setAriaDescribedBy(link, options.ariaDescribedBy);
    }
    
    if (options.target) {
      link.target = options.target;
    }
    
    return link;
  }
}

export const a11yUtils = A11yUtils.getInstance();

export default a11yUtils;
