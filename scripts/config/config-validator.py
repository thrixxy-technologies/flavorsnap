#!/usr/bin/env python3
"""
Configuration Validator for FlavorSnap
Validates configuration files against schemas and best practices
"""

import os
import sys
import json
import yaml
import logging
import argparse
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator
import cerberus
import pydantic
from pydantic import BaseModel, validator, ValidationError as PydanticValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: str
    validation_time: float
    timestamp: datetime

class ConfigurationSchema:
    """Configuration schema definitions"""
    
    # JSON Schema for validation
    APP_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "environment": {"type": "string", "enum": ["development", "staging", "production"]},
            "debug": {"type": "boolean"},
            "hot_reload": {"type": "boolean"},
            "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
        },
        "required": ["name", "version", "environment"],
        "additionalProperties": True
    }
    
    SERVER_SCHEMA = {
        "type": "object",
        "properties": {
            "host": {"type": "string", "minLength": 1},
            "port": {"type": "integer", "minimum": 1, "maximum": 65535},
            "workers": {"type": "integer", "minimum": 1},
            "reload": {"type": "boolean"},
            "access_log": {"type": "boolean"}
        },
        "required": ["host", "port"],
        "additionalProperties": True
    }
    
    DATABASE_SCHEMA = {
        "type": "object",
        "properties": {
            "host": {"type": "string", "minLength": 1},
            "port": {"type": "integer", "minimum": 1, "maximum": 65535},
            "name": {"type": "string", "minLength": 1},
            "username": {"type": "string", "minLength": 1},
            "password": {"type": "string", "minLength": 1},
            "pool_size": {"type": "integer", "minimum": 1},
            "max_overflow": {"type": "integer", "minimum": 0},
            "echo": {"type": "boolean"}
        },
        "required": ["host", "port", "name", "username", "password"],
        "additionalProperties": True
    }
    
    SECURITY_SCHEMA = {
        "type": "object",
        "properties": {
            "jwt_secret": {"type": "string", "minLength": 16},
            "jwt_expiration": {"type": "integer", "minimum": 60},
            "bcrypt_rounds": {"type": "integer", "minimum": 4, "maximum": 31},
            "rate_limiting": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "requests_per_minute": {"type": "integer", "minimum": 1}
                },
                "required": ["enabled"]
            },
            "cors": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "origins": {"type": "array", "items": {"type": "string"}},
                    "methods": {"type": "array", "items": {"type": "string"}},
                    "headers": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["enabled"]
            }
        },
        "required": ["jwt_secret"],
        "additionalProperties": True
    }
    
    # Full configuration schema
    FULL_SCHEMA = {
        "type": "object",
        "properties": {
            "app": APP_SCHEMA,
            "server": SERVER_SCHEMA,
            "database": DATABASE_SCHEMA,
            "security": SECURITY_SCHEMA,
            "redis": {"type": "object"},
            "ml": {"type": "object"},
            "upload": {"type": "object"},
            "cache": {"type": "object"},
            "logging": {"type": "object"},
            "monitoring": {"type": "object"},
            "features": {"type": "object"},
            "external_services": {"type": "object"},
            "performance": {"type": "object"},
            "validation": {"type": "object"},
            "version_control": {"type": "object"}
        },
        "required": ["app"],
        "additionalProperties": True
    }

