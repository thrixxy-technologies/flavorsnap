# Advanced Queue Management System for FlavorSnap

## Overview

This document describes the comprehensive queue management system implemented for FlavorSnap ML API. The system provides advanced features including priority queues, dead letter queues, monitoring, caching, persistence, and failure recovery mechanisms.

## Architecture

The queue management system consists of four main components:

1. **Batch Processor** (`batch_processor.py`) - Core queue processing with priority handling
2. **Cache Manager** (`cache_manager.py`) - Intelligent caching for queue operations and results
3. **Monitoring** (`monitoring.py`) - Comprehensive monitoring, analytics, and alerting
4. **Persistence** (`persistence.py`) - Durable storage and recovery mechanisms

## Features

### 1. Priority Queue Implementation

- **Priority Levels**: CRITICAL, HIGH, NORMAL, LOW
- **Automatic Ordering**: Tasks are processed based on priority and submission time
- **Dynamic Priority**: Tasks can be submitted with different priority levels
- **Queue Size Limits**: Configurable maximum queue size to prevent memory issues

### 2. Dead Letter Queue Handling

- **Failed Task Capture**: Tasks that fail after maximum retries are moved to dead letter queue
- **Retry Mechanism**: Failed tasks can be retried manually or automatically
- **Error Tracking**: Detailed error messages and failure reasons are preserved
- **Cleanup**: Automatic cleanup of old dead letter entries

### 3. Queue Monitoring

- **Real-time Metrics**: Queue size, processing time, throughput, error rates
- **Performance Analytics**: Detailed analytics with percentiles and trends
- **Alert System**: Configurable alerts for queue health issues
- **Dashboard Integration**: Ready-to-use dashboard data provider

### 4. Load Balancing

- **Worker Distribution**: Intelligent distribution of tasks across workers
- **Load Awareness**: Workers with lower load receive new tasks
- **Health Monitoring**: Worker health checks and automatic failover
- **Round-robin Fallback**: Fallback to round-robin distribution when needed

### 5. Queue Analytics

- **Performance Metrics**: Processing time, throughput, success rates
- **Historical Data**: Configurable retention of historical metrics
- **Trend Analysis**: Performance trends and capacity planning
- **Export Capabilities**: Export metrics in JSON or Prometheus format

### 6. Failure Recovery

- **Orphaned Task Recovery**: Automatic recovery of tasks stuck in running state
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Persistence Recovery**: Recovery from database failures during restart
- **Graceful Degradation**: System continues operating during partial failures

### 7. Performance Optimization

- **Caching Layer**: Multi-level caching for frequently accessed data
- **Connection Pooling**: Optimized database connections
- **Memory Management**: Efficient memory usage with configurable limits
- **Background Processing**: Non-blocking background operations

## Configuration

### Queue Configuration

```yaml
queue:
  max_workers: 4                    # Number of worker threads
  max_size: 10000                   # Maximum queue size
  persistence:
    backend: "sqlite"               # Storage backend (sqlite/file)
    db_path: "queue_persistence.db"
    recovery_enabled: true
    cleanup_interval: 3600
  monitoring:
    interval: 30                   # Monitoring interval in seconds
    max_history: 10000
    enable_alerts: true
  load_balancing:
    strategy: "round_robin"
    worker_health_check: true
  dead_letter_queue:
    max_size: 10000
    retry_delay: 60
    max_retries: 3
```

### Cache Configuration

```yaml
cache:
  type: "redis"                     # Cache type (redis/memory)
  host: "localhost"
  port: 6379
  password: ""
  db: 0
  ttl: 3600
  default_cache_size: 100           # MB
  result_cache_size: 50            # MB
  queue_cache_size: 200            # MB
  cleanup_interval: 300
```

## API Endpoints

### Queue Management

- `GET /queue/status` - Get queue status and statistics
- `GET /queue/task/<task_id>` - Get status of a specific task
- `POST /queue/task/<task_id>/cancel` - Cancel a pending task
- `POST /queue/retry/<task_id>` - Retry a failed task
- `GET /queue/monitoring` - Get comprehensive monitoring data
- `GET /queue/analytics` - Get detailed queue analytics
- `GET /queue/export` - Export metrics in JSON or Prometheus format

### Enhanced Prediction

- `POST /predict` - Enhanced prediction endpoint with queue support
  - Parameters:
    - `use_queue=true` - Submit to queue instead of direct processing
    - `priority=high|normal|low|critical` - Set task priority

## Usage Examples

### Direct Processing

```bash
curl -X POST -F "image=@food.jpg" http://localhost:5000/predict
```

### Queue Processing with Priority

```bash
curl -X POST \
  -F "image=@food.jpg" \
  -F "use_queue=true" \
  -F "priority=high" \
  http://localhost:5000/predict
```

Response:
```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "queued",
  "priority": "high",
  "message": "Task submitted to queue for processing"
}
```

### Check Task Status

```bash
curl http://localhost:5000/queue/task/12345678-1234-1234-1234-123456789012
```

### Get Queue Statistics

```bash
curl http://localhost:5000/queue/status
```

## Monitoring and Alerting

### Default Alerts

The system includes several default alerts:

