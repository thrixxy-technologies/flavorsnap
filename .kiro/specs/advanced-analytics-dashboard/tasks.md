# Implementation Plan: Advanced Analytics Dashboard

## Overview

Implement the advanced analytics dashboard across four files: `analytics_api.py` (backend endpoints + WebSocket), `dataVisualization.ts` (data transformation utilities), `Charts.tsx` (interactive chart renderer), and `analytics.tsx` (dashboard page orchestration). Tasks are ordered so each step integrates into the previous, ending with full wiring.

## Tasks

- [ ] 1. Set up data models and database schema
  - Add `custom_reports` and `behavior_events` PostgreSQL table migrations to `ml-model-api`
  - Define Python dataclasses/TypedDicts for `ReportConfig`, `PerformanceMetrics`, `BehaviorMetrics`, and `WsMessage`
  - Define TypeScript interfaces (`ChartDataset`, `ReportConfig`, `WsMessage`, `DashboardMode`, `FunnelStep`) in a shared types file
  - _Requirements: 3.1, 3.2, 5.1, 6.1_

- [ ] 2. Implement `dataVisualization.ts` utility functions
  - [ ] 2.1 Implement `transformToChartDataset`, `filterDataset`, and `computeFunnelSteps`
    - Validate non-empty inputs and parseable dates; return empty dataset on invalid input
    - _Requirements: 2.2, 2.5, 6.3, 6.4_

  - [ ]* 2.2 Write property test for `filterDataset` (Property 8)
    - **Property 8: Filter correctness**
    - **Validates: Requirements 2.5**

  - [ ] 2.3 Implement `formatForCSV` and `formatForJSON`
    - CSV: one row per data point, header row with field names
    - JSON: field names must be a subset of the Analytics_API response schema
    - _Requirements: 4.1, 4.2_

  - [ ]* 2.4 Write property tests for export utilities (Properties 11, 12)
    - **Property 11: CSV export completeness — Validates: Requirements 4.1**
    - **Property 12: JSON export schema conformance — Validates: Requirements 4.2**

  - [ ]* 2.5 Write property test for `computeFunnelSteps` (Property 17)
    - **Property 17: Funnel conversion rate correctness**
    - **Validates: Requirements 6.3, 6.4**

- [ ] 3. Checkpoint — Ensure all `dataVisualization.ts` tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement `analytics_api.py` — REST endpoints
  - [ ] 4.1 Implement `GET /analytics/performance-metrics` returning `PerformanceMetrics` shape
    - Pull p50/p95/p99 response times, error rate, and throughput from Prometheus/DB
    - _Requirements: 5.1_

  - [ ] 4.2 Implement `GET /analytics/behavior` returning `BehaviorMetrics` shape
    - Aggregate from `behavior_events` table; exclude all PII; use opaque `session_id` tokens
    - _Requirements: 6.1, 6.5_

  - [ ]* 4.3 Write property test for behavior API PII check (Property 18)
    - **Property 18: Behavior API response contains no PII**
    - **Validates: Requirements 6.5**

  - [ ] 4.4 Implement `POST /analytics/reports`, `GET /analytics/reports/:id`, and `PUT /analytics/reports/:id`
    - POST persists config and returns `report_id`; PUT updates in-place without creating a duplicate; GET 404 on missing ID
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.5 Write property tests for report CRUD (Properties 9, 10)
    - **Property 9: Report save-load round trip — Validates: Requirements 3.2, 3.3, 3.4**
    - **Property 10: Missing report returns 404 — Validates: Requirements 3.5**

  - [ ] 4.6 Implement `GET /analytics/export/csv` and `GET /analytics/export/json` streaming endpoints
    - Stream file response; respect the 100,000-row guard signal from the frontend
    - _Requirements: 4.1, 4.2_

- [ ] 5. Implement `analytics_api.py` — WebSocket endpoint
  - [ ] 5.1 Implement `WS /ws/analytics` with `metric_update`, `connection_ack`, and `reconcile_batch` message types
    - Emit `metric_update` at intervals ≤ 5 seconds; handle `request_reconcile` by replaying missed updates since `since_seq`
    - _Requirements: 1.1, 1.4_

  - [ ]* 5.2 Write property test for streaming interval invariant (Property 1)
    - **Property 1: Streaming update interval invariant**
    - **Validates: Requirements 1.1**

