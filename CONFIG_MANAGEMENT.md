# FlavorSnap Configuration Management

This document describes the comprehensive configuration management system implemented for FlavorSnap, addressing all requirements from issue #316.

## Overview

The configuration management system provides:
- Environment-specific configurations
- Configuration validation
- Hot configuration reloading
- Configuration versioning
- Security for sensitive configs
- Configuration monitoring
- Configuration backup

## Architecture

### Core Components

1. **config_manager.py** - Main configuration manager with all advanced features
2. **db_config.py** - Database-specific configuration management
3. **logger_config.py** - Logging configuration management
4. **config.yaml** - Base configuration file
5. **config.{environment}.yaml** - Environment-specific overrides

## Configuration Files

### Base Configuration (config.yaml)

The main configuration file contains default settings and environment variable placeholders:

```yaml
app:
  name: "flavorsnap"
  version: "1.0.0"
  debug: true
  host: "0.0.0.0"
  port: 5000
  secret_key: "${APP_SECRET_KEY:dev-secret-key-change-in-production}"
```

### Environment-Specific Configurations

- **config.production.yaml** - Production environment settings
- **config.staging.yaml** - Staging environment settings  
- **config.testing.yaml** - Testing environment settings

Environment configs override base settings and are automatically loaded based on the `ENVIRONMENT` environment variable.

## Features

### 1. Environment-Specific Configurations

Set the environment using the `ENVIRONMENT` environment variable:

```bash
export ENVIRONMENT=production
python app.py
```

The system will automatically load `config.production.yaml` and merge it with the base configuration.

### 2. Environment Variable Substitution

Configuration values support environment variable substitution with defaults:

```yaml
database:
  password: "${DB_PASSWORD:default-password}"
  host: "${DB_HOST:localhost}"
```

### 3. Configuration Validation

The system validates all configuration sections against defined schemas:

- Required fields checking
- Type validation
- Range validation
- Enum validation

### 4. Hot Configuration Reloading

Configuration changes are automatically detected and reloaded:

- File system monitoring using `watchdog`
- Debounced reload to prevent rapid changes
- Callback system for application updates
- Validation before applying changes

### 5. Configuration Versioning

Every configuration change is versioned:

```python
version_info = {
    'version': 'v1',
    'timestamp': '2024-01-01T12:00:00',
    'checksum': 'abc123...',
    'author': 'system',
    'description': 'Hot reload',
    'environment': 'production'
}
```

### 6. Security for Sensitive Configs

Sensitive configuration fields are encrypted:

- Uses Fernet symmetric encryption
- Configurable encryption key via `CONFIG_ENCRYPTION_KEY`
- Automatic encryption/decryption of sensitive fields
- Secure storage of passwords and secrets

Sensitive fields include:
- `app.secret_key`
- `database.password`
- `security.jwt_secret_key`
- `cache.password`

### 7. Configuration Monitoring

Real-time monitoring of configuration state:

```python
monitoring_info = {
    'environment': 'production',
    'config_path': './config.yaml',
    'last_reload': '2024-01-01T12:00:00',
    'version_count': 5,
    'checksum': 'abc123...',
    'watcher_active': True,
    'backup_count': 10,
    'validation_status': 'valid'
}
```

### 8. Configuration Backup

Automatic backup system:

- Backups created before any configuration change
- Timestamped backup files
- Configurable retention period
- Easy restoration from any backup

## Usage Examples

### Basic Usage

```python
from config_manager import get_config, get_config_value

# Get configuration manager
config = get_config()

# Get specific value
secret_key = get_config_value('app.secret_key')

# Get entire section
db_config = get_config_value('database')
```

### Database Configuration

```python
from db_config import db_config, get_db_session

# Test database connection
if db_config.test_connection():
    print("Database is connected")

# Use database session
with get_db_session() as session:
    # Database operations
    pass
```

### Logging Configuration

```python
from logger_config import get_logger

# Get logger
logger = get_logger(__name__)

# Log messages
logger.info("Application started")
logger.error("Something went wrong")
```

### Configuration Changes

```python
# Add callback for configuration changes
def on_config_change(new_config, old_config):
    print("Configuration changed!")
    # Update application state

config.add_change_callback(on_config_change)

# Manually reload configuration
config.reload_config()
```

## API Endpoints

The Flask application provides several configuration-related endpoints:

### GET /health
Returns application health status including database connectivity.

### GET /config
Returns non-sensitive configuration information.

### POST /config/reload
Manually triggers configuration reload.

## Environment Variables

Key environment variables:

- `ENVIRONMENT` - Environment name (development, staging, production, testing)
- `CONFIG_ENCRYPTION_KEY` - Key for encrypting sensitive configuration
- `APP_SECRET_KEY` - Flask application secret key
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database connection
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Security Considerations

1. **Encryption Key Management**
   - Store encryption key securely (e.g., in AWS KMS, HashiCorp Vault)
   - Rotate encryption keys regularly
   - Never commit encryption keys to version control

2. **Sensitive Data**
   - All sensitive fields are automatically encrypted
   - Use environment variables for production secrets
   - Regularly audit configuration for exposed sensitive data

3. **Access Control**
   - Limit access to configuration files
   - Use file permissions appropriately
   - Monitor configuration changes

## Best Practices

1. **Development**
   - Use environment-specific configs for different environments
   - Never commit production secrets to version control
   - Test configuration changes in staging first

2. **Production**
   - Enable all security features
   - Use strong encryption keys
   - Monitor configuration changes
   - Regular backup cleanup

3. **Monitoring**
   - Monitor configuration reload events
   - Set up alerts for validation failures
   - Track configuration version history

## Troubleshooting

### Common Issues

1. **Configuration Loading Fails**
   - Check file permissions
   - Verify YAML syntax
   - Ensure environment variables are set

2. **Hot Reload Not Working**
   - Check if file watcher is active
   - Verify file system permissions
   - Check logs for errors

3. **Encryption Errors**
   - Verify encryption key is set
   - Check key format (base64 encoded)
   - Ensure consistent key usage

### Debug Mode

Enable debug logging to troubleshoot issues:

```yaml
logging:
  level: "DEBUG"
  enable_console: true
```

## Migration Guide

### From Old Configuration

1. Install new dependencies:
```bash
pip install -r requirements.txt
```

2. Update environment variables:
```bash
export ENVIRONMENT=production
export CONFIG_ENCRYPTION_KEY=your-encryption-key
```

3. Update application code to use new configuration system.

### Backup Old Configuration

Before migrating, create a backup of your existing configuration:

```python
from config_manager import ConfigManager
config = ConfigManager()
config.backup.create_backup(config.config, "Pre-migration backup")
```

## Dependencies

New dependencies added for configuration management:

- `pyyaml` - YAML configuration file parsing
- `sqlalchemy` - Database ORM and connection pooling
- `psycopg2-binary` - PostgreSQL adapter
- `watchdog` - File system monitoring for hot reload
- `cryptography` - Encryption for sensitive configuration
- `python-dotenv` - Environment variable management

## Support

For issues or questions about the configuration management system:

1. Check the application logs
2. Verify configuration syntax
3. Test with a minimal configuration
4. Review this documentation

The configuration management system is designed to be robust, secure, and easy to use while providing all the advanced features required for production deployments.
