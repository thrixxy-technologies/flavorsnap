#!/usr/bin/env python3
"""
Advanced Backup Manager for FlavorSnap ML Model API
Implements automated backup system with scheduling, verification, and monitoring
"""

import os
import json
import sqlite3
import shutil
import gzip
import hashlib
import logging
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import redis
import psycopg2
from psycopg2 import sql
from dataclasses import dataclass, asdict
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """Backup configuration dataclass"""
    backup_type: str  # 'full', 'incremental', 'differential'
    storage_type: str  # 'local', 's3', 'gcs', 'azure'
    compression: bool = True
    encryption: bool = True
    retention_days: int = 30
    schedule: str = 'daily'  # 'hourly', 'daily', 'weekly'
    max_backup_size_gb: float = 10.0
    backup_path: str = '/tmp/flavorsnap_backups'
    s3_bucket: Optional[str] = None
    s3_region: str = 'us-east-1'
    verification_enabled: bool = True
    parallel_uploads: int = 4

@dataclass
class BackupMetadata:
    """Backup metadata for tracking and verification"""
    backup_id: str
    backup_type: str
    timestamp: datetime
    size_bytes: int
    checksum: str
    file_count: int
    compression_ratio: float
    storage_location: str
    status: str  # 'created', 'verified', 'failed'
    verification_timestamp: Optional[datetime] = None
    recovery_test_status: Optional[str] = None

