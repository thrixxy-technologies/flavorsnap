/**
 * Analytics utility for tracking user behavior and performance metrics
 * Supports Google Analytics 4 and custom event tracking
 */

export interface AnalyticsEvent {
  action: string;
  category: string;
  label?: string;
  value?: number;
  [key: string]: any;
}

export interface ClassificationEvent {
  prediction: string;
  confidence: number;
  fileSize: number;
  fileType: string;
  duration?: number;
  success: boolean;
}

export interface PerformanceMetrics {
  name: string;
  value: number;
  rating?: 'good' | 'needs-improvement' | 'poor';
}

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
    dataLayer?: any[];
  }
}

class Analytics {
  private isInitialized = false;
  private isDevelopment = typeof process !== 'undefined' && process.env.NODE_ENV === 'development';

  /**
   * Initialize Google Analytics
   */
  init(measurementId: string) {
    if (this.isInitialized || !measurementId) {
      return;
    }

    // Load GA4 script
    const script = document.createElement('script');
    script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
    script.async = true;
    document.head.appendChild(script);

    // Initialize dataLayer
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer?.push(arguments);
    };

    window.gtag('js', new Date());
    window.gtag('config', measurementId, {
      send_page_view: true,
      anonymize_ip: true,
    });

    this.isInitialized = true;

    if (this.isDevelopment) {
      console.log('[Analytics] Initialized with ID:', measurementId);
    }
  }

  /**
   * Track page views
   */
  pageView(url: string, title?: string) {
    if (!this.isInitialized) return;

    window.gtag?.('event', 'page_view', {
      page_path: url,
      page_title: title,
    });

    if (this.isDevelopment) {
      console.log('[Analytics] Page view:', { url, title });
    }
  }

  /**
   * Track custom events
   */
  event(event: AnalyticsEvent) {
    if (!this.isInitialized) return;

    const { action, category, label, value, ...params } = event;

    window.gtag?.('event', action, {
      event_category: category,
      event_label: label,
      value: value,
      ...params,
    });

    if (this.isDevelopment) {
      console.log('[Analytics] Event:', event);
    }
  }

  /**
   * Track classification events
   */
  trackClassification(data: ClassificationEvent) {
    this.event({
      action: 'food_classification',
      category: 'ML_Model',
      label: data.prediction,
      value: Math.round(data.confidence * 100),
      prediction: data.prediction,
      confidence: data.confidence,
      file_size: data.fileSize,
      file_type: data.fileType,
      duration_ms: data.duration,
      success: data.success,
    });
  }

  /**
   * Track image upload events
   */
  trackImageUpload(fileSize: number, fileType: string) {
    this.event({
      action: 'image_upload',
      category: 'User_Interaction',
      label: fileType,
      value: fileSize,
      file_size: fileSize,
      file_type: fileType,
    });
  }

  /**
   * Track errors
   */
  trackError(error: Error, errorInfo?: any, fatal = false) {
    this.event({
      action: 'exception',
      category: 'Error',
      label: error.message,
      description: error.stack,
      fatal: fatal,
      error_name: error.name,
      error_message: error.message,
      error_stack: error.stack,
      component_stack: errorInfo?.componentStack,
    });
  }

  /**
   * Track API errors
   */
  trackApiError(endpoint: string, statusCode: number, errorMessage: string) {
    this.event({
      action: 'api_error',
      category: 'API',
      label: endpoint,
      value: statusCode,
      endpoint: endpoint,
      status_code: statusCode,
      error_message: errorMessage,
    });
  }

  /**
   * Track performance metrics (Web Vitals)
   */
  trackPerformance(metric: PerformanceMetrics) {
    this.event({
      action: 'web_vitals',
      category: 'Performance',
      label: metric.name,
      value: Math.round(metric.value),
      metric_name: metric.name,
      metric_value: metric.value,
      metric_rating: metric.rating,
    });
  }

  /**
   * Track user timing
   */
  trackTiming(category: string, variable: string, value: number, label?: string) {
    if (!this.isInitialized) return;

    window.gtag?.('event', 'timing_complete', {
      name: variable,
      value: Math.round(value),
      event_category: category,
      event_label: label,
    });

    if (this.isDevelopment) {
      console.log('[Analytics] Timing:', { category, variable, value, label });
    }
  }

  /**
   * Set user properties
   */
  setUserProperty(property: string, value: string) {
    if (!this.isInitialized) return;

    window.gtag?.('set', 'user_properties', {
      [property]: value,
    });
  }

  /**
   * Track language change
   */
  trackLanguageChange(language: string) {
    this.event({
      action: 'language_change',
      category: 'User_Preference',
      label: language,
      language: language,
    });
  }

  /**
   * Track button clicks
   */
  trackButtonClick(buttonName: string, location?: string) {
    this.event({
      action: 'button_click',
      category: 'User_Interaction',
      label: buttonName,
      location: location,
    });
  }
}

export const analytics = new Analytics();
