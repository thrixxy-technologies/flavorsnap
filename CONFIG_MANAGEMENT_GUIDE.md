# FlavorSnap Advanced Configuration Management Guide

## Overview

FlavorSnap implements a comprehensive configuration management system that provides:

- **Environment-specific configurations** - Separate configs for development, staging, and production
- **Configuration validation** - Schema-based validation with type checking and range validation
- **Hot configuration reloading** - Automatic detection and reloading of configuration changes
- **Configuration versioning** - Track changes with version history and metadata
- **Security for sensitive configs** - Encryption of sensitive fields like passwords and secret keys
- **Configuration monitoring** - Real-time monitoring and health checks
- **Configuration backup** - Automatic and manual backup functionality

## Architecture

### Core Components

1. **ConfigManager** (`config_manager.py`) - Main configuration manager
2. **ConfigValidator** - Schema-based validation system
3. **ConfigSecurity** - Encryption/decryption of sensitive data
4. **ConfigBackup** - Backup and restore functionality
5. **ConfigFileWatcher** - File system monitoring for hot reload
6. **DatabaseConfig** (`db_config.py`) - Database-specific configuration
7. **LoggingConfig** (`logger_config.py`) - Logging configuration management

## Configuration Files

### Base Configuration: `config.yaml`

```yaml
# FlavorSnap Configuration Management
# Version: 1.0.0
# Environment: development

app:
  name: "flavorsnap"
  version: "1.0.0"
  debug: true
  host: "0.0.0.0"
  port: 5000
  secret_key: "${APP_SECRET_KEY:dev-secret-key-change-in-production}"

database:
  type: "postgresql"
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
  name: "${DB_NAME:flavorsnap}"
  user: "${DB_USER:postgres}"
  password: "${DB_PASSWORD:password}"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600

ml_model:
  model_path: "${MODEL_PATH:./model.pth}"
  classes_file: "${CLASSES_FILE:./food_classes.txt}"
  input_size: [224, 224]
  batch_size: 32
  device: "${ML_DEVICE:cpu}"

logging:
  level: "${LOG_LEVEL:INFO}"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "${LOG_FILE:./logs/app.log}"
  max_bytes: 10485760  # 10MB
  backup_count: 5
  enable_console: true

security:
  jwt_secret_key: "${JWT_SECRET_KEY:jwt-secret-change-in-production}"
  jwt_expiration_hours: 24
  bcrypt_rounds: 12
  rate_limit:
    requests_per_minute: 60
    burst_size: 10

monitoring:
  enable_metrics: true
  metrics_port: 9090
  health_check_interval: 30
  performance_tracking: true

file_storage:
  upload_folder: "${UPLOAD_FOLDER:./uploads}"
  max_file_size: 16777216  # 16MB
  allowed_extensions: ["jpg", "jpeg", "png", "gif", "bmp"]
  auto_cleanup_days: 7

cache:
  type: "redis"
  host: "${CACHE_HOST:localhost}"
  port: "${CACHE_PORT:6379}"
  password: "${CACHE_PASSWORD:}"
  db: 0
  ttl: 3600

features:
  enable_hot_reload: true
  enable_config_validation: true
  enable_backup: true
  enable_versioning: true
```

### Environment-Specific Configurations

- **`config.production.yaml`** - Production environment overrides
- **`config.staging.yaml`** - Staging environment overrides  
- **`config.testing.yaml`** - Testing environment overrides

## Environment Variables

### Application Configuration

- `ENVIRONMENT` - Current environment (development/staging/production)
- `APP_SECRET_KEY` - Flask application secret key
- `CONFIG_ENCRYPTION_KEY` - Key for encrypting sensitive configuration values

### Database Configuration

- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password

### ML Model Configuration

- `MODEL_PATH` - Path to the ML model file
- `CLASSES_FILE` - Path to the classes file
- `ML_DEVICE` - Device for model inference (cpu/cuda)

### Logging Configuration

- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `LOG_FILE` - Path to log file

### File Storage Configuration

- `UPLOAD_FOLDER` - Upload directory path

### Cache Configuration

- `CACHE_HOST` - Redis host
- `CACHE_PORT` - Redis port
- `CACHE_PASSWORD` - Redis password

## Security Features

### Sensitive Field Encryption

The following fields are automatically encrypted when stored:

- `app.secret_key`
- `database.password`
- `security.jwt_secret_key`
- `cache.password`

To enable encryption, set the `CONFIG_ENCRYPTION_KEY` environment variable with a Fernet-compatible key.

### Generating Encryption Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

## Configuration Validation

### Validation Schemas

The system includes comprehensive validation schemas for:

- **App Configuration** - Required fields, type validation, port range validation
- **Database Configuration** - Connection parameters, pool settings validation
- **Logging Configuration** - Log level validation, file size limits

### Custom Validation

Add custom validation schemas by extending the `ConfigValidator` class:

```python
validator = ConfigManager().validator
validator.schemas['custom_section'] = {
    'required': ['field1', 'field2'],
    'types': {
        'field1': str,
        'field2': int
    },
    'ranges': {
        'field2': (1, 100)
    }
}
```

## Hot Configuration Reloading

### Automatic Reloading

The system automatically detects configuration file changes and reloads them:

1. File system watcher monitors `.yaml` files
2. Changes trigger validation and reload
3. Callbacks are notified of changes
4. Backups are created before applying changes

