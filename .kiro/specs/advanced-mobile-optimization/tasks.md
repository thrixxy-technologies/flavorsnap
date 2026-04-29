# Implementation Plan: Advanced Mobile Optimization

## Overview

Implement the mobile optimization layer across four files: `useMobile.ts` (device/state hook), `mobileUtils.ts` (gesture handling, device detection, analytics), `MobileOptimized.tsx` (primary component), and `mobile.css` (touch and layout styles). Tasks are ordered so each step builds on the previous, ending with full integration.

## Tasks

- [ ] 1. Set up core types and interfaces
  - Create `DeviceProfile`, `GestureEvent`, `GestureType`, `AnalyticsEvent`, and `MobileAnalyticsConfig` TypeScript interfaces in `mobileUtils.ts`
  - Define the breakpoint map constants (`xs`/`sm`/`md`/`lg`/`xl`) and their pixel thresholds
  - _Requirements: 2.1, 6.1_

- [ ] 2. Implement device detection utilities in `mobileUtils.ts`
  - [ ] 2.1 Implement `detectOS(userAgent: string)` using the ordered regex rules from the design
    - _Requirements: 6.5_
  - [ ]* 2.2 Write property test for OS detection (Property 16)
    - **Property 16: OS detection from userAgent**
    - **Validates: Requirements 6.5**
  - [ ] 2.3 Implement `buildDeviceProfile()` reading `window.devicePixelRatio`, `window.innerWidth/Height`, `ontouchstart`, and `matchMedia('(pointer: fine)')`
    - _Requirements: 6.1_
  - [ ] 2.4 Implement `debounce(fn, delay)` utility with 16ms default
    - _Requirements: 3.6_
  - [ ]* 2.5 Write property test for debounce correctness (Property 7)
    - **Property 7: Debounce correctness**
    - **Validates: Requirements 3.6**
  - [ ] 2.6 Implement `shouldReduceAnimations()` checking `navigator.hardwareConcurrency <= 4`
    - _Requirements: 3.2_
  - [ ]* 2.7 Write property test for animation reduction threshold (Property 5)
    - **Property 5: Animation reduction on low-concurrency devices**
    - **Validates: Requirements 3.2**

- [ ] 3. Implement GestureHandler in `mobileUtils.ts`
  - [ ] 3.1 Implement `attachGestureHandler` with tap and long-press recognition (500ms hold, <10px movement)
    - _Requirements: 1.1, 1.2_
  - [ ]* 3.2 Write property test for long-press dispatch (Property 1)
    - **Property 1: Long-press event dispatch**
    - **Validates: Requirements 1.2**
  - [ ] 3.3 Implement swipe recognition (≥50px displacement, ≤300ms, ≥0.3 px/ms velocity) dispatching directional swipe events
    - _Requirements: 5.1, 5.2, 5.5_
  - [ ]* 3.4 Write property test for swipe dispatch with direction and velocity (Property 9)
    - **Property 9: Swipe dispatch with direction and velocity**
    - **Validates: Requirements 5.1, 5.2**
  - [ ]* 3.5 Write property test for velocity threshold preventing swipe (Property 12)
    - **Property 12: Velocity threshold prevents swipe**
    - **Validates: Requirements 5.5**
  - [ ] 3.6 Implement pinch recognition using two-touch Euclidean distance ratio
    - _Requirements: 5.3_
  - [ ]* 3.7 Write property test for pinch scale calculation (Property 10)
    - **Property 10: Pinch scale calculation**
    - **Validates: Requirements 5.3**
  - [ ] 3.8 Implement multi-touch cancellation of in-progress single-touch gestures
    - _Requirements: 5.6_
  - [ ]* 3.9 Write property test for multi-touch cancellation (Property 13)
    - **Property 13: Multi-touch cancels in-progress single-touch gesture**
    - **Validates: Requirements 5.6**
  - [ ] 3.10 Implement gesture propagation to nearest ancestor with a registered handler
    - _Requirements: 5.4_
  - [ ]* 3.11 Write property test for gesture propagation (Property 11)
    - **Property 11: Gesture propagation to ancestor**
    - **Validates: Requirements 5.4**

- [ ] 4. Checkpoint — Ensure all utility and gesture tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement MobileAnalytics in `mobileUtils.ts`
  - [ ] 5.1 Implement `createMobileAnalytics` with in-memory event queue, 10s interval flush, and 20-event batch flush
    - _Requirements: 7.5_
  - [ ]* 5.2 Write property test for batch flush at event count threshold (Property 20)
    - **Property 20: Batch flush at event count threshold**
    - **Validates: Requirements 7.5**
  - [ ] 5.3 Implement exponential backoff retry (1s, 2s, 4s) on non-2xx responses, max 3 retries
    - _Requirements: 7.6_
  - [ ]* 5.4 Write property test for retry on non-2xx response (Property 21)
    - **Property 21: Retry on non-2xx response**
    - **Validates: Requirements 7.6**
  - [ ] 5.5 Integrate `web-vitals` callbacks to record LCP, CLS, FID/INP events and `performance_budget_exceeded` when thresholds are breached
    - _Requirements: 7.3, 7.4_
  - [ ]* 5.6 Write property test for performance budget exceeded event (Property 19)
    - **Property 19: Performance budget exceeded event**
    - **Validates: Requirements 7.4**
  - [ ]* 5.7 Write property test for no PII in analytics payloads (Property 22)
    - **Property 22: No PII in analytics payloads**
    - **Validates: Requirements 7.7**
  - [ ]* 5.8 Write unit tests for MobileAnalytics batching, retry, and web-vitals recording
    - Test file: `frontend/__tests__/mobileAnalytics.test.ts`
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

