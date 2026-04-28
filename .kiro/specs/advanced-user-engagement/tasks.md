# Implementation Plan: Advanced User Engagement

## Overview

Implement the advanced user engagement system across the Python ML model API backend (`engagement_engine.py`, `gamification.py`) and the React/TypeScript frontend (`EngagementPanel.tsx`, `personalization.ts`). Tasks follow an incremental approach: data models first, then backend services, then frontend, then wiring.

## Tasks

- [ ] 1. Define data models and shared types
  - Add `UserProfile`, `BadgeRecord`, `JourneyState`, `JourneyDefinition`, `MilestoneDefinition`, `RewardDefinition`, `RewardRecord`, and `EngagementMetricSnapshot` dataclasses to `ml-model-api/gamification.py` and `ml-model-api/engagement_engine.py`
  - Add `Recommendation` and `ContentItem` TypeScript interfaces to `frontend/utils/personalization.ts`
  - _Requirements: 1.1, 3.1, 4.1, 5.1_

- [ ] 2. Implement Gamification_Service core (gamification.py)
  - [ ] 2.1 Implement `POST /gamification/action` — award points, update `UserProfile`, detect level-up, emit level-up event
    - Must update profile within 1 second; emit level-up event to Engagement_Engine on threshold crossing
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 2.2 Write property test for action awards correct points (Property 2)
    - **Property 2: Action awards correct points**
    - **Validates: Requirements 1.2**

  - [ ]* 2.3 Write property test for level advances when threshold crossed (Property 3)
    - **Property 3: Level advances when threshold crossed**
    - **Validates: Requirements 1.3**

  - [ ] 2.4 Implement badge grant logic — `POST /gamification/action` badge path and idempotent duplicate handling
    - Ignore duplicate badge grants; record timestamp on first grant only
    - _Requirements: 1.4, 1.5_

  - [ ]* 2.5 Write property test for badge grant idempotency (Property 4)
    - **Property 4: Badge grant is idempotent**
    - **Validates: Requirements 1.4, 1.5**

  - [ ]* 2.6 Write property test for User_Profile structural invariant (Property 1)
    - **Property 1: User Profile structural invariant**
    - **Validates: Requirements 1.1**

- [ ] 3. Implement Reward System (gamification.py)
  - [ ] 3.1 Implement reward catalog storage and `POST /gamification/reward/trigger` — evaluate trigger condition, grant reward, update `UserProfile`
    - Handle `feature_unlock` type by appending to `unlocked_features`; prevent re-grant of non-repeatable rewards
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [ ]* 3.2 Write property test for reward grant recorded with required fields and feature unlock propagation (Property 14)
    - **Property 14: Reward grant is recorded with all required fields and feature unlocks propagate**
    - **Validates: Requirements 5.2, 5.3, 5.4**

  - [ ]* 3.3 Write property test for non-repeatable reward grant idempotency (Property 15)
    - **Property 15: Non-repeatable reward grant is idempotent**
    - **Validates: Requirements 5.6**

- [ ] 4. Implement Leaderboard (gamification.py)
  - [ ] 4.1 Implement `GET /gamification/leaderboard` — rank users by Engagement_Score, support `global|friends|period` scopes, exclude private users, update within 10 seconds of score change
    - _Requirements: 6.1, 6.2, 6.6_

  - [ ] 4.2 Implement `GET /gamification/profile/{user_id}` — return full `UserProfile`
    - _Requirements: 1.1, 5.4_

  - [ ]* 4.3 Write property test for leaderboard sorted and excludes private users (Property 16)
    - **Property 16: Leaderboard is sorted by Engagement_Score descending and excludes private users**
    - **Validates: Requirements 6.1, 6.6**

  - [ ]* 4.4 Write property test for leaderboard reflects updated scores (Property 17)
    - **Property 17: Leaderboard reflects updated scores**
    - **Validates: Requirements 6.2**

- [ ] 5. Checkpoint — Ensure all gamification.py tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement Personalization Engine (engagement_engine.py)
  - [ ] 6.1 Implement `POST /engine/recommendations` — compute ranked recommendation list from interaction history and preferences, recompute within 5 seconds of history update
    - _Requirements: 2.1, 2.2_

  - [ ] 6.2 Implement `POST /engine/interactions` — record interaction events (view, dismiss, click) and trigger recommendation recomputation
    - _Requirements: 2.2, 2.4_

  - [ ] 6.3 Implement `POST /engine/preferences` — accept category interests and opt-outs, incorporate into subsequent recommendation computations
    - _Requirements: 2.5_

  - [ ]* 6.4 Write property test for recommendation list ordered by score descending (Property 5)
    - **Property 5: Recommendation list is ordered by score descending**
    - **Validates: Requirements 2.1, 2.3**

  - [ ]* 6.5 Write property test for opt-out preferences filter recommendations (Property 7)
    - **Property 7: Opt-out preferences filter recommendations**
    - **Validates: Requirements 2.5**

