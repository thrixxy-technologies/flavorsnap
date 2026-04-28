# FlavorSnap Monitoring

This document describes the monitoring infrastructure for FlavorSnap.

## Architecture

```
FlavorSnap API ──► /metrics ──► Prometheus ──► Grafana (dashboards)
                                     │
                                     └──► Alertmanager ──► Email / Slack / Webhook

Application logs ──► Filebeat ──► Logstash ──► Elasticsearch ──► Kibana
```

## Components

| Component | Port | Purpose |
|-----------|------|---------|
| Prometheus | 9090 | Metrics storage and querying |
| Grafana | 3001 | Dashboards and visualisation |
| Alertmanager | 9093 | Alert routing and deduplication |
| Node Exporter | 9100 | Host system metrics |
| cAdvisor | 8080 | Container metrics |
| Elasticsearch | 9200 | Log storage |
| Kibana | 5601 | Log exploration |
| Logstash | 5044 | Log ingestion pipeline |

## Quick Start

```bash
# Start the full monitoring stack
bash scripts/setup_monitoring.sh

# Start without ELK (lighter weight)
bash scripts/setup_monitoring.sh --skip-elk
```

## Metrics Collected

### HTTP Metrics
- `flavorsnap_http_requests_total` — request count by method, endpoint, status code
- `flavorsnap_http_request_duration_seconds` — latency histogram by method and endpoint
- `flavorsnap_http_request_size_bytes` — request body size histogram
- `flavorsnap_http_response_size_bytes` — response body size histogram
- `flavorsnap_http_errors_total` — error count by method, endpoint, status code
- `flavorsnap_active_requests` — gauge of in-flight requests

### Model / Inference Metrics
- `flavorsnap_model_inference_duration_seconds` — inference latency histogram
- `flavorsnap_model_inference_total` — inference count by model version and status
- `flavorsnap_model_confidence` — confidence score distribution per food class
- `flavorsnap_model_predictions_total` — prediction count per food class
- `flavorsnap_model_loaded` — gauge (1 = model loaded, 0 = not loaded)
- `flavorsnap_classification_latency_seconds` — end-to-end classification summary

### Cache Metrics
- `flavorsnap_cache_hits_total` — cache hits by cache type (redis / memory)
- `flavorsnap_cache_misses_total` — cache misses by cache type
- `flavorsnap_cache_size_bytes` — estimated cache size

### System Metrics
- `flavorsnap_system_cpu_usage_percent` — CPU usage %
- `flavorsnap_system_memory_usage_bytes` — memory used
- `flavorsnap_system_memory_total_bytes` — total memory
- `flavorsnap_system_disk_usage_percent` — disk usage % per mount point
- `flavorsnap_process_open_fds` — open file descriptors
- `flavorsnap_process_threads` — thread count
- `flavorsnap_api_uptime_seconds` — seconds since process start

### Upload Metrics
- `flavorsnap_upload_size_bytes` — uploaded image size histogram

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Prometheus metrics (text format) |
| `GET /monitoring/dashboard` | Full JSON snapshot of all metrics |
| `GET /monitoring/health` | Condensed health summary with overall status |
| `GET /monitoring/alerts` | List of currently firing alerts |
| `GET /monitoring/profiler` | Performance profiler stats per span |

## Alert Rules

Alerts are defined in `prometheus/alert_rules.yml` and evaluated by Prometheus.
Notifications are routed through Alertmanager (`monitoring/alertmanager.yml`).

### Default Alerts

| Alert | Severity | Condition |
|-------|----------|-----------|
| HighAPIErrorRate | critical | Error rate > 5% for 5 min |
| HighAPILatency | warning | p95 latency > 2s for 5 min |
| APIDown | critical | Service unreachable for 1 min |
| HighInferenceLatency | warning | p95 inference > 1s for 5 min |
| ModelInferenceErrorRate | critical | Inference errors > 2% for 3 min |
| ModelNotLoaded | critical | Model not loaded for 2 min |
| LowCacheHitRatio | warning | Cache hit ratio < 30% for 10 min |
| HighCPUUsage | warning | CPU > 80% for 5 min |
| CriticalCPUUsage | critical | CPU > 95% for 2 min |
| HighMemoryUsage | warning | Memory > 85% for 5 min |
| CriticalMemoryUsage | critical | Memory > 95% for 2 min |
| HighDiskUsage | warning | Disk > 85% for 10 min |
| CriticalDiskUsage | critical | Disk > 95% for 5 min |

## Configuring Notifications

Edit `monitoring/alertmanager.yml` to set up your notification channels:

```yaml
receivers:
  - name: 'critical-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts-critical'
    email_configs:
      - to: 'oncall@yourcompany.com'
        smarthost: 'smtp.yourcompany.com:587'
        from: 'alerts@yourcompany.com'
        auth_username: 'alerts@yourcompany.com'
        auth_password: 'YOUR_PASSWORD'
```

## Grafana Dashboards

The **FlavorSnap Overview** dashboard is auto-provisioned at startup and includes:

- HTTP request rate and latency (p50/p95) per endpoint
- Error rate by status code
- Active request gauge
- Model inference latency and predictions per food class
- Cache hit/miss rate and hit ratio gauge
- CPU, memory, and disk usage time series

Access Grafana at `http://localhost:3001` (default credentials: `admin` / `admin123`).

## Log Aggregation

Logs are shipped via Filebeat → Logstash → Elasticsearch and can be explored in Kibana at `http://localhost:5601`.

Index pattern: `flavorsnap-logs-*`

All Python services emit structured JSON logs. Key fields:

| Field | Description |
|-------|-------------|
| `log_level` | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `service` | Service name (e.g. `flavorsnap-nextjs`) |
| `event_type` | `api_request`, `api_response`, `error_with_traceback`, etc. |
| `log_message` | Human-readable message |
| `@timestamp` | ISO8601 timestamp |

## Performance Profiler

The built-in profiler (`src/monitoring/profiler.py`) records timing samples for named spans and exposes aggregated statistics (p50, p95, p99, mean, max) at `GET /monitoring/profiler`.

```python
from src.monitoring.profiler import get_profiler

profiler = get_profiler()

# Context manager
with profiler.span("my_operation"):
    do_work()

# Decorator
@profiler.profile("image_preprocessing")
def preprocess(image):
    ...
```

## Adding Custom Business Metrics

```python
from src.monitoring.metrics_collector import get_metrics_collector
from prometheus_client import Counter

# Define a custom counter
MY_COUNTER = Counter("flavorsnap_my_event_total", "Description", ["label"])

# Record it
MY_COUNTER.labels(label="value").inc()

# Or use the collector helpers
collector = get_metrics_collector()
collector.record_inference(duration_seconds=0.05, predicted_class="Akara", confidence=0.92)
```
