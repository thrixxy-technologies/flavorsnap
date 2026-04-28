"""
Database Configuration Management for FlavorSnap
Handles database connections, pooling, and configuration validation
"""

import os
import logging
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration manager with connection pooling and validation"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        self.config = {}
        self.engine = None
        self.SessionLocal = None
        self.Base = declarative_base()
        self._lock = threading.Lock()
        self._load_config()
        
    def _load_config(self):
        """Load database configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                full_config = yaml.safe_load(file)
                self.config = full_config.get('database', {})
            logger.info("Database configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            raise
    
    def _substitute_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration"""
        def substitute_value(value):
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                if ':' in env_var:
                    var_name, default_value = env_var.split(':', 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    return os.getenv(env_var.strip(), '')
            return value
        
        return {k: substitute_value(v) for k, v in config_dict.items()}
    
    def validate_config(self) -> bool:
        """Validate database configuration parameters"""
        required_fields = ['type', 'host', 'port', 'name', 'user', 'password']
        config = self._substitute_env_vars(self.config)
        
        for field in required_fields:
            if not config.get(field):
                logger.error(f"Missing required database configuration: {field}")
                return False
        
        # Validate port is numeric
        try:
            int(config['port'])
        except ValueError:
            logger.error("Database port must be a number")
            return False
        
        # Validate pool settings
        pool_fields = ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']
        for field in pool_fields:
            if field in config:
                try:
                    int(config[field])
                except ValueError:
                    logger.error(f"Database {field} must be a number")
                    return False
        
        logger.info("Database configuration validation passed")
        return True
    
    def get_connection_string(self) -> str:
        """Generate database connection string"""
        if not self.validate_config():
            raise ValueError("Invalid database configuration")
        
        config = self._substitute_env_vars(self.config)
        
        if config['type'].lower() == 'postgresql':
            return (
                f"postgresql://{config['user']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['name']}"
            )
        else:
            raise ValueError(f"Unsupported database type: {config['type']}")
    
    def initialize_engine(self):
        """Initialize database engine with connection pooling"""
        with self._lock:
            if self.engine is None:
                connection_string = self.get_connection_string()
                config = self._substitute_env_vars(self.config)
                
                engine_kwargs = {
                    'poolclass': QueuePool,
                    'pool_size': config.get('pool_size', 10),
                    'max_overflow': config.get('max_overflow', 20),
                    'pool_timeout': config.get('pool_timeout', 30),
                    'pool_recycle': config.get('pool_recycle', 3600),
                    'pool_pre_ping': True,
                    'echo': config.get('echo', False)
                }
                
                self.engine = create_engine(connection_string, **engine_kwargs)
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                logger.info("Database engine initialized with connection pooling")
    
    def get_session(self) -> Session:
        """Get database session"""
        if self.engine is None:
            self.initialize_engine()
        return self.SessionLocal()
    
    @contextmanager
    def get_db_session(self):
        """Context manager for database sessions"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_db_session() as session:
                session.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information (without sensitive data)"""
        config = self._substitute_env_vars(self.config)
        return {
            'type': config.get('type'),
            'host': config.get('host'),
            'port': config.get('port'),
            'name': config.get('name'),
            'user': config.get('user'),
            'pool_size': config.get('pool_size'),
            'max_overflow': config.get('max_overflow'),
            'pool_timeout': config.get('pool_timeout'),
            'pool_recycle': config.get('pool_recycle')
        }
    
    def reload_config(self):
        """Reload database configuration"""
        with self._lock:
            old_config = self.config.copy()
            try:
                self._load_config()
                if self.validate_config():
                    # Reinitialize engine with new config
                    if self.engine:
                        self.engine.dispose()
                        self.engine = None
                        self.SessionLocal = None
                    self.initialize_engine()
                    logger.info("Database configuration reloaded successfully")
                else:
                    self.config = old_config
                    logger.error("Invalid configuration, keeping previous settings")
            except Exception as e:
                self.config = old_config
                logger.error(f"Failed to reload database configuration: {e}")

# Global database configuration instance
db_config = DatabaseConfig()

def get_db_session():
    """Get database session dependency for FastAPI/Flask"""
    return db_config.get_db_session()

def init_database():
    """Initialize database and create tables"""
    db_config.initialize_engine()
    if db_config.test_connection():
        # Create all tables
        db_config.Base.metadata.create_all(bind=db_config.engine)
        logger.info("Database initialized successfully")
    else:
        raise RuntimeError("Failed to initialize database")
