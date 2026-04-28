import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

interface WebVitalsMetrics {
  lcp: number;
  fid: number;
  fcp: number;
  cls: number;
  ttfb: number;
}

class WebVitalsReporter {
  private static instance: WebVitalsReporter;
  private metrics: Partial<WebVitalsMetrics> = {};
  private observers: Map<string, PerformanceObserver> = new Map();

  private constructor() {}

  static getInstance(): WebVitalsReporter {
    if (!WebVitalsReporter.instance) {
      WebVitalsReporter.instance = new WebVitalsReporter();
    }
    return WebVitalsReporter.instance;
  }

  /**
   * Initialize Web Vitals monitoring
   */
  init(): void {
    if (typeof window === 'undefined') return;

    // Core Web Vitals
    getCLS(this.handleMetric.bind(this));
    getFID(this.handleMetric.bind(this));
    getFCP(this.handleMetric.bind(this));
    getLCP(this.handleMetric.bind(this));
    getTTFB(this.handleMetric.bind(this));

    // Additional performance monitoring
    this.observeLayoutShift();
    this.observeLongTasks();
    this.observeResourceTiming();
  }

  /**
   * Handle individual metric
   */
  private handleMetric(metric: any): void {
    const { name, value, rating, delta, id } = metric;

    this.metrics[name.toLowerCase() as keyof WebVitalsMetrics] = value;

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Web Vitals] ${name}: ${value} (${rating})`);
    }

    // Send to analytics
    this.sendToAnalytics({
      name,
      value,
      rating,
      delta,
      id,
      url: window.location.href,
      timestamp: Date.now(),
    });

    // Store for SEO monitoring
    this.storeMetric(name, value, rating);
  }

  /**
   * Send metrics to analytics service
   */
  private sendToAnalytics(metric: any): void {
    // Send to Google Analytics 4
    if (typeof gtag !== 'undefined') {
      gtag('event', metric.name, {
        event_category: 'Web Vitals',
        event_label: metric.id,
        value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
        non_interaction: true,
        custom_map: {
          metric_rating: metric.rating,
          metric_delta: metric.delta,
        },
      });
    }

    // Send to custom analytics endpoint
    this.sendCustomAnalytics(metric);
  }

  /**
   * Send to custom analytics endpoint
   */
  private sendCustomAnalytics(metric: any): void {
    if (typeof fetch === 'undefined') return;

    fetch('/api/analytics/web-vitals', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...metric,
        userAgent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
        },
        connection: this.getConnectionInfo(),
      }),
    }).catch(() => {
      // Silently fail to avoid affecting user experience
    });
  }

  /**
   * Get connection information
   */
  private getConnectionInfo(): any {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      return {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData,
      };
    }
    return null;
  }

  /**
   * Store metrics for SEO monitoring
   */
  private storeMetric(name: string, value: number, rating: string): void {
    const key = `webvital_${name.toLowerCase()}`;
    const data = {
      value,
      rating,
      timestamp: Date.now(),
      url: window.location.href,
    };

    // Store in localStorage for debugging
    try {
      const existing = JSON.parse(localStorage.getItem(key) || '[]');
      existing.push(data);
      
      // Keep only last 100 entries
      if (existing.length > 100) {
        existing.splice(0, existing.length - 100);
      }
      
      localStorage.setItem(key, JSON.stringify(existing));
    } catch (error) {
      // Silently fail
    }
  }

  /**
   * Observe additional layout shifts
   */
  private observeLayoutShift(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            // This is a layout shift without user input
            console.debug('[Layout Shift] Value:', (entry as any).value);
          }
        }
      });

      observer.observe({ type: 'layout-shift', buffered: true });
      this.observers.set('layout-shift', observer);
    }
  }

  /**
   * Observe long tasks
   */
  private observeLongTasks(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          console.debug('[Long Task] Duration:', entry.duration);
          
          // Send long task analytics
          this.sendToAnalytics({
            name: 'LongTask',
            value: entry.duration,
            rating: entry.duration > 50 ? 'poor' : 'good',
            delta: entry.duration,
            id: `longtask-${Date.now()}`,
            timestamp: Date.now(),
          });
        }
      });

      observer.observe({ type: 'longtask', buffered: true });
      this.observers.set('longtask', observer);
    }
  }

  /**
   * Observe resource timing
   */
  private observeResourceTiming(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const resource = entry as PerformanceResourceTiming;
          
          // Track slow resources
          if (resource.duration > 1000) {
            console.debug('[Slow Resource]', resource.name, resource.duration);
          }
        }
      });

      observer.observe({ type: 'resource', buffered: true });
      this.observers.set('resource', observer);
    }
  }

  /**
   * Get current metrics
   */
  getMetrics(): Partial<WebVitalsMetrics> {
    return { ...this.metrics };
  }

  /**
   * Get performance score (0-100)
   */
  getPerformanceScore(): number {
    const metrics = this.metrics;
    if (!metrics.lcp || !metrics.fid || !metrics.cls || !metrics.ttfb) {
      return 0;
    }

    // Scoring based on Google's thresholds
    let score = 100;

    // LCP: Good < 2.5s, Needs Improvement < 4s
    if (metrics.lcp > 4000) score -= 25;
    else if (metrics.lcp > 2500) score -= 15;

    // FID: Good < 100ms, Needs Improvement < 300ms
    if (metrics.fid > 300) score -= 25;
    else if (metrics.fid > 100) score -= 15;

    // CLS: Good < 0.1, Needs Improvement < 0.25
    if (metrics.cls > 0.25) score -= 25;
    else if (metrics.cls > 0.1) score -= 15;

    // TTFB: Good < 800ms, Needs Improvement < 1800ms
    if (metrics.ttfb > 1800) score -= 25;
    else if (metrics.ttfb > 800) score -= 15;

    return Math.max(0, score);
  }

  /**
   * Get performance grade
   */
  getPerformanceGrade(): 'excellent' | 'good' | 'needs-improvement' | 'poor' {
    const score = this.getPerformanceScore();
    if (score >= 90) return 'excellent';
    if (score >= 75) return 'good';
    if (score >= 50) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Cleanup observers
   */
  cleanup(): void {
    this.observers.forEach((observer) => {
      observer.disconnect();
    });
    this.observers.clear();
  }
}

// Export singleton instance
export default WebVitalsReporter;

// Export types
export type { WebVitalsMetrics };

// Export utility functions
export const reportWebVitals = (onPerfEntry?: (metric: any) => void): void => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    });
  } else {
    WebVitalsReporter.getInstance().init();
  }
};
