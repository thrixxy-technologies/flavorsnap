# Advanced Configuration Management for FlavorSnap

This directory contains the comprehensive configuration management system for FlavorSnap, providing advanced features including environment-specific configurations, secrets management, hot reloading, validation, version control, security implementation, and monitoring integration.

## Overview

The configuration management system is designed to provide enterprise-grade configuration handling with the following key features:

- **Environment-Specific Configurations**: Separate configurations for development, staging, and production
- **Secrets Management**: Encrypted storage and rotation of sensitive data
- **Hot Reloading**: Automatic configuration updates without service restart
- **Configuration Validation**: Schema validation and best practices checking
- **Version Control**: Track and rollback configuration changes
- **Security Implementation**: Access control and audit logging
- **Monitoring Integration**: Real-time metrics and health checks
- **Kubernetes Integration**: Native Kubernetes secrets and ConfigMaps support

## Architecture

### Core Components

#### 1. Configuration Manager (`ml-model-api/config_manager.py`)
Advanced configuration manager with validation, hot reloading, and monitoring.

**Features:**
- Pydantic-based validation with custom schemas
- Hot reloading with file system watching
- Version control with change tracking
- Prometheus metrics integration
- Thread-safe operations with locking
- Environment variable substitution
- Configuration export/import

**Usage:**
```python
from config_manager import get_config, set_config, reload_config

# Get configuration value
debug_mode = get_config('app.debug', False)

# Set configuration value
set_config('app.debug', True)

# Reload configuration
reload_config()
```

#### 2. Secrets Manager (`ml-model-api/secrets_manager.py`)
Comprehensive secrets management with encryption and rotation.

**Features:**
- AES-256 encryption with PBKDF2 key derivation
- Automatic secret rotation with configurable policies
- Redis caching for performance
- AWS Secrets Manager integration
- Audit logging for all operations
- Support for multiple secret types
- Backup and restore functionality

**Secret Types:**
- Password
- API Key
- Token
- Certificate
- SSH Key
- Database URL
- Encryption Key
- Custom

**Usage:**
```python
from secrets_manager import get_secret, create_secret, rotate_secret

# Get secret
api_key = get_secret('my_api_key')

# Create secret
create_secret('new_secret', 'secret_value', SecretType.API_KEY)

# Rotate secret
rotate_secret('my_api_key')
```

#### 3. Configuration Validator (`scripts/config/config-validator.py`)
Multi-validator configuration validation tool.

**Validators:**
- JSON Schema
- Cerberus
- Pydantic
- Custom business rules

**Usage:**
```bash
# Validate single file
python config-validator.py config/environments/production.yaml --validator jsonschema

# Validate directory
python config-validator.py config/environments/ --pattern "*.yaml" --validator all

# Generate report
python config-validator.py config/environments/ --output validation-report.json
```

#### 4. Configuration Migrator (`scripts/config/config-migrator.py`)
Configuration migration between environments and versions.

**Features:**
- Rule-based transformations
- Environment-specific mappings
- Configuration comparison
- Backup creation
- Validation after migration

**Usage:**
```bash
# Migrate from dev to staging
python config-migrator.py migrate \
    --source config/environments/development.yaml \
    --target config/environments/staging.yaml \
    --source-env development \
    --target-env staging

# Compare configurations
python config-migrator.py compare \
    --source config/environments/staging.yaml \
    --target config/environments/production.yaml
```

#### 5. Deployment Script (`scripts/config/deploy-config.sh`)
Automated deployment of configuration management infrastructure.

**Features:**
- Kubernetes deployment
- Secrets creation
- RBAC setup
- Monitoring integration
- Health checks
- Scaling support

**Usage:**
```bash
# Deploy complete system
./deploy-config.sh deploy

# Check status
./deploy-config.sh status

# Scale components
./deploy-config.sh scale config-manager 3
```

## Configuration Structure

### Environment-Specific Configurations

#### Development (`config/environments/development.yaml`)
```yaml
app:
  name: "FlavorSnap"
  version: "2.0.0"
  environment: "development"
  debug: true
  hot_reload: true
  log_level: "DEBUG"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  reload: true

database:
  host: "localhost"
  port: 5432
  name: "flavorsnap_dev"
  username: "postgres"
  password: "postgres"
  pool_size: 5
  echo: true
```

#### Staging (`config/environments/staging.yaml`)
```yaml
app:
  name: "FlavorSnap"
  version: "2.0.0"
  environment: "staging"
  debug: true
  hot_reload: false
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 2
  reload: false

database:
  host: "${DB_HOST}"
  port: "${DB_PORT:5432}"
  name: "${DB_NAME}"
  username: "${DB_USERNAME}"
  password: "${DB_PASSWORD}"
  pool_size: 10
  echo: false
```

