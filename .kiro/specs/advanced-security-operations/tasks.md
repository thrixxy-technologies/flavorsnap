# Implementation Plan: Advanced Security Operations

## Overview

Implement the SecOps platform as a set of loosely coupled Python services deployed to Kubernetes. Each component is built incrementally, wired to the shared event bus (Redis Streams) and PostgreSQL persistence layer, then integrated end-to-end.

## Tasks

- [ ] 1. Set up shared foundation (models, event bus, database)
  - [ ] 1.1 Create `security-operations/models.py` with all dataclasses and enums from the design (`Severity`, `IncidentStatus`, `Alert`, `Incident`, `ActionRecord`, `TelemetryRecord`, `ScanResult`, `VulnFinding`, `Policy`, `PolicyRule`, `ComplianceResult`, `RuleOutcome`, `Artifact`, `ForensicsManifest`, `Report`)
    - _Requirements: 1.2, 2.3, 3.2, 4.2, 5.3, 6.4, 7.2_
  - [ ] 1.2 Create `security-operations/event_bus.py` — Redis Streams wrapper with `publish(stream, event)` and `consume(stream, group, consumer)` methods
    - _Requirements: 3.1, 3.5_
  - [ ] 1.3 Create `security-operations/db.py` — SQLAlchemy session factory targeting the shared PostgreSQL instance; include schema migration stubs for all SecOps tables
    - _Requirements: 3.4, 7.6_

- [ ] 2. Implement ML Model API endpoint
  - [ ] 2.1 Add `/secops/score` POST endpoint to `ml-model-api/secops.py`; accept a normalized event payload, return `{"threat_score": float, "model_version": str}`
    - _Requirements: 1.2, 1.4_
  - [ ]* 2.2 Write unit tests for `secops.py` — valid payload returns score in [0.0, 1.0], malformed payload returns 400
    - _Requirements: 1.2_

- [ ] 3. Implement Security Monitor
  - [ ] 3.1 Create `security-operations/security_monitor.py` implementing `SecurityMonitor` with `register_source`, `collect_all`, and `get_health`; collection interval ≤60 s; store `TelemetryRecord` to DB with UTC timestamp and source_id; emit connectivity `Alert` when source is unreachable; forward threshold-crossing events to `secops.telemetry` stream
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [ ]* 3.2 Write property test for Security Monitor — Property 10: every registered source appears in collection results
    - **Property 10: Every registered source appears in collection results**
    - **Validates: Requirements 3.1**
  - [ ]* 3.3 Write property test for Security Monitor — Property 11: telemetry records contain UTC timestamp and source identifier
    - **Property 11: Telemetry records contain UTC timestamp and source identifier**
    - **Validates: Requirements 3.2**
  - [ ]* 3.4 Write property test for Security Monitor — Property 12: threshold crossing forwards event to Threat Detector
    - **Property 12: Threshold crossing forwards event to Threat Detector**
    - **Validates: Requirements 3.5**
  - [ ]* 3.5 Write property test for Security Monitor — Property 13: health endpoint covers all registered sources
    - **Property 13: Health endpoint covers all registered sources**
    - **Validates: Requirements 3.6**
  - [ ]* 3.6 Write unit tests for Security Monitor — unreachable source emits connectivity Alert and continues polling; health endpoint returns per-source status
    - _Requirements: 3.3, 3.6_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Threat Detector
  - [ ] 5.1 Create `security-operations/threat_detector.py` implementing `ThreatDetector` with `evaluate`, `reload_rules`, and `set_ml_threshold`; call `ML_Model_API /secops/score`; fall back to rule-based detection when ML is unavailable and log `degraded_mode=true`; deduplicate Alerts with identical `rule_id` + `affected_resource` within a 60-second window; support hot-reload of detection rules without restart
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [ ]* 5.2 Write property test for Threat Detector — Property 1: threat evaluation covers all active rules
    - **Property 1: Threat evaluation covers all active rules**
    - **Validates: Requirements 1.1**
  - [ ]* 5.3 Write property test for Threat Detector — Property 2: ML-triggered alerts contain all required fields
    - **Property 2: ML-triggered alerts contain all required fields**
    - **Validates: Requirements 1.2**
  - [ ]* 5.4 Write property test for Threat Detector — Property 3: alert deduplication within 60-second window
    - **Property 3: Alert deduplication within 60-second window**
    - **Validates: Requirements 1.3**
  - [ ]* 5.5 Write property test for Threat Detector — Property 4: hot-reload applies new rules immediately
    - **Property 4: Hot-reload applies new rules immediately**
    - **Validates: Requirements 1.5**
  - [ ]* 5.6 Write unit tests for Threat Detector — ML unavailable triggers rule-based fallback; rule parse error on reload retains previous rule set
    - _Requirements: 1.4, 1.5_

