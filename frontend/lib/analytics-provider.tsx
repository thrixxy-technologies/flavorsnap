/**
 * Analytics Provider Component
 * Initializes analytics and performance monitoring
 */

import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { analytics } from '@/utils/analytics';
import { monitorResourceTiming, monitorLongTasks, monitorMemoryUsage } from '@/utils/performance';

interface AnalyticsProviderProps {
  children: React.ReactNode;
  measurementId?: string;
}

export function AnalyticsProvider({ children, measurementId }: AnalyticsProviderProps) {
  const router = useRouter();

  useEffect(() => {
    // Initialize analytics with measurement ID from env
    const gaId = measurementId || process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
    
    if (gaId) {
      analytics.init(gaId);
    } else if (process.env.NODE_ENV === 'development') {
      console.warn('[Analytics] No GA_MEASUREMENT_ID provided. Analytics disabled.');
    }

    // Initialize performance monitoring
    monitorResourceTiming();
    monitorLongTasks();
    
    // Monitor memory usage in production only
    if (process.env.NODE_ENV === 'production') {
      monitorMemoryUsage();
    }
  }, [measurementId]);

  useEffect(() => {
    // Track page views on route change
    const handleRouteChange = (url: string) => {
      analytics.pageView(url);
    };

    router.events.on('routeChangeComplete', handleRouteChange);

    // Track initial page view
    analytics.pageView(router.pathname);

    return () => {
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, [router.events, router.pathname]);

  return <>{children}</>;
}
