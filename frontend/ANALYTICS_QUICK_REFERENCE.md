# Analytics Quick Reference

## Setup (One-time)

```bash
# 1. Add to .env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX

# 2. Install dependencies (if needed)
npm install @tanstack/react-query react-hook-form @hookform/resolvers zod

# 3. Start dev server
npm run dev
```

## Common Tasks

### Track a Button Click
```typescript
import { analytics } from '@/utils/analytics';

<button onClick={() => analytics.trackButtonClick('button_name', 'page_location')}>
  Click Me
</button>
```

### Track Custom Event
```typescript
analytics.event({
  action: 'user_action',
  category: 'Category',
  label: 'optional_label',
  value: 123,
});
```

### Track API Call Performance
```typescript
import { measureApiCall } from '@/utils/performance';

const data = await measureApiCall(
  () => fetch('/api/endpoint'),
  'endpoint_name'
);
```

### Measure Operation Time
```typescript
import { PerformanceTimer } from '@/utils/performance';

const timer = new PerformanceTimer('operation_name');
// ... do work ...
const duration = timer.end('Category', 'label');
```

### Track Error
```typescript
try {
  // ... code ...
} catch (error) {
  analytics.trackError(error as Error, null, false);
}
```

### Use Analytics Hook
```typescript
import { useAnalytics } from '@/hooks/useAnalytics';

function MyComponent() {
  const { trackClick, trackEvent } = useAnalytics();
  
  return (
    <button onClick={() => trackClick('my_button')}>
      Click
    </button>
  );
}
```

## Event Categories

| Category | Use For |
|----------|---------|
| `User_Interaction` | Clicks, uploads, form submissions |
| `ML_Model` | Classification results |
| `Performance` | Web Vitals, slow operations |
| `Error` | Exceptions, failures |
| `API` | API calls, errors |
| `User_Preference` | Settings, language changes |
| `Engagement` | Time on page, interactions |

## Viewing Data

### Real-time
Google Analytics → Reports → Real-time

### All Events
Google Analytics → Reports → Engagement → Events

### Performance
Filter events by `web_vitals`

### Errors
Filter events by `exception` or `api_error`

### Classifications
Filter events by `food_classification`

## Debug in Development

Open browser console to see:
```
[Analytics] Initialized with ID: G-XXXXXXXXXX
[Analytics] Page view: { url: '/', title: 'Home' }
[Analytics] Event: { action: 'button_click', ... }
[Performance] LCP: { value: 2400, rating: 'good' }
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No data in GA | Check env variable, wait 24-48h for reports |
| Console errors | Verify GA ID format (G-XXXXXXXXXX) |
| Events not tracking | Check browser console, disable ad blockers |
| Performance metrics missing | Use modern browser (Chrome/Edge) |

## Files Reference

| File | Purpose |
|------|---------|
| `utils/analytics.ts` | Core analytics functions |
| `utils/performance.ts` | Performance monitoring |
| `hooks/useAnalytics.ts` | React hooks for analytics |
| `lib/analytics-provider.tsx` | Analytics initialization |
| `docs/ANALYTICS.md` | Full documentation |

## Need More Help?

1. 📖 Read `ANALYTICS_SETUP.md` for detailed setup
2. 📚 Check `docs/ANALYTICS.md` for complete docs
3. 🧪 Run tests: `npm test analytics.test.ts`
4. 🐛 Check browser console for debug logs
