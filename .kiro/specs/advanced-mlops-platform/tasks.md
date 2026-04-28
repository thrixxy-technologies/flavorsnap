# Implementation Plan: Advanced MLOps Platform

## Overview

Implement the Advanced MLOps Platform as a set of Python modules under `mlops/`, a FastAPI gateway, Kubernetes manifests under `k8s/mlops/`, CLI scripts under `scripts/mlops/`, and a thin integration shim at `ml-model-api/mlops_platform.py`. All components use PostgreSQL for metadata, Redis for queuing and online feature serving, and S3-compatible object storage for artifacts.

## Tasks

- [ ] 1. Set up project structure, shared data models, and database layer
  - Create `mlops/` package with `__init__.py`
  - Create `mlops/models.py` with all dataclasses and enums (`LifecycleStage`, `RunStatus`, `JobStatus`, `ModelVersion`, `StageTransition`, `TrainingJobSpec`, `DeploymentSpec`, `Deployment`, `ABTestConfig`, `FeatureSpec`, `ExperimentRun`, etc.)
  - Create `mlops/db.py` with SQLAlchemy async engine, session factory, and schema definitions for all tables (model_versions, stage_transitions, training_jobs, deployments, ab_tests, feature_definitions, feature_lineage, experiment_runs, run_params, run_metrics, run_artifacts, run_audit_log)
  - Create `mlops/tests/` directory with `unit/` and `property/` subdirectories and `conftest.py` with shared fixtures (in-memory SQLite for unit tests, mock Redis, mock S3)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 5.1, 6.1, 7.1_

- [ ] 2. Implement Model Registry
  - [ ] 2.1 Implement `mlops/model_registry.py` with `ModelRegistry` class
    - `register()`: insert model version row, assign monotonically increasing version per name, store artifact URI, author, description, tags, metadata; initial stage = `DEVELOPMENT`
    - `get()`: fetch by name+version; raise `ModelNotFoundError` (→ HTTP 404) if missing
    - `query()`: filter by name, version, stage, author, date range, tags
    - `transition_stage()`: validate target is a valid `LifecycleStage`; insert `stage_transitions` row with timestamp, user, reason
    - `tag()`: upsert key-value tags on a model version
    - `get_transitions()`: return ordered transition history for a model version
    - Expose Prometheus counter `mlops_model_versions_total`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [ ]* 2.2 Write property tests for Model Registry (`mlops/tests/property/test_registry_properties.py`)
    - **Property 1: Model version record completeness** — Validates: Requirements 1.1
    - **Property 2: Version number monotonicity** — Validates: Requirements 1.2
    - **Property 3: Lifecycle stage validity** — Validates: Requirements 1.3
    - **Property 4: Stage transition record completeness** — Validates: Requirements 1.4
    - **Property 5: Archived model retention** — Validates: Requirements 1.5
    - **Property 6: Model query round-trip** — Validates: Requirements 1.6, 1.8
    - **Property 7: Missing model returns 404** — Validates: Requirements 1.7

  - [ ]* 2.3 Write unit tests for Model Registry (`mlops/tests/unit/test_model_registry.py`)
    - Each lifecycle stage is accepted; invalid stage names are rejected with HTTP 422
    - Tag upsert and query-by-tag round-trip
    - _Requirements: 1.3, 1.8_

