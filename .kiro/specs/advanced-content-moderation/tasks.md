# Implementation Plan: Advanced Content Moderation

## Overview

Implement the AI-powered content moderation system incrementally: core data models and DB schema first, then the AI classifier, automated reviewer, appeals system, metrics service, and finally the frontend moderation panel. Each layer builds on the previous and is wired together at the end.

## Tasks

- [ ] 1. Define core data models and database schema
  - Implement `ContentItem`, `ModerationDecision`, `AppealRecord`, and `QueueItem` dataclasses/models in Python
  - Create PostgreSQL migration with tables and indexes on `content_id`, `decided_at`, `status`, `reviewer_id`
  - _Requirements: 1.4, 3.1, 3.6, 4.3, 5.5_

- [ ] 2. Implement AI Classifier (`content_moderation.py`)
  - [ ] 2.1 Implement `AIClassifier.classify()` for text, image, and combined `ContentItem` inputs
    - Return `ClassificationResult` with `decision`, `confidence_score`, and `category`
    - Enforce valid category set: `hate_speech`, `spam`, `explicit_content`, `harassment`, `safe`
    - Return highest-severity category when multiple violation signals are detected
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 Write property test for confidence threshold routing (Properties 1 & 2)
    - **Property 1: High-confidence decisions are never escalated**
    - **Property 2: Low-confidence decisions are always escalated**
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 2.3 Write property test for valid category output (Property 5)
    - **Property 5: Classifier returns a valid category for every input**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ]* 2.4 Write property test for multi-signal severity (Property 6)
    - **Property 6: Multi-signal items return highest-severity category**
    - **Validates: Requirements 2.4**

  - [ ] 2.5 Implement `ModelRegistry` with `begin_swap()` and `complete_swap()` for zero-downtime model version updates
    - _Requirements: 2.5_

- [ ] 3. Implement Automated Reviewer (`automated_review.py`)
  - [ ] 3.1 Implement `AutomatedReviewer.review()` with confidence threshold routing and decision persistence
    - Route to `approved`/`rejected` when score ≥ 0.90, else `escalated`
    - Persist `ModerationDecision` with decision, confidence_score, category, timestamp, and `source="automated"`
    - On classifier failure: escalate and log error code
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 3.2 Write property test for persisted decision record (Property 3)
    - **Property 3: Every processed item has a persisted decision record**
    - **Validates: Requirements 1.4**

  - [ ]* 3.3 Write property test for classifier failure escalation (Property 4)
    - **Property 4: Classifier failure always escalates**
    - **Validates: Requirements 1.5**

  - [ ]* 3.4 Write unit tests for `AutomatedReviewer.review()`
    - Test boundary scores: 0.89, 0.90, 0.91
    - Test classifier exception path
    - _Requirements: 1.2, 1.3, 1.5_

- [ ] 4. Checkpoint — Ensure all backend classifier and reviewer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Appeals System (`appeals_system.py`)
  - [ ] 5.1 Implement `AppealsSystem.submit_appeal()` with duplicate detection and queue enqueue
    - Create `AppealRecord` with status `pending` and unique ID for rejected items only
    - Reject duplicate appeals with 409 error
    - Enforce reason string ≤ 1000 characters (400 error if exceeded)
    - Enqueue `ContentItem` to human review queue within 60 seconds
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 5.2 Implement `AppealsSystem.resolve_appeal()` with status update and user notification
    - Update appeal status to `approved` or `denied`, record `resolved_at` and `resolved_by`
    - Trigger notification to originating user
    - _Requirements: 3.5_

  - [ ]* 5.3 Write property test for appeal creation and duplicate rejection (Properties 7 & 8)
    - **Property 7: Appeal submission creates a pending record with unique ID**
    - **Property 8: Duplicate appeals are rejected**
    - **Validates: Requirements 3.1, 3.4**

  - [ ]* 5.4 Write property test for appeal reason length enforcement (Property 9)
    - **Property 9: Appeal reason length is enforced**
    - **Validates: Requirements 3.2**

  - [ ]* 5.5 Write unit tests for `AppealsSystem`
    - Test appeal on non-rejected item (should fail)
    - Test duplicate detection
    - _Requirements: 3.1, 3.4_

- [ ] 6. Implement human review queue with locking semantics
  - [ ] 6.1 Implement queue fetch ordered by `enqueued_at` ascending and lock acquisition endpoint
    - Lock a `QueueItem` to a `reviewer_id`; reject concurrent lock attempts with 423
    - _Requirements: 4.1, 4.4_

  - [ ] 6.2 Implement stale lock release background job (30-minute timeout)
    - Release lock and log timeout event for items locked > 30 minutes
    - _Requirements: 4.5_

  - [ ]* 6.3 Write property test for queue ordering (Property 10)
    - **Property 10: Queue ordering is oldest-first**
    - **Validates: Requirements 4.1**

  - [ ]* 6.4 Write property test for locking semantics and stale lock release (Properties 11 & 12)
    - **Property 11: Locking prevents concurrent edits**
    - **Property 12: Stale locks are released after 30 minutes**
    - **Validates: Requirements 4.4, 4.5**

