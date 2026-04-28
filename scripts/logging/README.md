# Advanced Logging System for FlavorSnap

This directory contains the comprehensive logging system implementation for FlavorSnap, providing structured logging, real-time aggregation, intelligent analysis, alert integration, performance monitoring, security logging, and compliance reporting.

## Overview

The logging system is designed to provide enterprise-grade observability with the following key features:

- **Structured Logging**: JSON-formatted logs with consistent schema
- **Log Aggregation**: Centralized collection from multiple sources
- **Intelligent Analysis**: Pattern detection, anomaly identification, and insights generation
- **Alert Integration**: Multi-channel alerting with escalation
- **Performance Monitoring**: Real-time performance metrics and health monitoring
- **Security Logging**: Comprehensive security event tracking and threat detection
- **Compliance Reporting**: Automated compliance assessments for multiple standards
- **Scalable Infrastructure**: Kubernetes-based deployment with auto-scaling

## Components

### Core Logging Components

#### 1. Logger Configuration (`ml-model-api/logger_config.py`)
Advanced Python logger with structured output, multiple handlers, and specialized loggers.

**Features:**
- Structured JSON logging with custom formatters
- Multiple output handlers (console, file, rotating files)
- Specialized loggers for different components
- Performance logging decorators
- Security and audit logging functions
- Context-aware logging with LoggerAdapter

**Usage:**
```python
from logger_config import setup_logging, get_logger, log_security_event

# Setup logging
setup_logging()

# Get specialized logger
api_logger = get_api_logger()
api_logger.info("API request processed", extra={'request_id': '123', 'user_id': 'user456'})

# Log security events
log_security_event(
    event_type='login_attempt',
    user_id='user456',
    ip_address='192.168.1.100',
    details={'success': True}
)
```

#### 2. Log Aggregator (`log-aggregator.py`)
Collects, parses, and aggregates logs from multiple sources.

**Features:**
- Multi-source log collection (files, HTTP, database)
- Structured and unstructured log parsing
- Real-time log processing with async I/O
- Pattern detection and analysis
- Prometheus metrics integration
- Configurable retention and rotation

**Configuration:**
```python
config = {
    'log_dir': '/app/logs',
    'output_dir': '/app/logs/analysis',
    'http_sources': [{'url': 'http://log-source.example.com/logs'}],
    'database': {
        'host': 'localhost',
        'port': 5432,
        'database': 'logs'
    }
}
```

#### 3. Log Analyzer (`log-analyzer.py`)
Provides intelligent log analysis with pattern detection and insights.

**Features:**
- Pattern detection for common issues
- Anomaly detection using statistical analysis
- Trend analysis and forecasting
- Business insights generation
- Performance bottleneck identification
- Security event correlation

**Analysis Types:**
- Error pattern detection
- Performance analysis
- Security threat identification
- Business event correlation
- Compliance violation detection

#### 4. Alert Manager (`alert-manager.py`)
Multi-channel alerting system with intelligent escalation.

**Features:**
- Multiple alert channels (Email, Slack, Discord, Teams, Webhook)
- Intelligent escalation based on severity and time
- Alert deduplication and cooldown
- Custom alert templates
- Alert acknowledgment and tracking
- Integration with monitoring systems

**Alert Channels:**
- **Email**: SMTP-based email alerts with HTML formatting
- **Slack**: Rich Slack notifications with attachments
- **Discord**: Discord embeds with color coding
- **Teams**: Microsoft Teams adaptive cards
- **Webhook**: Generic HTTP webhook integration

**Escalation Rules:**
- Time-based escalation (5min, 15min, 1hr)
- Severity-based escalation
- Multi-channel escalation
- Automatic acknowledgment

#### 5. Performance Monitor (`performance-monitor.py`)
Real-time performance monitoring for the logging system.

**Features:**
- System resource monitoring (CPU, memory, disk, network)
- Log processing performance metrics
- Health scoring and alerting
- Prometheus metrics integration
- Performance report generation
- Threshold-based alerting

**Metrics Tracked:**
- Logs processed per second
- Average processing time
- Memory usage
- Disk I/O
- Error rates
- System health score