class CerberusValidator:
    """Cerberus schema validator"""
    
    def __init__(self):
        self.schema = {
            'app': {
                'type': 'dict',
                'schema': {
                    'name': {'type': 'string', 'required': True},
                    'version': {'type': 'string', 'required': True, 'regex': r'^\d+\.\d+\.\d+$'},
                    'environment': {
                        'type': 'string',
                        'required': True,
                        'allowed': ['development', 'staging', 'production']
                    },
                    'debug': {'type': 'boolean'},
                    'hot_reload': {'type': 'boolean'},
                    'log_level': {
                        'type': 'string',
                        'allowed': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                    }
                }
            },
            'server': {
                'type': 'dict',
                'schema': {
                    'host': {'type': 'string', 'required': True},
                    'port': {
                        'type': 'integer',
                        'required': True,
                        'min': 1,
                        'max': 65535
                    },
                    'workers': {'type': 'integer', 'min': 1},
                    'reload': {'type': 'boolean'},
                    'access_log': {'type': 'boolean'}
                }
            },
            'database': {
                'type': 'dict',
                'schema': {
                    'host': {'type': 'string', 'required': True},
                    'port': {
                        'type': 'integer',
                        'required': True,
                        'min': 1,
                        'max': 65535
                    },
                    'name': {'type': 'string', 'required': True},
                    'username': {'type': 'string', 'required': True},
                    'password': {'type': 'string', 'required': True},
                    'pool_size': {'type': 'integer', 'min': 1},
                    'max_overflow': {'type': 'integer', 'min': 0},
                    'echo': {'type': 'boolean'}
                }
            },
            'security': {
                'type': 'dict',
                'schema': {
                    'jwt_secret': {
                        'type': 'string',
                        'required': True,
                        'minlength': 16
                    },
                    'jwt_expiration': {'type': 'integer', 'min': 60},
                    'bcrypt_rounds': {'type': 'integer', 'min': 4, 'max': 31},
                    'rate_limiting': {
                        'type': 'dict',
                        'schema': {
                            'enabled': {'type': 'boolean', 'required': True},
                            'requests_per_minute': {'type': 'integer', 'min': 1}
                        }
                    },
                    'cors': {
                        'type': 'dict',
                        'schema': {
                            'enabled': {'type': 'boolean', 'required': True},
                            'origins': {'type': 'list', 'schema': {'type': 'string'}},
                            'methods': {'type': 'list', 'schema': {'type': 'string'}},
                            'headers': {'type': 'list', 'schema': {'type': 'string'}}
                        }
                    }
                }
            }
        }
        self.validator = cerberus.Validator(self.schema)

class PydanticValidator:
    """Pydantic model validator"""
    
    class AppModel(BaseModel):
        name: str
        version: str
        environment: str
        debug: bool = False
        hot_reload: bool = False
        log_level: str = "INFO"
        
        @validator('version')
        def validate_version(cls, v):
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', v):
                raise ValueError('Version must be in format X.Y.Z')
            return v
        
        @validator('environment')
        def validate_environment(cls, v):
            allowed = ['development', 'staging', 'production']
            if v not in allowed:
                raise ValueError(f'Environment must be one of {allowed}')
            return v
        
        @validator('log_level')
        def validate_log_level(cls, v):
            allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in allowed:
                raise ValueError(f'Log level must be one of {allowed}')
            return v.upper()
    
    class ServerModel(BaseModel):
        host: str
        port: int
        workers: int = 1
        reload: bool = False
        access_log: bool = True
        
        @validator('port')
        def validate_port(cls, v):
            if not 1 <= v <= 65535:
                raise ValueError('Port must be between 1 and 65535')
            return v
        
        @validator('workers')
        def validate_workers(cls, v):
            if v < 1:
                raise ValueError('Workers must be at least 1')
            return v
    
    class DatabaseModel(BaseModel):
        host: str
        port: int
        name: str
        username: str
        password: str
        pool_size: int = 5
        max_overflow: int = 10
        echo: bool = False
        
        @validator('port')
        def validate_port(cls, v):
            if not 1 <= v <= 65535:
                raise ValueError('Port must be between 1 and 65535')
            return v
        
        @validator('pool_size')
        def validate_pool_size(cls, v):
            if v < 1:
                raise ValueError('Pool size must be at least 1')
            return v

