# Implementation Plan: Advanced Analytics Platform

## Overview

Incremental implementation of the analytics platform in Python, deployed on Kubernetes. Each task builds on the previous, wiring all components together at the end.

## Tasks

- [ ] 1. Set up project structure, data models, and shared infrastructure
  - Create `analytics-platform/` directory layout with `tests/unit/` and `tests/property/` subdirectories
  - Implement all dataclasses and enums in `analytics-platform/models.py` (DataSourceConfig, JobStatus, LineageEntry, DeadLetterRecord, MetricSample, Alert, DatasetEntry, AccessEvent, AuthUser, AuthEvent, DashboardConfig, Dashboard, SourceType, SensitivityLabel, Role, JobState, ExportFormat)
  - Implement `analytics-platform/db.py` with SQLAlchemy async engine targeting PostgreSQL + TimescaleDB; define analytics schema tables (jobs, lineage, dlq, metrics, datasets, access_events, auth_events, dashboards)
  - Implement `analytics-platform/event_bus.py` with Kafka producer/consumer wrappers using `aiokafka`
  - Create `k8s/analytics/namespace.yaml`, `k8s/analytics/configmap.yaml`, `k8s/analytics/secrets.yaml`, and `k8s/analytics/rbac.yaml`
  - _Requirements: 1.1, 1.4, 2.2, 5.1, 7.2_

- [ ] 2. Implement Pipeline Engine
  - [ ] 2.1 Implement `analytics-platform/pipeline_engine.py` with `PipelineEngine` class
    - Implement `validate_source()` for connectivity and schema checks for all four SourceType values
    - Implement `ingest()` with exponential backoff retry (base 1s, max 60s, 3 attempts), DLQ routing for failed records, lineage entry creation, and job metrics emission
    - Implement `get_job_status()` and `list_jobs()` backed by the `db` module
    - Route `mode="stream"` to Kafka topic and `mode="batch"` to Airflow DAG trigger
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.2 Write property tests for Pipeline Engine
    - **Property 1: Source type acceptance** — Validates: Requirements 1.1
    - **Property 2: Validation before extraction** — Validates: Requirements 1.2
    - **Property 3: Retry with exponential backoff** — Validates: Requirements 1.3
    - **Property 4: Mode routing** — Validates: Requirements 1.4
    - **Property 5: Failed records routed to DLQ with failure metric** — Validates: Requirements 1.5
    - **Property 6: Lineage entry completeness** — Validates: Requirements 1.6
    - **Property 7: Job completion metrics completeness** — Validates: Requirements 1.7
    - Write to `analytics-platform/tests/property/test_pipeline_properties.py`

  - [ ]* 2.3 Write unit tests for Pipeline Engine
    - Test each SourceType (REST_API, MESSAGE_QUEUE, RDBMS, OBJECT_STORAGE) connects and returns records
    - Test schema incompatibility returns structured error without beginning ingestion
    - Write to `analytics-platform/tests/unit/test_pipeline_engine.py`
    - _Requirements: 1.1, 1.2_

- [ ] 3. Implement Stream Processor
  - [ ] 3.1 Implement `analytics-platform/stream_processor.py` with `StreamProcessor` class
    - Wrap PyFlink job consuming from Kafka; support window sizes 60s, 300s, 900s, 3600s
    - Emit aggregation results to PostgreSQL within 5 seconds of record receipt
    - Publish alert events to Alert Manager when metric crosses configured threshold
    - Emit lag alert when consumer lag exceeds 30 seconds
    - Checkpoint state to S3 at ≤60-second intervals
    - Implement `start()`, `stop()`, `get_lag_seconds()`, `get_throughput_rps()`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 3.2 Write property tests for Stream Processor
    - **Property 8: Stream aggregation result emission** — Validates: Requirements 2.1
    - **Property 9: Window size configuration acceptance** — Validates: Requirements 2.2
    - **Property 10: Threshold breach triggers alert** — Validates: Requirements 2.3
    - **Property 11: Lag alert on sustained stream lag** — Validates: Requirements 2.5
    - **Property 12: Checkpoint state survival** — Validates: Requirements 2.6
    - Write to `analytics-platform/tests/property/test_stream_properties.py`

  - [ ]* 3.3 Write unit tests for Stream Processor
    - Test throughput ≥10,000 rps under nominal load
    - Test each supported window size is accepted
    - Write to `analytics-platform/tests/unit/test_stream_processor.py`
    - _Requirements: 2.2, 2.4_