#### Production (`config/environments/production.yaml`)
```yaml
app:
  name: "FlavorSnap"
  version: "2.0.0"
  environment: "production"
  debug: false
  hot_reload: false
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  reload: false

database:
  host: "${DB_HOST}"
  port: "${DB_PORT:5432}"
  name: "${DB_NAME}"
  username: "${DB_USERNAME}"
  password: "${DB_PASSWORD}"
  pool_size: 20
  echo: false
```

## Environment Variables

### Required Variables

#### Base Configuration
```bash
FLAVORSNAP_ENV=production
CONFIG_ENCRYPTION_KEY=base64_encoded_32_byte_key
```

#### Database
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flavorsnap
DB_USERNAME=flavorsnap
DB_PASSWORD=secure_password
```

#### Security
```bash
JWT_SECRET=secure_jwt_secret_at_least_32_chars
ENCRYPTION_KEY=base64_encoded_encryption_key
```

#### External Services
```bash
OPENAI_API_KEY=your_openai_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

#### Monitoring
```bash
DATADOG_API_KEY=your_datadog_api_key
DATADOG_APP_KEY=your_datadog_app_key
SENTRY_DSN=your_sentry_dsn
```

### Optional Variables

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# AWS
BACKUP_BUCKET=flavorsnap-backups
CLOUDFRONT_DOMAIN=cdn.flavorsnap.com

# Feature Flags
FEATURE_ML_CLASSIFICATION=true
FEATURE_BLOCKCHAIN_INTEGRATION=true
FEATURE_ANALYTICS=true
```

## Security Implementation

### Encryption

#### Configuration Encryption
- **Algorithm**: AES-256-CBC
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Salt**: 16 bytes per encryption
- **IV**: 16 bytes per encryption
- **Checksum**: SHA-256 for integrity verification

#### Secrets Encryption
- **Master Key**: 32 bytes, stored in environment variable
- **Per-Secret Keys**: Derived from master key
- **Rotation**: Configurable policies (daily, weekly, monthly)
- **Backup**: Encrypted backups with versioning

### Access Control

#### RBAC Configuration
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: config-manager-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
```

#### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: config-network-policy
spec:
  podSelector:
    matchLabels:
      app: flavorsnap-config
  policyTypes:
  - Ingress
  - Egress
```

### Audit Logging

#### Configuration Changes
- Timestamp
- User identification
- IP address
- Action performed
- Success/failure status
- Detailed description

#### Secret Operations
- All access attempts
- Creation, update, deletion
- Rotation events
- Failed authentication attempts

## Monitoring Integration

### Prometheus Metrics

#### Configuration Metrics
```prometheus
# Configuration loads
config_loads_total{environment="production", status="success"}

# Configuration changes
config_changes_total{change_type="update", environment="production"}

# Validation errors
config_validation_errors_total{environment="production", validation_type="pydantic"}

# Reload duration
config_reload_duration_seconds{environment="production"}
```

#### Secrets Metrics
```prometheus
# Total secrets
secrets_total{environment="production", status="active", type="api_key"}

# Secret operations
secret_operations_total{operation="create", environment="production", success="true"}

# Rotations
secret_rotations_total{environment="production", success="true"}

# Access patterns
secret_access_total{environment="production", secret_type="password"}
```

### Health Checks

#### Configuration Manager Health
```python
def health_check() -> Dict[str, Any]:
    return {
        'config_loaded': True,
        'validation_passed': True,
        'hot_reload_working': True,
        'secrets_available': True,
        'environment_vars_resolved': True,
        'healthy': True
    }
```

#### Secrets Manager Health
```python
def health_check() -> Dict[str, Any]:
    return {
        'storage_accessible': True,
        'encryption_working': True,
        'cache_working': True,
        'rotation_enabled': True,
        'aws_sync_working': True,
        'redis_connected': True,
        'healthy': True
    }
