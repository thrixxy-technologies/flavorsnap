# Analytics Deployment Checklist

Use this checklist to ensure analytics is properly configured and working.

## Pre-Deployment

### 1. Google Analytics Setup
- [ ] Created GA4 property at [analytics.google.com](https://analytics.google.com)
- [ ] Copied Measurement ID (format: G-XXXXXXXXXX)
- [ ] Added team members to GA property
- [ ] Configured data retention settings (14 months recommended)

### 2. Environment Configuration
- [ ] Created `.env.local` file
- [ ] Added `NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX`
- [ ] Verified environment variable is loaded (`echo $NEXT_PUBLIC_GA_MEASUREMENT_ID`)

### 3. Dependencies
- [ ] Verified all dependencies are installed:
  ```bash
  npm install
  ```
- [ ] Check for missing dependencies:
  - `@tanstack/react-query`
  - `react-hook-form`
  - `@hookform/resolvers`
  - `zod`

### 4. Code Review
- [ ] Reviewed `utils/analytics.ts` - Core analytics
- [ ] Reviewed `utils/performance.ts` - Performance monitoring
- [ ] Reviewed `lib/analytics-provider.tsx` - Initialization
- [ ] Reviewed `components/ErrorBoundary.tsx` - Error tracking
- [ ] Reviewed `pages/_app.tsx` - Provider integration
- [ ] Reviewed `pages/index.tsx` - Event tracking

### 5. Local Testing
- [ ] Started dev server: `npm run dev`
- [ ] Opened browser console
- [ ] Verified analytics initialization log
- [ ] Tested button clicks → Check console for events
- [ ] Tested image upload → Check console for tracking
- [ ] Tested classification → Check console for metrics
- [ ] Tested language change → Check console for event
- [ ] Triggered error → Check console for error tracking
- [ ] Checked Network tab for gtag requests

### 6. Build Test
- [ ] Built production bundle: `npm run build`
- [ ] No build errors
- [ ] No TypeScript errors
- [ ] Started production server: `npm start`
- [ ] Verified analytics works in production mode

## Deployment

### 7. Deploy to Production
- [ ] Deployed to hosting platform (Vercel, Netlify, etc.)
- [ ] Added `NEXT_PUBLIC_GA_MEASUREMENT_ID` to platform environment variables
- [ ] Verified deployment successful
- [ ] Visited production URL

### 8. Production Verification
- [ ] Opened production site
- [ ] Opened Google Analytics → Real-time reports
- [ ] Performed test interactions:
  - [ ] Clicked camera button
  - [ ] Uploaded image
  - [ ] Clicked classify button
  - [ ] Changed language
  - [ ] Navigated between pages
- [ ] Verified events appear in Real-time reports (may take 1-2 minutes)

### 9. Event Verification
Check these events in GA Real-time:
- [ ] `page_view` - Page navigation
- [ ] `button_click` - Button interactions
- [ ] `image_upload` - Image uploads
- [ ] `food_classification` - Classification results
- [ ] `language_change` - Language switches
- [ ] `web_vitals` - Performance metrics

### 10. Performance Metrics
- [ ] Wait 24-48 hours for full data
- [ ] Check Reports → Engagement → Pages and screens
- [ ] Verify Web Vitals are being collected
- [ ] Check for slow API calls
- [ ] Review resource loading times

## Post-Deployment

### 11. Create Custom Dashboards
- [ ] Classification Performance Dashboard
  - Metric: `food_classification` events
  - Dimensions: prediction, confidence, success
  - Filters: success = true/false
  
- [ ] Error Monitoring Dashboard
  - Metric: `exception` events
  - Dimensions: error_message, fatal
  - Sort by: count descending
  
- [ ] Performance Overview Dashboard
  - Metric: `web_vitals` events
  - Dimensions: metric_name, metric_rating
  - Filters: metric_rating = poor

### 12. Set Up Alerts
- [ ] High error rate alert (>10 errors/hour)
- [ ] Poor performance alert (LCP >4s)
- [ ] Low classification success rate (<80%)
- [ ] API error spike alert

### 13. Team Access
- [ ] Added team members to GA property
- [ ] Shared dashboard links
- [ ] Documented how to access reports
- [ ] Scheduled weekly review meeting

### 14. Documentation
- [ ] Team reviewed `ANALYTICS_SETUP.md`
- [ ] Team reviewed `docs/ANALYTICS.md`
- [ ] Team has access to `ANALYTICS_QUICK_REFERENCE.md`
- [ ] Created internal wiki/docs page

### 15. Monitoring Schedule
- [ ] Daily: Check Real-time reports for issues
- [ ] Weekly: Review classification success rates
- [ ] Weekly: Review performance metrics
- [ ] Monthly: Analyze user behavior trends
- [ ] Monthly: Review and optimize based on data

## Troubleshooting

### No Data in Google Analytics
- [ ] Verified Measurement ID is correct
- [ ] Checked environment variable is set in production
- [ ] Waited 24-48 hours for reports to populate
- [ ] Checked Real-time reports (immediate data)
- [ ] Disabled ad blockers
- [ ] Tested in incognito mode
- [ ] Checked browser console for errors
- [ ] Verified gtag requests in Network tab

### Events Not Tracking
- [ ] Checked event names are correct (case-sensitive)
- [ ] Verified analytics is initialized
- [ ] Checked browser console for errors
- [ ] Tested in different browsers
- [ ] Verified no Content Security Policy blocking

### Performance Metrics Missing
- [ ] Tested in modern browser (Chrome/Edge)
- [ ] Waited for page to fully load
- [ ] Checked PerformanceObserver support
- [ ] Verified no errors in console

## Success Criteria

### Week 1
- [ ] All events tracking correctly
- [ ] Real-time data visible
- [ ] No console errors
- [ ] Team can access GA

### Week 2
- [ ] Historical data accumulating
- [ ] Custom dashboards created
- [ ] Alerts configured
- [ ] First insights gathered

### Month 1
- [ ] Baseline metrics established
- [ ] Performance trends identified
- [ ] User behavior patterns understood
- [ ] First optimizations implemented

## Maintenance

### Weekly Tasks
- [ ] Review error reports
- [ ] Check performance metrics
- [ ] Monitor classification success rates
- [ ] Review user behavior patterns

### Monthly Tasks
- [ ] Analyze trends
- [ ] Update dashboards
- [ ] Review and adjust alerts
- [ ] Share insights with team
- [ ] Plan optimizations

### Quarterly Tasks
- [ ] Comprehensive analytics review
- [ ] Update tracking strategy
- [ ] Evaluate new metrics to track
- [ ] Review privacy compliance

## Notes

Add any deployment-specific notes here:

---

**Deployment Date**: _______________

**Deployed By**: _______________

**GA Measurement ID**: _______________

**Production URL**: _______________

**Issues Encountered**: 

---

## Sign-off

- [ ] Analytics properly configured
- [ ] All events tracking correctly
- [ ] Team trained on GA access
- [ ] Documentation complete
- [ ] Ready for production monitoring

**Signed**: _______________ **Date**: _______________
