# FlavorSnap Advanced Deployment System Guide

## Overview

This guide covers the advanced deployment system for FlavorSnap, featuring CI/CD pipeline integration, blue-green deployment, automatic rollback, health checks, deployment monitoring, zero-downtime deployment, and environment management.

## Architecture

### Components

1. **Deployment Manager** (`ml-model-api/deployment_manager.py`)
   - Blue-green deployment orchestration
   - Automatic rollback capabilities
   - Health check management
   - Deployment monitoring

2. **CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
   - Automated testing and security scanning
   - Docker image building and registry management
   - Staging and production deployment
   - Automatic rollback on failure

3. **Container Orchestration** (`docker-compose.yml`)
   - Multi-environment support (staging/production)
   - Blue-green deployment containers
   - Database, cache, and monitoring services
   - Load balancing with nginx

4. **Monitoring Stack**
   - Prometheus metrics collection
   - Grafana dashboards and alerting
   - Health checks and readiness probes
   - Performance monitoring

5. **Environment Management** (`scripts/`)
   - Automated environment setup
   - Deployment and rollback scripts
   - Configuration management

## Quick Start

### 1. Environment Setup

```bash
# Set up staging environment
./scripts/environment-setup.sh --environment staging

# Set up production environment
./scripts/environment-setup.sh --environment production
```

### 2. Start Services

```bash
# Development/Staging
./start-dev.sh

# Production
./start-prod.sh
```

### 3. Deploy New Version

```bash
# Deploy to staging
./scripts/deploy.sh --environment staging --tag v1.2.0

# Deploy to production with zero-downtime
./scripts/deploy.sh --environment production --tag v1.2.0
```

### 4. Rollback if Needed

```bash
# Rollback staging
./scripts/rollback.sh --environment staging

# Rollback production
./scripts/rollback.sh --environment production --reason "Performance issues"
```

## Detailed Configuration

### Environment Variables

Key environment variables for deployment:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://flavorsnap:password@postgres:5432/flavorsnap

# Redis
REDIS_PASSWORD=your_redis_password
REDIS_URL=redis://:password@redis:6379/0

# Application
FLASK_ENV=production
SECRET_KEY=your_secret_key
APP_HOST=0.0.0.0
APP_PORT=5000

# Deployment
DEPLOYMENT_ZERO_DOWNTIME=true
DEPLOYMENT_HEALTH_CHECK_INTERVAL=30
DEPLOYMENT_HEALTH_CHECK_TIMEOUT=10
DEPLOYMENT_ROLLBACK_THRESHOLD=0.5

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_password
METRICS_ENDPOINT=https://your-metrics.com/api/metrics
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### Blue-Green Deployment

The system uses blue-green deployment strategy:

- **Blue Environment**: Current production version
- **Green Environment**: New version being deployed
- **Traffic Switching**: Seamless switch between environments
- **Rollback**: Instant rollback to previous version

#### Deployment Flow

1. Build and test new version
2. Deploy to inactive environment (green if blue is active)
3. Run health checks on new deployment
4. Switch traffic to new environment
5. Scale down old environment
6. Monitor for issues

#### Automatic Rollback

Automatic rollback triggers:
- Health check failures
- Error rate > 50%
- Response time > 2 seconds
- Memory usage > 90%
- Disk space < 10%

### Health Checks

#### Enhanced Health Check Endpoint