- [ ] 3. Implement Training Orchestrator
  - [ ] 3.1 Implement `mlops/training_orchestrator.py` with `TrainingOrchestrator` class
    - `submit()`: validate spec, generate unique job ID (UUID), persist `TrainingJobStatus` row with `PENDING` status, enqueue Celery task, return job ID within 5 seconds
    - Celery task: create Kubernetes Job manifest with resource limits from `ComputeSpec`, submit via K8s API, poll status every ≤60 seconds, on success call `ModelRegistry.register()` then set status `COMPLETED`, on failure capture exit code + last 1000 log lines + set status `FAILED`
    - `cancel()`: call K8s delete Job API; set status `CANCELLED` within 30 seconds
    - `get_status()`: return current `TrainingJobStatus` from DB
    - `schedule()`: register Celery Beat periodic task with provided cron expression; log trigger time and schedule on each trigger
    - `list_jobs()`: query jobs with optional filters
    - Retry policy: exponential backoff `delay(n) = min(30 * 2^(n-1), 300)` seconds, up to `spec.max_retries`
    - Expose Prometheus counter `mlops_training_jobs_total` and histogram `mlops_training_job_duration_seconds`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

  - [ ]* 3.2 Write property tests for Training Orchestrator (`mlops/tests/property/test_training_properties.py`)
    - **Property 8: Training job ID uniqueness** — Validates: Requirements 2.2
    - **Property 9: Successful training auto-registers model** — Validates: Requirements 2.3
    - **Property 10: Failed training job record completeness** — Validates: Requirements 2.4
    - **Property 11: Training retry exponential backoff** — Validates: Requirements 2.7
    - **Property 12: Training job cancellation terminates job** — Validates: Requirements 2.9

  - [ ]* 3.3 Write unit tests for Training Orchestrator (`mlops/tests/unit/test_training_orchestrator.py`)
    - Job submission returns ID within 5 seconds (mock K8s)
    - Scheduled job logs trigger time and schedule name
    - Cancellation of non-running job returns HTTP 409
    - _Requirements: 2.2, 2.5, 2.6, 2.9_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Deployment Manager
  - [ ] 5.1 Implement `mlops/deployment_manager.py` with `DeploymentManager` class
    - `deploy()`: fetch model version from registry; run pre-deployment health check on target environment; if unhealthy abort with HTTP 503; create Kubernetes deployment for new version (inactive slot); start validation period timer; on timer expiry with errors < threshold promote (swap active slot); persist `Deployment` and `DeploymentManifest` rows
    - `rollback()`: swap traffic back to previous version within 60 seconds; persist rollback event with user, source version, target version
    - `get_health()`: query serving pod status; return `DeploymentHealth` with model version, status, uptime
    - `get_manifest()`: return stored `DeploymentManifest`
    - `list_deployments()`: query deployments with optional environment filter
    - Expose Prometheus counter `mlops_deployment_total`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [ ]* 5.2 Write property tests for Deployment Manager (`mlops/tests/property/test_deployment_properties.py`)
    - **Property 13: Pre-deployment health check gates deployment** — Validates: Requirements 3.2, 3.3
    - **Property 14: Blue-green traffic promotion requires validation period** — Validates: Requirements 3.4, 3.5
    - **Property 15: Rollback record completeness** — Validates: Requirements 3.7
    - **Property 16: Deployment manifest completeness** — Validates: Requirements 3.8
    - **Property 17: Health endpoint field completeness** — Validates: Requirements 3.9

  - [ ]* 5.3 Write unit tests for Deployment Manager (`mlops/tests/unit/test_deployment_manager.py`)
    - Blue-green deployment does not promote until validation period elapses
    - Rollback completes within 60 seconds (mock K8s)
    - Health endpoint returns valid JSON with `model_version`, `status`, `uptime`
    - _Requirements: 3.4, 3.5, 3.6, 3.9_

- [ ] 6. Implement Performance Monitor
  - [ ] 6.1 Implement `mlops/performance_monitor.py` with `PerformanceMonitor` class
    - `record_inference()`: persist `InferenceEvent`; update Prometheus histogram `mlops_inference_latency_ms` and counter `mlops_inference_errors_total`
    - `compute_drift()`: compute PSI between current prediction distribution and stored baseline; if score > threshold emit alert with model name, version, metric name, current value, threshold; persist `DriftResult`; minimum interval enforcement (1 minute)
    - `get_metrics()`: query time-series metric samples for model + metric + time range
    - `get_daily_report()`: aggregate daily p50/p95/p99 latency, throughput, error rate, drift score; persist `QualityReport`
    - `set_baseline()`: store baseline `PredictionDistribution` for a model version
    - Sustained error rate alert: background task checks every 30 seconds; if error rate > threshold for 5 continuous minutes emit critical alert
    - Alert delivery: send to all configured channels (webhook POST, SMTP email, PagerDuty Events API v2)
    - Expose Prometheus gauge `mlops_drift_score`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [ ]* 6.2 Write property tests for Performance Monitor (`mlops/tests/property/test_monitor_properties.py`)
    - **Property 18: Inference metric collection completeness** — Validates: Requirements 4.1
    - **Property 19: Drift alert field completeness** — Validates: Requirements 4.3
    - **Property 20: Metrics time-series round-trip** — Validates: Requirements 4.5
    - **Property 21: Sustained error rate triggers critical alert** — Validates: Requirements 4.6
    - **Property 22: Alert delivery to all configured channels** — Validates: Requirements 4.7

  - [ ]* 6.3 Write unit tests for Performance Monitor (`mlops/tests/unit/test_performance_monitor.py`)
    - Drift computation skipped when no baseline is set (no false alert)
    - Daily quality report contains all required summary fields
    - Metric storage buffer on unavailability (mock DB failure)
    - _Requirements: 4.2, 4.4, 4.8_

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement A/B Test Controller
  - [ ] 8.1 Implement `mlops/ab_test_controller.py` with `ABTestController` class
    - `start_test()`: validate no active test exists for endpoint (HTTP 409 if one does); persist `ABTest` row; configure traffic routing weights in Redis
    - `route_request()`: read routing weights from Redis; return champion or challenger model version according to configured split
    - `record_result()`: persist `InferenceResult` for the test; update per-model metric accumulators
    - `evaluate_safety()`: compare challenger vs champion error rate; if delta > `safety_error_threshold` call `stop_test()` automatically and set all traffic to champion
    - `get_status()`: return current `ABTestStatus` with traffic split, per-model metrics, and p-values
    - `stop_test()`: compute Welch's t-test (`scipy.stats.ttest_ind(equal_var=False)`) for each success metric; generate `ABTestReport` with recommendation; persist report; reset routing to 100% champion
    - Expose Prometheus gauge `mlops_ab_test_traffic_split`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 8.2 Write property tests for A/B Test Controller (`mlops/tests/property/test_ab_test_properties.py`)
    - **Property 23: A/B test traffic routing matches configured split** — Validates: Requirements 5.2
    - **Property 24: Per-request metric collection during A/B test** — Validates: Requirements 5.3
    - **Property 25: Statistical significance computed for all success metrics** — Validates: Requirements 5.4, 5.5
    - **Property 26: A/B test report completeness** — Validates: Requirements 5.6
    - **Property 27: Challenger safety halt** — Validates: Requirements 5.7
    - **Property 28: One active A/B test per endpoint** — Validates: Requirements 5.8

  - [ ]* 8.3 Write unit tests for A/B Test Controller (`mlops/tests/unit/test_ab_test_controller.py`)
    - A/B test report is generated when a test is stopped
    - Safety halt routes 100% traffic to champion and records halt event
    - Second test start on active endpoint returns HTTP 409
    - _Requirements: 5.6, 5.7, 5.8_

