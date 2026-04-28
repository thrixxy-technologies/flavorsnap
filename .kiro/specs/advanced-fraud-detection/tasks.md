# Implementation Plan: Advanced Fraud Detection

## Overview

Implement the fraud detection pipeline incrementally: data models and interfaces first, then feature extraction, ML inference, anomaly detection, risk scoring, alerting, investigation API, reporting, and performance monitoring. Frontend alert UI is wired in last.

## Tasks

- [ ] 1. Define core data models and interfaces
  - Add `Transaction`, `FeatureVector`, `ModelOutput`, `AnomalySignal`, `RiskScore`, `Alert`, `Case`, `ModelVersion` dataclasses to a shared `models.py` module
  - Ensure all fields match the design data models exactly
  - _Requirements: 1.1, 2.3, 3.3, 4.1, 4.4, 5.1, 6.1_

- [ ] 2. Implement Feature Extractor
  - [ ] 2.1 Implement `FeatureExtractor.extract` in `fraud_detection.py`
    - Accept a `Transaction` and `AccountHistory`, return a non-empty `FeatureVector`
    - _Requirements: 2.3_
  - [ ]* 2.2 Write property test for feature extraction (Property 1)
    - **Property 1: Feature extraction always produces a vector**
    - **Validates: Requirements 2.3**

- [ ] 3. Implement ML Model Inference
  - [ ] 3.1 Implement `FraudDetectionEngine.load_model` and `get_active_models` in `fraud_detection.py`
    - Support loading multiple model versions; track active versions and A/B traffic fractions
    - _Requirements: 2.1, 2.4_
  - [ ] 3.2 Implement hot-swap logic so loading a new version does not restart the service
    - _Requirements: 2.2_
  - [ ]* 3.3 Write property test for model hot-swap (Property 2)
    - **Property 2: Model hot-swap activates new version**
    - **Validates: Requirements 2.2, 2.4**
  - [ ] 3.4 Implement model inference fallback: on inference failure, fall back to previous version and emit error log
    - _Requirements: 2.5_

- [ ] 4. Implement Anomaly Detector
  - [ ] 4.1 Implement `AnomalyDetector.update_baseline` in `anomaly_detection.py`
    - Maintain a rolling 30-day per-user baseline; evict data older than 30 days on each update
    - Fall back to global population baseline when per-user history is insufficient
    - _Requirements: 3.1, 3.5_
  - [ ]* 4.2 Write property test for baseline window (Property 3)
    - **Property 3: Baseline excludes data older than 30 days**
    - **Validates: Requirements 3.1**
  - [ ] 4.3 Implement `AnomalyDetector.score` to compute deviation score and velocity flag
    - Flag transaction as anomalous when deviation exceeds configurable threshold; set `velocity_flag` for frequency/volume spikes
    - _Requirements: 3.2, 3.3, 3.4_
  - [ ]* 4.4 Write property test for anomaly flagging and signal emission (Property 4)
    - **Property 4: Anomaly flagging and signal emission**
    - **Validates: Requirements 3.2, 3.3**
  - [ ]* 4.5 Write property test for velocity anomaly detection (Property 5)
    - **Property 5: Velocity anomaly detection**
    - **Validates: Requirements 3.4**

- [ ] 5. Implement Risk Scorer
  - [ ] 5.1 Implement `RiskScorer.compute` in `risk_assessment.py`
    - Apply configurable weighted formula over model output and anomaly signal; clamp result to [0, 100]; classify into low/medium/high tier
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 5.2 Write property test for risk score bounds (Property 6)
    - **Property 6: Risk score is always bounded 0–100**
    - **Validates: Requirements 4.1**
  - [ ]* 5.3 Write property test for weighted formula (Property 7)
    - **Property 7: Risk score is a weighted combination of inputs**
    - **Validates: Requirements 4.2**
  - [ ]* 5.4 Write property test for tier classification (Property 8)
    - **Property 8: Tier classification is correct and exhaustive**
    - **Validates: Requirements 4.3**
  - [ ] 5.5 Implement `RiskScorer.persist` and `GET /risk-score/{transaction_id}` REST endpoint
    - Persist score, tier, signals, and timestamp; return them via the endpoint
    - _Requirements: 4.4, 4.5_
  - [ ]* 5.6 Write property test for risk score persistence round-trip (Property 9)
    - **Property 9: Risk score persistence round-trip**
    - **Validates: Requirements 4.4, 4.5**