- [ ] 6. Implement `useMobile` hook in `useMobile.ts`
  - [ ] 6.1 Build hook that initializes `DeviceProfile` via `buildDeviceProfile()` and exposes `isStandalone`, `orientation`, and `breakpoint`
    - _Requirements: 4.4, 6.1_
  - [ ] 6.2 Subscribe to `resize` and `orientationchange` events (debounced at 16ms) and update state inside `requestAnimationFrame`
    - _Requirements: 2.6, 6.6_
  - [ ]* 6.3 Write unit tests for hook state, DeviceProfile shape, and orientation updates
    - Test file: `frontend/__tests__/useMobile.test.ts`
    - _Requirements: 2.6, 6.1, 6.6_

- [ ] 7. Implement `mobile.css` styles
  - [ ] 7.1 Add responsive single/two-column layout rules at the defined breakpoints (320px, 480px, 768px, 1024px)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [ ] 7.2 Add `-webkit-overflow-scrolling: touch` and `overscroll-behavior` rules for scrollable containers
    - _Requirements: 1.4_
  - [ ] 7.3 Add safe-area inset padding using `env(safe-area-inset-*)` for iOS
    - _Requirements: 4.5_
  - [ ] 7.4 Add conditional hover and pointer-cursor styles gated on `@media (pointer: fine)`; add 8px minimum spacing rules for coarse-pointer devices
    - _Requirements: 6.3, 6.4_

- [ ] 8. Implement `MobileOptimized.tsx` component
  - [ ] 8.1 Scaffold the component with `MobileOptimizedProps`, consume `useMobile`, apply responsive layout classes from `mobile.css`, and render children
    - _Requirements: 2.2, 2.3, 2.4, 2.5_
  - [ ]* 8.2 Write property test for breakpoint-to-layout mapping (Property 4)
    - **Property 4: Breakpoint-to-layout mapping**
    - **Validates: Requirements 2.2, 2.3, 2.4**
  - [ ] 8.3 Attach `GestureHandler` via `useEffect` on the root element; wire `gestureHandlers` prop and analytics `touch_interaction` recording
    - _Requirements: 1.1, 7.1_
  - [ ]* 8.4 Write property test for touch_interaction analytics event completeness (Property 17)
    - **Property 17: touch_interaction analytics event completeness**
    - **Validates: Requirements 7.1**
  - [ ] 8.5 Implement touch target expansion: detect elements smaller than 44×44px and apply hit-area expansion without changing visual size
    - _Requirements: 1.3_
  - [ ]* 8.6 Write property test for touch target minimum size (Property 2)
    - **Property 2: Touch target minimum size**
    - **Validates: Requirements 1.3**
  - [ ] 8.7 Implement `preventDefault` on interactive controls with custom touch handling
    - _Requirements: 1.5_
  - [ ]* 8.8 Write property test for preventDefault on interactive controls (Property 3)
    - **Property 3: Prevent default on interactive controls**
    - **Validates: Requirements 1.5**
  - [ ] 8.9 Implement `IntersectionObserver`-based lazy loading for images and deferred components with 200px root margin; fall back to eager loading when API is unavailable
    - _Requirements: 3.1_
  - [ ] 8.10 Implement virtualized list rendering for lists with more than 50 items (render only items within 1.5× viewport height)
    - _Requirements: 3.5_
  - [ ]* 8.11 Write property test for virtualized list rendering threshold (Property 6)
    - **Property 6: Virtualized list rendering threshold**
    - **Validates: Requirements 3.5**
  - [ ] 8.12 Apply `shouldReduceAnimations()` result to disable non-essential CSS transitions on low-concurrency devices
    - _Requirements: 3.2_
  - [ ] 8.13 Implement Web Share API action (hidden when `navigator.share` is unavailable) and Vibration API haptic pulse (10ms, no-op when unavailable)
    - _Requirements: 4.1, 4.2_
  - [ ] 8.14 Set correct `inputmode` attributes on `tel`, `email`, and `number` inputs
    - _Requirements: 4.3_
  - [ ]* 8.15 Write property test for inputmode attribute correctness (Property 8)
    - **Property 8: inputmode attribute correctness**
    - **Validates: Requirements 4.3**
  - [ ] 8.16 Serve 2x image assets via `srcset` when `DeviceProfile.pixelRatio >= 2`
    - _Requirements: 6.2_
  - [ ]* 8.17 Write property test for high-DPI image srcset (Property 14)
    - **Property 14: High-DPI image srcset**
    - **Validates: Requirements 6.2**
  - [ ]* 8.18 Write property test for hover state conditional on hasFinePointer (Property 15)
    - **Property 15: Hover state conditional on hasFinePointer**
    - **Validates: Requirements 6.3, 6.4**
  - [ ] 8.19 Wire `MobileAnalytics` instance: initialize with `analyticsEndpoint` prop, record `viewport_change` events from `useMobile`, and call `destroy()` on unmount
    - _Requirements: 7.2_
  - [ ]* 8.20 Write property test for viewport_change analytics event completeness (Property 18)
    - **Property 18: viewport_change analytics event completeness**
    - **Validates: Requirements 7.2**
  - [ ]* 8.21 Write unit tests for component rendering, layout, touch targets, and inputmode
    - Test file: `frontend/__tests__/MobileOptimized.test.tsx`
    - _Requirements: 1.3, 2.1, 2.5, 4.3, 6.3, 6.4_

- [ ] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `fast-check` (add as dev dependency: `npm install -D fast-check`)
- Each property test must include the comment `// Feature: advanced-mobile-optimization, Property N: <text>`
- All 22 correctness properties from the design document are covered by property sub-tasks