1. **High Queue Size** - Warning when queue exceeds 1000 tasks
2. **High Error Rate** - Error when error rate exceeds 10%
3. **Low Throughput** - Warning when throughput drops below 1 task/sec
4. **High Processing Time** - Warning when average processing time exceeds 30 seconds

### Custom Alerts

Custom alerts can be added by extending the alert system:

```python
from monitoring import Alert, AlertLevel, AlertManager

alert_manager = AlertManager()
custom_alert = Alert(
    name="custom_metric",
    level=AlertLevel.WARNING,
    condition="custom_metric >",
    threshold=100.0,
    message="Custom metric threshold exceeded"
)
alert_manager.add_alert(custom_alert)
```

### Metrics Export

Metrics can be exported in different formats:

```bash
# JSON format
curl http://localhost:5000/queue/export?format=json

# Prometheus format
curl http://localhost:5000/queue/export?format=prometheus
```

## Performance Considerations

### Scaling Guidelines

1. **Worker Threads**: Start with 2-4 workers per CPU core
2. **Queue Size**: Monitor queue size and adjust based on memory constraints
3. **Cache Size**: Allocate cache based on available memory and access patterns
4. **Persistence**: Use SQLite for development, consider PostgreSQL for production

### Optimization Tips

1. **Enable Caching**: Always enable result caching for repeated predictions
2. **Monitor Metrics**: Regularly review queue metrics to identify bottlenecks
3. **Adjust Priorities**: Use priority levels appropriately for critical tasks
4. **Batch Processing**: Submit multiple related tasks together when possible

## Troubleshooting

### Common Issues

1. **Queue Full Error**
   - Increase `max_size` in configuration
   - Monitor processing speed and worker utilization
   - Consider adding more workers

2. **High Memory Usage**
   - Reduce cache sizes in configuration
   - Enable automatic cleanup of old tasks
   - Monitor memory usage patterns

3. **Slow Processing**
   - Check worker thread count
   - Monitor database performance
   - Review task complexity and resource requirements

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
logging:
  level: "DEBUG"
```

### Health Checks

Monitor system health with built-in endpoints:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/queue/status
```

## Integration with Existing Systems

### Database Integration

The queue system integrates with the existing database configuration:

```python
from db_config import get_db_session

# Use existing database sessions for persistence
with get_db_session() as session:
    # Queue operations
    pass
```

### Configuration Integration

Queue configuration is integrated with the existing config management system:

```python
from config_manager import get_config_value

max_workers = get_config_value('queue.max_workers', 4)
```

### Logging Integration

All queue operations use the existing logging configuration:

```python
from logger_config import get_logger

logger = get_logger(__name__)
```

## Security Considerations

### Access Control

- Queue management endpoints should be protected in production
- Consider implementing authentication and authorization
- Rate limiting for queue submission endpoints

### Data Protection

- Sensitive task data is encrypted at rest in persistence
- Cache data respects existing security configurations
- Audit logging for all queue operations

## Future Enhancements

### Planned Features

1. **Distributed Queues**: Support for multi-node queue processing
2. **Advanced Scheduling**: Cron-like scheduling for periodic tasks
3. **Webhook Support**: Notifications for task completion
4. **GraphQL API**: GraphQL interface for queue operations
5. **Machine Learning**: ML-based priority optimization

### Extensibility

The system is designed for extensibility:

- Custom persistence backends
- Pluggable monitoring systems
- Custom task processors
- Additional cache implementations

## Testing

### Unit Tests

Run unit tests for individual components:

```bash
python -m pytest tests/test_batch_processor.py
python -m pytest tests/test_cache_manager.py
python -m pytest tests/test_monitoring.py
python -m pytest tests/test_persistence.py
```

### Integration Tests

Run integration tests:

```bash
python -m pytest tests/test_queue_integration.py
```

### Load Testing

Load testing with Locust or similar tools:

```bash
locust -f tests/locustfile.py --host=http://localhost:5000
```

## Deployment

### Production Deployment

1. **Environment Variables**: Set appropriate environment variables
2. **Resource Limits**: Configure memory and CPU limits
3. **Monitoring Setup**: Configure external monitoring systems
4. **Backup Strategy**: Implement backup for persistence data

### Docker Deployment

```dockerfile
FROM python:3.9-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "ml-model-api/app.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flavorsnap-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: flavorsnap-api
  template:
    metadata:
      labels:
        app: flavorsnap-api
    spec:
      containers:
      - name: api
        image: flavorsnap/api:latest
        ports:
        - containerPort: 5000
        env:
        - name: DB_HOST
          value: "postgres-service"
        - name: CACHE_HOST
          value: "redis-service"
```

## Support and Maintenance

### Monitoring

- Regular monitoring of queue metrics
- Alert thresholds should be reviewed periodically
- Performance trends should be analyzed monthly

### Maintenance

- Regular cleanup of old tasks and metrics
- Database maintenance and optimization
- Cache cleanup and memory management

### Updates

- System can be updated without losing queue state
- Configuration changes can be applied via reload endpoint
- Database schema updates should be tested thoroughly

## Conclusion

The advanced queue management system provides a robust, scalable, and feature-rich solution for handling ML model inference tasks in the FlavorSnap application. The system is designed to handle high loads, provide detailed monitoring, and ensure reliable operation with comprehensive failure recovery mechanisms.

For questions or support, refer to the code documentation or contact the development team.
