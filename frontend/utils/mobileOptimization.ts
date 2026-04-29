/**
 * Mobile Optimization Utilities
 * Provides utilities for mobile-specific optimizations
 */

/**
 * Detect if the device is mobile
 */
export const isMobileDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
};

/**
 * Detect if the device is a tablet
 */
export const isTabletDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return /iPad|Android/i.test(navigator.userAgent) && 
         window.innerWidth >= 768 && 
         window.innerWidth <= 1024;
};

/**
 * Detect if the device supports touch
 */
export const isTouchDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return (
    'ontouchstart' in window ||
    navigator.maxTouchPoints > 0 ||
    (navigator as any).msMaxTouchPoints > 0
  );
};

/**
 * Get the current viewport size
 */
export const getViewportSize = () => {
  if (typeof window === 'undefined') {
    return { width: 0, height: 0 };
  }
  
  return {
    width: window.innerWidth,
    height: window.innerHeight,
  };
};

/**
 * Get the device pixel ratio
 */
export const getDevicePixelRatio = (): number => {
  if (typeof window === 'undefined') return 1;
  
  return window.devicePixelRatio || 1;
};

/**
 * Detect if the device is in landscape mode
 */
export const isLandscape = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return window.innerWidth > window.innerHeight;
};

/**
 * Detect if the device is in portrait mode
 */
export const isPortrait = (): boolean => {
  return !isLandscape();
};

/**
 * Get the optimal image size for the current device
 */
export const getOptimalImageSize = (
  originalWidth: number,
  originalHeight: number
): { width: number; height: number } => {
  const viewport = getViewportSize();
  const pixelRatio = getDevicePixelRatio();
  
  // Calculate the maximum width based on viewport and pixel ratio
  const maxWidth = Math.min(viewport.width * pixelRatio, originalWidth);
  
  // Maintain aspect ratio
  const aspectRatio = originalHeight / originalWidth;
  const height = Math.round(maxWidth * aspectRatio);
  
  return {
    width: Math.round(maxWidth),
    height,
  };
};

/**
 * Optimize image URL for mobile devices
 * Adds query parameters for image optimization services
 */