```

## Best Practices

### Configuration Management

1. **Environment Separation**
   - Use separate configs for each environment
   - Never share production configs with development
   - Validate environment-specific requirements

2. **Secret Management**
   - Never commit secrets to version control
   - Use different secrets for each environment
   - Implement regular rotation policies
   - Monitor secret access patterns

3. **Validation**
   - Validate configurations before deployment
   - Use multiple validators for comprehensive checking
   - Implement strict validation for production
   - Monitor validation failures

4. **Version Control**
   - Track all configuration changes
   - Use semantic versioning
   - Create meaningful commit messages
   - Implement rollback procedures

### Security Practices

1. **Encryption**
   - Use strong encryption algorithms
   - Implement proper key management
   - Rotate encryption keys regularly
   - Store keys securely

2. **Access Control**
   - Implement principle of least privilege
   - Use RBAC for Kubernetes resources
   - Audit all access attempts
   - Regularly review permissions

3. **Network Security**
   - Implement network policies
   - Use TLS for all communications
   - Restrict access to configuration endpoints
   - Monitor network traffic

### Performance Optimization

1. **Caching**
   - Cache frequently accessed configurations
   - Use Redis for distributed caching
   - Implement cache invalidation
   - Monitor cache hit rates

2. **Hot Reloading**
   - Use file system watching efficiently
   - Implement debouncing for rapid changes
   - Validate before applying changes
   - Monitor reload performance

3. **Resource Management**
   - Set appropriate resource limits
   - Implement auto-scaling
   - Monitor resource usage
   - Optimize memory usage

## Troubleshooting

### Common Issues

#### Configuration Loading Failures
```bash
# Check configuration syntax
python config-validator.py config/environments/production.yaml

# Check environment variables
env | grep FLAVORSNAP

# Check file permissions
ls -la config/environments/
```

#### Secrets Management Issues
```bash
# Check secrets manager health
curl http://secrets-manager:8080/health

# Check Redis connection
redis-cli -h redis -p 6379 ping

# Check encryption key
echo $CONFIG_ENCRYPTION_KEY | base64 -d | wc -c
```

#### Hot Reloading Issues
```bash
# Check file watcher status
kubectl logs deployment/config-manager -n flavorsnap-config

# Check configuration file permissions
ls -la config/environments/

# Test manual reload
curl -X POST http://config-manager:8080/reload
```

### Debug Commands

#### Configuration Debugging
```bash
# Export configuration without secrets
curl http://config-manager:8080/config?include_secrets=false

# Get configuration status
curl http://config-manager:8080/status

# Get validation results
curl http://config-manager:8080/validate
```

#### Secrets Debugging
```bash
# List secrets (without values)
curl http://secrets-manager:8080/secrets

# Get audit log
curl http://secrets-manager:8080/audit

# Check rotation status
curl http://secrets-manager:8080/rotation-status
```

## Migration Guide

### From Legacy Configuration

1. **Backup Current Configuration**
```bash
cp -r config/ config-backup-$(date +%Y%m%d)
```

2. **Migrate Environment Variables**
```bash
# Export current variables
env | grep FLAVORSNAP > current-env.txt

# Create new environment file
python config-migrator.py migrate \
    --source legacy-config.json \
    --target config/environments/production.yaml \
    --source-env legacy \
    --target-env production
```

3. **Validate New Configuration**
```bash
python config-validator.py config/environments/ --validator all
```

4. **Deploy New System**
```bash
./deploy-config.sh deploy
```

### Environment Promotion

1. **Development to Staging**
```bash
python config-migrator.py migrate \
    --source config/environments/development.yaml \
    --target config/environments/staging.yaml \
    --source-env development \
    --target-env staging \
    --rule dev_to_staging
```

2. **Staging to Production**
```bash
python config-migrator.py migrate \
    --source config/environments/staging.yaml \
    --target config/environments/production.yaml \
    --source-env staging \
    --target-env production \
    --rule staging_to_production
```

## Integration Examples

### Application Integration

#### Python Application
```python
from config_manager import config_manager
from secrets_manager import secrets_manager

# Initialize configuration
config_manager.enable_hot_reload()

# Use configuration
database_url = f"postgresql://{config_manager.get('database.username')}:{secrets_manager.get_secret('database.password')}@{config_manager.get('database.host')}:{config_manager.get('database.port')}/{config_manager.get('database.name')}"

# Monitor configuration changes
def on_config_change(old_config, new_config):
    print("Configuration changed!")
    # Reinitialize components if needed

config_manager.reload_callbacks.append(on_config_change)
```

#### Docker Integration
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy configuration
COPY config/ /app/config/
COPY ml-model-api/config_manager.py /app/
COPY ml-model-api/secrets_manager.py /app/

# Set environment variables
ENV FLAVORSNAP_ENV=production
ENV CONFIG_ENCRYPTION_KEY=${CONFIG_ENCRYPTION_KEY}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app.py"]
```

#### Kubernetes Integration
```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flavorsnap-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: flavorsnap/app:latest
        env:
        - name: FLAVORSNAP_ENV
          value: "production"
        - name: CONFIG_ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: master-encryption-key
              key: key
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config-volume
        configMap:
          name: app-config
```