- [ ] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Fraud Detection Engine orchestration
  - [ ] 7.1 Implement `FraudDetectionEngine.evaluate` in `fraud_detection.py`
    - Orchestrate feature extraction → model inference → anomaly scoring → risk scoring within 300ms; apply configurable fallback score and log on timeout
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ]* 7.2 Write unit tests for FDE timeout fallback and model inference fallback
    - Inject mock timeout and mock inference failure; assert fallback score applied and error logged
    - _Requirements: 1.3, 2.5_

- [ ] 8. Implement Alert Manager
  - [ ] 8.1 Implement `AlertManager.create_alert` with idempotency per transaction
    - Create alert only for high-tier scores; return existing alert ID on duplicate calls
    - _Requirements: 5.1, 5.3_
  - [ ]* 8.2 Write property test for high-tier transactions always producing an alert (Property 10)
    - **Property 10: High-tier transactions always produce an alert**
    - **Validates: Requirements 5.1**
  - [ ]* 8.3 Write property test for alert creation idempotency (Property 11)
    - **Property 11: Alert creation is idempotent per transaction**
    - **Validates: Requirements 5.3**
  - [ ] 8.4 Implement alert routing to email and in-app notification channels
    - _Requirements: 5.2_
  - [ ] 8.5 Implement `AlertManager.acknowledge`
    - Update status to acknowledged; persist analyst identifier and timestamp
    - _Requirements: 5.4_
  - [ ]* 8.6 Write property test for alert acknowledgment persistence (Property 12)
    - **Property 12: Alert acknowledgment is persisted**
    - **Validates: Requirements 5.4**
  - [ ] 8.7 Implement `AlertManager.apply_suppression_rules` and escalation on unacknowledged alerts
    - Evaluate configurable suppression rules; escalate to secondary channel after configurable duration
    - _Requirements: 5.5, 5.6_
  - [ ]* 8.8 Write property test for suppression rules (Property 13)
    - **Property 13: Suppression rules are applied correctly**
    - **Validates: Requirements 5.5**

- [ ] 9. Implement Investigation Tool API
  - [ ] 9.1 Implement `GET /cases/{case_id}` endpoint
    - Return transaction details, risk score, contributing signals, anomaly flags, and account history
    - _Requirements: 6.1_
  - [ ]* 9.2 Write property test for case detail completeness (Property 14)
    - **Property 14: Case detail contains all required fields**
    - **Validates: Requirements 6.1**
  - [ ] 9.3 Implement `GET /cases/{case_id}/transactions` endpoint
    - Return all transactions for the same user account within the preceding 90 days
    - _Requirements: 6.2_
  - [ ]* 9.4 Write property test for 90-day transaction history scope (Property 15)
    - **Property 15: Case transaction history is scoped to 90 days**
    - **Validates: Requirements 6.2**
  - [ ] 9.5 Implement `POST /cases/{case_id}/resolution` endpoint
    - Accept resolution status, free-text notes, and analyst identifier; persist with timestamp
    - _Requirements: 6.3, 6.4_
  - [ ]* 9.6 Write property test for case resolution round-trip (Property 16)
    - **Property 16: Case resolution round-trip**
    - **Validates: Requirements 6.3, 6.4**
  - [ ] 9.7 Implement `GET /cases` search endpoint with filters
    - Support filtering by date range, risk score tier, resolution status, and user account identifier
    - _Requirements: 6.5_
  - [ ]* 9.8 Write property test for case search filter correctness (Property 17)
    - **Property 17: Case search filters are correct**
    - **Validates: Requirements 6.5**
  - [ ] 9.9 Implement RBAC middleware for case endpoints
    - Deny access with HTTP 403 for users without fraud analyst or administrator role; log access attempts
    - _Requirements: 6.6_
  - [ ]* 9.10 Write property test for RBAC access control (Property 18)
    - **Property 18: RBAC restricts case access by role**
    - **Validates: Requirements 6.6**