`GET /health` provides comprehensive health information:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": "connected",
    "cache": "connected",
    "queue": "active",
    "disk_space": {
      "free_percent": 85.2,
      "free_gb": 42.1,
      "total_gb": 256.0
    },
    "memory": {
      "usage_percent": 45.3,
      "available_gb": 8.7,
      "total_gb": 16.0
    }
  },
  "version": "1.2.0",
  "environment": "production",
  "deployment_color": "green",
  "deployment_id": "deploy-1642248600"
}
```

#### Kubernetes Probes

- **Liveness Probe**: `GET /deployment/live`
- **Readiness Probe**: `GET /deployment/ready`
- **Startup Probe**: `GET /health`

### Monitoring and Alerting

#### Prometheus Metrics

Key metrics available:

- `flask_http_request_duration_seconds`
- `flask_http_request_total`
- `flask_http_request_exceptions_total`
- `flask_database_connections`
- `cache_hits_total`, `cache_misses_total`
- `queue_pending_tasks`, `queue_running_tasks`
- `process_resident_memory_bytes`

#### Grafana Dashboards

Available dashboards:
- Application Performance
- Infrastructure Metrics
- Queue Monitoring
- Deployment Status

#### Alerting Rules

Critical alerts:
- FlavorSnapDown
- HighErrorRate
- QueueBacklog
- DatabaseConnectionFailure
- MemoryLeakSuspected

### CI/CD Pipeline

#### Pipeline Stages

1. **Code Quality**
   - Linting (flake8, black, mypy)
   - Unit tests with coverage
   - Security scanning (Bandit, Trivy)

2. **Build**
   - Docker image building
   - Registry push
   - Image tagging

3. **Deploy to Staging**
   - Kubernetes deployment
   - Health checks
   - Integration tests

4. **Deploy to Production**
   - Blue-green deployment
   - Traffic switching
   - Post-deployment verification

5. **Monitoring**
   - Slack notifications
   - Metrics collection
   - Rollback on failure

#### Pipeline Triggers

- **Push to develop**: Deploy to staging
- **Push to main**: Deploy to production
- **Pull requests**: Run tests only
- **Release**: Full deployment pipeline

## Operations

### Deployment Commands

#### Manual Deployment

```bash
# Basic deployment
./scripts/deploy.sh

# With specific tag
./scripts/deploy.sh --tag v1.2.0

# Production deployment
./scripts/deploy.sh --environment production --tag v1.2.0

# Disable zero-downtime (maintenance mode)
./scripts/deploy.sh --no-zero-downtime --tag v1.2.0
```

#### Rollback Commands

```bash
# Rollback to previous version
./scripts/rollback.sh

# Rollback with reason
./scripts/rollback.sh --reason "Performance degradation"

# Rollback specific deployment
./scripts/rollback.sh --deployment-id deploy-1642248600
```

#### Status Monitoring

```bash
# Check deployment status
curl http://localhost/deployment/status

# Get metrics
curl http://localhost/deployment/metrics

# Health check
curl http://localhost/health
```

### Container Management

#### Docker Compose

```bash
# Start all services
docker-compose --profile full up -d

# Start specific services
docker-compose --profile blue,monitoring up -d

# View logs
docker-compose logs -f flavorsnap-blue

# Scale services
docker-compose up -d --scale flavorsnap-blue=3
```

#### Kubernetes

```bash
# Get deployment status
kubectl get deployments -n flavorsnap-prod

# View pods
kubectl get pods -n flavorsnap-prod -l color=green

# Check rollout status
kubectl rollout status deployment/flavorsnap-green -n flavorsnap-prod

# View logs
kubectl logs -f deployment/flavorsnap-green -n flavorsnap-prod
```

### Troubleshooting

#### Common Issues

1. **Health Check Failures**
   ```bash
   # Check pod status
   kubectl get pods -n flavorsnap-prod
   
   # View detailed health check
   kubectl describe pod <pod-name> -n flavorsnap-prod
   
   # Check logs
   kubectl logs <pod-name> -n flavorsnap-prod
   ```

2. **Deployment Stuck**
   ```bash
   # Check rollout status
   kubectl rollout status deployment/flavorsnap-green -n flavorsnap-prod
   
   # Cancel and retry
   kubectl rollout undo deployment/flavorsnap-green -n flavorsnap-prod
   ```

3. **High Memory Usage**
   ```bash
   # Check resource usage
   kubectl top pods -n flavorsnap-prod
   
   # Scale deployment
   kubectl scale deployment flavorsnap-green --replicas=3 -n flavorsnap-prod
   ```

#### Debug Mode

Enable debug logging:

```bash
# Set debug environment variable
export FLASK_ENV=development