- [ ] 7. Implement Journey Tracking (engagement_engine.py)
  - [ ] 7.1 Implement `POST /engine/journey/milestone` — record milestone completion, detect journey completion, notify Gamification_Service to award associated reward, ignore duplicates
    - _Requirements: 3.2, 3.4, 3.5_

  - [ ] 7.2 Implement `GET /engine/journey/{user_id}` — return journey state with `completed_milestones`, `next_milestone`, and `completion_pct`
    - _Requirements: 3.3_

  - [ ] 7.3 Implement achievement event generation on badge grant or journey completion — include `display_name`, `achievement_type`, `timestamp`
    - _Requirements: 6.4_

  - [ ]* 7.4 Write property test for journey state API consistency (Property 8)
    - **Property 8: Journey state API returns consistent completion data**
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [ ]* 7.5 Write property test for milestone completion idempotency (Property 9)
    - **Property 9: Milestone completion is idempotent**
    - **Validates: Requirements 3.5**

  - [ ]* 7.6 Write property test for journey completion triggers reward and records timestamp (Property 10)
    - **Property 10: Journey completion triggers reward and records timestamp**
    - **Validates: Requirements 3.4**

  - [ ]* 7.7 Write property test for achievement event contains required fields (Property 18)
    - **Property 18: Achievement event contains required fields**
    - **Validates: Requirements 6.4**

- [ ] 8. Implement Engagement Analytics (engagement_engine.py)
  - [ ] 8.1 Implement scheduled metric aggregation job — compute DAU, avg Engagement_Score, points per day, badge grant rate at ≤1-hour intervals; persist `EngagementMetricSnapshot` with 90-day retention
    - _Requirements: 4.1, 4.5_

  - [ ] 8.2 Implement `GET /engine/analytics` — validate date range, return metrics within 2 seconds, return HTTP 400 on invalid/reversed range
    - _Requirements: 4.2, 4.3, 4.4_

  - [ ]* 8.3 Write property test for analytics query returns all required metric fields (Property 11)
    - **Property 11: Analytics query returns all required metric fields**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 8.4 Write property test for invalid time range returns HTTP 400 (Property 12)
    - **Property 12: Invalid time range returns HTTP 400**
    - **Validates: Requirements 4.4**

  - [ ]* 8.5 Write property test for metric history retained for 90 days (Property 13)
    - **Property 13: Metric history retained for 90 days**
    - **Validates: Requirements 4.5**

- [ ] 9. Implement Performance Monitoring (engagement_engine.py)
  - [ ] 9.1 Add per-request latency and error rate instrumentation middleware to all Engagement_Engine endpoints
    - _Requirements: 7.1_

  - [ ] 9.2 Implement `GET /engine/health` — return `status`, `p95_latency_ms`, and `error_rate_pct` for the preceding 5-minute window; emit performance and error rate alert events when thresholds exceeded
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ]* 9.3 Write property test for every request produces a metric record (Property 19)
    - **Property 19: Every request produces a metric record**
    - **Validates: Requirements 7.1**

  - [ ]* 9.4 Write property test for health check response contains all required fields (Property 20)
    - **Property 20: Health check response contains all required fields**
    - **Validates: Requirements 7.2**

  - [ ]* 9.5 Write property test for performance alerts emitted when thresholds exceeded (Property 21)
    - **Property 21: Performance alerts emitted when thresholds exceeded**
    - **Validates: Requirements 7.3, 7.4**

- [ ] 10. Checkpoint — Ensure all engagement_engine.py tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement personalization.ts utility
  - [ ] 11.1 Implement `rankContent(items, recommendations)` — sort `ContentItem[]` by descending recommendation score, preserving items not in the recommendation list at the end
    - _Requirements: 2.3_

  - [ ] 11.2 Implement `reportDismissal(userId, contentId)` — POST dismiss interaction to `POST /engine/interactions` and remove the item from the local ranked list
    - _Requirements: 2.4_

  - [ ]* 11.3 Write property test for recommendation list ordering preserved by rankContent (Property 5 — frontend)
    - **Property 5: Recommendation list is ordered by score descending**
    - **Validates: Requirements 2.3**

  - [ ]* 11.4 Write property test for dismissed items excluded from displayed list (Property 6)
    - **Property 6: Dismissed items are excluded from displayed list**
    - **Validates: Requirements 2.4**

- [ ] 12. Implement EngagementPanel.tsx
  - [ ] 12.1 Implement data fetching on mount — fetch profile, journey state, leaderboard, analytics (operator only), and health status; wire to `personalization.ts` for ranked content display
    - Fall back to operator-defined default content when recommendations list is empty
    - _Requirements: 1.6, 2.6, 3.6, 4.6, 6.3, 7.5_

  - [ ] 12.2 Implement WebSocket subscription for real-time events — handle level-up notification (≤500ms display), reward grant notification (≤500ms display), and achievement share prompt; implement exponential-backoff reconnect with polling fallback
    - _Requirements: 1.7, 5.5, 6.5_

  - [ ] 12.3 Implement operator analytics summary view — render DAU, avg Engagement_Score, points per day, badge grant rate from analytics API response
    - _Requirements: 4.6_

  - [ ] 12.4 Implement system health indicator — display status from health endpoint, refresh every ≤60 seconds; show degraded indicator and log connectivity failure when endpoint is unreachable
    - _Requirements: 7.5, 7.6_

  - [ ]* 12.5 Write unit tests for EngagementPanel rendering
    - Test profile display, journey progress, leaderboard, analytics summary, health indicator, level-up notification, reward notification, and degraded health state with mock data
    - _Requirements: 1.6, 1.7, 3.6, 4.6, 5.5, 6.3, 7.5, 7.6_

- [ ] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests use **Hypothesis** (Python backend) and **fast-check** (TypeScript frontend), each running a minimum of 100 iterations
- Each property test must include a comment tag: `# Feature: advanced-user-engagement, Property N: <property_text>`
- All requirements are referenced by their clause numbers for traceability