export const optimizeImageUrl = (
  url: string,
  options: {
    width?: number;
    height?: number;
    quality?: number;
    format?: 'webp' | 'jpeg' | 'png';
  } = {}
): string => {
  if (!url) return url;
  
  const { width, height, quality = 80, format = 'webp' } = options;
  
  // If it's a blob URL or data URL, return as is
  if (url.startsWith('blob:') || url.startsWith('data:')) {
    return url;
  }
  
  // For external URLs, you might want to use an image optimization service
  // This is a placeholder - adjust based on your image CDN
  const params = new URLSearchParams();
  
  if (width) params.append('w', width.toString());
  if (height) params.append('h', height.toString());
  params.append('q', quality.toString());
  params.append('fm', format);
  
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}${params.toString()}`;
};

/**
 * Debounce function for resize events
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

/**
 * Throttle function for scroll events
 */
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Prevent body scroll (useful for modals on mobile)
 */
export const preventBodyScroll = (prevent: boolean = true): void => {
  if (typeof document === 'undefined') return;
  
  if (prevent) {
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.width = '100%';
  } else {
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.width = '';
  }
};

/**
 * Get safe area insets for notched devices
 */
export const getSafeAreaInsets = () => {
  if (typeof window === 'undefined' || !CSS.supports('padding', 'env(safe-area-inset-top)')) {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  }
  
  const computedStyle = getComputedStyle(document.documentElement);
  
  return {
    top: parseInt(computedStyle.getPropertyValue('env(safe-area-inset-top)') || '0'),
    right: parseInt(computedStyle.getPropertyValue('env(safe-area-inset-right)') || '0'),
    bottom: parseInt(computedStyle.getPropertyValue('env(safe-area-inset-bottom)') || '0'),
    left: parseInt(computedStyle.getPropertyValue('env(safe-area-inset-left)') || '0'),
  };
};

/**
 * Detect if the device has a notch
 */
export const hasNotch = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const insets = getSafeAreaInsets();
  return insets.top > 0 || insets.bottom > 0;
};

/**
 * Add touch ripple effect to an element
 */
export const addTouchRipple = (
  element: HTMLElement,
  event: TouchEvent | MouseEvent
): void => {
  const ripple = document.createElement('span');
  const rect = element.getBoundingClientRect();
  
  const x = ('touches' in event ? event.touches[0].clientX : event.clientX) - rect.left;
  const y = ('touches' in event ? event.touches[0].clientY : event.clientY) - rect.top;
  
  ripple.style.position = 'absolute';
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  ripple.style.width = '0';
  ripple.style.height = '0';
  ripple.style.borderRadius = '50%';
  ripple.style.background = 'rgba(255, 255, 255, 0.5)';
  ripple.style.transform = 'translate(-50%, -50%)';
  ripple.style.pointerEvents = 'none';
  ripple.style.transition = 'width 0.6s, height 0.6s, opacity 0.6s';
  
  element.style.position = 'relative';
  element.style.overflow = 'hidden';
  element.appendChild(ripple);
  
  // Trigger animation
  requestAnimationFrame(() => {
    ripple.style.width = '300px';
    ripple.style.height = '300px';
    ripple.style.opacity = '0';
  });
  
  // Remove ripple after animation
  setTimeout(() => {
    ripple.remove();
  }, 600);
};

/**
 * Detect network connection type
 */
export const getConnectionType = (): string => {
  if (typeof navigator === 'undefined' || !(navigator as any).connection) {
    return 'unknown';
  }
  
  const connection = (navigator as any).connection;
  return connection.effectiveType || connection.type || 'unknown';
};

/**
 * Check if the connection is slow
 */
export const isSlowConnection = (): boolean => {
  const connectionType = getConnectionType();
  return ['slow-2g', '2g', '3g'].includes(connectionType);
};

/**
 * Preload images for better mobile performance
 */
export const preloadImage = (src: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
};

/**
 * Lazy load images with Intersection Observer
 */
export const lazyLoadImage = (
  img: HTMLImageElement,
  options: IntersectionObserverInit = {}
): void => {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
    // Fallback for browsers without Intersection Observer
    if (img.dataset.src) {
      img.src = img.dataset.src;
    }
    return;
  }
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const image = entry.target as HTMLImageElement;
        if (image.dataset.src) {
          image.src = image.dataset.src;
          image.removeAttribute('data-src');
        }
        observer.unobserve(image);
      }
    });
  }, options);
  
  observer.observe(img);
};

/**
 * Vibrate device (if supported)
 */
export const vibrate = (pattern: number | number[]): void => {
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    navigator.vibrate(pattern);
  }
};

/**
 * Request fullscreen mode
 */
export const requestFullscreen = (element: HTMLElement = document.documentElement): void => {
  if (element.requestFullscreen) {
    element.requestFullscreen();
  } else if ((element as any).webkitRequestFullscreen) {
    (element as any).webkitRequestFullscreen();
  } else if ((element as any).mozRequestFullScreen) {
    (element as any).mozRequestFullScreen();
  } else if ((element as any).msRequestFullscreen) {
    (element as any).msRequestFullscreen();
  }
};

/**
 * Exit fullscreen mode
 */
export const exitFullscreen = (): void => {
  if (document.exitFullscreen) {
    document.exitFullscreen();
  } else if ((document as any).webkitExitFullscreen) {
    (document as any).webkitExitFullscreen();
  } else if ((document as any).mozCancelFullScreen) {
    (document as any).mozCancelFullScreen();
  } else if ((document as any).msExitFullscreen) {
    (document as any).msExitFullscreen();
  }
};

/**
 * Check if device is in fullscreen mode
 */
export const isFullscreen = (): boolean => {
  return !!(
    document.fullscreenElement ||
    (document as any).webkitFullscreenElement ||
    (document as any).mozFullScreenElement ||
    (document as any).msFullscreenElement
  );
};

/**
 * Get battery status (if supported)
 */
export const getBatteryStatus = async (): Promise<{
  level: number;
  charging: boolean;
} | null> => {
  if (typeof navigator === 'undefined' || !(navigator as any).getBattery) {
    return null;
  }
  
  try {
    const battery = await (navigator as any).getBattery();
    return {
      level: battery.level,
      charging: battery.charging,
    };
  } catch (error) {
    return null;
  }
};

/**
 * Enable/disable pull-to-refresh
 */
export const setPullToRefresh = (enabled: boolean): void => {
  if (typeof document === 'undefined') return;
  
  const body = document.body;
  if (enabled) {
    body.style.overscrollBehavior = 'auto';
  } else {
    body.style.overscrollBehavior = 'none';
  }
};

/**
 * Mobile-specific event listeners
 */
export const addMobileEventListeners = (
  element: HTMLElement,
  handlers: {
    onTap?: (e: TouchEvent) => void;
    onSwipeLeft?: (e: TouchEvent) => void;
    onSwipeRight?: (e: TouchEvent) => void;
    onSwipeUp?: (e: TouchEvent) => void;
    onSwipeDown?: (e: TouchEvent) => void;
  }
): (() => void) => {
  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;
  
  const handleTouchStart = (e: TouchEvent) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  };
  
  const handleTouchEnd = (e: TouchEvent) => {
    touchEndX = e.changedTouches[0].clientX;
    touchEndY = e.changedTouches[0].clientY;
    
    const deltaX = touchEndX - touchStartX;
    const deltaY = touchEndY - touchStartY;
    const threshold = 50;
    
    // Detect tap
    if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
      handlers.onTap?.(e);
      return;
    }
    
    // Detect swipe direction
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      // Horizontal swipe
      if (deltaX > threshold) {
        handlers.onSwipeRight?.(e);
      } else if (deltaX < -threshold) {
        handlers.onSwipeLeft?.(e);
      }
    } else {
      // Vertical swipe
      if (deltaY > threshold) {
        handlers.onSwipeDown?.(e);
      } else if (deltaY < -threshold) {
        handlers.onSwipeUp?.(e);
      }
    }
  };
  
  element.addEventListener('touchstart', handleTouchStart);
  element.addEventListener('touchend', handleTouchEnd);
  
  // Return cleanup function
  return () => {
    element.removeEventListener('touchstart', handleTouchStart);
    element.removeEventListener('touchend', handleTouchEnd);
  };
};

export default {
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
  preventBodyScroll,
  getSafeAreaInsets,
  hasNotch,
  addTouchRipple,
  getConnectionType,
  isSlowConnection,
  preloadImage,
  lazyLoadImage,
  vibrate,
  requestFullscreen,
  exitFullscreen,
  isFullscreen,
  getBatteryStatus,
  setPullToRefresh,
  addMobileEventListeners,
};