- [ ] 9. Implement Feature Store
  - [ ] 9.1 Implement `mlops/feature_store.py` with `FeatureStore` class wrapping Feast
    - `register_feature()`: validate name uniqueness within namespace and supported data type (`float`, `int`, `string`, `bool`, `list`); HTTP 409 on duplicate name+version; HTTP 422 on unsupported type; persist `FeatureDefinition` and `FeatureLineage` rows; register Feast `FeatureView`
    - `get_online_features()`: call Feast online store (Redis); target p99 latency < 50ms
    - `get_offline_features()`: call Feast offline store (PostgreSQL) with point-in-time join to prevent data leakage; return `pd.DataFrame`
    - `deprecate_feature()`: set `deprecated=True` and `deprecated_at` timestamp; schedule removal after 30 days; notify registered consumers
    - `get_lineage()`: return `FeatureLineage` for name+version
    - `search_catalog()`: return all `FeatureDefinition` records with usage statistics
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [ ]* 9.2 Write property tests for Feature Store (`mlops/tests/property/test_feature_store_properties.py`)
    - **Property 29: Feature registration validation** — Validates: Requirements 6.2, 6.3
    - **Property 30: Point-in-time correct batch retrieval** — Validates: Requirements 6.5
    - **Property 31: Feature lineage record completeness** — Validates: Requirements 6.6
    - **Property 32: Deprecated feature remains servable** — Validates: Requirements 6.7
    - **Property 33: Online/offline feature consistency** — Validates: Requirements 6.9

  - [ ]* 9.3 Write unit tests for Feature Store (`mlops/tests/unit/test_feature_store.py`)
    - Feature catalog returns all registered features with required fields
    - Online store fallback to offline store when Redis unavailable
    - Deprecation notification sent to registered consumers
    - _Requirements: 6.7, 6.8, 6.9_

