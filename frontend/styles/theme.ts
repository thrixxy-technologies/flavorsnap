// Theme configuration and utilities
export const themeConfig = {
  light: {
    background: '#ffffff',
    foreground: '#111827',
    muted: '#f3f4f6',
    accent: '#3b82f6',
    destructive: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
    border: '#e5e7eb',
    input: '#ffffff',
    card: '#ffffff',
    cardForeground: '#111827',
    popover: '#ffffff',
    popoverForeground: '#111827',
    primary: '#3b82f6',
    primaryForeground: '#ffffff',
    secondary: '#f3f4f6',
    secondaryForeground: '#111827',
  },
  dark: {
    background: '#111827',
    foreground: '#f9fafb',
    muted: '#374151',
    accent: '#3b82f6',
    destructive: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
    border: '#374151',
    input: '#1f2937',
    card: '#1f2937',
    cardForeground: '#f9fafb',
    popover: '#1f2937',
    popoverForeground: '#f9fafb',
    primary: '#3b82f6',
    primaryForeground: '#ffffff',
    secondary: '#374151',
    secondaryForeground: '#f9fafb',
  },
};

// CSS custom properties for theme transitions
export const themeTransitions = {
  fast: '150ms',
  standard: '300ms',
  slow: '500ms',
};

export const themeEasing = {
  easeOut: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  easeOutBack: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
};

// Generate CSS custom properties for a theme
export const generateThemeCSS = (theme: keyof typeof themeConfig) => {
  const colors = themeConfig[theme];
  const cssVars: Record<string, string> = {};
  
  Object.entries(colors).forEach(([key, value]) => {
    cssVars[`--color-${key}`] = value;
  });
  
  return cssVars;
};

// Apply theme transitions to CSS
export const applyThemeTransitions = () => {
  const style = document.createElement('style');
  style.textContent = `
    * {
      transition-property: background-color, border-color, color, fill, stroke;
      transition-timing-function: ${themeEasing.easeInOut};
      transition-duration: ${themeTransitions.standard};
    }
    
    /* Faster transitions for interactive elements */
    button, input, select, textarea, a {
      transition-duration: ${themeTransitions.fast};
    }
    
    /* Disable transitions during theme initialization */
    .no-transitions * {
      transition: none !important;
    }
  `;
  
  document.head.appendChild(style);
  
  // Remove the no-transitions class after a short delay
  setTimeout(() => {
    document.documentElement.classList.remove('no-transitions');
  }, 100);
};

// Check if color contrast meets WCAG AA standards
export const checkContrast = (foreground: string, background: string): boolean => {
  // Simple contrast check (in real implementation, use proper contrast calculation)
  const getLuminance = (hex: string): number => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = (rgb >> 16) & 0xff;
    const g = (rgb >> 8) & 0xff;
    const b = rgb & 0xff;
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  };
  
  const fgLuminance = getLuminance(foreground);
  const bgLuminance = getLuminance(background);
  const contrast = (Math.max(fgLuminance, bgLuminance) + 0.05) / (Math.min(fgLuminance, bgLuminance) + 0.05);
  
  return contrast >= 4.5; // WCAG AA standard
};

// Get system preference
export const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

// Listen for system theme changes
export const listenToSystemThemeChanges = (callback: (theme: 'light' | 'dark') => void) => {
  if (typeof window === 'undefined') return () => {};
  
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleChange = (e: MediaQueryListEvent) => {
    callback(e.matches ? 'dark' : 'light');
  };
  
  mediaQuery.addEventListener('change', handleChange);
  
  return () => {
    mediaQuery.removeEventListener('change', handleChange);
  };
};