#### 6. Security Logger (`security-logger.py`)
Comprehensive security event logging and threat detection.

**Features:**
- Security event classification
- Threat pattern detection
- IP blocking and monitoring
- Security incident creation
- Compliance event tracking
- Risk assessment

**Security Events Tracked:**
- Login attempts and failures
- Unauthorized access
- Data access and modification
- Privilege escalation
- Injection attempts
- Brute force attacks
- DDoS attacks

#### 7. Compliance Reporter (`compliance-reporter.py`)
Automated compliance reporting for multiple standards.

**Supported Standards:**
- **GDPR**: General Data Protection Regulation
- **HIPAA**: Health Insurance Portability and Accountability Act
- **PCI DSS**: Payment Card Industry Data Security Standard
- **SOX**: Sarbanes-Oxley Act
- **ISO 27001**: Information Security Management
- **NIST 800-53**: Security and Privacy Controls

**Compliance Features:**
- Automated requirement assessment
- Evidence collection and management
- Compliance scoring
- Gap analysis
- Recommendation generation
- Dashboard reporting

### Infrastructure Components

#### 1. Logging Infrastructure (`k8s/logging/logging-infrastructure.yaml`)
Complete Kubernetes deployment for logging infrastructure.

**Components:**
- **Elasticsearch**: Log storage and indexing
- **Logstash**: Log processing and transformation
- **Kibana**: Log visualization and analysis
- **Filebeat**: Log collection from containers
- **Fluentd**: Alternative log collector
- **Loki**: Alternative log aggregation
- **Grafana**: Metrics visualization

**Features:**
- High availability with multiple replicas
- Persistent storage for log data
- Automatic scaling based on load
- Network policies for security
- Resource limits and requests
- Health checks and monitoring

#### 2. Deployment Script (`scripts/logging/deploy-logging.sh`)
Automated deployment script for logging infrastructure.

**Features:**
- Prerequisite checking
- Namespace creation
- Component deployment
- Health verification
- Configuration management
- Security setup
- Monitoring integration

**Usage:**
```bash
# Deploy complete logging system
./deploy-logging.sh deploy

# Check deployment status
./deploy-logging.sh status

# Scale components
./deploy-logging.sh scale elasticsearch 3

# Cleanup deployment
./deploy-logging.sh cleanup
```

## Configuration

### Environment Variables

```bash
# Logging Configuration
LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG
LOG_DIR=/app/logs

# Component Levels
APP_LOG_LEVEL=INFO
API_LOG_LEVEL=INFO
ML_LOG_LEVEL=INFO
SECURITY_LOG_LEVEL=INFO
PERFORMANCE_LOG_LEVEL=INFO
AUDIT_LOG_LEVEL=INFO

# Alert Configuration
ALERT_EMAIL_ENABLED=true
ALERT_SLACK_ENABLED=true
ALERT_DISCORD_ENABLED=true

# Performance Thresholds
ERROR_RATE_WARNING=5.0
ERROR_RATE_CRITICAL=10.0
RESPONSE_TIME_WARNING=2000.0
RESPONSE_TIME_CRITICAL=5000.0
CPU_USAGE_WARNING=80.0
CPU_USAGE_CRITICAL=95.0
```

### Configuration Files

#### 1. Logging Configuration (`logging-config.yaml`)
```yaml
version: "1.0"

levels:
  root: INFO
  app: INFO
  api: INFO
  security: INFO

outputs:
  console:
    enabled: true
    format: colored
  file:
    enabled: true
    format: structured
    directory: /app/logs
  elasticsearch:
    enabled: true
    hosts: ["elasticsearch:9200"]
    index_pattern: "flavorsnap-logs-%Y.%m.%d"

aggregation:
  enabled: true
  interval_seconds: 60
  batch_size: 1000

analysis:
  enabled: true
  patterns:
    error_detection: true
    performance_analysis: true
    security_monitoring: true
```