- [ ] 6. Implement Incident Responder
  - [ ] 6.1 Create `security-operations/incident_responder.py` implementing `IncidentResponder` with `handle_alert`, `execute_playbook`, and `manual_override`; open `Incident` within 30 s for Critical/High alerts; record `ActionRecord` with action_type, executor, timestamp, outcome; retry failed actions up to 3× with exponential backoff (1 s, 2 s, 4 s) then escalate; prevent duplicate Incidents for the same open resource+rule; support authorized manual override
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - [ ]* 6.2 Write property test for Incident Responder — Property 5: Critical and High alerts always open an Incident
    - **Property 5: Critical and High alerts always open an Incident**
    - **Validates: Requirements 2.1**
  - [ ]* 6.3 Write property test for Incident Responder — Property 6: playbook executed matches alert rule
    - **Property 6: Playbook executed matches alert rule**
    - **Validates: Requirements 2.2**
  - [ ]* 6.4 Write property test for Incident Responder — Property 7: action records contain all required fields
    - **Property 7: Action records contain all required fields**
    - **Validates: Requirements 2.3**
  - [ ]* 6.5 Write property test for Incident Responder — Property 8: failed actions are retried exactly 3 times before escalation
    - **Property 8: Failed actions are retried exactly 3 times before escalation**
    - **Validates: Requirements 2.4**
  - [ ]* 6.6 Write property test for Incident Responder — Property 9: no duplicate Incidents for the same open resource+rule
    - **Property 9: No duplicate Incidents for the same open resource+rule**
    - **Validates: Requirements 2.5**
  - [ ]* 6.7 Write unit tests for Incident Responder — manual override records operator identity; duplicate incident attempt returns existing open Incident
    - _Requirements: 2.5, 2.6_

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement Vulnerability Scanner
  - [ ] 8.1 Create `security-operations/vulnerability_scanner.py` implementing `VulnerabilityScanner` with `scan` and `schedule`; identify CVEs from software inventory; assign CVSS-based `Severity`; create `Alert` for Critical/High findings; record failed scans with timestamp and reason; support configurable cron-based scheduling (minimum daily)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [ ] 8.2 Create `scripts/security/run_scan.py` — CLI wrapper that invokes `VulnerabilityScanner.scan` for a given target and prints results
    - _Requirements: 4.1, 4.5_
  - [ ]* 8.3 Write property test for Vulnerability Scanner — Property 14: scan results contain findings for all known CVEs
    - **Property 14: Scan results contain findings for all known CVEs**
    - **Validates: Requirements 4.1**
  - [ ]* 8.4 Write property test for Vulnerability Scanner — Property 15: vulnerability findings contain all required fields
    - **Property 15: Vulnerability findings contain all required fields**
    - **Validates: Requirements 4.2**
  - [ ]* 8.5 Write property test for Vulnerability Scanner — Property 16: CVSS score maps to correct Severity
    - **Property 16: CVSS score maps to correct Severity**
    - **Validates: Requirements 4.3**
  - [ ]* 8.6 Write property test for Vulnerability Scanner — Property 17: Critical and High vulnerabilities generate Alerts
    - **Property 17: Critical and High vulnerabilities generate Alerts**
    - **Validates: Requirements 4.4**
  - [ ]* 8.7 Write unit tests for Vulnerability Scanner — unreachable target records failed scan; CVSS boundary values (0.1, 3.9, 4.0, 6.9, 7.0, 8.9, 9.0, 10.0) map to correct Severity
    - _Requirements: 4.3, 4.6_

- [ ] 9. Implement Compliance Checker
  - [ ] 9.1 Create `security-operations/compliance_checker.py` implementing `ComplianceChecker` with `check` and `load_policy`; evaluate target against all rules in a versioned YAML Policy via OPA sidecar; return `ComplianceResult` with policy_name, policy_version, evaluated_at, and per-rule `RuleOutcome` (pass/fail/inconclusive); include remediation guidance for failing rules; mark rule as inconclusive on evaluation error
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - [ ] 9.2 Create sample Policy YAML files for CIS Benchmarks, NIST SP 800-53, and SOC 2 Type II under `k8s/security/policies/`
    - _Requirements: 5.5_
  - [ ] 9.3 Create `scripts/security/run_compliance.py` — CLI wrapper that loads a Policy file and runs `ComplianceChecker.check` against a target
    - _Requirements: 5.1, 5.2_
  - [ ]* 9.4 Write property test for Compliance Checker — Property 18: compliance result covers all policy rules with required fields
    - **Property 18: Compliance result covers all policy rules with required fields**
    - **Validates: Requirements 5.1, 5.3**
  - [ ]* 9.5 Write property test for Compliance Checker — Property 19: policy serialization round-trip
    - **Property 19: Policy serialization round-trip**
    - **Validates: Requirements 5.2**
  - [ ]* 9.6 Write property test for Compliance Checker — Property 20: failing rules include remediation guidance
    - **Property 20: Failing rules include remediation guidance**
    - **Validates: Requirements 5.6**
  - [ ]* 9.7 Write unit tests for Compliance Checker — rule evaluation error marks outcome as inconclusive; result includes error_message and rule_id
    - _Requirements: 5.4_

