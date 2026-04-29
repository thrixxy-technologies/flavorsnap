/**
 * useMobileResponsive Hook
 * Provides mobile-specific state and utilities
 */

import { useState, useEffect, useCallback } from 'react';
import {
  isMobileDevice,
  isTabletDevice,
  isTouchDevice,
  getViewportSize,
  isLandscape,
  debounce,
} from '@/utils/mobileOptimization';

interface MobileResponsiveState {
  isMobile: boolean;
  isTablet: boolean;
  isTouch: boolean;
  isLandscape: boolean;
  viewport: {
    width: number;
    height: number;
  };
  breakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

/**
 * Hook to manage mobile responsive state
 */
export const useMobileResponsive = () => {
  const [state, setState] = useState<MobileResponsiveState>({
    isMobile: false,
    isTablet: false,
    isTouch: false,
    isLandscape: false,
    viewport: { width: 0, height: 0 },
    breakpoint: 'xs',
  });

  const getBreakpoint = useCallback((width: number): MobileResponsiveState['breakpoint'] => {
    if (width < 640) return 'xs';
    if (width < 768) return 'sm';
    if (width < 1024) return 'md';
    if (width < 1280) return 'lg';
    if (width < 1536) return 'xl';
    return '2xl';
  }, []);

  const updateState = useCallback(() => {
    const viewport = getViewportSize();
    setState({
      isMobile: isMobileDevice(),
      isTablet: isTabletDevice(),
      isTouch: isTouchDevice(),
      isLandscape: isLandscape(),
      viewport,
      breakpoint: getBreakpoint(viewport.width),
    });
  }, [getBreakpoint]);

  useEffect(() => {
    // Initial state
    updateState();

    // Debounced resize handler
    const handleResize = debounce(updateState, 150);

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', updateState);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', updateState);
    };
  }, [updateState]);

  return state;
};

/**
 * Hook to detect if viewport matches a specific breakpoint
 */
export const useBreakpoint = (breakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl') => {
  const { breakpoint: currentBreakpoint } = useMobileResponsive();
  return currentBreakpoint === breakpoint;
};

/**
 * Hook to detect if viewport is at or above a specific breakpoint
 */
export const useMinBreakpoint = (breakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl') => {
  const { viewport } = useMobileResponsive();
  
  const breakpoints = {
    xs: 0,
    sm: 640,
    md: 768,
    lg: 1024,
    xl: 1280,
    '2xl': 1536,
  };
  
  return viewport.width >= breakpoints[breakpoint];
};

/**
 * Hook to detect if viewport is below a specific breakpoint
 */
export const useMaxBreakpoint = (breakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl') => {
  const { viewport } = useMobileResponsive();
  
  const breakpoints = {
    xs: 640,
    sm: 768,
    md: 1024,
    lg: 1280,
    xl: 1536,
    '2xl': Infinity,
  };
  
  return viewport.width < breakpoints[breakpoint];
};

/**
 * Hook for touch gesture detection
 */
export const useTouchGestures = (
  elementRef: React.RefObject<HTMLElement>,
  handlers: {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
    onTap?: () => void;
  }
) => {
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

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
        handlers.onTap?.();
        return;
      }

      // Detect swipe direction
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        // Horizontal swipe
        if (deltaX > threshold) {
          handlers.onSwipeRight?.();
        } else if (deltaX < -threshold) {
          handlers.onSwipeLeft?.();
        }
      } else {
        // Vertical swipe
        if (deltaY > threshold) {
          handlers.onSwipeDown?.();
        } else if (deltaY < -threshold) {
          handlers.onSwipeUp?.();
        }
      }
    };

    element.addEventListener('touchstart', handleTouchStart);
    element.addEventListener('touchend', handleTouchEnd);

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }, [elementRef, handlers]);
};

/**
 * Hook to manage body scroll lock (useful for modals)
 */
export const useBodyScrollLock = (locked: boolean) => {
  useEffect(() => {
    if (typeof document === 'undefined') return;

    if (locked) {
      const scrollY = window.scrollY;
      document.body.style.position = 'fixed';
      document.body.style.top = `-${scrollY}px`;
      document.body.style.width = '100%';
      document.body.style.overflow = 'hidden';
    } else {
      const scrollY = document.body.style.top;
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      document.body.style.overflow = '';
      window.scrollTo(0, parseInt(scrollY || '0') * -1);
    }

    return () => {
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      document.body.style.overflow = '';
    };
  }, [locked]);
};

/**
 * Hook to detect orientation changes
 */
export const useOrientation = () => {
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait');

  useEffect(() => {
    const updateOrientation = () => {
      setOrientation(window.innerWidth > window.innerHeight ? 'landscape' : 'portrait');
    };

    updateOrientation();

    window.addEventListener('resize', updateOrientation);
    window.addEventListener('orientationchange', updateOrientation);

    return () => {
      window.removeEventListener('resize', updateOrientation);
      window.removeEventListener('orientationchange', updateOrientation);
    };
  }, []);

  return orientation;
};

/**
 * Hook to detect network connection
 */
export const useNetworkStatus = () => {
  const [isOnline, setIsOnline] = useState(true);
  const [connectionType, setConnectionType] = useState<string>('unknown');

  useEffect(() => {
    const updateOnlineStatus = () => {
      setIsOnline(navigator.onLine);
    };

    const updateConnectionType = () => {
      if ((navigator as any).connection) {
        const connection = (navigator as any).connection;
        setConnectionType(connection.effectiveType || connection.type || 'unknown');
      }
    };

    updateOnlineStatus();
    updateConnectionType();

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    if ((navigator as any).connection) {
      (navigator as any).connection.addEventListener('change', updateConnectionType);
    }

    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);

      if ((navigator as any).connection) {
        (navigator as any).connection.removeEventListener('change', updateConnectionType);
      }
    };
  }, []);

  return { isOnline, connectionType, isSlowConnection: ['slow-2g', '2g', '3g'].includes(connectionType) };
};

/**
 * Hook for viewport-based visibility detection
 */
export const useIntersectionObserver = (
  elementRef: React.RefObject<HTMLElement>,
  options: IntersectionObserverInit = {}
) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting);
    }, options);

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [elementRef, options]);

  return isVisible;
};

export default useMobileResponsive;
