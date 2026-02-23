# Analytics & Performance Monitoring

This document describes the analytics and performance monitoring implementation for FlavorSnap.

## Overview

The application includes comprehensive tracking for:
- User behavior and interactions
- Food classification events
- Performance metrics (Web Vitals)
- Error tracking and monitoring
- API performance

## Setup

### 1. Google Analytics 4

1. Create a Google Analytics 4 property at [analytics.google.com](https://analytics.google.com)
2. Get your Measurement ID (format: `G-XXXXXXXXXX`)
3. Add it to your environment variables:

```bash
# .env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### 2. Verify Installation

After deployment, check:
- Google Analytics Real-Time reports
- Browser console in development mode for analytics logs
- Network tab for `gtag` requests

## Tracked Events

### User Interactions

| Event | Category | Description |
|-------|----------|-------------|
| `button_click` | User_Interaction | Tracks all button clicks |
| `image_upload` | User_Interaction | Tracks when users upload images |
| `language_change` | User_Preference | Tracks language selection |

### Classification Events

| Event | Category | Description |
|-------|----------|-------------|
| `food_classification` | ML_Model | Tracks classification results with prediction, confidence, file size, and duration |

### Performance Metrics

| Event | Category | Description |
|-------|----------|-------------|
| `web_vitals` | Performance | Core Web Vitals (CLS, FID, FCP, LCP, TTFB, INP) |
| `slow_api_call` | Performance | API calls taking >3 seconds |
| `slow_resource` | Performance | Resources taking >1 second to load |
| `long_task` | Performance | Tasks blocking main thread >50ms |
| `high_memory_usage` | Performance | Memory usage >90% |

### Error Tracking

| Event | Category | Description |
|-------|----------|-------------|
| `exception` | Error | React error boundary catches |
| `api_error` | API | Failed API requests |
| `repeated_error` | Error | Same error occurring multiple times |

## Usage

### Track Custom Events

```typescript
import { analytics } from '@/utils/analytics';

// Simple event
analytics.event({
  action: 'custom_action',
  category: 'Custom_Category',
  label: 'optional_label',
  value: 123,
});

// Button click
analytics.trackButtonClick('button_name', 'page_location');

// Error
analytics.trackError(error, errorInfo, isFatal);
```

### Measure Performance

```typescript
import { PerformanceTimer } from '@/utils/performance';

// Time an operation
const timer = new PerformanceTimer('operation_name');
// ... do work ...
const duration = timer.end('Category', 'label');
```

### Track API Calls

```typescript
import { measureApiCall } from '@/utils/performance';

const result = await measureApiCall(
  () => fetch('/api/endpoint'),
  'endpoint_name'
);
```

## Web Vitals

The application automatically tracks Core Web Vitals:

- **CLS** (Cumulative Layout Shift): Visual stability
- **FID** (First Input Delay): Interactivity
- **FCP** (First Contentful Paint): Loading performance
- **LCP** (Largest Contentful Paint): Loading performance
- **TTFB** (Time to First Byte): Server response time
- **INP** (Interaction to Next Paint): Responsiveness

### Thresholds

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| CLS | ≤0.1 | ≤0.25 | >0.25 |
| FID | ≤100ms | ≤300ms | >300ms |
| FCP | ≤1.8s | ≤3s | >3s |
| LCP | ≤2.5s | ≤4s | >4s |
| TTFB | ≤800ms | ≤1.8s | >1.8s |
| INP | ≤200ms | ≤500ms | >500ms |

## Privacy & Compliance

- IP anonymization is enabled by default
- No personally identifiable information (PII) is tracked
- Users can opt-out via browser settings or extensions
- Compliant with GDPR and privacy regulations

## Development Mode

In development:
- All events are logged to console
- Analytics warnings are shown if GA ID is missing
- Error details are displayed in ErrorBoundary

## Production Monitoring

### Google Analytics Dashboard

View in GA4:
1. **Real-time** → See live user activity
2. **Events** → All tracked events
3. **Engagement** → User behavior patterns
4. **Tech** → Performance metrics

### Custom Reports

Create custom reports for:
- Classification success rate
- Average confidence scores
- Performance by device/browser
- Error frequency and types

## Troubleshooting

### Analytics not working

1. Check environment variable is set
2. Verify GA Measurement ID format
3. Check browser console for errors
4. Disable ad blockers for testing
5. Check Network tab for gtag requests

### Performance metrics not showing

1. Ensure browser supports PerformanceObserver
2. Check for Content Security Policy issues
3. Verify page is fully loaded before checking

### High memory usage alerts

If you see frequent memory warnings:
1. Check for memory leaks in components
2. Review image handling and cleanup
3. Monitor component unmounting
4. Use React DevTools Profiler

## Best Practices

1. **Don't track PII**: Never send user emails, names, or sensitive data
2. **Batch events**: Avoid tracking too frequently (>1 event/second)
3. **Use meaningful labels**: Make events easy to understand in reports
4. **Test in development**: Verify events before deploying
5. **Monitor performance impact**: Analytics should be lightweight

## Future Enhancements

Potential additions:
- User session recording (e.g., Hotjar, FullStory)
- A/B testing framework
- Custom dashboards
- Real-time alerting for critical errors
- Conversion funnel tracking