- [ ] 4. Checkpoint — Ensure all pipeline and stream tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Batch Processor
  - [ ] 5.1 Implement `analytics-platform/batch_processor.py` with `BatchProcessor` class
    - Wrap Airflow DAG trigger via Airflow REST API; implement `submit_job()`, `get_job_status()`, `cancel_job()`
    - Persist job state to `db` module
    - _Requirements: 1.4_

  - [ ]* 5.2 Write unit tests for Batch Processor
    - Test job submission returns a job_id, status polling returns valid JobStatus, cancel returns bool
    - Write to `analytics-platform/tests/unit/test_batch_processor.py`
    - _Requirements: 1.4_

- [ ] 6. Implement Metrics Collector and Alert Manager
  - [ ] 6.1 Implement `analytics-platform/metrics_collector.py` with `MetricsCollector` class
    - Scrape all platform components at ≤15-second intervals; store raw samples in TimescaleDB hypertable
    - Configure TimescaleDB continuous aggregate for hourly downsampling; set retention policy (raw 30 days, aggregate 1 year)
    - Expose Prometheus-compatible `/metrics` endpoint via `get_metrics_response()`
    - Mark component health as degraded and notify Alert Manager when a component is unreachable within 30 seconds
    - _Requirements: 4.1, 4.3, 4.5, 4.6_

  - [ ] 6.2 Implement `analytics-platform/alert_manager.py` with `AlertManager` class
    - Evaluate metric thresholds; deduplicate alerts within 60-second window
    - Dispatch notifications via email, webhook, and PagerDuty; retry once on delivery failure; log failures
    - Implement `evaluate()`, `dispatch()`, `register_webhook()`
    - _Requirements: 4.2, 4.7_

  - [ ]* 6.3 Write property tests for Metrics Collector and Alert Manager
    - **Property 16: Metrics scrape completeness** — Validates: Requirements 4.1
    - **Property 17: Threshold alert dispatch** — Validates: Requirements 4.2
    - **Property 18: Metric retention policy configuration** — Validates: Requirements 4.3
    - **Property 19: Unreachable component marked degraded** — Validates: Requirements 4.5
    - **Property 20: Alert delivery to all channel types** — Validates: Requirements 4.7
    - Write to `analytics-platform/tests/property/test_metrics_properties.py`

  - [ ]* 6.4 Write unit tests for Metrics Collector and Alert Manager
    - Test `/metrics` endpoint returns response parseable by Prometheus client library
    - Test alert dispatch attempts all configured channels even when one fails
    - Write to `analytics-platform/tests/unit/test_metrics_collector.py` and `test_alert_manager.py`
    - _Requirements: 4.1, 4.6, 4.7_

- [ ] 7. Implement Governance Manager
  - [ ] 7.1 Implement `analytics-platform/governance_manager.py` with `GovernanceManager` class
    - Implement `classify_dataset()` enforcing SensitivityLabel enum values only
    - Implement `check_access()` with role-to-sensitivity-label permission matrix
    - Implement `log_access()` writing immutable AccessEvent rows to audit log table
    - Implement `enforce_retention()` purging expired records and writing purge events to audit log
    - Implement `get_lineage()` querying lineage entries by record_id
    - Implement `search_catalog()` returning DatasetEntry list with schema, owner, sensitivity, retention_days
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 7.2 Write property tests for Governance Manager
    - **Property 21: Dataset sensitivity label validity** — Validates: Requirements 5.1
    - **Property 22: Role-based dataset access enforcement** — Validates: Requirements 5.2
    - **Property 23: Access event audit log completeness** — Validates: Requirements 5.3
    - **Property 24: Retention enforcement and purge audit** — Validates: Requirements 5.4, 5.5
    - **Property 25: Lineage query round-trip** — Validates: Requirements 5.6
    - **Property 26: Data Catalog search completeness** — Validates: Requirements 5.7
    - Write to `analytics-platform/tests/property/test_governance_properties.py`

  - [ ]* 7.3 Write unit tests for Governance Manager
    - Test each sensitivity label is accepted; test unlabeled dataset registration is rejected
    - Test retention purge records purge event in audit log
    - Write to `analytics-platform/tests/unit/test_governance_manager.py`
    - _Requirements: 5.1, 5.5_

