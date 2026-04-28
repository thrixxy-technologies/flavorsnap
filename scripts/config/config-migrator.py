#!/usr/bin/env python3
"""
Configuration Migrator for FlavorSnap
Migrates configurations between environments and versions
"""

import os
import sys
import json
import yaml
import logging
import argparse
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil
import hashlib
import difflib
import copy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MigrationResult:
    """Migration result"""
    success: bool
    source_file: str
    target_file: str
    changes_made: List[str]
    warnings: List[str]
    errors: List[str]
    backup_created: bool
    migration_time: float
    timestamp: datetime

@dataclass
class MigrationRule:
    """Migration rule definition"""
    name: str
    source_environment: str
    target_environment: str
    transformations: List[Dict[str, Any]]
    validations: List[str]
    description: str

class ConfigMigrator:
    """Advanced configuration migrator"""
    
    def __init__(self):
        self.migration_rules = self._load_migration_rules()
        self.environment_mappings = {
            'development': {
                'debug': True,
                'hot_reload': True,
                'log_level': 'DEBUG',
                'workers': 1,
                'pool_size': 5
            },
            'staging': {
                'debug': True,
                'hot_reload': False,
                'log_level': 'INFO',
                'workers': 2,
                'pool_size': 10
            },
            'production': {
                'debug': False,
                'hot_reload': False,
                'log_level': 'INFO',
                'workers': 4,
                'pool_size': 20
            }
        }
        
        # Sensitive fields that should be handled carefully
        self.sensitive_fields = [
            'password', 'secret', 'key', 'token', 'dsn', 'api_key',
            'jwt_secret', 'encryption_key', 'private_key'
        ]
    
    def _load_migration_rules(self) -> List[MigrationRule]:
        """Load migration rules"""
        rules = [
            MigrationRule(
                name="dev_to_staging",
                source_environment="development",
                target_environment="staging",
                transformations=[
                    {
                        "type": "set_value",
                        "path": "app.debug",
                        "value": True
                    },
                    {
                        "type": "set_value",
                        "path": "app.hot_reload",
                        "value": False
                    },
                    {
                        "type": "set_value",
                        "path": "app.log_level",
                        "value": "INFO"
                    },
                    {
                        "type": "set_value",
                        "path": "server.workers",
                        "value": 2
                    },
                    {
                        "type": "set_value",
                        "path": "database.pool_size",
                        "value": 10
                    },
                    {
                        "type": "preserve_sensitive",
                        "paths": ["security.jwt_secret", "database.password"]
                    }
                ],
                validations=[
                    "required_sections",
                    "environment_specific",
                    "security_best_practices"
                ],
                description="Migrate configuration from development to staging"
            ),
            MigrationRule(
                name="staging_to_production",
                source_environment="staging",
                target_environment="production",
                transformations=[
                    {
                        "type": "set_value",
                        "path": "app.debug",
                        "value": False
                    },
                    {
                        "type": "set_value",
                        "path": "app.hot_reload",
                        "value": False
                    },
                    {
                        "type": "set_value",
                        "path": "app.log_level",
                        "value": "INFO"
                    },
                    {
                        "type": "set_value",
                        "path": "server.workers",
                        "value": 4
                    },
                    {
                        "type": "set_value",
                        "path": "database.pool_size",
                        "value": 20
                    },
                    {
                        "type": "set_value",
                        "path": "security.jwt_expiration",
                        "value": 1800
                    },
                    {
                        "type": "set_value",
                        "path": "security.bcrypt_rounds",
                        "value": 12
                    },
                    {
                        "type": "preserve_sensitive",
                        "paths": ["security.jwt_secret", "database.password"]
                    },
                    {
                        "type": "remove_field",
                        "paths": ["logging.handlers.console", "monitoring.datadog.sample_rate"]
                    }
                ],
                validations=[
                    "required_sections",
                    "production_security",
                    "performance_settings"
                ],
                description="Migrate configuration from staging to production"
            ),
            MigrationRule(
                name="version_upgrade",
                source_environment="*",
                target_environment="*",
                transformations=[
                    {
                        "type": "add_field",
                        "path": "version_control.enabled",
                        "value": True
                    },
                    {
                        "type": "add_field",
                        "path": "validation.strict_mode",
                        "value": False
                    },
                    {
                        "type": "migrate_field",
                        "old_path": "old_field_name",
                        "new_path": "new_field_name"
                    }
                ],
                validations=[
                    "schema_compatibility",
                    "required_fields"
                ],
                description="Upgrade configuration to new version"
            )
        ]
        
        return rules
    
    def migrate_config(self, source_file: str, target_file: str, 
                      source_env: str, target_env: str,
                      rule_name: Optional[str] = None,
                      create_backup: bool = True) -> MigrationResult:
        """Migrate configuration from source to target"""
        start_time = datetime.utcnow()
        
        try:
            # Load source configuration
            source_config = self._load_config_file(source_file)
            
            # Create backup if requested
            backup_created = False
            if create_backup:
                backup_created = self._create_backup(target_file)
            
            # Find migration rule
            rule = self._find_migration_rule(source_env, target_env, rule_name)
            
            if not rule:
                raise ValueError(f"No migration rule found for {source_env} -> {target_env}")
            
            # Apply transformations
            target_config, changes_made = self._apply_transformations(source_config, rule)
            
            # Set environment-specific values
            self._apply_environment_mappings(target_config, target_env)
            
            # Validate target configuration
            errors, warnings = self._validate_target_config(target_config, rule)
            
            # Save target configuration
            self._save_config_file(target_config, target_file)
            
            return MigrationResult(
                success=len(errors) == 0,
                source_file=source_file,
                target_file=target_file,
                changes_made=changes_made,
                warnings=warnings,
                errors=errors,
                backup_created=backup_created,
                migration_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                source_file=source_file,
                target_file=target_file,
                changes_made=[],
                warnings=[],
                errors=[str(e)],
                backup_created=backup_created,
                migration_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _save_config_file(self, config: Dict[str, Any], file_path: str):
        """Save configuration to file"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            elif path.suffix == '.json':
                json.dump(config, f, indent=2, sort_keys=True)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _create_backup(self, file_path: str) -> bool:
        """Create backup of existing file"""
        path = Path(file_path)
        
        if path.exists():
            backup_path = path.with_suffix(f".backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{path.suffix}")
            shutil.copy2(path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return True
        
        return False
    
    def _find_migration_rule(self, source_env: str, target_env: str, rule_name: Optional[str] = None) -> Optional[MigrationRule]:
        """Find migration rule"""
        if rule_name:
            for rule in self.migration_rules:
                if rule.name == rule_name:
                    return rule
        else:
            for rule in self.migration_rules:
                if (rule.source_environment == source_env or rule.source_environment == "*") and \
                   (rule.target_environment == target_env or rule.target_environment == "*"):
                    return rule
        
        return None
    
    def _apply_transformations(self, config: Dict[str, Any], rule: MigrationRule) -> Tuple[Dict[str, Any], List[str]]:
        """Apply transformation rules"""
        target_config = copy.deepcopy(config)
        changes_made = []
        
        for transformation in rule.transformations:
            try:
                change = self._apply_transformation(target_config, transformation)
                if change:
                    changes_made.append(change)
            except Exception as e:
                logger.warning(f"Failed to apply transformation {transformation}: {e}")
        
        return target_config, changes_made
    
    def _apply_transformation(self, config: Dict[str, Any], transformation: Dict[str, Any]) -> Optional[str]:
        """Apply single transformation"""
        trans_type = transformation.get("type")
        
        if trans_type == "set_value":
            return self._set_value(config, transformation["path"], transformation["value"])
        
        elif trans_type == "add_field":
            return self._add_field(config, transformation["path"], transformation["value"])
        
        elif trans_type == "remove_field":
            return self._remove_field(config, transformation["paths"])
        
        elif trans_type == "preserve_sensitive":
            return self._preserve_sensitive(config, transformation["paths"])
        
        elif trans_type == "migrate_field":
            return self._migrate_field(config, transformation["old_path"], transformation["new_path"])
        
        elif trans_type == "transform_value":
            return self._transform_value(config, transformation["path"], transformation["transform"])
        
        else:
            logger.warning(f"Unknown transformation type: {trans_type}")
            return None
    
    def _set_value(self, config: Dict[str, Any], path: str, value: Any) -> str:
        """Set value at path"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        old_value = current.get(keys[-1])
        current[keys[-1]] = value
        
        if old_value != value:
            return f"Set {path} = {value} (was {old_value})"
        
        return None
    
    def _add_field(self, config: Dict[str, Any], path: str, value: Any) -> str:
        """Add field if not exists"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        if keys[-1] not in current:
            current[keys[-1]] = value
            return f"Added {path} = {value}"
        
        return None
    
    def _remove_field(self, config: Dict[str, Any], paths: List[str]) -> List[str]:
        """Remove fields"""
        changes = []
        
        for path in paths:
            keys = path.split('.')
            current = config
            
            try:
                for key in keys[:-1]:
                    current = current[key]
                
                if keys[-1] in current:
                    del current[keys[-1]]
                    changes.append(f"Removed {path}")
            except KeyError:
                pass  # Field doesn't exist
        
        return changes
    
    def _preserve_sensitive(self, config: Dict[str, Any], paths: List[str]) -> List[str]:
        """Preserve sensitive fields (no-op, just for documentation)"""
        changes = []
        
        for path in paths:
            if self._get_nested_value(config, path) is not None:
                changes.append(f"Preserved sensitive field: {path}")
        
        return changes
    
    def _migrate_field(self, config: Dict[str, Any], old_path: str, new_path: str) -> Optional[str]:
        """Migrate field from old path to new path"""
        old_value = self._get_nested_value(config, old_path)
        
        if old_value is not None:
            self._set_value(config, new_path, old_value)
            self._remove_field(config, [old_path])
            return f"Migrated {old_path} -> {new_path}"
        
        return None
    
    def _transform_value(self, config: Dict[str, Any], path: str, transform_func: str) -> Optional[str]:
        """Transform value using function"""
        value = self._get_nested_value(config, path)
        
        if value is not None:
            try:
                # Simple transformation functions
                if transform_func == "to_upper":
                    new_value = str(value).upper()
                elif transform_func == "to_lower":
                    new_value = str(value).lower()
                elif transform_func == "multiply_by_2":
                    new_value = int(value) * 2
                elif transform_func == "add_1000":
                    new_value = int(value) + 1000
                else:
                    return None
                
                old_value = value
                self._set_value(config, path, new_value)
                return f"Transformed {path}: {old_value} -> {new_value}"
                
            except Exception as e:
                logger.warning(f"Failed to transform {path}: {e}")
        
        return None
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation"""
        keys = path.split('.')
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _apply_environment_mappings(self, config: Dict[str, Any], environment: str):
        """Apply environment-specific mappings"""
        if environment in self.environment_mappings:
            mappings = self.environment_mappings[environment]
            
            for path, value in mappings.items():
                self._set_value(config, path, value)
    
    def _validate_target_config(self, config: Dict[str, Any], rule: MigrationRule) -> Tuple[List[str], List[str]]:
        """Validate target configuration"""
        errors = []
        warnings = []
        
        for validation in rule.validations:
            try:
                if validation == "required_sections":
                    errors.extend(self._validate_required_sections(config))
                elif validation == "environment_specific":
                    errors.extend(self._validate_environment_specific(config))
                elif validation == "security_best_practices":
                    warnings.extend(self._validate_security_best_practices(config))
                elif validation == "production_security":
                    errors.extend(self._validate_production_security(config))
                elif validation == "performance_settings":
                    warnings.extend(self._validate_performance_settings(config))
                elif validation == "schema_compatibility":
                    errors.extend(self._validate_schema_compatibility(config))
                elif validation == "required_fields":
                    errors.extend(self._validate_required_fields(config))
            except Exception as e:
                warnings.append(f"Validation {validation} failed: {e}")
        
        return errors, warnings
    
    def _validate_required_sections(self, config: Dict[str, Any]) -> List[str]:
        """Validate required sections"""
        required = ['app', 'server']
        errors = []
        
        for section in required:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        return errors
    
    def _validate_environment_specific(self, config: Dict[str, Any]) -> List[str]:
        """Validate environment-specific settings"""
        errors = []
        environment = config.get('app', {}).get('environment', 'development')
        
        if environment == 'production':
            if config.get('app', {}).get('debug', True):
                errors.append("Debug mode should be disabled in production")
            
            if config.get('app', {}).get('hot_reload', True):
                errors.append("Hot reload should be disabled in production")
        
        return errors
    
    def _validate_security_best_practices(self, config: Dict[str, Any]) -> List[str]:
        """Validate security best practices"""
        warnings = []
        
        # Check JWT secret
        jwt_secret = config.get('security', {}).get('jwt_secret', '')
        if len(jwt_secret) < 32:
            warnings.append("JWT secret should be at least 32 characters")
        
        # Check bcrypt rounds
        bcrypt_rounds = config.get('security', {}).get('bcrypt_rounds', 10)
        if bcrypt_rounds < 10:
            warnings.append("Bcrypt rounds should be at least 10")
        
        return warnings
    
    def _validate_production_security(self, config: Dict[str, Any]) -> List[str]:
        """Validate production security settings"""
        errors = []
        
        # Check required security settings
        if not config.get('security', {}).get('jwt_secret'):
            errors.append("JWT secret is required in production")
        
        if not config.get('security', {}).get('rate_limiting', {}).get('enabled', False):
            errors.append("Rate limiting should be enabled in production")
        
        return errors
    
    def _validate_performance_settings(self, config: Dict[str, Any]) -> List[str]:
        """Validate performance settings"""
        warnings = []
        
        # Check worker count
        workers = config.get('server', {}).get('workers', 1)
        if workers < 2:
            warnings.append("Consider using at least 2 workers for better performance")
        
        # Check database pool size
        pool_size = config.get('database', {}).get('pool_size', 5)
        if pool_size < 10:
            warnings.append("Consider increasing database pool size for better performance")
        
        return warnings
    
    def _validate_schema_compatibility(self, config: Dict[str, Any]) -> List[str]:
        """Validate schema compatibility"""
        errors = []
        
        # Check for deprecated fields
        deprecated_fields = ['old_setting', 'legacy_config']
        for field in deprecated_fields:
            if self._get_nested_value(config, field) is not None:
                errors.append(f"Deprecated field found: {field}")
        
        return errors
    
    def _validate_required_fields(self, config: Dict[str, Any]) -> List[str]:
        """Validate required fields"""
        errors = []
        
        required_fields = {
            'app.name': str,
            'app.version': str,
            'app.environment': str,
            'server.host': str,
            'server.port': int
        }
        
        for path, expected_type in required_fields.items():
            value = self._get_nested_value(config, path)
            if value is None:
                errors.append(f"Required field missing: {path}")
            elif not isinstance(value, expected_type):
                errors.append(f"Field {path} should be {expected_type.__name__}, got {type(value).__name__}")
        
        return errors
    
    def compare_configs(self, file1: str, file2: str) -> Dict[str, Any]:
        """Compare two configuration files"""
        config1 = self._load_config_file(file1)
        config2 = self._load_config_file(file2)
        
        # Calculate differences
        differences = self._find_differences(config1, config2)
        
        # Generate diff
        diff = self._generate_diff(config1, config2, file1, file2)
        
        return {
            'file1': file1,
            'file2': file2,
            'differences': differences,
            'diff_text': diff,
            'similarity_score': self._calculate_similarity(config1, config2)
        }
    
    def _find_differences(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find differences between two configurations"""
        differences = []
        
        def compare_dicts(d1, d2, path=""):
            for key in set(d1.keys()) | set(d2.keys()):
                current_path = f"{path}.{key}" if path else key
                
                if key not in d1:
                    differences.append({
                        'type': 'added',
                        'path': current_path,
                        'value': d2[key]
                    })
                elif key not in d2:
                    differences.append({
                        'type': 'removed',
                        'path': current_path,
                        'value': d1[key]
                    })
                elif d1[key] != d2[key]:
                    if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                        compare_dicts(d1[key], d2[key], current_path)
                    else:
                        differences.append({
                            'type': 'changed',
                            'path': current_path,
                            'old_value': d1[key],
                            'new_value': d2[key]
                        })
        
        compare_dicts(config1, config2)
        return differences
    
    def _generate_diff(self, config1: Dict[str, Any], config2: Dict[str, Any], file1: str, file2: str) -> str:
        """Generate diff text"""
        text1 = yaml.dump(config1, default_flow_style=False, sort_keys=False)
        text2 = yaml.dump(config2, default_flow_style=False, sort_keys=False)
        
        diff = difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=file1,
            tofile=file2,
            lineterm=''
        )
        
        return ''.join(diff)
    
    def _calculate_similarity(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> float:
        """Calculate similarity score between two configurations"""
        str1 = json.dumps(config1, sort_keys=True)
        str2 = json.dumps(config2, sort_keys=True)
        
        similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
        return similarity * 100

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Migrate configuration files')
    parser.add_argument('action', choices=['migrate', 'compare'], help='Action to perform')
    parser.add_argument('--source', help='Source configuration file')
    parser.add_argument('--target', help='Target configuration file')
    parser.add_argument('--source-env', help='Source environment')
    parser.add_argument('--target-env', help='Target environment')
    parser.add_argument('--rule', help='Migration rule name')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--output', help='Output report file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    migrator = ConfigMigrator()
    
    try:
        if args.action == 'migrate':
            if not all([args.source, args.target, args.source_env, args.target_env]):
                print("Error: migrate action requires --source, --target, --source-env, and --target-env")
                sys.exit(1)
            
            result = migrator.migrate_config(
                args.source, args.target, args.source_env, args.target_env,
                args.rule, not args.no_backup
            )
            
            print(f"Migration completed: {'SUCCESS' if result.success else 'FAILED'}")
            print(f"Source: {result.source_file}")
            print(f"Target: {result.target_file}")
            print(f"Migration time: {result.migration_time:.3f}s")
            print(f"Backup created: {result.backup_created}")
            
            if result.changes_made:
                print("\nChanges made:")
                for change in result.changes_made:
                    print(f"  - {change}")
            
            if result.warnings:
                print("\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            if result.errors:
                print("\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")
            
            # Save report if requested
            if args.output:
                report = {
                    'result': asdict(result),
                    'timestamp': datetime.utcnow().isoformat()
                }
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"\nReport saved to: {args.output}")
            
            # Exit with error code if migration failed
            if not result.success:
                sys.exit(1)
        
        elif args.action == 'compare':
            if not all([args.source, args.target]):
                print("Error: compare action requires --source and --target")
                sys.exit(1)
            
            comparison = migrator.compare_configs(args.source, args.target)
            
            print(f"Comparing {comparison['file1']} and {comparison['file2']}")
            print(f"Similarity: {comparison['similarity_score']:.1f}%")
            print(f"Differences: {len(comparison['differences'])}")
            
            if comparison['differences']:
                print("\nDifferences:")
                for diff in comparison['differences']:
                    if diff['type'] == 'added':
                        print(f"  + {diff['path']}: {diff['value']}")
                    elif diff['type'] == 'removed':
                        print(f"  - {diff['path']}: {diff['value']}")
                    else:
                        print(f"  ~ {diff['path']}: {diff['old_value']} -> {diff['new_value']}")
            
            # Save comparison if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(comparison, f, indent=2, default=str)
                print(f"\nComparison saved to: {args.output}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