#### 2. Alert Configuration
```yaml
alerting:
  enabled: true
  channels:
    email:
      enabled: true
      smtp_server: smtp.gmail.com
      recipients: ["admin@flavorsnap.com"]
    slack:
      enabled: true
      webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      channel: "#alerts"
  thresholds:
    critical:
      error_rate: 10.0
      response_time_ms: 5000.0
    warning:
      error_rate: 5.0
      response_time_ms: 2000.0
```

## Usage

### 1. Basic Logging

```python
from logger_config import setup_logging, get_logger

# Initialize logging
setup_logging()

# Get logger
logger = get_logger('flavorsnap.app')

# Log events
logger.info("Application started")
logger.error("Database connection failed", extra={'error_code': 'DB_CONN_FAIL'})
```

### 2. Security Logging

```python
from logger_config import log_security_event

# Log security events
log_security_event(
    event_type='login_failure',
    user_id='user123',
    ip_address='192.168.1.100',
    details={'reason': 'invalid_password'}
)
```

### 3. Performance Logging

```python
from logger_config import log_performance

# Use performance decorator
@log_performance('database_query')
def execute_query(query):
    # Database operation
    return result

# Manual performance logging
perf_logger = get_performance_logger()
perf_logger.info("Query executed", extra={
    'query': query,
    'duration': 150.5,
    'rows_returned': 1000
})
```

### 4. Compliance Logging

```python
from logger_config import log_compliance_event

# Log compliance events
log_compliance_event(
    regulation='GDPR',
    event_type='data_access',
    data={
        'user_id': 'user123',
        'data_type': 'personal_data',
        'purpose': 'service_provision',
        'consent_obtained': True
    }
)
```

## Monitoring and Observability

### 1. Prometheus Metrics

The logging system exposes comprehensive Prometheus metrics:

**Logging Metrics:**
- `logging_logs_processed_total`: Total logs processed
- `logging_processing_duration_seconds`: Log processing time
- `logging_error_rate_percent`: Error rate percentage
- `logging_throughput_logs_per_second`: Logs per second

**Security Metrics:**
- `security_events_total`: Security events by type
- `security_failed_login_attempts_total`: Failed login attempts
- `security_suspicious_activities_total`: Suspicious activities
- `security_current_threat_level`: Current threat level

**Performance Metrics:**
- `logging_system_cpu_usage_percent`: CPU usage
- `logging_system_memory_usage_percent`: Memory usage
- `logging_system_disk_usage_percent`: Disk usage
- `logging_health_score`: Overall health score

### 2. Grafana Dashboards

Pre-configured Grafana dashboards include:

- **Logging Overview**: System-wide logging metrics
- **Security Dashboard**: Security events and threats
- **Performance Dashboard**: Performance metrics and health
- **Compliance Dashboard**: Compliance status and scores
- **Alert Dashboard**: Alert status and escalation

### 3. Kibana Dashboards

Kibana provides log visualization with:

- **Log Analysis**: Detailed log analysis and filtering
- **Security Events**: Security event visualization
- **Performance Logs**: Performance-related logs
- **Audit Logs**: Audit trail visualization
- **Error Analysis**: Error pattern analysis

## Security

### 1. Access Control

- Role-based access control (RBAC)
- Network policies for traffic isolation
- Service account management
- Pod security policies

### 2. Data Protection

- Encryption in transit (TLS)
- Encryption at rest (disk encryption)
- Sensitive data masking
- Data retention policies

### 3. Threat Detection

- Pattern-based threat detection
- Anomaly detection
- IP reputation checking
- Rate limiting
- Automated blocking

## Compliance

### 1. GDPR Compliance

- Personal data identification
- Consent management
- Data minimization
- Right to access
- Data retention limits

### 2. HIPAA Compliance

- Access control
- Audit logging
- Transmission security
- Data integrity
- Incident response

### 3. PCI DSS Compliance

- Strong cryptography
- Access control measures
- Secure transmission
- Vulnerability scanning
- Penetration testing

## Troubleshooting

### 1. Common Issues

**High Memory Usage:**
- Check log retention settings
- Increase memory limits
- Optimize log processing

