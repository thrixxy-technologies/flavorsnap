# FlavorSnap Analytics & Monitoring

Complete analytics and performance monitoring system for FlavorSnap food classification app.

## 🎯 What's Included

✅ **Google Analytics 4** - Full user behavior tracking  
✅ **Classification Tracking** - ML model performance metrics  
✅ **Performance Monitoring** - Web Vitals and custom metrics  
✅ **Error Tracking** - Automatic error reporting  
✅ **Custom Hooks** - Easy integration in React components  
✅ **Comprehensive Tests** - Full test coverage  
✅ **Documentation** - Complete guides and references  

## 🚀 Quick Start

### 1. Get Google Analytics ID
1. Go to [Google Analytics](https://analytics.google.com)
2. Create a GA4 property
3. Copy your Measurement ID (G-XXXXXXXXXX)

### 2. Configure
```bash
# Create .env.local
echo "NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX" > .env.local
```

### 3. Install & Run
```bash
npm install
npm run dev
```

That's it! Analytics is now tracking.

## 📊 What Gets Tracked

### User Behavior
- Button clicks (camera, classify, retry)
- Image uploads (size, type)
- Language preferences
- Page navigation
- Form submissions

### ML Model Performance
- Classification predictions
- Confidence scores
- Processing time
- Success/failure rates
- File characteristics

### Performance Metrics
- Core Web Vitals (CLS, FID, FCP, LCP, TTFB, INP)
- API response times
- Resource loading times
- Long tasks (>50ms)
- Memory usage

### Error Tracking
- React component errors
- API failures
- Repeated errors
- Full stack traces

## 📁 File Structure

```
frontend/
├── utils/
│   ├── analytics.ts              # Core analytics implementation
│   └── performance.ts             # Performance monitoring
├── lib/
│   └── analytics-provider.tsx     # Analytics initialization
├── hooks/
│   └── useAnalytics.ts            # React hooks for analytics
├── components/
│   └── ErrorBoundary.tsx          # Error tracking
├── pages/
│   ├── _app.tsx                   # Provider integration
│   └── index.tsx                  # Event tracking
├── __tests__/
│   └── analytics.test.ts          # Tests
├── docs/
│   ├── ANALYTICS.md               # Technical documentation
│   └── ANALYTICS_ARCHITECTURE.md  # System architecture
├── .env.example                   # Environment template
├── ANALYTICS_SETUP.md             # Setup guide
├── ANALYTICS_QUICK_REFERENCE.md   # Quick reference
├── DEPLOYMENT_CHECKLIST.md        # Deployment guide
├── IMPLEMENTATION_SUMMARY.md      # Implementation details
└── README_ANALYTICS.md            # This file
```

## 💻 Usage Examples

### Track Custom Event
```typescript
import { analytics } from '@/utils/analytics';

analytics.event({
  action: 'custom_action',
  category: 'Category',
  label: 'label',
  value: 100,
});
```

### Track Button Click
```typescript
<button onClick={() => analytics.trackButtonClick('button_name', 'page')}>
  Click Me
</button>
```

### Measure Performance
```typescript
import { PerformanceTimer } from '@/utils/performance';

const timer = new PerformanceTimer('operation');
// ... do work ...
const duration = timer.end('Category', 'label');
```

### Use Analytics Hook
```typescript
import { useAnalytics } from '@/hooks/useAnalytics';

function MyComponent() {
  const { trackClick } = useAnalytics();
  
  return (
    <button onClick={() => trackClick('my_button')}>
      Click
    </button>
  );
}
```

### Track Engagement
```typescript
import { useEngagementTracking } from '@/hooks/useAnalytics';

function MyPage() {
  useEngagementTracking('page_name');
  // Automatically tracks time spent on page
  return <div>Content</div>;
}
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [ANALYTICS_SETUP.md](./ANALYTICS_SETUP.md) | Quick setup guide |
| [ANALYTICS_QUICK_REFERENCE.md](./ANALYTICS_QUICK_REFERENCE.md) | Quick reference card |
| [docs/ANALYTICS.md](./docs/ANALYTICS.md) | Complete technical docs |
| [docs/ANALYTICS_ARCHITECTURE.md](./docs/ANALYTICS_ARCHITECTURE.md) | System architecture |
| [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) | Deployment guide |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | Implementation details |

## 🧪 Testing

```bash
# Run analytics tests
npm test analytics.test.ts

# Run all tests
npm test
```

## 🔍 Viewing Analytics Data

### Real-time Data
1. Open [Google Analytics](https://analytics.google.com)
2. Go to Reports → Real-time
3. See live user activity

### Historical Data
1. Reports → Engagement → Events
2. Filter by event name
3. Analyze trends

### Custom Reports
Create dashboards for:
- Classification success rates
- Performance metrics
- Error frequency
- User behavior patterns

## 🐛 Troubleshooting

### No data in Google Analytics
- Check environment variable is set
- Verify GA Measurement ID format
- Wait 24-48 hours for reports
- Check Real-time reports for immediate data
- Disable ad blockers

### Events not tracking
- Check browser console for errors
- Verify analytics is initialized
- Test in incognito mode
- Check Network tab for gtag requests

### Performance metrics missing
- Use modern browser (Chrome/Edge)
- Wait for page to fully load
- Check PerformanceObserver support

## 🔒 Privacy & Compliance

- ✅ IP anonymization enabled
- ✅ No PII tracked
- ✅ GDPR compliant
- ✅ User opt-out supported
- ✅ Transparent data collection

## 📈 Benefits

1. **Data-Driven Decisions** - Understand user behavior
2. **Performance Optimization** - Identify bottlenecks
3. **Error Prevention** - Catch issues early
4. **ML Insights** - Track model accuracy
5. **User Experience** - Monitor Core Web Vitals
6. **Business Metrics** - Track engagement

## 🎯 Next Steps

1. ✅ Complete setup (see [ANALYTICS_SETUP.md](./ANALYTICS_SETUP.md))
2. 📊 Create custom dashboards
3. 🔔 Set up alerts
4. 📈 Monitor trends
5. 🎯 Optimize based on data

## 🤝 Contributing

When adding new features:
1. Add appropriate analytics tracking
2. Update documentation
3. Add tests
4. Follow existing patterns

## 📞 Support

- 📖 Check documentation files
- 🧪 Run tests for debugging
- 🔍 Check browser console (dev mode)
- 💬 Ask team for help

## 📝 License

Same as main project.

---

**Ready to track?** Follow [ANALYTICS_SETUP.md](./ANALYTICS_SETUP.md) to get started!