class BackupManager:
    """Advanced backup management system"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backup_db_path = os.path.join(config.backup_path, 'backup_registry.db')
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.s3_client = None
        self.scheduler_thread = None
        self.running = False
        
        # Initialize backup directory
        Path(config.backup_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize storage clients
        self._init_storage_client()
        
        # Initialize backup registry database
        self._init_backup_registry()
        
        logger.info(f"BackupManager initialized with config: {config}")
    
    def _init_storage_client(self):
        """Initialize cloud storage client based on configuration"""
        if self.config.storage_type == 's3' and self.config.s3_bucket:
            self.s3_client = boto3.client('s3', region_name=self.config.s3_region)
            logger.info(f"S3 client initialized for bucket: {self.config.s3_bucket}")
    
    def _init_backup_registry(self):
        """Initialize SQLite database for backup metadata"""
        conn = sqlite3.connect(self.backup_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_registry (
                backup_id TEXT PRIMARY KEY,
                backup_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                file_count INTEGER NOT NULL,
                compression_ratio REAL NOT NULL,
                storage_location TEXT NOT NULL,
                status TEXT NOT NULL,
                verification_timestamp TEXT,
                recovery_test_status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type TEXT NOT NULL,
                schedule_expression TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT,
                enabled BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Backup registry database initialized")
    
    def create_full_backup(self) -> BackupMetadata:
        """Create a full backup of the system"""
        backup_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(self.config.backup_path, backup_id)
        
        try:
            logger.info(f"Starting full backup: {backup_id}")
            
            # Create backup directory
            Path(backup_path).mkdir(parents=True, exist_ok=True)
            
            # Backup databases
            db_backups = self._backup_databases(backup_path)
            
            # Backup model files
            model_backups = self._backup_models(backup_path)
            
            # Backup configuration files
            config_backups = self._backup_configurations(backup_path)
            
            # Create backup manifest
            manifest = self._create_backup_manifest(
                backup_id, db_backups + model_backups + config_backups
            )
            manifest_path = os.path.join(backup_path, 'manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            # Compress backup if enabled
            if self.config.compression:
                backup_path = self._compress_backup(backup_path)
            
            # Calculate backup statistics
            backup_size = self._calculate_backup_size(backup_path)
            checksum = self._calculate_checksum(backup_path)
            file_count = len(self._get_backup_files(backup_path))
            
            # Store backup (local or cloud)
            storage_location = self._store_backup(backup_path, backup_id)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type='full',
                timestamp=datetime.now(pytz.UTC),
                size_bytes=backup_size,
                checksum=checksum,
                file_count=file_count,
                compression_ratio=self._calculate_compression_ratio(backup_path),
                storage_location=storage_location,
                status='created'
            )
            
            # Save metadata to registry
            self._save_backup_metadata(metadata)
            
            # Verify backup if enabled
            if self.config.verification_enabled:
                self._verify_backup(metadata)
            
            logger.info(f"Full backup completed: {backup_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Full backup failed: {str(e)}")
            # Cleanup failed backup
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            raise
    
    def create_incremental_backup(self, base_backup_id: str) -> BackupMetadata:
        """Create incremental backup based on a full backup"""
        backup_id = f"incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(self.config.backup_path, backup_id)
        
        try:
            logger.info(f"Starting incremental backup: {backup_id} based on {base_backup_id}")
            
            # Get base backup metadata
            base_metadata = self._get_backup_metadata(base_backup_id)
            if not base_metadata:
                raise ValueError(f"Base backup {base_backup_id} not found")
            
            # Create backup directory
            Path(backup_path).mkdir(parents=True, exist_ok=True)
            
            # Find changed files since base backup
            changed_files = self._find_changed_files(base_metadata.timestamp)
            
            if not changed_files:
                logger.info("No changes detected, skipping incremental backup")
                return None
            
            # Backup only changed files
            self._backup_files_list(changed_files, backup_path)
            
            # Create incremental manifest
            manifest = self._create_backup_manifest(backup_id, changed_files, base_backup_id)
            manifest_path = os.path.join(backup_path, 'manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            # Compress backup if enabled
            if self.config.compression:
                backup_path = self._compress_backup(backup_path)
            
            # Calculate backup statistics
            backup_size = self._calculate_backup_size(backup_path)
            checksum = self._calculate_checksum(backup_path)
            file_count = len(changed_files)
            
            # Store backup
            storage_location = self._store_backup(backup_path, backup_id)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type='incremental',
                timestamp=datetime.now(pytz.UTC),
                size_bytes=backup_size,
                checksum=checksum,
                file_count=file_count,
                compression_ratio=self._calculate_compression_ratio(backup_path),
                storage_location=storage_location,
                status='created'
            )
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            # Verify backup if enabled
            if self.config.verification_enabled:
                self._verify_backup(metadata)
            
            logger.info(f"Incremental backup completed: {backup_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Incremental backup failed: {str(e)}")
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            raise
    
    def _backup_databases(self, backup_path: str) -> List[str]:
        """Backup all databases"""
        db_backups = []
        
        # Backup SQLite databases
        sqlite_dbs = [
            'ml-model-api/model_registry.db',
            'ml-model-api/predictions.db'
        ]
        
        for db_path in sqlite_dbs:
            if os.path.exists(db_path):
                backup_file = os.path.join(backup_path, f"sqlite_{os.path.basename(db_path)}")
                shutil.copy2(db_path, backup_file)
                db_backups.append(backup_file)
                logger.info(f"Backed up SQLite database: {db_path}")
        
        # Backup PostgreSQL databases if configured
        try:
            # This would be configured based on environment
            pg_backup_file = os.path.join(backup_path, 'postgresql_backup.sql')
            # pg_dump command would be executed here
            db_backups.append(pg_backup_file)
        except Exception as e:
            logger.warning(f"PostgreSQL backup skipped: {str(e)}")
        
        return db_backups
    
    def _backup_models(self, backup_path: str) -> List[str]:
        """Backup ML model files"""
        model_backups = []
        model_dir = 'models'
        
        if os.path.exists(model_dir):
            backup_model_dir = os.path.join(backup_path, 'models')
            shutil.copytree(model_dir, backup_model_dir, dirs_exist_ok=True)
            
            for root, dirs, files in os.walk(backup_model_dir):
                for file in files:
                    model_backups.append(os.path.join(root, file))
            
            logger.info(f"Backed up models directory: {len(model_backups)} files")
        
        # Backup main model file
        model_file = 'model.pth'
        if os.path.exists(model_file):
            backup_file = os.path.join(backup_path, model_file)
            shutil.copy2(model_file, backup_file)
            model_backups.append(backup_file)
            logger.info(f"Backed up main model: {model_file}")
        
        return model_backups
    
    def _backup_configurations(self, backup_path: str) -> List[str]:
        """Backup configuration files"""
        config_backups = []
        config_files = [
            'config.yaml',
            'docker-compose.yml',
            'requirements.txt',
            '.env.example',
            'ml-model-api/app.py',
            'ml-model-api/monitoring.py'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                backup_file = os.path.join(backup_path, config_file.replace('/', '_'))
                shutil.copy2(config_file, backup_file)
                config_backups.append(backup_file)
                logger.info(f"Backed up configuration: {config_file}")
        
        return config_backups
    
    def _create_backup_manifest(self, backup_id: str, files: List[str], 
                              base_backup_id: Optional[str] = None) -> Dict:
        """Create backup manifest with file metadata"""
        manifest = {
            'backup_id': backup_id,
            'backup_type': 'incremental' if base_backup_id else 'full',
            'base_backup_id': base_backup_id,
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'files': []
        }
        
        for file_path in files:
            if os.path.exists(file_path):
                file_stat = os.stat(file_path)
                file_checksum = self._calculate_file_checksum(file_path)
                
                manifest['files'].append({
                    'path': file_path,
                    'size': file_stat.st_size,
                    'modified_time': datetime.fromtimestamp(file_stat.st_mtime, pytz.UTC).isoformat(),
                    'checksum': file_checksum
                })
        
        return manifest
    
    def _compress_backup(self, backup_path: str) -> str:
        """Compress backup directory"""
        compressed_path = f"{backup_path}.tar.gz"
        
        logger.info(f"Compressing backup to: {compressed_path}")
        
        # Create tar.gz archive
        import tarfile
        with tarfile.open(compressed_path, 'w:gz') as tar:
            tar.add(backup_path, arcname=os.path.basename(backup_path))
        
        # Remove uncompressed directory
        shutil.rmtree(backup_path)
        
        logger.info(f"Backup compressed. Size: {os.path.getsize(compressed_path) / (1024*1024):.2f} MB")
        return compressed_path
    
    def _calculate_checksum(self, path: str) -> str:
        """Calculate SHA-256 checksum of backup"""
        hash_sha256 = hashlib.sha256()
        
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of a single file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _calculate_backup_size(self, path: str) -> int:
        """Calculate total size of backup"""
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
            return total_size
        return 0
    
    def _get_backup_files(self, path: str) -> List[str]:
        """Get list of all files in backup"""
        files = []
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for root, dirs, file_list in os.walk(path):
                for file in file_list:
                    files.append(os.path.join(root, file))
        return files
    
    def _calculate_compression_ratio(self, path: str) -> float:
        """Calculate compression ratio"""
        # This would compare original vs compressed size
        # For now, return a placeholder
        return 0.7
    
    def _store_backup(self, backup_path: str, backup_id: str) -> str:
        """Store backup to configured storage"""
        if self.config.storage_type == 'local':
            return backup_path
        elif self.config.storage_type == 's3' and self.s3_client:
            return self._store_to_s3(backup_path, backup_id)
        else:
            raise ValueError(f"Unsupported storage type: {self.config.storage_type}")
    
    def _store_to_s3(self, backup_path: str, backup_id: str) -> str:
        """Store backup to AWS S3"""
        s3_key = f"backups/{backup_id}"
        
        try:
            if os.path.isfile(backup_path):
                self.s3_client.upload_file(backup_path, self.config.s3_bucket, s3_key)
            elif os.path.isdir(backup_path):
                # Upload directory contents
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        local_path = os.path.join(root, file)
                        relative_path = os.path.relpath(local_path, backup_path)
                        s3_file_key = f"{s3_key}/{relative_path}"
                        self.s3_client.upload_file(local_path, self.config.s3_bucket, s3_file_key)
            
            logger.info(f"Backup stored to S3: s3://{self.config.s3_bucket}/{s3_key}")
            return f"s3://{self.config.s3_bucket}/{s3_key}"
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise
    
    def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to registry"""
        conn = sqlite3.connect(self.backup_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO backup_registry 
            (backup_id, backup_type, timestamp, size_bytes, checksum, 
             file_count, compression_ratio, storage_location, status,
             verification_timestamp, recovery_test_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.backup_id,
            metadata.backup_type,
            metadata.timestamp.isoformat(),
            metadata.size_bytes,
            metadata.checksum,
            metadata.file_count,
            metadata.compression_ratio,
            metadata.storage_location,
            metadata.status,
            metadata.verification_timestamp.isoformat() if metadata.verification_timestamp else None,
            metadata.recovery_test_status
        ))
        
        conn.commit()
        conn.close()
        
        # Cache in Redis
        self.redis_client.setex(
            f"backup:{metadata.backup_id}",
            86400,  # 24 hours TTL
            json.dumps(asdict(metadata), default=str)
        )
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup metadata from registry"""
        # Try Redis first
        cached = self.redis_client.get(f"backup:{backup_id}")
        if cached:
            data = json.loads(cached)
            return BackupMetadata(**data)
        
        # Fallback to SQLite
        conn = sqlite3.connect(self.backup_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM backup_registry WHERE backup_id = ?', (backup_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return BackupMetadata(
                backup_id=row[0],
                backup_type=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                size_bytes=row[3],
                checksum=row[4],
                file_count=row[5],
                compression_ratio=row[6],
                storage_location=row[7],
                status=row[8],
                verification_timestamp=datetime.fromisoformat(row[9]) if row[9] else None,
                recovery_test_status=row[10]
            )
        
        return None
    
    def _verify_backup(self, metadata: BackupMetadata) -> bool:
        """Verify backup integrity"""
        try:
            logger.info(f"Verifying backup: {metadata.backup_id}")
            
            # Download backup if stored in cloud
            local_backup_path = self._download_backup_for_verification(metadata)
            
            # Verify checksum
            calculated_checksum = self._calculate_checksum(local_backup_path)
            if calculated_checksum != metadata.checksum:
                logger.error(f"Checksum verification failed for {metadata.backup_id}")
                return False
            
            # Verify file count
            file_count = len(self._get_backup_files(local_backup_path))
            if file_count != metadata.file_count:
                logger.error(f"File count verification failed for {metadata.backup_id}")
                return False
            
            # Verify manifest if exists
            manifest_path = os.path.join(local_backup_path, 'manifest.json')
            if os.path.exists(manifest_path):
                if not self._verify_manifest(manifest_path, local_backup_path):
                    logger.error(f"Manifest verification failed for {metadata.backup_id}")
                    return False
            
            # Update verification status
            metadata.verification_timestamp = datetime.now(pytz.UTC)
            metadata.status = 'verified'
            self._save_backup_metadata(metadata)
            
            logger.info(f"Backup verification completed: {metadata.backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {str(e)}")
            return False
    
    def _download_backup_for_verification(self, metadata: BackupMetadata) -> str:
        """Download backup for local verification"""
        if metadata.storage_location.startswith('s3://'):
            # Download from S3
            import tempfile
            temp_dir = tempfile.mkdtemp()
            backup_path = os.path.join(temp_dir, os.path.basename(metadata.backup_id))
            
            # Parse S3 URL
            s3_url_parts = metadata.storage_location.replace('s3://', '').split('/')
            bucket = s3_url_parts[0]
            key = '/'.join(s3_url_parts[1:])
            
            self.s3_client.download_file(bucket, key, backup_path)
            return backup_path
        else:
            # Local backup
            return metadata.storage_location
    
    def _verify_manifest(self, manifest_path: str, backup_path: str) -> bool:
        """Verify backup manifest integrity"""
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_info in manifest.get('files', []):
                file_path = os.path.join(backup_path, file_info['path'])
                if not os.path.exists(file_path):
                    logger.error(f"Manifest file not found: {file_path}")
                    return False
                
                # Verify file checksum
                calculated_checksum = self._calculate_file_checksum(file_path)
                if calculated_checksum != file_info['checksum']:
                    logger.error(f"File checksum mismatch: {file_path}")
                    return False
                
                # Verify file size
                actual_size = os.path.getsize(file_path)
                if actual_size != file_info['size']:
                    logger.error(f"File size mismatch: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Manifest verification error: {str(e)}")
            return False
    
    def _find_changed_files(self, since_timestamp: datetime) -> List[str]:
        """Find files modified since given timestamp"""
        changed_files = []
        
        # Directories to monitor
        monitor_dirs = [
            'ml-model-api',
            'models',
            'config',
            '.'
        ]
        
        for directory in monitor_dirs:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_stat = os.stat(file_path)
                        
                        if datetime.fromtimestamp(file_stat.st_mtime, pytz.UTC) > since_timestamp:
                            changed_files.append(file_path)
        
        return changed_files
    
    def _backup_files_list(self, files: List[str], backup_path: str):
        """Backup specific list of files"""
        for file_path in files:
            if os.path.exists(file_path):
                # Create same directory structure in backup
                relative_path = os.path.relpath(file_path, '.')
                backup_file_path = os.path.join(backup_path, relative_path)
                
                # Create parent directories
                os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(file_path, backup_file_path)
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[BackupMetadata]:
        """List all backups or filtered by type"""
        conn = sqlite3.connect(self.backup_db_path)
        cursor = conn.cursor()
        
        if backup_type:
            cursor.execute('SELECT * FROM backup_registry WHERE backup_type = ? ORDER BY timestamp DESC', (backup_type,))
        else:
            cursor.execute('SELECT * FROM backup_registry ORDER BY timestamp DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        backups = []
        for row in rows:
            backups.append(BackupMetadata(
                backup_id=row[0],
                backup_type=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                size_bytes=row[3],
                checksum=row[4],
                file_count=row[5],
                compression_ratio=row[6],
                storage_location=row[7],
                status=row[8],
                verification_timestamp=datetime.fromisoformat(row[9]) if row[9] else None,
                recovery_test_status=row[10]
            ))
        
        return backups
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=self.config.retention_days)
        
        conn = sqlite3.connect(self.backup_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT backup_id, storage_location FROM backup_registry WHERE timestamp < ?', (cutoff_date.isoformat(),))
        old_backups = cursor.fetchall()
        
        for backup_id, storage_location in old_backups:
            try:
                # Remove from cloud storage if applicable
                if storage_location.startswith('s3://'):
                    self._remove_from_s3(storage_location)
                
                # Remove from registry
                cursor.execute('DELETE FROM backup_registry WHERE backup_id = ?', (backup_id,))
                
                logger.info(f"Cleaned up old backup: {backup_id}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup backup {backup_id}: {str(e)}")
        
        conn.commit()
        conn.close()
    
    def _remove_from_s3(self, s3_url: str):
        """Remove backup from S3"""
        s3_url_parts = s3_url.replace('s3://', '').split('/')
        bucket = s3_url_parts[0]
        key = '/'.join(s3_url_parts[1:])
        
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Removed from S3: {s3_url}")
        except ClientError as e:
            logger.error(f"Failed to remove from S3: {str(e)}")
    
    def start_scheduler(self):
        """Start backup scheduler"""
        if self.config.schedule == 'hourly':
            schedule.every().hour.do(self._scheduled_backup)
        elif self.config.schedule == 'daily':
            schedule.every().day.at("02:00").do(self._scheduled_backup)
        elif self.config.schedule == 'weekly':
            schedule.every().sunday.at("02:00").do(self._scheduled_backup)
        
        # Schedule cleanup
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"Backup scheduler started with {self.config.schedule} schedule")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            threading.Event().wait(60)  # Check every minute
    
    def _scheduled_backup(self):
        """Execute scheduled backup"""
        try:
            logger.info("Starting scheduled backup")
            metadata = self.create_full_backup()
            logger.info(f"Scheduled backup completed: {metadata.backup_id}")
        except Exception as e:
            logger.error(f"Scheduled backup failed: {str(e)}")
    
    def stop_scheduler(self):
        """Stop backup scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Backup scheduler stopped")

# Example usage and initialization
if __name__ == "__main__":
    # Example configuration
    config = BackupConfig(
        backup_type='full',
        storage_type='local',
        compression=True,
        encryption=True,
        retention_days=30,
        schedule='daily',
        backup_path='/tmp/flavorsnap_backups'
    )
    
    # Initialize backup manager
    backup_manager = BackupManager(config)
    
    # Create a backup
    try:
        metadata = backup_manager.create_full_backup()
        print(f"Backup created: {metadata.backup_id}")
        
        # List backups
        backups = backup_manager.list_backups()
        print(f"Total backups: {len(backups)}")
        
    except Exception as e:
        print(f"Backup failed: {str(e)}")
