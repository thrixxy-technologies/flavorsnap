# Implementation Plan: Advanced Data Pipeline

## Overview

Implement the advanced data pipeline system in Python, structured under `data-pipeline/` with Kubernetes manifests in `k8s/data-pipeline/` and helper scripts in `scripts/data-pipeline/`. The ML model API integration lives in `ml-model-api/data_pipeline.py`. Implementation follows the component order: data models → ETL engine → stream processor → batch processor → quality checker → governance manager → error handler → pipeline monitor → wiring + K8s deployment.

## Tasks

- [ ] 1. Set up project structure, data models, and shared types
  - Create `data-pipeline/` directory layout matching the test file layout in the design
  - Implement all dataclasses from the design: `PipelineConfig`, `DataSourceConfig`, `DataSinkConfig`, `Record`, `QualityRule`, `QualityTag`, `Checkpoint`, `LineageEvent`, `DeadLetterRecord`
  - Define all enums: `SourceType`, `SinkType`, `WriteMode`, `ExtractionStrategy`, `WindowType`, `RuleType`, `Severity`, `ErrorCategory`, `CircuitState`, `DataClassification`, `HealthStatus`
  - Create `data-pipeline/requirements.txt` with dependencies: `hypothesis`, `pytest`, `kafka-python`, `apache-airflow`, `great-expectations`, `openlineage-airflow`, `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `psycopg2-binary`, `boto3`, `requests`
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1_

- [ ] 2. Implement ETL Engine
  - [ ] 2.1 Implement `data-pipeline/etl_engine.py` with `ETLEngine` class
    - `extract()`: connect to source, validate connectivity before extraction (raise if fails), support `FULL`, `WATERMARK`, `CDC` strategies, record extraction start event to monitor
    - `transform()`: apply all rules from `TransformConfig`; on missing field apply default or route to DLQ; on schema violation pass to `ErrorHandler`; append `LineageEvent` with original payload
    - `load()`: write to sink with `APPEND`/`UPSERT`/`OVERWRITE` modes; use transactions where supported; retry up to `max_retries` with exponential backoff; on exhaustion route to DLQ and emit failure event; record completion event
    - `run_pipeline()`: orchestrate extract → transform → quality-check → load
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 2.2 Write property test for connectivity validation before extraction (Property 1)
    - **Property 1: Connectivity validation before extraction**
    - **Validates: Requirements 1.2**

  - [ ]* 2.3 Write property test for retry exponential backoff (Property 2)
    - **Property 2: Retry with exponential backoff**
    - **Validates: Requirements 1.3, 9.2**

  - [ ]* 2.4 Write property test for extraction event completeness (Property 3)
    - **Property 3: Extraction event completeness**
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 Write property test for watermark monotonicity (Property 4)
    - **Property 4: Incremental extraction watermark monotonicity**
    - **Validates: Requirements 1.5**

  - [ ]* 2.6 Write property test for transformation config applied to every record (Property 5)
    - **Property 5: Transformation config applied to every record**
    - **Validates: Requirements 2.1**

  - [ ]* 2.7 Write property test for missing field handling (Property 6)
    - **Property 6: Missing field handling**
    - **Validates: Requirements 2.2**

  - [ ]* 2.8 Write property test for schema violation rejection (Property 7)
    - **Property 7: Schema violation rejection**
    - **Validates: Requirements 2.4**

  - [ ]* 2.9 Write property test for lineage preserves original payload (Property 8)
    - **Property 8: Lineage preserves original payload**
    - **Validates: Requirements 2.5, 7.1**

  - [ ]* 2.10 Write property test for transactional all-or-nothing load (Property 9)
    - **Property 9: Transactional all-or-nothing load**
    - **Validates: Requirements 3.2**

  - [ ]* 2.11 Write property test for failed load routes to DLQ (Property 10)
    - **Property 10: Failed load routes to DLQ**
    - **Validates: Requirements 3.3**

  - [ ]* 2.12 Write property test for write mode semantics (Property 11)
    - **Property 11: Write mode semantics**
    - **Validates: Requirements 3.4**

  - [ ]* 2.13 Write property test for load completion event completeness (Property 12)
    - **Property 12: Load completion event completeness**
    - **Validates: Requirements 3.5**

  - [ ]* 2.14 Write unit tests for ETL Engine (`data-pipeline/tests/unit/test_etl_engine.py`)
    - Test each source type (RDBMS, S3, Kafka, REST API) connects and returns records
    - Test each transformation type produces correct output
    - Test schema violation routes to error handler
    - _Requirements: 1.1, 1.2, 2.1, 2.3, 2.4_

- [ ] 3. Checkpoint — Ensure all ETL engine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement Stream Processor
  - [ ] 4.1 Implement `data-pipeline/stream_processor.py` with `StreamProcessor` class
    - `start()`: consume from Kafka topic, apply transform pipeline, write to sink; commit offsets only after successful sink write (at-least-once)
    - `stop()`: graceful shutdown
    - `get_throughput_rps()`: return current records-per-second; emit metric to monitor at ≤10s intervals
    - `create_window()`: support `TUMBLING`, `SLIDING`, `SESSION` window types with configurable size
    - Emit backpressure alert when lag exceeds 60 seconds
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 4.2 Write property test for stream processing end-to-end latency (Property 13)
    - **Property 13: Stream processing end-to-end latency**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 4.3 Write property test for at-least-once delivery via offset commit ordering (Property 14)
    - **Property 14: At-least-once delivery via offset commit ordering**
    - **Validates: Requirements 4.3**

  - [ ]* 4.4 Write property test for throughput metric emission frequency (Property 15)
    - **Property 15: Throughput metric emission frequency**
    - **Validates: Requirements 4.4**

  - [ ]* 4.5 Write property test for backpressure alert on sustained lag (Property 16)
    - **Property 16: Backpressure alert on sustained lag**
    - **Validates: Requirements 4.5**

  - [ ]* 4.6 Write property test for windowed aggregation correctness (Property 17)
    - **Property 17: Windowed aggregation correctness**
    - **Validates: Requirements 4.6**

  - [ ]* 4.7 Write unit tests for Stream Processor (`data-pipeline/tests/unit/test_stream_processor.py`)
    - Test offset commit only occurs after successful write
    - Test window boundary correctness for each window type
    - _Requirements: 4.3, 4.6_

- [ ] 5. Implement Batch Processor
  - [ ] 5.1 Implement `data-pipeline/pipeline_batch_processor.py` with `PipelineBatchProcessor` class
    - `submit_job()`: create Airflow DAG for the job, schedule via cron (min 1-minute granularity), save initial checkpoint before processing begins
    - `get_checkpoint()` / `save_checkpoint()`: persist checkpoint to PostgreSQL `pipeline_checkpoints` table
    - `resume_from_checkpoint()`: resume from last offset, skipping already-processed records
    - Parallel worker pool defaulting to CPU core count
    - DAG dependency ordering: downstream job waits for all upstream dependencies
    - Emit completion event on finish
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 5.2 Write property test for checkpoint created on batch job start (Property 18)
    - **Property 18: Checkpoint created on batch job start**
    - **Validates: Requirements 5.2**

  - [ ]* 5.3 Write property test for checkpoint resume avoids duplicate processing (Property 19)
    - **Property 19: Checkpoint resume avoids duplicate processing**
    - **Validates: Requirements 5.3**

  - [ ]* 5.4 Write property test for batch completion event completeness (Property 20)
    - **Property 20: Batch completion event completeness**
    - **Validates: Requirements 5.5**

  - [ ]* 5.5 Write property test for DAG dependency ordering (Property 21)
    - **Property 21: DAG dependency ordering**
    - **Validates: Requirements 5.6**

  - [ ]* 5.6 Write unit tests for Batch Processor (`data-pipeline/tests/unit/test_batch_processor.py`)
    - Test checkpoint save/load round-trip
    - Test resume skips already-processed offsets
    - Test cron schedule parsing rejects sub-minute granularity
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 6. Checkpoint — Ensure all stream and batch processor tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Quality Checker
  - [ ] 7.1 Implement `data-pipeline/quality_checker.py` with `QualityChecker` class
    - `check_record()`: evaluate record against all rules; tag with `QualityTag` (rule_id + severity); never skip a rule
    - `check_batch()`: apply `check_record()` to all records; produce `QualityReport` with pass rate, per-rule failure counts, sample failing records
    - `enforce_pass_rate()`: halt pipeline and alert monitor when pass rate < threshold
    - Support rule types: `NULL_CHECK`, `RANGE`, `REGEX`, `REFERENTIAL_INTEGRITY`, `STATISTICAL_OUTLIER`
    - Treat blocking warnings as errors
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 7.2 Write property test for quality check applied to every record (Property 22)
    - **Property 22: Quality check applied to every record**
    - **Validates: Requirements 6.1**

  - [ ]* 7.3 Write property test for error-tagged records routed to DLQ (Property 23)
    - **Property 23: Error-tagged records routed to DLQ**
    - **Validates: Requirements 6.3, 6.4**

  - [ ]* 7.4 Write property test for quality report completeness (Property 24)
    - **Property 24: Quality report completeness**
    - **Validates: Requirements 6.6**

  - [ ]* 7.5 Write property test for pass rate threshold enforcement (Property 25)
    - **Property 25: Pass rate threshold enforcement**
    - **Validates: Requirements 6.7**

  - [ ]* 7.6 Write unit tests for Quality Checker (`data-pipeline/tests/unit/test_quality_checker.py`)
    - Test each rule type correctly tags a violating record
    - Test blocking warning treated as error
    - Test quality report contains sample failing records
    - _Requirements: 6.2, 6.3, 6.5, 6.6_

- [ ] 8. Implement Governance Manager
  - [ ] 8.1 Implement `data-pipeline/governance_manager.py` with `GovernanceManager` class
    - `record_lineage()`: persist `LineageEvent` to PostgreSQL `pipeline_lineage` table with TTL enforcement (min 90 days)
    - `mask_fields()`: redact fields not in `sink.authorized_fields` before write
    - `classify_source()`: store classification label; reject registration if label absent
    - `handle_deletion_request()`: flag all lineage records for subject within 24h
    - `audit_log()`: write structured audit entry with actor, timestamp, before/after values
    - Scheduled cleanup job for lineage retention enforcement
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 8.2 Write property test for field-level access control masking (Property 26)
    - **Property 26: Field-level access control masking**
    - **Validates: Requirements 7.2**

  - [ ]* 8.3 Write property test for classification required for source/sink registration (Property 27)
    - **Property 27: Classification required for source/sink registration**
    - **Validates: Requirements 7.3**

  - [ ]* 8.4 Write property test for lineage retention invariant (Property 28)
    - **Property 28: Lineage retention invariant**
    - **Validates: Requirements 7.4**

  - [ ]* 8.5 Write property test for deletion request completeness (Property 29)
    - **Property 29: Deletion request completeness**
    - **Validates: Requirements 7.5**

  - [ ]* 8.6 Write property test for audit log completeness (Property 30)
    - **Property 30: Audit log completeness**
    - **Validates: Requirements 7.6**

  - [ ]* 8.7 Write unit tests for Governance Manager (`data-pipeline/tests/unit/test_governance_manager.py`)
    - Test masked fields are absent from written record
    - Test unclassified source registration is rejected
    - Test audit log entry contains before/after values
    - _Requirements: 7.2, 7.3, 7.6_

- [ ] 9. Implement Error Handler
  - [ ] 9.1 Implement `data-pipeline/pipeline_error_handler.py` with `ErrorHandler` class
    - `classify()`: map every exception to exactly one of `TRANSIENT`, `PERMANENT`, `CONFIGURATION`
    - `handle()`: for TRANSIENT — retry with exponential backoff (`delay = min(base * 2^(attempt-1), max_delay)`); for PERMANENT — route to DLQ with reason + stack trace, continue; for CONFIGURATION — halt stage, preserve checkpoint, emit alert
    - `route_to_dlq()`: insert `DeadLetterRecord` into `pipeline_dlq` table with expiry = now + retention period
    - `check_circuit_breaker()`: track error rate in rolling 5-minute window; transition to `OPEN` when rate > threshold; `HALF_OPEN` after cool-down; `CLOSED` on probe success
    - Expose `POST /pipeline/dlq/{dlq_id}/replay` reprocessing API
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 9.2 Write property test for error classification exhaustiveness (Property 35)
    - **Property 35: Error classification exhaustiveness**
    - **Validates: Requirements 9.1**

  - [ ]* 9.3 Write property test for permanent error DLQ routing with metadata (Property 36)
    - **Property 36: Permanent error DLQ routing with metadata**
    - **Validates: Requirements 9.3**

  - [ ]* 9.4 Write property test for configuration error preserves checkpoint (Property 37)
    - **Property 37: Configuration error preserves checkpoint**
    - **Validates: Requirements 9.4**

  - [ ]* 9.5 Write property test for DLQ record retention and replayability (Property 38)
    - **Property 38: DLQ record retention and replayability**
    - **Validates: Requirements 9.5**

  - [ ]* 9.6 Write property test for single record failure isolation (Property 39)
    - **Property 39: Single record failure isolation**
    - **Validates: Requirements 9.6**

  - [ ]* 9.7 Write property test for circuit breaker triggers on high error rate (Property 40)
    - **Property 40: Circuit breaker triggers on high error rate**
    - **Validates: Requirements 9.7**

  - [ ]* 9.8 Write unit tests for Error Handler (`data-pipeline/tests/unit/test_error_handler.py`)
    - Test each error category triggers the correct action
    - Test DLQ record has correct expiry timestamp
    - Test circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.7_

- [ ] 10. Checkpoint — Ensure all quality, governance, and error handler tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement Pipeline Monitor
  - [ ] 11.1 Implement `data-pipeline/pipeline_monitor.py` with `PipelineMonitor` class
    - `record_event()`: emit structured JSON log to stdout for every lifecycle event (start, checkpoint, completion, failure); JSON must include `event_type` field
    - `update_health()`: update in-memory component health map; `/health` endpoint must reflect change within 5 seconds
    - `emit_alert()`: publish structured alert event to the existing alerting system when thresholds are breached
    - `get_metrics_response()`: return Prometheus text-format string with all 9 metrics from the design (counters, histograms, gauges)
    - Expose `/metrics` on configurable port and `/health` HTTP endpoints
    - Propagate W3C `traceparent` header across pipeline stages when tracing is enabled
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 11.2 Write property test for standard metrics presence (Property 31)
    - **Property 31: Standard metrics presence**
    - **Validates: Requirements 8.2**

  - [ ]* 11.3 Write property test for health status update latency (Property 32)
    - **Property 32: Health status update latency**
    - **Validates: Requirements 8.3**

  - [ ]* 11.4 Write property test for structured lifecycle log format (Property 33)
    - **Property 33: Structured lifecycle log format**
    - **Validates: Requirements 8.5**

  - [ ]* 11.5 Write property test for W3C TraceContext propagation (Property 34)
    - **Property 34: W3C TraceContext propagation**
    - **Validates: Requirements 8.6**

  - [ ]* 11.6 Write unit tests for Pipeline Monitor (`data-pipeline/tests/unit/test_pipeline_monitor.py`)
    - Test `/metrics` response is parseable by Prometheus client
    - Test `/health` returns valid JSON with `status` field
    - Test structured log output is valid JSON
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [ ] 12. Wire components together in `ml-model-api/data_pipeline.py`
  - [ ] 12.1 Implement `ml-model-api/data_pipeline.py` as the integration entry point
    - Instantiate and wire: `ETLEngine`, `StreamProcessor`, `PipelineBatchProcessor`, `QualityChecker`, `GovernanceManager`, `ErrorHandler`, `PipelineMonitor`
    - Load `PipelineConfig` from YAML configuration file
    - Route quality-checked records through governance masking before load
    - Pass all errors through `ErrorHandler`; feed monitor events from all components into `PipelineMonitor`
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1_

  - [ ]* 12.2 Write integration tests for end-to-end pipeline flow
    - Test a record flows from source through transform → quality check → governance → sink
    - Test a failing record ends up in DLQ and does not appear in sink
    - _Requirements: 2.4, 6.3, 9.3_

- [ ] 13. Create Kubernetes manifests in `k8s/data-pipeline/`
  - Create `k8s/data-pipeline/pipeline-etl-deployment.yaml`: Deployment for `pipeline-etl` workload (ETL Engine + Quality Checker + Governance Manager)
  - Create `k8s/data-pipeline/pipeline-stream-deployment.yaml`: Deployment for `pipeline-stream` workload (Stream Processor)
  - Create `k8s/data-pipeline/pipeline-monitor-deployment.yaml`: Deployment for `pipeline-monitor` sidecar/metrics server; expose `/metrics` and `/health` ports
  - Create `k8s/data-pipeline/pipeline-dlq-cronjob.yaml`: CronJob for DLQ TTL cleanup
  - Create `k8s/data-pipeline/configmap.yaml`: pipeline YAML configuration mounted as a volume
  - All workloads target the existing `flavorsnap` namespace
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 14. Create helper scripts in `scripts/data-pipeline/`
  - `scripts/data-pipeline/init_db.py`: create PostgreSQL tables (`pipeline_dlq`, `pipeline_lineage`, `pipeline_checkpoints`, `pipeline_audit_log`)
  - `scripts/data-pipeline/replay_dlq.py`: CLI wrapper around the DLQ reprocessing API
  - `scripts/data-pipeline/run_pipeline.py`: CLI entry point to trigger a pipeline run from a config file
  - _Requirements: 9.5, 7.4, 7.6_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests use Hypothesis with `@settings(max_examples=100)` and must include the comment tag `# Feature: advanced-data-pipeline, Property N: <property_text>`
- Each task references specific requirements for traceability
- All components are implemented in Python, consistent with the `ml-model-api` codebase
- Property test files map to design sections: `test_etl_properties.py` (1–12), `test_stream_properties.py` (13–17), `test_batch_properties.py` (18–21), `test_quality_properties.py` (22–25), `test_governance_properties.py` (26–30), `test_monitor_properties.py` (31–34), `test_error_properties.py` (35–40)