- [ ] 6. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement `Charts.tsx` — Chart Renderer component
  - [ ] 7.1 Implement the `ChartProps` interface and render all five chart types (`line`, `bar`, `pie`, `scatter`, `heatmap`) using Recharts
    - Each type must produce non-empty output for any valid `ChartDataset`
    - _Requirements: 2.1_

  - [ ]* 7.2 Write property test for all chart types rendering (Property 4)
    - **Property 4: All chart types render without error**
    - **Validates: Requirements 2.1**

  - [ ] 7.3 Add unified tooltip rendering (metric name, value, timestamp) to all chart types
    - _Requirements: 2.3_

  - [ ]* 7.4 Write property test for tooltip fields (Property 6)
    - **Property 6: Tooltip contains required fields**
    - **Validates: Requirements 2.3**

  - [ ] 7.5 Implement date range selection handler calling `onDateRangeSelect` and re-rendering within 300ms
    - _Requirements: 2.2_

  - [ ]* 7.6 Write property test for date range scoping (Property 5)
    - **Property 5: Date range scoping correctness**
    - **Validates: Requirements 2.2**

  - [ ] 7.7 Implement `onDrillDown` click handler wired to chart segment/data point click events
    - _Requirements: 2.4_

  - [ ]* 7.8 Write property test for drill-down callback (Property 7)
    - **Property 7: Drill-down callback correctness**
    - **Validates: Requirements 2.4**

  - [ ] 7.9 Add threshold-based alert overlay on metric widgets using the `thresholds` prop
    - _Requirements: 5.3_

  - [ ]* 7.10 Write property test for threshold alert indicator (Property 15)
    - **Property 15: Threshold alert indicator**
    - **Validates: Requirements 5.3**

  - [ ] 7.11 Add PNG export via `html2canvas` at minimum 1920×1080 resolution, triggered by a prop/callback
    - _Requirements: 4.3_

  - [ ] 7.12 Add touch-based pan and zoom event handlers for mobile viewports; enforce `minHeight` prop (minimum 250px)
    - _Requirements: 7.2_

  - [ ]* 7.13 Write property test for mobile chart minimum height (Property 20)
    - **Property 20: Mobile chart minimum height**
    - **Validates: Requirements 7.2**

- [ ] 8. Checkpoint — Ensure all `Charts.tsx` tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement `analytics.tsx` — Dashboard Page
  - [ ] 9.1 Refactor page to support `DashboardMode` state (`overview`, `performance`, `behavior`, `report-builder`) and add `wsRef`, `connectionStatus`, `activeReport`, and `thresholds` state
    - _Requirements: 1.1, 3.1, 5.2_

  - [ ] 9.2 Implement WebSocket connection lifecycle: connect on mount, transition `connectionStatus` to `'reconnecting'` on close, retry every 5 seconds, send `request_reconcile` on reconnect
    - _Requirements: 1.3, 1.4_

  - [ ]* 9.3 Write property test for connection state transitions on disconnect (Property 2)
    - **Property 2: Connection state transitions on disconnect**
    - **Validates: Requirements 1.3**

  - [ ]* 9.4 Write property test for reconciliation after reconnect (Property 3)
    - **Property 3: Reconciliation after reconnect**
    - **Validates: Requirements 1.4**

  - [ ] 9.5 Handle incoming `metric_update` messages and update the affected chart/metric within 500ms; display reconnection indicator when `connectionStatus === 'reconnecting'`
    - _Requirements: 1.2, 1.3_

  - [ ] 9.6 Implement performance monitoring mode: poll `GET /analytics/performance-metrics` at intervals ≤ 10 seconds, retain 24-hour rolling history in state
    - _Requirements: 5.2, 5.4_

  - [ ]* 9.7 Write property test for performance polling interval invariant (Property 14)
    - **Property 14: Performance metric polling interval invariant**
    - **Validates: Requirements 5.2**

  - [ ]* 9.8 Write property test for 24-hour rolling history retention (Property 16)
    - **Property 16: 24-hour rolling history retention**
    - **Validates: Requirements 5.4**

  - [ ] 9.9 Implement behavior analytics view: date range selector calling `GET /analytics/behavior`, funnel visualization using `computeFunnelSteps`, and step detail display
    - _Requirements: 6.2, 6.3, 6.4_

  - [ ] 9.10 Implement report builder UI: metric selector, filter inputs, date range picker, chart type selector; wire `POST`/`PUT`/`GET /analytics/reports` for save and load
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 9.11 Implement CSV, JSON, and PNG export actions; show confirmation modal when dataset exceeds 100,000 rows before initiating any download
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 9.12 Write property test for large dataset export guard (Property 13)
    - **Property 13: Large dataset export guard**
    - **Validates: Requirements 4.4**

  - [ ] 9.13 Implement responsive layout: single-column grid for viewports < 768px, reflow within 300ms on resize without data loss
    - _Requirements: 7.1, 7.4_

  - [ ]* 9.14 Write property test for mobile single-column layout (Property 19)
    - **Property 19: Mobile single-column layout**
    - **Validates: Requirements 7.1**

  - [ ]* 9.15 Write property test for data preservation on resize (Property 21)
    - **Property 21: Data preservation on resize**
    - **Validates: Requirements 7.4**

- [ ] 10. Wire all modules together
  - [ ] 10.1 Connect `analytics.tsx` to `Charts.tsx`: pass `ChartDataset` from `dataVisualization.ts` transforms, wire `onDrillDown`, `onDateRangeSelect`, and `thresholds` props
    - _Requirements: 2.2, 2.4, 2.5, 5.3_

  - [ ] 10.2 Connect filter state in `analytics.tsx` to `filterDataset` in `dataVisualization.ts` and verify re-render within 500ms
    - _Requirements: 2.5_

  - [ ]* 10.3 Write integration tests for `dataVisualization.ts` → `Charts.tsx` prop passing
    - Verify correct `ChartDataset` shape is passed after each transform
    - _Requirements: 2.1, 2.2, 2.5_

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `fast-check` (frontend) and `hypothesis` (backend) with 100 iterations minimum
- Unit tests live in `frontend/__tests__/` and `ml-model-api/test_analytics_api.py`