- [ ] 8. Implement Auth Service
  - [ ] 8.1 Implement `analytics-platform/auth_service.py` with `AuthService` class
    - Validate JWT tokens via Keycloak OIDC JWKS endpoint; return AuthUser on success
    - Enforce RBAC roles (VIEWER, ANALYST, ENGINEER, ADMINISTRATOR) via `check_role()`
    - Return HTTP 401 with `WWW-Authenticate` header for expired/invalid tokens
    - Track failed auth attempts per IP in Redis; block IP after 100 failures in 1 hour via `block_ip()` / `is_blocked()`; log block events to Governance Manager audit log
    - Record all auth decisions via `record_auth_event()` to Governance Manager audit log
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

  - [ ]* 8.2 Write property tests for Auth Service
    - **Property 31: Unauthenticated requests denied** — Validates: Requirements 7.1
    - **Property 32: RBAC role enforcement** — Validates: Requirements 7.2
    - **Property 33: Expired token returns 401 with WWW-Authenticate** — Validates: Requirements 7.3
    - **Property 34: IP blocking after failed auth attempts** — Validates: Requirements 7.5
    - **Property 35: Auth decision audit log completeness** — Validates: Requirements 7.6
    - Write to `analytics-platform/tests/property/test_auth_properties.py`

  - [ ]* 8.3 Write unit tests for Auth Service
    - Test expired token returns HTTP 401 with `WWW-Authenticate` header
    - Test IP blocking triggers after exactly 100 failed attempts
    - Write to `analytics-platform/tests/unit/test_auth_service.py`
    - _Requirements: 7.3, 7.5_

- [ ] 9. Implement Visualization Service
  - [ ] 9.1 Implement `analytics-platform/visualization_service.py` with `VisualizationService` class
    - Manage Grafana dashboards via Grafana HTTP API; implement `create_dashboard()`, `get_dashboard()`, `apply_filter()`, `export()`, `get_embed_url()`
    - Apply tenant branding (color scheme, logo) via Grafana Organizations for each tenant
    - Enforce Auth Service access controls on the embeddable iframe endpoint
    - Support auto-refresh intervals: 10s, 30s, 60s, 300s
    - Support export formats: CSV, JSON
    - Create pre-built system health dashboard displaying all Metrics Collector metrics
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.4_

  - [ ]* 9.2 Write property tests for Visualization Service
    - **Property 13: Dashboard export round-trip** — Validates: Requirements 3.5
    - **Property 14: Tenant branding applied to all tenant dashboards** — Validates: Requirements 3.6
    - **Property 15: Embed endpoint enforces same auth as native UI** — Validates: Requirements 3.7
    - Write to `analytics-platform/tests/property/test_visualization_properties.py`

  - [ ]* 9.3 Write unit tests for Visualization Service
    - Test each chart type (time-series, bar, pie, heatmap, tabular) renders without error
    - Test all four auto-refresh intervals are accepted
    - Test system health dashboard exists and contains all required metric panels
    - Write to `analytics-platform/tests/unit/test_visualization_service.py`
    - _Requirements: 3.1, 3.3, 4.4_