class ConfigValidator:
    """Advanced configuration validator"""
    
    def __init__(self):
        self.json_schema = ConfigurationSchema.FULL_SCHEMA
        self.cerberus_validator = CerberusValidator()
        self.pydantic_validator = PydanticValidator()
        
        # Validation rules
        self.validation_rules = {
            'required_sections': ['app'],
            'production_requirements': {
                'app.debug': False,
                'app.hot_reload': False,
                'security.jwt_secret': True,
                'security.rate_limiting.enabled': True
            },
            'security_best_practices': {
                'security.jwt_expiration': {'min': 300, 'max': 3600},
                'security.bcrypt_rounds': {'min': 10, 'max': 12},
                'database.pool_size': {'min': 10, 'max': 50}
            }
        }
    
    def validate_file(self, file_path: str, validator_type: str = 'jsonschema') -> ValidationResult:
        """Validate a configuration file"""
        start_time = datetime.utcnow()
        
        try:
            # Load configuration
            config = self._load_config_file(file_path)
            
            # Validate based on type
            if validator_type == 'jsonschema':
                return self._validate_with_jsonschema(config, file_path, start_time)
            elif validator_type == 'cerberus':
                return self._validate_with_cerberus(config, file_path, start_time)
            elif validator_type == 'pydantic':
                return self._validate_with_pydantic(config, file_path, start_time)
            elif validator_type == 'all':
                return self._validate_with_all(config, file_path, start_time)
            else:
                raise ValueError(f"Unknown validator type: {validator_type}")
                
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Failed to validate file: {str(e)}"],
                warnings=[],
                file_path=file_path,
                validation_time=0,
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
    
    def _validate_with_jsonschema(self, config: Dict[str, Any], file_path: str, start_time: datetime) -> ValidationResult:
        """Validate using JSON Schema"""
        errors = []
        warnings = []
        
        try:
            # Validate against schema
            validate(instance=config, schema=self.json_schema)
            
            # Additional validation rules
            errors.extend(self._validate_rules(config))
            warnings.extend(self._validate_best_practices(config))
            
            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
            
        except ValidationError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Schema validation failed: {e.message}"],
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    def _validate_with_cerberus(self, config: Dict[str, Any], file_path: str, start_time: datetime) -> ValidationResult:
        """Validate using Cerberus"""
        errors = []
        warnings = []
        
        try:
            # Validate with Cerberus
            self.cerberus_validator.validator.validate(config)
            
            if not self.cerberus_validator.validator.errors:
                # Additional validation rules
                errors.extend(self._validate_rules(config))
                warnings.extend(self._validate_best_practices(config))
            else:
                errors.extend(self._format_cerberus_errors(self.cerberus_validator.validator.errors))
            
            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Cerberus validation failed: {str(e)}"],
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    def _validate_with_pydantic(self, config: Dict[str, Any], file_path: str, start_time: datetime) -> ValidationResult:
        """Validate using Pydantic"""
        errors = []
        warnings = []
        
        try:
            # Validate app section
            if 'app' in config:
                PydanticValidator.AppModel(**config['app'])
            
            # Validate server section
            if 'server' in config:
                PydanticValidator.ServerModel(**config['server'])
            
            # Validate database section
            if 'database' in config:
                PydanticValidator.DatabaseModel(**config['database'])
            
            # Additional validation rules
            errors.extend(self._validate_rules(config))
            warnings.extend(self._validate_best_practices(config))
            
            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
            
        except PydanticValidationError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Pydantic validation failed: {str(e)}"],
                warnings=warnings,
                file_path=file_path,
                validation_time=(datetime.utcnow() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    def _validate_with_all(self, config: Dict[str, Any], file_path: str, start_time: datetime) -> ValidationResult:
        """Validate using all validators"""
        all_errors = []
        all_warnings = []
        
        # JSON Schema validation
        try:
            validate(instance=config, schema=self.json_schema)
        except ValidationError as e:
            all_errors.append(f"JSON Schema: {e.message}")
        
        # Cerberus validation
        try:
            self.cerberus_validator.validator.validate(config)
            if self.cerberus_validator.validator.errors:
                all_errors.extend([f"Cerberus: {err}" for err in self._format_cerberus_errors(self.cerberus_validator.validator.errors)])
        except Exception as e:
            all_errors.append(f"Cerberus: {str(e)}")
        
        # Pydantic validation
        try:
            if 'app' in config:
                PydanticValidator.AppModel(**config['app'])
            if 'server' in config:
                PydanticValidator.ServerModel(**config['server'])
            if 'database' in config:
                PydanticValidator.DatabaseModel(**config['database'])
        except PydanticValidationError as e:
            all_errors.append(f"Pydantic: {str(e)}")
        
        # Additional validation rules
        all_errors.extend(self._validate_rules(config))
        all_warnings.extend(self._validate_best_practices(config))
        
        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            file_path=file_path,
            validation_time=(datetime.utcnow() - start_time).total_seconds(),
            timestamp=start_time
        )
    
    def _validate_rules(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration rules"""
        errors = []
        
        # Check required sections
        for section in self.validation_rules['required_sections']:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Environment-specific requirements
        environment = config.get('app', {}).get('environment', 'development')
        if environment == 'production':
            prod_reqs = self.validation_rules['production_requirements']
            for key, expected_value in prod_reqs.items():
                actual_value = self._get_nested_value(config, key)
                if actual_value != expected_value:
                    errors.append(f"Production requirement violated: {key} should be {expected_value}, got {actual_value}")
        
        return errors
    
    def _validate_best_practices(self, config: Dict[str, Any]) -> List[str]:
        """Validate best practices"""
        warnings = []
        
        # Security best practices
        security_rules = self.validation_rules['security_best_practices']
        for key, rules in security_rules.items():
            actual_value = self._get_nested_value(config, key)
            if actual_value is not None:
                if isinstance(rules, dict) and 'min' in rules and 'max' in rules:
                    if not (rules['min'] <= actual_value <= rules['max']):
                        warnings.append(f"Security best practice: {key} should be between {rules['min']} and {rules['max']}, got {actual_value}")
        
        # Check for default passwords
        if config.get('database', {}).get('password') in ['password', 'admin', 'root', 'postgres']:
            warnings.append("Using default database password is not recommended")
        
        # Check for weak JWT secrets
        jwt_secret = config.get('security', {}).get('jwt_secret', '')
        if len(jwt_secret) < 32:
            warnings.append("JWT secret should be at least 32 characters long")
        
        return warnings
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get nested value using dot notation"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _format_cerberus_errors(self, errors: Dict[str, Any]) -> List[str]:
        """Format Cerberus errors"""
        formatted_errors = []
        
        def format_error(error_dict, prefix=""):
            for field, error in error_dict.items():
                if isinstance(error, dict):
                    format_error(error, f"{prefix}{field}.")
                elif isinstance(error, list):
                    for e in error:
                        formatted_errors.append(f"{prefix}{field}: {e}")
                else:
                    formatted_errors.append(f"{prefix}{field}: {error}")
        
        format_error(errors)
        return formatted_errors
    
    def validate_directory(self, directory: str, pattern: str = "*.yaml", validator_type: str = 'jsonschema') -> List[ValidationResult]:
        """Validate all configuration files in a directory"""
        results = []
        config_dir = Path(directory)
        
        if not config_dir.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        for file_path in config_dir.glob(pattern):
            result = self.validate_file(str(file_path), validator_type)
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[ValidationResult], output_file: str = None) -> Dict[str, Any]:
        """Generate validation report"""
        total_files = len(results)
        valid_files = len([r for r in results if r.valid])
        invalid_files = total_files - valid_files
        
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        total_time = sum(r.validation_time for r in results)
        
        report = {
            'summary': {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': invalid_files,
                'total_errors': total_errors,
                'total_warnings': total_warnings,
                'validation_time_seconds': total_time,
                'success_rate': (valid_files / total_files * 100) if total_files > 0 else 0
            },
            'files': []
        }
        
        for result in results:
            report['files'].append({
                'file_path': result.file_path,
                'valid': result.valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'validation_time': result.validation_time,
                'timestamp': result.timestamp.isoformat()
            })
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        return report

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Validate configuration files')
    parser.add_argument('path', help='Configuration file or directory to validate')
    parser.add_argument('--validator', choices=['jsonschema', 'cerberus', 'pydantic', 'all'], 
                       default='jsonschema', help='Validator to use')
    parser.add_argument('--pattern', default='*.yaml', help='File pattern for directory validation')
    parser.add_argument('--output', help='Output report file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = ConfigValidator()
    
    try:
        path = Path(args.path)
        
        if path.is_file():
            # Validate single file
            result = validator.validate_file(str(path), args.validator)
            
            print(f"File: {result.file_path}")
            print(f"Valid: {result.valid}")
            print(f"Validation time: {result.validation_time:.3f}s")
            
            if result.errors:
                print("Errors:")
                for error in result.errors:
                    print(f"  - {error}")
            
            if result.warnings:
                print("Warnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            results = [result]
            
        elif path.is_dir():
            # Validate directory
            results = validator.validate_directory(str(path), args.pattern, args.validator)
            
            print(f"Validated {len(results)} files in {args.path}")
            
            for result in results:
                status = "✓" if result.valid else "✗"
                print(f"{status} {result.file_path}")
                
                if args.verbose and (result.errors or result.warnings):
                    if result.errors:
                        for error in result.errors:
                            print(f"    ERROR: {error}")
                    if result.warnings:
                        for warning in result.warnings:
                            print(f"    WARNING: {warning}")
        
        else:
            print(f"Error: {args.path} is not a file or directory")
            sys.exit(1)
        
        # Generate report
        report = validator.generate_report(results, args.output)
        
        if args.output:
            print(f"Report saved to: {args.output}")
        
        # Print summary
        print("\nValidation Summary:")
        print(f"  Total files: {report['summary']['total_files']}")
        print(f"  Valid files: {report['summary']['valid_files']}")
        print(f"  Invalid files: {report['summary']['invalid_files']}")
        print(f"  Total errors: {report['summary']['total_errors']}")
        print(f"  Total warnings: {report['summary']['total_warnings']}")
        print(f"  Success rate: {report['summary']['success_rate']:.1f}%")
        print(f"  Total time: {report['summary']['validation_time_seconds']:.3f}s")
        
        # Exit with error code if any files are invalid
        if report['summary']['invalid_files'] > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
