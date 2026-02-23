/**
 * Tests for analytics utilities
 */

import { analytics } from '@/utils/analytics';

// Mock window.gtag
const mockGtag = jest.fn();

describe('Analytics', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock window.gtag
    global.window = {
      ...global.window,
      gtag: mockGtag,
      dataLayer: [],
    } as any;

    // Mock document.createElement for script injection
    const mockScript = {
      src: '',
      async: false,
    };
    jest.spyOn(document, 'createElement').mockReturnValue(mockScript as any);
    jest.spyOn(document.head, 'appendChild').mockImplementation(() => mockScript as any);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('init', () => {
    it('should initialize Google Analytics with measurement ID', () => {
      const measurementId = 'G-TEST123';
      analytics.init(measurementId);

      expect(document.createElement).toHaveBeenCalledWith('script');
      expect(mockGtag).toHaveBeenCalledWith('js', expect.any(Date));
      expect(mockGtag).toHaveBeenCalledWith('config', measurementId, {
        send_page_view: true,
        anonymize_ip: true,
      });
    });

    it('should not initialize without measurement ID', () => {
      analytics.init('');
      expect(document.createElement).not.toHaveBeenCalled();
    });
  });

  describe('pageView', () => {
    it('should track page views', () => {
      analytics.init('G-TEST123');
      analytics.pageView('/test-page', 'Test Page');

      expect(mockGtag).toHaveBeenCalledWith('event', 'page_view', {
        page_path: '/test-page',
        page_title: 'Test Page',
      });
    });
  });

  describe('event', () => {
    it('should track custom events', () => {
      analytics.init('G-TEST123');
      analytics.event({
        action: 'test_action',
        category: 'Test_Category',
        label: 'test_label',
        value: 100,
      });

      expect(mockGtag).toHaveBeenCalledWith('event', 'test_action', {
        event_category: 'Test_Category',
        event_label: 'test_label',
        value: 100,
      });
    });
  });

  describe('trackClassification', () => {
    it('should track successful classification', () => {
      analytics.init('G-TEST123');
      analytics.trackClassification({
        prediction: 'moi moi',
        confidence: 0.95,
        fileSize: 1024000,
        fileType: 'image/jpeg',
        duration: 1500,
        success: true,
      });

      expect(mockGtag).toHaveBeenCalledWith('event', 'food_classification', {
        event_category: 'ML_Model',
        event_label: 'moi moi',
        value: 95,
        prediction: 'moi moi',
        confidence: 0.95,
        file_size: 1024000,
        file_type: 'image/jpeg',
        duration_ms: 1500,
        success: true,
      });
    });
  });

  describe('trackError', () => {
    it('should track errors with stack trace', () => {
      analytics.init('G-TEST123');
      const error = new Error('Test error');
      analytics.trackError(error, { componentStack: 'Component stack' }, true);

      expect(mockGtag).toHaveBeenCalledWith('event', 'exception', expect.objectContaining({
        event_category: 'Error',
        event_label: 'Test error',
        fatal: true,
        error_name: 'Error',
        error_message: 'Test error',
      }));
    });
  });

  describe('trackApiError', () => {
    it('should track API errors', () => {
      analytics.init('G-TEST123');
      analytics.trackApiError('/api/classify', 500, 'Internal Server Error');

      expect(mockGtag).toHaveBeenCalledWith('event', 'api_error', {
        event_category: 'API',
        event_label: '/api/classify',
        value: 500,
        endpoint: '/api/classify',
        status_code: 500,
        error_message: 'Internal Server Error',
      });
    });
  });

  describe('trackPerformance', () => {
    it('should track performance metrics', () => {
      analytics.init('G-TEST123');
      analytics.trackPerformance({
        name: 'LCP',
        value: 2400,
        rating: 'good',
      });

      expect(mockGtag).toHaveBeenCalledWith('event', 'web_vitals', {
        event_category: 'Performance',
        event_label: 'LCP',
        value: 2400,
        metric_name: 'LCP',
        metric_value: 2400,
        metric_rating: 'good',
      });
    });
  });

  describe('trackButtonClick', () => {
    it('should track button clicks', () => {
      analytics.init('G-TEST123');
      analytics.trackButtonClick('submit_button', 'home_page');

      expect(mockGtag).toHaveBeenCalledWith('event', 'button_click', {
        event_category: 'User_Interaction',
        event_label: 'submit_button',
        location: 'home_page',
      });
    });
  });

  describe('trackLanguageChange', () => {
    it('should track language changes', () => {
      analytics.init('G-TEST123');
      analytics.trackLanguageChange('fr');

      expect(mockGtag).toHaveBeenCalledWith('event', 'language_change', {
        event_category: 'User_Preference',
        event_label: 'fr',
        language: 'fr',
      });
    });
  });
});