## Performance Considerations

### Configuration Loading
- **Lazy Loading**: Load configurations only when needed
- **Caching**: Cache parsed configurations in memory
- **Validation**: Validate once, cache results
- **Compression**: Use compressed storage for large configs

### Secrets Management
- **Encryption**: Use hardware acceleration if available
- **Caching**: Cache decrypted secrets with TTL
- **Batching**: Batch secret operations when possible
- **Connection Pooling**: Reuse database connections

### Hot Reloading
- **Debouncing**: Prevent rapid reloads
- **Validation**: Validate before applying changes
- **Rollback**: Implement automatic rollback on failure
- **Monitoring**: Track reload performance

## Maintenance

### Regular Tasks

#### Daily
- Check configuration validation results
- Monitor secret rotation status
- Review audit logs for anomalies
- Check system health metrics

#### Weekly
- Review configuration changes
- Update validation rules
- Check backup integrity
- Review access logs

#### Monthly
- Rotate encryption keys
- Update security policies
- Review and update documentation
- Performance optimization review

#### Quarterly
- Security audit
- Disaster recovery testing
- Architecture review
- Capacity planning

### Backup Procedures

#### Configuration Backup
```bash
# Create backup
kubectl get configmap -n flavorsnap-config -o yaml > config-backup.yaml

# Backup to S3
aws s3 cp config-backup.yaml s3://flavorsnap-backups/config/
```

#### Secrets Backup
```bash
# Create encrypted backup
python -c "
from secrets_manager import secrets_manager
import json
backup = secrets_manager.list_secrets(include_values=False)
with open('secrets-backup.json', 'w') as f:
    json.dump(backup, f, indent=2, default=str)
"

# Upload to secure storage
aws s3 cp secrets-backup.json s3://flavorsnap-backups/secrets/ --sse
```

## API Reference

### Configuration Manager API

#### Endpoints
- `GET /health` - Health check
- `GET /status` - Configuration status
- `GET /config` - Get configuration
- `POST /reload` - Reload configuration
- `GET /validate` - Validate configuration
- `GET /versions` - Get version history
- `POST /rollback/{version}` - Rollback to version

#### Example Usage
```bash
# Get configuration
curl http://config-manager:8080/config

# Reload configuration
curl -X POST http://config-manager:8080/reload

# Get status
curl http://config-manager:8080/status
```

### Secrets Manager API

#### Endpoints
- `GET /health` - Health check
- `GET /secrets` - List secrets
- `GET /secret/{name}` - Get secret value
- `POST /secret` - Create secret
- `PUT /secret/{name}` - Update secret
- `DELETE /secret/{name}` - Delete secret
- `POST /rotate/{name}` - Rotate secret
- `GET /audit` - Get audit log

#### Example Usage
```bash
# List secrets
curl http://secrets-manager:8080/secrets

# Get secret value
curl http://secrets-manager:8080/secret/my_api_key

# Create secret
curl -X POST http://secrets-manager:8080/secret \
  -H "Content-Type: application/json" \
  -d '{"name": "new_secret", "value": "secret_value", "type": "api_key"}'
```

## Testing

### Unit Tests
```bash
# Run configuration manager tests
python -m pytest tests/test_config_manager.py

# Run secrets manager tests
python -m pytest tests/test_secrets_manager.py

# Run validator tests
python -m pytest tests/test_config_validator.py
```

### Integration Tests
```bash
# Run end-to-end tests
python -m pytest tests/integration/

# Run performance tests
python -m pytest tests/performance/

# Run security tests
python -m pytest tests/security/
```

### Load Testing
```bash
# Configuration loading performance
python scripts/load-test-config.py --concurrency 100 --duration 60s

# Secrets access performance
python scripts/load-test-secrets.py --concurrency 50 --duration 60s
```

## Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/thrixxy-technologies/flavorsnap.git
cd flavorsnap

# Install dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run linting
flake8 scripts/config/
black scripts/config/
```

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Write unit tests
- Update documentation

### Pull Request Process
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit pull request
6. Code review
7. Merge to main

## Support

### Documentation
- This README
- API documentation
- Architecture diagrams
- Troubleshooting guide

### Community
- GitHub issues
- Discussion forums
- Slack channel
- Stack Overflow tag

### Contact
- Maintainers: config-team@flavorsnap.com
- Security: security@flavorsnap.com
- Support: support@flavorsnap.com

---

For more information, questions, or support, please refer to the main FlavorSnap documentation or create an issue in the repository.