- [ ] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement Reporting System
  - [ ] 11.1 Implement `ReportingSystem.generate_daily_report` in a new `reporting.py` module
    - Aggregate total transactions, alert counts by tier, confirmed fraud count, and false positive rate; deliver to configured recipients via email
    - _Requirements: 7.1, 7.3_
  - [ ]* 11.2 Write property test for daily report correctness (Property 19)
    - **Property 19: Daily report contains all required metrics**
    - **Validates: Requirements 7.1**
  - [ ] 11.3 Implement `ReportingSystem.on_demand_report` with CSV and JSON export
    - Accept date range; aggregate only data within that range; return bytes in requested format
    - _Requirements: 7.2, 7.5_
  - [ ]* 11.4 Write property test for on-demand report date range scoping (Property 20)
    - **Property 20: On-demand report aggregates only the requested date range**
    - **Validates: Requirements 7.2**
  - [ ]* 11.5 Write property test for CSV/JSON export equivalence (Property 21)
    - **Property 21: Report export formats are equivalent**
    - **Validates: Requirements 7.5**
  - [ ] 11.6 Implement report retry logic and failure alerting
    - Retry up to 3 times on failure; emit failure alert after final retry; retain report data for 12 months
    - _Requirements: 7.4, 7.6_

- [ ] 12. Implement Performance Monitor
  - [ ] 12.1 Implement `PerformanceMonitor.record_evaluation` and Prometheus scrape endpoint in `risk_assessment.py`
    - Track p50/p95/p99 evaluation latency, alert creation latency, model inference latency, and Risk Scorer throughput; expose via `GET /metrics`
    - _Requirements: 8.1, 8.4, 8.6_
  - [ ]* 12.2 Write property test for metrics dimensions completeness (Property 22)
    - **Property 22: Performance metrics expose all required dimensions**
    - **Validates: Requirements 8.1, 8.4**
  - [ ] 12.3 Implement `PerformanceMonitor.compute_model_quality`
    - Compute precision, recall, and FPR on rolling 24-hour window using resolved cases as ground truth; retain raw metric data for 30 days
    - _Requirements: 8.2, 8.5_
  - [ ]* 12.4 Write property test for model quality metric correctness (Property 23)
    - **Property 23: Model quality metrics are mathematically correct**
    - **Validates: Requirements 8.2**
  - [ ] 12.5 Implement metric threshold alerting
    - Emit exactly one alert to the operations notification channel when any tracked metric exceeds its configurable threshold
    - _Requirements: 8.3_
  - [ ]* 12.6 Write property test for metric threshold breach alerting (Property 24)
    - **Property 24: Metric threshold breach triggers alert**
    - **Validates: Requirements 8.3**

- [ ] 13. Implement FraudAlerts frontend component
  - [ ] 13.1 Update `frontend/components/FraudAlerts.tsx` to render the alert list
    - Fetch alerts from the API; display risk score tier, transaction details, and status; link each alert to its case detail view
    - _Requirements: 5.2, 6.1_
  - [ ] 13.2 Wire case detail navigation and resolution form into `FraudAlerts.tsx`
    - Allow analysts to open a case, view 90-day history, submit resolution with notes
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis` (Python) and `fast-check` (TypeScript)
- Each property test must be tagged: `# Feature: advanced-fraud-detection, Property {N}: {property_text}`
