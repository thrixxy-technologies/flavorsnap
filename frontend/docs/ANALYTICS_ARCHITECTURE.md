# Analytics Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interactions                       │
│  (Button Clicks, Image Uploads, Language Changes, etc.)     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   React Components                           │
│  • pages/index.tsx (Classification)                          │
│  • components/LanguageSwitcher.tsx                           │
│  • components/ErrorBoundary.tsx                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Analytics Layer                             │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ utils/           │  │ hooks/           │                │
│  │ analytics.ts     │  │ useAnalytics.ts  │                │
│  │                  │  │                  │                │
│  │ • trackEvent()   │  │ • trackClick()   │                │
│  │ • trackError()   │  │ • trackEvent()   │                │
│  │ • trackPerf()    │  │ • createTimer()  │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────────────────────────┐                  │
│  │ utils/performance.ts                  │                  │
│  │                                       │                  │
│  │ • PerformanceTimer                    │                  │
│  │ • measureApiCall()                    │                  │
│  │ • monitorResourceTiming()             │                  │
│  │ • reportWebVitals()                   │                  │
│  └──────────────────────────────────────┘                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Google Analytics 4                          │
│                                                              │
│  window.gtag('event', 'action', { ...data })                │
│                                                              │
│  • Collects events                                           │
│  • Processes metrics                                         │
│  • Generates reports                                         │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Action Flow
```
User clicks button
    ↓
onClick handler
    ↓
analytics.trackButtonClick('button_name', 'location')
    ↓
analytics.event({ action: 'button_click', ... })
    ↓
window.gtag('event', 'button_click', { ... })
    ↓
Google Analytics
```

### 2. Classification Flow
```
User uploads image
    ↓
analytics.trackImageUpload(size, type)
    ↓
User clicks classify
    ↓
PerformanceTimer starts
    ↓
API call to /api/classify
    ↓
Response received
    ↓
timer.end() → duration calculated
    ↓
analytics.trackClassification({
    prediction,
    confidence,
    fileSize,
    fileType,
    duration,
    success
})
    ↓
Google Analytics
```

### 3. Error Flow
```
Error occurs in component
    ↓
ErrorBoundary.componentDidCatch()
    ↓
analytics.trackError(error, errorInfo, fatal)
    ↓
window.gtag('event', 'exception', {
    error_message,
    error_stack,
    component_stack,
    fatal
})
    ↓
Google Analytics
```

### 4. Performance Flow
```
Page loads
    ↓
Web Vitals measured by browser
    ↓
reportWebVitals(metric)
    ↓
analytics.trackPerformance({
    name: 'LCP',
    value: 2400,
    rating: 'good'
})
    ↓
Google Analytics
```

## Component Integration

### _app.tsx (Root)
```typescript
<AnalyticsProvider>          // Initializes GA, monitors performance
  <ErrorBoundary>            // Tracks errors
    <QueryClientProvider>
      <Component />
    </QueryClientProvider>
  </ErrorBoundary>
</AnalyticsProvider>
```

### Page Component
```typescript
function Page() {
  // Track page engagement
  useEngagementTracking('home');
  
  // Track interactions
  const { trackClick } = useAnalytics();
  
  return (
    <button onClick={() => trackClick('button')}>
      Click
    </button>
  );
}
```

## Event Types

### User Interaction Events
```typescript
{
  action: 'button_click' | 'image_upload' | 'form_submit',
  category: 'User_Interaction',
  label: string,
  value?: number
}
```

### ML Model Events
```typescript
{
  action: 'food_classification',
  category: 'ML_Model',
  label: prediction,
  value: confidence * 100,
  prediction: string,
  confidence: number,
  file_size: number,
  file_type: string,
  duration_ms: number,
  success: boolean
}
```

### Performance Events
```typescript
{
  action: 'web_vitals',
  category: 'Performance',
  label: 'LCP' | 'FID' | 'CLS' | 'FCP' | 'TTFB' | 'INP',
  value: number,
  metric_rating: 'good' | 'needs-improvement' | 'poor'
}
```

### Error Events
```typescript
{
  action: 'exception',
  category: 'Error',
  label: error_message,
  description: error_stack,
  fatal: boolean,
  error_name: string,
  component_stack?: string
}
```

## Performance Monitoring

### Automatic Monitoring
- ✅ Web Vitals (CLS, FID, FCP, LCP, TTFB, INP)
- ✅ Resource loading times
- ✅ Long tasks (>50ms)
- ✅ Memory usage
- ✅ Page load time

### Manual Monitoring
```typescript
// Time an operation
const timer = new PerformanceTimer('operation');
// ... work ...
timer.end('Category', 'label');

// Measure API call
await measureApiCall(
  () => fetch('/api/endpoint'),
  'endpoint_name'
);
```

## Error Tracking

### Automatic Error Tracking
- ✅ React component errors (ErrorBoundary)
- ✅ API failures (mutation.onError)
- ✅ Repeated errors

### Manual Error Tracking
```typescript
try {
  // ... code ...
} catch (error) {
  analytics.trackError(error, null, false);
}
```

## Privacy & Security

### Data Anonymization
- IP addresses anonymized
- No PII collected
- User IDs not tracked
- Session-based only

### Compliance
- GDPR compliant
- Cookie consent compatible
- User opt-out supported
- Transparent data collection

## Scalability

### Current Implementation
- Client-side tracking only
- GA4 free tier (10M events/month)
- Real-time processing
- 14-month data retention

### Future Enhancements
- Server-side tracking
- Custom data warehouse
- Real-time dashboards
- Advanced ML analytics
- A/B testing framework

## Testing Strategy

### Unit Tests
```bash
npm test analytics.test.ts
```

### Integration Tests
- Test in development mode
- Verify console logs
- Check Network tab

### Production Verification
- Real-time reports in GA
- Event debugging in GA
- Custom dashboard validation

## Monitoring Checklist

- [ ] GA4 property created
- [ ] Measurement ID configured
- [ ] Analytics initialized
- [ ] Events tracking correctly
- [ ] Performance metrics collected
- [ ] Errors being reported
- [ ] Custom dashboards created
- [ ] Alerts configured
- [ ] Team has access
- [ ] Documentation reviewed

## Resources

- [Google Analytics 4 Documentation](https://developers.google.com/analytics/devguides/collection/ga4)
- [Web Vitals](https://web.dev/vitals/)
- [Performance API](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
