/**
 * Performance monitoring utilities
 * Tracks Web Vitals and custom performance metrics
 */

import { analytics } from './analytics';

export type WebVitalMetric = 'CLS' | 'FID' | 'FCP' | 'LCP' | 'TTFB' | 'INP';

interface Metric {
  name: WebVitalMetric;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  id: string;
}

/**
 * Get rating for Web Vitals metrics
 */
function getRating(name: WebVitalMetric, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds: Record<WebVitalMetric, [number, number]> = {
    CLS: [0.1, 0.25],
    FID: [100, 300],
    FCP: [1800, 3000],
    LCP: [2500, 4000],
    TTFB: [800, 1800],
    INP: [200, 500],
  };

  const [good, poor] = thresholds[name];
  if (value <= good) return 'good';
  if (value <= poor) return 'needs-improvement';
  return 'poor';
}

/**
 * Report Web Vitals to analytics
 */
export function reportWebVitals(metric: Metric) {
  analytics.trackPerformance({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
  });

  // Log in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[Performance]', {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
    });
  }
}

/**
 * Measure and report custom timing
 */
export class PerformanceTimer {
  private startTime: number;
  private name: string;

  constructor(name: string) {
    this.name = name;
    this.startTime = performance.now();
  }

  end(category = 'Custom', label?: string) {
    const duration = performance.now() - this.startTime;
    analytics.trackTiming(category, this.name, duration, label);
    return duration;
  }
}

/**
 * Monitor API request performance
 */
export function measureApiCall<T>(
  apiCall: () => Promise<T>,
  endpoint: string
): Promise<T> {
  const timer = new PerformanceTimer(`api_${endpoint}`);

  return apiCall()
    .then((result) => {
      const duration = timer.end('API', endpoint);
      
      // Track slow API calls
      if (duration > 3000) {
        analytics.event({
          action: 'slow_api_call',
          category: 'Performance',
          label: endpoint,
          value: Math.round(duration),
          duration_ms: duration,
        });
      }

      return result;
    })
    .catch((error) => {
      timer.end('API', `${endpoint}_error`);
      throw error;
    });
}

/**
 * Monitor resource loading performance
 */
export function monitorResourceTiming() {
  if (typeof window === 'undefined' || !window.performance) {
    return;
  }

  // Wait for page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      // Track slow resources
      resources.forEach((resource) => {
        if (resource.duration > 1000) {
          analytics.event({
            action: 'slow_resource',
            category: 'Performance',
            label: resource.name,
            value: Math.round(resource.duration),
            resource_type: resource.initiatorType,
            duration_ms: resource.duration,
          });
        }
      });

      // Calculate total page load time
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navigation) {
        const pageLoadTime = navigation.loadEventEnd - navigation.fetchStart;
        analytics.trackTiming('Page', 'load', pageLoadTime);
      }
    }, 0);
  });
}

/**
 * Monitor long tasks (tasks that block the main thread for >50ms)
 */
export function monitorLongTasks() {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return;
  }

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        analytics.event({
          action: 'long_task',
          category: 'Performance',
          label: entry.name,
          value: Math.round(entry.duration),
          duration_ms: entry.duration,
        });
      }
    });

    observer.observe({ entryTypes: ['longtask'] });
  } catch (e) {
    // PerformanceObserver not supported or longtask not available
  }
}

/**
 * Get current memory usage (if available)
 */
export function getMemoryUsage() {
  if (typeof window === 'undefined') return null;

  const memory = (performance as any).memory;
  if (!memory) return null;

  return {
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
    usagePercent: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
  };
}

/**
 * Track memory usage periodically
 */
export function monitorMemoryUsage(intervalMs = 30000) {
  if (typeof window === 'undefined') return;

  setInterval(() => {
    const memory = getMemoryUsage();
    if (memory && memory.usagePercent > 90) {
      analytics.event({
        action: 'high_memory_usage',
        category: 'Performance',
        label: 'memory_warning',
        value: Math.round(memory.usagePercent),
        used_mb: Math.round(memory.usedJSHeapSize / 1024 / 1024),
        total_mb: Math.round(memory.totalJSHeapSize / 1024 / 1024),
      });
    }
  }, intervalMs);
}