- [ ] 10. Checkpoint — Ensure all governance, auth, and visualization tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement API Gateway
  - [ ] 11.1 Implement `analytics-platform/api_gateway.py` as a FastAPI application
    - Mount all routes under `/v1` prefix; wire Auth Service as a FastAPI dependency for all routes
    - Implement `POST /v1/ingest` (submit ingestion job), `GET /v1/jobs/{job_id}` (poll status), `GET /v1/dashboards/{id}`, `POST /v1/webhooks` (register webhook)
    - Serve auto-generated OpenAPI 3.0 spec at `/GET /v1/openapi.json`
    - Integrate `slowapi` + Redis for per-API-key rate limiting at 1,000 req/min; return HTTP 429 with `Retry-After` on breach
    - Return HTTP 400 with structured JSON error body for malformed requests
    - Respond within 500ms for synchronous operations; return `job_id` immediately for long-running queries
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 11.2 Write property tests for API Gateway
    - **Property 27: Malformed request returns structured 400** — Validates: Requirements 6.3
    - **Property 28: Rate limit enforcement returns 429 with Retry-After** — Validates: Requirements 6.3, 6.4
    - **Property 29: Async job submission round-trip** — Validates: Requirements 6.6
    - **Property 30: Webhook delivery on job completion** — Validates: Requirements 6.7
    - Write to `analytics-platform/tests/property/test_api_properties.py`

  - [ ]* 11.3 Write unit tests for API Gateway
    - Test `/v1/openapi.json` returns a valid OpenAPI 3.0 document
    - Test rate limit returns HTTP 429 with `Retry-After` header
    - Test malformed request returns HTTP 400 with JSON body containing `error` field
    - Write to `analytics-platform/tests/unit/test_api_gateway.py`
    - _Requirements: 6.3, 6.4, 6.5_

- [ ] 12. Implement tenant isolation via PostgreSQL Row-Level Security
  - Add RLS policies to all analytics schema tables in `analytics-platform/db.py` keyed on `tenant_id`
  - Update `AuthService` to set the `app.current_tenant` session variable on each database connection
  - Verify that queries from one tenant cannot return rows belonging to another tenant
  - _Requirements: 7.7_

  - [ ]* 12.1 Write property test for tenant data isolation
    - **Property 36: Tenant data isolation** — Validates: Requirements 7.7
    - Write to `analytics-platform/tests/property/test_auth_properties.py`

- [ ] 13. Extend `ml-model-api/analytics_platform.py`
  - Add analytics ingestion endpoint that delegates to `PipelineEngine.ingest()` and returns job_id
  - Wire `AuthService` token validation as middleware
  - Emit `analytics_records_ingested_total` and `analytics_api_request_duration_seconds` Prometheus metrics
  - _Requirements: 1.1, 6.1, 7.1_

- [ ] 14. Create Kubernetes manifests
  - Write `k8s/analytics/pipeline-engine.yaml`, `stream-processor.yaml`, `batch-processor.yaml`, `metrics-collector.yaml`, `visualization-service.yaml`, `governance-manager.yaml`, `api-gateway.yaml`, `auth-service.yaml`, `alert-manager.yaml`
  - Each manifest includes Deployment, Service, and HorizontalPodAutoscaler; all containers mount secrets from `k8s/analytics/secrets.yaml`
  - Configure liveness and readiness probes for each component
  - _Requirements: 4.1, 4.5_

- [ ] 15. Create operational scripts
  - Write `scripts/analytics/run_pipeline.py` — CLI to trigger `PipelineEngine.ingest()` and tail job status
  - Write `scripts/analytics/run_batch.py` — CLI to submit and monitor a `BatchProcessor` job
  - Write `scripts/analytics/export_dashboard.py` — CLI to export a dashboard to CSV or JSON via `VisualizationService.export()`
  - Write `scripts/analytics/audit_report.py` — CLI to query `GovernanceManager` audit log and print a report
  - _Requirements: 1.1, 1.4, 3.5, 5.3_

- [ ] 16. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` and include the comment tag `# Feature: advanced-analytics-platform, Property N: <property_text>`
- Checkpoints ensure incremental validation before moving to the next phase