### Manual Reloading

```python
from config_manager import get_config

config = get_config()
config.reload_config()
```

### API Endpoint

```bash
curl -X POST http://localhost:5000/config/reload
```

## Configuration Versioning

### Version History

Each configuration change creates a version entry with:

- Version number (v1, v2, etc.)
- Timestamp
- Configuration checksum
- Author and description
- Environment

### Viewing Version History

```python
config = get_config()
history = config.get_version_history()
print(history)
```

## Configuration Backup

### Automatic Backups

Backups are automatically created:

- Before hot reload
- Before manual saves
- After configuration changes

### Manual Backup

```python
config = get_config()
backup_file = config.backup.create_backup(config.config, "Manual backup")
```

### Listing Backups

```python
backups = config.backup.list_backups()
for backup in backups:
    print(f"{backup['timestamp']}: {backup['description']}")
```

### Restoring from Backup

```python
config = get_config()
restored_config = config.backup.restore_backup(backup_file)
```

## Configuration Monitoring

### Health Check Endpoint

```bash
curl http://localhost:5000/health
```

### Configuration Monitoring Endpoint

```bash
curl http://localhost:5000/config
```

Returns monitoring information:

```json
{
    "environment": "development",
    "last_reload": "2024-01-15T10:30:00",
    "version_count": 5,
    "watcher_active": true,
    "backup_count": 10,
    "validation_status": "valid"
}
```

## Usage Examples

### Basic Usage

```python
from config_manager import get_config, get_config_value

# Get configuration manager
config = get_config()

# Get specific value
secret_key = get_config_value('app.secret_key')
db_host = get_config_value('database.host', 'localhost')

# Get entire section
db_config = config.get_section('database')
```

### Configuration Change Callbacks

```python
def on_config_change(new_config, old_config):
    print("Configuration changed!")
    # Handle configuration changes

config = get_config()
config.add_change_callback(on_config_change)
```

### Database Configuration

```python
from db_config import db_config, get_db_session

# Test database connection
if db_config.test_connection():
    print("Database connection successful")

# Use database session
with get_db_session() as session:
    # Perform database operations
    pass
```

### Logging Configuration

```python
from logger_config import get_logger

# Get logger
logger = get_logger(__name__)
logger.info("Application started")

# Change log level dynamically
from logger_config import logging_config
logging_config.set_level('DEBUG')
```

## Best Practices

### Environment Variables

1. Use environment variables for all sensitive data
2. Provide sensible defaults in configuration files
3. Use the `${VAR:default}` syntax for optional variables

### Configuration Security

1. Always set `CONFIG_ENCRYPTION_KEY` in production
2. Use different keys for different environments
3. Rotate encryption keys regularly

### Validation

1. Enable configuration validation in all environments
2. Add custom validation for application-specific settings
3. Test configuration changes in staging before production

### Monitoring

1. Monitor configuration reload events
2. Set up alerts for validation failures
3. Track configuration version history

### Backup Strategy

1. Enable automatic backups
2. Regularly clean up old backups
3. Store critical backups in secure locations

## Troubleshooting

### Common Issues

1. **Configuration Validation Failed**
   - Check validation error messages
   - Verify all required fields are present
   - Ensure field types and ranges are correct

2. **Hot Reload Not Working**
   - Verify file watcher is active
   - Check file permissions
   - Ensure configuration files are valid YAML

3. **Encryption Errors**
   - Verify `CONFIG_ENCRYPTION_KEY` is set
   - Check key format (must be Fernet-compatible)
   - Ensure key is the same used for encryption

4. **Database Connection Issues**
   - Verify database configuration
   - Check connection string format
   - Test database connectivity

### Debug Mode

Enable debug mode for detailed logging:

```yaml
app:
  debug: true

logging:
  level: "DEBUG"
```

## API Reference

### ConfigManager Class

#### Methods

- `get(key, default=None)` - Get configuration value by key
- `get_section(section)` - Get entire configuration section
- `reload_config()` - Reload configuration from file
- `save_config(description, author)` - Save configuration with versioning
- `add_change_callback(callback)` - Add configuration change callback
- `get_version_history()` - Get configuration version history
- `get_monitoring_info()` - Get monitoring information

### DatabaseConfig Class

#### Methods

- `test_connection()` - Test database connection
- `get_session()` - Get database session
- `get_db_session()` - Context manager for database sessions
- `get_connection_info()` - Get connection information
- `reload_config()` - Reload database configuration

### LoggingConfig Class

#### Methods

- `get_logger(name)` - Get logger instance
- `get_log_stats()` - Get logging statistics
- `reload_config()` - Reload logging configuration
- `set_level(level, logger_name)` - Change log level
- `setup_structured_logging()` - Setup JSON logging

## Dependencies

The configuration management system requires the following Python packages:

- `flask>=2.3.0` - Web framework
- `pyyaml>=6.0` - YAML parsing
- `sqlalchemy>=2.0.0` - Database ORM
- `psycopg2-binary>=2.9.0` - PostgreSQL driver
- `watchdog>=3.0.0` - File system monitoring
- `cryptography>=41.0.0` - Encryption
- `python-dotenv>=1.0.0` - Environment variable management

## License

This configuration management system is part of the FlavorSnap project and follows the same license terms.
