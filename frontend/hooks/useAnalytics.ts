/**
 * Custom React hook for analytics tracking
 * Provides convenient methods for tracking events in components
 */

import { useCallback, useEffect, type ReactNode } from 'react';
import { analytics } from '@/utils/analytics';
import { PerformanceTimer } from '@/utils/performance';

export function useAnalytics() {
  /**
   * Track a custom event
   */
  const trackEvent = useCallback((
    action: string,
    category: string,
    label?: string,
    value?: number,
    additionalParams?: Record<string, any>
  ) => {
    analytics.event({
      action,
      category,
      label,
      value,
      ...additionalParams,
    });
  }, []);

  /**
   * Track button click with automatic naming
   */
  const trackClick = useCallback((buttonName: string, location?: string) => {
    analytics.trackButtonClick(buttonName, location);
  }, []);

  /**
   * Track form submission
   */
  const trackFormSubmit = useCallback((formName: string, success: boolean) => {
    analytics.event({
      action: 'form_submit',
      category: 'User_Interaction',
      label: formName,
      success,
    });
  }, []);

  /**
   * Track page view (useful for SPAs)
   */
  const trackPageView = useCallback((url: string, title?: string) => {
    analytics.pageView(url, title);
  }, []);

  /**
   * Create a performance timer
   */
  const createTimer = useCallback((name: string) => {
    return new PerformanceTimer(name);
  }, []);

  return {
    trackEvent,
    trackClick,
    trackFormSubmit,
    trackPageView,
    createTimer,
  };
}

/**
 * Hook to track component mount/unmount
 */
export function useComponentTracking(componentName: string) {
  useEffect(() => {
    const mountTime = Date.now();

    analytics.event({
      action: 'component_mount',
      category: 'Component_Lifecycle',
      label: componentName,
    });

    return () => {
      const duration = Date.now() - mountTime;
      analytics.event({
        action: 'component_unmount',
        category: 'Component_Lifecycle',
        label: componentName,
        value: duration,
        duration_ms: duration,
      });
    };
  }, [componentName]);
}

/**
 * Hook to track user engagement time on page
 */
export function useEngagementTracking(pageName: string) {
  useEffect(() => {
    const startTime = Date.now();
    let isActive = true;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        isActive = false;
      } else {
        isActive = true;
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      if (isActive) {
        const engagementTime = Date.now() - startTime;
        analytics.event({
          action: 'page_engagement',
          category: 'Engagement',
          label: pageName,
          value: Math.round(engagementTime / 1000), // seconds
          duration_ms: engagementTime,
        });
      }
    };
  }, [pageName]);
}