- [ ] 7. Implement decision submission endpoint
  - Accept `approved`/`rejected` decision with `reviewer_id`, optional note (≤ 500 chars), and timestamp
  - Record `ModerationDecision` with `source="human"`
  - Release queue lock on submission
  - _Requirements: 4.3, 4.6_

- [ ] 8. Implement Metrics Service
  - [ ] 8.1 Implement latency recording for every `ContentItem` from submission to final decision
    - _Requirements: 5.1_

  - [ ] 8.2 Implement rolling 24-hour automated decision rate calculation
    - _Requirements: 5.2_

  - [ ] 8.3 Implement alert emission when average classifier latency exceeds 3 seconds over a 5-minute window
    - _Requirements: 5.3_

  - [ ] 8.4 Implement `GET /health` endpoint returning `status`, `queue_depth`, and `avg_latency_ms`
    - Must respond within 500ms
    - _Requirements: 5.4_

  - [ ]* 8.5 Write property test for health endpoint latency (Property 15)
    - **Property 15: Health endpoint responds within 500ms**
    - **Validates: Requirements 5.4**

- [ ] 9. Implement Reporting API
  - Implement `GET /reports` aggregating decisions by category, type, and date
  - Implement `GET /reports/reviewers` with per-reviewer total decisions and average decision time
  - Ensure aggregated data updates within 5 minutes of a new decision
  - _Requirements: 6.1, 6.4, 6.5_

- [ ] 10. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement `ModerationPanel.tsx` — Queue and content detail views
  - [ ] 11.1 Implement `ReviewQueue` sub-component
    - Display queue ordered oldest-first with queue depth and pending appeal count
    - Support filtering by violation category, decision status, and date range
    - Show empty-state message when queue is empty
    - Render within 1 second of navigation
    - _Requirements: 4.1, 7.1, 7.2, 7.3, 7.4_

  - [ ] 11.2 Implement `ContentDetail` sub-component
    - Display `ContentItem`, AI classification, confidence score, and appeal reason
    - _Requirements: 4.2_

  - [ ]* 11.3 Write property test for queue filter subset invariant (Property 17)
    - **Property 17: Queue filter reduces or preserves result set**
    - **Validates: Requirements 7.4**

- [ ] 12. Implement `DecisionForm` sub-component with validation
  - [ ] 12.1 Implement approve/reject form with optional note field (≤ 500 chars) and keyboard navigation
    - Inline validation error on missing required fields — no request dispatched
    - Treat whitespace-only notes as empty
    - _Requirements: 4.6, 7.5, 7.6_

  - [ ]* 12.2 Write property test for note validation (Properties 13 & 14)
    - **Property 13: Decision note length is enforced**
    - **Property 14: Whitespace-only notes are treated as empty**
    - **Validates: Requirements 4.6**

  - [ ]* 12.3 Write property test for validation blocking submission (Property 18)
    - **Property 18: Validation blocks submission on missing required fields**
    - **Validates: Requirements 7.6**

  - [ ]* 12.4 Write unit tests for `DecisionForm` validation rendering
    - Test missing required field renders inline error
    - _Requirements: 7.6_

- [ ] 13. Implement `Dashboard` and `ExportButton` sub-components
  - [ ] 13.1 Implement `Dashboard` with summary stats (total reviewed, breakdown by decision and category) and date-range selector
    - _Requirements: 6.2_

  - [ ] 13.2 Implement `ExportButton` triggering CSV generation from filtered records within 10 seconds
    - _Requirements: 6.3_

  - [ ]* 13.3 Write property test for CSV export completeness (Property 16)
    - **Property 16: CSV export contains all filtered records**
    - **Validates: Requirements 6.3**

- [ ] 14. Wire all components together
  - [ ] 14.1 Connect `ModerationPanel` to backend REST endpoints (queue fetch, lock, decision submit, reports, export)
    - _Requirements: 4.1, 4.2, 4.3, 6.1, 6.3_

  - [ ] 14.2 Wire `AutomatedReviewer` → `AIClassifier` → `MetricsService` → `ReportingAPI` in the FastAPI app
    - _Requirements: 1.1, 5.1, 6.1_

  - [ ] 14.3 Wire `AppealsSystem` → human review queue → `ModerationPanel`
    - _Requirements: 3.3, 4.2_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Python property tests use `pytest` + `hypothesis`; TypeScript property tests use `vitest` + `fast-check`
- Each property test must include the tag comment: `# Feature: advanced-content-moderation, Property <N>: <text>`
- All backend errors return structured JSON: `{ "error": "<code>", "message": "<human-readable>" }`
