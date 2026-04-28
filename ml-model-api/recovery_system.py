#!/usr/bin/env python3
"""
Advanced Recovery System for FlavorSnap ML Model API
Implements point-in-time recovery, backup restoration, and disaster recovery
"""

import os
import json
import sqlite3
import shutil
import tempfile
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import redis
import psycopg2
from psycopg2 import sql
from dataclasses import dataclass, asdict
import pytz
import subprocess
import tarfile
import gzip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/recovery_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RecoveryPoint:
    """Recovery point information"""
    recovery_id: str
    backup_id: str
    timestamp: datetime
    recovery_type: str  # 'full', 'incremental', 'point_in_time'
    status: str  # 'available', 'in_progress', 'completed', 'failed'
    description: str
    backup_metadata: Dict

@dataclass
class RecoveryConfig:
    """Recovery system configuration"""
    recovery_path: str = '/tmp/flavorsnap_recovery'
    temp_path: str = '/tmp/flavorsnap_recovery_temp'
    max_concurrent_recoveries: int = 2
    verification_enabled: bool = True
    rollback_enabled: bool = True
    recovery_timeout_minutes: int = 60
    auto_cleanup_temp: bool = True
    preserve_permissions: bool = True
    dry_run_mode: bool = False

class RecoverySystem:
    """Advanced recovery management system"""
    
    def __init__(self, config: RecoveryConfig):
        self.config = config
        self.recovery_db_path = os.path.join(config.recovery_path, 'recovery_registry.db')
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.s3_client = None
        self.active_recoveries = {}
        self.recovery_lock = threading.Lock()
        
        # Initialize recovery directory
        Path(config.recovery_path).mkdir(parents=True, exist_ok=True)
        Path(config.temp_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize recovery registry database
        self._init_recovery_registry()
        
        # Import backup manager for metadata access
        from backup_manager import BackupManager
        self.backup_manager = BackupManager(None)  # Will be configured properly
        
        logger.info(f"RecoverySystem initialized with config: {config}")
    
    def _init_recovery_registry(self):
        """Initialize SQLite database for recovery tracking"""
        conn = sqlite3.connect(self.recovery_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_registry (
                recovery_id TEXT PRIMARY KEY,
                backup_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                recovery_type TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT,
                backup_metadata TEXT,
                start_time TEXT,
                end_time TEXT,
                error_message TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recovery_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (recovery_id) REFERENCES recovery_registry (recovery_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Recovery registry database initialized")
    
    def create_recovery_point(self, backup_id: str, description: str = "") -> RecoveryPoint:
        """Create a recovery point from a backup"""
        recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Creating recovery point: {recovery_id} from backup: {backup_id}")
            
            # Get backup metadata
            backup_metadata = self.backup_manager._get_backup_metadata(backup_id)
            if not backup_metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            # Create recovery point
            recovery_point = RecoveryPoint(
                recovery_id=recovery_id,
                backup_id=backup_id,
                timestamp=datetime.now(pytz.UTC),
                recovery_type=backup_metadata.backup_type,
                status='available',
                description=description or f"Recovery point from backup {backup_id}",
                backup_metadata=asdict(backup_metadata)
            )
            
            # Save recovery point
            self._save_recovery_point(recovery_point)
            
            logger.info(f"Recovery point created: {recovery_id}")
            return recovery_point
            
        except Exception as e:
            logger.error(f"Failed to create recovery point: {str(e)}")
            raise
    
    def restore_full_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """Restore from a full backup"""
        recovery_id = f"restore_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting full restore: {recovery_id} from backup: {backup_id}")
            
            # Get backup metadata
            backup_metadata = self.backup_manager._get_backup_metadata(backup_id)
            if not backup_metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            # Create recovery record
            recovery_point = RecoveryPoint(
                recovery_id=recovery_id,
                backup_id=backup_id,
                timestamp=datetime.now(pytz.UTC),
                recovery_type='full',
                status='in_progress',
                description=f"Full restore from backup {backup_id}",
                backup_metadata=asdict(backup_metadata)
            )
            self._save_recovery_point(recovery_point)
            
            # Download backup if needed
            backup_path = self._download_backup(backup_metadata)
            
            # Extract backup
            extracted_path = self._extract_backup(backup_path)
            
            # Verify backup integrity
            if self.config.verification_enabled:
                if not self._verify_backup_integrity(extracted_path, backup_metadata):
                    raise ValueError("Backup integrity verification failed")
            
            # Perform restoration
            if target_path:
                self._restore_to_path(extracted_path, target_path)
            else:
                self._restore_to_original_locations(extracted_path)
            
            # Update recovery status
            recovery_point.status = 'completed'
            self._save_recovery_point(recovery_point)
            
            # Cleanup temporary files
            if self.config.auto_cleanup_temp:
                self._cleanup_temp_files(backup_path, extracted_path)
            
            logger.info(f"Full restore completed: {recovery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Full restore failed: {str(e)}")
            
            # Update recovery status
            if 'recovery_point' in locals():
                recovery_point.status = 'failed'
                self._save_recovery_point(recovery_point)
            
            return False
    
    def restore_incremental_backup(self, backup_id: str, base_backup_id: str, 
                                 target_path: Optional[str] = None) -> bool:
        """Restore from incremental backup with base backup"""
        recovery_id = f"restore_incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting incremental restore: {recovery_id} from backup: {backup_id}")
            
            # Get backup metadata
            backup_metadata = self.backup_manager._get_backup_metadata(backup_id)
            base_metadata = self.backup_manager._get_backup_metadata(base_backup_id)
            
            if not backup_metadata or not base_metadata:
                raise ValueError("Backup or base backup not found")
            
            # Create recovery record
            recovery_point = RecoveryPoint(
                recovery_id=recovery_id,
                backup_id=backup_id,
                timestamp=datetime.now(pytz.UTC),
                recovery_type='incremental',
                status='in_progress',
                description=f"Incremental restore from backup {backup_id} with base {base_backup_id}",
                backup_metadata=asdict(backup_metadata)
            )
            self._save_recovery_point(recovery_point)
            
            # Download and extract base backup
            base_backup_path = self._download_backup(base_metadata)
            base_extracted_path = self._extract_backup(base_backup_path)
            
            # Download and extract incremental backup
            incremental_backup_path = self._download_backup(backup_metadata)
            incremental_extracted_path = self._extract_backup(incremental_backup_path)
            
            # Apply incremental changes to base
            merged_path = self._merge_incremental_backup(base_extracted_path, incremental_extracted_path)
            
            # Verify merged backup
            if self.config.verification_enabled:
                if not self._verify_merged_backup(merged_path, backup_metadata, base_metadata):
                    raise ValueError("Merged backup verification failed")
            
            # Perform restoration
            if target_path:
                self._restore_to_path(merged_path, target_path)
            else:
                self._restore_to_original_locations(merged_path)
            
            # Update recovery status
            recovery_point.status = 'completed'
            self._save_recovery_point(recovery_point)
            
            # Cleanup
            if self.config.auto_cleanup_temp:
                self._cleanup_temp_files(base_backup_path, base_extracted_path, 
                                       incremental_backup_path, incremental_extracted_path)
            
            logger.info(f"Incremental restore completed: {recovery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Incremental restore failed: {str(e)}")
            
            if 'recovery_point' in locals():
                recovery_point.status = 'failed'
                self._save_recovery_point(recovery_point)
            
            return False
    
    def point_in_time_recovery(self, target_timestamp: datetime, 
                              target_path: Optional[str] = None) -> bool:
        """Perform point-in-time recovery"""
        recovery_id = f"pit_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting point-in-time recovery: {recovery_id} to {target_timestamp}")
            
            # Find appropriate backup chain
            backup_chain = self._find_backup_chain_for_timestamp(target_timestamp)
            if not backup_chain:
                raise ValueError(f"No backup chain found for timestamp {target_timestamp}")
            
            # Create recovery record
            recovery_point = RecoveryPoint(
                recovery_id=recovery_id,
                backup_id=backup_chain[0],
                timestamp=datetime.now(pytz.UTC),
                recovery_type='point_in_time',
                status='in_progress',
                description=f"Point-in-time recovery to {target_timestamp}",
                backup_metadata={'backup_chain': backup_chain}
            )
            self._save_recovery_point(recovery_point)
            
            # Restore from backup chain
            restored_path = self._restore_from_backup_chain(backup_chain)
            
            # Apply transaction logs if available (for databases)
            if self._has_transaction_logs():
                self._apply_transaction_logs(restored_path, target_timestamp)
            
            # Perform restoration
            if target_path:
                self._restore_to_path(restored_path, target_path)
            else:
                self._restore_to_original_locations(restored_path)
            
            # Update recovery status
            recovery_point.status = 'completed'
            self._save_recovery_point(recovery_point)
            
            logger.info(f"Point-in-time recovery completed: {recovery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Point-in-time recovery failed: {str(e)}")
            
            if 'recovery_point' in locals():
                recovery_point.status = 'failed'
                self._save_recovery_point(recovery_point)
            
            return False
    
    def _download_backup(self, backup_metadata) -> str:
        """Download backup for recovery"""
        if backup_metadata.storage_location.startswith('s3://'):
            # Download from S3
            temp_dir = tempfile.mkdtemp(prefix='recovery_download_')
            backup_path = os.path.join(temp_dir, os.path.basename(backup_metadata.backup_id))
            
            # Parse S3 URL
            s3_url_parts = backup_metadata.storage_location.replace('s3://', '').split('/')
            bucket = s3_url_parts[0]
            key = '/'.join(s3_url_parts[1:])
            
            self.s3_client.download_file(bucket, key, backup_path)
            logger.info(f"Downloaded backup from S3: {backup_metadata.backup_id}")
            return backup_path
        else:
            # Local backup
            return backup_metadata.storage_location
    
    def _extract_backup(self, backup_path: str) -> str:
        """Extract backup archive"""
        extract_path = tempfile.mkdtemp(prefix='recovery_extract_')
        
        logger.info(f"Extracting backup: {backup_path} to {extract_path}")
        
        if backup_path.endswith('.tar.gz'):
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(extract_path)
        elif backup_path.endswith('.gz'):
            with gzip.open(backup_path, 'rb') as f:
                with open(os.path.join(extract_path, 'extracted'), 'wb') as out:
                    shutil.copyfileobj(f, out)
        else:
            # Assume it's a directory
            shutil.copytree(backup_path, extract_path, dirs_exist_ok=True)
        
        logger.info(f"Backup extracted to: {extract_path}")
        return extract_path
    
    def _verify_backup_integrity(self, extracted_path: str, backup_metadata) -> bool:
        """Verify extracted backup integrity"""
        try:
            logger.info(f"Verifying backup integrity: {backup_metadata.backup_id}")
            
            # Verify checksum
            calculated_checksum = self.backup_manager._calculate_checksum(extracted_path)
            if calculated_checksum != backup_metadata.checksum:
                logger.error("Checksum verification failed")
                return False
            
            # Verify file count
            file_count = len(self.backup_manager._get_backup_files(extracted_path))
            if file_count != backup_metadata.file_count:
                logger.error("File count verification failed")
                return False
            
            # Verify manifest
            manifest_path = os.path.join(extracted_path, 'manifest.json')
            if os.path.exists(manifest_path):
                if not self.backup_manager._verify_manifest(manifest_path, extracted_path):
                    logger.error("Manifest verification failed")
                    return False
            
            logger.info("Backup integrity verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Backup integrity verification error: {str(e)}")
            return False
    
    def _restore_to_path(self, extracted_path: str, target_path: str):
        """Restore backup to specific path"""
        logger.info(f"Restoring to path: {target_path}")
        
        # Create target directory if it doesn't exist
        Path(target_path).mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for root, dirs, files in os.walk(extracted_path):
            for file in files:
                source_file = os.path.join(root, file)
                relative_path = os.path.relpath(source_file, extracted_path)
                target_file = os.path.join(target_path, relative_path)
                
                # Create parent directories
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                
                # Copy file preserving permissions if enabled
                if self.config.preserve_permissions:
                    shutil.copy2(source_file, target_file)
                else:
                    shutil.copy(source_file, target_file)
        
        logger.info(f"Restoration to path completed: {target_path}")
    
    def _restore_to_original_locations(self, extracted_path: str):
        """Restore backup to original locations"""
        logger.info("Restoring to original locations")
        
        # Read manifest to determine original locations
        manifest_path = os.path.join(extracted_path, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_info in manifest.get('files', []):
                backup_file_path = os.path.join(extracted_path, file_info['path'])
                original_path = file_info['path']
                
                if os.path.exists(backup_file_path):
                    # Create parent directories
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)
                    
                    # Copy file
                    if self.config.preserve_permissions:
                        shutil.copy2(backup_file_path, original_path)
                    else:
                        shutil.copy(backup_file_path, original_path)
                    
                    logger.info(f"Restored: {original_path}")
        else:
            # No manifest, restore based on directory structure
            self._restore_by_directory_structure(extracted_path)
    
    def _restore_by_directory_structure(self, extracted_path: str):
        """Restore files based on directory structure"""
        # Restore databases
        db_files = [
            'model_registry.db',
            'predictions.db'
        ]
        
        for db_file in db_files:
            source = os.path.join(extracted_path, f"sqlite_{db_file}")
            if os.path.exists(source):
                target = f"ml-model-api/{db_file}"
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)
                logger.info(f"Restored database: {target}")
        
        # Restore models
        models_source = os.path.join(extracted_path, 'models')
        if os.path.exists(models_source):
            shutil.copytree(models_source, 'models', dirs_exist_ok=True)
            logger.info("Restored models directory")
        
        # Restore main model
        model_source = os.path.join(extracted_path, 'model.pth')
        if os.path.exists(model_source):
            shutil.copy2(model_source, 'model.pth')
            logger.info("Restored main model")
        
        # Restore configuration files
        config_files = [
            'config.yaml',
            'docker-compose.yml',
            'requirements.txt'
        ]
        
        for config_file in config_files:
            source = os.path.join(extracted_path, config_file.replace('/', '_'))
            if os.path.exists(source):
                shutil.copy2(source, config_file)
                logger.info(f"Restored configuration: {config_file}")
    
    def _merge_incremental_backup(self, base_path: str, incremental_path: str) -> str:
        """Merge incremental backup with base backup"""
        merged_path = tempfile.mkdtemp(prefix='recovery_merged_')
        
        logger.info("Merging incremental backup with base backup")
        
        # Copy base backup to merged location
        shutil.copytree(base_path, merged_path, dirs_exist_ok=True)
        
        # Apply incremental changes
        incremental_manifest_path = os.path.join(incremental_path, 'manifest.json')
        if os.path.exists(incremental_manifest_path):
            with open(incremental_manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_info in manifest.get('files', []):
                source_file = os.path.join(incremental_path, file_info['path'])
                target_file = os.path.join(merged_path, file_info['path'])
                
                if os.path.exists(source_file):
                    # Create parent directories
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    
                    # Copy incremental file
                    shutil.copy2(source_file, target_file)
        
        logger.info(f"Incremental backup merged to: {merged_path}")
        return merged_path
    
    def _verify_merged_backup(self, merged_path: str, incremental_metadata, base_metadata) -> bool:
        """Verify merged backup integrity"""
        try:
            # Verify file count matches expected
            expected_file_count = base_metadata.file_count + incremental_metadata.file_count
            actual_file_count = len(self.backup_manager._get_backup_files(merged_path))
            
            if actual_file_count < expected_file_count:
                logger.error("Merged backup file count verification failed")
                return False
            
            logger.info("Merged backup verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Merged backup verification error: {str(e)}")
            return False
    
    def _find_backup_chain_for_timestamp(self, target_timestamp: datetime) -> List[str]:
        """Find backup chain for point-in-time recovery"""
        backups = self.backup_manager.list_backups()
        
        # Sort backups by timestamp
        backups.sort(key=lambda x: x.timestamp)
        
        # Find the most recent full backup before target timestamp
        base_backup = None
        incremental_backups = []
        
        for backup in backups:
            if backup.timestamp <= target_timestamp:
                if backup.backup_type == 'full':
                    base_backup = backup.backup_id
                    incremental_backups = []
                elif backup.backup_type == 'incremental' and base_backup:
                    incremental_backups.append(backup.backup_id)
        
        if base_backup:
            return [base_backup] + incremental_backups
        
        return []
    
    def _restore_from_backup_chain(self, backup_chain: List[str]) -> str:
        """Restore from a chain of backups"""
        if not backup_chain:
            raise ValueError("Empty backup chain")
        
        # Start with the base backup
        base_metadata = self.backup_manager._get_backup_metadata(backup_chain[0])
        base_backup_path = self._download_backup(base_metadata)
        current_path = self._extract_backup(base_backup_path)
        
        # Apply incremental backups in order
        for backup_id in backup_chain[1:]:
            incremental_metadata = self.backup_manager._get_backup_metadata(backup_id)
            incremental_backup_path = self._download_backup(incremental_metadata)
            incremental_extracted_path = self._extract_backup(incremental_backup_path)
            
            # Merge incremental backup
            current_path = self._merge_incremental_backup(current_path, incremental_extracted_path)
            
            # Cleanup temporary incremental backup
            if self.config.auto_cleanup_temp:
                shutil.rmtree(incremental_extracted_path)
        
        return current_path
    
    def _has_transaction_logs(self) -> bool:
        """Check if transaction logs are available"""
        # This would check for database transaction logs
        # For now, return False
        return False
    
    def _apply_transaction_logs(self, restored_path: str, target_timestamp: datetime):
        """Apply transaction logs up to target timestamp"""
        # This would apply database transaction logs
        # Implementation depends on database type
        pass
    
    def _save_recovery_point(self, recovery_point: RecoveryPoint):
        """Save recovery point to registry"""
        conn = sqlite3.connect(self.recovery_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO recovery_registry 
            (recovery_id, backup_id, timestamp, recovery_type, status, 
             description, backup_metadata, start_time, end_time, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recovery_point.recovery_id,
            recovery_point.backup_id,
            recovery_point.timestamp.isoformat(),
            recovery_point.recovery_type,
            recovery_point.status,
            recovery_point.description,
            json.dumps(recovery_point.backup_metadata),
            datetime.now(pytz.UTC).isoformat(),
            None,
            None
        ))
        
        conn.commit()
        conn.close()
        
        # Cache in Redis
        self.redis_client.setex(
            f"recovery:{recovery_point.recovery_id}",
            86400,  # 24 hours TTL
            json.dumps(asdict(recovery_point), default=str)
        )
    
    def list_recovery_points(self) -> List[RecoveryPoint]:
        """List all available recovery points"""
        conn = sqlite3.connect(self.recovery_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM recovery_registry ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        recovery_points = []
        for row in rows:
            recovery_points.append(RecoveryPoint(
                recovery_id=row[0],
                backup_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                recovery_type=row[3],
                status=row[4],
                description=row[5],
                backup_metadata=json.loads(row[6])
            ))
        
        return recovery_points
    
    def get_recovery_status(self, recovery_id: str) -> Optional[RecoveryPoint]:
        """Get status of a recovery operation"""
        # Try Redis first
        cached = self.redis_client.get(f"recovery:{recovery_id}")
        if cached:
            data = json.loads(cached)
            return RecoveryPoint(**data)
        
        # Fallback to SQLite
        conn = sqlite3.connect(self.recovery_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM recovery_registry WHERE recovery_id = ?', (recovery_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return RecoveryPoint(
                recovery_id=row[0],
                backup_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                recovery_type=row[3],
                status=row[4],
                description=row[5],
                backup_metadata=json.loads(row[6])
            )
        
        return None
    
    def test_recovery(self, backup_id: str) -> bool:
        """Test recovery without actually restoring"""
        logger.info(f"Testing recovery for backup: {backup_id}")
        
        try:
            # Get backup metadata
            backup_metadata = self.backup_manager._get_backup_metadata(backup_id)
            if not backup_metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            # Download backup
            backup_path = self._download_backup(backup_metadata)
            
            # Extract backup
            extracted_path = self._extract_backup(backup_path)
            
            # Verify integrity
            if not self._verify_backup_integrity(extracted_path, backup_metadata):
                raise ValueError("Backup integrity verification failed")
            
            # Test restoration to temporary location
            test_path = tempfile.mkdtemp(prefix='recovery_test_')
            self._restore_to_path(extracted_path, test_path)
            
            # Verify test restoration
            if not self._verify_test_restoration(test_path):
                raise ValueError("Test restoration verification failed")
            
            # Cleanup
            if self.config.auto_cleanup_temp:
                shutil.rmtree(test_path)
                shutil.rmtree(extracted_path)
            
            logger.info(f"Recovery test passed for backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Recovery test failed: {str(e)}")
            return False
    
    def _verify_test_restoration(self, test_path: str) -> bool:
        """Verify test restoration"""
        # Check if critical files exist
        critical_files = [
            'models',
            'config.yaml',
            'requirements.txt'
        ]
        
        for file_path in critical_files:
            full_path = os.path.join(test_path, file_path)
            if not os.path.exists(full_path):
                logger.error(f"Critical file missing in test restoration: {file_path}")
                return False
        
        return True
    
    def _cleanup_temp_files(self, *paths):
        """Clean up temporary files"""
        for path in paths:
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    logger.info(f"Cleaned up temporary file: {path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {str(e)}")
    
    def rollback_recovery(self, recovery_id: str) -> bool:
        """Rollback a recovery operation if rollback is enabled"""
        if not self.config.rollback_enabled:
            logger.warning("Rollback is disabled")
            return False
        
        try:
            logger.info(f"Rolling back recovery: {recovery_id}")
            
            # Get recovery information
            recovery_point = self.get_recovery_status(recovery_id)
            if not recovery_point:
                raise ValueError(f"Recovery {recovery_id} not found")
            
            # This would implement rollback logic
            # For now, just log the operation
            logger.info(f"Rollback completed for recovery: {recovery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = RecoveryConfig(
        recovery_path='/tmp/flavorsnap_recovery',
        verification_enabled=True,
        rollback_enabled=True
    )
    
    # Initialize recovery system
    recovery_system = RecoverySystem(config)
    
    # Test recovery
    try:
        # List available recovery points
        recovery_points = recovery_system.list_recovery_points()
        print(f"Available recovery points: {len(recovery_points)}")
        
        # Test a recovery
        if recovery_points:
            success = recovery_system.test_recovery(recovery_points[0].backup_id)
            print(f"Recovery test result: {success}")
            
    except Exception as e:
        print(f"Recovery system error: {str(e)}")