- [ ] 10. Implement Experiment Tracker
  - [ ] 10.1 Implement `mlops/experiment_tracker.py` with `ExperimentTracker` class wrapping MLflow
    - `start_run()`: create MLflow run; persist `ExperimentRun` row with globally unique UUID run ID; return run ID
    - `log_param()`: call `mlflow.log_param()`; if key already exists overwrite value and insert audit log row recording the overwrite
    - `log_metric()`: call `mlflow.log_metric()` with step; append `(step, value)` to metric series in DB
    - `log_artifact()`: upload file to configured object storage; persist `ArtifactRef` with path and size
    - `end_run()`: set final status and `ended_at` timestamp
    - `delete_run()`: set `deleted=True` and `deleted_at` timestamp; retain for 30 days
    - `search_runs()`: query by experiment name, status, param values, metric ranges, tags, date range; exclude soft-deleted by default (include with `include_deleted=True`)
    - `compare_runs()`: return `RunComparison` with side-by-side params and last metric values
    - Expose Prometheus counter `mlops_experiment_runs_total`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

  - [ ]* 10.2 Write property tests for Experiment Tracker (`mlops/tests/property/test_experiment_properties.py`)
    - **Property 34: Experiment run record completeness** — Validates: Requirements 7.1, 7.4
    - **Property 35: Run ID global uniqueness** — Validates: Requirements 7.2
    - **Property 36: Multi-step metric logging round-trip** — Validates: Requirements 7.3
    - **Property 37: Artifact reference completeness** — Validates: Requirements 7.7
    - **Property 38: Soft-deleted run remains retrievable** — Validates: Requirements 7.8
    - **Property 39: Parameter overwrite idempotence** — Validates: Requirements 7.9
    - **Property 40: Run search round-trip** — Validates: Requirements 7.10, 7.6

  - [ ]* 10.3 Write unit tests for Experiment Tracker (`mlops/tests/unit/test_experiment_tracker.py`)
    - Soft-deleted runs excluded from default search, included with `include_deleted=True`
    - Artifact log failure returns HTTP 503 without failing the run
    - Run comparison returns side-by-side params and metrics for given run IDs
    - _Requirements: 7.5, 7.7, 7.8_

- [ ] 11. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement MLOps API Gateway
  - [ ] 12.1 Implement `mlops/api_gateway.py` as a FastAPI application
    - Mount routers for each component: `/registry`, `/training`, `/deployments`, `/monitor`, `/ab-tests`, `/features`, `/experiments`
    - Wire each router to the corresponding component class (dependency injection via FastAPI `Depends`)
    - Add `/metrics` endpoint returning Prometheus exposition format
    - Add `/health` endpoint returning service status
    - Structured JSON logging middleware (fields: `timestamp`, `component`, `level`, `event`, `context`)
    - _Requirements: 1.6, 1.7, 2.2, 3.9, 4.5, 5.5, 6.8, 7.5, 7.10_

  - [ ] 12.2 Implement `ml-model-api/mlops_platform.py` integration shim
    - Import and mount the MLOps API Gateway as a sub-application on the existing FastAPI `app` at prefix `/mlops`
    - Ensure existing `app.py` routes are unaffected
    - _Requirements: 3.1, 3.9_

- [ ] 13. Create Kubernetes manifests
  - [ ] 13.1 Create `k8s/mlops/namespace.yaml` and `k8s/mlops/rbac.yaml`
    - Namespace `mlops`; ServiceAccount, Role, RoleBinding for training job creation and pod log access
    - _Requirements: 2.1, 2.9_

  - [ ] 13.2 Create component deployment manifests in `k8s/mlops/`
    - `configmap.yaml`: non-secret configuration (DB URL, Redis URL, S3 bucket, drift interval, alert thresholds)
    - `secrets.yaml`: template for secret references (DB password, S3 credentials, PagerDuty key)
    - One `Deployment` + `Service` manifest per component: `model-registry.yaml`, `training-orchestrator.yaml`, `deployment-manager.yaml`, `performance-monitor.yaml`, `ab-test-controller.yaml`, `feature-store.yaml`, `experiment-tracker.yaml`, `api-gateway.yaml`
    - Each deployment sets resource requests/limits, liveness/readiness probes on `/health`, and mounts the configmap
    - _Requirements: 3.1, 3.2, 4.1_

- [ ] 14. Create CLI scripts
  - [ ] 14.1 Implement `scripts/mlops/register_model.py`
    - CLI (argparse) to call `POST /mlops/registry/models` with name, artifact URI, author, description, optional tags
    - _Requirements: 1.1_

  - [ ] 14.2 Implement `scripts/mlops/submit_training_job.py`
    - CLI to call `POST /mlops/training/jobs` with dataset URI, architecture, hyperparameters JSON, compute spec
    - _Requirements: 2.1, 2.2_

  - [ ] 14.3 Implement `scripts/mlops/deploy_model.py`
    - CLI to call `POST /mlops/deployments` with model name, version, environment, optional validation period
    - _Requirements: 3.1_

  - [ ] 14.4 Implement `scripts/mlops/run_ab_test.py`
    - CLI to call `POST /mlops/ab-tests` with champion/challenger model info, traffic split, success metrics, duration
    - _Requirements: 5.1_

  - [ ] 14.5 Implement `scripts/mlops/backfill_features.py`
    - CLI to trigger batch feature computation for a list of entity keys and a point-in-time timestamp
    - _Requirements: 6.5_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` and a comment tag `# Feature: advanced-mlops-platform, Property N: <text>`
- Unit tests and property tests are complementary — both are needed for full coverage
- All components emit structured JSON logs and expose `/metrics` (Prometheus) and `/health` endpoints