**Slow Log Processing:**
- Check Elasticsearch cluster health
- Increase Logstash workers
- Optimize log parsing rules

**Alert Not Working:**
- Verify alert channel configuration
- Check network connectivity
- Review alert rules

### 2. Debug Commands

```bash
# Check pod status
kubectl get pods -n flavorsnap-logging

# Check logs
kubectl logs -n flavorsnap-logging deployment/logstash

# Check Elasticsearch health
curl -X GET "elasticsearch:9200/_cluster/health"

# Check Logstash pipeline
curl -X GET "logstash:9600/_node/stats/pipelines"

# Check Kibana status
curl -X GET "kibana:5601/api/status"
```

### 3. Performance Tuning

**Elasticsearch:**
- Increase heap size: `-Xms4g -Xmx4g`
- Optimize index settings
- Use SSD storage
- Configure shard allocation

**Logstash:**
- Increase pipeline workers
- Optimize filter order
- Use persistent queues
- Tune batch sizes

**Filebeat:**
- Adjust scan frequency
- Optimize multiline patterns
- Configure backpressure handling
- Tune buffer sizes

## Maintenance

### 1. Regular Tasks

**Daily:**
- Check system health
- Review alert status
- Monitor resource usage

**Weekly:**
- Review log retention
- Update security rules
- Performance analysis

**Monthly:**
- Compliance assessment
- Security audit
- Capacity planning

**Quarterly:**
- Security review
- Performance optimization
- Documentation update

### 2. Backup and Recovery

**Elastic Indices:**
```bash
# Create snapshot
curl -X PUT "elasticsearch:9200/_snapshot/backup/snapshot_1"

# Restore snapshot
curl -X POST "elasticsearch:9200/_snapshot/backup/snapshot_1/_restore"
```

**Configuration:**
```bash
# Backup ConfigMaps
kubectl get configmap -n flavorsnap-logging -o yaml > backup-config.yaml

# Restore ConfigMaps
kubectl apply -f backup-config.yaml
```

## Integration

### 1. External Systems

**Monitoring Integration:**
- Prometheus metrics
- Grafana dashboards
- Alertmanager integration

**SIEM Integration:**
- Splunk forwarder
- QRadar integration
- Elastic SIEM

**Cloud Integration:**
- AWS CloudWatch
- Azure Monitor
- Google Cloud Logging

### 2. API Integration

**Log Ingestion API:**
```python
import requests

# Send log to aggregator
response = requests.post(
    'http://log-aggregator:8080/api/logs',
    json={
        'timestamp': '2024-04-24T10:00:00Z',
        'level': 'INFO',
        'message': 'Test log',
        'source': 'test-app'
    }
)
```

**Alert API:**
```python
import requests

# Create alert
response = requests.post(
    'http://alert-manager:8080/api/alerts',
    json={
        'title': 'Test Alert',
        'message': 'This is a test alert',
        'severity': 'warning',
        'source': 'test-system'
    }
)
```

## Best Practices

### 1. Logging Best Practices

- Use structured logging with consistent schema
- Include correlation IDs for request tracing
- Log at appropriate levels
- Avoid logging sensitive data
- Use context for additional information

### 2. Performance Best Practices

- Monitor system resources
- Optimize log processing
- Use appropriate retention policies
- Scale based on load
- Regular performance reviews

### 3. Security Best Practices

- Implement access controls
- Encrypt sensitive data
- Regular security audits
- Monitor for threats
- Incident response planning

### 4. Compliance Best Practices

- Regular compliance assessments
- Maintain audit trails
- Document policies
- Employee training
- Continuous improvement

## Support

### 1. Documentation

- Component documentation in respective directories
- API documentation with examples
- Troubleshooting guides
- Best practices documentation

### 2. Monitoring

- System health monitoring
- Performance metrics
- Alert status tracking
- Compliance dashboard

### 3. Community

- Issue tracking in GitHub
- Community forums
- Regular updates
- Security notifications

## License

This logging system is part of the FlavorSnap project and follows the same licensing terms.

---

For more information, questions, or support, please refer to the main FlavorSnap documentation or create an issue in the repository.