# Or update deployment
kubectl set env deployment/flavorsnap-green FLASK_ENV=development -n flavorsnap-prod
```

## Security

### Security Measures

1. **Container Security**
   - Non-root user execution
   - Minimal base images
   - Security scanning in CI/CD
   - Resource limits

2. **Network Security**
   - Network policies in Kubernetes
   - Internal service communication
   - TLS encryption
   - Firewall rules

3. **Secrets Management**
   - Kubernetes secrets
   - Environment variable encryption
   - No secrets in code
   - Regular rotation

4. **Access Control**
   - RBAC in Kubernetes
   - Service accounts
   - API authentication
   - Audit logging

### Security Scanning

The CI/CD pipeline includes:
- **Bandit**: Python security linter
- **Trivy**: Container vulnerability scanner
- **SARIF**: Security findings report

## Performance

### Performance Optimization

1. **Application Level**
   - Connection pooling
   - Caching strategies
   - Queue management
   - Async processing

2. **Infrastructure Level**
   - Horizontal pod autoscaling
   - Resource limits
   - Load balancing
   - CDN integration

3. **Database Level**
   - Connection pooling
   - Query optimization
   - Index management
   - Backup strategies

### Performance Monitoring

Key performance indicators:
- Response time (p95 < 2s)
- Error rate (< 1%)
- Throughput (> 1000 req/s)
- Memory usage (< 80%)
- CPU usage (< 70%)

## Backup and Recovery

### Database Backup

```bash
# Create backup
kubectl exec -n flavorsnap-prod deployment/postgres -- pg_dump -U flavorsnap flavorsnap > backup.sql

# Restore backup
kubectl exec -i -n flavorsnap-prod deployment/postgres -- psql -U flavorsnap -d flavorsnap < backup.sql
```

### Disaster Recovery

1. **Data Recovery**
   - Database snapshots
   - File system backups
   - Configuration backups

2. **Service Recovery**
   - Automatic restarts
   - Health checks
   - Graceful degradation

3. **Infrastructure Recovery**
   - Multi-zone deployment
   - Failover procedures
   - Recovery time objectives

## Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Health check monitoring
   - Log review
   - Performance metrics review

2. **Weekly**
   - Security updates
   - Dependency updates
   - Backup verification

3. **Monthly**
   - Performance tuning
   - Capacity planning
   - Security audit

### Maintenance Windows

- **Staging**: Any time (no impact)
- **Production**: Scheduled maintenance windows
- **Zero-downtime**: No maintenance window required

## Best Practices

### Development

1. Use feature branches
2. Write comprehensive tests
3. Follow security guidelines
4. Document changes

### Deployment

1. Test in staging first
2. Use blue-green deployment
3. Monitor health checks
4. Have rollback plan

### Operations

1. Monitor all systems
2. Respond to alerts promptly
3. Document incidents
4. Continuously improve

## Support

### Getting Help

1. **Documentation**: This guide and inline comments
2. **Logs**: Application and system logs
3. **Monitoring**: Grafana dashboards and Prometheus metrics
4. **Alerts**: Slack notifications and email alerts

### Escalation

1. **Level 1**: Development team
2. **Level 2**: Operations team
3. **Level 3**: System administrators

### Contact Information

- **Development Team**: dev-team@company.com
- **Operations Team**: ops-team@company.com
- **Emergency**: emergency@company.com

## Appendix

### Configuration Files

- `ml-model-api/deployment_manager.py`: Deployment orchestration
- `docker-compose.yml`: Service orchestration
- `.github/workflows/ci-cd.yml`: CI/CD pipeline
- `nginx/default.conf`: Load balancer configuration
- `monitoring/prometheus.yml`: Metrics configuration

### Environment Scripts

- `scripts/deploy.sh`: Deployment script
- `scripts/rollback.sh`: Rollback script
- `scripts/environment-setup.sh`: Environment setup

### Monitoring Configuration

- `monitoring/flavorsnap_rules.yml`: Alerting rules
- `monitoring/grafana/`: Dashboard configurations

This deployment system provides enterprise-grade reliability, scalability, and maintainability for the FlavorSnap application.
