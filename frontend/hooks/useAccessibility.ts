import { useState, useEffect, useCallback, useRef } from 'react';

export interface AccessibilitySettings {
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
  focusVisible: boolean;
  darkMode: boolean;
  keyboardNavigation: boolean;
  skipLinks: boolean;
  focusTraps: boolean;
  screenReaderOptimized: boolean;
  ariaLabels: boolean;
  liveRegions: boolean;
  clickDelay: boolean;
  hoverDelay: boolean;
  errorAnnouncements: boolean;
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  colorBlindness: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';
  saturation: number;
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  action: () => void;
  description: string;
  global?: boolean;
}

export interface FocusTrap {
  activate: () => void;
  deactivate: () => void;
  isActive: boolean;
}

export interface UseAccessibilityReturn {
  settings: AccessibilitySettings;
  updateSetting: <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => void;
  resetSettings: () => void;
  
  // Keyboard navigation
  addKeyboardShortcut: (shortcut: KeyboardShortcut) => () => void;
  removeKeyboardShortcut: (shortcut: KeyboardShortcut) => void;
  handleKeyDown: (event: KeyboardEvent) => void;
  
  // Focus management
  trapFocus: (container: HTMLElement) => FocusTrap;
  setFocus: (element: HTMLElement) => void;
  restoreFocus: () => void;
  
  // Screen reader
  announceToScreenReader: (message: string, priority?: 'polite' | 'assertive') => void;
  updateAriaLabel: (element: HTMLElement, label: string) => void;
  updateAriaDescribedBy: (element: HTMLElement, descriptionId: string) => void;
  
  // Skip links
  addSkipLink: (target: string, label: string) => void;
  removeSkipLink: (target: string) => void;
  
  // Testing
  runAccessibilityTest: (testType: string) => Promise<boolean[]>;
  
  // Utilities
  detectScreenReader: () => boolean;
  detectHighContrast: () => boolean;
  detectReducedMotion: () => boolean;
  detectKeyboardNavigation: () => boolean;
}

const DEFAULT_SETTINGS: AccessibilitySettings = {
  highContrast: false,
  largeText: false,
  reducedMotion: false,
  focusVisible: true,
  darkMode: false,
  keyboardNavigation: true,
  skipLinks: true,
  focusTraps: false,
  screenReaderOptimized: false,
  ariaLabels: true,
  liveRegions: true,
  clickDelay: false,
  hoverDelay: false,
  errorAnnouncements: true,
  fontSize: 16,
  lineHeight: 1.5,
  letterSpacing: 0,
  colorBlindness: 'none',
  saturation: 100
};

