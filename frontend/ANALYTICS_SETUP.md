# Analytics Setup Guide

Quick guide to get analytics and monitoring running in FlavorSnap.

## Quick Start

### 1. Get Google Analytics ID

1. Go to [Google Analytics](https://analytics.google.com)
2. Create a new GA4 property
3. Copy your Measurement ID (format: `G-XXXXXXXXXX`)

### 2. Configure Environment

Create `.env.local` in the `frontend` directory:

```bash
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### 3. Deploy

```bash
npm run build
npm start
```

That's it! Analytics will automatically start tracking.

## What's Being Tracked

### ✅ User Behavior
- Button clicks (camera, classify)
- Image uploads
- Language changes
- Page navigation

### ✅ Classification Events
- Prediction results
- Confidence scores
- File sizes and types
- Processing duration
- Success/failure rates

### ✅ Performance Monitoring
- Core Web Vitals (LCP, FID, CLS, etc.)
- API response times
- Slow resources (>1s)
- Long tasks (>50ms)
- Memory usage

### ✅ Error Tracking
- React error boundary catches
- API failures
- Repeated errors
- Component errors with stack traces

## Verify It's Working

### Development Mode
Check browser console for logs:
```
[Analytics] Initialized with ID: G-XXXXXXXXXX
[Analytics] Page view: { url: '/', title: 'Home' }
[Analytics] Event: { action: 'button_click', ... }
```

### Production Mode
1. Open Google Analytics
2. Go to **Reports** → **Real-time**
3. Interact with your app
4. See events appear in real-time

## View Analytics Data

### In Google Analytics

**Real-time Activity**
- Reports → Real-time → Overview

**All Events**
- Reports → Engagement → Events

**Performance Metrics**
- Reports → Engagement → Pages and screens
- Look for web_vitals events

**Error Tracking**
- Reports → Engagement → Events
- Filter by `exception` and `api_error`

**Classification Analytics**
- Reports → Engagement → Events
- Filter by `food_classification`
- View prediction success rates

## Custom Dashboards

Create custom reports in GA4:

1. **Classification Performance**
   - Metric: food_classification events
   - Dimensions: prediction, confidence
   - Filter: success = true

2. **Error Monitoring**
   - Metric: exception events
   - Dimensions: error_message, fatal
   - Sort by: count descending

3. **Performance Overview**
   - Metric: web_vitals events
   - Dimensions: metric_name, metric_rating
   - Filter: metric_rating = poor

## Testing

Run analytics tests:

```bash
npm test analytics.test.ts
```

## Troubleshooting

### No data in Google Analytics

1. **Check environment variable**
   ```bash
   echo $NEXT_PUBLIC_GA_MEASUREMENT_ID
   ```

2. **Check browser console**
   - Look for analytics initialization logs
   - Check for errors

3. **Check Network tab**
   - Filter by "google-analytics" or "gtag"
   - Verify requests are being sent

4. **Disable ad blockers**
   - Ad blockers may block GA requests
   - Test in incognito mode

### Events not showing

1. **Wait 24-48 hours**
   - Some reports have processing delay
   - Real-time reports show immediate data

2. **Check event names**
   - Events are case-sensitive
   - Use exact names from documentation

### Performance metrics missing

1. **Check browser support**
   - Some metrics require modern browsers
   - Test in Chrome/Edge for full support

2. **Wait for page load**
   - Metrics are collected after page fully loads
   - Navigate between pages to trigger

## Privacy & Compliance

- ✅ IP anonymization enabled
- ✅ No PII tracked
- ✅ GDPR compliant
- ✅ Users can opt-out via browser settings

## Need Help?

- 📖 [Full Documentation](./docs/ANALYTICS.md)
- 🐛 [Report Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

## Next Steps

1. ✅ Set up Google Analytics
2. ✅ Deploy and verify tracking
3. 📊 Create custom dashboards
4. 🔔 Set up alerts for critical errors
5. 📈 Monitor performance trends
6. 🎯 Optimize based on data