- [ ] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement Forensics Engine
  - [ ] 11.1 Create `security-operations/forensics_engine.py` implementing `ForensicsEngine` with `collect` and `get_artifact`; compute SHA-256 hash per artifact; preserve original `mtime`; produce `ForensicsManifest` with artifact list, hashes, timestamps, and source identifiers; log and continue on access-denied artifacts; enforce `forensics-investigator` RBAC role on `get_artifact`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - [ ] 11.2 Create `scripts/security/collect_forensics.py` — CLI wrapper that initiates forensic collection for a given incident ID
    - _Requirements: 6.1_
  - [ ]* 11.3 Write property test for Forensics Engine — Property 21: forensic artifact integrity and manifest completeness
    - **Property 21: Forensic artifact integrity and manifest completeness**
    - **Validates: Requirements 6.1, 6.2, 6.4**
  - [ ]* 11.4 Write property test for Forensics Engine — Property 22: original artifact timestamps are preserved
    - **Property 22: Original artifact timestamps are preserved**
    - **Validates: Requirements 6.3**
  - [ ]* 11.5 Write property test for Forensics Engine — Property 23: unauthorized access to forensic archives is rejected
    - **Property 23: Unauthorized access to forensic archives is rejected**
    - **Validates: Requirements 6.6**
  - [ ]* 11.6 Write unit tests for Forensics Engine — access-denied artifact is logged and skipped; manifest records failure entry; authorized access succeeds
    - _Requirements: 6.5, 6.6_

- [ ] 12. Implement Report Generator
  - [ ] 12.1 Create `security-operations/report_generator.py` implementing `ReportGenerator` with `generate` and `schedule`; aggregate data from PostgreSQL; render PDF and JSON formats; deliver to configured notification channels within 5 minutes of scheduled time; retry once within 10 minutes on failure; retain reports for ≥1 year
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  - [ ] 12.2 Create `scripts/security/generate_report.py` — CLI wrapper that triggers `ReportGenerator.generate` for a given period and format
    - _Requirements: 7.1, 7.3_
  - [ ]* 12.3 Write property test for Report Generator — Property 24: generated reports contain all required summary fields
    - **Property 24: Generated reports contain all required summary fields**
    - **Validates: Requirements 7.2**
  - [ ]* 12.4 Write property test for Report Generator — Property 25: report delivery reaches all configured channels
    - **Property 25: Report delivery reaches all configured channels**
    - **Validates: Requirements 7.4**
  - [ ]* 12.5 Write unit tests for Report Generator — generation failure logs timestamp and reason and retries once; scheduled report delivered within 5 minutes
    - _Requirements: 7.5_

- [ ] 13. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Create Kubernetes manifests
  - [ ] 14.1 Create `k8s/security/namespace.yaml` defining the `secops` namespace
    - _Requirements: 1.1, 2.1, 3.1_
  - [ ] 14.2 Create Deployment + Service manifests for each component: `threat-detector.yaml`, `incident-responder.yaml`, `security-monitor.yaml`, `vulnerability-scanner.yaml`, `compliance-checker.yaml`, `forensics-engine.yaml`, `report-generator.yaml`
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1_
  - [ ] 14.3 Create `k8s/security/rbac.yaml` — ServiceAccount, Roles, and RoleBindings including the `forensics-investigator` role
    - _Requirements: 6.6_
  - [ ] 14.4 Create `k8s/security/configmap.yaml` with shared configuration (ML threshold, collection interval, retention periods, notification channels) and `k8s/security/secrets.yaml` stubs for sealed secrets
    - _Requirements: 1.2, 3.1, 3.4, 7.6_

- [ ] 15. Wire components together via event bus
  - [ ] 15.1 Update `security_monitor.py` to publish telemetry events to the `secops.telemetry` Redis Stream and subscribe to the `secops.alerts` stream for connectivity alerts
    - _Requirements: 3.1, 3.3, 3.5_
  - [ ] 15.2 Update `threat_detector.py` to consume from `secops.telemetry` and publish generated `Alert` records to the `secops.alerts` stream
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ] 15.3 Update `incident_responder.py` to consume from `secops.alerts` and persist `Incident` and `ActionRecord` objects to PostgreSQL
    - _Requirements: 2.1, 2.2, 2.3_
  - [ ]* 15.4 Write integration tests for alert-to-incident flow (`tests/integration/secops/test_alert_to_incident_flow.py`)
    - _Requirements: 1.2, 2.1, 2.2_
  - [ ]* 15.5 Write integration tests for scan-to-alert flow (`tests/integration/secops/test_scan_to_alert_flow.py`)
    - _Requirements: 4.4_
  - [ ]* 15.6 Write integration tests for report generation flow (`tests/integration/secops/test_report_generation_flow.py`)
    - _Requirements: 7.2, 7.4_

- [ ] 16. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` and must include the tag comment `# Feature: advanced-security-operations, Property <N>: <property_text>`
- Unit tests cover CVSS boundary values (0.1, 3.9, 4.0, 6.9, 7.0, 8.9, 9.0, 10.0) and all error/fallback paths
- Checkpoints ensure incremental validation before moving to the next component group