export const useAccessibility = (): UseAccessibilityReturn => {
  const [settings, setSettings] = useState<AccessibilitySettings>(DEFAULT_SETTINGS);
  const [keyboardShortcuts, setKeyboardShortcuts] = useState<KeyboardShortcut[]>([]);
  const [skipLinks, setSkipLinks] = useState<Map<string, HTMLElement>>(new Map());
  const [focusTraps, setFocusTraps] = useState<Map<HTMLElement, FocusTrap>>(new Map());
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const liveRegionRef = useRef<HTMLDivElement | null>(null);

  // Load settings from localStorage
  useEffect(() => {
    try {
      const savedSettings = localStorage.getItem('accessibility-settings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      }
    } catch (error) {
      console.error('Failed to load accessibility settings:', error);
    }
  }, []);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('accessibility-settings', JSON.stringify(settings));
    applyAccessibilitySettings(settings);
  }, [settings]);

  // Create live region for screen reader announcements
  useEffect(() => {
    if (!liveRegionRef.current && settings.liveRegions) {
      liveRegionRef.current = document.createElement('div');
      liveRegionRef.current.setAttribute('role', 'status');
      liveRegionRef.current.setAttribute('aria-live', 'polite');
      liveRegionRef.current.setAttribute('aria-atomic', 'true');
      liveRegionRef.current.className = 'sr-only';
      document.body.appendChild(liveRegionRef.current);
    }

    return () => {
      if (liveRegionRef.current) {
        document.body.removeChild(liveRegionRef.current);
        liveRegionRef.current = null;
      }
    };
  }, [settings.liveRegions]);

  // Detect user preferences
  useEffect(() => {
    const mediaQueries = {
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)'),
      highContrast: window.matchMedia('(prefers-contrast: high)'),
      darkMode: window.matchMedia('(prefers-color-scheme: dark)')
    };

    const updateSettingsFromPreferences = () => {
      setSettings(prev => ({
        ...prev,
        reducedMotion: prev.reducedMotion || mediaQueries.reducedMotion.matches,
        highContrast: prev.highContrast || mediaQueries.highContrast.matches,
        darkMode: prev.darkMode || mediaQueries.darkMode.matches
      }));
    };

    updateSettingsFromPreferences();

    Object.values(mediaQueries).forEach(mq => {
      mq.addEventListener('change', updateSettingsFromPreferences);
    });

    return () => {
      Object.values(mediaQueries).forEach(mq => {
        mq.removeEventListener('change', updateSettingsFromPreferences);
      });
    };
  }, []);

  // Global keyboard event handler
  useEffect(() => {
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (!settings.keyboardNavigation) return;

      keyboardShortcuts.forEach(shortcut => {
        if (shortcut.global && matchesShortcut(event, shortcut)) {
          event.preventDefault();
          shortcut.action();
        }
      });
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, [keyboardShortcuts, settings.keyboardNavigation]);

  const applyAccessibilitySettings = (currentSettings: AccessibilitySettings) => {
    const root = document.documentElement;
    
    // Apply data attributes for CSS
    root.setAttribute('data-high-contrast', currentSettings.highContrast.toString());
    root.setAttribute('data-large-text', currentSettings.largeText.toString());
    root.setAttribute('data-reduced-motion', currentSettings.reducedMotion.toString());
    root.setAttribute('data-focus-visible', currentSettings.focusVisible.toString());
    root.setAttribute('data-dark-mode', currentSettings.darkMode.toString());
    root.setAttribute('data-screen-reader', currentSettings.screenReaderOptimized.toString());
    root.setAttribute('data-aria-labels', currentSettings.ariaLabels.toString());
    
    // Apply CSS custom properties
    root.style.setProperty('--font-size-base', `${currentSettings.fontSize}px`);
    root.style.setProperty('--line-height-base', currentSettings.lineHeight.toString());
    root.style.setProperty('--letter-spacing-base', `${currentSettings.letterSpacing}px`);
    root.style.setProperty('--saturation', `${currentSettings.saturation}%`);
    
    // Apply color blindness mode
    root.setAttribute('data-color-blindness', currentSettings.colorBlindness);
    
    // Add body classes for immediate visual feedback
    document.body.classList.toggle('high-contrast', currentSettings.highContrast);
    document.body.classList.toggle('large-text', currentSettings.largeText);
    document.body.classList.toggle('reduced-motion', currentSettings.reducedMotion);
    document.body.classList.toggle('dark-mode', currentSettings.darkMode);
    document.body.classList.toggle('screen-reader-opt', currentSettings.screenReaderOptimized);
    document.body.classList.toggle('keyboard-nav', currentSettings.keyboardNavigation);
  };

  const updateSetting = useCallback(<K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  // Keyboard navigation
  const addKeyboardShortcut = useCallback((shortcut: KeyboardShortcut) => {
    setKeyboardShortcuts(prev => [...prev, shortcut]);
    
    // Return cleanup function
    return () => {
      setKeyboardShortcuts(prev => prev.filter(s => s !== shortcut));
    };
  }, []);

  const removeKeyboardShortcut = useCallback((shortcut: KeyboardShortcut) => {
    setKeyboardShortcuts(prev => prev.filter(s => s !== shortcut));
  }, []);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!settings.keyboardNavigation) return;

    keyboardShortcuts.forEach(shortcut => {
      if (!shortcut.global && matchesShortcut(event, shortcut)) {
        event.preventDefault();
        shortcut.action();
      }
    });
  }, [keyboardShortcuts, settings.keyboardNavigation]);

  // Focus management
  const trapFocus = useCallback((container: HTMLElement): FocusTrap => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const trap: FocusTrap = {
      activate: () => {
        previousFocusRef.current = document.activeElement as HTMLElement;
        if (firstElement) {
          firstElement.focus();
        }
        setFocusTraps(prev => new Map(prev.set(container, trap)));
      },
      deactivate: () => {
        setFocusTraps(prev => {
          const newMap = new Map(prev);
          newMap.delete(container);
          return newMap;
        });
        if (previousFocusRef.current) {
          previousFocusRef.current.focus();
        }
      },
      isActive: focusTraps.has(container)
    };

    const handleTrapKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        if (event.shiftKey) {
          if (document.activeElement === firstElement) {
            event.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement?.focus();
          }
        }
      }
    };

    container.addEventListener('keydown', handleTrapKeyDown);
    
    return trap;
  }, [focusTraps]);

  const setFocus = useCallback((element: HTMLElement) => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    element.focus();
  }, []);

  const restoreFocus = useCallback(() => {
    if (previousFocusRef.current) {
      previousFocusRef.current.focus();
      previousFocusRef.current = null;
    }
  }, []);

  // Screen reader
  const announceToScreenReader = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!settings.liveRegions || !settings.screenReaderOptimized) return;

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
  }, [settings.liveRegions, settings.screenReaderOptimized]);

  const updateAriaLabel = useCallback((element: HTMLElement, label: string) => {
    if (settings.ariaLabels) {
      element.setAttribute('aria-label', label);
    }
  }, [settings.ariaLabels]);

  const updateAriaDescribedBy = useCallback((element: HTMLElement, descriptionId: string) => {
    if (settings.ariaLabels) {
      element.setAttribute('aria-describedby', descriptionId);
    }
  }, [settings.ariaLabels]);

  // Skip links
  const addSkipLink = useCallback((target: string, label: string) => {
    const skipLink = document.createElement('a');
    skipLink.href = `#${target}`;
    skipLink.textContent = label;
    skipLink.className = 'skip-link';
    skipLink.setAttribute('role', 'navigation');
    skipLink.setAttribute('aria-label', `Skip to ${label}`);
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    setSkipLinks(prev => new Map(prev.set(target, skipLink)));
  }, []);

  const removeSkipLink = useCallback((target: string) => {
    const skipLink = skipLinks.get(target);
    if (skipLink) {
      document.body.removeChild(skipLink);
      setSkipLinks(prev => {
        const newMap = new Map(prev);
        newMap.delete(target);
        return newMap;
      });
    }
  }, [skipLinks]);

  // Testing
  const runAccessibilityTest = useCallback(async (testType: string): Promise<boolean[]> => {
    const results: boolean[] = [];

    switch (testType) {
      case 'keyboard':
        results.push(testKeyboardNavigation());
        break;
      case 'contrast':
        results.push(testContrastRatio());
        break;
      case 'screen-reader':
        results.push(testScreenReaderSupport());
        break;
      case 'focus':
        results.push(testFocusIndicators());
        break;
      case 'aria':
        results.push(testARIALabels());
        break;
      default:
        break;
    }

    return results;
  }, []);

  // Detection utilities
  const detectScreenReader = useCallback(() => {
    return window.speechSynthesis !== undefined || 
           navigator.userAgent.includes('NVDA') ||
           navigator.userAgent.includes('JAWS') ||
           navigator.userAgent.includes('VoiceOver');
  }, []);

  const detectHighContrast = useCallback(() => {
    return window.matchMedia('(prefers-contrast: high)').matches ||
          window.matchMedia('(forced-colors: active)').matches;
  }, []);

  const detectReducedMotion = useCallback(() => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const detectKeyboardNavigation = useCallback(() => {
    // Check if user has used keyboard recently
    let lastKeyboardUse = 0;
    const handleKeyboardUse = () => {
      lastKeyboardUse = Date.now();
    };
    
    document.addEventListener('keydown', handleKeyboardUse);
    
    return () => {
      document.removeEventListener('keydown', handleKeyboardUse);
      return Date.now() - lastKeyboardUse < 5000; // Used keyboard in last 5 seconds
    };
  }, []);

  // Helper functions
  const matchesShortcut = (event: KeyboardEvent, shortcut: KeyboardShortcut): boolean => {
    return (
      event.key.toLowerCase() === shortcut.key.toLowerCase() &&
      !!event.ctrlKey === !!shortcut.ctrlKey &&
      !!event.altKey === !!shortcut.altKey &&
      !!event.shiftKey === !!shortcut.shiftKey
    );
  };

  const testKeyboardNavigation = (): boolean => {
    const focusableElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    return focusableElements.length > 0;
  };

  const testContrastRatio = (): boolean => {
    // Simplified contrast test - in real implementation would use color calculations
    return settings.highContrast || detectHighContrast();
  };

  const testScreenReaderSupport = (): boolean => {
    return settings.screenReaderOptimized && detectScreenReader();
  };

  const testFocusIndicators = (): boolean => {
    const focusableElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    // Check if elements have focus styles
    for (let i = 0; i < Math.min(5, focusableElements.length); i++) {
      const element = focusableElements[i] as HTMLElement;
      const styles = window.getComputedStyle(element);
      const focusStyles = styles.outline || styles.boxShadow || styles.border;
      if (!focusStyles || focusStyles === 'none') {
        return false;
      }
    }
    return true;
  };

  const testARIALabels = (): boolean => {
    const interactiveElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [role="button"]'
    );
    
    for (let i = 0; i < Math.min(5, interactiveElements.length); i++) {
      const element = interactiveElements[i] as HTMLElement;
      if (!element.getAttribute('aria-label') && 
          !element.getAttribute('aria-labelledby') &&
          !element.textContent?.trim()) {
        return false;
      }
    }
    return true;
  };

  return {
    settings,
    updateSetting,
    resetSettings,
    addKeyboardShortcut,
    removeKeyboardShortcut,
    handleKeyDown,
    trapFocus,
    setFocus,
    restoreFocus,
    announceToScreenReader,
    updateAriaLabel,
    updateAriaDescribedBy,
    addSkipLink,
    removeSkipLink,
    runAccessibilityTest,
    detectScreenReader,
    detectHighContrast,
    detectReducedMotion,
    detectKeyboardNavigation
  };
};

export default useAccessibility;
