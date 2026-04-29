// WCAG Compliance, Color Contrast, Keyboard Navigation, Screen Reader Audit
import type { A11yIssue, IssueSeverity } from './accessibilityTester';

export type WCAGLevel = 'A' | 'AA' | 'AAA';

// ─── Helpers ────────────────────────────────────────────────────────────────

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return m ? { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) } : null;
}

function rgbStringToHex(rgb: string): string | null {
  const m = rgb.match(/\d+/g);
  if (!m || m.length < 3) return null;
  return '#' + [m[0], m[1], m[2]].map(n => parseInt(n).toString(16).padStart(2, '0')).join('');
}

function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(fg: string, bg: string): number | null {
  const fgHex = fg.startsWith('rgb') ? rgbStringToHex(fg) : fg;
  const bgHex = bg.startsWith('rgb') ? rgbStringToHex(bg) : bg;
  if (!fgHex || !bgHex) return null;
  const fgRgb = hexToRgb(fgHex);
  const bgRgb = hexToRgb(bgHex);
  if (!fgRgb || !bgRgb) return null;
  const l1 = getLuminance(fgRgb.r, fgRgb.g, fgRgb.b);
  const l2 = getLuminance(bgRgb.r, bgRgb.g, bgRgb.b);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

function elementSelector(el: Element): string {
  const id = el.id ? `#${el.id}` : '';
  const cls = el.classList.length ? `.${Array.from(el.classList).slice(0, 2).join('.')}` : '';
  return `${el.tagName.toLowerCase()}${id}${cls}`;
}

function issue(
  rule: string,
  wcag: string,
  severity: IssueSeverity,
  passed: boolean,
  message: string,
  el?: Element
): A11yIssue {
  return {
    id: `${rule}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    rule,
    wcagCriteria: wcag,
    severity,
    passed,
    message,
    element: el ? el.outerHTML.slice(0, 120) : undefined,
    selector: el ? elementSelector(el) : undefined,
  };
}

// ─── Individual checks ───────────────────────────────────────────────────────

function checkImagesAlt(root: Element): A11yIssue[] {
  return Array.from(root.querySelectorAll('img')).map(img => {
    const hasAlt = img.hasAttribute('alt');
    return issue(
      'image-alt',
      'WCAG 1.1.1',
      'critical',
      hasAlt,
      hasAlt ? 'Image has alt attribute' : 'Image missing alt attribute',
      img
    );
  });
}

function checkFormLabels(root: Element): A11yIssue[] {
  const inputs = Array.from(
    root.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea')
  );
  return inputs.map(input => {
    const id = input.id;
    const hasLabel =
      (id && root.querySelector(`label[for="${id}"]`) !== null) ||
      input.hasAttribute('aria-label') ||
      input.hasAttribute('aria-labelledby') ||
      input.closest('label') !== null;
    return issue(
      'form-label',
      'WCAG 1.3.1',
      'critical',
      !!hasLabel,
      hasLabel ? 'Form field has accessible label' : 'Form field missing accessible label',
      input
    );
  });
}

function checkHeadingOrder(root: Element): A11yIssue[] {
  const headings = Array.from(root.querySelectorAll('h1,h2,h3,h4,h5,h6'));
  const results: A11yIssue[] = [];
  let prevLevel = 0;
  for (const h of headings) {
    const level = parseInt(h.tagName[1]);
    const skipped = prevLevel > 0 && level > prevLevel + 1;
    results.push(
      issue(
        'heading-order',
        'WCAG 1.3.1',
        'moderate',
        !skipped,
        skipped
          ? `Heading level skipped: h${prevLevel} → h${level}`
          : `Heading order correct (h${level})`,
        h
      )
    );
    prevLevel = level;
  }
  return results;
}

function checkColorContrast(root: Element): A11yIssue[] {
  const textEls = Array.from(
    root.querySelectorAll('p, span, a, button, label, h1, h2, h3, h4, h5, h6, li, td, th')
  ).slice(0, 50); // cap for performance

  return textEls.map(el => {
    const styles = window.getComputedStyle(el);
    const fg = styles.color;
    const bg = styles.backgroundColor;
    const ratio = contrastRatio(fg, bg);
    const fontSize = parseFloat(styles.fontSize);
    const bold = parseInt(styles.fontWeight) >= 700;
    const isLargeText = fontSize >= 18 || (bold && fontSize >= 14);
    const required = isLargeText ? 3 : 4.5;
    const passed = ratio !== null && ratio >= required;
    return issue(
      'color-contrast',
      'WCAG 1.4.3',
      'serious',
      passed,
      ratio !== null
        ? `Contrast ratio ${ratio.toFixed(2)}:1 (required ${required}:1)`
        : 'Could not determine contrast ratio',
      el
    );
  });
}

function checkKeyboardFocusable(root: Element): A11yIssue[] {
  const interactive = Array.from(
    root.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"], [onclick]')
  );
  return interactive.map(el => {
    const tabindex = el.getAttribute('tabindex');
    const focusable = tabindex !== '-1';
    return issue(
      'keyboard-focusable',
      'WCAG 2.1.1',
      'critical',
      focusable,
      focusable ? 'Element is keyboard focusable' : 'Element not keyboard focusable (tabindex="-1")',
      el
    );
  });
}

function checkFocusVisible(root: Element): A11yIssue[] {
  const focusable = Array.from(
    root.querySelectorAll('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])')
  ).slice(0, 30);
  return focusable.map(el => {
    const styles = window.getComputedStyle(el);
    const outline = styles.outline;
    const outlineWidth = parseFloat(styles.outlineWidth);
    const hasVisibleFocus = outline !== 'none' && outlineWidth > 0;
    return issue(
      'focus-visible',
      'WCAG 2.4.7',
      'serious',
      hasVisibleFocus,
      hasVisibleFocus ? 'Focus indicator visible' : 'Focus indicator may not be visible',
      el
    );
  });
}

function checkAriaRoles(root: Element): A11yIssue[] {
  const validRoles = new Set([
    'alert', 'alertdialog', 'application', 'article', 'banner', 'button',
    'cell', 'checkbox', 'columnheader', 'combobox', 'complementary',
    'contentinfo', 'definition', 'dialog', 'directory', 'document',
    'feed', 'figure', 'form', 'grid', 'gridcell', 'group', 'heading',
    'img', 'link', 'list', 'listbox', 'listitem', 'log', 'main',
    'marquee', 'math', 'menu', 'menubar', 'menuitem', 'menuitemcheckbox',
    'menuitemradio', 'navigation', 'none', 'note', 'option', 'presentation',
    'progressbar', 'radio', 'radiogroup', 'region', 'row', 'rowgroup',
    'rowheader', 'scrollbar', 'search', 'searchbox', 'separator',
    'slider', 'spinbutton', 'status', 'switch', 'tab', 'table',
    'tablist', 'tabpanel', 'term', 'textbox', 'timer', 'toolbar',
    'tooltip', 'tree', 'treegrid', 'treeitem',
  ]);
  return Array.from(root.querySelectorAll('[role]')).map(el => {
    const role = el.getAttribute('role') ?? '';
    const valid = validRoles.has(role);
    return issue(
      'aria-roles',
      'WCAG 4.1.2',
      'serious',
      valid,
      valid ? `Valid ARIA role: "${role}"` : `Invalid ARIA role: "${role}"`,
      el
    );
  });
}

function checkLandmarks(root: Element): A11yIssue[] {
  const hasMain =
    root.querySelector('main, [role="main"]') !== null;
  const hasNav =
    root.querySelector('nav, [role="navigation"]') !== null;
  return [
    issue('landmark-main', 'WCAG 1.3.6', 'moderate', hasMain,
      hasMain ? 'Page has main landmark' : 'Page missing main landmark'),
    issue('landmark-nav', 'WCAG 1.3.6', 'minor', hasNav,
      hasNav ? 'Page has navigation landmark' : 'Page missing navigation landmark'),
  ];
}

function checkPageTitle(): A11yIssue[] {
  if (typeof document === 'undefined') return [];
  const hasTitle = document.title.trim().length > 0;
  return [
    issue('page-title', 'WCAG 2.4.2', 'serious', hasTitle,
      hasTitle ? `Page title: "${document.title}"` : 'Page is missing a title'),
  ];
}

function checkLanguage(): A11yIssue[] {
  if (typeof document === 'undefined') return [];
  const lang = document.documentElement.getAttribute('lang');
  const hasLang = !!lang && lang.trim().length > 0;
  return [
    issue('html-lang', 'WCAG 3.1.1', 'serious', hasLang,
      hasLang ? `Page language set: "${lang}"` : 'Page missing lang attribute on <html>'),
  ];
}

function checkScreenReaderText(root: Element): A11yIssue[] {
  // Check buttons/links have accessible names
  const els = Array.from(root.querySelectorAll('button, a[href], [role="button"]'));
  return els.map(el => {
    const text = (el.textContent ?? '').trim();
    const ariaLabel = el.getAttribute('aria-label') ?? '';
    const ariaLabelledby = el.getAttribute('aria-labelledby') ?? '';
    const title = el.getAttribute('title') ?? '';
    const hasName = text.length > 0 || ariaLabel.length > 0 || ariaLabelledby.length > 0 || title.length > 0;
    return issue(
      'accessible-name',
      'WCAG 4.1.2',
      'critical',
      hasName,
      hasName ? 'Element has accessible name' : 'Element missing accessible name',
      el
    );
  });
}

// ─── Audit runner ────────────────────────────────────────────────────────────

class A11yAudit {
  private static instance: A11yAudit;

  private constructor() {}

  static getInstance(): A11yAudit {
    if (!A11yAudit.instance) {
      A11yAudit.instance = new A11yAudit();
    }
    return A11yAudit.instance;
  }

  async runAll(root: Element = document.body, level: WCAGLevel = 'AA'): Promise<A11yIssue[]> {
    const checks: A11yIssue[] = [
      ...checkPageTitle(),
      ...checkLanguage(),
      ...checkLandmarks(root),
      ...checkImagesAlt(root),
      ...checkFormLabels(root),
      ...checkHeadingOrder(root),
      ...checkAriaRoles(root),
      ...checkScreenReaderText(root),
      ...checkKeyboardFocusable(root),
      ...checkFocusVisible(root),
    ];

    // AAA-only: color contrast (expensive, skip for level A)
    if (level === 'AA' || level === 'AAA') {
      checks.push(...checkColorContrast(root));
    }

    return checks;
  }

  // Individual check exports for targeted use
  checkColorContrast = checkColorContrast;
  checkKeyboardFocusable = checkKeyboardFocusable;
  checkScreenReaderText = checkScreenReaderText;
  checkFormLabels = checkFormLabels;
  checkImagesAlt = checkImagesAlt;
}

export const a11yAudit = A11yAudit.getInstance();
